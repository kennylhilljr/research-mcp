"""The OSF adapter: JSON:API over https, no auth (LLD-sources-v3 5.1; PRD-sources-v5 1.3 row
16). OSF hosts preprints for many providers (PsyArXiv, SocArXiv and others); ``SearchFilters
.provider`` restricts a search to one of them. Maps a preprint's own DOI (OSF mints DOIs with
prefix ``10.31234``) to a normalized ``Identifier`` and its landing page to a fulltext
candidate. The exact JSON:API shape (pagination params, the ``contributors`` embed) is not in
any approved document; it is this unit's ``[assumption]``, recorded in the handoff.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier, normalize_doi
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

_HOST = "api.osf.io"
_PREPRINTS_URL = f"https://{_HOST}/v2/preprints/"
_PROBE_ID = "ezcuj"
_EMBED = "contributors"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="osf",
        title="OSF Preprints",
        group="preprints",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.FULLTEXT}),
        id_schemes=frozenset({"doi"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # OSF publishes no fixed public rate limit; a conservative rate [assumption].
        rate=RateSpec(rps=2, burst=2, concurrency=2),
        max_page_size=100,
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _authors(item: Any) -> list[Author]:
    contributors = (((item.get("embeds") or {}).get("contributors") or {}).get("data")) or []
    authors = []
    for entry in contributors:
        user = (((entry.get("embeds") or {}).get("users") or {}).get("data") or {}).get(
            "attributes"
        ) or {}
        full_name = user.get("full_name")
        if full_name:
            authors.append(Author(name=full_name))
    return authors


def _work_record(item: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    attrs = item["attributes"]
    title = attrs.get("title")
    if not title:
        raise ValueError("osf preprint has no title")
    doi_raw = attrs.get("doi")
    if not doi_raw:
        raise ValueError("osf preprint has no doi")
    ident = Identifier("doi", normalize_doi(doi_raw))
    date_published = attrs.get("date_published")
    published_at = date.fromisoformat(date_published[:10]) if date_published else None
    provider = ((item.get("relationships") or {}).get("provider") or {}).get("data") or {}
    html = ((item.get("links") or {}).get("html")) or ""
    return WorkRecord(
        ids=[ident],
        title=" ".join(title.split()),
        authors=_authors(item),
        year=published_at.year if published_at else None,
        published_at=published_at,
        work_type="preprint",
        abstract=attrs.get("description"),
        oa_locations=([OaLocation(url=html, source=source_id, kind="landing")] if html else []),
        extra={"provider": provider.get("id")} if provider.get("id") else {},
        provenance=Provenance(
            source=source_id,
            upstream_id=item["id"],
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


def _guid_from_doi(doi_value: str) -> str:
    """The OSF guid is the last path segment of the preprint's own DOI (``.../osf.io/<guid>``)."""
    return doi_value.rstrip("/").rsplit("/", 1)[-1]


class OsfAdapter:
    """Translates the OSF Preprints JSON:API; it sleeps, retries and reads secrets never."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        page = int(req.cursor) if req.cursor else 1
        params = {
            "filter[q]": req.query,
            "page[size]": str(limit),
            "page": str(page),
            "embed": _EMBED,
        }
        if req.filters.provider:
            params["filter[provider]"] = req.filters.provider
        data: Any = await self.ctx.http.get_json(_PREPRINTS_URL, source=self.spec.id, params=params)
        records = [_work_record(item, self.spec.id, self.ctx.clock.now()) for item in data["data"]]
        has_next = bool((data.get("links") or {}).get("next"))
        return SearchPage(records=records, next_cursor=str(page + 1) if has_next else None)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        guid = _guid_from_doi(ident.value)
        try:
            data: Any = await self.ctx.http.get_json(
                f"{_PREPRINTS_URL}{guid}/", source=self.spec.id, params={"embed": _EMBED}
            )
        except HttpError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise
        return _work_record(data["data"], self.spec.id, self.ctx.clock.now())

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
            data: Any = await self.ctx.http.get_json(
                f"{_PREPRINTS_URL}{_PROBE_ID}/", source=self.spec.id, params={"embed": _EMBED}
            )
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            item = data["data"]
            shape_ok = bool(item["id"]) and bool(item["attributes"].get("title"))
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = OsfAdapter
