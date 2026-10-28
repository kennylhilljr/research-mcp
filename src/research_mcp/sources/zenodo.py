"""The Zenodo adapter: JSON over https, an optional token for a higher rate (LLD-sources-v3
5.1, 4; PRD-sources-v5 SRC-20). Calls the Zenodo REST API, keyed by a record's ``doi``, and
surfaces its PDF files and record landing page as fulltext candidates. ``ZENODO_TOKEN`` is
not required: without it the anonymous rate applies (LLD-sources-v3 4 lists the Keychain item).

The Zenodo record shape (``hits.hits`` with ``id``, ``doi`` and ``metadata``) is fixed here
from the provider's published documentation and is not itself tested against the live API;
it is recorded as an assumption in the unit's handoff.
"""

from __future__ import annotations

import functools
import re
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
from research_mcp.core.specs import AuthSpec, RateSpec
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors

ADAPTER_VERSION = "1"

_HOST = "zenodo.org"
_RECORDS_URL = f"https://{_HOST}/api/records"
_PROBE_DOI = "10.5281/zenodo.1234567"
_ZENODO_DOI_SUFFIX = re.compile(r"zenodo\.(\d+)$", re.IGNORECASE)


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="zenodo",
        title="Zenodo",
        group="repositories",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.FULLTEXT}),
        id_schemes=frozenset({"doi"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("ZENODO_TOKEN",),
            required=False,
            placement="query",
            param="access_token",
            origins=(f"https://{_HOST}",),
            signup_url="https://zenodo.org/signup",
        ),
        # Zenodo publishes an anonymous limit of about 60 requests a minute; a
        # conservative rate [assumption].
        rate=RateSpec(rps=1, burst=5, concurrency=2),
        docs_url="https://developers.zenodo.org",
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _author(entry: Any) -> Author:
    name = entry.get("name") or ""
    family = name.split(",", 1)[0].strip() if "," in name else None
    return Author(name=name, family=family, orcid=entry.get("orcid"))


def _oa_locations(item: Any) -> list[OaLocation]:
    locations = [
        OaLocation(url=f"https://{_HOST}/records/{item['id']}", source="zenodo", kind="landing")
    ]
    for file_entry in item.get("files", []):
        key = file_entry.get("key", "")
        link = (file_entry.get("links") or {}).get("self")
        if link and key.lower().endswith(".pdf"):
            locations.append(OaLocation(url=link, source="zenodo", kind="pdf"))
    return locations


def _work_record(item: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    ident = Identifier("doi", normalize_doi(item["doi"]))
    metadata = item["metadata"]
    title = metadata["title"]
    if not title:
        raise ValueError("zenodo record has no title")
    published_raw = metadata.get("publication_date")
    published_at = date.fromisoformat(published_raw) if published_raw else None
    work_type = (metadata.get("resource_type") or {}).get("type") or "article"
    return WorkRecord(
        ids=[ident],
        title=" ".join(title.split()),
        authors=[_author(entry) for entry in metadata.get("creators", [])],
        year=published_at.year if published_at else None,
        published_at=published_at,
        work_type=work_type,
        abstract=metadata.get("description"),
        oa_locations=_oa_locations(item),
        provenance=Provenance(
            source=source_id,
            upstream_id=str(item["id"]),
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class ZenodoAdapter:
    """Translates the Zenodo REST API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _search_raw(self, query: str, page: int, size: int) -> Any:
        """The raw, unparsed search response; callers index it in their own error context."""
        params = {"q": query, "size": str(size), "page": str(page)}
        return await self.ctx.http.get_json(_RECORDS_URL, source=self.spec.id, params=params)

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        page = int(req.cursor) if req.cursor else 1
        data: Any = await self._search_raw(req.query, page, limit)
        hits = data["hits"]
        total = hits.get("total")
        records = [_work_record(item, self.spec.id, self.ctx.clock.now()) for item in hits["hits"]]
        next_cursor = str(page + 1) if total is not None and page * limit < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        direct = _ZENODO_DOI_SUFFIX.search(ident.value)
        if direct:
            try:
                item: Any = await self.ctx.http.get_json(
                    f"{_RECORDS_URL}/{direct[1]}", source=self.spec.id
                )
            except HttpError as exc:
                if exc.code is ErrorCode.NOT_FOUND:
                    return None
                raise
            return _work_record(item, self.spec.id, self.ctx.clock.now())
        data: Any = await self._search_raw(f'doi:"{ident.value}"', 1, 1)
        hits = data["hits"]["hits"]
        if not hits:
            return None
        return _work_record(hits[0], self.spec.id, self.ctx.clock.now())

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
            data = await self._search_raw(f'doi:"{_PROBE_DOI}"', 1, 1)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            hits = data["hits"]["hits"]
            shape_ok = bool(hits) and bool(hits[0]["metadata"]["title"]) and bool(hits[0]["doi"])
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = ZenodoAdapter
