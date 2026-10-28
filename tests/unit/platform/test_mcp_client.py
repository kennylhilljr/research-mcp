"""The upstream MCP client: streamable HTTP over the shared ``HttpClient``.

LLD-sources-v3 5.6 and M1-plan-v6 2.2 (M1-11). Every upstream is ``FakeMcpServer`` from
``research_mcp.testing.adapters`` behind an ``httpx.MockTransport``, so each MCP message is
a real request through the HTTP client's host policy, rate limits and telemetry.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import anyio
import httpx
import pytest

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.models import CallRecord
from research_mcp.core.specs import RateSpec, SourcePolicy
from research_mcp.platform.http import HttpClient
from research_mcp.platform.mcp_client import PROTOCOL_VERSION, McpClient
from research_mcp.platform.secrets import Secret
from research_mcp.testing.adapters import FakeMcpServer, text_result
from research_mcp.testing.clock import FakeClock, FakeSleeper

SERVER = "https://mcp.fake-upstream.org/mcp"
POLICY = SourcePolicy(
    source="upstream",
    hosts=frozenset({"mcp.fake-upstream.org"}),
    auth=None,
    rate=RateSpec(rps=1000.0, burst=1000, concurrency=8),
    timeout_s=5.0,
    max_bytes=100_000,
)


class Policies:
    def policy(self, source: str) -> SourcePolicy:
        return POLICY


class NoCredentials:
    def secret_for(self, source: str) -> Secret | None:
        return None


class Sink:
    def __init__(self) -> None:
        self.records: list[CallRecord] = []

    def record(self, call: CallRecord) -> None:
        self.records.append(call)


class Wire(httpx.AsyncByteStream):
    def __init__(self, content: bytes) -> None:
        self.content = content

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.content


class Stack:
    """``McpClient`` over ``HttpClient`` over a fake server; requests are recorded."""

    def __init__(self, server: FakeMcpServer) -> None:
        self.server = server
        self.requests: list[httpx.Request] = []
        self.sink = Sink()
        clock = FakeClock()

        def handle(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            response = server.handle(request)
            if not response.is_stream_consumed:
                return response
            # A test's own httpx.Response(json=...) arrives read; send it unread instead.
            return httpx.Response(
                response.status_code, headers=response.headers, stream=Wire(response.content)
            )

        self.http = HttpClient(
            Policies(),
            NoCredentials(),
            self.sink,
            clock,
            FakeSleeper(clock),
            None,
            transport=httpx.MockTransport(handle),
        )
        self.client = McpClient(self.http)

    async def call(self, tool: str = "echo", **arguments: Any) -> Any:
        return await self.client.call_tool(SERVER, tool, arguments, source="upstream")


def echo(arguments: dict[str, Any]) -> Any:
    return text_result(f"echo {arguments.get('q')}")


@pytest.fixture
async def stack() -> Any:
    made: list[Stack] = []

    def build(server: FakeMcpServer | None = None) -> Stack:
        made.append(Stack(server or FakeMcpServer({"echo": echo})))
        return made[-1]

    yield build
    for item in made:
        await item.http.aclose()


async def test_call_tool_opens_a_session_then_calls_the_tool(stack: Any) -> None:
    """@spec SRC-22: initialize, the initialized notice, then tools/call, each over HTTP."""
    s = stack()
    result = await s.call(q="hi")
    assert result == text_result("echo hi")
    assert s.server.methods == ["initialize", "notifications/initialized", "tools/call"]
    assert s.server.calls == [("echo", {"q": "hi"})]
    init, notice, call = s.requests
    assert "mcp-session-id" not in init.headers
    for request in (init, notice, call):
        assert request.url == httpx.URL(SERVER)
        assert "application/json" in request.headers["accept"]
        assert "text/event-stream" in request.headers["accept"]
    for request in (notice, call):
        assert request.headers["mcp-session-id"] == "fake-session-1"
        assert request.headers["mcp-protocol-version"] == PROTOCOL_VERSION
    # Telemetry: one CallRecord per request, for the calling source.
    assert [(r.source, r.op) for r in s.sink.records] == [("upstream", "post_events")] * 3


async def test_session_is_reused_and_reopened_once_when_it_expires(stack: Any) -> None:
    """@spec SRC-22: Later calls reuse the session; a 404 for it opens one new session."""
    s = stack()
    await s.call(q="a")
    await s.call(q="b")
    assert s.server.methods.count("initialize") == 1
    s.server.expire_sessions()
    assert await s.call(q="c") == text_result("echo c")
    assert s.server.methods.count("initialize") == 2
    assert s.requests[-1].headers["mcp-session-id"] == "fake-session-2"


async def test_concurrent_first_calls_open_one_session(stack: Any) -> None:
    """Two calls that start together share one initialize."""
    s = stack()
    async with anyio.create_task_group() as tg:
        tg.start_soon(s.call)
        tg.start_soon(s.call)
    assert s.server.methods.count("initialize") == 1
    assert len(s.server.calls) == 2


async def test_a_late_404_on_an_ended_session_keeps_the_reopened_one(
    stack: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A call still holding the ended session must not drop the one another call reopened."""
    s = stack()
    await s.call()
    stale = s.client._sessions[(SERVER, "upstream")]
    s.server.expire_sessions()
    await s.call()
    assert s.server.methods.count("initialize") == 2
    # The next call starts with the stale session, as a concurrent call would have.
    session = s.client._session
    handed = [stale]

    async def first_stale(server: str, source: str) -> Any:
        return handed.pop() if handed else await session(server, source)

    monkeypatch.setattr(s.client, "_session", first_stale)
    await s.call()
    assert s.server.methods.count("initialize") == 2


