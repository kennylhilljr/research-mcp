"""Tests for the ORCID adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 SRC-20).

Generic conformance (429/5xx/malformed/oversize/host policy/probe) is already checked for
every registered adapter, ORCID included, by
``tests/sources/test_conformance.py::test_conformance_passes[orcid]``; because ORCID
declares only ``Capability.AUTHORS``, that run exercises ``search_authors`` as the generic
suite's first call. This file covers what it does not: that ``search`` and ``get`` are
undeclared stubs, the query-by-name and query-by-orcid paths, and the author mapping.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.orcid import ADAPTER, SPEC, OrcidAuthor
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_orcid_declares_only_authors_and_maps_the_expanded_result(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: ORCID declares only authors and maps name, orcid id and affiliation."""
    source = _registered()
    assert source.spec.capabilities == frozenset({Capability.AUTHORS})
    assert source.spec.auth is None
    assert source.spec.hosts == frozenset({"pub.orcid.org"})

    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["search_ok"])
    authors = await harness.adapter.search_authors(query="Researcher", orcid=None, limit=5)
    request = harness.requests[0]
    assert request.url.host == "pub.orcid.org"
    assert request.url.params["q"] == "Researcher"
    assert request.headers["accept"] == "application/json"

    assert len(authors) == 1
    author = authors[0]
    assert isinstance(author, OrcidAuthor)
    assert author.name == "Jane Researcher"
    assert author.orcid == "0000-0002-1825-0097"
    assert author.affiliations == ["Example University"]


# @spec SRC-20
async def test_orcid_id_lookup_queries_by_orcid_field(harness_for: Any, fixtures_of: Any) -> None:
    """@spec SRC-20: an explicit orcid iD is folded into the Lucene ``orcid:<id>`` query."""
    source = _registered()
    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["get_ok"])
    authors = await harness.adapter.search_authors(query=None, orcid="0000-0002-1825-0097", limit=1)
    request = harness.requests[0]
    assert request.url.params["q"] == "orcid:0000-0002-1825-0097"
    assert len(authors) == 1


# @spec SRC-20
async def test_orcid_search_and_get_are_stubs_for_undeclared_capabilities(
    harness_for: Any,
) -> None:
    """@spec SRC-20: search() and get() are never called for orcid; their stubs are inert."""
    source = _registered()
    assert Capability.SEARCH not in source.spec.capabilities
    assert Capability.GET not in source.spec.capabilities
    harness = harness_for(source)
    page = await harness.adapter.search(SearchRequest(query="anything", limit=1))
    assert page.records == []
    assert harness.requests == []
