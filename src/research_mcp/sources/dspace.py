"""The DSpace adapter: one module serves every DSpace 7 repository configured as an
instance (LLD-sources-v3 2.3, 3.3, 5.12; PRD-sources-v5 SRC-20, SRC-21). ``instance_spec``
turns each ``sources.dspace_*`` entry into its own ``SourceSpec``, derived from the
configured ``base_url``'s host; ``defaults.toml`` ships the four v1 instances (MIT, Harvard,
Cornell, Penn). ``probe`` reads the reported ``dspaceVersion`` from the REST root and every
mapped record carries the last version this adapter instance has seen in
``extra["dspace_version"]``.
"""

from __future__ import annotations

import dataclasses
import functools
import re
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier, normalize_doi, normalize_handle
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

# The kind has no configured instance until defaults.toml (or the owner's config) supplies
# one; this host is never dialed outside a test that builds the bare kind directly.
_PLACEHOLDER_HOST = "dspace.invalid"
_ISSUED = re.compile(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?")


# @spec SRC-21
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="dspace",
        title="DSpace repository",
        group="repositories",
        capabilities=frozenset({Capability.SEARCH, Capability.GET, Capability.FULLTEXT}),
        id_schemes=frozenset({"handle", "doi"}),
        hosts=frozenset({_PLACEHOLDER_HOST}),
        auth=None,
        # DSpace publishes no fixed per-repository rate; a conservative shared default
        # [assumption], confirmed against no provider docs since every instance is self-hosted.
        rate=RateSpec(rps=2, burst=2, concurrency=2),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class DspaceInstance(BaseModel):
    """One repository's settings: its REST API root and a display title (LLD-sources-v3 2.3,
    5.12). ``base_url`` carries the host ``instance_spec`` uses; the adapter rebuilds the
    DSpace 7 REST root as ``https://<host>/server/api``, since every DSpace 7 deployment
    mounts it there [inferred] and ``SourceAdapter.__init__`` is given only the spec.
    """

    # defer_build: building a pydantic model at import time reads PYDANTIC_DISABLE_PLUGINS
    # from the environment (PLAT-3; the same reason SourceSpec uses defer_build in base.py).
    model_config = ConfigDict(strict=True, extra="forbid", defer_build=True)

    base_url: str
    title: str

    @field_validator("base_url")
    @classmethod
    def _https_base_url(cls, value: str) -> str:
        url = urlsplit(value)
        if url.scheme != "https" or not url.hostname:
            raise ValueError("base_url must be an https URL")
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("base_url must carry no credentials, query or fragment")
        return value


INSTANCE_MODEL = DspaceInstance


# @spec SRC-21
def instance_spec(base: SourceSpec, instance_id: str, cfg: DspaceInstance) -> SourceSpec:
    """One source per configured repository, hosted at ``cfg.base_url``'s host."""
    # DspaceInstance already rejected a base_url with no host.
    host = urlsplit(cfg.base_url).hostname or ""
    return dataclasses.replace(
        base, id=instance_id, title=cfg.title, hosts=frozenset({host}), instance_of=base.id
    )


def _meta(metadata: Any, field: str) -> list[str]:
    return [entry["value"] for entry in metadata.get(field, []) if entry.get("value")]


def _author(value: str) -> Author:
    family, separator, given = value.partition(", ")
    name = f"{given} {family}".strip() if separator else value
    return Author(name=name, family=family or None)


def _issued(value: str) -> tuple[int | None, date | None]:
    match = _ISSUED.match(value)
    if not match:
        return None, None
    year = int(match[1])
    if match[2] and match[3]:
        return year, date(year, int(match[2]), int(match[3]))
    return year, None


def _work_record(
    item: Any, source_id: str, retrieved_at: datetime, version: str | None
) -> WorkRecord:
    name = item["name"]
    if not name:
        raise ValueError("dspace item has no name")
    metadata = item.get("metadata") or {}
    ids = [Identifier("handle", normalize_handle(item["handle"]))]
    dois = _meta(metadata, "dc.identifier.doi")
    if dois:
        ids.append(Identifier("doi", normalize_doi(dois[0])))
    issued = _meta(metadata, "dc.date.issued")
    year, published_at = _issued(issued[0]) if issued else (None, None)
    abstracts = _meta(metadata, "dc.description.abstract")
    types = _meta(metadata, "dc.type")
    return WorkRecord(
        ids=ids,
        title=" ".join(name.split()),
        authors=[_author(value) for value in _meta(metadata, "dc.contributor.author")],
        year=year,
        published_at=published_at,
        work_type=types[0].lower() if types else "article",
        abstract=abstracts[0] if abstracts else None,
        extra={"dspace_version": version, "dspace_uuid": item["uuid"]},
        provenance=Provenance(
            source=source_id,
            upstream_id=item["uuid"],
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class DspaceAdapter:
    """Translates the DSpace 7 REST API; it sleeps, retries and reads secrets never."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx
        self._version: str | None = None

    @property
    def _base(self) -> str:
        host = next(iter(sorted(self.spec.hosts)))
        return f"https://{host}/server/api"

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        page = int(req.cursor) if req.cursor else 0
        params = {"query": req.query, "page": str(page), "size": str(limit)}
        data: Any = await self.ctx.http.get_json(
            f"{self._base}/discover/search/objects", source=self.spec.id, params=params
        )
        result = data["_embedded"]["searchResult"]
        objects = result["_embedded"]["objects"]
        records = [
            _work_record(
                obj["_embedded"]["indexableObject"],
                self.spec.id,
                self.ctx.clock.now(),
                self._version,
            )
            for obj in objects
        ]
        total = (result.get("page") or {}).get("totalElements")
        next_page = page + 1
        next_cursor = str(next_page) if total is not None and next_page * limit < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        try:
            data: Any = await self.ctx.http.get_json(
                f"{self._base}/pid/find", source=self.spec.id, params={"id": ident.value}
            )
        except HttpError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise
        return _work_record(data, self.spec.id, self.ctx.clock.now(), self._version)

    @translate_errors
    async def fulltext_candidates(self, work: WorkRecord) -> list[FulltextCandidate]:
        uuid = work.extra.get("dspace_uuid")
        if not uuid:
            return []
        data: Any = await self.ctx.http.get_json(
            f"{self._base}/core/items/{uuid}/bundles",
            source=self.spec.id,
            params={"embed": "bundles/bitstreams"},
        )
        candidates: list[FulltextCandidate] = []
        for bundle in (data.get("_embedded") or {}).get("bundles", []):
            if bundle.get("name") != "ORIGINAL":
                continue
            for bitstream in (bundle.get("_embedded") or {}).get("bitstreams", []):
                href = ((bitstream.get("_links") or {}).get("content") or {}).get("href")
                if href:
                    candidates.append(
                        FulltextCandidate(
                            location=OaLocation(url=href, source=self.spec.id, kind="pdf"),
                            priority=len(candidates),
                        )
                    )
        return candidates

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

    # @spec SRC-21
    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data: Any = await self.ctx.http.get_json(f"{self._base}/", source=self.spec.id)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        version = data.get("dspaceVersion") if isinstance(data, dict) else None
        self._version = version
        return ProbeResult(
            ok=True,
            latency_ms=int(elapsed.total_seconds() * 1000),
            shape_ok=bool(version),
            api_version=version,
        )


ADAPTER = DspaceAdapter
