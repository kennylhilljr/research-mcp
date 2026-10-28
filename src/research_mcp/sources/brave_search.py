"""The Brave Search adapter: one metered web source (LLD-sources-v3 5.7, 5.8; SPEC-v5 4, 9).

Brave has no free probe, so ``probe`` spends one search query, at most once every 24 hours
(``ProbeSpec.cost = "metered"``). A ``site_set`` is sent as several batched queries (at most
3, 380 characters each, query-named domains first), each a separate call that counts
against the daily cap; the adapter merges their results and reports ``truncated`` when
domains were dropped. The subscription token goes only in the ``X-Subscription-Token``
header, for the ``api.search.brave.com`` origin, attached by ``platform/http.py``; this
module never sees it.
"""

from __future__ import annotations

import functools
from typing import Any

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_url
from research_mcp.core.models import ProbeResult, Provenance, SearchPage, SearchRequest, WorkRecord
from research_mcp.core.specs import AuthSpec, ProbeSpec, RateSpec
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors
from research_mcp.sources.sitequery import site_batches

ADAPTER_VERSION = "1"

_HOST = "api.search.brave.com"
_ORIGIN = f"https://{_HOST}"
_SEARCH_URL = f"{_ORIGIN}/res/v1/web/search"
_PROBE_CADENCE_S = 24 * 3600
_PROBE_QUERY = "research"
_MAX_SITE_CHARS = 380
_MAX_SITE_BATCHES = 3


# @spec SRC-33
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import (PLAT-3), as in openalex.py and vertex_search.py.
    return SourceSpec(
        id="brave_search",
        title="Brave Search",
        group="web",
        capabilities=frozenset({Capability.SEARCH}),
        id_schemes=frozenset({"url"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("BRAVE_SEARCH_API_KEY",),
            required=True,
            placement="header",
            param="X-Subscription-Token",
            origins=(_ORIGIN,),
            signup_url="https://brave.com/search/api/",
            validation="probe",
        ),
        # Brave publishes per-plan limits; a conservative base-tier rate [assumption].
        rate=RateSpec(rps=1, burst=1, concurrency=1),
        timeout_s=10.0,
        # Brave's documented maximum `count` per request [assumption].
        max_page_size=20,
        probe=ProbeSpec(_PROBE_CADENCE_S, "metered", "one web search query; no free probe exists"),
        enabled_by_default=False,
        docs_url="https://api.search.brave.com/app/documentation/web-search/get-started",
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _record(result: Any, source_id: str, ctx: SourceContext) -> WorkRecord:
    url = normalize_url(result["url"])
    title = result.get("title") or url
    return WorkRecord(
        ids=[Identifier("url", url)],
        title=" ".join(str(title).split()),
        work_type="webpage",
        abstract=result.get("description"),
        provenance=Provenance(
            source=source_id,
            upstream_id=url,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=ctx.clock.now(),
        ),
    )


class BraveSearchAdapter:
    """Translates the Brave Web Search API; it never sleeps, retries or reads a secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _call(self, query: str, count: int) -> Any:
        return await self.ctx.http.get_json(
            _SEARCH_URL, source=self.spec.id, params={"q": query, "count": str(count)}
        )

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        count = min(req.limit, self.spec.max_page_size)
        if req.site_domains:
            # Each batch is a separate call and counts against the daily cap (5.8, 5.9).
            batches = site_batches(req.query, req.site_domains, _MAX_SITE_CHARS, _MAX_SITE_BATCHES)
            records: list[WorkRecord] = []
            for batch_query in batches.queries:
                data = await self._call(batch_query, count)
                records.extend(
                    _record(item, self.spec.id, self.ctx) for item in data["web"]["results"]
                )
            return SearchPage(records=records, truncated=batches.truncated)
        data = await self._call(req.query, count)
        records = [_record(item, self.spec.id, self.ctx) for item in data["web"]["results"]]
        return SearchPage(records=records)

    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data: Any = await self._call(_PROBE_QUERY, 1)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        web = data.get("web") if isinstance(data, dict) else None
        results = web.get("results") if isinstance(web, dict) else None
        return ProbeResult(
            ok=True,
            latency_ms=int(elapsed.total_seconds() * 1000),
            shape_ok=isinstance(results, list),
        )


ADAPTER = BraveSearchAdapter
