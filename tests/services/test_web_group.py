"""The ``web`` group: gating, daily caps and the fallback chain (LLD-sources-v3 5.7 to 5.9).

Every web source here is declared in this file (plan check ``rm-m1b``): a stub adapter that
never calls out, registered through ``extra_adapters``, so gating and the daily cap are
exercised before the real Brave, SerpAPI, Programmable Search or Vertex adapters exist.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from research_mcp.core.specs import RateSpec
from research_mcp.settings import Settings, SourceSettings
from research_mcp.sources.base import Capability, SourceContext, SourceSpec
from research_mcp.sources.registry import SourceRegistry
from research_mcp.testing.clock import FakeClock

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)


class OfflineSettings(Settings):
    """Settings from keyword arguments only: no config file, no environment."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


class WebAdapter:
    """A web-group adapter stub: it never calls out."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx


def web_spec(id: str, **overrides: Any) -> SourceSpec:
    values: dict[str, Any] = {
        "id": id,
        "title": f"{id} source",
        "group": "web",
        "capabilities": frozenset({Capability.SEARCH}),
        "id_schemes": frozenset({"url"}),
        "hosts": frozenset({f"api.{id.replace('_', '-')}.example"}),
        "auth": None,
        "rate": RateSpec(rps=5.0),
        "enabled_by_default": False,
    }
    values.update(overrides)
    return SourceSpec(**values)


VERTEX_ALPHA = web_spec("vertex_alpha")
VERTEX_BETA = web_spec("vertex_beta")
BRAVE_SEARCH = web_spec("brave_search")
SERPAPI = web_spec("serpapi")
GOOGLE_PSE = web_spec("google_pse")
WEB_SOURCES = (VERTEX_ALPHA, VERTEX_BETA, BRAVE_SEARCH, SERPAPI, GOOGLE_PSE)


def build(
    settings: Settings | None = None,
    *,
    extra: tuple[SourceSpec, ...] = WEB_SOURCES,
    clock: FakeClock | None = None,
    **ports: Any,
) -> SourceRegistry:
    settings = settings or OfflineSettings()
    clock = clock or FakeClock(NOW)
    ctx = SourceContext(
        http=cast(Any, None),
        mcp=None,
        settings=SourceSettings(),
        clock=clock,
        contact_email=None,
    )
    ports.setdefault("has_credential", lambda name: True)
    return SourceRegistry(
        settings,
        lambda spec: ctx,
        clock=clock,
        modules=[],
        extra_adapters=tuple((spec, WebAdapter) for spec in extra),
        **ports,
    )


def test_web_excluded_from_auto_selection_even_when_listed_as_default() -> None:
    """@spec SRC-28: Auto selection never includes ``web``, even if settings list it."""
    registry = build(OfflineSettings(federation={"default_groups": ["scholarly", "web"]}))
    assert registry.select(None, Capability.SEARCH) == []


def test_web_group_runs_only_when_named_by_group_or_id() -> None:
    """@spec SRC-28: A caller must name the ``web`` group or a source id to run it."""
    settings = OfflineSettings(sources={"brave_search": {"enabled": True}})
    registry = build(settings)
    assert registry.select(None, Capability.SEARCH) == []
    by_group = {s.source: s.skip for s in registry.select(["web"], Capability.SEARCH)}
    assert by_group["brave_search"] is None
    assert by_group["vertex_alpha"] is not None
    assert by_group["vertex_alpha"].state == "disabled"
    (by_id,) = registry.select(None, Capability.SEARCH, explicit=["brave_search"])
    assert by_id.skip is None


def test_web_source_stays_disabled_without_enabled_true_even_with_credential() -> None:
    """@spec SRC-28: Presence of settings and a credential never enables a web source."""
    registry = build(has_credential=lambda name: True)
    (selected,) = registry.select(None, Capability.SEARCH, explicit=["brave_search"])
    assert selected.skip is not None
    assert selected.skip.state == "disabled"


def test_web_source_at_daily_cap_is_budget_exhausted_until_midnight() -> None:
    """@spec SRC-29: At ``budget_cap`` calls today, the source is ``budget_exhausted``.

    The reset time is the next local midnight by a ``FakeClock``; under the cap, or once the
    day's count resets, the same source is reachable again.
    """
    clock = FakeClock(NOW)
    settings = OfflineSettings(sources={"serpapi": {"enabled": True, "budget_cap": 1}})
    calls_today = {"serpapi": 1}
    registry = build(settings, clock=clock, calls_today=lambda source: calls_today.get(source, 0))
    (selected,) = registry.select(None, Capability.SEARCH, explicit=["serpapi"])
    assert selected.skip is not None
    assert selected.skip.state == "budget_exhausted"
    (view,) = registry.view("serpapi")
    assert view.state == "budget_exhausted"
    assert view.budget_reset_at is not None
    assert view.budget_reset_at > clock.now()
    calls_today["serpapi"] = 0
    (under_cap,) = registry.select(None, Capability.SEARCH, explicit=["serpapi"])
    assert under_cap.skip is None


def test_web_chain_expands_vertex_wildcard_in_id_order_and_drops_unregistered() -> None:
    """``web_chain`` expands ``vertex_*`` to the registered instances, drops unknown names."""
    settings = OfflineSettings(
        sources={
            "vertex_alpha": {"enabled": True},
            "vertex_beta": {"enabled": True},
            "brave_search": {"enabled": True},
        }
    )
    registry = build(settings)
    chain = registry.web_chain("fallback", ["vertex_*", "brave_search", "serpapi", "nope"])
    assert [s.source for s in chain] == ["vertex_alpha", "vertex_beta", "brave_search", "serpapi"]
    assert chain[0].skip is None
    assert chain[2].skip is None
    assert chain[3].skip is not None
    assert chain[3].skip.state == "disabled"


def test_web_chain_defaults_to_the_web_order_setting() -> None:
    """Without an explicit order, ``web_chain`` reads ``web.order``."""
    registry = build()
    chain = registry.web_chain("fallback")
    assert [s.source for s in chain] == [
        "vertex_alpha",
        "vertex_beta",
        "brave_search",
        "serpapi",
        "google_pse",
    ]
