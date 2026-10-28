"""The SerpAPI adapter: one metered web source (LLD-sources-v3 5.7, 5.8; SPEC-v5 4, 9).

SerpAPI has a free probe, ``GET /account.json``, which spends no search and gives the
searches left (``ProbeResult.quota_remaining``). A ``site_set`` is sent as one query (at
most 380 characters, query-named domains first); domains that do not fit are dropped and
``SearchPage.truncated`` is set (SRC-31). The key is accepted only as the ``api_key`` query
parameter: ``platform/http.py`` attaches it after the request URL is captured for logging
and call records, so it never reaches a log line, an error or a call record (SRC-33); this
module never sees the key itself.
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

_HOST = "serpapi.com"
_ORIGIN = f"https://{_HOST}"
_SEARCH_URL = f"{_ORIGIN}/search.json"
_ACCOUNT_URL = f"{_ORIGIN}/account.json"
_PROBE_CADENCE_S = 6 * 3600
# LLD-sources-v3 5.8 fixes max_batches=1 for SerpAPI but not a character budget; reusing
# Brave's per-query budget [assumption].
_MAX_SITE_CHARS = 380
_MAX_SITE_BATCHES = 1


# @spec SRC-33
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import (PLAT-3), as in openalex.py and vertex_search.py.
    return SourceSpec(
        id="serpapi",
        title="SerpAPI",
        group="web",
        capabilities=frozenset({Capability.SEARCH}),
        id_schemes=frozenset({"url"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("SERPAPI_API_KEY",),
            required=True,
            placement="query",
            param="api_key",
            origins=(_ORIGIN,),
            signup_url="https://serpapi.com/users/sign_up",
            validation="probe",
        ),
        # SerpAPI's limit is the monthly plan quota, not a published rps; a conservative
        # rate so a page never floods the account [assumption].
        rate=RateSpec(rps=5, burst=5, concurrency=2),
        timeout_s=10.0,
        max_page_size=20,  # [assumption]: a page of Google results beyond this is unusual
        probe=ProbeSpec(_PROBE_CADENCE_S, "free", "GET account.json; no search is spent"),
        enabled_by_default=False,
        docs_url="https://serpapi.com/search-api",
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _record(result: Any, source_id: str, ctx: SourceContext) -> WorkRecord:
    url = normalize_url(result["link"])
    title = result.get("title") or url
    return WorkRecord(
        ids=[Identifier("url", url)],
        title=" ".join(str(title).split()),
        work_type="webpage",
        abstract=result.get("snippet"),
        provenance=Provenance(
            source=source_id,
            upstream_id=url,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=ctx.clock.now(),
        ),
    )


class SerpApiAdapter:
    """Translates the SerpAPI Google engine; it never sleeps, retries or reads a secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        count = min(req.limit, self.spec.max_page_size)
        query = req.query
        truncated = False
        if req.site_domains:
            batches = site_batches(req.query, req.site_domains, _MAX_SITE_CHARS, _MAX_SITE_BATCHES)
            query = batches.queries[0]
            truncated = batches.truncated
        data: Any = await self.ctx.http.get_json(
            _SEARCH_URL,
            source=self.spec.id,
            params={"engine": "google", "q": query, "num": str(count)},
        )
        records = [_record(item, self.spec.id, self.ctx) for item in data["organic_results"]]
        return SearchPage(records=records, truncated=truncated)

    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data: Any = await self.ctx.http.get_json(_ACCOUNT_URL, source=self.spec.id)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        left = data.get("total_searches_left") if isinstance(data, dict) else None
        shape_ok = isinstance(left, int)
        return ProbeResult(
            ok=True,
            latency_ms=int(elapsed.total_seconds() * 1000),
            shape_ok=shape_ok,
            quota_remaining=str(left) if shape_ok else None,
        )


ADAPTER = SerpApiAdapter
