"""The federation service: selection, fan-out, ranking and the combined cursor.

LLD-search-v2 5.4 and the M0-13 row of M0-plan-v4 section 2.2. Every source is a scripted
in-memory adapter registered through ``extra_adapters``; nothing reaches the network.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, cast

import anyio
import pytest

from research_mcp.core.budget import decode_cursor, encode_cursor
from research_mcp.core.errors import ErrorCode, HttpError, ToolError
from research_mcp.core.ids import Identifier
from research_mcp.core.models import (
    FederatedResult,
    Provenance,
    SearchFilters,
    SearchPage,
    SearchRequest,
    WorkRecord,
)
from research_mcp.core.specs import AuthSpec, RateSpec
from research_mcp.services.federation import FederationService
from research_mcp.settings import Settings, SourceSettings
from research_mcp.sources.base import Capability, SourceContext, SourceSpec
from research_mcp.sources.registry import SourceRegistry
from research_mcp.testing.clock import FakeClock

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
KEY = b"k" * 32
Search = Callable[[SearchRequest], Awaitable[SearchPage]]


class OfflineSettings(Settings):
    """Settings from keyword arguments only: no config file, no environment."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


def rec(source: str, doi: str) -> WorkRecord:
    return WorkRecord(
        ids=[Identifier("doi", doi)],
        title=f"Work {doi}",
        provenance=Provenance(
            source=source, upstream_id=doi, adapter_version="1", retrieved_at=NOW
        ),
    )


def spec(id: str, **overrides: Any) -> SourceSpec:
    values: dict[str, Any] = {
        "id": id,
        "title": f"{id} source",
        "group": "scholarly",
        "capabilities": frozenset({Capability.SEARCH}),
        "id_schemes": frozenset({"doi"}),
        "hosts": frozenset({f"api.{id}.org"}),
        "auth": None,
        "rate": RateSpec(rps=5.0),
    }
    values.update(overrides)
    return SourceSpec(**values)


def page(source: str, *dois: str, next_cursor: str | None = None) -> Search:
    async def search(req: SearchRequest) -> SearchPage:
        return SearchPage(records=[rec(source, d) for d in dois], next_cursor=next_cursor)

    return search


def sleeping(seconds: float, source: str = "x") -> Search:
    async def search(req: SearchRequest) -> SearchPage:
        await anyio.sleep(seconds)
        return SearchPage(records=[rec(source, f"10.1/{source}")])

    return search


def failing(exc: Exception) -> Search:
    async def search(req: SearchRequest) -> SearchPage:
        raise exc

    return search


class Harness:
    """A registry of scripted sources that records every search request it receives."""

    def __init__(self) -> None:
        self.adapters: list[tuple[SourceSpec, type[Any]]] = []
        self.calls: list[tuple[str, SearchRequest]] = []
        self.health: dict[str, str] = {}
        self.recorded: list[tuple[SearchRequest, FederatedResult, int]] = []

    def add(self, source: SourceSpec, search: Search) -> None:
        calls = self.calls

        class Scripted:
            def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
                self.spec = spec

            async def search(self, req: SearchRequest) -> SearchPage:
                calls.append((self.spec.id, req))
                return await search(req)

        self.adapters.append((source, Scripted))

    def service(self, record: Any = None, **settings: Any) -> FederationService:
        config = OfflineSettings(**settings)
        ctx = SourceContext(
            http=cast(Any, None),
            mcp=None,
            settings=SourceSettings(),
            clock=FakeClock(NOW),
            contact_email=None,
        )
        registry = SourceRegistry(
            config,
            lambda spec: ctx,
            has_credential=lambda name: False,
            health=self.health.get,
            modules=[],
            extra_adapters=self.adapters,
        )

        async def remember(req: SearchRequest, result: FederatedResult, latency_ms: int) -> None:
            self.recorded.append((req, result, latency_ms))

        return FederationService(registry, config, KEY, record_search=record or remember)

    def called(self) -> list[str]:
        return sorted(source for source, _ in self.calls)


def states(result: FederatedResult) -> dict[str, str]:
    return {s.source: s.state for s in result.statuses}


async def test_sources_run_concurrently() -> None:
    """@spec SRCH-1: three fake sources of 1 s each finish in about 1 s."""
    harness = Harness()
    for name in ("one", "two", "three"):
        harness.add(spec(name), sleeping(1.0, name))
    service = harness.service()
    started = time.monotonic()
    result = await service.search(SearchRequest(query="q"))
    elapsed = time.monotonic() - started
    assert 0.9 <= elapsed < 1.6
    assert states(result) == {"one": "ok", "two": "ok", "three": "ok"}
    assert len(result.works) == 3
    assert all(s.latency_ms is not None and s.latency_ms >= 900 for s in result.statuses)


