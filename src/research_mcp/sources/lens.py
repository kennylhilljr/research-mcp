"""The Lens.org adapter: JSON over https, a required bearer token (LLD-sources-v3 5.1;
PRD-sources-v5 1.3 row 15). Disabled by default, like every source the owner has to switch
on and pay for (``enabled_by_default=False``). Uses the Scholarly Search API, which answers
a JSON body over ``POST`` rather than query parameters; the catalog note calls this source
"patents", which is the Lens Patent API on a different endpoint. This unit ships the
scholarly endpoint [assumption, flagged for the owner to confirm which the catalog means].
Only ``search`` is declared: Lens's scholarly search has no per-record fetch by id, so
``get`` is a stub a registered source never calls (SRC-FR-2).
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal
from urllib.parse import quote

from pydantic import BaseModel

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_doi, normalize_url
from research_mcp.core.models import (
    Author,
    CitationPage,
    FulltextCandidate,
    JsonValue,
    ProbeResult,
    Provenance,
    SearchPage,
    SearchRequest,
    WorkRecord,
)
from research_mcp.core.specs import AuthSpec, RateSpec
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors

ADAPTER_VERSION = "1"

_HOST = "api.lens.org"
_SEARCH_URL = f"https://{_HOST}/scholarly/search"
_INCLUDE = ("lens_id", "title", "year_published", "authors", "external_ids", "source")
_PROBE_QUERY = "research"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="lens",
        title="Lens.org",
        group="scholarly",
        capabilities=frozenset({Capability.SEARCH}),
        id_schemes=frozenset({"doi", "url"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("LENS_API_TOKEN",),
            required=True,
            placement="bearer",
            param="",
            origins=(f"https://{_HOST}",),
            signup_url="https://www.lens.org/lens/user/subscriptions",
        ),
        # Lens's free scholarly tier publishes a modest per-minute cap; a conservative rate
        # within it [assumption].
        rate=RateSpec(rps=1, burst=2, concurrency=1),
        enabled_by_default=False,
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _article_url(lens_id: str) -> str:
    return f"https://www.lens.org/lens/scholar/article/{quote(lens_id, safe='')}"


def _author(entry: Any) -> Author:
    given = entry.get("first_name")
    family = entry.get("last_name")
    name = " ".join(part for part in (given, family) if part)
    return Author(name=name, family=family)


def _doi(item: Any) -> str | None:
    for entry in item.get("external_ids") or []:
        if entry.get("type") == "doi" and entry.get("value"):
            return str(entry["value"])
    return None


def _ids(item: Any) -> list[Identifier]:
    ids = [Identifier("url", normalize_url(_article_url(item["lens_id"])))]
    doi = _doi(item)
    if doi:
        ids.append(Identifier("doi", normalize_doi(doi)))
    return ids


def _work_record(item: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    title = item.get("title")
    if not title:
        raise ValueError("lens item has no title")
    return WorkRecord(
        ids=_ids(item),
        title=" ".join(title.split()),
        authors=[_author(entry) for entry in item.get("authors", [])],
        year=item.get("year_published"),
        venue=(item.get("source") or {}).get("title"),
        provenance=Provenance(
            source=source_id,
            upstream_id=item["lens_id"],
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class LensAdapter:
    """Translates the Lens.org Scholarly Search API; it sleeps, retries and reads no
    secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _search(self, query: str, size: int, offset: int) -> Any:
        body: JsonValue = {
            "query": query,
            "size": size,
            "from": offset,
            "include": list(_INCLUDE),
        }
        return await self.ctx.http.post_json(_SEARCH_URL, source=self.spec.id, json=body)

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        offset = int(req.cursor) if req.cursor else 0
        data: Any = await self._search(req.query, limit, offset)
        total = data["total"]
        records = [_work_record(item, self.spec.id, self.ctx.clock.now()) for item in data["data"]]
        next_offset = offset + limit
        next_cursor = str(next_offset) if next_offset < total else None
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
        try:
            data = await self._search(_PROBE_QUERY, 1, 0)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            items = data["data"]
            shape_ok = bool(items) and bool(items[0].get("lens_id")) and bool(items[0].get("title"))
        except (KeyError, TypeError, IndexError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = LensAdapter
