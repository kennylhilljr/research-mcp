"""The source conformance suite: eight checks against every registered adapter.

LLD-sources-v3 5.3. The suite is parametrized over ``SourceRegistry.all()`` (see
``conftest.py``); run one source with ``-k <id>``. Each check builds a fresh harness that
serves one fixture for every request through ``httpx.MockTransport``, with a ``FakeClock``
and a ``FakeSleeper``, so retries and waits are recorded and nothing sleeps for real.

The checks are keyed by capability (M1-plan-v6 2.2): checks 1 and 2 and the search
fixtures belong to ``search``, the ``get_ok`` mapping check to ``get``, and checks 3 to 6
call the first method the source declares, so a source without ``search`` is never
searched.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier, parse_any
from research_mcp.core.models import JsonValue, SearchPage, SearchRequest, WorkRecord
from research_mcp.platform.http import MAX_ATTEMPTS, RETRIED_5XX
from research_mcp.sources.base import Capability, SourceAdapter, SourceSpec, translate_errors
from research_mcp.sources.registry import RegisteredSource, SourceRegistry
from research_mcp.testing.adapters import FAKE_SPEC, FIXTURES, FakeAdapter

SEARCH_FIXTURES = ("search_ok", "search_empty")
FIXTURE_NAMES = (
    *SEARCH_FIXTURES,
    "get_ok",
    "err_429",
    "err_5xx",
    "malformed",
    "oversize.marker",
)
# An identifier per scheme for the calls that take one; the mock upstream ignores it.
CONFORMANCE_IDS = {"doi": "10.5555/conformance.1", "url": "https://conformance.invalid/1"}

HarnessFor = Callable[..., Any]
Call = Callable[[SourceAdapter], Awaitable[object]]


def request_for(source: RegisteredSource) -> SearchRequest:
    return SearchRequest(query="research", limit=min(10, source.spec.max_page_size))


def ident_for(spec: SourceSpec) -> Identifier:
    scheme = next((s for s in sorted(spec.id_schemes) if s in CONFORMANCE_IDS), None)
    if scheme is None:
        scheme = min(spec.id_schemes, default="doi")
        return Identifier(scheme, "conformance-1")
    return Identifier(scheme, CONFORMANCE_IDS[scheme])


def required_fixtures(spec: SourceSpec) -> tuple[str, ...]:
    """The seven fixtures; the two search fixtures only for a source that can search."""
    if Capability.SEARCH in spec.capabilities:
        return FIXTURE_NAMES
    return tuple(name for name in FIXTURE_NAMES if name not in SEARCH_FIXTURES)


def first_call(source: RegisteredSource) -> Call:
    """The call checks 3 to 6 make: the first method the source declares, in this order."""
    spec = source.spec
    ident = ident_for(spec)
    calls: list[tuple[Capability, Call]] = [
        (Capability.SEARCH, lambda adapter: adapter.search(request_for(source))),
        (Capability.GET, lambda adapter: adapter.get(ident)),
        (Capability.CITATIONS, lambda adapter: adapter.citations(ident, "citing", None, 10)),
        (Capability.AUTHORS, lambda adapter: adapter.search_authors("research", None, 10)),
        (Capability.UPDATES, lambda adapter: adapter.updates(ident)),
    ]
    for capability, call in calls:
        if capability in spec.capabilities:
            return call
    pytest.fail(f"{spec.id} declares no capability the suite can call")


def retry_after_s(headers: dict[str, str]) -> float:
    value = next(v for k, v in headers.items() if k.lower() == "retry-after")
    return float(value)


def check_record(record: WorkRecord, source: RegisteredSource, harness: Any) -> None:
    assert record.ids, "a record has no identifier"
    for ident in record.ids:
        again = parse_any(f"{ident.scheme}:{ident.value}")
        assert (again.scheme, again.value) == (ident.scheme, ident.value)
    assert record.provenance.source == source.spec.id
    assert record.provenance.upstream_id
    assert record.provenance.adapter_version
    assert record.provenance.retrieved_at == harness.clock.now()


async def check_search_ok(source: RegisteredSource, harness_for: HarnessFor, fx: Any) -> Any:
    """1. ``search_ok`` maps to records with normalized identifiers and provenance."""
    harness = harness_for(source)
    harness.serve(fx["search_ok"])
    page = await harness.adapter.search(request_for(source))
    assert isinstance(page, SearchPage)
    assert page.records, "search_ok gave no records"
    for record in page.records:
        check_record(record, source, harness)
    return harness


async def check_search_empty(source: RegisteredSource, harness_for: HarnessFor, fx: Any) -> Any:
    """2. ``search_empty`` is an empty page, not an error."""
    harness = harness_for(source)
    harness.serve(fx["search_empty"])
    page = await harness.adapter.search(request_for(source))
    assert page.records == []
    return harness


async def check_get_ok(source: RegisteredSource, harness_for: HarnessFor, fx: Any) -> Any:
    """For ``get``: ``get_ok`` maps to one record with normalized identifiers and provenance."""
    harness = harness_for(source)
    harness.serve(fx["get_ok"])
    record = await harness.adapter.get(ident_for(source.spec))
    assert isinstance(record, WorkRecord), "get_ok gave no record"
    check_record(record, source, harness)
    return harness


async def check_rate_limited(
    source: RegisteredSource, harness_for: HarnessFor, fx: Any, call: Call
) -> Any:
    """3. A 429 raises ``rate_limited`` with ``retry_after_ms``; the sleeper records the wait."""
    harness = harness_for(source)
    harness.serve_error(fx["err_429"])
    status, headers, _ = harness.error_parts(fx["err_429"])
    assert status == 429
    with pytest.raises(HttpError) as caught:
        await call(harness.adapter)
    assert caught.value.code is ErrorCode.RATE_LIMITED
    assert caught.value.retry_after_ms is not None
    assert retry_after_s(headers) in harness.sleeper.sleeps
    return harness


async def check_upstream_error(
    source: RegisteredSource, harness_for: HarnessFor, fx: Any, call: Call
) -> Any:
    """4. A 5xx raises ``upstream_error`` once the retry budget is spent."""
    harness = harness_for(source)
    harness.serve_error(fx["err_5xx"])
    status, _, _ = harness.error_parts(fx["err_5xx"])
    assert status in RETRIED_5XX
    with pytest.raises(HttpError) as caught:
        await call(harness.adapter)
    assert caught.value.code is ErrorCode.UPSTREAM_ERROR
    assert len(harness.requests) == MAX_ATTEMPTS
    return harness


async def check_malformed(
    source: RegisteredSource, harness_for: HarnessFor, fx: Any, call: Call
) -> Any:
    """5. A malformed body raises ``upstream_error``, never ``KeyError``, ``TypeError`` or
    ``ValueError``."""
    harness = harness_for(source)
    harness.serve(fx["malformed"])
    with pytest.raises(HttpError) as caught:
        await call(harness.adapter)
    assert caught.value.code is ErrorCode.UPSTREAM_ERROR
    return harness


async def check_oversize(
    source: RegisteredSource, harness_for: HarnessFor, fx: Any, stream_cls: Any, call: Call
) -> Any:
    """6. An oversize body raises ``too_large`` before the whole body is read."""
    harness = harness_for(source)
    stream = stream_cls(total=source.spec.max_bytes * 4 + 65_536)
    harness.serve_stream(stream, fx["get_ok"].content_type)
    with pytest.raises(HttpError) as caught:
        await call(harness.adapter)
    assert caught.value.code is ErrorCode.TOO_LARGE
    assert stream.sent < stream.total
    return harness


async def check_probe(source: RegisteredSource, harness_for: HarnessFor, fx: Any) -> list[Any]:
    """8. ``probe`` is ok and shape_ok against ``get_ok``, not shape_ok against ``malformed``."""
    good = harness_for(source)
    good.serve(fx["get_ok"])
    result = await good.adapter.probe()
    assert (result.ok, result.shape_ok) == (True, True)
    bad = harness_for(source)
    bad.serve(fx["malformed"])
    result = await bad.adapter.probe()
    assert result.shape_ok is False
    return [good, bad]


def check_classifier_is_tested(source: RegisteredSource) -> None:
    """An adapter that declares an ``error_classifier`` has a test file that exercises it."""
    classifier = source.spec.error_classifier
    if classifier is None:
        return
    folder = source.spec.instance_of or source.spec.id
    test_file = Path(__file__).parent / folder / f"test_{folder}.py"
    assert test_file.is_file(), f"{test_file} is missing"
    assert classifier.__name__ in test_file.read_text(encoding="utf-8")


async def run_conformance(
    source: RegisteredSource, harness_for: HarnessFor, fixtures_of: Any, stream_cls: Any
) -> None:
    fx = fixtures_of(source)
    missing = [name for name in required_fixtures(source.spec) if name not in fx]
    assert missing == [], f"{source.spec.id} lacks fixtures {missing}"
    capabilities = source.spec.capabilities
    call = first_call(source)
    harnesses = []
    if Capability.SEARCH in capabilities:
        harnesses.append(await check_search_ok(source, harness_for, fx))
        harnesses.append(await check_search_empty(source, harness_for, fx))
    if Capability.GET in capabilities:
        harnesses.append(await check_get_ok(source, harness_for, fx))
    harnesses += [
        await check_rate_limited(source, harness_for, fx, call),
        await check_upstream_error(source, harness_for, fx, call),
        await check_malformed(source, harness_for, fx, call),
        await check_oversize(source, harness_for, fx, stream_cls, call),
        *await check_probe(source, harness_for, fx),
    ]
    # 7. Every request goes to a host in spec.hosts.
    hosts = {request.url.host for harness in harnesses for request in harness.requests}
    assert hosts, "no check reached the upstream"
    assert hosts <= source.spec.hosts
    check_classifier_is_tested(source)


async def test_conformance_passes(
    registered_source: RegisteredSource,
    harness_for: HarnessFor,
    fixtures_of: Any,
    counting_stream: Any,
) -> None:
    """@spec SRC-6: Each registered adapter passes the eight checks with its seven fixtures."""
    await run_conformance(registered_source, harness_for, fixtures_of, counting_stream)


async def test_conformance_passes_for_fake_adapter(
    conformance: SourceRegistry,
    harness_for: HarnessFor,
    fixtures_of: Any,
    counting_stream: Any,
) -> None:
    """@spec SRC-6: The suite runs against the fake adapter from ``research_mcp.testing``."""
    fake = conformance.get(FAKE_SPEC.id)
    assert fake is not None and fake.adapter_cls is FakeAdapter
    await run_conformance(fake, harness_for, fixtures_of, counting_stream)


class GetOnlyAdapter(FakeAdapter):
    """A source that declares ``get`` but not ``search``, like ``docs_site`` in M1."""

    FIXTURES = {name: FIXTURES[name] for name in FIXTURES if name not in SEARCH_FIXTURES}
    searched = 0

    async def search(self, req: SearchRequest) -> SearchPage:
        type(self).searched += 1
        raise AssertionError("a source without search was searched")


async def test_conformance_runs_only_the_checks_of_declared_capabilities(
    conformance: SourceRegistry,
    harness_for: HarnessFor,
    fixtures_of: Any,
    counting_stream: Any,
) -> None:
    """@spec SRC-6: A source without ``search`` passes on ``get`` and is never searched."""
    fake = conformance.get(FAKE_SPEC.id)
    assert fake is not None
    spec = dataclasses.replace(FAKE_SPEC, id="fake_get", capabilities=frozenset({Capability.GET}))
    source = RegisteredSource(spec, GetOnlyAdapter, fake.settings, None)
    assert "search_ok" not in required_fixtures(spec)
    assert "get_ok" in required_fixtures(spec)
    await run_conformance(source, harness_for, fixtures_of, counting_stream)
    assert GetOnlyAdapter.searched == 0
    # The same adapter declared with search is searched, so the keying is what spared it.
    searching = RegisteredSource(FAKE_SPEC, GetOnlyAdapter, fake.settings, None)
    with pytest.raises(AssertionError):
        await run_conformance(searching, harness_for, fixtures_of, counting_stream)


class RecordingMcp:
    """A stand-in ``McpUpstreamPort`` built over the harness's HTTP client."""

    def __init__(self, http: Any) -> None:
        self.http = http

    async def call_tool(self, server: str, tool: str, arguments: Any, *, source: str) -> JsonValue:
        return None


