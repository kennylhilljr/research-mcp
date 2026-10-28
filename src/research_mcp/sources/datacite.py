"""The DataCite adapter: the public JSON:API over https, no credential (LLD-sources-v3 5.1,
5.5; PRD-sources-v5 SRC-20). Maps a DOI record's ``attributes.titles`` and ``creators`` to a
``WorkRecord``, and its resolvable ``attributes.url`` to a landing-page OA location.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import datetime
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

_HOST = "api.datacite.org"
_DOIS_URL = f"https://{_HOST}/dois"
# A Dryad dataset DOI used widely as a DataCite example record [assumption].
_PROBE_DOI = "10.5061/dryad.8515"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="datacite",
        title="DataCite",
        group="scholarly",
        capabilities=frozenset({Capability.SEARCH, Capability.GET}),
        id_schemes=frozenset({"doi"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # DataCite publishes no fixed number for the public REST API; a conservative rate
        # for shared infrastructure [assumption].
        rate=RateSpec(rps=3, burst=3, concurrency=2),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _author(entry: Any) -> Author:
    given = entry.get("givenName")
    family = entry.get("familyName")
    name = " ".join(part for part in (given, family) if part) or entry.get("name") or ""
    return Author(name=name, family=family)


def _abstract(attributes: Any) -> str | None:
    for entry in attributes.get("descriptions") or []:
        if entry.get("descriptionType") == "Abstract" and entry.get("description"):
            return str(entry["description"])
    return None


def _oa_locations(attributes: Any) -> list[OaLocation]:
    url = attributes.get("url")
    if not url:
        return []
    return [OaLocation(url=url, source="datacite", kind="landing")]


def _work_record(entry: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    attributes = entry["attributes"]
    ident = Identifier("doi", normalize_doi(entry["id"]))
    titles = attributes.get("titles") or []
    if not titles or not titles[0].get("title"):
        raise ValueError("datacite record has no title")
    title = " ".join(titles[0]["title"].split())
    work_type = ((attributes.get("types") or {}).get("resourceTypeGeneral") or "dataset").lower()
    return WorkRecord(
        ids=[ident],
        title=title,
        authors=[_author(entry) for entry in attributes.get("creators", [])],
        year=attributes.get("publicationYear"),
        venue=attributes.get("publisher"),
        work_type=work_type,
        abstract=_abstract(attributes),
        oa_locations=_oa_locations(attributes),
        provenance=Provenance(
            source=source_id,
            upstream_id=ident.value,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class DataciteAdapter:
    """Translates the DataCite REST API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _fetch_work(self, doi_value: str) -> Any:
        """``dois/<doi>``; ``None`` for a 404."""
        try:
            data: Any = await self.ctx.http.get_json(
                f"{_DOIS_URL}/{doi_value}", source=self.spec.id
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
        page_number = int(req.cursor) if req.cursor else 1
        params = {
            "query": req.query,
            "page[size]": str(limit),
            "page[number]": str(page_number),
        }
        data: Any = await self.ctx.http.get_json(_DOIS_URL, source=self.spec.id, params=params)
        records = [_work_record(item, self.spec.id, self.ctx.clock.now()) for item in data["data"]]
        total = (data.get("meta") or {}).get("total")
        seen = page_number * limit
        next_cursor = str(page_number + 1) if total is not None and seen < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        data = await self._fetch_work(ident.value)
        if data is None:
            return None
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
            data = await self._fetch_work(_PROBE_DOI)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            entry = (data or {})["data"]
            titles = entry["attributes"].get("titles") or []
            shape_ok = bool(entry.get("id")) and bool(titles)
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = DataciteAdapter
