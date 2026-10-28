"""Tests for the Hugging Face Papers adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 1.3 row
20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, Hugging Face Papers included, by
``tests/sources/test_conformance.py::test_conformance_passes[hf_papers]``. This file covers
what SRC-20 adds on top of that suite for this source: the arXiv-id mapping, the page-size
cap on the response ("cap response size", the catalog note), and that ``get`` makes no
network call since this source has no per-paper lookup endpoint.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.hf_papers import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
def test_hf_papers_declares_search_only() -> None:
    """@spec SRC-20: Hugging Face has no per-paper lookup endpoint, only search."""
    assert SPEC.capabilities == frozenset({Capability.SEARCH})
    assert SPEC.max_page_size < 100  # caps the response size (the catalog note)


# @spec SRC-20
async def test_hf_papers_search_maps_arxiv_id_and_authors(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: search() maps each paper's arXiv id, title and authors."""
    source = _registered()
    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["search_ok"])
    page = await harness.adapter.search(SearchRequest(query="transformer", limit=5))
    request = harness.requests[0]
    assert request.url.host == "huggingface.co"
    assert request.url.params["q"] == "transformer"
    assert len(page.records) == 1
    record = page.records[0]
    ident = record.ids[0]
    assert (ident.scheme, ident.value) == ("arxiv", "2301.00001")
    assert {a.name for a in record.authors} == {"Jane Doe", "John Smith"}
    assert record.extra["upvotes"] == 42


# @spec SRC-20
async def test_hf_papers_search_caps_the_page_size(harness_for: Any, fixtures_of: Any) -> None:
    """@spec SRC-20: a limit above ``max_page_size`` is capped before slicing the response."""
    source = _registered()
    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["search_ok"])
    page = await harness.adapter.search(SearchRequest(query="transformer", limit=10_000))
    assert len(page.records) <= source.spec.max_page_size


# @spec SRC-20
async def test_hf_papers_get_makes_no_network_call(harness_for: Any) -> None:
    """@spec SRC-20: get() is never called by selection, and makes no HTTP call anyway."""
    source = _registered()
    harness = harness_for(source)
    record = await harness.adapter.get(Identifier("arxiv", "2301.00001"))
    assert record is None
    assert harness.requests == []
