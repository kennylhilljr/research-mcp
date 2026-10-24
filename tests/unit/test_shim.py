"""Where the stdio shim gets the daemon token (LLD-platform-v2 4.7, 5.7; LLD-security-v2 E30)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from mcp import types

from research_mcp import shim as shim_module
from research_mcp.platform.secrets import FakeProvider, SecretState
from research_mcp.settings import Settings
from research_mcp.shim import AUTH_FAILED_MESSAGE, Shim
from research_mcp.testing.clock import FakeClock, FakeSleeper
from research_mcp.testing.launchctl import FakeLaunchctl

KEYCHAIN_TOKEN = "keychain-token-0123456789abcdefghijklmnopqrstuv"
ROTATED_TOKEN = "rotated-token-0123456789abcdefghijklmnopqrstuvw"
DECOY_TOKEN = "decoy-token-0123456789abcdefghijklmnopqrstuvwxyz"
SERVICE = "research-mcp/DAEMON_TOKEN"


class OfflineSettings(Settings):
    """Settings from init arguments only, so the test reads no real config file."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


class Daemon(httpx.AsyncBaseTransport):
    """A ready daemon that accepts only ``accepted`` bearer tokens and records each one."""

    def __init__(self, accepted: set[str]) -> None:
        self.accepted = accepted
        self.bearers: list[str | None] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/readyz":
            return httpx.Response(200, json={"status": "ready"})
        body = json.loads(await request.aread())
        bearer = request.headers.get("authorization")
        self.bearers.append(bearer)
        if bearer not in {f"Bearer {token}" for token in self.accepted}:
            return httpx.Response(401, json={"error": "unauthorized"})
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": {}})


def ping(request_id: int = 1) -> types.JSONRPCMessage:
    return types.JSONRPCMessage(types.JSONRPCRequest(jsonrpc="2.0", id=request_id, method="ping"))


def make_shim(provider: FakeProvider, daemon: Daemon) -> Shim:
    return Shim(
        OfflineSettings(),
        provider=provider,
        launchctl=FakeLaunchctl(),
        sleeper=FakeSleeper(FakeClock()),
        transport=daemon,
    )


def keychain_reads(provider: FakeProvider) -> list[list[str]]:
    return [argv for argv in provider.argv if SERVICE in argv and "-w" in argv]


async def test_shim_reads_daemon_token_only_from_keychain(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """@spec SEC-26: the shim sends the Keychain token and ignores decoys outside the Keychain."""
    for name in ("DAEMON_TOKEN", "RESEARCH_MCP_DAEMON_TOKEN", "RESEARCH_MCP_TOKEN", "MCP_TOKEN"):
        monkeypatch.setenv(name, DECOY_TOKEN)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "DAEMON_TOKEN").write_text(DECOY_TOKEN)
    provider = FakeProvider({"DAEMON_TOKEN": KEYCHAIN_TOKEN}, environ={"DAEMON_TOKEN": DECOY_TOKEN})
    daemon = Daemon({KEYCHAIN_TOKEN, DECOY_TOKEN})

    reply = await make_shim(provider, daemon).handle(ping())

    assert reply is not None and isinstance(reply.root, types.JSONRPCResponse)
    assert daemon.bearers == [f"Bearer {KEYCHAIN_TOKEN}"]
    assert keychain_reads(provider) == [
        ["/usr/bin/security", "find-generic-password", "-s", SERVICE, "-a", "tester", "-w"]
    ]


def test_shim_builds_keychain_provider_for_settings_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """@spec SEC-26: with no injected provider the shim reads ``server.token`` from the Keychain."""
    built: list[str] = []

    def keychain_provider(user: str) -> FakeProvider:
        built.append(user)
        return FakeProvider(user=user)

    monkeypatch.setattr(shim_module, "KeychainProvider", keychain_provider)
    monkeypatch.setattr(shim_module.getpass, "getuser", lambda: "owner")

    Shim(OfflineSettings())

    assert built == ["owner"]


@pytest.mark.parametrize("state", [SecretState.MISSING, SecretState.LOCKED])
async def test_shim_has_no_fallback_when_keychain_has_no_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, state: SecretState
) -> None:
    """@spec SEC-26: with no readable Keychain token the shim sends nothing, despite decoys."""
    for name in ("DAEMON_TOKEN", "RESEARCH_MCP_DAEMON_TOKEN", "RESEARCH_MCP_TOKEN", "MCP_TOKEN"):
        monkeypatch.setenv(name, DECOY_TOKEN)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "DAEMON_TOKEN").write_text(DECOY_TOKEN)
    provider = FakeProvider(environ={"DAEMON_TOKEN": DECOY_TOKEN})
    if state is not SecretState.MISSING:
        provider.items["DAEMON_TOKEN"] = KEYCHAIN_TOKEN
        provider.states["DAEMON_TOKEN"] = state
    daemon = Daemon({DECOY_TOKEN})

    reply = await make_shim(provider, daemon).handle(ping(3))

    assert reply is not None and isinstance(reply.root, types.JSONRPCError)
    assert reply.root.error.data == {"code": "auth_failed", "retryable": False}
    assert daemon.bearers == []
    assert keychain_reads(provider)


async def test_shim_rereads_keychain_token_once_on_401() -> None:
    """@spec SEC-26: a 401 re-reads the Keychain token once and retries with the rotated value."""
    provider = FakeProvider({"DAEMON_TOKEN": KEYCHAIN_TOKEN})
    daemon = Daemon({KEYCHAIN_TOKEN})
    shim = make_shim(provider, daemon)
    assert isinstance((await shim.handle(ping(1))), types.JSONRPCMessage)

    provider.items["DAEMON_TOKEN"] = ROTATED_TOKEN
    daemon.accepted = {ROTATED_TOKEN}
    reply = await shim.handle(ping(2))

    assert reply is not None and isinstance(reply.root, types.JSONRPCResponse)
    assert daemon.bearers == [
        f"Bearer {KEYCHAIN_TOKEN}",
        f"Bearer {KEYCHAIN_TOKEN}",
        f"Bearer {ROTATED_TOKEN}",
    ]
    assert len(keychain_reads(provider)) == 2


async def test_shim_returns_auth_failed_after_second_401() -> None:
    """@spec SEC-26: a second 401 after the one re-read returns ``auth_failed``."""
    provider = FakeProvider({"DAEMON_TOKEN": KEYCHAIN_TOKEN})
    daemon = Daemon(set())

    reply = await make_shim(provider, daemon).handle(ping(7))

    assert reply is not None and isinstance(reply.root, types.JSONRPCError)
    error = reply.root.error
    assert error.message == AUTH_FAILED_MESSAGE
    assert error.data == {"code": "auth_failed", "retryable": False}
    assert reply.root.id == 7
    assert len(daemon.bearers) == 2
    assert len(keychain_reads(provider)) == 2
