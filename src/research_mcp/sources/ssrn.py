"""The SSRN adapter: JSON over https, no auth (LLD-sources-v3 5.1; PRD-sources-v5 1.3 row 19).
SSRN has no public API of its own; its working papers are indexed by Crossref under DOI
prefix ``10.2139`` (the catalog note), so this adapter calls ``api.crossref.org`` with that
prefix as a filter. No ``fulltext`` capability is declared: SSRN papers often need a login to
download, so this source never offers a PDF location (the catalog note).
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
_SSRN_PREFIX = "10.2139"
_PROBE_DOI = "10.2139/ssrn.0000001"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="ssrn",
        title="SSRN",
        group="preprints",
        capabilities=frozenset({Capability.SEARCH, Capability.GET}),
        id_schemes=frozenset({"doi"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # Shares Crossref's polite pool; the same conservative rate [assumption] as crossref.py.
        rate=RateSpec(rps=5, burst=5, concurrency=2),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _author(entry: Any) -> Author:
    given = entry.get("given")
    family = entry.get("family")
    name = " ".join(part for part in (given, family) if part)
    return Author(name=name, family=family, orcid=entry.get("ORCID"))


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


def _work_record(message: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    ident = Identifier("doi", normalize_doi(message["DOI"]))
    titles = message.get("title") or []
    if not titles:
        raise ValueError("ssrn item has no title")
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
        work_type="preprint",
        abstract=message.get("abstract"),
        provenance=Provenance(
            source=source_id,
            upstream_id=ident.value,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class SsrnAdapter:
    """Translates Crossref's REST API, filtered to the SSRN DOI prefix; it holds no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _fetch_raw(self, doi_value: str) -> Any:
        """``works/<doi>``, unparsed; ``None`` for a 404. The ``message`` extraction and the
        SSRN-prefix filter are each caller's job, so ``probe`` can tell a transport error
        from a malformed body (as ``crossref.py`` separates ``HttpError`` from the parsing
        ``KeyError``/``TypeError``)."""
        try:
            return await self.ctx.http.get_json(
                f"{_WORKS_URL}/{quote(doi_value, safe='/')}", source=self.spec.id
            )
        except HttpError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        offset = int(req.cursor) if req.cursor else 0
        params = {
            "query": req.query,
            "filter": f"prefix:{_SSRN_PREFIX}",
            "rows": str(limit),
            "offset": str(offset),
        }
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
        data = await self._fetch_raw(ident.value)
        if data is None:
            return None
        message = data["message"]
        if not message.get("DOI", "").startswith(f"{_SSRN_PREFIX}/"):
            return None
        return _work_record(message, self.spec.id, self.ctx.clock.now())

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
            data = await self._fetch_raw(_PROBE_DOI)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            message = (data or {})["message"]
            shape_ok = bool(message["DOI"]) and bool(message["title"])
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = SsrnAdapter
