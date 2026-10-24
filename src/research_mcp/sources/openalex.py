"""The OpenAlex adapter: JSON over https, a required API key (LLD-sources-v2 5.1; PRD-sources-v5
SRC-12). Sends the key as the ``api_key`` query parameter, caps a page at 100 records, maps a
work's ``topics`` into ``WorkRecord.extra`` and an author's ``last_known_institutions`` into
their affiliations, and classifies an insufficient-budget 429 as ``budget_exhausted``.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier, normalize_doi, normalize_openalex
from research_mcp.core.models import (
    Author,
    CitationPage,
    FulltextCandidate,
    JsonValue,
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

_HOST = "api.openalex.org"
_WORKS_URL = f"https://{_HOST}/works"
_AUTHORS_URL = f"https://{_HOST}/authors"
_PROBE_ID = "W2741809807"
_INSUFFICIENT_BUDGET = b"insufficient budget"


# @spec SRC-12
def classify_openalex(status: int, body: bytes) -> tuple[ErrorCode, str | None] | None:
    """A 429 naming an exhausted daily budget, distinct from a plain rate limit."""
    if status == 429 and _INSUFFICIENT_BUDGET in body.lower():
        return (ErrorCode.BUDGET_EXHAUSTED, "daily budget")
    return None


# @spec SRC-12
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="openalex",
        title="OpenAlex",
        group="scholarly",
        capabilities=frozenset(
            {
                Capability.SEARCH,
                Capability.GET,
                Capability.FULLTEXT,
                Capability.CITATIONS,
                Capability.AUTHORS,
            }
        ),
        id_schemes=frozenset({"doi", "openalex"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("OPENALEX_API_KEY",),
            required=True,
            placement="query",
            param="api_key",
            origins=(f"https://{_HOST}",),
            signup_url="https://openalex.org",
        ),
        # OpenAlex publishes no fixed keyed-caller number; a conservative rate [assumption].
        rate=RateSpec(rps=10, burst=10, concurrency=4),
        max_page_size=100,
        error_classifier=classify_openalex,
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class OpenAlexAuthor(BaseModel):
    """One author from the ``/authors`` endpoint (SRC-12: ``last_known_institutions``).

    Not yet ``AuthorRecord`` in ``core/models.py`` (LLD-sources-v2 2.1, 5.13); the fields are
    fixed here from the OpenAlex fixtures until a shared model exists [assumption].
    """

    model_config = ConfigDict(defer_build=True)

    name: str
    orcid: str | None
    ids: list[Identifier]
    affiliations: list[str] = []
    works_count: int | None


def _author(entry: Any) -> Author:
    author = entry.get("author") or {}
    return Author(name=author.get("display_name") or "", orcid=author.get("orcid"))


def _author_record(entry: Any) -> OpenAlexAuthor:
    # The author's own id is "A..."; normalize_openalex only accepts a work's "W..." form.
    author_id = entry["id"].rsplit("/", 1)[-1].upper()
    institutions = entry.get("last_known_institutions") or []
    return OpenAlexAuthor(
        name=entry.get("display_name") or "",
        orcid=entry.get("orcid"),
        ids=[Identifier("openalex_author", author_id)],
        affiliations=[inst["display_name"] for inst in institutions if inst.get("display_name")],
        works_count=entry.get("works_count"),
    )


def _oa_ident(raw: str) -> Identifier:
    return Identifier("openalex", normalize_openalex(raw))


def _topics(data: Any) -> list[JsonValue]:
    return [topic["display_name"] for topic in data.get("topics", []) if topic.get("display_name")]


def _oa_locations(data: Any) -> list[OaLocation]:
    primary = data.get("primary_location") or {}
    pdf_url = primary.get("pdf_url")
    if pdf_url:
        return [
            OaLocation(url=pdf_url, source="openalex", kind="pdf", license=primary.get("license"))
        ]
    oa_url = (data.get("open_access") or {}).get("oa_url")
    if oa_url:
        return [OaLocation(url=oa_url, source="openalex", kind="html")]
    return []


def _work_record(data: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    openalex_id = normalize_openalex(data["id"])
    ids = [Identifier("openalex", openalex_id)]
    doi_raw = data.get("doi")
    if doi_raw:
        ids.append(Identifier("doi", normalize_doi(doi_raw)))
    title = data.get("title") or data.get("display_name")
    if not title:
        raise ValueError("openalex work has no title")
    published_at = (
        date.fromisoformat(data["publication_date"]) if data.get("publication_date") else None
    )
    venue = ((data.get("primary_location") or {}).get("source") or {}).get("display_name")
    return WorkRecord(
        ids=ids,
        title=" ".join(title.split()),
        authors=[_author(entry) for entry in data.get("authorships", [])],
        year=data.get("publication_year"),
        published_at=published_at,
        venue=venue,
        work_type=data.get("type") or "article",
        oa_locations=_oa_locations(data),
        is_retracted=data.get("is_retracted"),
        extra={"topics": _topics(data)},
        provenance=Provenance(
            source=source_id,
            upstream_id=openalex_id,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class OpenAlexAdapter:
    """Translates the OpenAlex Works and Authors APIs; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _fetch_work(self, ident: Identifier) -> Any:
        """``works/doi:<doi>`` or ``works/<openalex id>``; ``None`` for a 404."""
        path = f"doi:{ident.value}" if ident.scheme == "doi" else ident.value
        try:
            data: Any = await self.ctx.http.get_json(f"{_WORKS_URL}/{path}", source=self.spec.id)
        except HttpError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise
        return data

    # @spec SRC-12
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        params = {"search": req.query, "per_page": str(limit), "cursor": req.cursor or "*"}
        data: Any = await self.ctx.http.get_json(_WORKS_URL, source=self.spec.id, params=params)
        meta = data.get("meta") or {}
        records = [
            _work_record(item, self.spec.id, self.ctx.clock.now()) for item in data["results"]
        ]
        return SearchPage(
            records=records, total=meta.get("count"), next_cursor=meta.get("next_cursor")
        )

    # @spec SRC-12
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        data = await self._fetch_work(ident)
        if data is None:
            return None
        return _work_record(data, self.spec.id, self.ctx.clock.now())

    async def fulltext_candidates(self, work: WorkRecord) -> list[FulltextCandidate]:
        return [
            FulltextCandidate(location=location, priority=index)
            for index, location in enumerate(work.oa_locations)
        ]

    @translate_errors
    async def citations(
        self,
        ident: Identifier,
        direction: Literal["citing", "cited"],
        cursor: str | None,
        limit: int,
    ) -> CitationPage:
        data = await self._fetch_work(ident)
        if data is None:
            return CitationPage(ids=[])
        openalex_id = normalize_openalex(data["id"])
        if direction == "cited":
            referenced = data.get("referenced_works", [])
            start = int(cursor) if cursor else 0
            page = referenced[start : start + limit]
            next_cursor = str(start + limit) if start + limit < len(referenced) else None
            return CitationPage(ids=[_oa_ident(w) for w in page], next_cursor=next_cursor)
        params = {
            "filter": f"cites:{openalex_id}",
            "per_page": str(min(limit, self.spec.max_page_size)),
            "cursor": cursor or "*",
        }
        citing: Any = await self.ctx.http.get_json(_WORKS_URL, source=self.spec.id, params=params)
        return CitationPage(
            ids=[_oa_ident(item["id"]) for item in citing["results"]],
            next_cursor=(citing.get("meta") or {}).get("next_cursor"),
        )

    # @spec SRC-12
    @translate_errors
    async def search_authors(
        self, query: str | None, orcid: str | None, limit: int
    ) -> Sequence[BaseModel]:
        params: dict[str, str] = {"per_page": str(min(limit, self.spec.max_page_size))}
        if orcid:
            params["filter"] = f"orcid:{orcid}"
        elif query:
            params["search"] = query
        data: Any = await self.ctx.http.get_json(_AUTHORS_URL, source=self.spec.id, params=params)
        return [_author_record(entry) for entry in data["results"]]

    async def updates(self, ident: Identifier) -> Sequence[BaseModel]:
        return []

    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data = await self._fetch_work(Identifier("openalex", _PROBE_ID))
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            shape_ok = bool((data or {})["id"]) and bool(
                (data or {}).get("title") or (data or {}).get("display_name")
            )
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = OpenAlexAdapter
