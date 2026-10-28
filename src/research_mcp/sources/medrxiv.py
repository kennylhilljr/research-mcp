"""The medRxiv adapter: JSON over https, no auth (LLD-sources-v3 5.1; PRD-sources-v5 1.3 row
18). medRxiv shares its details API with bioRxiv (``api.biorxiv.org``, a different ``server``
path segment) and, like it, answers only ``get`` by DOI, with no keyword search (discovery
runs through Europe PMC and Crossref, per the catalog note). Maps a medRxiv DOI to a
normalized ``Identifier`` and the version-numbered content page to a PDF fulltext candidate.
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

_HOST = "api.biorxiv.org"
_CONTENT_HOST = "www.medrxiv.org"
_SERVER = "medrxiv"
_PROBE_DOI = "10.1101/2020.02.02.020000"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="medrxiv",
        title="medRxiv",
        group="preprints",
        capabilities=frozenset({Capability.GET, Capability.FULLTEXT}),
        id_schemes=frozenset({"doi"}),
        hosts=frozenset({_HOST, _CONTENT_HOST}),
        auth=None,
        # medRxiv publishes no fixed public rate limit; a conservative rate [assumption].
        rate=RateSpec(rps=1, burst=1, concurrency=1),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _authors(raw: str | None) -> list[Author]:
    if not raw:
        return []
    return [Author(name=part.strip()) for part in raw.split(";") if part.strip()]


def _pdf_location(
    doi_value: str, version: str | None, source_id: str, content_host: str
) -> OaLocation | None:
    if not version:
        return None
    return OaLocation(
        url=f"https://{content_host}/content/{doi_value}v{version}.full.pdf",
        source=source_id,
        kind="pdf",
        version=version,
    )


def _work_record(
    entry: Any, source_id: str, retrieved_at: datetime, content_host: str
) -> WorkRecord:
    doi_raw = entry.get("doi")
    if not doi_raw:
        raise ValueError("medRxiv entry has no doi")
    doi_value = normalize_doi(doi_raw)
    title = entry.get("title")
    if not title:
        raise ValueError("medRxiv entry has no title")
    date_text = entry.get("date")
    published_at = date.fromisoformat(date_text) if date_text else None
    version = entry.get("version")
    oa = _pdf_location(doi_value, version, source_id, content_host)
    return WorkRecord(
        ids=[Identifier("doi", doi_value)],
        title=" ".join(title.split()),
        authors=_authors(entry.get("authors")),
        year=published_at.year if published_at else None,
        published_at=published_at,
        venue=entry.get("category"),
        work_type="preprint",
        abstract=entry.get("abstract"),
        oa_locations=[oa] if oa is not None else [],
        provenance=Provenance(
            source=source_id,
            upstream_id=doi_value,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class MedrxivAdapter:
    """Translates the medRxiv details API; it sleeps, retries and reads secrets never."""

    SERVER = _SERVER
    CONTENT_HOST = _CONTENT_HOST

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _fetch_raw(self, doi_value: str) -> Any:
        """``details/<server>/<doi>``, unparsed: each caller extracts ``collection`` itself,
        so ``probe`` can tell a transport error from a malformed body (as ``crossref.py``
        separates ``HttpError`` from the parsing ``KeyError``/``TypeError``)."""
        return await self.ctx.http.get_json(
            f"https://{_HOST}/details/{self.SERVER}/{doi_value}", source=self.spec.id
        )

    async def search(self, req: SearchRequest) -> SearchPage:
        return SearchPage(records=[])

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        data = await self._fetch_raw(ident.value)
        collection = data["collection"]
        if not collection:
            return None
        return _work_record(collection[-1], self.spec.id, self.ctx.clock.now(), self.CONTENT_HOST)

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
            data = await self._fetch_raw(_PROBE_DOI)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            collection = data["collection"]
            entry = collection[-1] if collection else {}
            shape_ok = bool(entry["doi"]) and bool(entry["title"])
        except (KeyError, TypeError, IndexError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = MedrxivAdapter
