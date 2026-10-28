"""The Vertex AI Search adapter: one source per engine, ``vertex_<name>`` (LLD-sources-v3 5.7).

An instance kind (2.3): each ``sources.vertex_<name>`` entry with
``instance_of = "vertex_search"`` names a project, a location and an engine id, which are
settings, not secrets (SRC-FR-23). ``search`` POSTs to the engine's default serving config
and ``probe`` reads the engine resource, which costs no query.

The adapter never sees the Google sign-in. ``platform/google_adc.py`` holds the token in
memory and ``platform/http.py`` attaches it, with ``X-Goog-User-Project``, only for the
origin in ``SPEC.auth.origins`` (LLD-sources-v3 4; LLD-platform-v3 4.2).
"""

from __future__ import annotations

import dataclasses
import functools
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from research_mcp.core.errors import HttpError
from research_mcp.core.ids import Identifier, normalize_url
from research_mcp.core.models import (
    JsonValue,
    ProbeResult,
    Provenance,
    SearchPage,
    SearchRequest,
    WorkRecord,
)
from research_mcp.core.specs import AuthSpec, ProbeSpec, RateSpec
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors
from research_mcp.sources.sitequery import host_matches

ADAPTER_VERSION = "1"

_HOST = "discoveryengine.googleapis.com"
_ORIGIN = f"https://{_HOST}"
_INSTANCE_PREFIX = "vertex_"
_PROBE_CADENCE_S = 6 * 3600


class VertexInstance(BaseModel):
    """One ``sources.vertex_<name>`` entry. The patterns keep each value one path segment."""

    model_config = ConfigDict(strict=True, extra="forbid", defer_build=True)

    # Google project ids, optionally domain-scoped ("example.com:project").
    project: str = Field(pattern=r"^(?:[a-z0-9.-]+:)?[a-z][a-z0-9-]{4,28}[a-z0-9]$")
    location: str = Field(default="global", pattern=r"^[a-z][a-z0-9-]{0,62}$")
    engine_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,62}$")
    title: str | None = Field(default=None, min_length=1, max_length=120)


INSTANCE_MODEL = VertexInstance


# The kind is listed once, unconfigured, until an instance exists (2.3), and an
# unconfigured source is never called (SRC-INV-1). The conformance suite still exercises
# the kind entry with empty settings, so it gets these coordinates [assumption].
@functools.cache
def _kind_engine() -> VertexInstance:
    return VertexInstance(project="unconfigured", engine_id="unconfigured")


@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import (PLAT-3), as in openalex.py.
    return SourceSpec(
        id="vertex_search",
        title="Vertex AI Search",
        group="web",
        capabilities=frozenset({Capability.SEARCH}),
        id_schemes=frozenset({"url"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("GOOGLE_SIGNIN",),
            required=True,
            placement="bearer",
            param="Authorization",
            origins=(_ORIGIN,),
            signup_url="https://cloud.google.com/docs/authentication/provide-credentials-adc",
            validation="probe",
        ),
        # Google's default Discovery Engine quota is per project and per minute; a
        # conservative rate below it [assumption]. The daily cap is budget_cap (5.9).
        rate=RateSpec(rps=5, burst=5, concurrency=2),
        timeout_s=10.0,
        # The page size limit of website search with advanced indexing [assumption].
        max_page_size=50,
        extras=frozenset({"gcp"}),
        probe=ProbeSpec(_PROBE_CADENCE_S, "free", "GET the engine resource; no query cost"),
        enabled_by_default=False,
        docs_url="https://cloud.google.com/generative-ai-app-builder/docs/reference/rest",
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# @spec SRC-32
def instance_spec(base: SourceSpec, instance_id: str, cfg: BaseModel) -> SourceSpec:
    """The spec of one engine: its own id and title; the host and the sign-in stay the kind's."""
    if not isinstance(cfg, VertexInstance):
        raise ValueError("vertex_search instance settings are not a VertexInstance")
    if not instance_id.startswith(_INSTANCE_PREFIX):
        raise ValueError("a vertex_search instance is named vertex_<name>")
    return dataclasses.replace(
        base,
        id=instance_id,
        title=cfg.title or f"Vertex AI Search: {cfg.engine_id}",
        instance_of=base.id,
    )


def _engine(settings: SourceSettings) -> VertexInstance:
    fields = {k: v for k, v in (settings.model_extra or {}).items() if k != "instance_of"}
    if not fields:
        return _kind_engine()
    try:
        return VertexInstance.model_validate(fields)
    except ValueError:
        # The registry lists an invalid entry unconfigured and never calls it (5.2 row 5).
        return _kind_engine()


def _engine_url(engine: VertexInstance) -> str:
    return (
        f"{_ORIGIN}/v1/projects/{engine.project}/locations/{engine.location}"
        f"/collections/default_collection/engines/{engine.engine_id}"
    )


def _snippet(data: Any) -> str | None:
    for item in data.get("snippets") or []:
        text = item.get("snippet")
        if text:
            return str(text)
    return None


def _record(result: Any, source_id: str, ctx: SourceContext) -> WorkRecord:
    document = result["document"]
    data = document["derivedStructData"]
    url = normalize_url(data["link"])
    title = data.get("title") or url
    return WorkRecord(
        ids=[Identifier("url", url)],
        title=" ".join(str(title).split()),
        work_type="webpage",
        venue=data.get("displayLink"),
        abstract=_snippet(data),
        provenance=Provenance(
            source=source_id,
            upstream_id=document.get("id") or result["id"],
            adapter_version=ADAPTER_VERSION,
            retrieved_at=ctx.clock.now(),
        ),
    )


# @spec SRC-20
class VertexSearchAdapter:
    """Translates the Discovery Engine search API; it never sleeps, retries or reads a secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx
        self._engine_url = _engine_url(_engine(ctx.settings))

    # @spec SRC-32
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        body: dict[str, JsonValue] = {
            "query": req.query,
            "pageSize": min(req.limit, self.spec.max_page_size),
        }
        if req.cursor:
            body["pageToken"] = req.cursor
        data: Any = await self.ctx.http.post_json(
            f"{self._engine_url}/servingConfigs/default_search:search",
            source=self.spec.id,
            json=body,
        )
        if not isinstance(data, dict):
            raise ValueError("vertex search reply is not an object")
        records = [_record(item, self.spec.id, self.ctx) for item in data.get("results") or []]
        total = data.get("totalSize")
        if req.site_domains:
            # The engine's scope is set in Google Cloud, so a site set filters after the
            # call, by the parsed host (LLD-sources-v3 5.8).
            records = [
                r
                for r in records
                if host_matches(urlsplit(r.ids[0].value).hostname or "", req.site_domains)
            ]
            total = None
        return SearchPage(
            records=records,
            total=total if isinstance(total, int) else None,
            next_cursor=data.get("nextPageToken") or None,
        )

    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data: Any = await self.ctx.http.get_json(self._engine_url, source=self.spec.id)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        name = data.get("name") if isinstance(data, dict) else None
        shape_ok = isinstance(name, str) and "/engines/" in name
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=shape_ok
        )


ADAPTER = VertexSearchAdapter
