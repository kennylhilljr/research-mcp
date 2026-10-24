"""SourceSpec validation, adapter discovery, instances and the selection skips.

LLD-sources-v2 2.1, 2.3 and 5.2, with the M0-09 rows of M0-plan-v4 section 2.2. Settings
never read the owner's files or environment, and every upstream is an
``httpx.MockTransport``, so nothing here touches the network.
"""

from __future__ import annotations

import dataclasses
import sys
from collections.abc import AsyncIterator, Callable, Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

import research_mcp.sources as sources_pkg
from research_mcp.core.errors import ErrorCode, ToolError
from research_mcp.core.models import CallRecord, SearchRequest
from research_mcp.core.specs import AuthSpec, ProbeSpec, RateSpec
from research_mcp.platform.http import HttpClient
from research_mcp.settings import Settings, SourceSettings
from research_mcp.sources.base import Capability, SourceContext, SourceSpec
from research_mcp.sources.registry import SourceRegistry, default_has_extra
from research_mcp.testing.adapters import FAKE_SPEC, FakeAdapter
from research_mcp.testing.clock import FakeClock, FakeSleeper


class OfflineSettings(Settings):
    """Settings from keyword arguments only: no config file, no environment."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


def spec(**overrides: Any) -> SourceSpec:
    values: dict[str, Any] = {
        "id": "demo",
        "title": "Demo source",
        "group": "scholarly",
        "capabilities": frozenset({Capability.SEARCH}),
        "id_schemes": frozenset({"doi"}),
        "hosts": frozenset({"api.demo.org"}),
        "auth": None,
        "rate": RateSpec(rps=5.0, burst=2, concurrency=2),
    }
    values.update(overrides)
    return SourceSpec(**values)


def auth(**overrides: Any) -> AuthSpec:
    values: dict[str, Any] = {
        "secrets": ("DEMO_API_KEY",),
        "required": True,
        "placement": "header",
        "param": "x-api-key",
        "origins": ("https://api.demo.org",),
        "signup_url": "https://demo.org/keys",
    }
    values.update(overrides)
    return AuthSpec(**values)


class Body(httpx.AsyncByteStream):
    """An empty result page that arrives unread, as from a network transport."""

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b'{"total": 0, "next": null, "results": []}'


class Network:
    """An HTTP client over a mock transport that records every request it sees."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.clock = FakeClock(datetime(2026, 10, 23, 12, tzinfo=UTC))
        self.records: list[CallRecord] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, headers={"content-type": "application/json"}, stream=Body())

    def client(self, registry: SourceRegistry) -> HttpClient:
        network = self

        class Sink:
            def record(self, call: CallRecord) -> None:
                network.records.append(call)

        class NoCredentials:
            def secret_for(self, source: str) -> None:
                return None

        return HttpClient(
            registry,
            NoCredentials(),
            Sink(),
            self.clock,
            FakeSleeper(self.clock),
            "owner@uni.edu",
            transport=httpx.MockTransport(self.handler),
        )


def build(
    settings: Settings | None = None,
    *,
    extra: tuple[tuple[SourceSpec, type[Any]], ...] = ((FAKE_SPEC, FakeAdapter),),
    network: Network | None = None,
    **ports: Any,
) -> SourceRegistry:
    network = network or Network()
    holder: dict[str, HttpClient] = {}
    settings = settings or OfflineSettings()

    def ctx_factory(source: SourceSpec) -> SourceContext:
        return SourceContext(
            http=holder["http"],
            mcp=None,
            settings=settings.sources.get(source.id) or SourceSettings(),
            clock=network.clock,
            contact_email=settings.contact.email,
        )

    ports.setdefault("has_credential", lambda name: True)
    ports.setdefault("has_extra", lambda extra: True)
    registry = SourceRegistry(
        settings,
        ctx_factory,
        clock=network.clock,
        modules=ports.pop("modules", []),
        extra_adapters=extra,
        **ports,
    )
    holder["http"] = network.client(registry)
    return registry


