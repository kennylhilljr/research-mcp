"""Tests for the OpenAlex adapter (LLD-sources-v2 5.1, 5.3; PRD-sources-v5 SRC-12).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, OpenAlex included, by
``tests/sources/test_conformance.py::test_conformance_passes[openalex]``. This file covers
what SRC-12 adds on top of that suite: the ``api_key`` query parameter, the page size cap of
100, the ``topics`` and ``last_known_institutions`` mappings, and the error classifier that
turns an insufficient-budget 429 into ``budget_exhausted``.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.openalex import ADAPTER, SPEC, OpenAlexAuthor, classify_openalex
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


def _json_response(status: int, payload: Any, headers: dict[str, str] | None = None) -> Any:
    merged = {"content-type": "application/json", **(headers or {})}
    return lambda request: httpx.Response(
        status, headers=merged, stream=_Body(json.dumps(payload).encode())
    )


# @spec SRC-12
async def test_openalex_api_key_page_size_and_topics(harness_for: Any, fixtures_of: Any) -> None:
    """@spec SRC-12: OpenAlex sends its API key, caps a page at 100, and maps topics."""
    source = _registered()
    assert source.spec.max_page_size <= 100
    assert source.spec.auth is not None
    assert source.spec.auth.placement == "query"
    assert source.spec.hosts == frozenset({"api.openalex.org"})
    key_name = source.spec.auth.secrets[0]

    fx = fixtures_of(source)

    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="open access", limit=250))
    search_request = search_harness.requests[0]
    assert search_request.url.host == "api.openalex.org"
    assert search_request.url.params["api_key"] == f"fake-{key_name.lower()}"
    assert search_request.url.params["per_page"] == "100"
    assert len(page.records) == 1
    record = page.records[0]
    assert record.extra["topics"] == ["Open Access and Scholarly Communication"]
    ids = {(ident.scheme, ident.value) for ident in record.ids}
    assert ("openalex", "W2741809807") in ids
    assert ("doi", "10.7717/peerj.4375") in ids

    # get_ok.json carries the same work independently of search(), and sends api_key too.
    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(Identifier("doi", "10.7717/peerj.4375"))
    assert got is not None
    assert got.extra["topics"] == ["Open Access and Scholarly Communication"]
    get_request = get_harness.requests[0]
    assert get_request.url.params["api_key"] == f"fake-{key_name.lower()}"


# @spec SRC-12
async def test_openalex_search_authors_maps_last_known_institutions(harness_for: Any) -> None:
    """@spec SRC-12: search_authors maps an author's last_known_institutions to affiliations."""
    source = _registered()
    harness = harness_for(source)
    payload = {
        "results": [
            {
                "id": "https://openalex.org/A2208157607",
                "display_name": "Heather Piwowar",
                "orcid": "https://orcid.org/0000-0003-1613-5981",
                "works_count": 42,
                "last_known_institutions": [{"display_name": "University of Example"}],
            }
        ]
    }
    harness.respond = _json_response(200, payload)
    authors = await harness.adapter.search_authors(query="Piwowar", orcid=None, limit=5)
    assert len(authors) == 1
    author = authors[0]
    assert isinstance(author, OpenAlexAuthor)
    assert author.affiliations == ["University of Example"]
    assert author.works_count == 42
    assert harness.requests[0].url.params["search"] == "Piwowar"


# @spec SRC-12
async def test_openalex_classify_openalex_maps_insufficient_budget(harness_for: Any) -> None:
    """@spec SRC-12: classify_openalex maps an insufficient-budget 429 to budget_exhausted."""
    assert classify_openalex(503, b"insufficient budget") is None
    assert classify_openalex(429, b"plain rate limit") is None
    assert classify_openalex(429, b"Insufficient Budget for this request") == (
        ErrorCode.BUDGET_EXHAUSTED,
        "daily budget",
    )

    source = _registered()
    assert source.spec.error_classifier is classify_openalex
    harness = harness_for(source)
    harness.respond = _json_response(
        429, {"message": "Insufficient budget for this call"}, {"retry-after": "5"}
    )
    with pytest.raises(HttpError) as caught:
        await harness.adapter.search(SearchRequest(query="open access", limit=1))
    assert caught.value.code is ErrorCode.BUDGET_EXHAUSTED
    assert caught.value.detail == "daily budget"
