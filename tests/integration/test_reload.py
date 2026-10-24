"""Credential reload: ``reload_credentials`` and the SIGHUP receiver (LLD-platform-v2 5.10)."""

from __future__ import annotations

import logging
import os
import signal
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anyio
import httpx
import pytest
from starlette.applications import Starlette

from research_mcp import daemon
from research_mcp.app import build_app
from research_mcp.platform.secrets import FakeProvider, SecretState
from research_mcp.settings import Settings
from research_mcp.testing.clock import FakeClock, FakeSleeper

OLD = "old-daemon-token-0123456789abcdefghijklmnopq"
NEW = "new-daemon-token-0123456789abcdefghijklmnopq"
BASE = "http://127.0.0.1:7319"


class OfflineSettings(Settings):
    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


def make_app(tmp_path: Path, provider: FakeProvider) -> Starlette:
    settings = OfflineSettings(
        paths={
            "state_dir": tmp_path / "state",
            "data_dir": tmp_path / "state" / "cache",
            "model_cache_dir": tmp_path / "models",
            "log_dir": tmp_path / "logs",
        }
    )
    settings.paths.create_directories()
    clock = FakeClock(datetime(2026, 10, 24, 12, tzinfo=UTC))
    return build_app(
        settings, secrets=provider, adapters=[], clock=clock, sleeper=FakeSleeper(clock)
    )


@asynccontextmanager
async def running(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE) as client,
    ):
        yield client


async def status_code(client: httpx.AsyncClient, token: str) -> int:
    response = await client.get("/api/status", headers={"Authorization": f"Bearer {token}"})
    return response.status_code


async def test_reload_returns_changed_names_and_switches_the_token(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """@spec SEC-4: a reload re-reads secrets and returns the names whose fingerprints changed."""
    provider = FakeProvider({"DAEMON_TOKEN": OLD})
    app = make_app(tmp_path, provider)
    async with running(app) as client:
        assert await status_code(client, OLD) == 200
        reads = len(provider.argv)
        assert await app.state.reload_credentials() == []  # nothing changed: idempotent
        assert len(provider.argv) > reads  # but the Keychain was read again

        provider.items["DAEMON_TOKEN"] = NEW
        with caplog.at_level(logging.INFO, logger="research_mcp"):
            assert await app.state.reload_credentials() == ["DAEMON_TOKEN"]
        # The gate reads the token on each request, so the old one stops working.
        assert await status_code(client, OLD) == 401
        assert await status_code(client, NEW) == 200
        redactor = app.state.runtime.redactor
        assert redactor.redact(f"{OLD} {NEW}") == "[REDACTED] [REDACTED]"
        assert "DAEMON_TOKEN" in caplog.text
        assert OLD not in caplog.text and NEW not in caplog.text


async def test_locked_keychain_keeps_the_last_good_token(tmp_path: Path) -> None:
    """@spec SEC-4: a reload that finds the Keychain locked keeps the previous secret."""
    provider = FakeProvider({"DAEMON_TOKEN": OLD})
    app = make_app(tmp_path, provider)
    async with running(app) as client:
        provider.states["DAEMON_TOKEN"] = SecretState.LOCKED
        assert await app.state.reload_credentials() == []
        assert app.state.runtime.secrets.state("DAEMON_TOKEN") is SecretState.LOCKED
        assert await status_code(client, OLD) == 200

        provider.states.clear()
        del provider.items["DAEMON_TOKEN"]  # a missing item clears the value
        assert await app.state.reload_credentials() == ["DAEMON_TOKEN"]
        assert await status_code(client, OLD) == 401


async def test_sighup_runs_reload_and_a_failure_does_not_stop_the_daemon(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """@spec SEC-4: SIGHUP calls reload_credentials; a failing reload is a warning only."""
    calls: list[int] = []
    first, second = anyio.Event(), anyio.Event()

    async def reload_credentials() -> list[str]:
        calls.append(len(calls))
        if len(calls) == 1:
            first.set()
            raise RuntimeError("keychain exploded: token=abc123")
        second.set()
        return []

    app: Any = SimpleNamespace(state=SimpleNamespace(reload_credentials=reload_credentials))
    with caplog.at_level(logging.WARNING, logger="research_mcp"):
        async with anyio.create_task_group() as tasks:
            ready = anyio.Event()
            tasks.start_soon(daemon.reload_on_sighup, app, ready)
            await ready.wait()
            os.kill(os.getpid(), signal.SIGHUP)
            with anyio.fail_after(5):
                await first.wait()
            await anyio.sleep(0.05)  # let the receiver log the failure and wait again
            os.kill(os.getpid(), signal.SIGHUP)
            with anyio.fail_after(5):
                await second.wait()
            tasks.cancel_scope.cancel()
    assert calls == [0, 1]
    assert "reload_credentials.failed" in caplog.text
    assert "abc123" not in caplog.text and "exploded" not in caplog.text
