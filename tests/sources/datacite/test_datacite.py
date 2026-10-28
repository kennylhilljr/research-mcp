"""Tests for the DataCite adapter (LLD-sources-v3 5.1, 5.5; PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, DataCite included, by
``tests/sources/test_conformance.py::test_conformance_passes[datacite]``. This file covers
what this unit adds on top of that suite: the JSON:API ``data.attributes`` mapping (DOI,
title, creators, resolvable URL) and ``page[number]`` pagination.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.datacite import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource

_DOI = "10.5061/dryad.8515"


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_datacite_doi_creator_and_url_mapping(harness_for: Any, fixtures_of: Any) -> None:
    """@spec SRC-20: DataCite needs no credential and maps the JSON:API DOI record."""
    source = _registered()
    assert source.spec.auth is None
    assert source.spec.hosts == frozenset({"api.datacite.org"})

    fx = fixtures_of(source)
    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="dryad", limit=1))
    search_request = search_harness.requests[0]
    assert search_request.url.params["page[size]"] == "1"
    assert search_request.url.params["page[number]"] == "1"
    assert len(page.records) == 1
    record = page.records[0]
    assert record.ids == [Identifier("doi", _DOI)]
    assert record.authors[0].name == "Jane Researcher"
    assert (
        record.oa_locations[0].url == "https://datadryad.org/stash/dataset/doi:10.5061/dryad.8515"
    )
    assert record.work_type == "dataset"

    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(Identifier("doi", _DOI))
    assert got is not None
    assert got.ids == [Identifier("doi", _DOI)]
    assert got.year == 2015
