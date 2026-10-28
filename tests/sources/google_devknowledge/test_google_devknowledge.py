"""Tests for the Google Developer Knowledge adapter (LLD-sources-v3 5.1, 5.3;
PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, Google Developer Knowledge
included, by ``tests/sources/test_conformance.py::test_conformance_passes[google_devknowledge]``.
This file covers what the catalog adds on top of that suite: the ``x-goog-api-key`` header
and the document's own URL mapped to a ``url`` identifier.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.google_devknowledge import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_google_devknowledge_api_key_header_and_url_identifier(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: Google Developer Knowledge sends x-goog-api-key and maps a url identifier."""
    source = _registered()
    assert source.spec.auth is not None
    assert source.spec.auth.placement == "header"
    assert source.spec.auth.param == "x-goog-api-key"
    assert source.spec.auth.required is True
    assert source.spec.hosts == frozenset({"developerknowledge.googleapis.com"})
    assert source.spec.id_schemes == frozenset({"url"})
    key_name = source.spec.auth.secrets[0]
    assert key_name == "GOOGLE_DEVKNOWLEDGE_API_KEY"

    fx = fixtures_of(source)

    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="jetpack compose", limit=1))
    search_request = search_harness.requests[0]
    assert search_request.url.host == "developerknowledge.googleapis.com"
    assert search_request.headers["x-goog-api-key"] == f"fake-{key_name.lower()}"
    assert len(page.records) == 1
    record = page.records[0]
    assert record.ids[0].scheme == "url"
    assert record.ids[0].value == "https://developer.android.com/jetpack/compose"
    assert record.work_type == "webpage"

    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(
        Identifier("url", "https://developer.android.com/jetpack/compose")
    )
    assert got is not None
    assert got.ids[0].value == "https://developer.android.com/jetpack/compose"
    get_request = get_harness.requests[0]
    assert get_request.headers["x-goog-api-key"] == f"fake-{key_name.lower()}"
