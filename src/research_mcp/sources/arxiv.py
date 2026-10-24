"""The arXiv adapter: Atom XML over https, 1 request per 3 seconds (LLD-sources-v2 5.1;
PRD-sources-v5 SRC-10). Maps arXiv ids (with their version) to normalized ``Identifier``s
and the PDF link arXiv always publishes to an ``OaLocation`` fulltext candidate.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring
from pydantic import BaseModel

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_arxiv
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

_HOST = "export.arxiv.org"
_QUERY_URL = f"https://{_HOST}/api/query"
_ATOM = "{http://www.w3.org/2005/Atom}"
_OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"
_ERROR_ID_PREFIX = "http://arxiv.org/api/errors"
_PROBE_ID = "0704.0001"


# @spec SRC-10
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="arxiv",
        title="arXiv",
        group="preprints",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.FULLTEXT}),
        id_schemes=frozenset({"arxiv"}),
        hosts=frozenset({_HOST}),
        auth=None,
        rate=RateSpec(rps=1 / 3, burst=1, concurrency=1),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _find_text(elem: Any, tag: str) -> str | None:
    found = elem.find(tag)
    if found is None or found.text is None:
        return None
    text = found.text.strip()
    return text or None


def _published_date(text: str | None) -> date | None:
    if text is None:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00")).date()


def _entry_id(entry: Any) -> str | None:
    """The entry's ``<id>`` text, or ``None`` for an arXiv API error entry."""
    raw_id = _find_text(entry, f"{_ATOM}id")
    if raw_id is None or raw_id.startswith(_ERROR_ID_PREFIX):
        return None
    return raw_id


def _pdf_location(entry: Any) -> OaLocation | None:
    for link in entry.findall(f"{_ATOM}link"):
        if link.get("title") == "pdf":
            href = link.get("href")
            if href:
                return OaLocation(url=href, source="arxiv", kind="pdf")
    return None


def _work_record(entry: Any, source_id: str, retrieved_at: datetime) -> WorkRecord | None:
    raw_id = _entry_id(entry)
    if raw_id is None:
        return None
    value, version = normalize_arxiv(raw_id)
    ident = Identifier("arxiv", value, version)
    title = _find_text(entry, f"{_ATOM}title")
    if title is None:
        raise ValueError("arxiv entry has no title")
    summary = _find_text(entry, f"{_ATOM}summary")
    published = _published_date(_find_text(entry, f"{_ATOM}published"))
    authors = [
        Author(name=name)
        for author in entry.findall(f"{_ATOM}author")
        if (name := _find_text(author, f"{_ATOM}name")) is not None
    ]
    oa = _pdf_location(entry)
    return WorkRecord(
        ids=[ident],
        title=" ".join(title.split()),
        authors=authors,
        year=published.year if published else None,
        published_at=published,
        work_type="preprint",
        abstract=" ".join(summary.split()) if summary else None,
        oa_locations=[oa] if oa is not None else [],
        provenance=Provenance(
            source=source_id,
            upstream_id=value,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


def _id_list_value(ident: Identifier) -> str:
    return ident.value if ident.version is None else f"{ident.value}v{ident.version}"


class ArxivAdapter:
    """Translates the arXiv Atom API; it sleeps, retries and reads secrets never."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    # @spec SRC-10
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        start = int(req.cursor) if req.cursor else 0
        response = await self.ctx.http.get_text(
            _QUERY_URL,
            source=self.spec.id,
            params={
                "search_query": f"all:{req.query}",
                "start": str(start),
                "max_results": str(limit),
            },
        )
        feed = fromstring(response.text)
        total_text = _find_text(feed, f"{_OPENSEARCH}totalResults")
        total = int(total_text) if total_text is not None else None
        records = [
            record
            for entry in feed.findall(f"{_ATOM}entry")
            if (record := _work_record(entry, self.spec.id, self.ctx.clock.now())) is not None
        ]
        next_start = start + limit
        next_cursor = str(next_start) if total is not None and next_start < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        response = await self.ctx.http.get_text(
            _QUERY_URL,
            source=self.spec.id,
            params={"id_list": _id_list_value(ident), "max_results": "1"},
        )
        feed = fromstring(response.text)
        entry = feed.find(f"{_ATOM}entry")
        if entry is None:
            return None
        return _work_record(entry, self.spec.id, self.ctx.clock.now())

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
            response = await self.ctx.http.get_text(
                _QUERY_URL,
                source=self.spec.id,
                params={"id_list": _PROBE_ID, "max_results": "1"},
            )
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            feed = fromstring(response.text)
            entry = feed.find(f"{_ATOM}entry")
            shape_ok = (
                entry is not None
                and _entry_id(entry) is not None
                and _find_text(entry, f"{_ATOM}title") is not None
            )
        except (ParseError, DefusedXmlException):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = ArxivAdapter
