"""MCP resources. M0 has one: ``research://sources`` (LLD-search-v2 2.3)."""

from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from research_mcp.mcp_app.server import Services
from research_mcp.sources.registry import SourceView

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP", services: Services) -> None:
    # @spec SRC-8
    @mcp.resource("research://sources", mime_type="application/json")
    def sources() -> str:
        """Every source with its state and, when it cannot run, the exact fix."""
        views = services.registry.view()
        return TypeAdapter(list[SourceView]).dump_json(views).decode()
