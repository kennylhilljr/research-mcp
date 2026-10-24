"""The composition root and the daemon (LLD-platform-v2 2.3, 4.5, 5.2, 5.10)."""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest
from starlette.applications import Starlette

from research_mcp import daemon
from research_mcp.app import build_app
from research_mcp.core.ids import Identifier
from research_mcp.core.models import Provenance, SearchPage, SearchRequest, WorkRecord
from research_mcp.core.specs import RateSpec
from research_mcp.platform.secrets import FakeProvider, SecretState
from research_mcp.settings import ServerSettings, Settings
from research_mcp.sources.base import Capability, SourceContext, SourceSpec
from research_mcp.testing.clock import FakeClock, FakeSleeper
from research_mcp.version import __version__

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
TOKEN = "daemon-token-0123456789abcdefghijklmnopqrstuv"
BASE = "http://127.0.0.1:7319"
MCP_HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


class OfflineSettings(Settings):
    """Settings from keyword arguments only: no config file, no environment."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


def offline_settings(tmp_path: Path) -> Settings:
    settings = OfflineSettings(
        paths={
            "state_dir": tmp_path / "state",
            "data_dir": tmp_path / "state" / "cache",
            "model_cache_dir": tmp_path / "models",
            "log_dir": tmp_path / "logs",
        }
    )
    settings.paths.create_directories()
    return settings


SLOW_SPEC_ARGS: dict[str, Any] = {
    "title": "Slow source",
    "group": "scholarly",
    "capabilities": frozenset({Capability.SEARCH, Capability.GET}),
    "id_schemes": frozenset({"doi"}),
    "hosts": frozenset({"api.slow.org"}),
    "auth": None,
    "rate": RateSpec(rps=5.0),
}


class SlowAdapter:
    """A source that takes a second to answer, without blocking the loop."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec

    async def search(self, req: SearchRequest) -> SearchPage:
        await anyio.sleep(1.0)
        record = WorkRecord(
            ids=[Identifier("doi", "10.5555/slow.1")],
            title="A slow work",
            provenance=Provenance(
                source=self.spec.id, upstream_id="s1", adapter_version="1", retrieved_at=NOW
            ),
        )
        return SearchPage(records=[record])

    async def get(self, ident: Identifier) -> WorkRecord | None:
        return None


def make_app(
    settings: Settings, provider: FakeProvider | None = None, **kwargs: Any
) -> tuple[Starlette, FakeProvider]:
    provider = provider or FakeProvider({"DAEMON_TOKEN": TOKEN})
    kwargs.setdefault("adapters", [])
    kwargs.setdefault("clock", FakeClock(NOW))
    kwargs.setdefault("sleeper", FakeSleeper(kwargs["clock"]))
    return build_app(settings, secrets=provider, **kwargs), provider


@asynccontextmanager
async def running(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE) as client,
    ):
        yield client


