"""The source registry: discovery, instances, selection and the views (LLD-sources-v2 5.2).

Adapters are found by scanning the ``research_mcp.sources`` package (2.3); instance kinds
also get one source per settings entry whose ``instance_of`` names them. Credential
presence, health, the daily call count and extra detection come in as callables, so
nothing here imports the secrets, health or store modules.
"""

import dataclasses
import importlib
import importlib.util
import logging
import pkgutil
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from types import ModuleType
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

import research_mcp.sources as sources_pkg
from research_mcp.core.envelope import SourceStatus
from research_mcp.core.errors import ErrorCode, HttpError, ToolError
from research_mcp.core.models import Clock, SearchFilters
from research_mcp.core.specs import SourcePolicy
from research_mcp.core.timeutil import SystemClock
from research_mcp.settings import Settings, SourceSettings
from research_mcp.sources.base import Capability, SourceAdapter, SourceContext, SourceSpec

PACKAGE = "research_mcp.sources"
SYSTEM_CLOCK = SystemClock()
# The module each extra installs; find_spec looks for it without importing it.
EXTRA_MODULES = {
    "pdf": "fitz",
    "embeddings": "fastembed",
    "macos": "Foundation",
    "gcp": "google.auth",
}
_NOT_ADAPTERS = frozenset({"base", "registry"})
_log = logging.getLogger(__name__)

SkipState = Literal["disabled", "unconfigured", "budget_exhausted", "skipped_unhealthy"]
InstanceBuilder = Callable[[SourceSpec, str, BaseModel], SourceSpec]


def default_has_extra(extra: str) -> bool:
    module = EXTRA_MODULES.get(extra)
    if module is None:
        return False
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        # find_spec imports a dotted name's parent; a missing parent means a missing extra.
        return False


def next_local_midnight(now: datetime) -> datetime:
    """The next midnight in the system time zone, as a UTC time."""
    tomorrow = now.astimezone().date() + timedelta(days=1)
    return datetime.combine(tomorrow, time()).astimezone().astimezone(UTC)


@dataclass(frozen=True)
class RegisteredSource:
    spec: SourceSpec
    adapter_cls: type[SourceAdapter]
    settings: SourceSettings
    instance: BaseModel | None


@dataclass(frozen=True)
class Selected:
    source: str
    adapter: SourceAdapter
    skip: SourceStatus | None


@dataclass(frozen=True)
class SourceView:
    id: str
    title: str
    group: str
    capabilities: tuple[str, ...]
    state: str
    reason: str | None
    fix_hint: str | None
    enabled: bool
    shutdown_on: date | None
    deprecated_days: int | None
    signup_url: str | None
    docs_url: str | None
    budget_cap: int | None
    calls_today: int | None
    budget_reset_at: datetime | None


@dataclass(frozen=True)
class _Skip:
    state: SkipState
    reason: str
    fix_hint: str | None


@dataclass(frozen=True)
class _Kind:
    base: SourceSpec
    adapter_cls: type[SourceAdapter]
    model: type[BaseModel]
    build: InstanceBuilder


def _adapter_modules(modules: Iterable[str] | None) -> Iterator[ModuleType]:
    if modules is None:
        modules = [
            f"{PACKAGE}.{info.name}"
            for info in pkgutil.iter_modules(sources_pkg.__path__)
            if not info.ispkg and info.name not in _NOT_ADAPTERS
        ]
    for name in modules:
        module = importlib.import_module(name)
        if isinstance(getattr(module, "SPEC", None), SourceSpec) and hasattr(module, "ADAPTER"):
            yield module


