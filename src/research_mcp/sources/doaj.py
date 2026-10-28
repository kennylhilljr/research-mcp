"""The DOAJ adapter: JSON over https, no credential (LLD-sources-v3 5.1; PRD-sources-v5
SRC-20). Calls the DOAJ Article Search API, keyed by a Crossref-style ``doi`` identifier in
an article's ``bibjson.identifier`` list, and surfaces its ``bibjson.link`` entries as
fulltext candidates.

The DOAJ API v2 response shape (``results`` list of ``{"id", "bibjson": {...}}``) is fixed
here from the provider's published documentation and is not itself tested against the live
API; it is recorded as an assumption in the unit's handoff.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import quote

from pydantic import BaseModel

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_doi
from research_mcp.core.models import (
    Author,
    CitationPage,
    FulltextCandidate,
    OaLocation,
    ProbeResult,
    Provenance,
    SearchPage,
    SearchRequest,
    WorkRecord,
)
from research_mcp.core.specs import RateSpec
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors

ADAPTER_VERSION = "1"

_HOST = "doaj.org"
_SEARCH_URL = f"https://{_HOST}/api/search/articles"
_PROBE_DOI = "10.1037/0003-066x.59.1.29"


def _identifier_value(bibjson: Any, scheme: str) -> str | None:
    for ident in bibjson.get("identifier", []):
        if ident.get("type") == scheme:
            value = ident.get("id")
            return value if isinstance(value, str) else None
    return None


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="doaj",
        title="DOAJ",
        group="scholarly",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.FULLTEXT}),
        id_schemes=frozenset({"doi"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # DOAJ publishes no fixed anonymous-caller number; a conservative rate [assumption].
        rate=RateSpec(rps=2, burst=2, concurrency=2),
        docs_url="https://doaj.org/api/docs",
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _oa_locations(bibjson: Any) -> list[OaLocation]:
    locations: list[OaLocation] = []
    for link in bibjson.get("link", []):
        url = link.get("url")
        if not url:
            continue
        kind: Literal["pdf", "html"] = "pdf" if url.lower().endswith(".pdf") else "html"
        locations.append(OaLocation(url=url, source="doaj", kind=kind))
    return locations


def _work_record(item: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    bibjson = item["bibjson"]
    doi_raw = _identifier_value(bibjson, "doi")
    if not doi_raw:
        raise ValueError("doaj article has no doi identifier")
    ident = Identifier("doi", normalize_doi(doi_raw))
    title = bibjson["title"]
    if not title:
        raise ValueError("doaj article has no title")
    year_raw = bibjson.get("year")
    year = int(year_raw) if year_raw else None
    published_at = None
    if year:
        month_raw = bibjson.get("month")
        published_at = date(year, int(month_raw) if month_raw else 1, 1)
    authors = [Author(name=a.get("name") or "") for a in bibjson.get("author", [])]
    venue = (bibjson.get("journal") or {}).get("title")
    return WorkRecord(
        ids=[ident],
        title=" ".join(title.split()),
        authors=authors,
        year=year,
        published_at=published_at,
        venue=venue,
        work_type="article",
        abstract=bibjson.get("abstract"),
        oa_locations=_oa_locations(bibjson),
        provenance=Provenance(
            source=source_id,
            upstream_id=item["id"],
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class DoajAdapter:
    """Translates the DOAJ Article Search API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _fetch(self, query: str, page: int, size: int) -> Any:
        """The raw, unparsed response; callers index into it in their own error context."""
        url = f"{_SEARCH_URL}/{quote(query, safe='')}"
        params = {"page": str(page), "pageSize": str(size)}
        return await self.ctx.http.get_json(url, source=self.spec.id, params=params)

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        page = int(req.cursor) if req.cursor else 1
        data: Any = await self._fetch(req.query, page, limit)
        total = data.get("total")
        records = [
            _work_record(item, self.spec.id, self.ctx.clock.now()) for item in data["results"]
        ]
        next_cursor = str(page + 1) if total is not None and page * limit < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        data: Any = await self._fetch(f'doi:"{ident.value}"', 1, 1)
        results = data["results"]
        if not results:
            return None
        return _work_record(results[0], self.spec.id, self.ctx.clock.now())

    async def fulltext_candidates(self, work: WorkRecord) -> list[FulltextCandidate]:
        return [
            FulltextCandidate(location=location, priority=index)
            for index, location in enumerate(work.oa_locations)
        ]

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
    ) -> Sequence[BaseModel]:
        return []

    async def updates(self, ident: Identifier) -> Sequence[BaseModel]:
        return []

    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data = await self._fetch(f'doi:"{_PROBE_DOI}"', 1, 1)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            results = data["results"]
            shape_ok = bool(results) and bool(results[0]["bibjson"]["title"])
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = DoajAdapter
