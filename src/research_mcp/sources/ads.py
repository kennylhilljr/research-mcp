"""The NASA ADS adapter: JSON over https, a required bearer token (LLD-sources-v3 5.1;
PRD-sources-v5 1.3 row 14). Disabled by default, like every source the owner has to switch
on and pay for (``enabled_by_default=False``). Maps a Solr ``bibcode`` document to a
``WorkRecord`` with its ADS abstract-page URL as the identifier, and its DOI too when ADS
has one; ``citations`` uses the Solr ``citations()``/``references()`` search operators
[assumption, unconfirmed against the live API].
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal
from urllib.parse import quote, unquote, urlsplit

from pydantic import BaseModel

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_doi, normalize_url
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
from research_mcp.core.specs import AuthSpec, RateSpec
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors

ADAPTER_VERSION = "1"

_HOST = "api.adsabs.harvard.edu"
_SEARCH_URL = f"https://{_HOST}/v1/search/query"
_FL = "bibcode,title,author,year,doi,pub,doctype,abstract"
_PROBE_BIBCODE = "2005ApJ...622..759B"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="ads",
        title="NASA ADS",
        group="scholarly",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.CITATIONS}),
        id_schemes=frozenset({"doi", "url"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("ADS_API_TOKEN",),
            required=True,
            placement="bearer",
            param="",
            origins=(f"https://{_HOST}",),
            signup_url="https://ui.adsabs.harvard.edu/user/settings/token",
        ),
        # ADS publishes a 5000-call daily limit per key; a conservative per-second rate
        # within it [assumption].
        rate=RateSpec(rps=2, burst=2, concurrency=2),
        enabled_by_default=False,
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _abstract_url(bibcode: str) -> str:
    return f"https://ui.adsabs.harvard.edu/abs/{quote(bibcode, safe='')}/abstract"


def _author(raw: str) -> Author:
    family, _, given = raw.partition(", ")
    name = f"{given} {family}".strip() if given else family
    return Author(name=name or raw, family=family or None)


def _ids(doc: Any) -> list[Identifier]:
    ids = [Identifier("url", normalize_url(_abstract_url(doc["bibcode"])))]
    doi = next(iter(doc.get("doi") or []), None)
    if doi:
        ids.append(Identifier("doi", normalize_doi(doi)))
    return ids


def _work_record(doc: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    title = next(iter(doc.get("title") or []), None)
    if not title:
        raise ValueError("ads doc has no title")
    year = doc.get("year")
    return WorkRecord(
        ids=_ids(doc),
        title=" ".join(title.split()),
        authors=[_author(entry) for entry in doc.get("author", [])],
        year=int(year) if year else None,
        venue=doc.get("pub"),
        work_type=doc.get("doctype") or "article",
        abstract=doc.get("abstract"),
        provenance=Provenance(
            source=source_id,
            upstream_id=doc["bibcode"],
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


def _bibcode_from_url(url: str) -> str:
    segments = urlsplit(url).path.rstrip("/").split("/")
    return unquote(segments[-2]) if len(segments) >= 2 else unquote(segments[-1])


def _bibcode_of(ident: Identifier) -> str:
    """The bibcode a query targets, from a ``doi``, ``url`` or raw-value identifier."""
    if ident.scheme == "url":
        return _bibcode_from_url(ident.value)
    return ident.value


def _ident_query(ident: Identifier) -> str:
    if ident.scheme == "doi":
        return f'doi:"{ident.value}"'
    return f'bibcode:"{_bibcode_of(ident)}"'


class AdsAdapter:
    """Translates the ADS Solr search API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _query(self, query: str, rows: int, start: int) -> Any:
        params = {"q": query, "rows": str(rows), "start": str(start), "fl": _FL}
        return await self.ctx.http.get_json(_SEARCH_URL, source=self.spec.id, params=params)

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        start = int(req.cursor) if req.cursor else 0
        data: Any = await self._query(req.query, limit, start)
        response = data["response"]
        total = response["numFound"]
        records = [
            _work_record(doc, self.spec.id, self.ctx.clock.now()) for doc in response["docs"]
        ]
        next_start = start + limit
        next_cursor = str(next_start) if next_start < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        data: Any = await self._query(_ident_query(ident), 1, 0)
        docs = data["response"]["docs"]
        if not docs:
            return None
        return _work_record(docs[0], self.spec.id, self.ctx.clock.now())

    async def fulltext_candidates(self, work: WorkRecord) -> list[FulltextCandidate]:
        return []

    @translate_errors
    async def citations(
        self,
        ident: Identifier,
        direction: Literal["citing", "cited"],
        cursor: str | None,
        limit: int,
    ) -> CitationPage:
        bibcode = _bibcode_of(ident) if ident.scheme != "doi" else None
        if bibcode is None:
            resolved = await self._query(_ident_query(ident), 1, 0)
            docs = resolved["response"]["docs"]
            if not docs:
                return CitationPage(ids=[])
            bibcode = docs[0]["bibcode"]
        operator = "citations" if direction == "citing" else "references"
        start = int(cursor) if cursor else 0
        data: Any = await self._query(f'{operator}(bibcode:"{bibcode}")', limit, start)
        response = data["response"]
        ids = [
            Identifier("url", normalize_url(_abstract_url(doc["bibcode"])))
            for doc in response["docs"]
        ]
        next_start = start + limit
        next_cursor = str(next_start) if next_start < response["numFound"] else None
        return CitationPage(ids=ids, next_cursor=next_cursor)

    async def search_authors(
        self, query: str | None, orcid: str | None, limit: int
    ) -> Sequence[BaseModel]:
        return []

    async def updates(self, ident: Identifier) -> Sequence[BaseModel]:
        return []

    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data = await self._query(f'bibcode:"{_PROBE_BIBCODE}"', 1, 0)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            docs = data["response"]["docs"]
            shape_ok = bool(docs) and bool(docs[0].get("title"))
        except (KeyError, TypeError, IndexError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = AdsAdapter
