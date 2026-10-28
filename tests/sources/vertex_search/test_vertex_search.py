"""Tests for the Vertex AI Search adapter (LLD-sources-v3 4, 5.7; LLD-platform-v3 4.2).

The generic conformance checks run for the unconfigured kind entry in
``tests/sources/test_conformance.py::test_conformance_passes[vertex_search]``. This file
runs the same checks for a configured ``vertex_<name>`` instance, and covers what SRC-32
adds: the Google sign-in refreshed off the event loop by ``GoogleAdcProvider`` with a fake
loader, the token sent only to ``discoveryengine.googleapis.com`` with
``X-Goog-User-Project``, and the refresh recorded as a call record. Every token request
goes to an ``httpx.MockTransport``; no real sign-in is read.
"""

from __future__ import annotations

import importlib.util
import json
import threading
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import anyio
import httpx
import pytest

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.models import CallRecord, SearchRequest
from research_mcp.platform.google_adc import GoogleAdcProvider
from research_mcp.platform.http import HttpClient
from research_mcp.platform.secrets import SecretCache, SecretRef
from research_mcp.settings import Settings
from research_mcp.sources import vertex_search
from research_mcp.sources.base import SourceContext
from research_mcp.sources.registry import RegisteredSource, SourceRegistry
from research_mcp.testing.clock import FakeClock, FakeSleeper

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
FIXTURES = Path(__file__).parent / "fixtures"
MODULE = "research_mcp.sources.vertex_search"
INSTANCE = "vertex_docs"
ENGINE = {
    "instance_of": "vertex_search",
    "project": "owner-project",
    "location": "global",
    "engine_id": "docs-search",
    "title": "Owner docs engine",
}
ENGINE_PATH = (
    "/v1/projects/owner-project/locations/global/collections/default_collection/engines/docs-search"
)
# Generated for these tests; not a real token.
FRESH = "ya29.test-vertex-token-5c81d2"


