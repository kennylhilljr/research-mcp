"""The DBLP adapter: JSON over https, no auth (LLD-sources-v3 5.1; PRD-sources-v5 1.3 row
12). DBLP's publication search API blocks datacenter IPs as a bot defense but answers from
an ordinary residential or Mac connection; nothing in this adapter works around that. Only
``search`` is declared: DBLP has no per-publication fetch endpoint, so ``get`` is a stub a
registered source never calls (SRC-FR-2).
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal

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
from research_mcp.core.specs import RateSpec
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors

ADAPTER_VERSION = "1"

_HOST = "dblp.org"
_SEARCH_URL = f"https://{_HOST}/search/publ/api"
_PROBE_QUERY = "data management"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="dblp",
        title="DBLP",
        group="scholarly",
        capabilities=frozenset({Capability.SEARCH}),
        id_schemes=frozenset({"doi", "url"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # DBLP publishes no fixed rate for the search API; a conservative rate [assumption].
        rate=RateSpec(rps=2, burst=2, concurrency=1),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _as_list(value: Any) -> list[Any]:
    """DBLP collapses a single child to a bare object instead of a one-item list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _authors(info: Any) -> list[Author]:
    authors = (info.get("authors") or {}).get("author")
    return [
        Author(name=entry["text"])
        for entry in _as_list(authors)
        if isinstance(entry, dict) and entry.get("text")
    ]


def _ids(info: Any) -> list[Identifier]:
    ids = [Identifier("url", normalize_url(info["url"]))]
    doi = info.get("doi")
    if doi:
        ids.append(Identifier("doi", normalize_doi(doi)))
    return ids


def _year(info: Any) -> int | None:
    year = info.get("year")
    return int(year) if year else None


def _work_record(hit: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    info = hit["info"]
    title = info.get("title")
    if not title:
        raise ValueError("dblp hit has no title")
    year = _year(info)
    return WorkRecord(
        ids=_ids(info),
        title=" ".join(title.split()),
        authors=_authors(info),
        year=year,
        venue=info.get("venue"),
        work_type=info.get("type") or "article",
        provenance=Provenance(
            source=source_id,
            upstream_id=info.get("key") or info["url"],
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


def _hits(data: Any) -> list[Any]:
    return _as_list(data["result"]["hits"].get("hit"))


class DblpAdapter:
    """Translates the DBLP publication search API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        first = int(req.cursor) if req.cursor else 0
        params = {"q": req.query, "format": "json", "h": str(limit), "f": str(first)}
        data: Any = await self.ctx.http.get_json(_SEARCH_URL, source=self.spec.id, params=params)
        hits = data["result"]["hits"]
        total = int(hits["@total"])
        records = [_work_record(hit, self.spec.id, self.ctx.clock.now()) for hit in _hits(data)]
        next_first = first + limit
        next_cursor = str(next_first) if next_first < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    async def get(self, ident: Identifier) -> WorkRecord | None:
        return None

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

    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        params = {"q": _PROBE_QUERY, "format": "json", "h": "1", "f": "0"}
        try:
            data: Any = await self.ctx.http.get_json(
                _SEARCH_URL, source=self.spec.id, params=params
            )
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            hit = _hits(data)[0]
            shape_ok = bool(hit["info"].get("title"))
        except (KeyError, TypeError, IndexError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = DblpAdapter
