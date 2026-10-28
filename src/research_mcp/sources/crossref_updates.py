"""The Crossref retractions and corrections adapter: JSON over https, polite pool
(LLD-sources-v3 5.1; PRD-sources-v5 SRC-20, catalog row 37; LLD-search-v3 5.10). Serves only
``Capability.UPDATES``, over the same ``works/{doi}`` endpoint as ``crossref.py``, mapped to
the shared ``UpdateNotice`` model the integrity service reads (including the Retraction Watch
records Crossref folds into ``update-to``), rather than the scholarly adapter's own ad hoc
``CrossrefUpdate`` type.
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
    CitationPage,
    FulltextCandidate,
    ProbeResult,
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
_PROBE_DOI = "10.1037/0003-066x.59.1.29"

# Crossref's "update-to" entry "type" values that are an integrity notice, mapped to the
# shared UpdateNotice.kind literal; a type outside this map (for example "new_version") is
# not reported here [assumption: LLD-search-v3 5.10 names only retractions and corrections].
_KIND_MAP: dict[str, Literal["retraction", "correction", "expression_of_concern"]] = {
    "retraction": "retraction",
    "correction": "correction",
    "corrigendum": "correction",
    "erratum": "correction",
    "expression_of_concern": "expression_of_concern",
}


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="crossref_updates",
        title="Crossref retractions and corrections",
        group="integrity",
        capabilities=frozenset({Capability.UPDATES}),
        id_schemes=frozenset({"doi"}),
        hosts=frozenset({_HOST}),
        auth=None,
        needs_contact=True,
        # Crossref publishes no fixed polite-pool number; a conservative rate [assumption],
        # the same as the scholarly crossref adapter.
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


def _notice(entry: Any, source_id: str) -> UpdateNotice | None:
    kind = _KIND_MAP.get(str(entry.get("type")))
    if kind is None:
        return None
    related = Identifier("doi", normalize_doi(entry["DOI"])) if "DOI" in entry else None
    return UpdateNotice(
        kind=kind,
        related=related,
        date=_issued_date(entry.get("updated")),
        source=source_id,
        detail_url=f"https://doi.org/{related.value}" if related is not None else None,
    )


class CrossrefUpdatesAdapter:
    """Translates Crossref's ``update-to`` field; it sleeps, retries and reads secrets never."""

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

    async def search(self, req: SearchRequest) -> SearchPage:
        return SearchPage(records=[])

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

    # @spec SRC-20
    @translate_errors
    async def updates(self, ident: Identifier) -> Sequence[BaseModel]:
        data = await self._fetch_work(ident.value)
        if data is None:
            return []
        message = data["message"]
        notices = (_notice(entry, self.spec.id) for entry in message.get("update-to", []))
        return [notice for notice in notices if notice is not None]

    async def probe(self) -> ProbeResult:
        started: datetime = self.ctx.clock.now()
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


ADAPTER = CrossrefUpdatesAdapter