VALID_BOUNDS: list[tuple[str, dict[str, Any]]] = [
    ("id too short", {"id": "a"}),
    ("id with capital", {"id": "Demo"}),
    ("id with dash", {"id": "demo-source"}),
    ("id too long", {"id": "a" * 41}),
    ("empty title", {"title": ""}),
    ("long title", {"title": "t" * 121}),
    ("unknown group", {"group": "blogs"}),
    ("no capabilities", {"capabilities": frozenset()}),
    ("no hosts", {"hosts": frozenset()}),
    ("host with scheme", {"hosts": frozenset({"https://api.demo.org"})}),
    ("host with path", {"hosts": frozenset({"api.demo.org/v1"})}),
    ("host with port", {"hosts": frozenset({"api.demo.org:443"})}),
    ("host with userinfo", {"hosts": frozenset({"user@api.demo.org"})}),
    ("uppercase host", {"hosts": frozenset({"API.demo.org"})}),
    ("auth without origins", {"auth": auth(origins=())}),
    ("auth origin host not in hosts", {"auth": auth(origins=("https://other.org",))}),
    ("auth without secrets", {"auth": auth(secrets=())}),
    ("auth secret name lowercase", {"auth": auth(secrets=("demo_key",))}),
    ("required auth signup not https", {"auth": auth(signup_url="http://demo.org/keys")}),
    ("zero rps", {"rate": RateSpec(rps=0.0)}),
    ("negative rps", {"rate": RateSpec(rps=-1.0)}),
    ("rps over 50", {"rate": RateSpec(rps=50.5)}),
    ("nan rps", {"rate": RateSpec(rps=float("nan"))}),
    ("zero burst", {"rate": RateSpec(rps=1.0, burst=0)}),
    ("burst over 50", {"rate": RateSpec(rps=1.0, burst=51)}),
    ("zero concurrency", {"rate": RateSpec(rps=1.0, concurrency=0)}),
    ("concurrency over 16", {"rate": RateSpec(rps=1.0, concurrency=17)}),
    ("zero daily quota", {"rate": RateSpec(rps=1.0, daily_quota=0)}),
    ("timeout under 0.5", {"timeout_s": 0.4}),
    ("timeout over 60", {"timeout_s": 61.0}),
    ("page size 0", {"max_page_size": 0}),
    ("page size over 1000", {"max_page_size": 1001}),
    ("max bytes under 1024", {"max_bytes": 1023}),
    ("max bytes over 50 MB", {"max_bytes": 50_000_001}),
    ("unknown extra", {"extras": frozenset({"gpu"})}),
    ("probe cadence under 60", {"probe": ProbeSpec(59, "free", "")}),
    ("probe cadence over a week", {"probe": ProbeSpec(604_801, "free", "")}),
    ("metered probe under an hour", {"probe": ProbeSpec(3599, "metered", "")}),
    ("docs url not https", {"docs_url": "http://demo.org/docs"}),
    ("web source enabled by default", {"group": "web", "enabled_by_default": True}),
]


@pytest.mark.parametrize(("case", "overrides"), VALID_BOUNDS, ids=[c for c, _ in VALID_BOUNDS])
def test_spec_rejects_missing_field_out_of_bounds_rate_and_auth_without_origins(
    case: str, overrides: dict[str, Any]
) -> None:
    """@spec SRC-1: A spec outside a bound of the 2.1 table, or auth without origins, fails."""
    with pytest.raises(ValueError):
        spec(**overrides)


@pytest.mark.parametrize(
    "field", ["id", "title", "group", "capabilities", "id_schemes", "hosts", "auth", "rate"]
)
def test_spec_rejects_a_missing_required_field(field: str) -> None:
    """@spec SRC-1: Leaving out any required field fails at construction."""
    values = {
        name: getattr(spec(), name)
        for name in ("id", "title", "group", "capabilities", "id_schemes", "hosts", "auth", "rate")
    }
    del values[field]
    with pytest.raises((TypeError, ValueError)):
        SourceSpec(**values)


