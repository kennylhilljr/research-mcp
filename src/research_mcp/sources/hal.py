"""The HAL adapter: JSON over https, no credential (LLD-sources-v3 5.1; PRD-sources-v5
SRC-20). Calls the HAL (Hyper Articles en Ligne) search API, keyed by a document's own
``halId_s`` (carried as a ``url`` identifier, since no HAL-specific scheme is registered in
``core/ids.py``) and, when present, its ``doiId_s``. Surfaces the document page as a
fulltext candidate when ``openAccess_bool`` is set.

The HAL Solr-backed response shape (``response.docs`` with ``halId_s``, ``title_s``,
``authFullName_s``, ``producedDate_s``, ``docType_s``, ``doiId_s``, ``uri_s`` and
``openAccess_bool``) is fixed here from the provider's published documentation and is not
itself tested against the live API; it is recorded as an assumption in the unit's handoff.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_doi, normalize_url
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

_HOST = "api.archives-ouvertes.fr"
_SEARCH_URL = f"https://{_HOST}/search/"
_PROBE_DOI = "10.1037/0003-066x.59.1.29"
_FIELDS = (
    "halId_s,title_s,authFullName_s,producedDate_s,docType_s,doiId_s,uri_s,abstract_s,"
    "openAccess_bool"
)
_DOC_TYPES = {
    "ART": "article",
    "COMM": "conference-paper",
    "THESE": "thesis",
    "OUV": "book",
    "COUV": "book-chapter",
    "REPORT": "report",
}


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="hal",
        title="HAL",
        group="repositories",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.FULLTEXT}),
        id_schemes=frozenset({"doi", "url"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # HAL publishes no fixed anonymous-caller number; a conservative rate [assumption].
        rate=RateSpec(rps=2, burst=4, concurrency=2),
        docs_url="https://api.archives-ouvertes.fr/docs",
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _hal_id_from_url(value: str) -> str:
    return urlsplit(value).path.lstrip("/").split("/")[0]


def _work_record(doc: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    hal_id = doc["halId_s"]
    permalink = doc.get("uri_s") or f"https://hal.science/{hal_id}"
    ids = [Identifier("url", normalize_url(permalink))]
    doi_raw = doc.get("doiId_s")
    if doi_raw:
        ids.append(Identifier("doi", normalize_doi(doi_raw)))
    titles = doc["title_s"]
    if not titles:
        raise ValueError("hal document has no title")
    title = titles[0]
    produced_raw = doc.get("producedDate_s")
    published_at = date.fromisoformat(produced_raw) if produced_raw else None
    abstracts = doc.get("abstract_s") or []
    oa_locations = []
    if doc.get("openAccess_bool"):
        oa_locations.append(OaLocation(url=f"{permalink}/document", source="hal", kind="pdf"))
    return WorkRecord(
        ids=ids,
        title=" ".join(title.split()),
        authors=[Author(name=name) for name in doc.get("authFullName_s", [])],
        year=published_at.year if published_at else None,
        published_at=published_at,
        work_type=_DOC_TYPES.get(doc.get("docType_s", ""), "article"),
        abstract=abstracts[0] if abstracts else None,
        oa_locations=oa_locations,
        provenance=Provenance(
            source=source_id,
            upstream_id=hal_id,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class HalAdapter:
    """Translates the HAL search API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _search_raw(self, query: str, start: int, rows: int) -> Any:
        """The raw, unparsed response; callers index it in their own error context."""
        params = {"q": query, "wt": "json", "rows": str(rows), "start": str(start), "fl": _FIELDS}
        return await self.ctx.http.get_json(_SEARCH_URL, source=self.spec.id, params=params)

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        start = int(req.cursor) if req.cursor else 0
        data: Any = await self._search_raw(req.query, start, limit)
        response = data["response"]
        total = response.get("numFound")
        records = [
            _work_record(doc, self.spec.id, self.ctx.clock.now()) for doc in response["docs"]
        ]
        next_start = start + limit
        next_cursor = str(next_start) if total is not None and next_start < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        if ident.scheme == "doi":
            query = f"doiId_s:{ident.value}"
        else:
            query = f"halId_s:{_hal_id_from_url(ident.value)}"
        data: Any = await self._search_raw(query, 0, 1)
        docs = data["response"]["docs"]
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
            data = await self._search_raw(f"doiId_s:{_PROBE_DOI}", 0, 1)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            docs = data["response"]["docs"]
            shape_ok = bool(docs) and bool(docs[0]["title_s"]) and bool(docs[0]["halId_s"])
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = HalAdapter
