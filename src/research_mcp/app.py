"""The composition root: ``build_app(settings)`` and the auth gate (LLD-platform-v2 2.3, 4.5, 5.2).

Building the app creates nothing. Its lifespan creates every component in dependency order
(secrets, stores, the HTTP client, sources and services, the MCP session manager, jobs,
the scheduler) and closes them in reverse. One deny-by-default ``AuthGate`` stands in front
of every mount: the Host and Origin check on every path, then the credential the path's
request class needs (LLD-security-v2 4.3 E3, 5.2). The UI mounts arrive with the UI
component; until then every ``/ui`` path is refused, because no UI session can exist.
"""

from __future__ import annotations

import getpass
import json
import logging
import secrets as stdlib_secrets
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

import anyio
import httpx
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from research_mcp.core.models import CallRecord, Clock, Sleeper
from research_mcp.core.timeutil import SystemClock
from research_mcp.mcp_app.server import Services, build_mcp
from research_mcp.platform import auth
from research_mcp.platform.http import HttpClient
from research_mcp.platform.jobs import JobService
from research_mcp.platform.logging import rotate_stderr_log
from research_mcp.platform.redact import Redactor
from research_mcp.platform.scheduler import Every, Scheduler
from research_mcp.platform.secrets import (
    KeychainProvider,
    SecretCache,
    SecretProvider,
    SecretRef,
    SecretState,
)
from research_mcp.platform.stores import (
    CACHE_MIGRATIONS,
    STATE_MIGRATIONS,
    CacheStore,
    Database,
    Migrator,
    StateStore,
)
from research_mcp.services.federation import FederationService
from research_mcp.services.works import WorksService
from research_mcp.settings import Settings, SourceSettings
from research_mcp.sources.base import SourceAdapter, SourceContext, SourceSpec
from research_mcp.sources.registry import SourceRegistry
from research_mcp.version import __version__

_log = logging.getLogger(__name__)

FLUSH_S = 1.0
LOG_ROTATE_S = 15 * 60
READY_TICK_MAX = timedelta(minutes=3)
STDERR_LOG = "daemon.err.log"
_UNREADABLE = (SecretState.LOCKED, SecretState.ERROR)

CredentialsChanged = Callable[[list[str]], Awaitable[None]]


async def _nothing_changed(names: list[str]) -> None:
    """The default ``credentials_changed`` port; the health component replaces it."""


@dataclass
class Runtime:
    """Everything the lifespan created; ``None`` until it runs."""

    settings: Settings
    redactor: Redactor
    clock: Clock
    refs: dict[str, SecretRef] = field(default_factory=dict)
    secrets: SecretCache | None = None
    state: StateStore | None = None
    cache: CacheStore | None = None
    http: HttpClient | None = None
    registry: SourceRegistry | None = None
    services: Services | None = None
    mcp_asgi: ASGIApp | None = None
    jobs: JobService | None = None
    scheduler: Scheduler | None = None
    credentials_changed: CredentialsChanged = _nothing_changed


class _StoreSink:
    """The HTTP client's ``CallSink``: buffered in ``StateStore``, flushed every second."""

    def __init__(self, state: StateStore) -> None:
        self._state = state

    def record(self, call: CallRecord) -> None:
        self._state.record_call(call)


def _bracket(host: str) -> str:
    return f"[{host}]" if ":" in host else host