class OfflineSettings(Settings):
    """Settings from keyword arguments only: no config file, no environment."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


class Sink:
    def __init__(self) -> None:
        self.records: list[CallRecord] = []

    def record(self, call: CallRecord) -> None:
        self.records.append(call)


class FakeCredentials:
    """A sign-in whose refresh asks the token endpoint through the given request."""

    def __init__(self) -> None:
        self.token: str | None = None
        self.expiry: datetime | None = None
        self.account = "owner@example.com"
        self.refresh_threads: list[int] = []

    def refresh(self, request: Any) -> None:
        self.refresh_threads.append(threading.get_ident())
        reply = request(
            url="https://oauth2.googleapis.com/token",
            method="POST",
            body=b"grant_type=refresh_token",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        self.token = json.loads(reply.data)["access_token"]
        self.expiry = (NOW + timedelta(hours=1)).replace(tzinfo=None)


class Body(httpx.AsyncByteStream):
    """A body that arrives unread, as from a network transport."""

    def __init__(self, content: bytes) -> None:
        self.content = content

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.content

    async def aclose(self) -> None:
        return None


def fixture(name: str) -> bytes:
    return (FIXTURES / f"{name}.json").read_bytes()


def settings(**sources: Any) -> OfflineSettings:
    return OfflineSettings(sources=sources)


def registry(cfg: OfflineSettings, clock: FakeClock | None = None) -> SourceRegistry:
    def no_context(spec: Any) -> Any:
        raise AssertionError("these tests build adapters themselves")

    return SourceRegistry(
        cfg,
        no_context,
        has_credential=lambda name: True,
        has_extra=lambda extra: True,
        clock=clock or FakeClock(NOW),
        modules=[MODULE],
    )


def configured(**overrides: Any) -> RegisteredSource:
    source = registry(settings(**{INSTANCE: {**ENGINE, "enabled": True, **overrides}})).get(
        INSTANCE
    )
    assert source is not None
    return source


def load_conformance() -> ModuleType:
    """``tests/sources/test_conformance.py`` as a plain module, so its tests are not collected."""
    path = Path(__file__).parent.parent / "test_conformance.py"
    spec = importlib.util.spec_from_file_location("vertex_conformance_checks", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_conformance_passes_for_a_configured_instance(
    harness_for: Any, fixtures_of: Any, counting_stream: Any
) -> None:
    """@spec SRC-20: A configured ``vertex_<name>`` instance passes the conformance suite."""
    source = configured()
    assert source.spec.id == INSTANCE
    assert source.spec.instance_of == "vertex_search"
    assert source.spec.title == "Owner docs engine"
    assert source.spec.hosts == frozenset({"discoveryengine.googleapis.com"})
    assert set(fixtures_of(source)) == {
        "search_ok",
        "search_empty",
        "get_ok",
        "err_429",
        "err_5xx",
        "malformed",
        "oversize.marker",
    }
    await load_conformance().run_conformance(source, harness_for, fixtures_of, counting_stream)


def test_spec_is_an_opt_in_metered_web_source_signed_in_with_google() -> None:
    """@spec SRC-32: The spec scopes the Google sign-in to the Vertex origin, as a bearer."""
    spec = vertex_search.SPEC
    assert spec.id == "vertex_search"
    assert spec.group == "web"
    assert spec.enabled_by_default is False
    assert spec.extras == frozenset({"gcp"})
    assert spec.hosts == frozenset({"discoveryengine.googleapis.com"})
    assert spec.auth is not None
    assert spec.auth.secrets == ("GOOGLE_SIGNIN",)
    assert spec.auth.placement == "bearer"
    assert spec.auth.origins == ("https://discoveryengine.googleapis.com",)
    assert spec.auth.validation == "probe"
    # The engine-metadata probe costs no query, every 6 h (LLD-sources-v3 5.7).
    assert (spec.probe.cadence_s, spec.probe.cost) == (6 * 3600, "free")


async def test_refresh_off_loop_token_only_to_discoveryengine_with_project_header_and_call_record() -> (  # noqa: E501
    None
):
    """@spec SRC-32: The sign-in refreshes off the event loop through ``GoogleAdcProvider``,
    its token goes only to ``discoveryengine.googleapis.com`` with ``X-Goog-User-Project``,
    and the refresh is recorded as a ``google_signin`` call record."""
    clock = FakeClock(NOW)
    sink = Sink()
    creds = FakeCredentials()
    token_requests: list[httpx.Request] = []

    def token_endpoint(request: httpx.Request) -> httpx.Response:
        token_requests.append(request)
        return httpx.Response(200, json={"access_token": FRESH, "expires_in": 3600})

    provider = GoogleAdcProvider(
        lambda: (creds, "owner-project"),
        sink,
        clock,
        transport=httpx.MockTransport(token_endpoint),
    )
    cache = SecretCache(
        provider,
        {"GOOGLE_SIGNIN": SecretRef.parse("gcloud_adc:GOOGLE_SIGNIN")},
        {INSTANCE: "GOOGLE_SIGNIN"},
    )

    loop_thread = threading.get_ident()
    await anyio.to_thread.run_sync(cache.load)
    assert creds.refresh_threads, "the sign-in was never refreshed"
    assert loop_thread not in creds.refresh_threads

    api_requests: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        api_requests.append(request)
        body = fixture("get_ok" if request.method == "GET" else "search_ok")
        return httpx.Response(200, headers={"content-type": "application/json"}, stream=Body(body))

    reg = registry(settings(**{INSTANCE: {**ENGINE, "enabled": True}}), clock)
    source = reg.get(INSTANCE)
    assert source is not None
    http = HttpClient(
        reg, cache, sink, clock, FakeSleeper(clock), None, transport=httpx.MockTransport(upstream)
    )
    try:
        adapter = source.adapter_cls(
            source.spec,
            SourceContext(
                http=http, mcp=None, settings=source.settings, clock=clock, contact_email=None
            ),
        )
        page = await adapter.search(SearchRequest(query="single sign on", limit=5))
        probe = await adapter.probe()
        assert page.records and probe.shape_ok

        # The token leaves only for the Vertex origin, with the instance's project.
        assert [r.url.host for r in api_requests] == ["discoveryengine.googleapis.com"] * 2
        for request in api_requests:
            assert request.url.scheme == "https"
            assert request.url.path.startswith(ENGINE_PATH)
            assert request.headers["authorization"] == f"Bearer {FRESH}"
            assert request.headers["x-goog-user-project"] == "owner-project"
        for request in token_requests:
            assert request.url.host == "oauth2.googleapis.com"
            assert FRESH not in str(request.url) and FRESH not in str(request.headers)

        # Any other host is refused before a request is sent, so the token cannot follow.
        for elsewhere in ("https://oauth2.googleapis.com/token", "https://www.googleapis.com/x"):
            with pytest.raises(HttpError) as caught:
                await http.get_json(elsewhere, source=INSTANCE)
            assert caught.value.code is ErrorCode.BLOCKED_BY_POLICY
        assert len(api_requests) == 2
    finally:
        await http.aclose()

    refreshes = [r for r in sink.records if r.source == "google_signin"]
    assert len(refreshes) == 1
    assert (refreshes[0].op, refreshes[0].status) == ("refresh", 200)
    assert len(token_requests) == 1
    assert {r.source for r in sink.records} >= {"google_signin", INSTANCE}


async def test_search_posts_query_page_size_and_token_to_the_serving_config(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-32: ``search`` POSTs ``query``, ``pageSize`` and ``pageToken`` to the
    engine's default serving config and maps results to ``webpage`` records."""
    source = configured()
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["search_ok"])
    page = await harness.adapter.search(
        SearchRequest(query="single sign on", limit=500, cursor="recorded-page-token")
    )
    request = harness.requests[0]
    assert request.method == "POST"
    assert request.url.path == f"{ENGINE_PATH}/servingConfigs/default_search:search"
    assert json.loads(request.content) == {
        "query": "single sign on",
        "pageSize": source.spec.max_page_size,
        "pageToken": "recorded-page-token",
    }
    assert page.next_cursor == "recorded-next-page-token"
    assert page.total == 3
    first = page.records[0]
    assert first.work_type == "webpage"
    assert first.title == "Server Administration Guide"
    assert [(i.scheme, i.value) for i in first.ids] == [
        ("url", "https://www.keycloak.org/docs/latest/server_admin/index.html")
    ]
    assert first.abstract is not None and first.abstract.startswith("Keycloak is a single")
    assert first.provenance.upstream_id == "8b1d1c6f0a2e4b7d"
    # A result without snippets has no abstract.
    assert page.records[2].abstract is None


