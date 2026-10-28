"""The base of the upstream MCP adapters, AWS Knowledge and Microsoft Learn (LLD-sources-v3 5.6).

An upstream MCP adapter calls tools on a vendor's MCP server through
``SourceContext.mcp`` (``McpUpstreamPort``), never through HTTP of its own. The port runs
over the daemon's shared HTTP client, so the source's host policy, rate limits, telemetry
and redaction apply to every call (SRC-FR-10; SRC-22). A subclass names its server, its two
tools and the arguments they take, and maps the tool results to ``WorkRecord``s.

This module defines neither ``SPEC`` nor ``ADAPTER``, so discovery skips it.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier, normalize_url
from research_mcp.core.models import (
    AuthorRecord,
    CitationPage,
    FulltextCandidate,
    JsonValue,
    ProbeResult,
    Provenance,
    SearchPage,
    SearchRequest,
    UpdateNotice,
    WorkRecord,
)
from research_mcp.sources.base import SourceContext, SourceSpec, translate_errors

ADAPTER_VERSION = "1"


def tool_text(payload: Any) -> str:
    """The text items of a ``tools/call`` result, joined; a result in another shape raises."""
    content = payload["content"]
    if not isinstance(content, list):
        raise TypeError("tool result content is not a list")
    texts = [item["text"] for item in content if item["type"] == "text"]
    if not all(isinstance(text, str) for text in texts):
        raise TypeError("tool result text is not a string")
    return "\n".join(texts)


def tool_json(payload: Any) -> Any:
    """The JSON a tool returned: its ``structuredContent``, else its text parsed as JSON."""
    if not isinstance(payload, dict):
        raise TypeError("tool result is not an object")
    structured = payload.get("structuredContent")
    if structured is not None:
        return structured
    return json.loads(tool_text(payload))


def markdown_title(text: str) -> str | None:
    """The first level-one heading of a Markdown page."""
    for line in text.splitlines():
        if line.startswith("# "):
            title = " ".join(line[2:].split())
            if title:
                return title
    return None


class UpstreamMcpAdapter:
    """Search and get over two tools of an upstream MCP server; subclasses map results."""

    server: str  # the MCP endpoint URL; its host is in spec.hosts
    search_tool: str
    get_tool: str
    probe_url: str  # a page the get tool reads for the probe
    venue: str

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    def search_arguments(self, req: SearchRequest, limit: int) -> dict[str, JsonValue]:
        raise NotImplementedError

    def get_arguments(self, url: str) -> dict[str, JsonValue]:
        return {"url": url}

    def map_search(self, payload: JsonValue) -> list[WorkRecord]:
        raise NotImplementedError

    def map_get(self, payload: JsonValue, url: str) -> WorkRecord | None:
        """A fetched page: the Markdown text, titled by its first heading or its URL."""
        text = tool_text(payload)
        return self.record(url, markdown_title(text) or url, text)

    def record(self, url: str, title: str, abstract: str | None) -> WorkRecord:
        if not isinstance(url, str) or not isinstance(title, str) or not title.strip():
            raise ValueError("an upstream result needs a URL and a title")
        if abstract is not None and not isinstance(abstract, str):
            raise TypeError("an upstream snippet is not a string")
        value = normalize_url(url)
        return WorkRecord(
            ids=[Identifier("url", value)],
            title=" ".join(title.split()),
            venue=self.venue,
            work_type="webpage",
            abstract=abstract,
            provenance=Provenance(
                source=self.spec.id,
                upstream_id=value,
                adapter_version=ADAPTER_VERSION,
                retrieved_at=self.ctx.clock.now(),
            ),
        )

    async def call(self, tool: str, arguments: dict[str, JsonValue]) -> JsonValue:
        if self.ctx.mcp is None:
            raise HttpError(ErrorCode.UNCONFIGURED, detail="no upstream MCP port")
        return await self.ctx.mcp.call_tool(self.server, tool, arguments, source=self.spec.id)

    # @spec SRC-22
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = max(1, min(req.limit, self.spec.max_page_size))
        payload = await self.call(self.search_tool, self.search_arguments(req, limit))
        return SearchPage(records=self.map_search(payload)[:limit])

    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        if ident.scheme != "url":
            return None
        payload = await self.call(self.get_tool, self.get_arguments(ident.value))
        return self.map_get(payload, ident.value)

    async def fulltext_candidates(self, work: WorkRecord) -> list[FulltextCandidate]:
        return []

    async def citations(
        self,
        ident: Identifier,
        direction: Literal["citing", "cited"],
        cursor: str | None,
        limit: int,
    ) -> CitationPage:
        return CitationPage(ids=[])

    async def search_authors(
        self, query: str | None, orcid: str | None, limit: int
    ) -> list[AuthorRecord]:
        return []

    async def updates(self, ident: Identifier) -> list[UpdateNotice]:
        return []

    async def probe(self) -> ProbeResult:
        """Read ``probe_url`` with the get tool; shape_ok when the page maps to a record."""
        started = self.ctx.clock.now()
        try:
            payload = await self.call(self.get_tool, self.get_arguments(self.probe_url))
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        latency_ms = int((self.ctx.clock.now() - started).total_seconds() * 1000)
        try:
            shape_ok = self.map_get(payload, self.probe_url) is not None
        except (KeyError, TypeError, ValueError):
            shape_ok = False
        return ProbeResult(ok=True, latency_ms=latency_ms, shape_ok=shape_ok)
