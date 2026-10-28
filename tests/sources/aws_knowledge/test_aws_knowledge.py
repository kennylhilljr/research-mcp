"""The AWS Knowledge adapter against the in-memory MCP server fake (LLD-sources-v3 5.6).

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
from research_mcp.sources import aws_knowledge
from research_mcp.sources.aws_knowledge import AwsKnowledgeAdapter
from research_mcp.testing.adapters import FakeMcpServer, text_result

SERVER = "https://knowledge-mcp.global.api.aws"
SEARCH = "aws___search_documentation"
READ = "aws___read_documentation"
WELCOME = "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html"
HITS = [
    {"rank_order": 2, "url": WELCOME + "#b", "title": "Second", "context": "two"},
    {"rank_order": 1, "url": WELCOME, "title": "What is Amazon S3?", "context": "one"},
]


def server() -> FakeMcpServer:
    return FakeMcpServer(
        {
            SEARCH: lambda arguments: text_result(json.dumps(HITS)),
            READ: lambda arguments: text_result(f"# Page at {arguments['url']}\n\nBody."),
        }
    )


def stack_for(mcp_stack: Any, fake: FakeMcpServer | None = None) -> Any:
    return mcp_stack(aws_knowledge.SPEC, AwsKnowledgeAdapter, fake or server())


async def test_calls_go_through_upstream_port_with_policy_and_telemetry(mcp_stack: Any) -> None:
    """@spec SRC-22: AWS Knowledge calls go through McpUpstreamPort over the shared client.

    The fake server sees the tool call; every request reaches the spec's host; the client
    records a ``CallRecord`` per request for ``aws_knowledge``; the spec's rate limit makes
    the client wait; and a server off the spec's hosts is ``blocked_by_policy`` unsent.
    """
    stack = stack_for(mcp_stack)
    page = await stack.adapter.search(SearchRequest(query="s3 lifecycle", limit=5))
    assert [r.title for r in page.records] == ["What is Amazon S3?", "Second"]
    assert stack.server.calls == [(SEARCH, {"search_phrase": "s3 lifecycle", "limit": 5})]
    assert {request.url for request in stack.requests} == {httpx.URL(SERVER)}
    assert len(stack.sink.records) == len(stack.requests) == 3
    assert {(r.source, r.op, r.status) for r in stack.sink.records} == {
        ("aws_knowledge", "post_events", 200),
        ("aws_knowledge", "post_events", 202),
    }
    # Three requests against a burst of two: the third waited for a token (PLAT-37).
    assert sum(stack.sleeper.sleeps) > 0

    sent = len(stack.requests)
    stack.adapter.server = "https://knowledge-mcp.evil.example/mcp"
    with pytest.raises(HttpError) as caught:
        await stack.adapter.search(SearchRequest(query="x"))
    assert caught.value.code is ErrorCode.BLOCKED_BY_POLICY
    assert len(stack.requests) == sent
    assert all(r.source == "aws_knowledge" for r in stack.sink.records)


async def test_a_tool_error_is_upstream_error_and_its_text_stays_out(
    mcp_stack: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """@spec SRC-22: A failing tool is ``upstream_error``; its text is in no error or log."""
    leaked = "internal trace sk-live-aws-0123456789"
    fake = FakeMcpServer({SEARCH: lambda arguments: text_result(leaked, is_error=True)})
    stack = stack_for(mcp_stack, fake)
    caplog.set_level(logging.DEBUG)
    with pytest.raises(HttpError) as caught:
        await stack.adapter.search(SearchRequest(query="x"))
    assert caught.value.code is ErrorCode.UPSTREAM_ERROR
    assert leaked not in repr(caught.value)
    assert leaked not in caplog.text


async def test_get_reads_the_page_and_probe_uses_the_read_tool(mcp_stack: Any) -> None:
    """``get`` maps the fetched Markdown; ``probe`` reads a known page with the same tool."""
    stack = stack_for(mcp_stack)
    record = await stack.adapter.get(Identifier("url", WELCOME))
    assert record is not None
    assert record.title == f"Page at {WELCOME}"
    assert record.ids == [Identifier("url", WELCOME)]
    assert (record.work_type, record.venue) == ("webpage", "AWS documentation")
    assert await stack.adapter.get(Identifier("doi", "10.1/x")) is None
    probe = await stack.adapter.probe()
    assert (probe.ok, probe.shape_ok) == (True, True)
    assert [name for name, _ in stack.server.calls] == [READ, READ]


async def test_structured_results_are_read_too(mcp_stack: Any) -> None:
    """A server that sends ``structuredContent`` as ``{"result": [...]}`` maps the same."""
    fake = FakeMcpServer(
        {SEARCH: lambda arguments: {"content": [], "structuredContent": {"result": HITS}}}
    )
    stack = stack_for(mcp_stack, fake)
    page = await stack.adapter.search(SearchRequest(query="s3"))
    assert len(page.records) == 2


@pytest.mark.parametrize("items", [[1, 2], ["a"], [None], [[]]])
async def test_a_result_list_of_non_objects_is_upstream_error(mcp_stack: Any, items: Any) -> None:
    """A search list whose items are not objects is ``upstream_error``, not a raw exception."""
    fake = FakeMcpServer({SEARCH: lambda arguments: text_result(json.dumps(items))})
    stack = stack_for(mcp_stack, fake)
    with pytest.raises(HttpError) as caught:
        await stack.adapter.search(SearchRequest(query="x"))
    assert caught.value.code is ErrorCode.UPSTREAM_ERROR


@pytest.mark.parametrize(
    "result",
    [{"content": [1]}, {"content": ["text"]}, {"content": [{"type": "text"}]}, {"content": {}}],
)
async def test_a_malformed_page_makes_the_probe_shape_fail(mcp_stack: Any, result: Any) -> None:
    """A read result in the wrong shape gives ``shape_ok=False`` and never raises."""
    fake = FakeMcpServer({READ: lambda arguments: result})
    stack = stack_for(mcp_stack, fake)
    probe = await stack.adapter.probe()
    assert (probe.ok, probe.shape_ok) == (True, False)


async def test_conformance_runs_over_the_upstream_mcp_port(
    conformance: Any,
    harness_for: Any,
    fixtures_of: Any,
    counting_stream: Any,
    run_conformance: Any,
) -> None:
    """@spec SRC-20: aws_knowledge passes the conformance suite with its own fixtures, over
    an ``McpClient`` on the harness's ``HttpClient``, so the checks see real MCP traffic."""
    source = conformance.get("aws_knowledge")
    assert source is not None
    await run_conformance(source, harness_for, fixtures_of, counting_stream)

    harness = harness_for(source)
    assert isinstance(harness.adapter.ctx.mcp, McpClient)
    harness.serve(fixtures_of(source)["search_ok"])
    page = await harness.adapter.search(SearchRequest(query="s3"))
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
        "http://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html",
        "https://docs.aws.amazon.com.evil.example/x",
        "https://user:pw@docs.aws.amazon.com/x",
        "https://docs.aws.amazon.com:8443/x",
        "https://learn.microsoft.com/en-us/azure/",
        "not a url",
    ],
)
async def test_get_sends_no_url_off_the_aws_documentation_host(mcp_stack: Any, url: str) -> None:
    """@spec SRC-20: ``get`` answers None for a URL not on AWS documentation; nothing is sent."""
    stack = stack_for(mcp_stack)
    assert await stack.adapter.get(Identifier("url", url)) is None
    assert stack.server.calls == []
    assert stack.server.methods == []
