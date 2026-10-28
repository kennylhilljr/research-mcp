"""The IETF adapter: Datatracker's JSON API over https (LLD-sources-v3 5.1; PRD-sources-v5
SRC-20, catalog row 28). Maps a document's name to a normalized ``rfc`` ``Identifier``,
its status and relations (``obsoletes``, ``obsoleted_by``) into ``WorkRecord.extra``, and
the RFC Editor's canonical HTML page into a fulltext candidate (status and obsoletes, as the
catalog describes this source).

The exact Datatracker document fields (``std_level``, ``obsoletes``, ``obsoleted_by``) are
fixed here from the fixtures until the owner confirms them against a live call [assumption].
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import quote

from pydantic import BaseModel

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier, normalize_rfc
from research_mcp.core.models import (
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

_HOST = "datatracker.ietf.org"
_DOCUMENT_URL = f"https://{_HOST}/api/v1/doc/document/"
_PROBE_NAME = "rfc2119"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="ietf",
        title="IETF Datatracker",
        group="standards",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.FULLTEXT}),
        id_schemes=frozenset({"rfc"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # Datatracker publishes no fixed per-caller number; a conservative rate [assumption].
        rate=RateSpec(rps=2, burst=2, concurrency=2),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _rfc_name(ident: Identifier) -> str:
    return f"rfc{ident.value}"


def _html_location(name: str) -> OaLocation:
    return OaLocation(url=f"https://www.rfc-editor.org/rfc/{name}.html", source="ietf", kind="html")


def _title(data: Any) -> str:
    title = data.get("title")
    if not title:
        raise ValueError("ietf document has no title")
    return " ".join(str(title).split())


def _published_date(data: Any) -> date | None:
    time_text = data.get("time")
    if not time_text:
        return None
    return datetime.fromisoformat(time_text.replace("Z", "+00:00")).date()


def _work_record(data: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    name = str(data["name"])
    ident = Identifier("rfc", normalize_rfc(name))
    published = _published_date(data)
    return WorkRecord(
        ids=[ident],
        title=_title(data),
        year=published.year if published else None,
        published_at=published,
        venue="IETF",
        work_type="standard",
        abstract=data.get("abstract") or None,
        oa_locations=[_html_location(name)],
        extra={
            "status": data.get("std_level"),
            "obsoletes": list(data.get("obsoletes") or []),
            "obsoleted_by": list(data.get("obsoleted_by") or []),
        },
        provenance=Provenance(
            source=source_id,
            upstream_id=name,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class IetfAdapter:
    """Translates the IETF Datatracker document API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _fetch_document(self, name: str) -> Any:
        """``doc/document/<name>/``; ``None`` for a 404."""
        try:
            data: Any = await self.ctx.http.get_json(
                f"{_DOCUMENT_URL}{quote(name, safe='')}/", source=self.spec.id
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
        params = {
            "type": "rfc",
            "title__icontains": req.query,
            "limit": str(limit),
            "offset": str(offset),
        }
        data: Any = await self.ctx.http.get_json(_DOCUMENT_URL, source=self.spec.id, params=params)
        meta = data.get("meta") or {}
        total = meta.get("total_count")
        records = [
            _work_record(item, self.spec.id, self.ctx.clock.now())
            for item in data.get("objects", [])
        ]
        next_offset = offset + limit
        next_cursor = str(next_offset) if total is not None and next_offset < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        data = await self._fetch_document(_rfc_name(ident))
        if data is None:
            return None
        return _work_record(data, self.spec.id, self.ctx.clock.now())

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
            data = await self._fetch_document(_PROBE_NAME)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            shape_ok = bool((data or {}).get("name")) and bool((data or {}).get("title"))
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = IetfAdapter
