"""The stdio shim against an in-process daemon (LLD-platform-v2 2.3, 5.7)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest
from mcp import types
from mcp.client.session import ClientSession
from mcp.shared.exceptions import McpError
from mcp.shared.memory import create_client_server_memory_streams
from mcp.shared.message import SessionMessage
from starlette.applications import Starlette

from research_mcp.app import build_app
from research_mcp.platform.secrets import FakeProvider
from research_mcp.settings import Settings
from research_mcp.shim import DAEMON_LABEL, UNREACHABLE_MESSAGE, Shim, SystemLaunchctl
from research_mcp.testing.adapters import FAKE_SPEC, FIXTURES, FakeAdapter
from research_mcp.testing.clock import FakeClock, FakeSleeper
from research_mcp.testing.launchctl import FakeLaunchctl

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
TOKEN = "daemon-token-0123456789abcdefghijklmnopqrstuv"


class OfflineSettings(Settings):
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


def fake_upstream(request: httpx.Request) -> httpx.Response:
    """The fake source's API, from its recorded fixture, with the body unread like a socket's."""
    assert request.url.host == "api.fake-source.org"
    return httpx.Response(200, stream=httpx.ByteStream(FIXTURES["search_ok"][1]))


def make_app(settings: Settings) -> Starlette:
    clock = FakeClock(NOW)
    return build_app(
        settings,
        secrets=FakeProvider({"DAEMON_TOKEN": TOKEN}),
        transport=httpx.MockTransport(fake_upstream),
        clock=clock,
        sleeper=FakeSleeper(clock),
        adapters=[(FAKE_SPEC, FakeAdapter)],
    )


class Daemon(httpx.AsyncBaseTransport):
    """The loopback daemon as the shim sees it: up or down, and replaceable (a restart)."""

    def __init__(self, app: Starlette | None = None) -> None:
        self.app = app
        self.up = app is not None
        self.session_errors = 0
        self.requests: list[dict[str, Any]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if not self.up or self.app is None:
            raise httpx.ConnectError("connection refused", request=request)
        if request.url.path.startswith("/mcp"):
            body = json.loads(await request.aread())
            self.requests.append({"auth": request.headers.get("authorization"), **body})
            replayed = body.get("method") in {"initialize", "notifications/initialized"}
            if self.session_errors and not replayed:
                self.session_errors -= 1
                return httpx.Response(404, json={"error": "session not found"})
        inner = httpx.ASGITransport(app=self.app)
        return await inner.handle_async_request(request)

    def methods(self) -> list[str]:
        return [str(item.get("method")) for item in self.requests]


@asynccontextmanager
async def daemon_running(app: Starlette) -> AsyncIterator[Starlette]:
    async with app.router.lifespan_context(app):
        yield app


@asynccontextmanager
async def shim_session(shim: Shim) -> AsyncIterator[ClientSession]:
    async with (
        create_client_server_memory_streams() as (client_streams, shim_streams),
        anyio.create_task_group() as tasks,
    ):
        tasks.start_soon(shim.relay, shim_streams[0], shim_streams[1])
        try:
            async with ClientSession(client_streams[0], client_streams[1]) as client:
                yield client
        finally:
            tasks.cancel_scope.cancel()


def make_shim(
    settings: Settings, daemon: Daemon, launchctl: FakeLaunchctl, sleeper: FakeSleeper
) -> Shim:
    return Shim(
        settings,
        provider=FakeProvider({"DAEMON_TOKEN": TOKEN}),
        launchctl=launchctl,
        sleeper=sleeper,
        transport=daemon,
    )


def result_text(result: types.CallToolResult) -> dict[str, Any]:
    block = result.content[0]
    assert isinstance(block, types.TextContent)
    return dict(json.loads(block.text))


async def test_full_mcp_session_through_shim(tmp_path: Path) -> None:
    """@spec PLAT-72: initialize, list tools and call search through the shim to the daemon."""
    settings = offline_settings(tmp_path)
    async with daemon_running(make_app(settings)) as app:
        daemon = Daemon(app)
        launchctl = FakeLaunchctl()
        shim = make_shim(settings, daemon, launchctl, FakeSleeper(FakeClock(NOW)))
        async with shim_session(shim) as client:
            init = await client.initialize()
            assert init.serverInfo.name == "research-mcp"
            tools = await client.list_tools()
            assert {"search", "get_work", "list_sources"} <= {tool.name for tool in tools.tools}
            found = await client.call_tool("search", {"query": "fake"})
            assert not found.isError
            body = result_text(found)
            assert [work["title"] for work in body["data"]] == ["A fake work"]
            assert [status["state"] for status in body["source_status"]] == ["ok"]

    assert daemon.methods() == [
        "initialize",
        "notifications/initialized",
        "tools/list",
        "tools/call",
    ]
    assert {item["auth"] for item in daemon.requests} == {f"Bearer {TOKEN}"}
    assert launchctl.starts == []  # the daemon was up, so launchd was not asked


async def test_down_daemon_starts_via_launchctl_then_one_error(tmp_path: Path) -> None:
    """@spec PLAT-73: a down daemon is started through launchd, retried, then one MCP error."""
    settings = offline_settings(tmp_path)
    daemon = Daemon()
    launchctl = FakeLaunchctl(loaded=True)
    clock = FakeClock(NOW)
    sleeper = FakeSleeper(clock)
    shim = make_shim(settings, daemon, launchctl, sleeper)
    request = types.JSONRPCRequest(jsonrpc="2.0", id=7, method="tools/list", params={})
    note = types.JSONRPCNotification(jsonrpc="2.0", method="notifications/initialized")

    async with (
        create_client_server_memory_streams() as (client_streams, shim_streams),
        anyio.create_task_group() as tasks,
    ):
        tasks.start_soon(shim.relay, shim_streams[0], shim_streams[1])
        read, write = client_streams
        await write.send(SessionMessage(types.JSONRPCMessage(request)))
        with anyio.fail_after(5):
            reply = await read.receive()
        await write.send(SessionMessage(types.JSONRPCMessage(note)))  # no reply for a note
        with anyio.move_on_after(0.2):
            extra = await read.receive()
            pytest.fail(f"a second message came back: {extra}")
        tasks.cancel_scope.cancel()

    assert isinstance(reply, SessionMessage)
    error = reply.message.root
    assert isinstance(error, types.JSONRPCError) and error.id == 7
    assert error.error.message == UNREACHABLE_MESSAGE
    assert error.error.data == {"code": "internal", "retryable": True}
    assert launchctl.starts == [("kickstart", DAEMON_LABEL)] * 3
    # Each start request is followed by 20 s of polling every 0.5 s on the injected sleeper.
    assert sleeper.sleeps[:40] == [0.5] * 40 and sum(sleeper.sleeps[:120]) == 60


async def test_unloaded_daemon_is_bootstrapped(tmp_path: Path) -> None:
    """@spec PLAT-73: when the job is not loaded the shim bootstraps the installed plist."""
    settings = offline_settings(tmp_path)
    async with daemon_running(make_app(settings)) as app:
        daemon = Daemon(app)
        daemon.up = False

        def start() -> None:
            daemon.up = True

        launchctl = FakeLaunchctl(loaded=False, on_start=start)
        shim = make_shim(settings, daemon, launchctl, FakeSleeper(FakeClock(NOW)))
        async with shim_session(shim) as client:
            await client.initialize()
            assert (await client.list_tools()).tools
    assert [call[0] for call in launchctl.starts] == ["bootstrap"]
    assert launchctl.starts[0][1].endswith(f"Library/LaunchAgents/{DAEMON_LABEL}.plist")


async def test_stateless_restart_and_initialize_replay(tmp_path: Path) -> None:
    """@spec PLAT-77: MCP is stateless, the shim survives a restart and replays initialize once."""
    settings = offline_settings(tmp_path)
    async with AsyncExitStack() as stack:
        first = await stack.enter_async_context(daemon_running(make_app(settings)))
        daemon = Daemon(first)
        launchctl = FakeLaunchctl()
        shim = make_shim(settings, daemon, launchctl, FakeSleeper(FakeClock(NOW)))
        client = await stack.enter_async_context(shim_session(shim))
        await client.initialize()
        assert (await client.list_tools()).tools

        # Stateless: the daemon issues no session id, so nothing ties the client to it.
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=first), base_url="http://127.0.0.1:7319"
        ) as direct:
            response = await direct.post(
                "/mcp/",
                headers={
                    "Authorization": f"Bearer {TOKEN}",
                    "Accept": "application/json, text/event-stream",
                },
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            )
        assert response.status_code == 200 and "mcp-session-id" not in response.headers

        # The daemon restarts: it is down, launchd brings up a new process.
        second = await stack.enter_async_context(daemon_running(make_app(settings)))
        daemon.up = False

        def restarted() -> None:
            daemon.app = second
            daemon.up = True

        launchctl.on_start = restarted
        assert (await client.list_tools()).tools
        assert launchctl.starts == [("kickstart", DAEMON_LABEL)]

        # A session error: the shim replays initialize once, then the call goes through.
        before = len(daemon.requests)
        daemon.session_errors = 1
        found = await client.call_tool("search", {"query": "fake"})
        assert not found.isError
        assert daemon.methods()[before:] == [
            "tools/call",
            "initialize",
            "notifications/initialized",
            "tools/call",
        ]

        # A second session error on the same request is not replayed again.
        before = len(daemon.requests)
        daemon.session_errors = 2
        with pytest.raises(McpError):
            await client.list_tools()
        assert daemon.methods()[before:] == [
            "tools/list",
            "initialize",
            "notifications/initialized",
            "tools/list",
        ]


async def test_system_launchctl_commands() -> None:
    """@spec PLAT-73: the real port asks launchd for the daemon job in the user's GUI domain."""
    seen: list[list[str]] = []

    def runner(returncode: int) -> Callable[..., Awaitable[Any]]:
        async def run(argv: list[str], **kwargs: Any) -> Any:
            seen.append(argv)
            assert kwargs.get("check") is False
            return type("Done", (), {"returncode": returncode})()

        return run

    port = SystemLaunchctl(uid=501, runner=runner(0))
    assert await port.is_loaded(DAEMON_LABEL)
    await port.kickstart(DAEMON_LABEL)
    await port.bootstrap(Path("/Users/me/Library/LaunchAgents/local.research-mcpd.plist"))
    await port.bootout(DAEMON_LABEL)
    await port.kill("SIGHUP", DAEMON_LABEL)
    assert seen == [
        ["/bin/launchctl", "print", f"gui/501/{DAEMON_LABEL}"],
        ["/bin/launchctl", "kickstart", f"gui/501/{DAEMON_LABEL}"],
        [
            "/bin/launchctl",
            "bootstrap",
            "gui/501",
            "/Users/me/Library/LaunchAgents/local.research-mcpd.plist",
        ],
        ["/bin/launchctl", "bootout", f"gui/501/{DAEMON_LABEL}"],
        ["/bin/launchctl", "kill", "SIGHUP", f"gui/501/{DAEMON_LABEL}"],
    ]
    assert not await SystemLaunchctl(uid=501, runner=runner(113)).is_loaded(DAEMON_LABEL)
