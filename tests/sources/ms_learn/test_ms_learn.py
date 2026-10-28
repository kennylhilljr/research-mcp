"""The Microsoft Learn adapter against the in-memory MCP server fake (LLD-sources-v3 5.6).

Every call goes adapter, ``McpClient``, ``HttpClient``, ``httpx.MockTransport`` and
``FakeMcpServer``, so the tests see the real HTTP traffic of each MCP message.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
import pytest

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.platform.mcp_client import McpClient
from research_mcp.sources import ms_learn
from research_mcp.sources.ms_learn import MsLearnAdapter
from research_mcp.testing.adapters import FakeMcpServer, text_result

SERVER = "https://learn.microsoft.com/api/mcp"
SEARCH = "microsoft_docs_search"
FETCH = "microsoft_docs_fetch"
BLOBS = "https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-introduction"
CHUNKS = {
    "results": [
        {"title": f"Chunk {n}", "content": f"text {n}", "contentUrl": f"{BLOBS}?n={n}"}
        for n in range(12)
    ]
}


def server(*, event_stream: bool = True) -> FakeMcpServer:
    return FakeMcpServer(
        {
            SEARCH: lambda arguments: text_result(json.dumps(CHUNKS)),
            FETCH: lambda arguments: text_result("# Introduction to Azure Blob Storage\n\nBody."),
        },
        event_stream=event_stream,
    )


def stack_for(mcp_stack: Any, fake: FakeMcpServer | None = None) -> Any:
    return mcp_stack(ms_learn.SPEC, MsLearnAdapter, fake or server())


async def test_calls_go_through_upstream_port_with_policy_and_telemetry(mcp_stack: Any) -> None:
    """@spec SRC-22: Microsoft Learn calls go through McpUpstreamPort over the shared client.

    The fake server sees the tool call; every request reaches the spec's host; the client
    records a ``CallRecord`` per request for ``ms_learn``; the spec's rate limit makes the
    client wait; and a server off the spec's hosts is ``blocked_by_policy`` unsent.
    """
    stack = stack_for(mcp_stack)
    page = await stack.adapter.search(SearchRequest(query="blob lifecycle", limit=3))
    assert [r.title for r in page.records] == ["Chunk 0", "Chunk 1", "Chunk 2"]
    assert stack.server.calls == [(SEARCH, {"query": "blob lifecycle"})]
    assert {request.url for request in stack.requests} == {httpx.URL(SERVER)}
    assert len(stack.sink.records) == len(stack.requests) == 3
    assert {(r.source, r.op) for r in stack.sink.records} == {("ms_learn", "post_events")}
    # Three requests against a burst of two: the third waited for a token (PLAT-37).
    assert sum(stack.sleeper.sleeps) > 0

    sent = len(stack.requests)
    stack.adapter.server = "https://learn.microsoft.com.evil.example/api/mcp"
    with pytest.raises(HttpError) as caught:
        await stack.adapter.search(SearchRequest(query="x"))
    assert caught.value.code is ErrorCode.BLOCKED_BY_POLICY
    assert len(stack.requests) == sent


async def test_a_tool_error_is_upstream_error_and_its_text_stays_out(
    mcp_stack: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """@spec SRC-22: A failing tool is ``upstream_error``; its text is in no error or log."""
    leaked = "internal trace sk-live-learn-0123456789"
    fake = FakeMcpServer({SEARCH: lambda arguments: text_result(leaked, is_error=True)})
    stack = stack_for(mcp_stack, fake)
    caplog.set_level(logging.DEBUG)
    with pytest.raises(HttpError) as caught:
        await stack.adapter.search(SearchRequest(query="x"))
    assert caught.value.code is ErrorCode.UPSTREAM_ERROR
    assert leaked not in repr(caught.value)
    assert leaked not in caplog.text


async def test_search_is_capped_at_the_page_size_and_get_reads_the_page(mcp_stack: Any) -> None:
    """Twelve chunks give at most ``max_page_size`` records; ``get`` maps the fetched page."""
    stack = stack_for(mcp_stack, server(event_stream=False))
    page = await stack.adapter.search(SearchRequest(query="blob", limit=50))
    assert len(page.records) == ms_learn.SPEC.max_page_size
    record = await stack.adapter.get(Identifier("url", BLOBS))
    assert record is not None
    assert record.title == "Introduction to Azure Blob Storage"
    assert (record.work_type, record.venue) == ("webpage", "Microsoft Learn")
    assert stack.server.calls[-1] == (FETCH, {"url": BLOBS})


@pytest.mark.parametrize("items", [[1, 2], ["a"], [None]])
async def test_a_result_list_of_non_objects_is_upstream_error(mcp_stack: Any, items: Any) -> None:
    """A search list whose items are not objects is ``upstream_error``, not a raw exception."""
    payload = json.dumps({"results": items})
    fake = FakeMcpServer({SEARCH: lambda arguments: text_result(payload)})
    stack = stack_for(mcp_stack, fake)
    with pytest.raises(HttpError) as caught:
        await stack.adapter.search(SearchRequest(query="x"))
    assert caught.value.code is ErrorCode.UPSTREAM_ERROR


async def test_conformance_runs_over_the_upstream_mcp_port(
    conformance: Any,
    harness_for: Any,
    fixtures_of: Any,
    counting_stream: Any,
    run_conformance: Any,
) -> None:
    """@spec SRC-20: ms_learn passes the conformance suite with its own fixtures, over an
    ``McpClient`` on the harness's ``HttpClient``, so the checks see real MCP traffic."""
    source = conformance.get("ms_learn")
    assert source is not None
    await run_conformance(source, harness_for, fixtures_of, counting_stream)

    harness = harness_for(source)
    assert isinstance(harness.adapter.ctx.mcp, McpClient)
    harness.serve(fixtures_of(source)["search_ok"])
    page = await harness.adapter.search(SearchRequest(query="blob"))
    assert page.records
    assert [json.loads(r.content)["method"] for r in harness.handshakes] == [
        "initialize",
        "notifications/initialized",
    ]
    (call,) = harness.requests
    assert call.url == httpx.URL(SERVER)
    assert json.loads(call.content)["params"]["name"] == SEARCH


@pytest.mark.parametrize(
    "url",
    [
        "https://internal.corp.example/admin?token=secret",
        "http://169.254.169.254/latest/meta-data/",
        "http://learn.microsoft.com/en-us/azure/",
        "https://learn.microsoft.com.evil.example/x",
        "https://user:pw@learn.microsoft.com/x",
        "https://learn.microsoft.com:8443/x",
        "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html",
        "not a url",
    ],
)
async def test_get_sends_no_url_off_the_microsoft_learn_host(mcp_stack: Any, url: str) -> None:
    """@spec SRC-20: ``get`` answers None for a URL not on Microsoft Learn; nothing is sent."""
    stack = stack_for(mcp_stack)
    assert await stack.adapter.get(Identifier("url", url)) is None
    assert stack.server.calls == []
    assert stack.server.methods == []
