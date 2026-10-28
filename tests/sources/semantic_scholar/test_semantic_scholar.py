"""Tests for the Semantic Scholar adapter (LLD-sources-v3 5.1, 5.5; PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, Semantic Scholar included, by
``tests/sources/test_conformance.py::test_conformance_passes[semantic_scholar]``. This file
covers what this unit adds on top of that suite: the optional ``x-api-key`` header, the DOI
and ``s2`` identifier mapping, and the declared ``citations`` capability over the
``/citations`` and ``/references`` endpoints.
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
from research_mcp.sources.semantic_scholar import ADAPTER, SPEC

_PAPER_ID = "544783878925a1e49473ad93329796726b5fa592"
_DOI = "10.18653/v1/n18-3011"


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
    headers = {"content-type": "application/json"}
    return lambda request: httpx.Response(
        status, headers=headers, stream=_Body(json.dumps(payload).encode())
    )


# @spec SRC-20
async def test_semantic_scholar_optional_key_and_doi_s2_mapping(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: Semantic Scholar sends its optional key and maps DOI and s2 identifiers."""
    source = _registered()
    assert source.spec.auth is not None
    assert source.spec.auth.required is False
    assert source.spec.auth.placement == "header"
    assert source.spec.hosts == frozenset({"api.semanticscholar.org"})
    key_name = source.spec.auth.secrets[0]

    fx = fixtures_of(source)
    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="literature graph", limit=1))
    search_request = search_harness.requests[0]
    assert search_request.url.host == "api.semanticscholar.org"
    assert search_request.headers["x-api-key"] == f"fake-{key_name.lower()}"
    assert len(page.records) == 1
    ids = {(ident.scheme, ident.value) for ident in page.records[0].ids}
    assert ("s2", _PAPER_ID) in ids
    assert ("doi", _DOI) in ids

    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(Identifier("doi", _DOI))
    assert got is not None
    assert got.oa_locations[0].url == "https://aclanthology.org/N18-3011.pdf"


# @spec SRC-20
async def test_semantic_scholar_citations_maps_citing_and_cited(harness_for: Any) -> None:
    """@spec SRC-20: citations maps the citing and cited directions to normalized identifiers."""
    source = _registered()
    assert Capability.CITATIONS in source.spec.capabilities
    harness = harness_for(source)

    harness.respond = _json_response(
        200,
        {
            "offset": 0,
            "next": 10,
            "data": [{"citingPaper": {"paperId": _PAPER_ID, "externalIds": {"DOI": _DOI.upper()}}}],
        },
    )
    page = await harness.adapter.citations(Identifier("doi", _DOI), "citing", None, 10)
    assert page.ids == [Identifier("doi", _DOI)]
    assert page.next_cursor == "10"

    harness.respond = _json_response(
        200, {"offset": 0, "data": [{"citedPaper": {"paperId": _PAPER_ID, "externalIds": {}}}]}
    )
    page = await harness.adapter.citations(Identifier("doi", _DOI), "cited", None, 10)
    assert page.ids == [Identifier("s2", _PAPER_ID)]
    assert page.next_cursor is None
