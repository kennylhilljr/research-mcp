"""Tests for the DOAJ adapter (LLD-sources-v3 5.1; PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, DOAJ included, by
``tests/sources/test_conformance.py::test_conformance_passes[doaj]``. This file covers what
this adapter adds on top of that suite: the ``bibjson.identifier`` DOI mapping, the
year/month date and the ``bibjson.link`` fulltext candidate.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.doaj import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_doaj_bibjson_doi_mapping_and_fulltext_link(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: DOAJ maps the bibjson DOI identifier and a fulltext link candidate."""
    source = _registered()

    assert Capability.FULLTEXT in source.spec.capabilities
    assert source.spec.needs_contact is False
    assert source.spec.auth is None
    assert source.spec.hosts == frozenset({"doaj.org"})

    fx = fixtures_of(source)

    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="attention", limit=1))
    search_request = search_harness.requests[0]
    assert search_request.url.host == "doaj.org"
    assert len(page.records) == 1
    record = page.records[0]
    ident = record.ids[0]
    assert (ident.scheme, ident.value) == ("doi", "10.1037/0003-066x.59.1.29")
    assert record.year == 2020
    assert record.published_at is not None
    assert (record.published_at.year, record.published_at.month) == (2020, 5)
    assert len(record.oa_locations) == 1
    assert record.oa_locations[0].kind == "pdf"

    candidates = await search_harness.adapter.fulltext_candidates(record)
    assert len(candidates) == 1

    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(Identifier("doi", "10.1037/0003-066x.59.1.29"))
    assert got is not None
    assert got.ids[0].value == "10.1037/0003-066x.59.1.29"
