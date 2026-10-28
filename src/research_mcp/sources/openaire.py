"""The OpenAIRE adapter: JSON over https, no credential (LLD-sources-v3 5.1; PRD-sources-v5
SRC-20). Calls the OpenAIRE Graph API ``researchProducts`` endpoint, keyed by a research
product's ``doi`` pid, and surfaces its open-access ``instances`` as fulltext candidates.

The exact Graph API response shape (``header``/``results``, a ``pids`` list with
``scheme``/``value`` entries, ``authors`` with ``fullName``, and ``instances`` with
``urls``/``accessRight``) is fixed here from the provider's published documentation and is
not itself tested against the live API; it is recorded as an assumption in the unit's
handoff.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

from research_mcp.core.errors import HttpError
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

_HOST = "api.openaire.eu"
_PRODUCTS_URL = f"https://{_HOST}/graph/v1/researchProducts"
_PROBE_DOI = "10.1037/0003-066x.59.1.29"


def _pid(item: Any, scheme: str) -> str | None:
    for pid in item.get("pids", []):
        if pid.get("scheme") == scheme:
            value = pid.get("value")
            return value if isinstance(value, str) else None
    return None


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="openaire",
        title="OpenAIRE",
        group="scholarly",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.FULLTEXT}),
        id_schemes=frozenset({"doi"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # OpenAIRE publishes no fixed anonymous-caller number; a conservative rate [assumption].
        rate=RateSpec(rps=2, burst=4, concurrency=2),
        docs_url="https://graph.openaire.eu/docs/apis/search-api",
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _oa_locations(item: Any) -> list[OaLocation]:
    locations: list[OaLocation] = []
    for instance in item.get("instances", []):
        right = (instance.get("accessRight") or {}).get("code")
        if right != "OPEN":
            continue
        for url in instance.get("urls", []):
            kind: Literal["pdf", "html"] = "pdf" if url.lower().endswith(".pdf") else "html"
            locations.append(OaLocation(url=url, source="openaire", kind=kind))
    return locations


def _work_record(item: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    doi_raw = _pid(item, "doi")
    if not doi_raw:
        raise ValueError("openaire research product has no doi pid")
    ident = Identifier("doi", normalize_doi(doi_raw))
    title = item["mainTitle"]
    if not title:
        raise ValueError("openaire research product has no mainTitle")
    published_raw = item.get("publicationDate")
    published_at = date.fromisoformat(published_raw) if published_raw else None
    authors = [
        Author(name=a.get("fullName") or "", orcid=a.get("orcid")) for a in item.get("authors", [])
    ]
    descriptions = item.get("descriptions") or []
    return WorkRecord(
        ids=[ident],
        title=" ".join(title.split()),
        authors=authors,
        year=published_at.year if published_at else None,
        published_at=published_at,
        venue=item.get("publisher"),
        work_type=item.get("type") or "article",
        abstract=descriptions[0] if descriptions else None,
        oa_locations=_oa_locations(item),
        provenance=Provenance(
            source=source_id,
            upstream_id=item["id"],
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class OpenaireAdapter:
    """Translates the OpenAIRE Graph API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _fetch(self, params: dict[str, str]) -> Any:
        """The raw, unparsed response; callers index into it in their own error context."""
        return await self.ctx.http.get_json(_PRODUCTS_URL, source=self.spec.id, params=params)

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        page = int(req.cursor) if req.cursor else 1
        params = {"search": req.query, "page": str(page), "pageSize": str(limit)}
        data: Any = await self._fetch(params)
        header = data.get("header") or {}
        total = header.get("numFound")
        records = [
            _work_record(item, self.spec.id, self.ctx.clock.now()) for item in data["results"]
        ]
        next_cursor = str(page + 1) if total is not None and page * limit < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        data: Any = await self._fetch({"doi": ident.value, "pageSize": "1"})
        results = data["results"]
        if not results:
            return None
        return _work_record(results[0], self.spec.id, self.ctx.clock.now())

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
            data = await self._fetch({"doi": _PROBE_DOI, "pageSize": "1"})
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            results = data["results"]
            shape_ok = bool(results) and bool(results[0]["mainTitle"]) and bool(results[0]["id"])
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = OpenaireAdapter
