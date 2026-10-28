"""The Semantic Scholar adapter: the Graph API over https, an optional API key
(LLD-sources-v3 5.1, 5.5; PRD-sources-v5 SRC-20). Maps a paper's ``externalIds.DOI`` and
``paperId`` to normalized identifiers, its ``openAccessPdf`` to an OA location, and declares
the ``citations`` capability over the ``/citations`` and ``/references`` endpoints.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier, normalize_doi, normalize_s2
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
from research_mcp.core.specs import AuthSpec, RateSpec
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors

ADAPTER_VERSION = "1"

_HOST = "api.semanticscholar.org"
_BASE_URL = f"https://{_HOST}/graph/v1"
_PAPER_URL = f"{_BASE_URL}/paper"
# A placeholder paperId (40 lowercase hex characters, the shape Semantic Scholar assigns);
# confirmed against a real, stable paper before this probe is relied on [assumption].
_PROBE_ID = "544783878925a1e49473ad93329796726b5fa592"
_FIELDS = "paperId,externalIds,title,abstract,year,venue,publicationDate,authors,openAccessPdf"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="semantic_scholar",
        title="Semantic Scholar",
        group="scholarly",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.CITATIONS}),
        id_schemes=frozenset({"doi", "s2"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("SEMANTIC_SCHOLAR_API_KEY",),
            required=False,
            placement="header",
            param="x-api-key",
            origins=(f"https://{_HOST}",),
            signup_url="https://www.semanticscholar.org/product/api",
        ),
        # The shared unauthenticated pool is published as a low, strict rate; a key raises
        # it, but the client holds one shared policy, so the conservative figure is used
        # for both cases [assumption].
        rate=RateSpec(rps=1, burst=1, concurrency=1),
        max_page_size=100,
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _author(entry: Any) -> Author:
    return Author(name=entry.get("name") or "")


def _oa_locations(data: Any) -> list[OaLocation]:
    pdf = data.get("openAccessPdf")
    if not pdf or not pdf.get("url"):
        return []
    return [OaLocation(url=pdf["url"], source="semantic_scholar", kind="pdf")]


def _s2_ident(raw: str) -> Identifier:
    return Identifier("s2", normalize_s2(raw))


def _work_record(data: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    ids = [_s2_ident(data["paperId"])]
    doi_raw = (data.get("externalIds") or {}).get("DOI")
    if doi_raw:
        ids.append(Identifier("doi", normalize_doi(doi_raw)))
    title = data.get("title")
    if not title:
        raise ValueError("semantic scholar paper has no title")
    published_at = (
        date.fromisoformat(data["publicationDate"]) if data.get("publicationDate") else None
    )
    return WorkRecord(
        ids=ids,
        title=" ".join(title.split()),
        authors=[_author(entry) for entry in data.get("authors", [])],
        year=data.get("year"),
        published_at=published_at,
        venue=data.get("venue"),
        work_type="article",
        abstract=data.get("abstract"),
        oa_locations=_oa_locations(data),
        provenance=Provenance(
            source=source_id,
            upstream_id=data["paperId"],
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


def _paper_path(ident: Identifier) -> str:
    return f"DOI:{ident.value}" if ident.scheme == "doi" else ident.value


class SemanticScholarAdapter:
    """Translates the Semantic Scholar Graph API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _fetch_work(self, ident: Identifier) -> Any:
        """``paper/<id>``; ``None`` for a 404."""
        try:
            data: Any = await self.ctx.http.get_json(
                f"{_PAPER_URL}/{_paper_path(ident)}",
                source=self.spec.id,
                params={"fields": _FIELDS},
            )
        except HttpError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise
        return data

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        params = {
            "query": req.query,
            "limit": str(limit),
            "offset": req.cursor or "0",
            "fields": _FIELDS,
        }
        data: Any = await self.ctx.http.get_json(
            f"{_PAPER_URL}/search", source=self.spec.id, params=params
        )
        records = [_work_record(item, self.spec.id, self.ctx.clock.now()) for item in data["data"]]
        next_offset = data.get("next")
        return SearchPage(
            records=records,
            total=data.get("total"),
            next_cursor=str(next_offset) if next_offset is not None else None,
        )

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        data = await self._fetch_work(ident)
        if data is None:
            return None
        return _work_record(data, self.spec.id, self.ctx.clock.now())

    async def fulltext_candidates(self, work: WorkRecord) -> list[FulltextCandidate]:
        return [
            FulltextCandidate(location=location, priority=index)
            for index, location in enumerate(work.oa_locations)
        ]

    # @spec SRC-20
    @translate_errors
    async def citations(
        self,
        ident: Identifier,
        direction: Literal["citing", "cited"],
        cursor: str | None,
        limit: int,
    ) -> CitationPage:
        endpoint = "citations" if direction == "citing" else "references"
        wrapper_key = "citingPaper" if direction == "citing" else "citedPaper"
        offset = cursor or "0"
        params = {
            "offset": offset,
            "limit": str(min(limit, self.spec.max_page_size)),
            "fields": "paperId,externalIds",
        }
        data: Any = await self.ctx.http.get_json(
            f"{_PAPER_URL}/{_paper_path(ident)}/{endpoint}", source=self.spec.id, params=params
        )
        ids: list[Identifier] = []
        for entry in data["data"]:
            paper = entry.get(wrapper_key) or {}
            if not paper.get("paperId"):
                continue
            doi_raw = (paper.get("externalIds") or {}).get("DOI")
            ids.append(
                Identifier("doi", normalize_doi(doi_raw))
                if doi_raw
                else _s2_ident(paper["paperId"])
            )
        next_offset = data.get("next")
        return CitationPage(
            ids=ids, next_cursor=str(next_offset) if next_offset is not None else None
        )

    async def search_authors(
        self, query: str | None, orcid: str | None, limit: int
    ) -> Sequence[BaseModel]:
        return []

    async def updates(self, ident: Identifier) -> Sequence[BaseModel]:
        return []

    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data = await self._fetch_work(Identifier("s2", _PROBE_ID))
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            shape_ok = bool((data or {})["paperId"]) and bool((data or {}).get("title"))
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = SemanticScholarAdapter