class AuthGate:
    """One deny-by-default gate in front of every mount (LLD-security-v2 E3, 5.2).

    Order: Host and Origin, then the request class. ``/healthz`` and ``/readyz`` need no
    credential; ``/mcp`` and ``/api`` need the bearer token, read from ``SecretCache`` on
    each request so a reload changes which token is valid; ``/ui`` needs a UI session or
    the login token, which do not exist before the UI component; any other path needs the
    bearer token and then gets the router's 404.
    """

    def __init__(self, app: ASGIApp, runtime: Runtime) -> None:
        self.app = app
        self.runtime = runtime
        server = runtime.settings.server
        hosts = {f"127.0.0.1:{server.port}", f"localhost:{server.port}"}
        hosts.add(f"{_bracket(server.host)}:{server.port}")
        self.hosts = frozenset(hosts)
        self.origins = frozenset(f"http://{host}" for host in hosts)

    # @spec SEC-11, SEC-12
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return
        if scope["type"] != "http":
            await send({"type": "websocket.close", "code": 1008})
            return
        headers = Headers(scope=scope)
        origin = headers.get("origin")
        host = headers.get("host", "").lower()
        if host not in self.hosts or (origin is not None and origin.lower() not in self.origins):
            await _refuse(403, "forbidden")(scope, receive, send)
            return
        path: str = scope["path"]
        if path in ("/healthz", "/readyz"):
            await self.app(scope, receive, send)
            return
        if path == "/ui" or path.startswith("/ui/") or not self._bearer_ok(headers):
            await _refuse(401, "unauthorized")(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def _bearer_ok(self, headers: Headers) -> bool:
        scheme, _, token = headers.get("authorization", "").partition(" ")
        cache = self.runtime.secrets
        if scheme.lower() != "bearer" or cache is None:
            return False
        return auth.token_matches(token.strip(), cache.get(auth.DAEMON_TOKEN))


def _refuse(status: int, error: str) -> Response:
    extra = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return JSONResponse({"error": error}, status_code=status, headers=extra)


def _secret_refs(
    settings: Settings, registry: SourceRegistry
) -> tuple[dict[str, SecretRef], dict[str, str]]:
    """The daemon token and every Keychain item a source declares, from validated settings."""
    refs = {auth.DAEMON_TOKEN: SecretRef.parse(settings.server.token)}
    sources: dict[str, str] = {}
    for source in registry.all():
        spec_auth = source.spec.auth
        if spec_auth is None:
            continue
        for name in spec_auth.secrets:
            refs.setdefault(name, SecretRef("keychain", name, f"research-mcp/{name}"))
        if spec_auth.secrets:
            sources[source.spec.id] = spec_auth.secrets[0]
    return refs, sources


class _AnyioSleeper:
    async def sleep(self, seconds: float) -> None:
        await anyio.sleep(seconds)


# @spec PLAT-70, PLAT-75
def build_app(
    settings: Settings,
    *,
    secrets: SecretProvider | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    clock: Clock | None = None,
    sleeper: Sleeper | None = None,
    adapters: Iterable[tuple[SourceSpec, type[SourceAdapter]]] | None = None,
    launchctl: Any | None = None,
    redactor: Redactor | None = None,
) -> Starlette:
    """The daemon's Starlette app. The keyword arguments are the test seams.

    The daemon passes only ``redactor`` (the one its logging uses) and so gets the real
    Keychain, network, clock and discovered adapters. No signal handler is installed here.
    """
    runtime = Runtime(settings, redactor or Redactor(), clock or SystemClock())
    reload_lock = anyio.Lock()

    # @spec SEC-4
    async def reload_credentials() -> list[str]:
        """Re-read the secrets; register and report the names whose fingerprint changed."""
        async with reload_lock:
            cache = runtime.secrets
            if cache is None:
                return []
            changed = await anyio.to_thread.run_sync(cache.reload)
            for name in changed:
                runtime.redactor.register(cache.get(name))
            await runtime.credentials_changed(changed)
            _log.info("credentials.reloaded: %s", ", ".join(changed) or "none")
            return changed

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            await _start(
                runtime,
                stack,
                provider=secrets,
                transport=transport,
                sleeper=sleeper or _AnyioSleeper(),
                adapters=adapters,
            )
            yield

    async def mcp_endpoint(scope: Scope, receive: Receive, send: Send) -> None:
        target = runtime.mcp_asgi
        if target is None:
            await _refuse(503, "starting")(scope, receive, send)
            return
        await target(scope, receive, send)

    app = Starlette(
        routes=[
            Route("/healthz", _healthz, methods=["GET"]),
            Route("/readyz", _readyz_for(runtime), methods=["GET"]),
            Route("/api/status", _status_for(runtime), methods=["GET"]),
            Mount("/mcp", app=mcp_endpoint),
        ],
        middleware=[Middleware(AuthGate, runtime=runtime)],
        lifespan=lifespan,
    )
    app.state.runtime = runtime
    app.state.reload_credentials = reload_credentials
    app.state.launchctl = launchctl
    return app


async def _start(
    runtime: Runtime,
    stack: AsyncExitStack,
    *,
    provider: SecretProvider | None,
    transport: httpx.AsyncBaseTransport | None,
    sleeper: Sleeper,
    adapters: Iterable[tuple[SourceSpec, type[SourceAdapter]]] | None,
) -> None:
    """Create every component in order; ``stack`` closes them in reverse."""
    settings, clock = runtime.settings, runtime.clock

    def context(spec: SourceSpec) -> SourceContext:
        if runtime.http is None:  # adapters are built on first selection, after the client
            raise RuntimeError("the HTTP client is not open")
        return SourceContext(
            http=runtime.http,
            mcp=None,
            settings=settings.sources.get(spec.id) or SourceSettings(),
            clock=clock,
            contact_email=settings.contact.email,
        )

    def has_credential(name: str) -> bool:
        return runtime.secrets is not None and runtime.secrets.get(name) is not None

    registry = SourceRegistry(
        settings,
        context,
        has_credential=has_credential,
        clock=clock,
        modules=None if adapters is None else [],
        extra_adapters=adapters or (),
    )
    refs, by_source = _secret_refs(settings, registry)
    cache = SecretCache(provider or KeychainProvider(getpass.getuser()), refs, by_source)
    await anyio.to_thread.run_sync(cache.load)
    for name in refs:
        runtime.redactor.register(cache.get(name))
    runtime.refs, runtime.secrets = refs, cache

    paths = settings.paths
    state = StateStore(await _open(stack, Path(paths.state_dir) / "state.db", STATE_MIGRATIONS))
    store = CacheStore(await _open(stack, Path(paths.data_dir) / "cache.db", CACHE_MIGRATIONS))
    runtime.state, runtime.cache = state, store

    http = HttpClient(
        registry, cache, _StoreSink(state), clock, sleeper, settings.contact.email, transport
    )
    stack.push_async_callback(http.aclose)
    runtime.http, runtime.registry = http, registry

    token = cache.get(auth.DAEMON_TOKEN)
    # Without a daemon token no request passes the gate, so a random key loses nothing.
    key = auth.cursor_key(token) if token is not None else stdlib_secrets.token_bytes(32)
    services = Services(
        settings=settings,
        registry=registry,
        federation=FederationService(registry, settings, key),
        works=WorksService(registry, settings),
        redactor=runtime.redactor,
    )
    mcp = build_mcp(services)
    mcp_asgi = mcp.streamable_http_app()
    await stack.enter_async_context(mcp.session_manager.run())
    runtime.services, runtime.mcp_asgi = services, mcp_asgi
    stack.callback(setattr, runtime, "mcp_asgi", None)

    runtime.jobs = await stack.enter_async_context(JobService(state, clock))

    scheduler = Scheduler(state, clock)
    stderr_log = Path(paths.log_dir) / STDERR_LOG

    async def log_rotate() -> None:
        await anyio.to_thread.run_sync(rotate_stderr_log, stderr_log)

    scheduler.add("log_rotate", Every(LOG_ROTATE_S), log_rotate)
    runtime.scheduler = scheduler

    stack.push_async_callback(_flush, state)  # after the loops stop, before the stores close
    tasks = await stack.enter_async_context(anyio.create_task_group())
    stack.callback(tasks.cancel_scope.cancel)
    await tasks.start(scheduler.run)
    tasks.start_soon(_flush_every_second, state)


async def _open(stack: AsyncExitStack, path: Path, migrations: Path) -> Database:
    db = Database(path)
    await db.open(Migrator(migrations))
    stack.push_async_callback(db.close)
    return db


async def _flush(state: StateStore) -> None:
    try:
        await state.flush()
    except Exception:  # noqa: BLE001 - telemetry loss is a warning, never a crash
        _log.warning("calls.flush_failed", extra={"operation": "flush"})


async def _flush_every_second(state: StateStore) -> None:
    while True:
        await anyio.sleep(FLUSH_S)
        await _flush(state)


async def _healthz(request: Request) -> Response:
    return JSONResponse({"status": "ok", "version": __version__})


def _readyz_for(runtime: Runtime) -> Callable[[Request], Awaitable[Response]]:
    async def readyz(request: Request) -> Response:
        """200 when the stores answer, the scheduler ticked recently and the Keychain reads."""
        checks = {
            "stores": await _stores_ok(runtime),
            "scheduler": _scheduler_ok(runtime),
            "keychain": _keychain_ok(runtime),
        }
        if all(checks.values()):
            return JSONResponse({"status": "ok", "checks": checks})
        failed = [name for name, ok in checks.items() if not ok]
        return JSONResponse({"status": "not_ready", "failed": failed}, status_code=503)

    return readyz


async def _stores_ok(runtime: Runtime) -> bool:
    if runtime.state is None or runtime.cache is None:
        return False
    try:
        await runtime.state.schedule_get("log_rotate")
        await runtime.cache.outbox_drain(1)
    except Exception:  # noqa: BLE001 - any failure means not ready
        return False
    return True


def _scheduler_ok(runtime: Runtime) -> bool:
    scheduler = runtime.scheduler
    if scheduler is None or not scheduler.running or scheduler.last_tick is None:
        return False
    return runtime.clock.now() - scheduler.last_tick < READY_TICK_MAX


def _keychain_ok(runtime: Runtime) -> bool:
    """The states cached at start and by each reload; no new Keychain call per request."""
    cache = runtime.secrets
    if cache is None:
        return False
    return all(cache.state(name) not in _UNREADABLE for name in runtime.refs)


def _status_for(runtime: Runtime) -> Callable[[Request], Awaitable[Response]]:
    async def status(request: Request) -> Response:
        """Sources and jobs, redacted; the health component adds the rest of StatusReport."""
        registry, jobs = runtime.registry, runtime.jobs
        if registry is None or jobs is None:
            return _refuse(503, "starting")
        payload = {
            "version": __version__,
            "sources": [{"id": view.id, "state": view.state} for view in registry.view()],
            "jobs": [
                job.model_dump(mode="json", include={"job_id", "kind", "state", "progress"})
                for job in await jobs.list()
            ],
        }
        text = runtime.redactor.redact(json.dumps(payload))
        return Response(text, media_type="application/json")

    return status