async def test_slow_source_times_out() -> None:
    """@spec SRCH-2: a source still running at its own timeout is cancelled as timeout."""
    harness = Harness()
    harness.add(spec("slow", timeout_s=0.5), sleeping(30.0, "slow"))
    harness.add(spec("fast"), page("fast", "10.1/fast"))
    started = time.monotonic()
    result = await harness.service().search(SearchRequest(query="q"))
    assert time.monotonic() - started < 2.0
    assert states(result) == {"slow": "timeout", "fast": "ok"}
    slow = next(s for s in result.statuses if s.source == "slow")
    assert slow.error_code is ErrorCode.UPSTREAM_TIMEOUT
    assert [w.found_in for w in result.works] == [["fast"]]


async def test_source_running_at_deadline_times_out() -> None:
    """@spec SRCH-2: a source still running at the overall deadline is reported as timeout."""
    harness = Harness()
    harness.add(spec("slow", timeout_s=10.0), sleeping(30.0, "slow"))
    harness.add(spec("fast"), page("fast", "10.1/fast"))
    started = time.monotonic()
    result = await harness.service(federation={"deadline_s": 0.5}).search(SearchRequest(query="q"))
    assert time.monotonic() - started < 2.0
    assert states(result) == {"slow": "timeout", "fast": "ok"}
    assert [w.found_in for w in result.works] == [["fast"]]


async def test_failing_source_gets_status() -> None:
    """@spec SRCH-3: failing sources never fail the search and every source gets one status."""
    harness = Harness()
    harness.add(spec("good"), page("good", "10.1/g"))
    harness.add(spec("upstream"), failing(HttpError(ErrorCode.UPSTREAM_ERROR, status=502)))
    harness.add(
        spec("limited"), failing(HttpError(ErrorCode.RATE_LIMITED, status=429, retry_after_ms=2000))
    )
    harness.add(spec("spent"), failing(HttpError(ErrorCode.BUDGET_EXHAUSTED)))
    harness.add(spec("buggy"), failing(RuntimeError("adapter bug")))
    harness.add(spec("off"), page("off", "10.1/off"))
    harness.add(spec("nothing"), page("nothing"))
    result = await harness.service(sources={"off": {"enabled": False}}).search(
        SearchRequest(query="q")
    )
    by_source = {s.source: s for s in result.statuses}
    assert sorted(by_source) == sorted(
        ["good", "upstream", "limited", "spent", "buggy", "off", "nothing"]
    )
    assert len(result.statuses) == len(by_source)
    assert {k: (v.state, v.error_code) for k, v in by_source.items()} == {
        "good": ("ok", None),
        "upstream": ("error", ErrorCode.UPSTREAM_ERROR),
        "limited": ("rate_limited", ErrorCode.RATE_LIMITED),
        "spent": ("budget_exhausted", ErrorCode.BUDGET_EXHAUSTED),
        "buggy": ("error", ErrorCode.INTERNAL),
        "off": ("disabled", None),
        "nothing": ("empty", None),
    }
    assert by_source["limited"].retry_after_ms == 2000
    assert by_source["good"].count == 1
    assert "off" not in harness.called()
    assert [w.found_in for w in result.works] == [["good"]]


async def test_rrf_golden_order() -> None:
    """@spec SRCH-6: works are ranked by reciprocal rank fusion plus the multi-source boost."""
    harness = Harness()
    harness.add(spec("aa"), page("aa", "10.1/w1", "10.1/w2", "10.1/w3"))
    harness.add(spec("bb"), page("bb", "10.1/w3", "10.1/w4"))
    harness.add(spec("cc"), page("cc", "10.1/w4"))
    result = await harness.service().search(SearchRequest(query="q"))
    # w4: 1/62 + 1/61 + 0.1; w3: 1/63 + 1/61 + 0.1; w1: 1/61; w2: 1/62.
    assert [w.ids[0].value for w in result.works] == ["10.1/w4", "10.1/w3", "10.1/w1", "10.1/w2"]
    assert result.works[0].found_in == ["bb", "cc"]

    trimmed = await harness.service().search(SearchRequest(query="q", limit=2))
    assert [w.ids[0].value for w in trimmed.works] == ["10.1/w4", "10.1/w3"]


async def test_per_source_limit_respects_page_size() -> None:
    """Each source is asked for min(per_source_limit, max_page_size) records (5.4 step 2)."""
    harness = Harness()
    harness.add(spec("small", max_page_size=3), page("small"))
    harness.add(spec("large"), page("large"))
    filters = SearchFilters(year_from=2020)
    await harness.service().search(SearchRequest(query="q", filters=filters), per_source_limit=10)
    limits = {source: (req.limit, req.query, req.filters) for source, req in harness.calls}
    assert limits == {"small": (3, "q", filters), "large": (10, "q", filters)}


