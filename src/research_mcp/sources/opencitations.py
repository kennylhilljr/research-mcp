"""The OpenCitations adapter: JSON over https, an optional access token (LLD-sources-v3 5.1;
PRD-sources-v5 SRC-20, catalog row 36: "port the existing adapter"). Serves only
``Capability.CITATIONS`` over the Index API's ``citations`` (who cites a DOI) and
``references`` (what a DOI cites) endpoints.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal
from urllib.parse import quote

from pydantic import BaseModel

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_doi
from research_mcp.core.models import (
    CitationPage,
    FulltextCandidate,
    ProbeResult,
    SearchPage,
    SearchRequest,
    WorkRecord,
)
from research_mcp.core.specs import AuthSpec, RateSpec
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors

_HOST = "opencitations.net"
_BASE_URL = f"https://{_HOST}/index/api/v2"
# A stable, long-cited DOI; confirmed against the live API before this spec ships [assumption].
_PROBE_DOI = "10.1186/1756-8722-6-59"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="opencitations",
        title="OpenCitations",
        group="integrity",
        capabilities=frozenset({Capability.CITATIONS}),
        id_schemes=frozenset({"doi"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("OPENCITATIONS_TOKEN",),
            required=False,
            placement="header",
            param="authorization",
            origins=(f"https://{_HOST}",),
            signup_url="https://opencitations.net/accesstoken",
        ),
        # OpenCitations publishes no fixed number for an anonymous or keyed caller; a
        # conservative rate [assumption].
        rate=RateSpec(rps=5, burst=5, concurrency=2),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _endpoint_and_key(direction: Literal["citing", "cited"]) -> tuple[str, str]:
    """The Index API endpoint and the entry field naming the other side of the edge."""
    if direction == "citing":
        # "citations/<doi>" lists entries whose "cited" is <doi>; "citing" is who cites it.
        return "citations", "citing"
    # "references/<doi>" lists entries whose "citing" is <doi>; "cited" is what it cites.
    return "references", "cited"


class OpenCitationsAdapter:
    """Translates the OpenCitations Index API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _edges(self, doi: str, direction: Literal["citing", "cited"]) -> Any:
        endpoint, _ = _endpoint_and_key(direction)
        url = f"{_BASE_URL}/{endpoint}/{quote(doi, safe='/')}"
        return await self.ctx.http.get_json(url, source=self.spec.id)

    async def search(self, req: SearchRequest) -> SearchPage:
        return SearchPage(records=[])

    async def get(self, ident: Identifier) -> WorkRecord | None:
        return None

    async def fulltext_candidates(self, work: WorkRecord) -> list[FulltextCandidate]:
        return []

    # @spec SRC-20
    @translate_errors
    async def citations(
        self,
        ident: Identifier,
        direction: Literal["citing", "cited"],
        cursor: str | None,
        limit: int,
    ) -> CitationPage:
        _, key = _endpoint_and_key(direction)
        edges = await self._edges(ident.value, direction)
        start = int(cursor) if cursor else 0
        page = edges[start : start + limit]
        ids = [Identifier("doi", normalize_doi(entry[key])) for entry in page]
        next_cursor = str(start + limit) if start + limit < len(edges) else None
        return CitationPage(ids=ids, next_cursor=next_cursor)

    async def search_authors(
        self, query: str | None, orcid: str | None, limit: int
    ) -> Sequence[BaseModel]:
        return []

    async def updates(self, ident: Identifier) -> Sequence[BaseModel]:
        return []

    async def probe(self) -> ProbeResult:
        started: datetime = self.ctx.clock.now()
        try:
            data = await self._edges(_PROBE_DOI, "citing")
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            shape_ok = isinstance(data, list) and bool(data) and "citing" in data[0]
        except (KeyError, TypeError, IndexError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = OpenCitationsAdapter
