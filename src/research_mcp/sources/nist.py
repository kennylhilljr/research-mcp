"""The NIST adapter: Crossref's JSON API over https, scoped to NIST's own DOI prefix
(LLD-sources-v3 5.1; PRD-sources-v5 SRC-20, catalog row 29: "Crossref prefix 10.6028 plus
CSRC pages"). Filters every Crossref call to ``prefix:10.6028``, maps a work's DOI and
issued date like the Crossref adapter, and maps Crossref's ``resource.primary.URL`` (the
publisher-maintained landing page, which for NIST is a CSRC or NVLPUBS page) into a
fulltext candidate.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import quote

from pydantic import BaseModel

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier, normalize_doi
from research_mcp.core.models import (
    Author,
    AuthorRecord,
    CitationPage,
    FulltextCandidate,
    OaLocation,
    ProbeResult,
    Provenance,
    SearchPage,
    SearchRequest,
    UpdateNotice,
    WorkRecord,
)
from research_mcp.core.specs import RateSpec
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors

ADAPTER_VERSION = "1"

_HOST = "api.crossref.org"
_WORKS_URL = f"https://{_HOST}/works"
_PREFIX = "10.6028"
_PROBE_DOI = "10.6028/nist.sp.800-63-3"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="nist",
        title="NIST Publications",
        group="standards",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.FULLTEXT}),
        id_schemes=frozenset({"doi"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # Crossref publishes no fixed polite-pool number; a conservative rate [assumption].
        rate=RateSpec(rps=5, burst=5, concurrency=2),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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


def _landing_location(message: Any) -> list[OaLocation]:
    """The CSRC or NVLPUBS landing page Crossref records as the publisher's resource."""
    url = ((message.get("resource") or {}).get("primary") or {}).get("URL")
    if not url:
        return []
    return [OaLocation(url=url, source="nist", kind="landing")]


def _work_record(message: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    ident = Identifier("doi", normalize_doi(message["DOI"]))
    titles = message.get("title") or []
    if not titles:
        raise ValueError("nist item has no title")
    title = " ".join(titles[0].split())
    issued = _issued_date(message.get("issued"))
    return WorkRecord(
        ids=[ident],
        title=title,
        authors=[_author(entry) for entry in message.get("author", [])],
        year=issued.year if issued else None,
        published_at=issued,
        venue="NIST",
        work_type=message.get("type") or "report",
        abstract=message.get("abstract"),
        oa_locations=_landing_location(message),
        provenance=Provenance(
            source=source_id,
            upstream_id=ident.value,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class NistAdapter:
    """Translates Crossref's API, scoped to NIST's DOI prefix; reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    def _params(self, extra: dict[str, str]) -> dict[str, str]:
        params = dict(extra)
        if self.ctx.contact_email:
            params["mailto"] = self.ctx.contact_email
        return params

    async def _fetch_work(self, doi_value: str) -> Any:
        """``works/<doi>``; ``None`` for a 404."""
        try:
            data: Any = await self.ctx.http.get_json(
                f"{_WORKS_URL}/{quote(doi_value, safe='/')}",
                source=self.spec.id,
                params=self._params({}),
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
        offset = int(req.cursor) if req.cursor else 0
        params = self._params(
            {
                "query": req.query,
                "filter": f"prefix:{_PREFIX}",
                "rows": str(limit),
                "offset": str(offset),
            }
        )
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

    # @spec SRC-20
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
    ) -> Sequence[BaseModel] | list[AuthorRecord]:
        return []

    async def updates(self, ident: Identifier) -> Sequence[BaseModel] | list[UpdateNotice]:
        return []

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


ADAPTER = NistAdapter