def test_spec_accepts_the_edges_of_each_bound() -> None:
    """@spec SRC-1: The bounds are inclusive where the 2.1 table says so."""
    low = spec(
        id="ab",
        title="t",
        rate=RateSpec(rps=0.001, burst=1, concurrency=1, daily_quota=1),
        timeout_s=0.5,
        max_page_size=1,
        max_bytes=1024,
        probe=ProbeSpec(60, "free", ""),
        auth=auth(required=False, signup_url=""),
    )
    high = spec(
        id="a" * 40,
        title="t" * 120,
        rate=RateSpec(rps=50.0, burst=50, concurrency=16),
        timeout_s=60.0,
        max_page_size=1000,
        max_bytes=50_000_000,
        probe=ProbeSpec(604_800, "metered", ""),
        extras=frozenset({"pdf", "embeddings", "macos", "gcp"}),
        docs_url="https://demo.org/docs",
        shutdown_on=date(2027, 1, 1),
    )
    web = spec(group="web", enabled_by_default=False, probe=ProbeSpec(3600, "metered", ""))
    assert low.max_bytes == 1024
    assert high.max_page_size == 1000
    assert web.enabled_by_default is False


def test_spec_policy_and_deprecated_days() -> None:
    """The policy copies the spec's limits; ``deprecated_days`` counts down to the shutdown."""
    source = spec(shutdown_on=date(2027, 1, 1), rate=RateSpec(rps=2.0, daily_quota=500))
    policy = source.policy(daily_quota=100)
    assert policy.source == "demo"
    assert policy.hosts == frozenset({"api.demo.org"})
    assert policy.rate == RateSpec(rps=2.0, daily_quota=100)
    assert source.policy().rate.daily_quota == 500
    assert (policy.timeout_s, policy.max_bytes) == (5.0, 5_000_000)
    assert source.deprecated_days(date(2026, 12, 22)) == 10
    assert source.deprecated_days(date(2027, 3, 1)) == 0
    assert spec().deprecated_days(date(2026, 12, 22)) is None


def test_duplicate_ids_fail_at_construction() -> None:
    """Two specs with one id are refused when the registry is built, not at the first call."""
    with pytest.raises(ValueError, match="fake"):
        build(extra=((FAKE_SPEC, FakeAdapter), (FAKE_SPEC, FakeAdapter)))


PLAIN_MODULE = """\
from research_mcp.testing.adapters import FAKE_SPEC, FakeAdapter
import dataclasses

SPEC = dataclasses.replace(FAKE_SPEC, id="{name}", title="Discovered {name}")
ADAPTER = FakeAdapter
"""

KIND_MODULE = """\
from research_mcp.testing.adapters import (
    FAKE_KIND_SPEC as SPEC,
    FakeAdapter as ADAPTER,
    FakeInstance as INSTANCE_MODEL,
    fake_instance_spec as instance_spec,
)
"""

HELPER_MODULE = '"""A helper module with neither SPEC nor ADAPTER, like robots.py."""\nVALUE = 1\n'


