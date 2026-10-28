"""Tests for the PubMed adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 row 22).

Generic conformance (search_ok/search_empty/get_ok/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, PubMed included, by
``tests/sources/test_conformance.py::test_conformance_passes[pubmed]``. This file covers
what the adapter adds on top of that suite: the ESearch-then-ESummary resolution (with the
second call skipped when ESearch finds nothing), the docsum mapping, and the optional
``NCBI_API_KEY`` query parameter.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.pubmed import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_pubmed_resolves_esearch_through_esummary_and_skips_the_empty_case(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: PubMed maps ESearch ids through ESummary, skipping ESummary when empty."""
    source = _registered()

    assert source.spec.capabilities == frozenset({Capability.SEARCH, Capability.GET})
    assert source.spec.hosts == frozenset({"eutils.ncbi.nlm.nih.gov"})
    assert source.spec.auth is not None
    assert source.spec.auth.required is False
    assert source.spec.auth.secrets == ("NCBI_API_KEY",)

    fx = fixtures_of(source)

    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="sample intervention", limit=1))
    # ESearch, then one ESummary call for the ids ESearch found.
    assert len(search_harness.requests) == 2
    assert all(r.url.host == "eutils.ncbi.nlm.nih.gov" for r in search_harness.requests)
    # The optional credential attaches to both eutils calls.
    assert all(r.url.params["api_key"] == "fake-ncbi_api_key" for r in search_harness.requests)
    assert len(page.records) == 1
    record = page.records[0]
    assert (record.ids[0].scheme, record.ids[0].value) == ("pmid", "23555192")
    assert record.title == "An example randomized trial of a sample intervention."
    assert [a.name for a in record.authors] == ["Smith J", "Doe A"]
    assert record.year == 2021
    assert record.published_at is not None and (
        record.published_at.month,
        record.published_at.day,
    ) == (6, 15)
    assert record.venue == "Journal of Example Medicine"

    empty_harness = harness_for(source)
    empty_harness.serve(fx["search_empty"])
    empty_page = await empty_harness.adapter.search(SearchRequest(query="nothing at all", limit=1))
    assert empty_page.records == []
    # No id to summarize, so the adapter never makes the second call.
    assert len(empty_harness.requests) == 1

    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(Identifier("pmid", "23555192"))
    assert got is not None
    assert got.ids[0].value == "23555192"
    assert got.title == "An example randomized trial of a sample intervention."
    assert len(get_harness.requests) == 1
