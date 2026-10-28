"""Tests for the Europe PMC adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 row 21).

Generic conformance (search_ok/search_empty/get_ok/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, Europe PMC included, by
``tests/sources/test_conformance.py::test_conformance_passes[europe_pmc]``. This file covers
what the adapter adds on top of that suite: the pmid/pmcid/doi identifier mapping, the date
and author mapping, ``get`` by any of the three schemes, and the PMC OA full text locations
that ``fulltext_candidates`` reads back.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.europe_pmc import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_europe_pmc_maps_identifiers_dates_and_oa_locations(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: Europe PMC maps pmid/pmcid/doi, dates and PMC OA full text locations."""
    source = _registered()

    assert source.spec.capabilities == frozenset(
        {Capability.SEARCH, Capability.GET, Capability.FULLTEXT}
    )
    assert source.spec.hosts == frozenset({"www.ebi.ac.uk"})
    assert source.spec.auth is None

    fx = fixtures_of(source)

    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="sample topic", limit=1))
    assert len(search_harness.requests) == 1
    assert search_harness.requests[0].url.host == "www.ebi.ac.uk"
    assert len(page.records) == 1
    record = page.records[0]
    ids = {(ident.scheme, ident.value) for ident in record.ids}
    assert ids == {
        ("pmid", "23555192"),
        ("pmcid", "PMC3625057"),
        ("doi", "10.1000/example.europepmc.1"),
    }
    assert [a.name for a in record.authors] == ["Smith J", "Doe A."]
    assert record.year == 2013
    assert record.published_at is not None and (
        record.published_at.year,
        record.published_at.month,
        record.published_at.day,
    ) == (2013, 3, 15)
    assert len(record.oa_locations) == 2
    assert {loc.kind for loc in record.oa_locations} == {"pdf", "html"}

    # The record's own full text locations become fulltext_candidates, in order, no new call.
    candidates = await search_harness.adapter.fulltext_candidates(record)
    assert [c.location.kind for c in candidates] == ["pdf", "html"]

    # get() by DOI, PMCID and PMID each send a query built from the identifier's scheme.
    for scheme, value in (
        ("doi", "10.1000/example.europepmc.1"),
        ("pmcid", "PMC3625057"),
        ("pmid", "23555192"),
    ):
        get_harness = harness_for(source)
        get_harness.serve(fx["get_ok"])
        got = await get_harness.adapter.get(Identifier(scheme, value))
        assert got is not None
        assert ("pmid", "23555192") in {(i.scheme, i.value) for i in got.ids}
        assert len(get_harness.requests) == 1
