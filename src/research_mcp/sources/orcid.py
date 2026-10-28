"""The ORCID adapter: JSON over https, no auth (LLD-sources-v3 5.1; PRD-sources-v5 1.3 row
13). ORCID's public API answers author identity only, so the spec declares only
``Capability.AUTHORS``; ``search``, ``get``, ``citations`` and ``updates`` are stubs a
registered source never calls (SRC-FR-2). An explicit ``orcid`` iD is folded into the same
expanded-search query ORCID's Lucene syntax accepts (``orcid:<id>``), so one endpoint
serves both lookup paths.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier
from research_mcp.core.models import (
    CitationPage,
    FulltextCandidate,
    ProbeResult,
    SearchPage,
    SearchRequest,
    WorkRecord,
)
from research_mcp.core.specs import RateSpec
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors

_HOST = "pub.orcid.org"
_SEARCH_URL = f"https://{_HOST}/v3.0/expanded-search/"
_ACCEPT_JSON = {"Accept": "application/json"}
_PROBE_QUERY = "orcid:0000-0002-1825-0097"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="orcid",
        title="ORCID",
        group="scholarly",
        capabilities=frozenset({Capability.AUTHORS}),
        id_schemes=frozenset(),
        hosts=frozenset({_HOST}),
        auth=None,
        # ORCID publishes no fixed rate for the public API; a conservative rate [assumption].
        rate=RateSpec(rps=3, burst=3, concurrency=2),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class OrcidAuthor(BaseModel):
    """One ``expanded-result`` entry.

    Not yet ``AuthorRecord`` in ``core/models.py`` (whose ``found_in`` is filled by the
    merging Authors service, M1-20): the fields are fixed here from the ORCID fixtures
    until that service exists, the same shape as ``OpenAlexAuthor`` in ``sources/openalex``
    [assumption].
    """

    model_config = ConfigDict(defer_build=True)

    name: str
    orcid: str | None
    ids: list[Identifier]
    affiliations: list[str] = []
    works_count: int | None


def _author_record(entry: Any) -> OrcidAuthor:
    given = entry.get("given-names")
    family = entry.get("family-names")
    name = " ".join(part for part in (given, family) if part) or entry.get("credit-name")
    if not name:
        raise ValueError("orcid entry has no name")
    orcid_id = entry["orcid-id"]
    institutions = entry.get("institution-name") or []
    return OrcidAuthor(
        name=name,
        orcid=orcid_id,
        ids=[Identifier("orcid", orcid_id)],
        affiliations=[inst for inst in institutions if inst],
        works_count=None,
    )


class OrcidAdapter:
    """Translates the ORCID public API expanded-search; it sleeps, retries and reads no
    secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _expanded_search(self, query: str, limit: int) -> Any:
        params = {"q": query, "start": "0", "rows": str(min(limit, self.spec.max_page_size))}
        return await self.ctx.http.get_json(
            _SEARCH_URL, source=self.spec.id, params=params, headers=_ACCEPT_JSON
        )

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

    # @spec SRC-20
    @translate_errors
    async def search_authors(
        self, query: str | None, orcid: str | None, limit: int
    ) -> Sequence[BaseModel]:
        q = f"orcid:{orcid}" if orcid else (query or "")
        data: Any = await self._expanded_search(q, limit)
        return [_author_record(entry) for entry in data["expanded-result"]]

    async def updates(self, ident: Identifier) -> Sequence[BaseModel]:
        return []

    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data: Any = await self._expanded_search(_PROBE_QUERY, 1)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            results = data["expanded-result"]
            shape_ok = bool(results) and bool(results[0].get("orcid-id"))
        except (KeyError, TypeError, IndexError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = OrcidAdapter
