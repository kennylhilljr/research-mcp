"""The ClinicalTrials.gov adapter: JSON over https, no credential (LLD-sources-v3 5.1;
PRD-sources-v5 row 23, "port the existing adapter"). Maps the API v2 ``protocolSection`` to
a normalized NCT identifier, a partial start date and the lead sponsor as venue.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier, normalize_nct
from research_mcp.core.models import (
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

_HOST = "clinicaltrials.gov"
_STUDIES_URL = f"https://{_HOST}/api/v2/studies"
# A long-registered trial used only to check the upstream is alive [assumption].
_PROBE_NCT = "NCT00000419"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="clinical_trials",
        title="ClinicalTrials.gov",
        group="biomed",
        capabilities=frozenset({Capability.SEARCH, Capability.GET}),
        id_schemes=frozenset({"nct"}),
        hosts=frozenset({_HOST}),
        auth=None,
        # ClinicalTrials.gov publishes no fixed rate for the public API; conservative [assumption].
        rate=RateSpec(rps=5, burst=5, concurrency=2),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _partial_date(text: str | None) -> date | None:
    """A date module value like ``"2021-06-15"``, ``"2021-06"`` or ``"2021"``."""
    if not text:
        return None
    parts = text.split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def _work_record(study: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    protocol = study["protocolSection"]
    ident_module = protocol["identificationModule"]
    nct_id = ident_module["nctId"]
    title = ident_module.get("briefTitle") or ident_module.get("officialTitle")
    if not title:
        raise ValueError("clinical trials record has no title")
    status_module = protocol.get("statusModule") or {}
    published_at = _partial_date((status_module.get("startDateStruct") or {}).get("date"))
    sponsor = ((protocol.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}).get(
        "name"
    )
    summary = (protocol.get("descriptionModule") or {}).get("briefSummary")
    status = status_module.get("overallStatus")
    return WorkRecord(
        ids=[Identifier("nct", normalize_nct(nct_id))],
        title=" ".join(title.split()),
        year=published_at.year if published_at else None,
        published_at=published_at,
        venue=sponsor,
        work_type="clinical_trial",
        abstract=summary,
        extra={"status": status} if status else {},
        provenance=Provenance(
            source=source_id,
            upstream_id=nct_id,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class ClinicalTrialsAdapter:
    """Translates the ClinicalTrials.gov v2 Studies API; it sleeps, retries and reads no secret."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        params = {"query.term": req.query, "pageSize": str(limit), "format": "json"}
        if req.cursor:
            params["pageToken"] = req.cursor
        data: Any = await self.ctx.http.get_json(_STUDIES_URL, source=self.spec.id, params=params)
        records = [
            _work_record(study, self.spec.id, self.ctx.clock.now()) for study in data["studies"]
        ]
        return SearchPage(
            records=records, total=data.get("totalCount"), next_cursor=data.get("nextPageToken")
        )

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        try:
            data: Any = await self.ctx.http.get_json(
                f"{_STUDIES_URL}/{ident.value}", source=self.spec.id, params={"format": "json"}
            )
        except HttpError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise
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
    ) -> Sequence[BaseModel]:
        return []

    async def updates(self, ident: Identifier) -> Sequence[BaseModel]:
        return []

    # @spec SRC-20
    async def probe(self) -> ProbeResult:
        started = self.ctx.clock.now()
        try:
            data: Any = await self.ctx.http.get_json(
                f"{_STUDIES_URL}/{_PROBE_NCT}", source=self.spec.id, params={"format": "json"}
            )
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            shape_ok = bool(data["protocolSection"]["identificationModule"]["nctId"])
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = ClinicalTrialsAdapter