async def test_lifespan_opens_and_closes_everything(tmp_path: Path) -> None:
    """@spec PLAT-70: build_app opens every component in its lifespan and closes them all."""
    settings = offline_settings(tmp_path)
    app, provider = make_app(settings)
    runtime = app.state.runtime
    assert runtime.state is None  # nothing is created when the app is built

    async with running(app) as client:
        assert runtime.secrets.state("DAEMON_TOKEN") is SecretState.OK
        assert runtime.redactor.redact(f"saw {TOKEN}") == "saw [REDACTED]"
        assert await runtime.state.job_list() == []
        assert await runtime.cache.outbox_drain(1) == []
        assert runtime.scheduler.running and runtime.jobs is not None
        assert runtime.services.registry.all() == []
        response = await client.post(
            "/mcp/",
            headers=MCP_HEADERS,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        assert response.status_code == 200
        assert "search" in {tool["name"] for tool in response.json()["result"]["tools"]}
        state_db, cache_db = runtime.state.db, runtime.cache.db
        http = runtime.http

    assert not runtime.scheduler.running
    assert http._client.is_closed
    for db in (state_db, cache_db):
        with pytest.raises(RuntimeError, match="not open"):
            async with db.read():
                pass
    # The migrations ran: both files exist at the schema version the code ships.
    for path in (tmp_path / "state" / "state.db", tmp_path / "state" / "cache" / "cache.db"):
        with sqlite3.connect(path) as conn:
            assert conn.execute("PRAGMA user_version").fetchone()[0] >= 1
    assert provider.argv  # the token was read through the provider, once at start


async def test_healthz_and_readyz(tmp_path: Path) -> None:
    """@spec PLAT-70: /healthz and /readyz answer without a credential; readyz checks parts."""
    settings = offline_settings(tmp_path)
    clock = FakeClock(NOW)
    app, provider = make_app(settings, clock=clock)
    async with running(app) as client:
        health = await client.get("/healthz")
        assert (health.status_code, health.json()) == (
            200,
            {"status": "ok", "version": __version__},
        )
        ready = await client.get("/readyz")
        assert ready.status_code == 200
        assert ready.json() == {
            "status": "ok",
            "checks": {"stores": True, "scheduler": True, "keychain": True},
        }

        provider.states["DAEMON_TOKEN"] = SecretState.LOCKED
        await app.state.reload_credentials()
        clock.advance(181)  # the scheduler's last tick is now over 3 minutes old
        ready = await client.get("/readyz")
        assert ready.status_code == 503
        assert ready.json() == {"status": "not_ready", "failed": ["scheduler", "keychain"]}
        await app.state.runtime.state.db.close()
        assert "stores" in (await client.get("/readyz")).json()["failed"]


async def test_event_loop_heartbeat_under_slow_source(tmp_path: Path) -> None:
    """@spec PLAT-75: while a slow source runs, the loop's heartbeat gap stays under 200 ms."""
    settings = offline_settings(tmp_path)
    spec = SourceSpec(id="slow", **SLOW_SPEC_ARGS)
    app, _ = make_app(settings, adapters=[(spec, SlowAdapter)])
    gaps: list[float] = []
    async with running(app) as client, anyio.create_task_group() as tasks:

        async def heartbeat() -> None:
            last = time.monotonic()
            while True:
                await anyio.sleep(0.01)
                now = time.monotonic()
                gaps.append(now - last)
                last = now

        tasks.start_soon(heartbeat)
        call = {"name": "search", "arguments": {"query": "slow things"}}
        response = await client.post(
            "/mcp/",
            headers=MCP_HEADERS,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": call},
        )
        tasks.cancel_scope.cancel()

    body = json.loads(response.json()["result"]["content"][0]["text"])
    assert [work["title"] for work in body["data"]] == ["A slow work"]
    assert len(gaps) > 50 and max(gaps) < 0.2


async def test_daemon_refuses_non_loopback_bind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """@spec PLAT-71: the daemon never binds a non-loopback address, even unvalidated."""
    for host in ("127.0.0.1", "::1", "127.5.6.7"):
        daemon.assert_loopback(host)
    for host in ("0.0.0.0", "10.0.0.2", "::", "example.org", "127.0.0.1%en0"):  # noqa: S104
        with pytest.raises(daemon.NotLoopbackError):
            daemon.assert_loopback(host)

    # A settings object built without validation still cannot reach uvicorn.
    bound: list[Any] = []

    async def no_bind(self: Any, *args: Any, **kwargs: Any) -> None:
        bound.append(self)

    monkeypatch.setattr("uvicorn.Server.serve", no_bind)
    settings = offline_settings(tmp_path)
    unchecked = settings.model_copy(
        update={"server": ServerSettings.model_construct(host="0.0.0.0", port=7319)}  # noqa: S104
    )
    app, _ = make_app(settings)
    with pytest.raises(daemon.NotLoopbackError):
        await daemon.serve(app, unchecked)
    assert bound == []

    # From the environment, validation stops the daemon before anything starts.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("RESEARCH_MCP_SERVER__HOST", "192.0.2.10")
    monkeypatch.setattr(daemon, "build_app", lambda *a, **k: pytest.fail("built an app"))
    assert daemon.main() == 2
    err = capsys.readouterr().err
    assert "server.host" in err and "192.0.2.10" not in err
    assert bound == []
