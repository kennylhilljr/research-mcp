"""Tests for the CORE adapter (LLD-sources-v3 4, 5.1, 5.5; PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, CORE included, by
``tests/sources/test_conformance.py::test_conformance_passes[core]``. This file covers what
this unit adds on top of that suite: the required bearer key, the CORE and DOI identifier
mapping, and ``downloadUrl`` as a full-text PDF location.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.core_ac import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource

_CORE_ID = "38953630"
_DOI = "10.1016/j.example.2020.01.001"


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_core_bearer_key_and_core_doi_mapping(harness_for: Any, fixtures_of: Any) -> None:
    """@spec SRC-20: CORE sends a bearer key and maps CORE and DOI identifiers and the
    download URL to a full-text PDF location."""
    source = _registered()
    assert source.spec.auth is not None
    assert source.spec.auth.required is True
    assert source.spec.auth.placement == "bearer"
    assert source.spec.hosts == frozenset({"api.core.ac.uk"})
    key_name = source.spec.auth.secrets[0]

    fx = fixtures_of(source)
    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="open access", limit=1))
    search_request = search_harness.requests[0]
    assert search_request.headers["authorization"] == f"Bearer fake-{key_name.lower()}"
    assert len(page.records) == 1
    record = page.records[0]
    ids = {(ident.scheme, ident.value) for ident in record.ids}
    assert ("core", _CORE_ID) in ids
    assert ("doi", _DOI) in ids

    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(Identifier("core", _CORE_ID))
    assert got is not None
    candidates = await get_harness.adapter.fulltext_candidates(got)
    assert Capability.FULLTEXT in source.spec.capabilities
    assert len(candidates) == 1
    assert candidates[0].location.url == "https://core.ac.uk/download/38953630.pdf"
    assert candidates[0].location.kind == "pdf"
