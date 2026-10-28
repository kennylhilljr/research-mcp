"""The Hugging Face Papers adapter: JSON over https, no auth (LLD-sources-v3 5.1; PRD-sources-v5
1.3 row 20). Covers ML papers with code, indexed by their arXiv id, so this source declares
only ``search``: Hugging Face has no per-paper lookup endpoint of its own (the catalog note).
``max_page_size`` caps the response size, as the catalog note asks. The exact response shape
is not in any approved document; it is this unit's ``[assumption]``, recorded in the handoff.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_arxiv
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

_HOST = "huggingface.co"
_SEARCH_URL = f"https://{_HOST}/api/papers/search"
_PROBE_QUERY = "attention"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="hf_papers",
        title="Hugging Face Papers",
        group="preprints",
        capabilities=frozenset({Capability.SEARCH}),
        id_schemes=frozenset({"arxiv"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # Hugging Face publishes no fixed public rate limit; a conservative rate [assumption].
        rate=RateSpec(rps=2, burst=2, concurrency=2),
        # Caps the response size, as the catalog note asks (PRD-sources-v5 1.3 row 20).
        max_page_size=50,
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _work_record(entry: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    paper = entry["paper"]
    arxiv_id = paper.get("id")
    if not arxiv_id:
        raise ValueError("hf_papers entry has no arxiv id")
    title = paper.get("title")
    if not title:
        raise ValueError("hf_papers entry has no title")
    value, version = normalize_arxiv(arxiv_id)
    published = paper.get("publishedAt")
    published_at = (
        datetime.fromisoformat(published.replace("Z", "+00:00")).date() if published else None
    )
    authors = [Author(name=a["name"]) for a in paper.get("authors", []) if a.get("name")]
    return WorkRecord(
        ids=[Identifier("arxiv", value, version)],
        title=" ".join(title.split()),
        authors=authors,
        year=published_at.year if published_at else None,
        published_at=published_at,
        work_type="preprint",
        abstract=paper.get("summary"),
        extra={"upvotes": paper.get("upvotes")} if paper.get("upvotes") is not None else {},
        provenance=Provenance(
            source=source_id,
            upstream_id=value,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class HfPapersAdapter:
    """Translates the Hugging Face Papers search API; it sleeps, retries and holds no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _fetch_raw(self, query: str) -> Any:
        """The raw search response; parsing is each caller's job (so ``probe`` can tell a
        transport error from a malformed body, as ``crossref.py`` separates ``HttpError``
        from the parsing ``KeyError``/``TypeError``)."""
        return await self.ctx.http.get_json(_SEARCH_URL, source=self.spec.id, params={"q": query})

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        data = await self._fetch_raw(req.query)
        records = [
            _work_record(entry, self.spec.id, self.ctx.clock.now()) for entry in data[:limit]
        ]
        return SearchPage(records=records)

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

    async def updates(self, ident: Identifier) -> Sequence[BaseModel]:
        return []

    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data = await self._fetch_raw(_PROBE_QUERY)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            entry = data[0]
            shape_ok = bool(entry["paper"]["id"]) and bool(entry["paper"]["title"])
        except (KeyError, TypeError, IndexError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = HfPapersAdapter
