"""Tests for the Programmable Search adapter (LLD-sources-v3 5.7, 5.8; SPEC-v5 4, 9).

The generic conformance checks run in
``tests/sources/test_conformance.py::test_conformance_passes[google_pse]``. This file
covers what SRC-33 adds beyond conformance: the ``x-goog-api-key`` header and the
registered source reporting ``deprecated(days)`` for its announced shutdown, and SRC-31's
single, truncating site-set query.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from research_mcp.core.models import SearchRequest
from research_mcp.settings import Settings
from research_mcp.sources import google_pse
from research_mcp.sources.registry import RegisteredSource, SourceRegistry
from research_mcp.testing.clock import FakeClock

MODULE = "research_mcp.sources.google_pse"
NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)


class OfflineSettings(Settings):
    """Settings from keyword arguments only: no config file, no environment."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


def registry(clock: FakeClock | None = None, **sources: Any) -> SourceRegistry:
    def no_context(spec: Any) -> Any:
        raise AssertionError("these tests build adapters through the harness")

    return SourceRegistry(
        OfflineSettings(sources=sources),
        no_context,
        has_credential=lambda name: True,
        has_extra=lambda extra: True,
        clock=clock or FakeClock(NOW),
        modules=[MODULE],
    )


def configured(**overrides: Any) -> RegisteredSource:
    source = registry(google_pse={"enabled": True, "engine_id": "v1_docs_engine", **overrides}).get(
        "google_pse"
    )
    assert source is not None
    return source


async def test_conformance_passes(harness_for: Any, fixtures_of: Any, counting_stream: Any) -> None:
    """@spec SRC-20: ``google_pse`` passes the eight-check conformance suite."""
    from tests.sources.test_conformance import run_conformance

    await run_conformance(configured(), harness_for, fixtures_of, counting_stream)


def test_spec_shares_the_devknowledge_key_and_announces_its_shutdown() -> None:
    """@spec SRC-33: The key is the devknowledge key, sent as a header; the spec carries
    the announced shutdown date."""
    spec = google_pse.SPEC
    assert spec.id == "google_pse"
    assert spec.group == "web"
    assert spec.enabled_by_default is False
    assert spec.hosts == frozenset({"www.googleapis.com"})
    assert spec.auth is not None
    assert spec.auth.secrets == ("GOOGLE_DEVKNOWLEDGE_API_KEY",)
    assert spec.auth.placement == "header"
    assert spec.auth.param == "x-goog-api-key"
    assert spec.auth.origins == ("https://www.googleapis.com",)
    assert spec.auth.validation == "probe"
    assert spec.shutdown_on == date(2027, 1, 1)
    # No free probe exists, so the probe spends one query, at most once a day (5.7).
    assert (spec.probe.cadence_s, spec.probe.cost) == (24 * 3600, "metered")


def test_registered_source_reports_deprecated_days() -> None:
    """@spec SRC-33: The registry reports ``deprecated(days)`` ahead of the shutdown."""
    clock = FakeClock(datetime(2026, 12, 1, 12, tzinfo=UTC))
    reg = registry(clock=clock, google_pse={"enabled": True, "engine_id": "v1_docs_engine"})
    view = reg.view("google_pse")[0]
    assert view.shutdown_on == date(2027, 1, 1)
    assert view.deprecated_days == 31


async def test_search_sends_cx_q_num_and_the_api_key_header(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-33: ``search`` sends ``cx``, ``q`` and ``num`` and attaches the key as
    ``x-goog-api-key``."""
    source = configured()
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["search_ok"])
    page = await harness.adapter.search(SearchRequest(query="single sign on", limit=5))
    request = harness.requests[0]
    assert request.method == "GET"
    assert request.url.params["cx"] == "v1_docs_engine"
    assert request.url.params["q"] == "single sign on"
    assert request.url.params["num"] == "5"
    assert request.headers["x-goog-api-key"] == "fake-google_devknowledge_api_key"
    first = page.records[0]
    assert first.work_type == "webpage"
    assert first.title == "Server Administration Guide"
    assert [(i.scheme, i.value) for i in first.ids] == [
        ("url", "https://www.keycloak.org/docs/latest/server_admin/index.html")
    ]
    assert page.total == 3
    assert page.records[2].abstract is None


async def test_without_an_engine_id_setting_cx_is_omitted(
    harness_for: Any, fixtures_of: Any
) -> None:
    """Without ``sources.google_pse.engine_id``, the request carries no ``cx`` at all."""
    source = registry(google_pse={"enabled": True}).get("google_pse")
    assert source is not None
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["search_empty"])
    await harness.adapter.search(SearchRequest(query="nothing", limit=3))
    assert "cx" not in harness.requests[0].url.params


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


async def test_probe_spends_one_query_and_checks_the_items_shape(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-33: ``probe`` calls the search endpoint and checks the items shape."""
    source = configured()
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["get_ok"])
    result = await harness.adapter.probe()
    assert (result.ok, result.shape_ok) == (True, True)
    request = harness.requests[0]
    assert request.url.params["q"] == "research"
    assert request.url.params["num"] == "1"

    harness = harness_for(source)
    harness.serve(fixtures_of(source)["malformed"])
    result = await harness.adapter.probe()
    assert (result.ok, result.shape_ok) == (True, False)
