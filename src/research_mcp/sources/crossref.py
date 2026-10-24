"""The Crossref adapter: JSON over https, polite pool (LLD-sources-v2 5.1; PRD-sources-v5
SRC-11). Sends the owner's contact address as ``mailto`` on every request, maps a work's
``DOI`` to a normalized ``Identifier`` and its ``issued`` date-parts to a calendar date, and
declares the ``updates`` capability over Crossref's ``update-to`` field.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier, normalize_doi
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

_HOST = "api.crossref.org"
_WORKS_URL = f"https://{_HOST}/works"
_PROBE_DOI = "10.1037/0003-066x.59.1.29"


# @spec SRC-11
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="crossref",
        title="Crossref",
        group="scholarly",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.UPDATES}),
        id_schemes=frozenset({"doi"}),
        hosts=frozenset({_HOST}),
        auth=None,
        needs_contact=True,
        # Crossref publishes no fixed polite-pool number; a conservative rate [assumption].
        rate=RateSpec(rps=5, burst=5, concurrency=2),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class CrossrefUpdate(BaseModel):
    """One ``update-to`` entry: a correction, retraction or new version of a work.

    Not yet in ``core/models.py`` (LLD-sources-v2 2.1, 5.13); the fields are fixed here from
    the Crossref fixtures until a shared ``UpdateNotice`` model exists [assumption].
    """

    model_config = ConfigDict(defer_build=True)

    kind: str
    related: Identifier | None
    date: date | None
    source: str


def _issued_date(parts_obj: Any) -> date | None:
    if not isinstance(parts_obj, dict):
        return None
    parts = parts_obj.get("date-parts")
    if not parts or not parts[0] or parts[0][0] is None:
        return None
    year, *rest = parts[0]
    month = rest[0] if len(rest) > 0 else 1
    day = rest[1] if len(rest) > 1 else 1
    return date(year, month, day)


def _author(entry: Any) -> Author:
    given = entry.get("given")
    family = entry.get("family")
    name = " ".join(part for part in (given, family) if part)
    return Author(name=name, family=family, orcid=entry.get("ORCID"))


def _work_record(message: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    ident = Identifier("doi", normalize_doi(message["DOI"]))
    titles = message.get("title") or []
    if not titles:
        raise ValueError("crossref item has no title")
    title = " ".join(titles[0].split())
    issued = _issued_date(message.get("issued"))
    venue = next(iter(message.get("container-title") or []), None)
    return WorkRecord(
        ids=[ident],
        title=title,
        authors=[_author(entry) for entry in message.get("author", [])],
        year=issued.year if issued else None,
        published_at=issued,
        venue=venue,
        work_type=message.get("type") or "article",
        abstract=message.get("abstract"),
        provenance=Provenance(
            source=source_id,
            upstream_id=ident.value,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class CrossrefAdapter:
    """Translates the Crossref REST API; it sleeps, retries and reads secrets never."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _fetch_work(self, doi_value: str) -> Any:
        """``works/<doi>``, with ``mailto`` when a contact is set; ``None`` for a 404."""
        params = {"mailto": self.ctx.contact_email} if self.ctx.contact_email else {}
        try:
            data: Any = await self.ctx.http.get_json(
                f"{_WORKS_URL}/{quote(doi_value, safe='/')}", source=self.spec.id, params=params
            )
        except HttpError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise
        return data

    # @spec SRC-11
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        offset = int(req.cursor) if req.cursor else 0
        params = {"query": req.query, "rows": str(limit), "offset": str(offset)}
        if self.ctx.contact_email:
            params["mailto"] = self.ctx.contact_email
        data: Any = await self.ctx.http.get_json(_WORKS_URL, source=self.spec.id, params=params)
        message = data["message"]
        total = message.get("total-results")
        records = [
            _work_record(item, self.spec.id, self.ctx.clock.now())
            for item in message.get("items", [])
        ]
        next_offset = offset + limit
        next_cursor = str(next_offset) if total is not None and next_offset < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    # @spec SRC-11
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        data = await self._fetch_work(ident.value)
        if data is None:
            return None
        return _work_record(data["message"], self.spec.id, self.ctx.clock.now())

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

    # @spec SRC-11
    @translate_errors
    async def updates(self, ident: Identifier) -> Sequence[BaseModel]:
        data = await self._fetch_work(ident.value)
        if data is None:
            return []
        message = data["message"]
        return [
            CrossrefUpdate(
                kind=entry.get("type") or "update",
                related=Identifier("doi", normalize_doi(entry["DOI"])) if "DOI" in entry else None,
                date=_issued_date(entry.get("updated")),
                source=self.spec.id,
            )
            for entry in message.get("update-to", [])
        ]

    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data = await self._fetch_work(_PROBE_DOI)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            message = (data or {})["message"]
            shape_ok = bool(message.get("DOI")) and bool(message.get("title"))
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = CrossrefAdapter
