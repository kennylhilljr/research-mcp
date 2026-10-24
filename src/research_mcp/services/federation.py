"""Cross-source search: selection, fan-out, merge, ranking and the combined cursor.

LLD-search-v2 5.4. Search recording is an injected port whose default does nothing; M0
writes no ``searches`` row (M0-plan-v4 section 2.2, row M0-13; SRCH-34 wires it in M1).
"""

import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Literal

import anyio

from research_mcp.core.budget import decode_cursor, encode_cursor
from research_mcp.core.envelope import SourceStatus
from research_mcp.core.errors import ErrorCode, ToolError
from research_mcp.core.models import FederatedResult, SearchPage, SearchRequest, Work
from research_mcp.services.works import group, merge, run_sources
from research_mcp.settings import Settings
from research_mcp.sources.base import Capability, SourceAdapter
from research_mcp.sources.registry import SourceRegistry

RRF_K = 60
MULTI_SOURCE_BOOST = 0.1
_log = logging.getLogger(__name__)

RecordSearch = Callable[[SearchRequest, FederatedResult, int], Awaitable[None]]


async def record_nothing(req: SearchRequest, result: FederatedResult, latency_ms: int) -> None:
    """The default search-recording port: M0 keeps no search records."""


def rank(pages: Sequence[tuple[str, SearchPage]], *, fuzzy: bool = True) -> list[Work]:
    """Merged works by reciprocal rank fusion, plus a boost for each additional source.

    A work's rank in a source is the best position of its records on that source's page.
    Equal scores keep the order of first appearance.
    """
    records = []
    positions: dict[int, tuple[str, int]] = {}
    for source, page in pages:
        for position, record in enumerate(page.records, start=1):
            positions[id(record)] = (source, position)
            records.append(record)
    scored: list[tuple[float, int, Work]] = []
    for index, members in enumerate(group(records, fuzzy=fuzzy)):
        best: dict[str, int] = {}
        for record in members.records:
            source, position = positions[id(record)]
            best[source] = min(best.get(source, position), position)
        score = sum(1 / (RRF_K + p) for p in best.values())
        score += MULTI_SOURCE_BOOST * (len(best) - 1)
        scored.append((-score, index, merge(members)))
    return [work for _, _, work in sorted(scored, key=lambda item: item[:2])]


class FederationService:
    def __init__(
        self,
        registry: SourceRegistry,
        settings: Settings,
        cursor_key: bytes,
        *,
        record_search: RecordSearch = record_nothing,
    ) -> None:
        self._registry = registry
        self._settings = settings
        self._cursor_key = cursor_key
        self._record_search = record_search

    def _slots(self, cursor: str | None) -> dict[str, str] | None:
        """Each source's own cursor; ``None`` on the first page. Absent means exhausted."""
        if cursor is None:
            return None
        slots = decode_cursor(cursor, self._cursor_key).get("s")
        if not isinstance(slots, dict):
            raise ToolError(ErrorCode.INVALID_ARGUMENT, "Invalid cursor")
        own: dict[str, str] = {}
        for source, value in slots.items():
            if not isinstance(value, str):
                raise ToolError(ErrorCode.INVALID_ARGUMENT, "Invalid cursor")
            own[source] = value
        return own

    # @spec SRCH-1, SRCH-2, SRCH-3, SRCH-6, SRCH-7, SRCH-8
    async def search(
        self,
        req: SearchRequest,
        sources: Literal["auto"] | Sequence[str] = "auto",
        groups: Sequence[str] = (),
        *,
        per_source_limit: int = 10,
    ) -> FederatedResult:
        """One page of merged, ranked works with exactly one status per selected source."""
        started = anyio.current_time()
        federation = self._settings.federation
        explicit = None if sources == "auto" else list(sources)
        selected = self._registry.select(groups or None, Capability.SEARCH, req.filters, explicit)
        slots = self._slots(req.cursor)
        statuses: dict[str, SourceStatus] = {}
        runnable = []
        for item in selected:
            if item.skip is not None:
                statuses[item.source] = item.skip
            elif slots is not None and item.source not in slots:
                statuses[item.source] = SourceStatus(source=item.source, state="empty")
            else:
                runnable.append(item)

        async def search(adapter: SourceAdapter) -> SearchPage:
            limit = min(per_source_limit, adapter.spec.max_page_size)
            cursor = None if slots is None else slots[adapter.spec.id]
            return await adapter.search(req.model_copy(update={"limit": limit, "cursor": cursor}))

        answers, failures = await run_sources(runnable, search, federation.deadline_s)
        statuses.update(failures)
        pages: list[tuple[str, SearchPage]] = []
        next_slots: dict[str, str] = {}
        for item in runnable:
            answer = answers.get(item.source)
            if answer is None:
                continue
            count = len(answer.value.records)
            statuses[item.source] = SourceStatus(
                source=item.source,
                state="ok" if count else "empty",
                count=count,
                latency_ms=answer.latency_ms,
            )
            pages.append((item.source, answer.value))
            if answer.value.next_cursor is not None:
                next_slots[item.source] = answer.value.next_cursor
        works = rank(pages, fuzzy=federation.fuzzy_merge)[: req.limit]
        result = FederatedResult(
            works=works,
            statuses=[statuses[item.source] for item in selected],
            next_cursor=encode_cursor({"s": dict(next_slots)}, self._cursor_key)
            if next_slots
            else None,
        )
        if federation.record_searches:
            await self._record(req, result, int((anyio.current_time() - started) * 1000))
        return result

    async def _record(self, req: SearchRequest, result: FederatedResult, latency_ms: int) -> None:
        try:
            await self._record_search(req, result, latency_ms)
        except Exception as exc:  # noqa: BLE001 - a recording failure never fails the search
            _log.warning("search record failed", extra={"error": type(exc).__name__})
