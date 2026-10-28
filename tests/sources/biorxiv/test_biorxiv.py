"""Tests for the bioRxiv adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 1.3 row 17).

Generic conformance (``get_ok``/429/5xx/malformed/oversize/host policy/probe) is already
checked for every registered adapter, bioRxiv included, by
``tests/sources/test_conformance.py::test_conformance_passes[biorxiv]``. This file covers
what SRC-20 adds on top of that suite for this source: no ``search`` capability (and no call
when ``search`` is invoked anyway), the semicolon-joined author mapping, and the
version-numbered PDF fulltext candidate.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.biorxiv import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


class _Body(httpx.AsyncByteStream):
    """A body that arrives unread, as from a network transport (tests/sources/conftest.py)."""

    def __init__(self, content: bytes) -> None:
        self.content = content

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.content

    async def aclose(self) -> None:
        return None


def _json_response(status: int, payload: Any) -> Any:
    return lambda request: httpx.Response(
        status,
        headers={"content-type": "application/json"},
        stream=_Body(json.dumps(payload).encode()),
    )


# @spec SRC-20
def test_biorxiv_declares_no_search_capability() -> None:
    """@spec SRC-20: bioRxiv has no keyword search of its own (discovery runs elsewhere)."""
    assert Capability.SEARCH not in SPEC.capabilities
    assert Capability.GET in SPEC.capabilities
    assert Capability.FULLTEXT in SPEC.capabilities


# @spec SRC-20
async def test_biorxiv_search_never_calls_the_network(harness_for: Any) -> None:
    """@spec SRC-20: search() is never called by selection, and makes no HTTP call anyway."""
    source = _registered()
    harness = harness_for(source)
    page = await harness.adapter.search(SearchRequest(query="anything"))
    assert page.records == []
    assert harness.requests == []


# @spec SRC-20
async def test_biorxiv_get_maps_authors_and_pdf_location(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: get() splits the semicolon-joined authors and builds a versioned PDF URL."""
    source = _registered()
    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["get_ok"])
    record = await harness.adapter.get(Identifier("doi", "10.1101/2020.01.01.012345"))
    assert record is not None
    assert [a.name for a in record.authors] == ["Doe, J.", "Smith, A."]
    assert record.oa_locations[0].url == (
        "https://www.biorxiv.org/content/10.1101/2020.01.01.012345v1.full.pdf"
    )
    assert record.oa_locations[0].kind == "pdf"
    request = harness.requests[0]
    assert request.url.host == "api.biorxiv.org"
    assert "/details/biorxiv/10.1101/2020.01.01.012345" in str(request.url)


# @spec SRC-20
async def test_biorxiv_get_returns_none_for_an_empty_collection(harness_for: Any) -> None:
    """@spec SRC-20: an empty ``collection`` (no posts found) maps to ``None``, not an error."""
    source = _registered()
    harness = harness_for(source)
    harness.respond = _json_response(
        200, {"collection": [], "messages": [{"status": "no posts found"}]}
    )
    record = await harness.adapter.get(Identifier("doi", "10.1101/nonexistent"))
    assert record is None
