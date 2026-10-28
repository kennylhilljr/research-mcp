"""Tests for the DBLP adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, DBLP included, by
``tests/sources/test_conformance.py::test_conformance_passes[dblp]``. This file covers what
that suite does not: the DOI-or-url identifier choice, the single-author collapse DBLP's
JSON uses instead of a one-item list, and that ``get`` is a stub never called for a
``search``-only source.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.dblp import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_dblp_declares_only_search_and_maps_doi_and_authors(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: DBLP declares only search, maps its DOI, and lists every author."""
    source = _registered()
    assert source.spec.capabilities == frozenset({Capability.SEARCH})
    assert source.spec.auth is None
    assert source.spec.hosts == frozenset({"dblp.org"})

    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["search_ok"])
    page = await harness.adapter.search(SearchRequest(query="research", limit=1))
    request = harness.requests[0]
    assert request.url.host == "dblp.org"
    assert request.url.params["format"] == "json"

    assert len(page.records) == 1
    record = page.records[0]
    assert [a.name for a in record.authors] == ["Jane Researcher", "Alex Example"]
    ids = {(ident.scheme, ident.value) for ident in record.ids}
    assert ("doi", "10.1000/example.dblp") in ids
    assert ("url", "https://dblp.org/rec/conf/example/ResearcherExample20") in ids
    assert record.year == 2020


# @spec SRC-20
async def test_dblp_search_without_doi_falls_back_to_url_identifier(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: a hit with no DOI still gets a round-trippable url identifier."""
    source = _registered()
    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["get_ok"])
    page = await harness.adapter.search(SearchRequest(query="data management", limit=1))
    assert len(page.records) == 1
    record = page.records[0]
    assert [ident.scheme for ident in record.ids] == ["url"]
    assert record.authors[0].name == "Solo Author"


# @spec SRC-20
async def test_dblp_get_is_a_stub_for_the_undeclared_capability(harness_for: Any) -> None:
    """@spec SRC-20: get() is never called for dblp, and the stub answers None if it were."""
    source = _registered()
    assert Capability.GET not in source.spec.capabilities
    harness = harness_for(source)
    assert await harness.adapter.get(Identifier("doi", "10.1000/example.dblp")) is None
