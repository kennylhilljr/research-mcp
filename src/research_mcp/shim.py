"""``research-mcp stdio``: relays MCP from stdio to the daemon over HTTP (LLD-platform-v2 5.7).

The shim is the only way an MCP client reaches the daemon; no client holds the loopback URL
or the token. The token is read only from the Keychain, through ``settings.server.token``
(which validation keeps a ``keychain:`` reference), and revealed only by
``platform/auth.py``. When the daemon is down the shim asks launchd to start it, polls
``/readyz``, and after three start requests returns one MCP error. A 401 re-reads the
token once; a 404 or 400 replays ``initialize`` once.
"""

from __future__ import annotations

import getpass
import logging
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Protocol

import anyio
import httpx
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp import types
from mcp.shared.message import SessionMessage
from pydantic import ValidationError

from research_mcp.core.models import Sleeper
from research_mcp.platform import auth
from research_mcp.platform.secrets import KeychainProvider, Secret, SecretProvider, SecretRef
from research_mcp.settings import Settings

_log = logging.getLogger(__name__)

DAEMON_LABEL = "local.research-mcpd"
LAUNCHCTL = "/bin/launchctl"
POLL_S = 0.5
START_WAIT_S = 20.0
START_ATTEMPTS = 3
UNREACHABLE_MESSAGE = "The research-mcp daemon is not reachable; run `research-mcp doctor`."
AUTH_FAILED_MESSAGE = "The research-mcp daemon refused the token; run `research-mcp doctor`."
BAD_REPLY_MESSAGE = "The research-mcp daemon sent an unexpected reply; run `research-mcp doctor`."
ACCEPT = "application/json, text/event-stream"

ReadStream = MemoryObjectReceiveStream[SessionMessage | Exception]
WriteStream = MemoryObjectSendStream[SessionMessage]


class LaunchctlPort(Protocol):
    """What the shim, ``install`` and ``secrets rotate-token`` ask of launchd."""

    async def is_loaded(self, label: str) -> bool: ...
    async def kickstart(self, label: str) -> None: ...
    async def bootstrap(self, plist: Path) -> None: ...
    async def bootout(self, label: str) -> None: ...
    async def kill(self, signal_name: str, label: str) -> None: ...


Runner = Callable[..., Awaitable[Any]]


class SystemLaunchctl:
    """``/bin/launchctl`` in the user's GUI domain; no argument ever carries a secret."""

    def __init__(self, uid: int | None = None, runner: Runner = anyio.run_process) -> None:
        self._domain = f"gui/{os.getuid() if uid is None else uid}"
        self._runner = runner

    async def _run(self, *args: str) -> int:
        done = await self._runner([LAUNCHCTL, *args], check=False)
        return int(done.returncode)

    async def is_loaded(self, label: str) -> bool:
        return await self._run("print", f"{self._domain}/{label}") == 0

    async def kickstart(self, label: str) -> None:
        await self._run("kickstart", f"{self._domain}/{label}")

    async def bootstrap(self, plist: Path) -> None:
        await self._run("bootstrap", self._domain, str(plist))

    async def bootout(self, label: str) -> None:
        await self._run("bootout", f"{self._domain}/{label}")

    async def kill(self, signal_name: str, label: str) -> None:
        await self._run("kill", signal_name, f"{self._domain}/{label}")


def daemon_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{DAEMON_LABEL}.plist"


class _AnyioSleeper:
    async def sleep(self, seconds: float) -> None:
        await anyio.sleep(seconds)


class _Unreachable(Exception):
    pass


class _AuthRefused(Exception):
    pass


def _error(
    request_id: types.RequestId, message: str, code: str, retryable: bool
) -> types.JSONRPCMessage:
    data = {"code": code, "retryable": retryable}
    error = types.ErrorData(code=types.INTERNAL_ERROR, message=message, data=data)
    return types.JSONRPCMessage(types.JSONRPCError(jsonrpc="2.0", id=request_id, error=error))


