"""Tests for the ERIC adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 SRC-20, catalog
row 38).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, ERIC included, by
``tests/sources/test_conformance.py::test_conformance_passes[eric]``. This file covers what
SRC-20 adds on top of that suite: no credential, mapping a record to a ``url`` identifier
(ERIC has no identifier scheme of its own), and resolving that identifier's accession
number back out of its query string on ``get``.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier, normalize_url
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.eric import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_eric_no_credential_and_url_identifier_round_trip(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: ERIC needs no credential and maps a record to a url identifier."""
    source = _registered()

    assert source.spec.auth is None
    assert source.spec.hosts == frozenset({"api.ies.ed.gov"})

    fx = fixtures_of(source)

    # search_ok.json carries accession EJ1197742.
    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="formative assessment"))
    search_request = search_harness.requests[0]
    assert search_request.url.host == "api.ies.ed.gov"
    assert search_request.url.params["search"] == "formative assessment"
    assert len(page.records) == 1
    record = page.records[0]
    assert record.extra["eric_id"] == "EJ1197742"
    assert record.year == 2019
    assert len(record.authors) == 2
    ident = record.ids[0]
    assert ident.scheme == "url"
    assert ident.value == normalize_url("https://eric.ed.gov/?id=EJ1197742")

    # get() resolves the url identifier search() produced back to the accession number.
    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(ident)
    assert got is not None
    assert got.extra["eric_id"] == "EJ1197742"
    get_request = get_harness.requests[0]
    assert get_request.url.params["search"] == "id:EJ1197742"

    # get() also accepts a bare accession number, not only a url identifier.
    bare_harness = harness_for(source)
    bare_harness.serve(fx["get_ok"])
    bare = await bare_harness.adapter.get(Identifier("url", "EJ1197742"))
    assert bare is not None
    assert bare_harness.requests[0].url.params["search"] == "id:EJ1197742"
