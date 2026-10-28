"""Tests for the OpenCitations adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 SRC-20,
catalog row 36).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, OpenCitations included, by
``tests/sources/test_conformance.py::test_conformance_passes[opencitations]``. This file
covers what SRC-20 adds on top of that suite: the citations-only capability, the optional
token header, and the ``citing``/``cited`` direction mapping over the Index API.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.opencitations import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_opencitations_citations_only_and_direction_mapping(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: OpenCitations serves only citations, over an optional token header."""
    source = _registered()

    assert source.spec.capabilities == frozenset({Capability.CITATIONS})
    assert source.spec.auth is not None
    assert source.spec.auth.required is False
    assert source.spec.auth.placement == "header"
    assert source.spec.hosts == frozenset({"opencitations.net"})
    key_name = source.spec.auth.secrets[0]

    fx = fixtures_of(source)

    # get_ok.json carries one edge: 10.1037/... cites 10.1186/1756-8722-6-59.
    citing_harness = harness_for(source)
    citing_harness.serve(fx["get_ok"])
    doi = Identifier("doi", "10.1186/1756-8722-6-59")
    page = await citing_harness.adapter.citations(doi, "citing", None, 10)
    citing_request = citing_harness.requests[0]
    assert citing_request.url.host == "opencitations.net"
    assert "/citations/" in str(citing_request.url)
    assert citing_request.headers["authorization"] == f"fake-{key_name.lower()}"
    assert [(i.scheme, i.value) for i in page.ids] == [("doi", "10.1037/0003-066x.59.1.29")]

    # The "cited" direction calls the "references" endpoint and reads the other field.
    cited_harness = harness_for(source)
    cited_harness.serve(fx["get_ok"])
    cited_page = await cited_harness.adapter.citations(doi, "cited", None, 10)
    cited_request = cited_harness.requests[0]
    assert "/references/" in str(cited_request.url)
    assert [(i.scheme, i.value) for i in cited_page.ids] == [("doi", "10.1186/1756-8722-6-59")]