async def test_combined_cursor_continues_and_reports_empty() -> None:
    """@spec SRCH-7: a continued search resumes each source and reports exhausted ones empty."""
    harness = Harness()
    cursors: dict[str, str | None] = {}

    async def paged(req: SearchRequest) -> SearchPage:
        cursors["paged"] = req.cursor
        if req.cursor is None:
            return SearchPage(records=[rec("paged", "10.1/p1")], next_cursor="page-2")
        return SearchPage(records=[rec("paged", "10.1/p2")], next_cursor=None)

    harness.add(spec("paged"), paged)
    harness.add(spec("single"), page("single", "10.1/s1"))
    service = harness.service()

    first = await service.search(SearchRequest(query="q"))
    assert first.next_cursor is not None
    assert states(first) == {"paged": "ok", "single": "ok"}

    harness.calls.clear()
    second = await service.search(SearchRequest(query="q", cursor=first.next_cursor))
    assert cursors["paged"] == "page-2"
    assert harness.called() == ["paged"]
    assert states(second) == {"paged": "ok", "single": "empty"}
    assert [w.ids[0].value for w in second.works] == ["10.1/p2"]
    assert second.next_cursor is None


async def test_combined_cursor_rejects_tampering() -> None:
    """@spec SRCH-7: a forged or malformed combined cursor is invalid_argument."""
    harness = Harness()
    harness.add(spec("paged"), page("paged", "10.1/p", next_cursor="n"))
    service = harness.service()
    first = await service.search(SearchRequest(query="q"))
    assert first.next_cursor is not None
    payload = decode_cursor(first.next_cursor, KEY)
    assert payload["s"] == {"paged": "n"}
    query = payload["q"]
    harness.calls.clear()
    for cursor in (
        first.next_cursor[:-2] + "AA",
        encode_cursor({"q": query, "s": {"paged": "n"}}, b"other" * 8),
        encode_cursor({"q": query, "s": ["paged"]}, KEY),
        encode_cursor({"q": query, "s": {"paged": 3}}, KEY),
        encode_cursor({"s": {"paged": "n"}}, KEY),
    ):
        with pytest.raises(ToolError) as caught:
            await service.search(SearchRequest(query="q", cursor=cursor))
        assert caught.value.code is ErrorCode.INVALID_ARGUMENT
    assert harness.calls == []


async def test_combined_cursor_retries_failed_sources() -> None:
    """@spec SRCH-7: only exhausted sources are empty; failed and skipped ones run again.

    A source that failed or was skipped on page 1 starts from its first page; one that
    fails on a continued page keeps the cursor it had.
    """
    harness = Harness()
    script: dict[str, list[Search]] = {
        "paged": [
            page("paged", "10.1/p1", next_cursor="p-2"),
            failing(HttpError(ErrorCode.UPSTREAM_ERROR, status=503)),
            page("paged", "10.1/p2", next_cursor="p-3"),
        ],
        "flaky": [
            failing(HttpError(ErrorCode.UPSTREAM_ERROR, status=502)),
            page("flaky", "10.1/f1", next_cursor="f-2"),
            page("flaky", "10.1/f2"),
        ],
        "slow": [sleeping(30.0, "slow"), page("slow", "10.1/s1"), page("slow")],
        "resting": [page("resting", "10.1/r1"), page("resting")],
    }

    def scripted(source: str) -> Search:
        async def search(req: SearchRequest) -> SearchPage:
            return await script[source].pop(0)(req)

        return search

    harness.add(spec("paged"), scripted("paged"))
    harness.add(spec("flaky"), scripted("flaky"))
    harness.add(spec("slow", timeout_s=0.5), scripted("slow"))
    harness.add(spec("resting"), scripted("resting"))
    harness.health["resting"] = "down"
    service = harness.service()

    first = await service.search(SearchRequest(query="q"))
    assert states(first) == {
        "paged": "ok",
        "flaky": "error",
        "slow": "timeout",
        "resting": "skipped_unhealthy",
    }
    assert first.next_cursor is not None

    harness.calls.clear()
    del harness.health["resting"]
    second = await service.search(SearchRequest(query="q", cursor=first.next_cursor))
    cursors = {source: req.cursor for source, req in harness.calls}
    assert cursors == {"paged": "p-2", "flaky": None, "slow": None, "resting": None}
    assert states(second) == {"paged": "error", "flaky": "ok", "slow": "ok", "resting": "ok"}
    assert second.next_cursor is not None

    harness.calls.clear()
    third = await service.search(SearchRequest(query="q", cursor=second.next_cursor))
    cursors = {source: req.cursor for source, req in harness.calls}
    assert cursors == {"paged": "p-2", "flaky": "f-2"}
    assert states(third) == {"paged": "ok", "flaky": "ok", "slow": "empty", "resting": "empty"}
    assert sorted(w.ids[0].value for w in third.works) == ["10.1/f2", "10.1/p2"]


