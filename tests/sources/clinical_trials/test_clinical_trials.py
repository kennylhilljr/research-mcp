"""Tests for the ClinicalTrials.gov adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 row 23).

Generic conformance (search_ok/search_empty/get_ok/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, ClinicalTrials.gov included, by
``tests/sources/test_conformance.py::test_conformance_passes[clinical_trials]``. This file
covers what the adapter adds on top of that suite: the NCT identifier, the partial start
date and the lead sponsor mapped from the API v2 ``protocolSection``.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.clinical_trials import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_clinical_trials_maps_nct_date_and_sponsor(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: ClinicalTrials.gov maps the protocol section to NCT id, date and sponsor."""
    source = _registered()

    assert source.spec.capabilities == frozenset({Capability.SEARCH, Capability.GET})
    assert source.spec.hosts == frozenset({"clinicaltrials.gov"})
    assert source.spec.auth is None

    fx = fixtures_of(source)

    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="sample intervention", limit=1))
    assert len(search_harness.requests) == 1
    assert search_harness.requests[0].url.host == "clinicaltrials.gov"
    assert len(page.records) == 1
    record = page.records[0]
    assert (record.ids[0].scheme, record.ids[0].value) == ("nct", "NCT00000419")
    assert record.title == "A Sample Trial of an Example Intervention"
    assert record.year == 2000
    assert record.published_at is not None and (
        record.published_at.year,
        record.published_at.month,
        record.published_at.day,
    ) == (2000, 6, 15)
    assert record.venue == "Example University"
    assert record.work_type == "clinical_trial"
    assert record.extra == {"status": "COMPLETED"}

    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(Identifier("nct", "NCT00000419"))
    assert got is not None
    assert got.ids[0].value == "NCT00000419"
    assert got.title == "A Sample Trial of an Example Intervention"
    assert len(get_harness.requests) == 1