class SourceRegistry:
    """Every source the daemon knows, and which of them a call may use."""

    # @spec SRC-2
    def __init__(
        self,
        settings: Settings,
        ctx_factory: Callable[[SourceSpec], SourceContext],
        *,
        has_credential: Callable[[str], bool],
        health: Callable[[str], str | None] = lambda s: None,
        calls_today: Callable[[str], int] = lambda s: 0,
        has_extra: Callable[[str], bool] = default_has_extra,
        clock: Clock = SYSTEM_CLOCK,
        modules: Iterable[str] | None = None,
        extra_adapters: Iterable[tuple[SourceSpec, type[SourceAdapter]]] = (),
    ) -> None:
        self._settings = settings
        self._ctx_factory = ctx_factory
        self._has_credential = has_credential
        self._health = health
        self._calls_today = calls_today
        self._has_extra = has_extra
        self._clock = clock
        self._sources: dict[str, RegisteredSource] = {}
        self._needs_instance: set[str] = set()
        self._adapters: dict[str, SourceAdapter] = {}
        kinds: dict[str, _Kind] = {}
        for module in _adapter_modules(modules):
            spec: SourceSpec = module.SPEC
            model = getattr(module, "INSTANCE_MODEL", None)
            build = getattr(module, "instance_spec", None)
            if model is not None and build is not None:
                kinds[spec.id] = _Kind(spec, module.ADAPTER, model, build)
            else:
                self._add(spec, module.ADAPTER, None)
        for spec, adapter_cls in extra_adapters:
            self._add(spec, adapter_cls, None)
        self._add_instances(kinds)

    def _add(
        self, spec: SourceSpec, adapter_cls: type[SourceAdapter], instance: BaseModel | None
    ) -> None:
        if spec.id in self._sources:
            raise ValueError(f"two sources share the id {spec.id}")
        settings = self._settings.sources.get(spec.id) or SourceSettings()
        self._sources[spec.id] = RegisteredSource(spec, adapter_cls, settings, instance)

    def _add_instances(self, kinds: dict[str, _Kind]) -> None:
        configured: set[str] = set()
        for instance_id, cfg in sorted(self._settings.sources.items()):
            fields: dict[str, Any] = dict(cfg.model_extra or {})
            kind_id = fields.pop("instance_of", None)
            if kind_id is None:
                continue
            kind = kinds.get(kind_id)
            if kind is None:
                _log.warning("instance of an unknown kind", extra={"source": instance_id})
                continue
            configured.add(kind_id)
            self._add_instance(kind, instance_id, fields)
        for kind_id, kind in kinds.items():
            if kind_id not in configured:
                self._add(kind.base, kind.adapter_cls, None)
                self._needs_instance.add(kind_id)

    def _add_instance(self, kind: _Kind, instance_id: str, fields: dict[str, Any]) -> None:
        """One source from one settings entry; an invalid entry is listed ``unconfigured``."""
        try:
            instance = kind.model.model_validate(fields)
            spec = kind.build(kind.base, instance_id, instance)
        except ValueError as exc:
            names = (
                [".".join(map(str, e["loc"])) for e in exc.errors()]
                if isinstance(exc, ValidationError)
                else []
            )
            # Field names only: a rejected value may be a URL the owner considers private.
            _log.warning(
                "invalid instance settings", extra={"source": instance_id, "fields": names}
            )
            try:
                spec = dataclasses.replace(kind.base, id=instance_id, instance_of=kind.base.id)
            except ValueError:
                _log.warning("invalid instance id", extra={"source": kind.base.id})
                return
            self._add(spec, kind.adapter_cls, None)
            self._needs_instance.add(instance_id)
            return
        self._add(spec, kind.adapter_cls, instance)

    def all(self) -> list[RegisteredSource]:
        return [self._sources[source] for source in sorted(self._sources)]

    def get(self, id: str) -> RegisteredSource | None:
        return self._sources.get(id)

    def by_group(self, group: str) -> list[RegisteredSource]:
        return [source for source in self.all() if source.spec.group == group]

    def policy(self, source: str) -> SourcePolicy:
        """The ``PolicyResolver`` of the HTTP client; an unknown source may call nothing."""
        registered = self._sources.get(source)
        if registered is None:
            raise HttpError(ErrorCode.BLOCKED_BY_POLICY)
        return registered.spec.policy(daily_quota=registered.settings.budget_cap)

    def select(
        self,
        groups: Iterable[str] | None,
        capability: Capability,
        filters: SearchFilters | None = None,
        explicit: Iterable[str] | None = None,
    ) -> list[Selected]:
        """The candidate sources with their skips; a source with a skip is never called.

        ``explicit`` ids win over ``groups``; with neither, the default groups without
        ``web``. ``filters`` go to the adapters and do not change selection.
        """
        named = list(dict.fromkeys(explicit or ()))
        if named:
            unknown = [source for source in named if source not in self._sources]
            if unknown:
                raise ToolError(ErrorCode.INVALID_ARGUMENT, f"unknown source: {unknown[0]}")
            chosen = [self._sources[source] for source in named]
        else:
            wanted = set(groups or ())
            if not wanted:
                wanted = set(self._settings.federation.default_groups) - {"web"}
            chosen = [source for source in self.all() if source.spec.group in wanted]
        selected: list[Selected] = []
        for source in chosen:
            if capability not in source.spec.capabilities:
                continue
            own = self._own_skip(source)
            state = own.state if own is not None else None
            if state is None and not named:
                # An explicit request for an unhealthy source tries it once (SRCH-FR-8).
                state = self._health_skip(source.spec.id)
            skip = None if state is None else SourceStatus(source=source.spec.id, state=state)
            selected.append(Selected(source.spec.id, self._adapter(source), skip))
        return selected

    def view(self, id: str | None = None) -> list[SourceView]:
        if id is None:
            return [self._view(source) for source in self.all()]
        source = self._sources.get(id)
        if source is None:
            raise ToolError(ErrorCode.INVALID_ARGUMENT, f"unknown source: {id}")
        return [self._view(source)]

    def _adapter(self, source: RegisteredSource) -> SourceAdapter:
        adapter = self._adapters.get(source.spec.id)
        if adapter is None:
            adapter = source.adapter_cls(source.spec, self._ctx_factory(source.spec))
            self._adapters[source.spec.id] = adapter
        return adapter

    def _enabled(self, source: RegisteredSource) -> bool:
        enabled = source.settings.enabled
        return source.spec.enabled_by_default if enabled is None else enabled

    # @spec SRC-3, SRC-4, SRC-5
    def _own_skip(self, source: RegisteredSource) -> _Skip | None:
        """Rows 1 to 6 of the selection table; the first match wins."""
        spec = source.spec
        if not self._enabled(source):
            return _Skip(
                "disabled",
                "Disabled in settings.",
                f"Enable it with `research-mcp config set sources.{spec.id}.enabled true`",
            )
        return self._unconfigured(source) or self._budget_skip(source)

    def _unconfigured(self, source: RegisteredSource) -> _Skip | None:
        spec = source.spec
        extra = next((e for e in sorted(spec.extras) if not self._has_extra(e)), None)
        if extra is not None:
            return _Skip(
                "unconfigured",
                f"The optional extra `{extra}` is not installed.",
                f"Install the extra: `uv tool install 'research-mcp[{extra}]'`",
            )
        if spec.auth is not None and spec.auth.required:
            name = next((n for n in spec.auth.secrets if not self._has_credential(n)), None)
            if name is not None:
                return _Skip(
                    "unconfigured",
                    f"Keychain item `research-mcp/{name}` is missing.",
                    f"Add Keychain item `research-mcp/{name}` "
                    f"(sign up: `{spec.auth.signup_url}`): "
                    f'`security add-generic-password -U -s research-mcp/{name} -a "$USER" -w`',
                )
        if spec.needs_contact and not self._settings.contact.email:
            return _Skip(
                "unconfigured",
                "`contact.email` is not set.",
                "Set `contact.email` to your own address: "
                "`research-mcp config set contact.email <address>`",
            )
        if spec.id in self._needs_instance:
            name, kind = (
                ("<name>", spec.id) if spec.instance_of is None else (spec.id, spec.instance_of)
            )
            return _Skip(
                "unconfigured",
                "No valid instance settings.",
                f'Add or complete `sources.{name}` (`instance_of = "{kind}"`)',
            )
        return None

    def _budget_skip(self, source: RegisteredSource) -> _Skip | None:
        cap = source.settings.budget_cap
        if cap is not None and self._calls_today(source.spec.id) >= cap:
            return _Skip("budget_exhausted", "Daily cap reached; resets at local midnight.", None)
        return None

    def _health_skip(self, source: str) -> SkipState | None:
        """Health ``down`` or ``rate_limited`` is ``skipped_unhealthy`` (M0-plan-v4 2.2)."""
        state = self._health(source)
        if state is None:
            return None
        name = state.partition("(")[0]
        if name in ("down", "rate_limited"):
            return "skipped_unhealthy"
        if name == "budget_exhausted":
            return "budget_exhausted"
        return None

    def _view(self, source: RegisteredSource) -> SourceView:
        spec, cap = source.spec, source.settings.budget_cap
        own = self._own_skip(source)
        state = own.state if own is not None else (self._health(spec.id) or "ok")
        now = self._clock.now()
        return SourceView(
            id=spec.id,
            title=spec.title,
            group=spec.group,
            capabilities=tuple(sorted(c.value for c in spec.capabilities)),
            state=state,
            reason=None if own is None else own.reason,
            fix_hint=None if own is None else own.fix_hint,
            enabled=self._enabled(source),
            shutdown_on=spec.shutdown_on,
            deprecated_days=spec.deprecated_days(now.astimezone().date()),
            signup_url=spec.auth.signup_url or None if spec.auth is not None else None,
            docs_url=spec.docs_url or None,
            budget_cap=cap,
            calls_today=None if cap is None else self._calls_today(spec.id),
            budget_reset_at=None if cap is None else next_local_midnight(now),
        )
