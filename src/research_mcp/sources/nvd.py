"""The NVD adapter: the CVE API 2.0 over https (LLD-sources-v3 5.1; PRD-sources-v5 SRC-20,
catalog row 30). Maps a CVE record to the NVD detail page as a ``url`` ``Identifier`` (there
is no CVE identifier scheme in ``core/ids.py``, and this unit adds none), its first English
description to the work's title and abstract, and attaches the optional ``NVD_API_KEY`` as
the ``apiKey`` header.

NVD returns ``200`` with an empty ``vulnerabilities`` list for an unknown CVE id, never
``404`` [assumption, from the published CVE API 2.0 schema]; ``get`` maps that to ``None``.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import urlsplit

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

_HOST = "services.nvd.nist.gov"
_CVE_URL = f"https://{_HOST}/rest/json/cves/2.0"
_DETAIL_PAGE = "https://nvd.nist.gov/vuln/detail/"
_PROBE_ID = "CVE-1999-0001"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="nvd",
        title="NVD (CVE API 2.0)",
        group="standards",
        capabilities=frozenset({Capability.SEARCH, Capability.GET}),
        id_schemes=frozenset({"url"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("NVD_API_KEY",),
            required=False,
            placement="header",
            param="apiKey",
            origins=(f"https://{_HOST}",),
            signup_url="https://nvd.nist.gov/developers/request-an-api-key",
        ),
        # NVD's published public limit without a key: 5 requests per rolling 30 s [assumption].
        rate=RateSpec(rps=5 / 30, burst=5, concurrency=1),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _cve_id_from_identifier(ident: Identifier) -> str:
    path = urlsplit(ident.value).path
    return path.rsplit("/", 1)[-1]


def _cve_ident(cve_id: str) -> Identifier:
    return Identifier("url", normalize_url(f"{_DETAIL_PAGE}{cve_id}"))


def _description(cve: Any) -> str:
    for entry in cve.get("descriptions", []):
        if entry.get("lang") == "en" and entry.get("value"):
            return str(entry["value"])
    raise ValueError("nvd record has no English description")


def _cve_date(cve: Any, field: str) -> date | None:
    text = cve.get(field)
    if not text:
        return None
    return datetime.fromisoformat(text).date()


def _work_record(cve: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    cve_id = str(cve["id"])
    description = _description(cve)
    published = _cve_date(cve, "published")
    return WorkRecord(
        ids=[_cve_ident(cve_id)],
        title=" ".join(description.split()),
        year=published.year if published else None,
        published_at=published,
        venue="NVD",
        work_type="advisory",
        abstract=description,
        extra={"vuln_status": cve.get("vulnStatus")},
        provenance=Provenance(
            source=source_id,
            upstream_id=cve_id,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class NvdAdapter:
    """Translates the NVD CVE API 2.0; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        start_index = int(req.cursor) if req.cursor else 0
        params = {
            "keywordSearch": req.query,
            "resultsPerPage": str(limit),
            "startIndex": str(start_index),
        }
        data: Any = await self.ctx.http.get_json(_CVE_URL, source=self.spec.id, params=params)
        total = data.get("totalResults")
        records = [
            _work_record(item["cve"], self.spec.id, self.ctx.clock.now())
            for item in data.get("vulnerabilities", [])
        ]
        next_index = start_index + limit
        next_cursor = str(next_index) if total is not None and next_index < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        params = {"cveId": _cve_id_from_identifier(ident)}
        data: Any = await self.ctx.http.get_json(_CVE_URL, source=self.spec.id, params=params)
        vulnerabilities = data.get("vulnerabilities") or []
        if not vulnerabilities:
            return None
        return _work_record(vulnerabilities[0]["cve"], self.spec.id, self.ctx.clock.now())

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
                _CVE_URL, source=self.spec.id, params={"cveId": _PROBE_ID}
            )
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            vulnerabilities = data.get("vulnerabilities") or []
            shape_ok = bool(vulnerabilities) and bool(vulnerabilities[0]["cve"].get("id"))
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = NvdAdapter
