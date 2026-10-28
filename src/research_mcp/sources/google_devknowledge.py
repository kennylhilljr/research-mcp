"""The Google Developer Knowledge adapter: Google's v1 developer-docs search API over
https (LLD-sources-v3 5.1; PRD-sources-v5 SRC-20, catalog row 33). Sends the shared
``GOOGLE_DEVKNOWLEDGE_API_KEY`` (shared with ``google_pse``, as in v1) in the
``x-goog-api-key`` header and maps a document's own URL to a ``url`` ``Identifier``.

The exact host and path (``developerknowledge.googleapis.com``, ``documents:search`` and
``documents:lookup``) are not in any approved document; they are fixed here from the
fixtures until the owner confirms them against a live call [assumption].
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_url
from research_mcp.core.models import (
    AuthorRecord,
    CitationPage,
    FulltextCandidate,
    ProbeResult,
    Provenance,
    SearchPage,
    SearchRequest,
    UpdateNotice,
    WorkRecord,
)
from research_mcp.core.specs import AuthSpec, RateSpec
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors

ADAPTER_VERSION = "1"

_HOST = "developerknowledge.googleapis.com"
_SEARCH_URL = f"https://{_HOST}/v1/documents:search"
_LOOKUP_URL = f"https://{_HOST}/v1/documents:lookup"
_PROBE_URL = "https://developer.android.com/"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="google_devknowledge",
        title="Google Developer Knowledge",
        group="vendor_docs",
        capabilities=frozenset({Capability.SEARCH, Capability.GET}),
        id_schemes=frozenset({"url"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("GOOGLE_DEVKNOWLEDGE_API_KEY",),
            required=True,
            placement="header",
            param="x-goog-api-key",
            origins=(f"https://{_HOST}",),
            signup_url="https://console.cloud.google.com/apis/credentials",
        ),
        # The provider publishes no fixed per-key number; a conservative rate [assumption].
        rate=RateSpec(rps=2, burst=2, concurrency=2),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _updated_at(doc: Any) -> datetime | None:
    text = doc.get("updateTime")
    if not text:
        return None
    return datetime.fromisoformat(str(text).replace("Z", "+00:00"))


def _work_record(doc: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    url = doc["url"]
    ident = Identifier("url", normalize_url(url))
    title = doc.get("title")
    if not title:
        raise ValueError("google_devknowledge document has no title")
    updated = _updated_at(doc)
    return WorkRecord(
        ids=[ident],
        title=" ".join(str(title).split()),
        published_at=updated.date() if updated else None,
        year=updated.year if updated else None,
        venue="Google Developer Knowledge",
        work_type="webpage",
        abstract=doc.get("snippet"),
        provenance=Provenance(
            source=source_id,
            upstream_id=doc.get("name") or ident.value,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class GoogleDevKnowledgeAdapter:
    """Translates the Google Developer Knowledge API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        params = {"query": req.query, "pageSize": str(limit)}
        if req.cursor:
            params["pageToken"] = req.cursor
        data: Any = await self.ctx.http.get_json(_SEARCH_URL, source=self.spec.id, params=params)
        records = [
            _work_record(doc, self.spec.id, self.ctx.clock.now())
            for doc in data.get("documents", [])
        ]
        return SearchPage(records=records, next_cursor=data.get("nextPageToken") or None)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        data: Any = await self.ctx.http.get_json(
            _LOOKUP_URL, source=self.spec.id, params={"url": ident.value}
        )
        if not data:
            return None
        return _work_record(data, self.spec.id, self.ctx.clock.now())

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
    ) -> Sequence[BaseModel] | list[AuthorRecord]:
        return []

    async def updates(self, ident: Identifier) -> Sequence[BaseModel] | list[UpdateNotice]:
        return []

    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data: Any = await self.ctx.http.get_json(
                _LOOKUP_URL, source=self.spec.id, params={"url": _PROBE_URL}
            )
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            shape_ok = bool((data or {}).get("url")) and bool((data or {}).get("title"))
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = GoogleDevKnowledgeAdapter
