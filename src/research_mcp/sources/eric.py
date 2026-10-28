"""The ERIC adapter: JSON over https, no credential (LLD-sources-v3 5.1; PRD-sources-v5
SRC-20, catalog row 38: "education research"). ERIC has no registered identifier scheme of
its own, so a record's id is its ERIC landing page as a normalized ``url`` identifier, with
the accession number kept in ``extra``; ``get`` reads that number back out of the url when
one is given, and otherwise uses the identifier's value as the accession number directly.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from typing import Any, Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_url
from research_mcp.core.models import (
    Author,
    CitationPage,
    FulltextCandidate,
    ProbeResult,
    Provenance,
    SearchPage,
    SearchRequest,
    WorkRecord,
)
from research_mcp.core.specs import RateSpec
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors

ADAPTER_VERSION = "1"

_HOST = "api.ies.ed.gov"
_SEARCH_URL = f"https://{_HOST}/eric/"
_LANDING_URL = "https://eric.ed.gov/"
_PROBE_ID = "EJ1197742"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="eric",
        title="ERIC",
        group="education",
        capabilities=frozenset({Capability.SEARCH, Capability.GET}),
        id_schemes=frozenset({"url"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # ERIC publishes no fixed caller number; a conservative rate [assumption].
        rate=RateSpec(rps=2, burst=5, concurrency=2),
        docs_url="https://eric.ed.gov",
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _accession_from_ident(ident: Identifier) -> str:
    """The ERIC accession number from a ``url`` identifier's ``id`` query parameter, or the
    identifier's bare value when it carries none (for example a caller that already holds
    the accession number, or the generic conformance identifier)."""
    if ident.value.startswith("http://") or ident.value.startswith("https://"):
        query = parse_qs(urlsplit(ident.value).query)
        found = query.get("id")
        if found:
            return found[0]
    return ident.value


def _landing_identifier(accession: str) -> Identifier:
    return Identifier("url", normalize_url(f"{_LANDING_URL}?id={accession}"))


def _author(name: str) -> Author:
    return Author(name=name)


def _work_record(doc: Any, source_id: str, retrieved_at: Any) -> WorkRecord:
    accession = doc["id"]
    title = doc.get("title")
    if not title:
        raise ValueError("eric doc has no title")
    year_raw = doc.get("publicationdateyear")
    year = int(year_raw) if year_raw else None
    work_type = next(iter(doc.get("publicationtype") or []), "article")
    return WorkRecord(
        ids=[_landing_identifier(accession)],
        title=" ".join(str(title).split()),
        authors=[_author(name) for name in doc.get("author") or []],
        year=year,
        work_type=work_type,
        abstract=doc.get("description"),
        extra={"eric_id": accession, "subject": list(doc.get("subject") or [])},
        provenance=Provenance(
            source=source_id,
            upstream_id=accession,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class EricAdapter:
    """Translates the ERIC search API; it sleeps, retries and reads secrets never."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _docs(self, params: dict[str, str]) -> Any:
        """The raw response body; callers unwrap ``response`` so a malformed body raises
        inside their own ``translate_errors`` scope rather than this shared helper's."""
        return await self.ctx.http.get_json(_SEARCH_URL, source=self.spec.id, params=params)

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        start = int(req.cursor) if req.cursor else 0
        data = await self._docs(
            {"search": req.query, "format": "json", "start": str(start), "rows": str(limit)}
        )
        response = data["response"]
        total = response.get("numFound")
        records = [
            _work_record(doc, self.spec.id, self.ctx.clock.now())
            for doc in response.get("docs", [])
        ]
        next_start = start + limit
        next_cursor = str(next_start) if total is not None and next_start < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        accession = _accession_from_ident(ident)
        data = await self._docs({"search": f"id:{accession}", "format": "json", "rows": "1"})
        docs = data["response"].get("docs", [])
        if not docs:
            return None
        return _work_record(docs[0], self.spec.id, self.ctx.clock.now())

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
            data = await self._docs({"search": f"id:{_PROBE_ID}", "format": "json", "rows": "1"})
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            docs = data["response"]["docs"]
            shape_ok = bool(docs) and bool(docs[0].get("id")) and bool(docs[0].get("title"))
        except (KeyError, TypeError, IndexError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = EricAdapter
