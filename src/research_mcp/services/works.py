"""Grouping and merging of source records, and ``get_work`` (LLD-search-v2 5.3).

``group`` and ``merge`` are pure. ``run_sources`` is the fan-out that ``get_work`` and the
federation service share: one task per source under its own timeout and the overall
deadline, so a slow or failing source only ever costs its own status (SRCH-FR-3).
"""

import logging
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass

import anyio

from research_mcp.core.envelope import SourceStatus
from research_mcp.core.errors import ErrorCode, HttpError, ToolError
from research_mcp.core.ids import Identifier, parse_any, title_key
from research_mcp.core.models import Conflict, JsonValue, OaLocation, Work, WorkRecord
from research_mcp.settings import Settings
from research_mcp.sources.base import GROUPS, Capability, SourceAdapter
from research_mcp.sources.registry import Selected, SourceRegistry

SOURCE_PRIORITY = ("crossref", "openalex", "datacite", "semantic_scholar")
_HTTP_STATES: dict[ErrorCode, str] = {
    ErrorCode.RATE_LIMITED: "rate_limited",
    ErrorCode.BUDGET_EXHAUSTED: "budget_exhausted",
    ErrorCode.UPSTREAM_TIMEOUT: "timeout",
    ErrorCode.UNCONFIGURED: "unconfigured",
    ErrorCode.DISABLED: "disabled",
}
_log = logging.getLogger(__name__)


@dataclass
class Group:
    records: list[WorkRecord]
    fuzzy: bool = False


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, a: int, b: int) -> None:
        a, b = self.find(a), self.find(b)
        # The lower index stays the root, so groups keep the order of first appearance.
        self.parent[max(a, b)] = min(a, b)

    def clusters(self) -> list[list[int]]:
        roots: dict[int, list[int]] = {}
        for item in range(len(self.parent)):
            roots.setdefault(self.find(item), []).append(item)
        return list(roots.values())


def _join[K](keys: Sequence[Iterable[K]]) -> list[list[int]]:
    """Clusters of the item indexes that share at least one key, transitively."""
    sets = _UnionFind(len(keys))
    owner: dict[K, int] = {}
    for index, item_keys in enumerate(keys):
        for key in item_keys:
            if key in owner:
                sets.union(owner[key], index)
            else:
                owner[key] = index
    return sets.clusters()


def _fuzzy_key(record: WorkRecord) -> tuple[str, int, str] | None:
    """Title key, year and first author's family name; ``None`` when any is missing."""
    if record.year is None or not record.authors:
        return None
    first = record.authors[0]
    # [assumption] An author without a family name falls back to the last word of the name.
    family = (first.family or "".join(first.name.split()[-1:])).casefold()
    key = title_key(record.title)
    return (key, record.year, family) if key and family else None


# @spec SRCH-4, SRCH-5
def group(records: Sequence[WorkRecord], *, fuzzy: bool = True) -> list[Group]:
    """Union-find over every identifier, then the fuzzy merge when ``fuzzy`` is on."""
    by_id = _join([[(i.scheme, i.value) for i in record.ids] for record in records])
    if not fuzzy:
        return [Group([records[i] for i in members]) for members in by_id]
    keys = [{k for i in members if (k := _fuzzy_key(records[i])) is not None} for members in by_id]
    groups = []
    for joined in _join(keys):
        members = sorted(i for cluster in joined for i in by_id[cluster])
        groups.append(Group([records[i] for i in members], fuzzy=len(joined) > 1))
    return groups


def _by_priority(records: Sequence[WorkRecord]) -> list[WorkRecord]:
    rank = {source: index for index, source in enumerate(SOURCE_PRIORITY)}
    return sorted(records, key=lambda r: rank.get(r.provenance.source, len(rank)))


def _conflict(
    field: str,
    records: Sequence[WorkRecord],
    value: Callable[[WorkRecord], JsonValue],
    same: Callable[[JsonValue], object] = lambda v: v,
) -> Conflict | None:
    values: dict[str, JsonValue] = {}
    seen: set[object] = set()
    for record in records:
        found = value(record)
        if found is not None and record.provenance.source not in values:
            values[record.provenance.source] = found
            seen.add(same(found))
    return Conflict(field=field, values=values) if len(seen) > 1 else None


def _unique_ids(records: Sequence[WorkRecord]) -> list[Identifier]:
    ids: dict[tuple[str, str], Identifier] = {}
    for record in records:
        for ident in record.ids:
            ids.setdefault((ident.scheme, ident.value), ident)
    return list(ids.values())


def _unique_locations(records: Sequence[WorkRecord]) -> list[OaLocation]:
    locations: dict[str, OaLocation] = {}
    for record in records:
        for location in record.oa_locations:
            locations.setdefault(location.url, location)
    return list(locations.values())


