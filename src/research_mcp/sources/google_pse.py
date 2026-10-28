"""The Programmable Search adapter: one metered web source, shutting down 2027-01-01
(LLD-sources-v3 5.7, 5.8; SPEC-v5 4, 9).

Google has no free probe for this engine, so ``probe`` spends one search query, at most
once every 24 hours. The engine id (``cx``) is a plain setting (``sources.google_pse.
engine_id``), not a secret; the key is ``GOOGLE_DEVKNOWLEDGE_API_KEY``, shared with
``google_devknowledge``, and this module never sees it: ``platform/http.py`` attaches it
as the ``x-goog-api-key`` header only for the ``www.googleapis.com`` origin. A ``site_set``
is sent as one query (at most 380 characters, query-named domains first); domains that do
not fit are dropped and ``SearchPage.truncated`` is set (SRC-31). ``SPEC.shutdown_on``
makes the registry report ``deprecated(days)`` until removal (SRC-33).
"""

from __future__ import annotations

import functools
from datetime import date
from typing import Any

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_url
from research_mcp.core.models import ProbeResult, Provenance, SearchPage, SearchRequest, WorkRecord
from research_mcp.core.specs import AuthSpec, ProbeSpec, RateSpec
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors
from research_mcp.sources.sitequery import site_batches

ADAPTER_VERSION = "1"

_HOST = "www.googleapis.com"
_ORIGIN = f"https://{_HOST}"
_SEARCH_URL = f"{_ORIGIN}/customsearch/v1"
_PROBE_CADENCE_S = 24 * 3600
_PROBE_QUERY = "research"
# LLD-sources-v3 5.8 fixes max_batches=1 for Programmable Search but not a character
# budget; reusing Brave's per-query budget [assumption].
_MAX_SITE_CHARS = 380
_MAX_SITE_BATCHES = 1
_SHUTDOWN_ON = date(2027, 1, 1)


# @spec SRC-33
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import (PLAT-3), as in openalex.py and vertex_search.py.
    return SourceSpec(
        id="google_pse",
        title="Programmable Search",
        group="web",
        capabilities=frozenset({Capability.SEARCH}),
        id_schemes=frozenset({"url"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("GOOGLE_DEVKNOWLEDGE_API_KEY",),
            required=True,
            placement="header",
            param="x-goog-api-key",
            origins=(_ORIGIN,),
            signup_url="https://developers.google.com/custom-search/v1/overview",
            validation="probe",
        ),
        rate=RateSpec(rps=5, burst=5, concurrency=2),  # [assumption]
        timeout_s=10.0,
        max_page_size=10,  # Google's documented maximum `num` per request
        probe=ProbeSpec(_PROBE_CADENCE_S, "metered", "one search query; no free probe exists"),
        enabled_by_default=False,
        shutdown_on=_SHUTDOWN_ON,
        docs_url="https://developers.google.com/custom-search/v1/overview",
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _engine_id(settings: SourceSettings) -> str | None:
    """``sources.google_pse.engine_id`` (``cx``); not a secret (LLD-sources-v3 3.2)."""
    value = (settings.model_extra or {}).get("engine_id")
    return value if isinstance(value, str) and value else None


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


class GooglePseAdapter:
    """Translates the Custom Search JSON API; it never sleeps, retries or reads a secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _call(self, query: str, count: int) -> Any:
        params = {"q": query, "num": str(count)}
        engine_id = _engine_id(self.ctx.settings)
        if engine_id:
            params["cx"] = engine_id
        return await self.ctx.http.get_json(_SEARCH_URL, source=self.spec.id, params=params)

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
        data: Any = await self._call(query, count)
        records = [_record(item, self.spec.id, self.ctx) for item in data["items"]]
        total = (data.get("searchInformation") or {}).get("totalResults")
        return SearchPage(
            records=records,
            total=int(total) if isinstance(total, str) and total.isdigit() else None,
            truncated=truncated,
        )

    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data: Any = await self._call(_PROBE_QUERY, 1)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        items = data.get("items") if isinstance(data, dict) else None
        return ProbeResult(
            ok=True,
            latency_ms=int(elapsed.total_seconds() * 1000),
            shape_ok=isinstance(items, list),
        )


ADAPTER = GooglePseAdapter