@pytest.fixture
def discovered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A folder on the ``research_mcp.sources`` path holding modules the scan must find."""
    folder = tmp_path / "extra_sources"
    folder.mkdir()
    (folder / "zz_alpha.py").write_text(PLAIN_MODULE.format(name="zz_alpha"))
    (folder / "zz_kind.py").write_text(KIND_MODULE)
    (folder / "zz_helper.py").write_text(HELPER_MODULE)
    monkeypatch.setattr(sources_pkg, "__path__", [*sources_pkg.__path__, str(folder)])
    yield folder
    for name in ("zz_alpha", "zz_kind", "zz_helper"):
        sys.modules.pop(f"research_mcp.sources.{name}", None)


def test_discovers_builtin_and_builds_two_instances_from_settings(discovered: Path) -> None:
    """@spec SRC-2: The scan finds the built-in adapters and settings alone add two instances."""
    settings = OfflineSettings(
        sources={
            "zz_kind_north": {
                "instance_of": "zz_kind",
                "base_url": "https://north.repo.org/server/api",
                "title": "North repository",
            },
            "zz_kind_south": {
                "instance_of": "zz_kind",
                "base_url": "https://south.repo.org/server/api",
                "title": "South repository",
            },
        }
    )
    registry = build(settings, extra=(), modules=None)
    ids = [source.spec.id for source in registry.all()]
    assert "zz_alpha" in ids
    assert {"zz_kind_north", "zz_kind_south"} <= set(ids)
    # The kind with configured instances is not listed itself; helpers are not adapters.
    assert "zz_kind" not in ids
    assert not any(name in ids for name in ("zz_helper", "base", "registry"))
    north = registry.get("zz_kind_north")
    assert north is not None
    assert north.adapter_cls is FakeAdapter
    assert north.spec.title == "North repository"
    assert north.spec.hosts == frozenset({"north.repo.org"})
    assert north.spec.instance_of == "zz_kind"
    assert north.instance is not None
    south = registry.get("zz_kind_south")
    assert south is not None
    assert south.spec.hosts == frozenset({"south.repo.org"})
    selected = {s.source: s for s in registry.select(["repositories"], Capability.SEARCH)}
    assert selected["zz_kind_north"].skip is None
    assert selected["zz_kind_south"].skip is None
    assert selected["zz_kind_north"].adapter is not selected["zz_kind_south"].adapter


def test_kind_without_instances_is_listed_once_unconfigured(discovered: Path) -> None:
    """A kind with no instance entry is listed once, with the fix that adds one."""
    registry = build(extra=(), modules=None)
    (view,) = registry.view("zz_kind")
    assert view.state == "unconfigured"
    assert view.fix_hint is not None
    assert "sources.<name>" in view.fix_hint
    assert "instance_of = " in view.fix_hint


def test_invalid_instance_entry_is_unconfigured_and_does_not_stop_the_registry(
    discovered: Path,
) -> None:
    """An entry that fails its kind's model is ``unconfigured``; the others still work."""
    settings = OfflineSettings(
        sources={
            "zz_kind_good": {
                "instance_of": "zz_kind",
                "base_url": "https://good.repo.org/api",
                "title": "Good",
            },
            "zz_kind_bad": {"instance_of": "zz_kind", "title": "Bad", "colour": "red"},
        }
    )
    registry = build(settings, extra=(), modules=None)
    states = {view.id: view.state for view in registry.view()}
    assert states["zz_kind_good"] == "ok"
    assert states["zz_kind_bad"] == "unconfigured"
    (bad,) = registry.view("zz_kind_bad")
    assert bad.fix_hint is not None
    assert "sources.zz_kind_bad" in bad.fix_hint


def test_disabled_source_is_skipped_and_records_no_request() -> None:
    """@spec SRC-3: A disabled source is never called and is reported ``disabled``."""
    network = Network()
    settings = OfflineSettings(sources={"fake": {"enabled": False}})
    registry = build(settings, network=network)
    for picked in (
        registry.select(["scholarly"], Capability.SEARCH),
        registry.select(None, Capability.SEARCH, explicit=["fake"]),
    ):
        (selected,) = picked
        assert selected.skip is not None
        assert selected.skip.state == "disabled"
        assert selected.skip.source == "fake"
    (view,) = registry.view("fake")
    assert view.state == "disabled"
    assert view.enabled is False
    assert view.fix_hint == ("Enable it with `research-mcp config set sources.fake.enabled true`")
    assert network.requests == []
    assert network.records == []


