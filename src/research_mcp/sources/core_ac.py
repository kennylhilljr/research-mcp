"""The CORE adapter: the v3 REST API over https, a required bearer API key
(LLD-sources-v3 4, 5.1, 5.5; PRD-sources-v5 SRC-20). Maps a work's ``id`` and ``doi`` to
normalized identifiers and its ``downloadUrl`` to a full-text PDF location. The key is
attached only to CORE origins (SRC-INV-6), enforced by the shared HTTP client's policy.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier, normalize_core, normalize_doi
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

_HOST = "api.core.ac.uk"
_BASE_URL = f"https://{_HOST}/v3"
_WORKS_URL = f"{_BASE_URL}/works"
_SEARCH_URL = f"{_BASE_URL}/search/works"
# A CORE work id used only as the probe target; any existing numeric id works, confirmed
# against the live API before this probe is relied on [assumption].
_PROBE_ID = "38953630"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="core",
        title="CORE",
        group="scholarly",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.FULLTEXT}),
        id_schemes=frozenset({"doi", "core"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("CORE_API_KEY",),
            required=True,
            placement="bearer",
            param="",
            origins=(f"https://{_HOST}",),
            signup_url="https://core.ac.uk/services/api",
        ),
        # CORE's free tier publishes a low request rate; a conservative figure
        # [assumption].
        rate=RateSpec(rps=1, burst=2, concurrency=1),
        max_page_size=100,
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _author(entry: Any) -> Author:
    return Author(name=entry.get("name") or "")


def _oa_locations(data: Any) -> list[OaLocation]:
    download_url = data.get("downloadUrl")
    if not download_url:
        return []
    return [OaLocation(url=download_url, source="core", kind="pdf")]


def _core_ident(raw: object) -> Identifier:
    return Identifier("core", normalize_core(str(raw)))


def _work_record(data: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    ids = [_core_ident(data["id"])]
    doi_raw = data.get("doi")
    if doi_raw:
        ids.append(Identifier("doi", normalize_doi(doi_raw)))
    title = data.get("title")
    if not title:
        raise ValueError("core work has no title")
    return WorkRecord(
        ids=ids,
        title=" ".join(title.split()),
        authors=[_author(entry) for entry in data.get("authors", [])],
        year=data.get("yearPublished"),
        venue=data.get("publisher"),
        work_type=data.get("documentType") or "article",
        abstract=data.get("abstract"),
        oa_locations=_oa_locations(data),
        provenance=Provenance(
            source=source_id,
            upstream_id=str(data["id"]),
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class CoreAdapter:
    """Translates the CORE v3 REST API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _fetch_work(self, work_id: str) -> Any:
        """``works/<id>``; ``None`` for a 404."""
        try:
            data: Any = await self.ctx.http.get_json(f"{_WORKS_URL}/{work_id}", source=self.spec.id)
        except HttpError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise
        return data

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        offset = int(req.cursor) if req.cursor else 0
        params = {"q": req.query, "limit": str(limit), "offset": str(offset)}
        data: Any = await self.ctx.http.get_json(_SEARCH_URL, source=self.spec.id, params=params)
        records = [
            _work_record(item, self.spec.id, self.ctx.clock.now()) for item in data["results"]
        ]
        total = data.get("totalHits")
        next_offset = offset + limit
        next_cursor = str(next_offset) if total is not None and next_offset < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        # CORE's REST API resolves "works/<id>" with either its own numeric id or a DOI
        # [assumption]; confirmed against the live API before this is relied on.
        data = await self._fetch_work(ident.value)
        if data is None:
            return None
        return _work_record(data, self.spec.id, self.ctx.clock.now())

    # @spec SRC-20
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
            data = await self._fetch_work(_PROBE_ID)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            shape_ok = bool((data or {})["id"]) and bool((data or {}).get("title"))
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = CoreAdapter
