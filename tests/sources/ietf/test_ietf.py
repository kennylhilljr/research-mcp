"""Tests for the IETF adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, IETF included, by
``tests/sources/test_conformance.py::test_conformance_passes[ietf]``. This file covers what
the catalog adds on top of that suite: the normalized ``rfc`` identifier, the document's
status and ``obsoletes``/``obsoleted_by`` relations, and the RFC Editor fulltext candidate.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.ietf import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_ietf_rfc_identifier_status_and_obsoletes_mapping(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: IETF maps the rfc identifier, status, obsoletes and a fulltext page."""
    source = _registered()

    assert Capability.FULLTEXT in source.spec.capabilities
    assert source.spec.auth is None
    assert source.spec.hosts == frozenset({"datatracker.ietf.org"})
    assert source.spec.id_schemes == frozenset({"rfc"})

    fx = fixtures_of(source)

    # search_ok.json carries rfc8259, with std_level and obsoletes("rfc7159").
    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="json", limit=1))
    search_request = search_harness.requests[0]
    assert search_request.url.host == "datatracker.ietf.org"
    assert search_request.url.params["title__icontains"] == "json"
    assert len(page.records) == 1
    record = page.records[0]
    assert (record.ids[0].scheme, record.ids[0].value) == ("rfc", "8259")
    assert record.extra["status"] == "Internet Standard"
    assert record.extra["obsoletes"] == ["rfc7159"]
    assert record.oa_locations[0].url == "https://www.rfc-editor.org/rfc/rfc8259.html"

    # get_ok.json maps the same document independently of search().
    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(Identifier("rfc", "8259"))
    assert got is not None
    assert got.ids[0].value == "8259"
    assert got.extra["obsoletes"] == ["rfc7159"]
    get_request = get_harness.requests[0]
    assert get_request.url.path.endswith("/rfc8259/")

    candidates = await get_harness.adapter.fulltext_candidates(got)
    assert len(candidates) == 1
    assert candidates[0].location.url == "https://www.rfc-editor.org/rfc/rfc8259.html"
