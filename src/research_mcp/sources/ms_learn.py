"""The Microsoft Learn adapter: Microsoft documentation through the Learn MCP server.

LLD-sources-v3 5.6; PRD-sources-v5 catalog row 32. ``microsoft_docs_search`` returns up
to ten content chunks (``title``, ``content``, ``contentUrl``) and ``microsoft_docs_fetch``
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

_HOST = "learn.microsoft.com"


@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import (PLAT-3), like the other adapters.
    return SourceSpec(
        id="ms_learn",
        title="Microsoft Learn",
        group="vendor_docs",
        capabilities=frozenset({Capability.SEARCH, Capability.GET}),
        id_schemes=frozenset({"url"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # Microsoft publishes no number for the public server; a conservative rate
        # [assumption].
        rate=RateSpec(rps=2, burst=2, concurrency=2),
        timeout_s=15.0,
        # The search tool returns at most ten chunks and takes no count.
        max_page_size=10,
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# @spec SRC-20
class MsLearnAdapter(UpstreamMcpAdapter):
    """Translates the Microsoft Learn MCP tools; all I/O goes through ``ctx.mcp``."""

    server = f"https://{_HOST}/api/mcp"
    search_tool = "microsoft_docs_search"
    get_tool = "microsoft_docs_fetch"
    probe_url = "https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-introduction"
    venue = "Microsoft Learn"
    doc_hosts = frozenset({"learn.microsoft.com"})

    def search_arguments(self, req: SearchRequest, limit: int) -> dict[str, JsonValue]:
        return {"query": req.query}

    def map_search(self, payload: JsonValue) -> list[WorkRecord]:
        data: Any = tool_json(payload)
        items = object_list(data["results"])
        return [
            self.record(item["contentUrl"], item["title"], item.get("content")) for item in items
        ]


ADAPTER = MsLearnAdapter
