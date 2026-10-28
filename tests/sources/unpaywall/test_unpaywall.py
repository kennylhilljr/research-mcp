"""Tests for the Unpaywall adapter (LLD-sources-v3 4, 5.1, 5.5; PRD-sources-v5 SRC-20).

Generic conformance (``get_ok``/429/5xx/malformed/oversize/host policy/probe) is already
checked for every registered adapter, Unpaywall included, by
``tests/sources/test_conformance.py::test_conformance_passes[unpaywall]``. This file covers
what this unit adds on top of that suite: the ``email`` contact parameter (no credential),
the ``best_oa_location`` to full-text mapping, and that ``search`` is never declared and
always returns an empty page.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.registry import RegisteredSource
from research_mcp.sources.unpaywall import ADAPTER, SPEC

_DOI = "10.1038/nature12373"


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_unpaywall_declares_no_search_and_needs_contact(harness_for: Any) -> None:
    """@spec SRC-20: Unpaywall declares get and fulltext, not search, and needs a contact
    address instead of a credential."""
    source = _registered()
    assert source.spec.auth is None
    assert source.spec.needs_contact is True
    assert source.spec.capabilities == frozenset({Capability.GET, Capability.FULLTEXT})

    harness = harness_for(source)
    page = await harness.adapter.search(SearchRequest(query="irrelevant", limit=1))
    assert page.records == []
    assert harness.requests == []


# @spec SRC-20
async def test_unpaywall_email_param_and_best_oa_location_mapping(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: get sends the contact email and maps best_oa_location to a full-text
    candidate."""
    source = _registered()
    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["get_ok"])

    got = await harness.adapter.get(Identifier("doi", _DOI))
    assert got is not None
    assert got.ids == [Identifier("doi", _DOI)]
    request = harness.requests[0]
    assert request.url.host == "api.unpaywall.org"
    assert request.url.params["email"] == "conformance@research-mcp.dev"

    candidates = await harness.adapter.fulltext_candidates(got)
    assert len(candidates) == 1
    assert candidates[0].location.url == "https://example.org/paper.pdf"
    assert candidates[0].location.kind == "pdf"
    assert candidates[0].location.license == "cc-by"
