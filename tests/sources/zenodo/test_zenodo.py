"""Tests for the Zenodo adapter (LLD-sources-v3 5.1, 4; PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, Zenodo included, by
``tests/sources/test_conformance.py::test_conformance_passes[zenodo]``. This file covers
what this adapter adds on top of that suite: the optional ``ZENODO_TOKEN`` credential, the
creator and PDF-file mapping, and the direct ``records/{id}`` lookup for a Zenodo-shaped DOI.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.registry import RegisteredSource
from research_mcp.sources.zenodo import ADAPTER, SPEC


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_zenodo_optional_token_and_file_mapping(harness_for: Any, fixtures_of: Any) -> None:
    """@spec SRC-20: Zenodo's token is optional, and creators and PDF files map correctly."""
    source = _registered()

    assert Capability.FULLTEXT in source.spec.capabilities
    assert source.spec.needs_contact is False
    assert source.spec.auth is not None
    assert source.spec.auth.required is False
    assert source.spec.auth.secrets == ("ZENODO_TOKEN",)
    assert source.spec.hosts == frozenset({"zenodo.org"})

    fx = fixtures_of(source)

    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="attention", limit=1))
    search_request = search_harness.requests[0]
    assert search_request.url.host == "zenodo.org"
    assert len(page.records) == 1
    record = page.records[0]
    ident = record.ids[0]
    assert (ident.scheme, ident.value) == ("doi", "10.5281/zenodo.1234567")
    assert record.authors[0].name == "Researcher, Jane"
    assert record.authors[0].family == "Researcher"
    assert record.year == 2020
    # The landing page is always a candidate; the .pdf file adds a second one.
    assert len(record.oa_locations) == 2
    assert {loc.kind for loc in record.oa_locations} == {"landing", "pdf"}


# @spec SRC-20
async def test_zenodo_get_by_doi_suffix_uses_the_direct_records_endpoint(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: A Zenodo-shaped DOI (``.../zenodo.<id>``) fetches ``records/{id}``."""
    source = _registered()
    fx = fixtures_of(source)

    direct_harness = harness_for(source)
    direct_harness.serve(fx["get_direct_ok"])
    got = await direct_harness.adapter.get(Identifier("doi", "10.5281/zenodo.1234567"))
    assert got is not None
    assert got.ids[0].value == "10.5281/zenodo.1234567"
    direct_request = direct_harness.requests[0]
    assert direct_request.url.path.endswith("/1234567")