async def test_first_page_sends_no_page_token(harness_for: Any, fixtures_of: Any) -> None:
    """@spec SRC-32: Without a cursor the body holds only ``query`` and ``pageSize``."""
    source = configured()
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["search_empty"])
    page = await harness.adapter.search(SearchRequest(query="nothing", limit=3))
    assert json.loads(harness.requests[0].content) == {"query": "nothing", "pageSize": 3}
    assert (page.records, page.next_cursor) == ([], None)


async def test_site_set_filters_results_by_host_after_the_call(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-31: Vertex sends the plain query and keeps only results whose host is in
    the site set, exactly or as a subdomain, never by substring."""
    source = configured()
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["search_ok"])
    page = await harness.adapter.search(
        SearchRequest(
            query="single sign on",
            site_set="v1_docs",
            site_domains=("keycloak.org", "ietf.org.example", "ory.s"),
        )
    )
    assert json.loads(harness.requests[0].content)["query"] == "single sign on"
    assert [r.title for r in page.records] == ["Server Administration Guide"]
    assert page.total is None

    harness = harness_for(source)
    harness.serve(fixtures_of(source)["search_ok"])
    page = await harness.adapter.search(
        SearchRequest(query="x", site_set="other", site_domains=("example.org",))
    )
    assert page.records == []


async def test_probe_reads_engine_metadata_without_a_query(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-32: ``probe`` GETs the engine resource, which costs no search query."""
    source = configured()
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["get_ok"])
    result = await harness.adapter.probe()
    assert (result.ok, result.shape_ok) == (True, True)
    request = harness.requests[0]
    assert (request.method, request.url.path) == ("GET", ENGINE_PATH)


@pytest.mark.parametrize(
    ("name", "fields"),
    [
        ("vertex_docs", {"project": "owner-project"}),  # no engine_id
        ("vertex_docs", {**ENGINE, "project": "Owner Project"}),
        ("vertex_docs", {**ENGINE, "engine_id": "../other"}),
        ("vertex_docs", {**ENGINE, "token": "not-a-setting"}),
        ("docs_engine", ENGINE),  # instances are named vertex_<name>
    ],
)
def test_invalid_instance_settings_leave_only_that_instance_unconfigured(
    name: str, fields: dict[str, Any]
) -> None:
    """@spec SRC-32: Project, location and engine id are validated settings; a bad entry is
    listed ``unconfigured`` and the other instances still build."""
    entry = {"instance_of": "vertex_search", **fields, "enabled": True}
    reg = registry(settings(**{name: entry, "vertex_good": {**ENGINE, "enabled": True}}))
    bad = reg.view(name)[0]
    assert bad.state == "unconfigured"
    good = reg.view("vertex_good")[0]
    assert good.state == "ok"