# @spec SRCH-9
def merge(group: Group) -> Work:
    """One work: fields by source priority, every id, OA location and source, and conflicts."""
    ordered = _by_priority(group.records)
    conflicts = [
        # Titles that differ only in case, punctuation or stop words agree.
        _conflict("title", ordered, lambda r: r.title or None, lambda v: title_key(str(v))),
        _conflict("year", ordered, lambda r: r.year),
        _conflict("is_retracted", ordered, lambda r: r.is_retracted),
    ]
    return Work(
        ids=_unique_ids(group.records),
        title=next((r.title for r in ordered if r.title), ordered[0].title),
        authors=next((r.authors for r in ordered if r.authors), []),
        year=next((r.year for r in ordered if r.year is not None), None),
        venue=next((r.venue for r in ordered if r.venue), None),
        work_type=ordered[0].work_type,
        abstract=next((r.abstract for r in ordered if r.abstract), None),
        oa_locations=_unique_locations(ordered),
        found_in=list(dict.fromkeys(r.provenance.source for r in group.records)),
        fuzzy=group.fuzzy,
        conflicts=[c for c in conflicts if c is not None],
    )


@dataclass(frozen=True)
class Answer[T]:
    value: T
    latency_ms: int


def _elapsed_ms(started: float) -> int:
    return int((anyio.current_time() - started) * 1000)


def _failure(source: str, exc: Exception, latency_ms: int) -> SourceStatus:
    if isinstance(exc, TimeoutError):
        return SourceStatus(
            source=source,
            state="timeout",
            latency_ms=latency_ms,
            error_code=ErrorCode.UPSTREAM_TIMEOUT,
        )
    if isinstance(exc, HttpError):
        state = _HTTP_STATES.get(exc.code, "error")
        return SourceStatus.model_validate(
            {
                "source": source,
                "state": state,
                "latency_ms": latency_ms,
                "retry_after_ms": exc.retry_after_ms,
                "error_code": exc.code,
            }
        )
    # The type only: an adapter's message may quote an upstream body.
    _log.warning("source failed", extra={"source": source, "error": type(exc).__name__})
    return SourceStatus(
        source=source, state="error", latency_ms=latency_ms, error_code=ErrorCode.INTERNAL
    )


async def run_sources[T](
    selected: Sequence[Selected],
    call: Callable[[SourceAdapter], Awaitable[T]],
    deadline_s: float,
) -> tuple[dict[str, Answer[T]], dict[str, SourceStatus]]:
    """Run ``call`` on every source concurrently: the answers, and a status per failure.

    Each source runs under ``fail_after(spec.timeout_s)``; whatever is still running at
    ``deadline_s`` is cancelled and reported as ``timeout``.
    """
    answers: dict[str, Answer[T]] = {}
    failures: dict[str, SourceStatus] = {}
    started = anyio.current_time()

    async def one(item: Selected) -> None:
        begun = anyio.current_time()
        try:
            with anyio.fail_after(item.adapter.spec.timeout_s):
                value = await call(item.adapter)
        except Exception as exc:  # noqa: BLE001 - a failing source never fails the call
            failures[item.source] = _failure(item.source, exc, _elapsed_ms(begun))
        else:
            answers[item.source] = Answer(value, _elapsed_ms(begun))

    with anyio.move_on_after(deadline_s):
        async with anyio.create_task_group() as tasks:
            for item in selected:
                tasks.start_soon(one, item)
    for item in selected:
        if item.source not in answers and item.source not in failures:
            failures[item.source] = _failure(item.source, TimeoutError(), _elapsed_ms(started))
    return answers, failures


class WorksService:
    def __init__(self, registry: SourceRegistry, settings: Settings) -> None:
        self._registry = registry
        self._settings = settings

    # @spec SRCH-17
    async def get_work(self, id: str) -> tuple[Work, list[SourceStatus]]:
        """The work behind ``id``, merged from every source that understands its scheme.

        Raises ``IdentifierError`` for an id that does not parse, before any call.
        """
        ident = parse_any(id)
        selected = [
            item
            for item in self._registry.select(sorted(GROUPS), Capability.GET)
            if ident.scheme in item.adapter.spec.id_schemes
        ]
        statuses = {item.source: item.skip for item in selected if item.skip is not None}
        runnable = [item for item in selected if item.skip is None]

        async def get(adapter: SourceAdapter) -> WorkRecord | None:
            return await adapter.get(ident)

        answers, failures = await run_sources(runnable, get, self._settings.federation.deadline_s)
        statuses.update(failures)
        records: list[WorkRecord] = []
        for source, answer in answers.items():
            found = answer.value is not None
            if answer.value is not None:
                records.append(answer.value)
            statuses[source] = SourceStatus(
                source=source,
                state="ok" if found else "empty",
                count=int(found),
                latency_ms=answer.latency_ms,
            )
        ordered = [statuses[item.source] for item in selected]
        if not records:
            raise ToolError(ErrorCode.NOT_FOUND, "No source has a record for this identifier")
        # Keep the selection order, so source priority ties break the same way every time.
        rank = {item.source: index for index, item in enumerate(selected)}
        records.sort(key=lambda r: rank.get(r.provenance.source, len(rank)))
        return merge(Group(records)), ordered
