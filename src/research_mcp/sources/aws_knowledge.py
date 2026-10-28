"""The AWS Knowledge adapter: AWS documentation through AWS's public MCP server.

LLD-sources-v3 5.6; PRD-sources-v5 catalog row 31. ``aws___search_documentation`` returns
a ranked list of pages (``url``, ``title``, ``context``) and ``aws___read_documentation``
returns a page as Markdown. The calls go through ``McpUpstreamPort`` (SRC-22). Free and
unauthenticated.
"""

from __future__ import annotations

import functools
from typing import Any

from research_mcp.core.models import JsonValue, SearchRequest, WorkRecord
from research_mcp.core.specs import RateSpec
from research_mcp.sources.base import Capability, SourceSpec
from research_mcp.sources.mcp_upstream import UpstreamMcpAdapter, object_list, tool_json

_HOST = "knowledge-mcp.global.api.aws"


@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import (PLAT-3), like the other adapters.
    return SourceSpec(
        id="aws_knowledge",
        title="AWS Knowledge",
        group="vendor_docs",
        capabilities=frozenset({Capability.SEARCH, Capability.GET}),
        id_schemes=frozenset({"url"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # AWS publishes no number for the public server; a conservative rate [assumption].
        rate=RateSpec(rps=2, burst=2, concurrency=2),
        timeout_s=15.0,
        max_page_size=10,
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# @spec SRC-20
class AwsKnowledgeAdapter(UpstreamMcpAdapter):
    """Translates the AWS Knowledge MCP tools; all I/O goes through ``ctx.mcp``."""

    server = f"https://{_HOST}"
    search_tool = "aws___search_documentation"
    get_tool = "aws___read_documentation"
    probe_url = "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html"
    venue = "AWS documentation"
    doc_hosts = frozenset({"docs.aws.amazon.com"})

    def search_arguments(self, req: SearchRequest, limit: int) -> dict[str, JsonValue]:
        return {"search_phrase": req.query, "limit": limit}

    def map_search(self, payload: JsonValue) -> list[WorkRecord]:
        data: Any = tool_json(payload)
        # A server that returns structured content wraps the list as {"result": [...]}.
        items = object_list(data["result"] if isinstance(data, dict) else data)
        ranked = sorted(items, key=lambda item: item.get("rank_order", 0))
        return [self.record(item["url"], item["title"], item.get("context")) for item in ranked]


ADAPTER = AwsKnowledgeAdapter