class Shim:
    """One relay per client process. The keyword arguments are the test seams."""

    def __init__(
        self,
        settings: Settings,
        *,
        provider: SecretProvider | None = None,
        launchctl: LaunchctlPort | None = None,
        sleeper: Sleeper | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        server = settings.server
        host = f"[{server.host}]" if ":" in server.host else server.host
        self._ref = SecretRef.parse(server.token)
        self._provider = provider or KeychainProvider(getpass.getuser())
        self._launchctl = launchctl or SystemLaunchctl()
        self._sleeper = sleeper or _AnyioSleeper()
        self._client = httpx.AsyncClient(
            base_url=f"http://{host}:{server.port}",
            transport=transport,
            timeout=httpx.Timeout(300.0, connect=5.0),
        )
        self._token: Secret | None = None
        self._ready_seen = False
        self._start_lock = anyio.Lock()
        self._initialize: dict[str, Any] | None = None
        self._initialized: dict[str, Any] | None = None

    async def relay(self, read_stream: ReadStream, write_stream: WriteStream) -> None:
        """Answer each client message from the daemon until the client closes stdin."""
        async with self._client, write_stream, anyio.create_task_group() as tasks:
            async for item in read_stream:
                if isinstance(item, Exception):
                    _log.warning("shim.unreadable_message")
                    continue
                tasks.start_soon(self._answer, item.message, write_stream)

    async def _answer(self, message: types.JSONRPCMessage, write_stream: WriteStream) -> None:
        reply = await self.handle(message)
        if reply is not None:
            await write_stream.send(SessionMessage(reply))

    # @spec PLAT-72, PLAT-77
    async def handle(self, message: types.JSONRPCMessage) -> types.JSONRPCMessage | None:
        """Relay one message; return the reply for a request, ``None`` for anything else."""
        root = message.root
        payload = message.model_dump(by_alias=True, mode="json", exclude_none=True)
        method = getattr(root, "method", None)
        if method == "initialize":
            self._initialize = payload
        elif method == "notifications/initialized":
            self._initialized = payload
        if not isinstance(root, types.JSONRPCRequest):
            # Notifications and responses get no reply, so a failure to deliver is dropped.
            try:
                await self._send(payload, start=False)
            except (_Unreachable, _AuthRefused):
                _log.warning("shim.message_dropped", extra={"operation": str(method)})
            return None
        try:
            response = await self._post(payload, replay=method != "initialize")
        except _Unreachable:
            return _error(root.id, UNREACHABLE_MESSAGE, "internal", True)
        except _AuthRefused:
            return _error(root.id, AUTH_FAILED_MESSAGE, "auth_failed", False)
        try:
            return types.JSONRPCMessage.model_validate_json(response.content)
        except ValidationError:
            return _error(root.id, BAD_REPLY_MESSAGE, "internal", True)

    async def _post(self, payload: dict[str, Any], *, replay: bool) -> httpx.Response:
        response = await self._send(payload, start=True)
        if response.status_code == 401:
            self._token = None  # the token may have been rotated: re-read it once
            response = await self._send(payload, start=True)
            if response.status_code == 401:
                raise _AuthRefused
        if replay and response.status_code in (400, 404) and self._initialize is not None:
            # A session error: replay initialize once, then the request once (PLAT-77).
            await self._send(self._initialize, start=True)
            if self._initialized is not None:
                await self._send(self._initialized, start=True)
            response = await self._send(payload, start=True)
        return response

    async def _send(self, payload: dict[str, Any], *, start: bool) -> httpx.Response:
        if start and not self._ready_seen:
            await self._ensure_daemon()
        headers = {**await self._bearer(), "Accept": ACCEPT}
        try:
            return await self._client.post("/mcp/", json=payload, headers=headers)
        except httpx.ConnectError:
            if not start:
                raise _Unreachable from None
        except httpx.HTTPError:
            raise _Unreachable from None
        # The daemon went away (a restart or a crash): start it again, then resend once.
        self._ready_seen = False
        await self._ensure_daemon()
        try:
            return await self._client.post("/mcp/", json=payload, headers=headers)
        except httpx.HTTPError:
            raise _Unreachable from None

    async def _bearer(self) -> dict[str, str]:
        if self._token is None:
            _, secret = await anyio.to_thread.run_sync(self._provider.get, self._ref)
            if secret is None:
                raise _AuthRefused
            self._token = secret
        return auth.bearer_header(self._token)

    # @spec PLAT-73
    async def _ensure_daemon(self) -> None:
        """Probe ``/readyz``; if down, ask launchd to start the daemon, up to three times."""
        async with self._start_lock:
            if self._ready_seen or await self._ready():
                self._ready_seen = True
                return
            for _ in range(START_ATTEMPTS):
                await self._start()
                for _ in range(int(START_WAIT_S / POLL_S)):
                    await self._sleeper.sleep(POLL_S)
                    if await self._ready():
                        self._ready_seen = True
                        return
            raise _Unreachable

    async def _start(self) -> None:
        try:
            if await self._launchctl.is_loaded(DAEMON_LABEL):
                await self._launchctl.kickstart(DAEMON_LABEL)
            else:
                await self._launchctl.bootstrap(daemon_plist())
        except OSError:
            _log.warning("shim.launchctl_failed", extra={"operation": "start"})

    async def _ready(self) -> bool:
        try:
            response = await self._client.get("/readyz")
        except httpx.HTTPError:
            return False
        return response.status_code == 200


def main(settings: Settings) -> int:
    """Run the shim on this process's stdin and stdout; ``cli.py`` passes the settings."""
    from mcp.server.stdio import stdio_server

    shim = Shim(settings)

    async def run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await shim.relay(read_stream, write_stream)

    anyio.run(run)
    return 0
