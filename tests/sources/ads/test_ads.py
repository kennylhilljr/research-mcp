"""Tests for the NASA ADS adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, ADS included, by
``tests/sources/test_conformance.py::test_conformance_passes[ads]``. This file covers what
that suite does not: the disabled-by-default spec, the bearer token attachment, the DOI and
url identifiers over a bibcode, and the ``citations`` and ``references`` query operators.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.ads import ADAPTER, SPEC
from research_mcp.sources.base import Capability
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_ads_is_disabled_by_default_and_sends_a_bearer_token(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: ADS is off until the owner enables it, and attaches its bearer token."""
    source = _registered()
    assert source.spec.enabled_by_default is False
    assert source.spec.auth is not None
    assert source.spec.auth.placement == "bearer"
    assert source.spec.hosts == frozenset({"api.adsabs.harvard.edu"})
    key_name = source.spec.auth.secrets[0]

    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["search_ok"])
    page = await harness.adapter.search(SearchRequest(query="example", limit=1))
    request = harness.requests[0]
    assert request.headers["authorization"] == f"Bearer fake-{key_name.lower()}"

    assert len(page.records) == 1
    record = page.records[0]
    ids = {(ident.scheme, ident.value) for ident in record.ids}
    assert ("doi", "10.1086/123456") in ids
    assert any(scheme == "url" and "2005ApJ...622..759B" in value for scheme, value in ids)
    assert record.authors[0].name == "Jane Researcher"


# @spec SRC-20
async def test_ads_get_resolves_a_doi_identifier(harness_for: Any, fixtures_of: Any) -> None:
    """@spec SRC-20: get() with a doi identifier queries ADS by ``doi:"..."``."""
    source = _registered()
    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["get_ok"])
    record = await harness.adapter.get(Identifier("doi", "10.1086/123456"))
    assert record is not None
    request = harness.requests[0]
    assert request.url.params["q"] == 'doi:"10.1086/123456"'


# @spec SRC-20
async def test_ads_citations_uses_the_citations_and_references_operators(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: citing uses ``citations()``, cited uses ``references()``."""
    source = _registered()
    fx = fixtures_of(source)

    citing_harness = harness_for(source)
    citing_harness.serve(fx["search_ok"])
    await citing_harness.adapter.citations(Identifier("doi", "10.1086/123456"), "citing", None, 10)
    assert "citations(bibcode:" in citing_harness.requests[-1].url.params["q"]

    cited_harness = harness_for(source)
    cited_harness.serve(fx["search_ok"])
    await cited_harness.adapter.citations(Identifier("doi", "10.1086/123456"), "cited", None, 10)
    assert "references(bibcode:" in cited_harness.requests[-1].url.params["q"]
    assert Capability.CITATIONS in source.spec.capabilities
