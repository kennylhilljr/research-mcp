"""The auth gate in front of every mount (LLD-security-v2 4.3 E3, 5.2; LLD-platform-v2 4.5)."""

from __future__ import annotations

import hmac
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from starlette.applications import Starlette

from research_mcp.app import build_app
from research_mcp.platform import auth
from research_mcp.platform.secrets import FakeProvider
from research_mcp.settings import Settings
from research_mcp.testing.clock import FakeClock, FakeSleeper

TOKEN = "daemon-token-0123456789abcdefghijklmnopqrstuv"
BASE = "http://127.0.0.1:7319"
LIST_TOOLS = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
ACCEPT = {"Accept": "application/json, text/event-stream"}


class OfflineSettings(Settings):
    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


def make_app(tmp_path: Path) -> Starlette:
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
        settings,
        secrets=FakeProvider({"DAEMON_TOKEN": TOKEN}),
        adapters=[],
        clock=clock,
        sleeper=FakeSleeper(clock),
    )


@asynccontextmanager
async def client_for(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    app = make_app(tmp_path)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE) as client,
    ):
        yield client


def bearer(token: str = TOKEN) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_mcp_and_api_need_the_bearer_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@spec SEC-11: /mcp and /api answer 401 without the bearer token; hmac.compare_digest."""
    compared: list[tuple[bytes, bytes]] = []
    real = hmac.compare_digest

    def spy(a: bytes, b: bytes) -> bool:
        compared.append((a, b))
        return real(a, b)

    monkeypatch.setattr(auth.hmac, "compare_digest", spy)
    async with client_for(tmp_path) as client:
        for headers in ({}, bearer("wrong"), bearer(TOKEN + "x"), {"Authorization": TOKEN}):
            mcp = await client.post("/mcp/", json=LIST_TOOLS, headers={**ACCEPT, **headers})
            assert mcp.status_code == 401, headers
            assert mcp.headers["www-authenticate"] == "Bearer"
            assert TOKEN not in mcp.text
            assert (await client.get("/api/status", headers=headers)).status_code == 401
        # The session cookie is never a credential for /mcp.
        cookie = {"Cookie": f"rmcp_session={TOKEN}"}
        assert (await client.post("/mcp/", json=LIST_TOOLS, headers=cookie)).status_code == 401

        compared.clear()
        mcp = await client.post("/mcp/", json=LIST_TOOLS, headers={**ACCEPT, **bearer()})
        assert mcp.status_code == 200 and mcp.json()["result"]["tools"]
        assert compared == [(TOKEN.encode(), TOKEN.encode())]
        status = await client.get("/api/status", headers=bearer())
        assert status.status_code == 200 and status.json()["sources"] == []

        # Deny by default: an unlisted path is 401 without a credential, 404 with one.
        assert (await client.get("/nothing-here")).status_code == 401
        assert (await client.get("/nothing-here", headers=bearer())).status_code == 404
        # The UI needs a UI session (or the one-time login token); a bearer is not one.
        for path in ("/ui/", "/ui/static/app.css", "/ui/login?t=abc", "/ui/jobs"):
            assert (await client.get(path, headers=bearer())).status_code == 401, path
        # Only /healthz and /readyz answer without a credential.
        assert (await client.get("/healthz")).status_code == 200
        assert (await client.get("/readyz")).status_code == 200


async def test_foreign_host_or_origin_is_refused(tmp_path: Path) -> None:
    """@spec SEC-12: a foreign Host or Origin is refused on every path, whatever the token."""
    async with client_for(tmp_path) as client:
        for path in ("/mcp/", "/api/status", "/healthz", "/readyz", "/ui/"):
            for headers in (
                {"Host": "evil.example:7319"},
                {"Host": "127.0.0.1:8080"},
                {"Host": "127.0.0.1"},
                {"Origin": "http://evil.example"},
                {"Origin": "http://127.0.0.1:8080"},
                {"Origin": "https://127.0.0.1:7319"},
                {"Origin": "null"},
            ):
                response = await client.get(path, headers={**bearer(), **headers})
                assert response.status_code == 403, (path, headers)

        local = {**ACCEPT, **bearer(), "Host": "localhost:7319", "Origin": "http://localhost:7319"}
        assert (await client.post("/mcp/", json=LIST_TOOLS, headers=local)).status_code == 200
        same = {**ACCEPT, **bearer(), "Origin": "http://127.0.0.1:7319"}
        assert (await client.post("/mcp/", json=LIST_TOOLS, headers=same)).status_code == 200


def test_daemon_token_helpers() -> None:
    """@spec SEC-11: the bearer comparison is on the encoded bytes and fails closed."""
    from research_mcp.platform.secrets import Secret, SecretRef

    secret = Secret(SecretRef.parse("keychain:research-mcp/DAEMON_TOKEN"), TOKEN)
    assert auth.token_matches(TOKEN, secret)
    assert not auth.token_matches(TOKEN[:-1], secret)
    assert not auth.token_matches("", secret)
    assert not auth.token_matches(TOKEN, None)
    assert not auth.token_matches("ünïcode", secret)
    assert auth.bearer_header(secret) == {"Authorization": f"Bearer {TOKEN}"}
    minted = auth.mint_token()
    assert len(minted) == 43 and "=" not in minted and minted != auth.mint_token()
    key = auth.cursor_key(secret)
    assert len(key) == 32 and key == auth.cursor_key(secret)
    other = Secret(secret.ref, TOKEN + "2")
    assert auth.cursor_key(other) != key
