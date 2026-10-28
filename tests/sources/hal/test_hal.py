"""Tests for the HAL adapter (LLD-sources-v3 5.1; PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, HAL included, by
``tests/sources/test_conformance.py::test_conformance_passes[hal]``. This file covers what
this adapter adds on top of that suite: the ``halId_s``/``uri_s`` to ``url`` identifier (HAL
has no scheme of its own in ``core/ids.py``), the optional ``doiId_s`` identifier, the
``openAccess_bool`` fulltext candidate, and ``get`` by a bare ``url`` identifier when no DOI
is known.
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
from research_mcp.sources.hal import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource

_NO_DOI_DOC = {
    "response": {
        "numFound": 1,
        "start": 0,
        "docs": [
            {
                "halId_s": "hal-02222222",
                "title_s": ["A document with no DOI"],
                "authFullName_s": ["Jane Researcher"],
                "producedDate_s": "2019-03-10",
                "docType_s": "COMM",
                "uri_s": "https://hal.science/hal-02222222",
                "openAccess_bool": False,
            }
        ],
    }
}


class _Body(httpx.AsyncByteStream):
    """A body that arrives unread, as from a network transport (``tests/sources/conftest.py``)."""

    def __init__(self, content: bytes) -> None:
        self.content = content

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.content

    async def aclose(self) -> None:
        return None


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_hal_url_and_doi_identifiers_and_fulltext_candidate(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: HAL carries its permalink as a ``url`` identifier plus any ``doiId_s``."""
    source = _registered()

    assert Capability.FULLTEXT in source.spec.capabilities
    assert source.spec.needs_contact is False
    assert source.spec.auth is None
    assert source.spec.hosts == frozenset({"api.archives-ouvertes.fr"})

    fx = fixtures_of(source)

    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="attention", limit=1))
    search_request = search_harness.requests[0]
    assert search_request.url.host == "api.archives-ouvertes.fr"
    assert len(page.records) == 1
    record = page.records[0]
    schemes = {ident.scheme for ident in record.ids}
    assert schemes == {"url", "doi"}
    url_ident = next(ident for ident in record.ids if ident.scheme == "url")
    assert url_ident.value == "https://hal.science/hal-01440606"
    doi_ident = next(ident for ident in record.ids if ident.scheme == "doi")
    assert doi_ident.value == "10.1037/0003-066x.59.1.29"
    assert record.work_type == "article"
    assert len(record.oa_locations) == 1
    assert record.oa_locations[0].url == "https://hal.science/hal-01440606/document"

    candidates = await search_harness.adapter.fulltext_candidates(record)
    assert len(candidates) == 1


# @spec SRC-20
async def test_hal_get_by_url_identifier_without_a_doi(harness_for: Any, fixtures_of: Any) -> None:
    """@spec SRC-20: ``get`` by a ``url`` identifier works for a document with no DOI."""
    source = _registered()
    harness = harness_for(source)
    body = json.dumps(_NO_DOI_DOC).encode()
    harness.respond = lambda request: httpx.Response(
        200, headers={"content-type": "application/json"}, stream=_Body(body)
    )
    got = await harness.adapter.get(Identifier("url", "https://hal.science/hal-02222222"))
    assert got is not None
    assert [ident.scheme for ident in got.ids] == ["url"]
    assert got.work_type == "conference-paper"
    assert got.oa_locations == []
    request = harness.requests[0]
    assert "halId_s%3Ahal-02222222" in str(request.url) or "halId_s:hal-02222222" in str(
        request.url
    )
