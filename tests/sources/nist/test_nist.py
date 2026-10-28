"""Tests for the NIST adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, NIST included, by
``tests/sources/test_conformance.py::test_conformance_passes[nist]``. This file covers what
the catalog adds on top of that suite: the Crossref prefix filter and the CSRC landing page
mapped from ``resource.primary.URL`` (SRC-20: "Crossref prefix 10.6028 plus CSRC pages").
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.nist import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_nist_prefix_filter_doi_mapping_and_csrc_landing_page(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: NIST filters to prefix 10.6028, maps DOIs and a CSRC landing page."""
    source = _registered()

    assert Capability.FULLTEXT in source.spec.capabilities
    assert source.spec.auth is None
    assert source.spec.hosts == frozenset({"api.crossref.org"})

    fx = fixtures_of(source)

    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="digital identity", limit=1))
    search_request = search_harness.requests[0]
    assert search_request.url.host == "api.crossref.org"
    assert search_request.url.params["filter"] == "prefix:10.6028"
    assert len(page.records) == 1
    record = page.records[0]
    ident = record.ids[0]
    assert (ident.scheme, ident.value) == ("doi", "10.6028/nist.sp.800-63-3")
    assert record.oa_locations[0].url == "https://csrc.nist.gov/pubs/sp/800/63/3/upd2/final"
    assert record.oa_locations[0].kind == "landing"

    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(Identifier("doi", "10.6028/nist.sp.800-63-3"))
    assert got is not None
    assert got.oa_locations[0].url == "https://csrc.nist.gov/pubs/sp/800/63/3/upd2/final"

    candidates = await get_harness.adapter.fulltext_candidates(got)
    assert len(candidates) == 1
    assert candidates[0].location.url == got.oa_locations[0].url
