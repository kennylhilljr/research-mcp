"""Tests for the OSF adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 1.3 row 16).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, OSF included, by
``tests/sources/test_conformance.py::test_conformance_passes[osf]``. This file covers what
SRC-20 adds on top of that suite for this source: the provider filter, the DOI and
contributors mapping, and the guid-from-DOI lookup that ``get`` uses.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchFilters, SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.osf import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_osf_search_provider_filter_and_mapping(harness_for: Any, fixtures_of: Any) -> None:
    """@spec SRC-20: OSF sends a provider filter and maps the DOI, authors and landing page."""
    source = _registered()
    fx = fixtures_of(source)

    harness = harness_for(source)
    harness.serve(fx["search_ok"])
    page = await harness.adapter.search(
        SearchRequest(query="replication", filters=SearchFilters(provider="psyarxiv"), limit=5)
    )
    request = harness.requests[0]
    assert request.url.host == "api.osf.io"
    assert request.url.params["filter[provider]"] == "psyarxiv"
    assert request.url.params["filter[q]"] == "replication"
    assert len(page.records) == 1
    record = page.records[0]
    ident = record.ids[0]
    assert (ident.scheme, ident.value) == ("doi", "10.31234/osf.io/ezcuj")
    assert {a.name for a in record.authors} == {"Jane Doe", "John Smith"}
    assert record.extra["provider"] == "psyarxiv"
    assert record.oa_locations[0].url == "https://osf.io/ezcuj"
    assert record.oa_locations[0].kind == "landing"
    # search_ok.json carries a non-null links.next, so the page reports a next cursor.
    assert page.next_cursor == "2"


# @spec SRC-20
async def test_osf_get_resolves_the_guid_from_the_doi(harness_for: Any, fixtures_of: Any) -> None:
    """@spec SRC-20: get() extracts the OSF guid from the DOI suffix and fetches by id."""
    source = _registered()
    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["get_ok"])
    record = await harness.adapter.get(Identifier("doi", "10.31234/osf.io/ezcuj"))
    assert record is not None
    assert record.title == "Replication Crisis in Social Psychology"
    request = harness.requests[0]
    assert str(request.url).startswith("https://api.osf.io/v2/preprints/ezcuj/")
