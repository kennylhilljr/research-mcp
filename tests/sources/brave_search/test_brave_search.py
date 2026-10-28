"""Tests for the Brave Search adapter (LLD-sources-v3 5.7, 5.8; SPEC-v5 4, 9).

The generic conformance checks run in
``tests/sources/test_conformance.py::test_conformance_passes[brave_search]``. This file
covers what SRC-33 adds beyond conformance: the ``X-Subscription-Token`` header, and
SRC-31: batching a ``site_set`` into separate calls that count against the cap and
merging their results with ``truncated`` set when domains are dropped.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from research_mcp.core.models import SearchRequest
from research_mcp.settings import Settings
from research_mcp.sources import brave_search
from research_mcp.sources.registry import RegisteredSource, SourceRegistry
from research_mcp.testing.clock import FakeClock

MODULE = "research_mcp.sources.brave_search"
NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)


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
    source = registry(brave_search={"enabled": True}).get("brave_search")
    assert source is not None
    return source


async def test_conformance_passes(harness_for: Any, fixtures_of: Any, counting_stream: Any) -> None:
    """@spec SRC-20: ``brave_search`` passes the eight-check conformance suite."""
    from tests.sources.test_conformance import run_conformance

    await run_conformance(configured(), harness_for, fixtures_of, counting_stream)


def test_spec_is_an_opt_in_metered_web_source() -> None:
    """@spec SRC-33: The spec scopes the subscription token to the Brave origin."""
    spec = brave_search.SPEC
    assert spec.id == "brave_search"
    assert spec.group == "web"
    assert spec.enabled_by_default is False
    assert spec.hosts == frozenset({"api.search.brave.com"})
    assert spec.auth is not None
    assert spec.auth.secrets == ("BRAVE_SEARCH_API_KEY",)
    assert spec.auth.placement == "header"
    assert spec.auth.param == "X-Subscription-Token"
    assert spec.auth.origins == ("https://api.search.brave.com",)
    assert spec.auth.validation == "probe"
    # No free probe exists, so the probe spends one query, at most once a day (5.7).
    assert (spec.probe.cadence_s, spec.probe.cost) == (24 * 3600, "metered")


async def test_search_sends_the_subscription_token_header_and_query(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-33: ``search`` sends ``q`` and ``count`` and attaches the token header."""
    source = configured()
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["search_ok"])
    page = await harness.adapter.search(SearchRequest(query="single sign on", limit=5))
    request = harness.requests[0]
    assert request.method == "GET"
    assert request.url.params["q"] == "single sign on"
    assert request.url.params["count"] == "5"
    assert request.headers["x-subscription-token"] == "fake-brave_search_api_key"
    first = page.records[0]
    assert first.work_type == "webpage"
    assert first.title == "Server Administration Guide"
    assert [(i.scheme, i.value) for i in first.ids] == [
        ("url", "https://www.keycloak.org/docs/latest/server_admin/index.html")
    ]
    assert first.abstract is not None and first.abstract.startswith("Keycloak is a single")
    # A result without a description has no abstract.
    assert page.records[2].abstract is None


async def test_site_set_splits_into_batched_calls_and_merges_results(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-31: A long site set is split into several calls, each counted separately,
    and the results are merged with ``truncated`` set when domains are dropped."""
    source = configured()
    harness = harness_for(source)
    fx = fixtures_of(source)
    domains = tuple(f"d{i}.example" for i in range(100))  # forces truncation past 3 batches
    harness.serve(fx["search_ok"])
    page = await harness.adapter.search(
        SearchRequest(query="docs", site_set="big", site_domains=domains)
    )
    assert 1 < len(harness.requests) <= 3
    for request in harness.requests:
        assert "site:" in request.url.params["q"]
        assert len(request.url.params["q"]) <= 380
    # Every batch's three results were merged (the mock serves the same fixture each call).
    assert len(page.records) == 3 * len(harness.requests)
    assert page.truncated is True


async def test_no_site_set_sends_the_plain_query_and_does_not_truncate(
    harness_for: Any, fixtures_of: Any
) -> None:
    """Without a site set, one call is made and ``truncated`` stays false."""
    source = configured()
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["search_empty"])
    page = await harness.adapter.search(SearchRequest(query="nothing", limit=3))
    assert len(harness.requests) == 1
    assert harness.requests[0].url.params["q"] == "nothing"
    assert (page.records, page.truncated) == ([], False)


async def test_probe_spends_one_query_and_checks_the_results_shape(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-33: ``probe`` calls the search endpoint and checks the results shape."""
    source = configured()
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["get_ok"])
    result = await harness.adapter.probe()
    assert (result.ok, result.shape_ok) == (True, True)
    request = harness.requests[0]
    assert request.url.params["q"] == "research"
    assert request.url.params["count"] == "1"

    harness = harness_for(source)
    harness.serve(fixtures_of(source)["malformed"])
    result = await harness.adapter.probe()
    assert (result.ok, result.shape_ok) == (True, False)
