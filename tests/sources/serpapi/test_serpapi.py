"""Tests for the SerpAPI adapter (LLD-sources-v3 5.7, 5.8; SPEC-v5 4, 9).

The generic conformance checks run in
``tests/sources/test_conformance.py::test_conformance_passes[serpapi]``. This file covers
what SRC-33 adds beyond conformance: the key is attached only as the ``api_key`` query
parameter and never rides along in a call record or an error, and SRC-31's single,
truncating site-set query.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.models import SearchRequest
from research_mcp.settings import Settings
from research_mcp.sources import serpapi
from research_mcp.sources.registry import RegisteredSource, SourceRegistry
from research_mcp.testing.clock import FakeClock

MODULE = "research_mcp.sources.serpapi"
NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
FAKE_KEY = "fake-serpapi_api_key"


class OfflineSettings(Settings):
    """Settings from keyword arguments only: no config file, no environment."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


def registry(**sources: Any) -> SourceRegistry:
    def no_context(spec: Any) -> Any:
        raise AssertionError("these tests build adapters through the harness")

    return SourceRegistry(
        OfflineSettings(sources=sources),
        no_context,
        has_credential=lambda name: True,
        has_extra=lambda extra: True,
        clock=FakeClock(NOW),
        modules=[MODULE],
    )


def configured() -> RegisteredSource:
    source = registry(serpapi={"enabled": True}).get("serpapi")
    assert source is not None
    return source


async def test_conformance_passes(harness_for: Any, fixtures_of: Any, counting_stream: Any) -> None:
    """@spec SRC-20: ``serpapi`` passes the eight-check conformance suite."""
    from tests.sources.test_conformance import run_conformance

    await run_conformance(configured(), harness_for, fixtures_of, counting_stream)


def test_spec_sends_the_key_only_as_a_query_parameter() -> None:
    """@spec SRC-33: The key is accepted only as the ``api_key`` query parameter."""
    spec = serpapi.SPEC
    assert spec.id == "serpapi"
    assert spec.group == "web"
    assert spec.enabled_by_default is False
    assert spec.hosts == frozenset({"serpapi.com"})
    assert spec.auth is not None
    assert spec.auth.secrets == ("SERPAPI_API_KEY",)
    assert spec.auth.placement == "query"
    assert spec.auth.param == "api_key"
    assert spec.auth.origins == ("https://serpapi.com",)
    assert spec.auth.validation == "probe"
    # account.json is free, so the probe spends no search (5.7).
    assert (spec.probe.cadence_s, spec.probe.cost) == (6 * 3600, "free")


async def test_search_sends_engine_q_and_num_with_the_key_in_the_query(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-33: ``search`` sends ``engine``, ``q`` and ``num``; the key is attached to
    the real request's query string and nowhere else."""
    source = configured()
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["search_ok"])
    page = await harness.adapter.search(SearchRequest(query="single sign on", limit=5))
    request = harness.requests[0]
    assert request.method == "GET"
    assert request.url.params["engine"] == "google"
    assert request.url.params["q"] == "single sign on"
    assert request.url.params["num"] == "5"
    assert request.url.params["api_key"] == FAKE_KEY
    first = page.records[0]
    assert first.work_type == "webpage"
    assert first.title == "Server Administration Guide"
    assert [(i.scheme, i.value) for i in first.ids] == [
        ("url", "https://www.keycloak.org/docs/latest/server_admin/index.html")
    ]
    assert first.abstract is not None and first.abstract.startswith("Keycloak is a single")
    assert page.records[2].abstract is None


async def test_key_never_appears_in_a_call_record_or_a_raised_error(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-33: The key rides along in the real request only; call records and a
    raised ``HttpError`` never carry it."""
    source = configured()
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["search_ok"])
    await harness.adapter.search(SearchRequest(query="single sign on", limit=5))
    assert harness.sink.records, "no call record was made"
    for record in harness.sink.records:
        assert FAKE_KEY not in repr(record)

    harness = harness_for(source)
    harness.serve_error(fixtures_of(source)["err_429"])
    try:
        await harness.adapter.search(SearchRequest(query="single sign on", limit=5))
    except HttpError as exc:
        assert exc.code is ErrorCode.RATE_LIMITED
        assert FAKE_KEY not in str(exc) and FAKE_KEY not in repr(exc)
        assert exc.detail is None or FAKE_KEY not in exc.detail
    else:
        raise AssertionError("expected HttpError")
    for record in harness.sink.records:
        assert FAKE_KEY not in repr(record)


async def test_site_set_sends_one_query_and_truncates_dropped_domains(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-31: A long site set still yields one query; domains that do not fit are
    dropped and ``truncated`` is set."""
    source = configured()
    harness = harness_for(source)
    domains = tuple(f"d{i}.example" for i in range(100))
    harness.serve(fixtures_of(source)["search_ok"])
    page = await harness.adapter.search(
        SearchRequest(query="docs", site_set="big", site_domains=domains)
    )
    assert len(harness.requests) == 1
    query = harness.requests[0].url.params["q"]
    assert "site:" in query and len(query) <= 380
    assert page.truncated is True

    harness = harness_for(source)
    harness.serve(fixtures_of(source)["search_ok"])
    page = await harness.adapter.search(
        SearchRequest(query="docs", site_set="small", site_domains=("keycloak.org",))
    )
    assert "site:keycloak.org" in harness.requests[0].url.params["q"]
    assert page.truncated is False


async def test_probe_reads_searches_left_without_spending_one(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-33: ``probe`` GETs ``account.json`` and reports the searches left."""
    source = configured()
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["get_ok"])
    result = await harness.adapter.probe()
    assert (result.ok, result.shape_ok) == (True, True)
    assert result.quota_remaining == "97"
    request = harness.requests[0]
    assert "search.json" not in request.url.path

    harness = harness_for(source)
    harness.serve(fixtures_of(source)["malformed"])
    result = await harness.adapter.probe()
    assert (result.ok, result.shape_ok) == (True, False)