async def test_enabled_source_reaches_the_network_through_select() -> None:
    """The same registry with the source enabled calls it, so the disabled case is real."""
    network = Network()
    registry = build(OfflineSettings(sources={"fake": {"enabled": True}}), network=network)
    (selected,) = registry.select(None, Capability.SEARCH, explicit=["fake"])
    assert selected.skip is None
    await selected.adapter.search(SearchRequest(query="graphs"))
    assert len(network.requests) == 1


def test_disabled_by_default_needs_enabled_true() -> None:
    """A spec that is off by default is ``disabled`` until settings turn it on."""
    off = dataclasses.replace(FAKE_SPEC, id="quiet", enabled_by_default=False)
    registry = build(extra=((off, FakeAdapter),))
    assert registry.view("quiet")[0].state == "disabled"
    registry = build(
        OfflineSettings(sources={"quiet": {"enabled": True}}), extra=((off, FakeAdapter),)
    )
    assert registry.view("quiet")[0].state == "ok"


KEYED = dataclasses.replace(
    FAKE_SPEC,
    id="keyed",
    hosts=frozenset({"api.keyed.org"}),
    auth=AuthSpec(
        secrets=("KEYED_API_KEY",),
        required=True,
        placement="header",
        param="x-api-key",
        origins=("https://api.keyed.org",),
        signup_url="https://keyed.org/signup",
    ),
)
POLITE = dataclasses.replace(FAKE_SPEC, id="polite", needs_contact=True)


def test_missing_credential_or_contact_is_unconfigured_with_exact_fix() -> None:
    """@spec SRC-4: A missing required credential or unset contact gives the exact fix."""
    registry = build(
        extra=((KEYED, FakeAdapter), (POLITE, FakeAdapter)),
        has_credential=lambda name: False,
    )
    skips = {s.source: s.skip for s in registry.select(["scholarly"], Capability.SEARCH)}
    assert skips["keyed"] is not None and skips["keyed"].state == "unconfigured"
    assert skips["polite"] is not None and skips["polite"].state == "unconfigured"
    views = {view.id: view for view in registry.view()}
    assert views["keyed"].state == "unconfigured"
    assert views["keyed"].fix_hint == (
        "Add Keychain item `research-mcp/KEYED_API_KEY` (sign up: `https://keyed.org/signup`): "
        '`security add-generic-password -U -s research-mcp/KEYED_API_KEY -a "$USER" -w`'
    )
    assert views["keyed"].signup_url == "https://keyed.org/signup"
    assert views["polite"].state == "unconfigured"
    assert views["polite"].fix_hint == (
        "Set `contact.email` to your own address: `research-mcp config set contact.email <address>`"
    )


def test_credential_and_contact_present_are_not_skipped() -> None:
    """With the Keychain item present and a contact address set, nothing is skipped."""
    seen: list[str] = []

    def has_credential(name: str) -> bool:
        seen.append(name)
        return True

    registry = build(
        OfflineSettings(contact={"email": "owner@uni.edu"}),
        extra=((KEYED, FakeAdapter), (POLITE, FakeAdapter)),
        has_credential=has_credential,
    )
    assert all(s.skip is None for s in registry.select(["scholarly"], Capability.SEARCH))
    assert "KEYED_API_KEY" in seen


def test_optional_credential_missing_is_not_a_skip() -> None:
    """Only a required credential makes a source ``unconfigured``."""
    assert KEYED.auth is not None
    optional = dataclasses.replace(
        KEYED, id="optional", auth=dataclasses.replace(KEYED.auth, required=False)
    )
    registry = build(extra=((optional, FakeAdapter),), has_credential=lambda name: False)
    assert registry.view("optional")[0].state == "ok"


GCP = dataclasses.replace(FAKE_SPEC, id="needs_gcp", extras=frozenset({"gcp"}))


