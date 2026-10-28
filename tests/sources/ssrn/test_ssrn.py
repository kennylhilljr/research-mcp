"""Tests for the SSRN adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 1.3 row 19).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, SSRN included, by
``tests/sources/test_conformance.py::test_conformance_passes[ssrn]``. This file covers what
SRC-20 adds on top of that suite for this source: the Crossref ``prefix:10.2139`` filter, that
SSRN has no ``fulltext`` capability, and that a DOI outside the SSRN prefix maps to ``None``.
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
from research_mcp.sources.registry import RegisteredSource
from research_mcp.sources.ssrn import ADAPTER, SPEC


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
def test_ssrn_declares_no_fulltext_capability() -> None:
    """@spec SRC-20: SSRN papers often need a login to download, so no PDF is ever offered."""
    assert Capability.FULLTEXT not in SPEC.capabilities
    assert SPEC.capabilities == frozenset({Capability.SEARCH, Capability.GET})


# @spec SRC-20
async def test_ssrn_search_filters_to_the_crossref_prefix(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: search() calls Crossref with ``filter=prefix:10.2139`` and maps the DOI."""
    source = _registered()
    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["search_ok"])
    page = await harness.adapter.search(SearchRequest(query="capital structure", limit=5))
    request = harness.requests[0]
    assert request.url.host == "api.crossref.org"
    assert request.url.params["filter"] == "prefix:10.2139"
    assert request.url.params["query"] == "capital structure"
    assert len(page.records) == 1
    ident = page.records[0].ids[0]
    assert (ident.scheme, ident.value) == ("doi", "10.2139/ssrn.1234567")
    assert page.records[0].work_type == "preprint"


# @spec SRC-20
async def test_ssrn_get_returns_none_outside_the_ssrn_prefix(harness_for: Any) -> None:
    """@spec SRC-20: a Crossref hit whose DOI is not under 10.2139 is not an SSRN paper."""
    source = _registered()
    harness = harness_for(source)
    harness.respond = _json_response(
        200,
        {"message": {"DOI": "10.1234/not-ssrn.1", "title": ["Something else entirely"]}},
    )
    record = await harness.adapter.get(Identifier("doi", "10.1234/not-ssrn.1"))
    assert record is None