async def test_combined_cursor_bound_to_query() -> None:
    """@spec SRCH-7: a combined cursor is rejected with another query, filters or selection."""
    harness = Harness()
    harness.add(spec("paged"), page("paged", "10.1/p", next_cursor="n"))
    harness.add(spec("other"), page("other", "10.1/o", next_cursor="m"))
    service = harness.service()
    first = await service.search(SearchRequest(query="q"))
    assert first.next_cursor is not None
    harness.calls.clear()
    for req, sources in (
        (SearchRequest(query="other", cursor=first.next_cursor), "auto"),
        (
            SearchRequest(
                query="q", filters=SearchFilters(year_from=2020), cursor=first.next_cursor
            ),
            "auto",
        ),
        (SearchRequest(query="q", cursor=first.next_cursor), ["paged"]),
    ):
        with pytest.raises(ToolError) as caught:
            await service.search(req, sources=sources)
        assert caught.value.code is ErrorCode.INVALID_ARGUMENT
    assert harness.calls == []
    # The page size is not part of the binding.
    again = await service.search(SearchRequest(query="q", limit=5, cursor=first.next_cursor))
    assert states(again) == {"paged": "ok", "other": "ok"}


async def test_auto_skips_unconfigured_disabled_down() -> None:
    """@spec SRCH-8: auto picks the default groups and skips unusable sources with a status."""
    harness = Harness()
    harness.add(spec("ready"), page("ready", "10.1/r"))
    harness.add(spec("preprint", group="preprints"), page("preprint", "10.1/p"))
    harness.add(spec("off"), page("off", "10.1/off"))
    keyed = AuthSpec(
        secrets=("KEYED_API_KEY",),
        required=True,
        placement="header",
        param="x-api-key",
        origins=("https://api.keyed.org",),
        signup_url="https://keyed.org/signup",
    )
    harness.add(spec("keyed", auth=keyed), page("keyed", "10.1/k"))
    harness.add(spec("broken"), page("broken", "10.1/b"))
    harness.add(spec("medline", group="biomed"), page("medline", "10.1/m"))
    harness.add(spec("websrc", group="web", enabled_by_default=False), page("websrc", "10.1/w"))
    harness.health["broken"] = "down"
    service = harness.service(sources={"off": {"enabled": False}, "websrc": {"enabled": True}})

    result = await service.search(SearchRequest(query="q"))
    assert states(result) == {
        "broken": "skipped_unhealthy",
        "keyed": "unconfigured",
        "off": "disabled",
        "preprint": "ok",
        "ready": "ok",
    }
    assert harness.called() == ["preprint", "ready"]

    # A source named explicitly that is down is tried once (SRCH-FR-8).
    harness.calls.clear()
    named = await service.search(SearchRequest(query="q"), sources=["broken", "off"])
    assert states(named) == {"broken": "ok", "off": "disabled"}
    assert harness.called() == ["broken"]

    # Naming a group replaces the default groups.
    harness.calls.clear()
    await service.search(SearchRequest(query="q"), groups=["biomed"])
    assert harness.called() == ["medline"]


async def test_search_recording_port() -> None:
    """The search goes to the injected recording port only while record_searches is on.

    M0-plan-v4 section 2.2, row M0-13: M0 writes no searches row; a failing port never
    fails the search (LLD-search-v2 5.11).
    """
    harness = Harness()
    harness.add(spec("ready"), page("ready", "10.1/r"))
    req = SearchRequest(query="q")
    result = await harness.service().search(req)
    assert len(harness.recorded) == 1
    recorded_req, recorded_result, latency_ms = harness.recorded[0]
    assert recorded_req == req
    assert recorded_result == result
    assert latency_ms >= 0

    await harness.service(federation={"record_searches": False}).search(req)
    assert len(harness.recorded) == 1

    async def broken(req: SearchRequest, result: FederatedResult, latency_ms: int) -> None:
        raise OSError("store unavailable")

    survived = await harness.service(record=broken).search(req)
    assert states(survived) == {"ready": "ok"}


async def test_default_recording_port_does_nothing() -> None:
    """Without an injected port the service records nothing and still searches."""
    harness = Harness()
    harness.add(spec("ready"), page("ready", "10.1/r"))
    config = OfflineSettings()
    ctx = SourceContext(
        http=cast(Any, None),
        mcp=None,
        settings=SourceSettings(),
        clock=FakeClock(NOW),
        contact_email=None,
    )
    registry = SourceRegistry(
        config,
        lambda spec: ctx,
        has_credential=lambda name: False,
        modules=[],
        extra_adapters=harness.adapters,
    )
    result = await FederationService(registry, config, KEY).search(SearchRequest(query="q"))
    assert states(result) == {"ready": "ok"}