def test_missing_extra_is_unconfigured_with_install_command() -> None:
    """@spec SRC-5: A source whose optional extra is missing names the install command."""
    asked: list[str] = []

    def has_extra(extra: str) -> bool:
        asked.append(extra)
        return False

    registry = build(extra=((GCP, FakeAdapter),), has_extra=has_extra)
    (selected,) = registry.select(["scholarly"], Capability.SEARCH)
    assert selected.skip is not None and selected.skip.state == "unconfigured"
    (view,) = registry.view("needs_gcp")
    assert view.state == "unconfigured"
    assert view.fix_hint == "Install the extra: `uv tool install 'research-mcp[gcp]'`"
    assert asked == ["gcp", "gcp"]
    present = build(extra=((GCP, FakeAdapter),), has_extra=lambda extra: True)
    assert present.view("needs_gcp")[0].state == "ok"


def test_default_has_extra_looks_up_modules_without_importing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``default_has_extra`` asks ``find_spec`` for the extra's module."""
    import importlib.util

    asked: list[str] = []

    def find_spec(name: str) -> object | None:
        asked.append(name)
        if name == "google.auth":
            raise ModuleNotFoundError(name)
        return object() if name == "fitz" else None

    monkeypatch.setattr(importlib.util, "find_spec", find_spec)
    assert default_has_extra("gcp") is False
    assert default_has_extra("pdf") is True
    assert default_has_extra("embeddings") is False
    assert default_has_extra("unknown") is False
    assert asked[:2] == ["google.auth", "fitz"]


def test_skip_order_first_match_wins() -> None:
    """Disabled beats a missing extra, which beats a missing credential and contact."""
    everything = dataclasses.replace(
        KEYED, id="everything", needs_contact=True, extras=frozenset({"gcp"})
    )
    off = OfflineSettings(sources={"everything": {"enabled": False}})
    ports: dict[str, Callable[[str], bool]] = {
        "has_credential": lambda name: False,
        "has_extra": lambda extra: False,
    }
    assert build(off, extra=((everything, FakeAdapter),), **ports).view()[0].state == "disabled"
    view = build(extra=((everything, FakeAdapter),), **ports).view()[0]
    assert view.fix_hint is not None and view.fix_hint.startswith("Install the extra")
    ports["has_extra"] = lambda extra: True
    view = build(extra=((everything, FakeAdapter),), **ports).view()[0]
    assert view.fix_hint is not None and view.fix_hint.startswith("Add Keychain item")


def test_health_down_or_rate_limited_is_skipped_unhealthy_under_auto() -> None:
    """Under auto, health ``down`` or ``rate_limited`` is ``skipped_unhealthy`` (M0-plan 2.2).

    ``budget_exhausted`` keeps its own state, ``retry_after_ms`` stays ``None`` in M0, and a
    source named explicitly is tried once whatever its health (SRCH-FR-8).
    """
    states = {"one": "down", "two": "rate_limited", "three": "budget_exhausted", "four": "ok"}
    extra = tuple((dataclasses.replace(FAKE_SPEC, id=name), FakeAdapter) for name in states)
    registry = build(extra=extra, health=states.get)
    skips = {s.source: s.skip for s in registry.select(None, Capability.SEARCH)}
    assert skips["one"] is not None and skips["one"].state == "skipped_unhealthy"
    assert skips["two"] is not None and skips["two"].state == "skipped_unhealthy"
    assert skips["three"] is not None and skips["three"].state == "budget_exhausted"
    assert skips["four"] is None
    assert all(s is None or s.retry_after_ms is None for s in skips.values())
    explicit = registry.select(None, Capability.SEARCH, explicit=["one", "two"])
    assert [s.skip for s in explicit] == [None, None]
    assert {view.id: view.state for view in registry.view()}["one"] == "down"


def test_health_default_port_skips_nothing() -> None:
    """Without a health port no source is skipped for health."""
    registry = build()
    (selected,) = registry.select(None, Capability.SEARCH)
    assert selected.skip is None
    assert registry.view("fake")[0].state == "ok"


