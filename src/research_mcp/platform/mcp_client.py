"""The upstream MCP client: ``McpUpstreamPort`` over the shared HTTP client.

LLD-sources-v3 2.1 and 5.6; LLD-platform-v3 4.4. The AWS Knowledge and Microsoft Learn
adapters call ``McpClient.call_tool``. Every MCP message is a POST through
``HttpClient.post_events`` with the calling source's id, so the source's host policy, rate
limits, retries, byte cap and call telemetry apply to it as to any other upstream call, and
no adapter opens a client of its own (SRC-22).

The client speaks MCP streamable HTTP: ``initialize`` opens a session whose
``Mcp-Session-Id`` goes on every later request, ``notifications/initialized`` follows it,
and a 404 for a live session opens one new session and repeats the call once. An MCP-level
failure (a JSON-RPC error, a tool result with ``isError``, a reply with no result for the
request) becomes ``HttpError(upstream_error)`` with a fixed detail, so the federation and
health layers classify it like any upstream error and no upstream text reaches a message.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import anyio

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.models import JsonValue
from research_mcp.platform.http import SESSION_HEADER, EventReply
from research_mcp.version import __version__

PROTOCOL_VERSION = "2025-06-18"
PROTOCOL_HEADER = "MCP-Protocol-Version"
# A server's protocolVersion goes into a request header, so only a dated version is used.
_DATED_VERSION = re.compile(r"\d{4}-\d{2}-\d{2}")
ACCEPT = "application/json, text/event-stream"
CLIENT_NAME = "research-mcp"


class EventPort(Protocol):
    """The part of ``HttpClient`` the MCP client uses."""

    async def post_events(
        self,
        url: str,
        *,
        source: str,
        json: JsonValue,
        headers: Mapping[str, str] | None = None,
    ) -> EventReply: ...


@dataclass(frozen=True)
class _Session:
    session_id: str | None
    protocol_version: str


def _malformed() -> HttpError:
    return HttpError(ErrorCode.UPSTREAM_ERROR, detail="malformed_body")


class McpClient:
    """``McpUpstreamPort`` (LLD-sources-v3 2.1) over the daemon's one ``HttpClient``."""

    def __init__(self, http: EventPort) -> None:
        self._http = http
        self._ids = itertools.count(1)
        self._sessions: dict[tuple[str, str], _Session] = {}
        self._locks: dict[tuple[str, str], anyio.Lock] = {}

    # @spec SRC-22
    async def call_tool(
        self, server: str, tool: str, arguments: Mapping[str, JsonValue], *, source: str
    ) -> JsonValue:
        """Call ``tool`` on the MCP server at ``server``; return the ``tools/call`` result."""
        params: dict[str, JsonValue] = {"name": tool, "arguments": dict(arguments)}
        session = await self._session(server, source)
        try:
            result = await self._rpc(server, source, session, "tools/call", params)
        except HttpError as exc:
            if exc.code is not ErrorCode.NOT_FOUND or session.session_id is None:
                raise
            # The server ended the session: open a new one and repeat the call once. Drop
            # it only if it is still the stored one, so a concurrent call's fresh session
            # survives.
            if self._sessions.get((server, source)) is session:
                del self._sessions[(server, source)]
            session = await self._session(server, source)
            result = await self._rpc(server, source, session, "tools/call", params)
        if result.get("isError") is True:
            raise HttpError(ErrorCode.UPSTREAM_ERROR, detail="tool_error")
        return result

    async def _session(self, server: str, source: str) -> _Session:
        key = (server, source)
        lock = self._locks.setdefault(key, anyio.Lock())
        async with lock:
            session = self._sessions.get(key)
            if session is None:
                session = await self._open(server, source)
                self._sessions[key] = session
            return session

    async def _open(self, server: str, source: str) -> _Session:
        params: dict[str, JsonValue] = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": CLIENT_NAME, "version": __version__},
        }
        rpc_id = next(self._ids)
        message: dict[str, JsonValue] = {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": "initialize",
            "params": params,
        }
        reply = await self._http.post_events(
            server, source=source, json=message, headers={"Accept": ACCEPT}
        )
        result = self._result(reply, rpc_id)
        version = result.get("protocolVersion")
        if not isinstance(version, str) or _DATED_VERSION.fullmatch(version) is None:
            version = PROTOCOL_VERSION
        session = _Session(session_id=reply.session_id, protocol_version=version)
        notice: dict[str, JsonValue] = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        await self._http.post_events(
            server, source=source, json=notice, headers=self._headers(session)
        )
        return session

    async def _rpc(
        self,
        server: str,
        source: str,
        session: _Session,
        method: str,
        params: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        rpc_id = next(self._ids)
        message: dict[str, JsonValue] = {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": method,
            "params": params,
        }
        reply = await self._http.post_events(
            server, source=source, json=message, headers=self._headers(session)
        )
        return self._result(reply, rpc_id)

    @staticmethod
    def _headers(session: _Session) -> dict[str, str]:
        headers = {"Accept": ACCEPT, PROTOCOL_HEADER: session.protocol_version}
        if session.session_id is not None:
            headers[SESSION_HEADER] = session.session_id
        return headers

    @staticmethod
    def _result(reply: EventReply, rpc_id: int) -> dict[str, JsonValue]:
        """The ``result`` of the reply to ``rpc_id``; other messages in the stream are skipped."""
        for message in reply.messages:
            if not isinstance(message, dict) or message.get("id") != rpc_id:
                continue
            if "error" in message:
                raise HttpError(ErrorCode.UPSTREAM_ERROR, detail="mcp_error")
            result = message.get("result")
            if not isinstance(result, dict):
                raise _malformed()
            return result
        raise _malformed()
