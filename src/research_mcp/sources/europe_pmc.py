"""The Europe PMC adapter: JSON over https, no credential (LLD-sources-v3 5.1; PRD-sources-v5
row 21, "port the existing adapter; add PMC OA full text"). One ``search`` endpoint serves
search, get (by PMID, PMCID or DOI) and probe; PMC's ``fullTextUrlList`` becomes the record's
``OaLocation`` candidates that ``fulltext_candidates`` reads back (SRC-FR-9).
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_doi, normalize_pmcid, normalize_pmid
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

_HOST = "www.ebi.ac.uk"
_SEARCH_URL = f"https://{_HOST}/europepmc/webservices/rest/search"
# A stable, long-published PMID used only to check the upstream is alive [assumption].
_PROBE_QUERY = "EXT_ID:23555192 AND SRC:MED"
# How a ``get`` identifier scheme becomes an Europe PMC query term [assumption].
_GET_QUERIES = {
    "pmid": "EXT_ID:{value} AND SRC:MED",
    "pmcid": "PMCID:{value}",
    "doi": "DOI:{value}",
}


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="europe_pmc",
        title="Europe PMC",
        group="biomed",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.FULLTEXT}),
        id_schemes=frozenset({"pmid", "pmcid", "doi"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # Europe PMC publishes no fixed rate for anonymous callers; conservative [assumption].
        rate=RateSpec(rps=5, burst=5, concurrency=2),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _ids(item: Any) -> list[Identifier]:
    ids: list[Identifier] = []
    if item.get("pmid"):
        ids.append(Identifier("pmid", normalize_pmid(item["pmid"])))
    if item.get("pmcid"):
        ids.append(Identifier("pmcid", normalize_pmcid(item["pmcid"])))
    if item.get("doi"):
        ids.append(Identifier("doi", normalize_doi(item["doi"])))
    return ids


def _authors(author_string: str | None) -> list[Author]:
    if not author_string:
        return []
    return [Author(name=part) for name in author_string.split(",") if (part := name.strip())]


def _oa_locations(item: Any) -> list[OaLocation]:
    urls = ((item.get("fullTextUrlList") or {}).get("fullTextUrl")) or []
    locations: list[OaLocation] = []
    for entry in urls:
        url = entry.get("url")
        if not url:
            continue
        kind: Literal["pdf", "html"] = "pdf" if entry.get("documentStyle") == "pdf" else "html"
        locations.append(OaLocation(url=url, source="europe_pmc", kind=kind))
    return locations


def _work_record(item: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    ids = _ids(item)
    if not ids:
        raise ValueError("europe pmc record has no identifier")
    title = item.get("title")
    if not title:
        raise ValueError("europe pmc record has no title")
    pub_year = item.get("pubYear")
    year = int(pub_year) if pub_year and pub_year.isdigit() else None
    first_pub = item.get("firstPublicationDate")
    published_at = date.fromisoformat(first_pub) if first_pub else None
    return WorkRecord(
        ids=ids,
        title=" ".join(title.split()),
        authors=_authors(item.get("authorString")),
        year=year,
        published_at=published_at,
        venue=item.get("journalTitle"),
        work_type="article",
        abstract=item.get("abstractText"),
        oa_locations=_oa_locations(item),
        provenance=Provenance(
            source=source_id,
            upstream_id=item.get("id") or ids[0].value,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class EuropePmcAdapter:
    """Translates the Europe PMC REST search API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        params = {
            "query": req.query,
            "format": "json",
            "pageSize": str(limit),
            "resultType": "core",
        }
        if req.cursor:
            params["cursorMark"] = req.cursor
        data: Any = await self.ctx.http.get_json(_SEARCH_URL, source=self.spec.id, params=params)
        results = data["resultList"]["result"]
        records = [_work_record(item, self.spec.id, self.ctx.clock.now()) for item in results]
        next_cursor = data.get("nextCursorMark")
        # Europe PMC repeats the cursor mark on the last page; only a changed one means more.
        if next_cursor is None or next_cursor == req.cursor:
            next_cursor = None
        return SearchPage(records=records, total=data.get("hitCount"), next_cursor=next_cursor)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        template = _GET_QUERIES.get(ident.scheme)
        if template is None:
            return None
        params = {
            "query": template.format(value=ident.value),
            "format": "json",
            "pageSize": "1",
            "resultType": "core",
        }
        data: Any = await self.ctx.http.get_json(_SEARCH_URL, source=self.spec.id, params=params)
        results = data["resultList"]["result"]
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

    # @spec SRC-20
    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data: Any = await self.ctx.http.get_json(
                _SEARCH_URL,
                source=self.spec.id,
                params={
                    "query": _PROBE_QUERY,
                    "format": "json",
                    "pageSize": "1",
                    "resultType": "core",
                },
            )
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            results = data["resultList"]["result"]
            shape_ok = bool(results) and bool(results[0].get("title"))
        except (KeyError, TypeError, IndexError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = EuropePmcAdapter
