"""Tests for the Lens.org adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, Lens included, by
``tests/sources/test_conformance.py::test_conformance_passes[lens]``. This file covers what
that suite does not: the disabled-by-default spec, the ``POST`` JSON body (not query
parameters), the bearer token attachment, the DOI-or-url identifier choice, and that
``get`` is a stub never called for a ``search``-only source.
"""

from __future__ import annotations

import json
from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.lens import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_lens_is_disabled_by_default_and_posts_a_json_body(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: Lens is off until the owner enables it, and posts its query as JSON."""
    source = _registered()
    assert source.spec.enabled_by_default is False
    assert source.spec.capabilities == frozenset({Capability.SEARCH})
    assert source.spec.auth is not None
    assert source.spec.auth.placement == "bearer"
    assert source.spec.hosts == frozenset({"api.lens.org"})
    key_name = source.spec.auth.secrets[0]

    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["search_ok"])
    page = await harness.adapter.search(SearchRequest(query="example", limit=1))
    request = harness.requests[0]
    assert request.method == "POST"
    assert request.headers["authorization"] == f"Bearer fake-{key_name.lower()}"
    body = json.loads(request.content)
    assert body["query"] == "example"
    assert body["size"] == 1

    assert len(page.records) == 1
    record = page.records[0]
    ids = {(ident.scheme, ident.value) for ident in record.ids}
    assert ("doi", "10.1000/example.lens") in ids
    assert record.authors[0].name == "Jane Researcher"
    assert record.venue == "Journal of Examples"


# @spec SRC-20
async def test_lens_get_is_a_stub_for_the_undeclared_capability(harness_for: Any) -> None:
    """@spec SRC-20: get() is never called for lens, and the stub answers None if it were."""
    source = _registered()
    assert Capability.GET not in source.spec.capabilities
    harness = harness_for(source)
    assert await harness.adapter.get(Identifier("doi", "10.1000/example.lens")) is None
