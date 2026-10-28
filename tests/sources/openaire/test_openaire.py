"""Tests for the OpenAIRE adapter (LLD-sources-v3 5.1; PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, OpenAIRE included, by
``tests/sources/test_conformance.py::test_conformance_passes[openaire]``. This file covers
what this adapter adds on top of that suite: the DOI pid mapping and the open-access
``instances`` surfaced as fulltext candidates.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.openaire import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_openaire_doi_pid_mapping_and_fulltext_candidate(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: OpenAIRE maps the DOI pid and an open instance to a fulltext candidate."""
    source = _registered()

    assert Capability.FULLTEXT in source.spec.capabilities
    assert source.spec.needs_contact is False
    assert source.spec.auth is None
    assert source.spec.hosts == frozenset({"api.openaire.eu"})

    fx = fixtures_of(source)

    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="attention", limit=1))
    search_request = search_harness.requests[0]
    assert search_request.url.host == "api.openaire.eu"
    assert len(page.records) == 1
    record = page.records[0]
    ident = record.ids[0]
    assert (ident.scheme, ident.value) == ("doi", "10.1037/0003-066x.59.1.29")
    assert record.year == 2020
    assert len(record.oa_locations) == 1
    assert record.oa_locations[0].kind == "pdf"
    assert record.oa_locations[0].url == "https://example.org/fulltext.pdf"

    candidates = await search_harness.adapter.fulltext_candidates(record)
    assert len(candidates) == 1
    assert candidates[0].location.url == "https://example.org/fulltext.pdf"

    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(Identifier("doi", "10.1037/0003-066x.59.1.29"))
    assert got is not None
    assert got.ids[0].value == "10.1037/0003-066x.59.1.29"
