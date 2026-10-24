"""The M0 discovery tools: ``search``, ``get_work`` and ``list_sources`` (LLD-search-v2 2.1).

Tools are thin: validate arguments, call one service, wrap the result in the envelope.
The bounds live in the signatures, so the SDK emits them in each input schema
(PLAT-FR-31). This module does not use postponed annotations: the SDK reads the
signatures through ``@tool_boundary``'s wrapper and resolves them in its own globals.
"""

from typing import TYPE_CHECKING, Annotated, Literal

from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from research_mcp.core.envelope import ToolResult
from research_mcp.core.errors import ErrorCode, ToolError
from research_mcp.core.ids import Identifier
from research_mcp.core.models import Author, SearchFilters, SearchRequest, Work
from research_mcp.mcp_app.server import Services, tool_boundary
from research_mcp.sources.registry import SourceView

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

COMPACT_AUTHORS = 3
# [assumption] SRCH-FR-7 says "a short abstract snippet" without a length.
SNIPPET_CHARS = 300
# [assumption] LLD-search-v2 2.1 writes `work_type: Literal[...]` without the values.
WorkType = Literal[
    "article",
    "preprint",
    "book",
    "book-chapter",
    "dataset",
    "thesis",
    "report",
    "repository",
    "code",
    "webpage",
]


def read_only(open_world: bool) -> ToolAnnotations:
    """All four hints, so no client has to guess a default (PLAT-FR-26)."""
    return ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=open_world
    )


class CompactWork(BaseModel):
    """A work in ``compact`` detail (SRCH-FR-7). [assumption] The LLD names no model."""

    model_config = ConfigDict(defer_build=True)

    work_id: str | None
    ids: list[Identifier]
    title: str
    authors: list[Author]
    author_count: int
    year: int | None
    venue: str | None
    work_type: str
    oa: bool
    abstract: str | None
    found_in: list[str]
    fuzzy: bool = False


def snippet(text: str | None) -> str | None:
    if text is None or len(text) <= SNIPPET_CHARS:
        return text
    return text[:SNIPPET_CHARS].rsplit(" ", 1)[0] + "..."


def compact(work: Work) -> CompactWork:
    return CompactWork(
        work_id=work.work_id,
        ids=work.ids,
        title=work.title,
        authors=work.authors[:COMPACT_AUTHORS],
        author_count=len(work.authors),
        year=work.year,
        venue=work.venue,
        work_type=work.work_type,
        oa=bool(work.oa_locations),
        abstract=snippet(work.abstract),
        found_in=work.found_in,
        fuzzy=work.fuzzy,
    )


# @spec PLAT-60
def register(mcp: "FastMCP", services: Services) -> None:
    """Register the M0 tools, each with all four annotations and ``@tool_boundary``."""
    boundary = tool_boundary(services)

    # @spec SRCH-20, SRCH-22
    @mcp.tool(annotations=read_only(open_world=True))
    @boundary
    async def search(
        query: Annotated[str, Field(min_length=1, max_length=500)],
        sources: Literal["auto"] | Annotated[list[str], Field(max_length=20)] = "auto",
        groups: list[str] = [],  # noqa: B006 - the SDK validates into a new list per call
        year_from: Annotated[int, Field(ge=1800, le=2100)] | None = None,
        year_to: Annotated[int, Field(ge=1800, le=2100)] | None = None,
        work_type: WorkType | None = None,
        oa_only: bool = False,
        provider: str | None = None,
        repository: str | None = None,
        limit: Annotated[int, Field(ge=1, le=50)] = 20,
        per_source_limit: Annotated[int, Field(ge=1, le=25)] = 10,
        cursor: str | None = None,
        detail: Literal["compact", "full"] = "compact",
    ) -> ToolResult[list[CompactWork] | list[Work]]:
        """Search many sources at once; one merged, ranked page with a status per source."""
        try:
            filters = SearchFilters(
                year_from=year_from,
                year_to=year_to,
                work_type=work_type,
                oa_only=oa_only,
                provider=provider,
                repository=repository,
            )
        except ValidationError as exc:
            raise ToolError(ErrorCode.INVALID_ARGUMENT, "Invalid search filters") from exc
        request = SearchRequest(query=query, filters=filters, limit=limit, cursor=cursor)
        result = await services.federation.search(
            request, sources, groups, per_source_limit=per_source_limit
        )
        works = result.works if detail == "full" else [compact(w) for w in result.works]
        return ToolResult[list[CompactWork] | list[Work]](
            data=works, source_status=result.statuses, next_cursor=result.next_cursor
        )

    # @spec SRCH-23
    @mcp.tool(annotations=read_only(open_world=True))
    @boundary
    async def get_work(
        id: Annotated[str, Field(min_length=1, max_length=300)],
    ) -> ToolResult[Work]:
        """One work by any identifier form, merged from every source that understands it."""
        work, statuses = await services.works.get_work(id)
        return ToolResult[Work](data=work, source_status=statuses)

    # @spec SRC-8
    @mcp.tool(annotations=read_only(open_world=False))
    @boundary
    async def list_sources(
        group: str | None = None,
        state: str | None = None,
    ) -> ToolResult[list[SourceView]]:
        """Every source with its state and, when it cannot run, the exact fix."""
        views = [
            view
            for view in services.registry.view()
            if (group is None or view.group == group)
            and (state is None or view.state.partition("(")[0] == state)
        ]
        return ToolResult[list[SourceView]](data=views)
