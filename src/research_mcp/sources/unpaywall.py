"""The Unpaywall adapter: the DOI lookup API over https, a contact email instead of a
credential (LLD-sources-v3 4, 5.1, 5.5; PRD-sources-v5 SRC-20). Declares ``get`` and
``fulltext``: the single ``/v2/{doi}`` lookup both maps to a ``WorkRecord`` and yields the
OA location ``fulltext_candidates`` turns into a priority order (SRC-FR-19 style, scholarly
group). Unpaywall indexes no catalog of its own, so ``search`` is never called (no capability
declared) and returns an empty page.
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

_HOST = "api.unpaywall.org"
_BASE_URL = f"https://{_HOST}/v2"
# Used as an example DOI in Unpaywall's own API documentation [assumption].
_PROBE_DOI = "10.1038/nature12373"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="unpaywall",
        title="Unpaywall",
        group="scholarly",
        capabilities=frozenset({Capability.GET, Capability.FULLTEXT}),
        id_schemes=frozenset({"doi"}),
        hosts=frozenset({_HOST}),
        auth=None,
        needs_contact=True,
        # Unpaywall asks for at most one request per second; a conservative figure
        # [assumption].
        rate=RateSpec(rps=1, burst=2, concurrency=2),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _author(entry: Any) -> Author:
    given = entry.get("given")
    family = entry.get("family")
    name = " ".join(part for part in (given, family) if part)
    return Author(name=name, family=family)


def _opt_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _oa_locations(data: Any) -> list[OaLocation]:
    best = data.get("best_oa_location")
    if not best or not best.get("url"):
        return []
    pdf_url = best.get("url_for_pdf")
    kind: Literal["pdf", "html"] = "pdf" if pdf_url else "html"
    return [
        OaLocation(
            url=best["url"],
            source="unpaywall",
            kind=kind,
            license=best.get("license"),
            version=best.get("version"),
        )
    ]


def _work_record(data: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    ident = Identifier("doi", normalize_doi(data["doi"]))
    title = data.get("title")
    if not title:
        raise ValueError("unpaywall record has no title")
    return WorkRecord(
        ids=[ident],
        title=" ".join(title.split()),
        authors=[_author(entry) for entry in data.get("z_authors") or []],
        year=data.get("year"),
        published_at=_opt_date(data.get("published_date")),
        venue=data.get("journal_name"),
        work_type=data.get("genre") or "article",
        oa_locations=_oa_locations(data),
        provenance=Provenance(
            source=source_id,
            upstream_id=ident.value,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class UnpaywallAdapter:
    """Translates the Unpaywall DOI lookup API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _fetch_work(self, doi_value: str) -> Any:
        """``v2/<doi>?email=...``; ``None`` for a 404."""
        params = {"email": self.ctx.contact_email} if self.ctx.contact_email else {}
        try:
            data: Any = await self.ctx.http.get_json(
                f"{_BASE_URL}/{doi_value}", source=self.spec.id, params=params
            )
        except HttpError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise
        return data

    async def search(self, req: SearchRequest) -> SearchPage:
        return SearchPage(records=[])

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        data = await self._fetch_work(ident.value)
        if data is None:
            return None
        return _work_record(data, self.spec.id, self.ctx.clock.now())

    # @spec SRC-20
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
            shape_ok = bool((data or {})["doi"]) and bool((data or {}).get("title"))
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = UnpaywallAdapter
