"""The PubMed adapter: NCBI E-utilities over https (LLD-sources-v3 5.1; PRD-sources-v5 row
22, "E-utilities"). A search resolves through ``esearch`` to a page of PubMed ids, then
``esummary`` maps the fields for those ids; an empty id list skips the second call, so
``search_empty`` costs one request. ``NCBI_API_KEY`` is optional and raises NCBI's published
rate past the anonymous figure used below [assumption].
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_pmid
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

_HOST = "eutils.ncbi.nlm.nih.gov"
_BASE = f"https://{_HOST}/entrez/eutils"
_ESEARCH_URL = f"{_BASE}/esearch.fcgi"
_ESUMMARY_URL = f"{_BASE}/esummary.fcgi"
# A stable, long-published PMID used only to check the upstream is alive [assumption].
_PROBE_PMID = "23555192"
_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="pubmed",
        title="PubMed",
        group="biomed",
        capabilities=frozenset({Capability.SEARCH, Capability.GET}),
        id_schemes=frozenset({"pmid"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("NCBI_API_KEY",),
            required=False,
            placement="query",
            param="api_key",
            origins=(f"https://{_HOST}",),
            signup_url="https://www.ncbi.nlm.nih.gov/account/",
        ),
        # NCBI's published anonymous rate is 3 requests per second [assumption].
        rate=RateSpec(rps=3, burst=3, concurrency=2),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _pubdate(text: str | None) -> tuple[int | None, date | None]:
    """ESummary's ``pubdate``: ``"2021 Jun 15"``, ``"2021 Jun"`` or just ``"2021"``."""
    if not text:
        return None, None
    parts = text.split()
    if not parts or not parts[0].isdigit():
        return None, None
    year = int(parts[0])
    month = _MONTHS.get(parts[1][:3].lower()) if len(parts) > 1 else None
    if month is None:
        return year, None
    day_text = parts[2] if len(parts) > 2 else None
    day = int(day_text) if day_text and day_text.isdigit() else 1
    return year, date(year, month, day)


def _authors(entry: Any) -> list[Author]:
    return [Author(name=name) for a in entry.get("authors", []) if (name := a.get("name"))]


def _work_record(entry: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    pmid = entry["uid"]
    title = entry.get("title")
    if not title:
        raise ValueError("pubmed docsum has no title")
    year, published_at = _pubdate(entry.get("pubdate"))
    return WorkRecord(
        ids=[Identifier("pmid", normalize_pmid(pmid))],
        title=" ".join(title.split()),
        authors=_authors(entry),
        year=year,
        published_at=published_at,
        venue=entry.get("fulljournalname"),
        work_type="article",
        provenance=Provenance(
            source=source_id,
            upstream_id=pmid,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class PubmedAdapter:
    """Translates NCBI's ESearch and ESummary E-utilities; it sleeps, retries and reads no
    secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        start = int(req.cursor) if req.cursor else 0
        params = {
            "db": "pubmed",
            "term": req.query,
            "retmode": "json",
            "retstart": str(start),
            "retmax": str(limit),
        }
        data: Any = await self.ctx.http.get_json(_ESEARCH_URL, source=self.spec.id, params=params)
        esearch = data["esearchresult"]
        ids = esearch.get("idlist", [])
        total_text = esearch.get("count")
        total = int(total_text) if total_text is not None else None
        if not ids:
            # Nothing to summarize: skip the second call rather than ask for an empty id list.
            return SearchPage(records=[], total=total, next_cursor=None)
        summary: Any = await self.ctx.http.get_json(
            _ESUMMARY_URL,
            source=self.spec.id,
            params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
        )
        result = summary["result"]
        records = [
            _work_record(result[uid], self.spec.id, self.ctx.clock.now()) for uid in result["uids"]
        ]
        next_start = start + limit
        next_cursor = str(next_start) if total is not None and next_start < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        data: Any = await self.ctx.http.get_json(
            _ESUMMARY_URL,
            source=self.spec.id,
            params={"db": "pubmed", "id": ident.value, "retmode": "json"},
        )
        result = data["result"]
        uids = result.get("uids", [])
        if not uids:
            return None
        return _work_record(result[uids[0]], self.spec.id, self.ctx.clock.now())

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
    ) -> Sequence[BaseModel]:
        return []

    async def updates(self, ident: Identifier) -> Sequence[BaseModel]:
        return []

    # @spec SRC-20
    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data: Any = await self.ctx.http.get_json(
                _ESUMMARY_URL,
                source=self.spec.id,
                params={"db": "pubmed", "id": _PROBE_PMID, "retmode": "json"},
            )
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            result = data["result"]
            uid = result["uids"][0]
            shape_ok = bool(result[uid].get("title"))
        except (KeyError, TypeError, IndexError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = PubmedAdapter