def test_auto_selection_uses_default_groups_without_web() -> None:
    """Auto selection reads ``federation.default_groups`` and never includes ``web``."""
    web = dataclasses.replace(FAKE_SPEC, id="webby", group="web", enabled_by_default=False)
    biomed = dataclasses.replace(FAKE_SPEC, id="medical", group="biomed")
    settings = OfflineSettings(federation={"default_groups": ["scholarly", "web"]})
    extra = ((FAKE_SPEC, FakeAdapter), (web, FakeAdapter), (biomed, FakeAdapter))
    registry = build(settings, extra=extra)
    assert [s.source for s in registry.select(None, Capability.SEARCH)] == ["fake"]
    assert [s.source for s in registry.select(["web"], Capability.SEARCH)] == ["webby"]
    assert [s.source for s in registry.select(["biomed"], Capability.SEARCH)] == ["medical"]
    assert registry.select(None, Capability.CITATIONS) == []
    assert [s.spec.id for s in registry.by_group("biomed")] == ["medical"]


def test_unknown_explicit_id_is_invalid_argument() -> None:
    """An explicit id that is not registered is ``invalid_argument`` before any call."""
    registry = build()
    with pytest.raises(ToolError) as caught:
        registry.select(None, Capability.SEARCH, explicit=["nope"])
    assert caught.value.code is ErrorCode.INVALID_ARGUMENT
    with pytest.raises(ToolError):
        registry.view("nope")
    assert registry.get("nope") is None


def test_daily_cap_reached_is_budget_exhausted() -> None:
    """At ``budget_cap`` calls today the source is ``budget_exhausted`` until local midnight."""
    settings = OfflineSettings(sources={"fake": {"budget_cap": 3}})
    registry = build(settings, calls_today=lambda source: 3)
    (selected,) = registry.select(None, Capability.SEARCH)
    assert selected.skip is not None and selected.skip.state == "budget_exhausted"
    (view,) = registry.view("fake")
    assert (view.state, view.budget_cap, view.calls_today) == ("budget_exhausted", 3, 3)
    assert view.budget_reset_at is not None
    assert view.budget_reset_at > datetime(2026, 10, 23, 12, tzinfo=UTC)
    under = build(settings, calls_today=lambda source: 2)
    assert under.view("fake")[0].state == "ok"
    assert registry.policy("fake").rate.daily_quota == 3


def test_policy_of_an_unknown_source_is_blocked() -> None:
    """The registry is the HTTP client's policy resolver; an unknown source gets none."""
    from research_mcp.core.errors import HttpError

    with pytest.raises(HttpError) as caught:
        build().policy("nope")
    assert caught.value.code is ErrorCode.BLOCKED_BY_POLICY


def test_view_carries_spec_fields() -> None:
    """A view lists the spec's title, group, capabilities, URLs and shutdown countdown."""
    dated = dataclasses.replace(
        FAKE_SPEC,
        id="dated",
        shutdown_on=date(2026, 11, 2),
        docs_url="https://fake-source.org/docs",
    )
    (view,) = build(extra=((dated, FakeAdapter),)).view("dated")
    assert view.title == dated.title
    assert view.group == "scholarly"
    assert view.capabilities == tuple(sorted(c.value for c in dated.capabilities))
    assert view.docs_url == "https://fake-source.org/docs"
    assert view.signup_url is None
    assert view.shutdown_on == date(2026, 11, 2)
    assert view.deprecated_days is not None and 9 <= view.deprecated_days <= 10
    assert view.reason is None and view.fix_hint is None
    assert view.budget_cap is None and view.calls_today is None
    assert view.enabled is True


def test_registry_construction_imports_nothing_when_modules_is_empty() -> None:
    """``modules=[]`` loads no module, so tests see only the adapters they pass in."""
    registry = build(extra=())
    assert registry.all() == []