async def test_harness_builds_the_mcp_port_over_its_http_client(
    conformance: SourceRegistry, harness_for: HarnessFor
) -> None:
    """The harness passes its ``HttpClient`` to an ``mcp`` factory; without one ``mcp`` is None."""
    fake = conformance.get(FAKE_SPEC.id)
    assert fake is not None
    plain = harness_for(fake)
    assert plain.adapter.ctx.mcp is None
    built: list[Any] = []

    def factory(http: Any) -> RecordingMcp:
        built.append(RecordingMcp(http))
        return built[-1]

    harness = harness_for(fake, mcp=factory)
    assert harness.adapter.ctx.mcp is built[0]
    assert built[0].http is harness.http


class LeakyAdapter(FakeAdapter):
    """Maps records without ``translate_errors``, so a malformed body leaks ``KeyError``."""

    async def search(self, req: SearchRequest) -> SearchPage:
        data: Any = await self.ctx.http.get_json(self.url("/search"), source=self.spec.id)
        return SearchPage(records=[self.record(item) for item in data["results"]])


class SwallowingAdapter(FakeAdapter):
    """Turns every upstream error into an empty page, hiding 429s and 5xx."""

    async def search(self, req: SearchRequest) -> SearchPage:
        try:
            return await super().search(req)
        except HttpError:
            return SearchPage(records=[])


class OffHostAdapter(FakeAdapter):
    """Calls a host its spec does not list."""

    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        await self.ctx.http.get_json("https://elsewhere.example.net/search", source=self.spec.id)
        return SearchPage(records=[])


@pytest.mark.parametrize("broken", [LeakyAdapter, SwallowingAdapter, OffHostAdapter])
async def test_conformance_fails_for_a_broken_adapter(
    broken: type[FakeAdapter],
    conformance: SourceRegistry,
    harness_for: HarnessFor,
    fixtures_of: Any,
    counting_stream: Any,
) -> None:
    """@spec SRC-6: An adapter that leaks parse errors, hides errors or leaves its hosts fails."""
    fake = conformance.get(FAKE_SPEC.id)
    assert fake is not None
    source = RegisteredSource(
        spec=fake.spec, adapter_cls=broken, settings=fake.settings, instance=None
    )
    with pytest.raises((AssertionError, KeyError, HttpError, pytest.fail.Exception)):
        await run_conformance(source, harness_for, fixtures_of, counting_stream)