async def test_json_replies_work_like_event_streams(stack: Any) -> None:
    """A server that answers with JSON bodies is read the same way."""
    s = stack(FakeMcpServer({"echo": echo}, event_stream=False))
    assert await s.call(q="j") == text_result("echo j")


async def test_mcp_errors_become_http_errors_without_upstream_text(
    stack: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """@spec SRC-22: A JSON-RPC error or a tool error is upstream_error with a fixed detail."""
    leaky = "token sk-live-0123456789"
    s = stack(FakeMcpServer({"fails": lambda arguments: text_result(leaky, is_error=True)}))
    caplog.set_level(logging.DEBUG)
    with pytest.raises(HttpError) as caught:
        await s.call("fails")
    assert (caught.value.code, caught.value.detail) == (ErrorCode.UPSTREAM_ERROR, "tool_error")
    with pytest.raises(HttpError) as caught:
        await s.call("missing")
    assert (caught.value.code, caught.value.detail) == (ErrorCode.UPSTREAM_ERROR, "mcp_error")
    assert leaky not in str(caught.value)
    assert leaky not in caplog.text


@pytest.mark.parametrize(
    "reply",
    [
        {"jsonrpc": "2.0", "id": 999, "result": {}},
        {"jsonrpc": "2.0", "id": 0, "result": "not an object"},
        {"jsonrpc": "2.0", "method": "notifications/progress"},
    ],
    ids=["other-id", "result-not-object", "no-reply"],
)
async def test_a_reply_without_a_matching_result_is_malformed(
    stack: Any, reply: dict[str, Any]
) -> None:
    """A reply with no result for the request's id is upstream_error, malformed_body."""
    server = FakeMcpServer({"echo": echo})
    s = stack(server)
    await s.call()

    def wrong(request: httpx.Request) -> httpx.Response:
        body = dict(reply)
        if body.get("id") == 0:
            # The request's own id, so only the result's shape is wrong.
            body["id"] = json.loads(request.content)["id"]
        return httpx.Response(200, json=body)

    server.handle = wrong  # type: ignore[method-assign]
    with pytest.raises(HttpError) as caught:
        await s.call()
    assert (caught.value.code, caught.value.detail) == (ErrorCode.UPSTREAM_ERROR, "malformed_body")


async def test_a_server_off_the_source_hosts_is_blocked_before_any_request(stack: Any) -> None:
    """@spec SRC-22: The source's host policy applies to the MCP endpoint."""
    s = stack()
    with pytest.raises(HttpError) as caught:
        await s.client.call_tool("https://evil.example/mcp", "echo", {}, source="upstream")
    assert caught.value.code is ErrorCode.BLOCKED_BY_POLICY
    assert s.requests == []


async def test_http_errors_pass_through_with_their_code(stack: Any) -> None:
    """A 429 on tools/call reaches the caller as rate_limited, after the client's retries."""
    server = FakeMcpServer({"echo": echo})
    s = stack(server)
    await s.call()
    server.handle = lambda request: httpx.Response(  # type: ignore[method-assign]
        429, headers={"Retry-After": "1"}
    )
    with pytest.raises(HttpError) as caught:
        await s.call()
    assert caught.value.code is ErrorCode.RATE_LIMITED
    assert caught.value.retry_after_ms == 1000
