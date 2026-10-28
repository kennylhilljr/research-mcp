"""Tests for the NVD adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 SRC-20).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, NVD included, by
``tests/sources/test_conformance.py::test_conformance_passes[nvd]``. This file covers what
the catalog adds on top of that suite: the optional ``apiKey`` header, the CVE detail page
as a ``url`` identifier, and the ``vulnerabilities: []`` shape for an unknown CVE (``get``
returns ``None`` without a 404).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.nvd import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


class _Body(httpx.AsyncByteStream):
    def __init__(self, content: bytes) -> None:
        self.content = content

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.content

    async def aclose(self) -> None:
        return None


def _json_response(status: int, payload: Any) -> Any:
    headers = {"content-type": "application/json"}
    body = json.dumps(payload).encode()
    return lambda request: httpx.Response(status, headers=headers, stream=_Body(body))


# @spec SRC-20
async def test_nvd_api_key_header_and_detail_page_identifier(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: NVD sends the optional apiKey header and maps the CVE detail page."""
    source = _registered()
    assert source.spec.auth is not None
    assert source.spec.auth.required is False
    assert source.spec.auth.placement == "header"
    assert source.spec.auth.param == "apiKey"
    assert source.spec.hosts == frozenset({"services.nvd.nist.gov"})
    key_name = source.spec.auth.secrets[0]

    fx = fixtures_of(source)

    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="log4j", limit=1))
    search_request = search_harness.requests[0]
    assert search_request.url.host == "services.nvd.nist.gov"
    assert search_request.headers["apikey"] == f"fake-{key_name.lower()}"
    assert len(page.records) == 1
    record = page.records[0]
    ident = record.ids[0]
    assert ident.scheme == "url"
    assert ident.value == "https://nvd.nist.gov/vuln/detail/CVE-2021-44228"
    assert "Log4j2" in record.abstract

    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(
        Identifier("url", "https://nvd.nist.gov/vuln/detail/CVE-2021-44228")
    )
    assert got is not None
    assert got.ids[0].value == "https://nvd.nist.gov/vuln/detail/CVE-2021-44228"
    get_request = get_harness.requests[0]
    assert get_request.url.params["cveId"] == "CVE-2021-44228"


# @spec SRC-20
async def test_nvd_unknown_cve_returns_none_without_a_404(harness_for: Any) -> None:
    """@spec SRC-20: an empty vulnerabilities list (NVD's not-found shape) maps get() to None."""
    source = _registered()
    harness = harness_for(source)
    harness.respond = _json_response(
        200,
        {
            "resultsPerPage": 1,
            "startIndex": 0,
            "totalResults": 0,
            "format": "NVD_CVE",
            "version": "2.0",
            "timestamp": "2024-01-01T00:00:00.000",
            "vulnerabilities": [],
        },
    )
    got = await harness.adapter.get(
        Identifier("url", "https://nvd.nist.gov/vuln/detail/CVE-0000-00000")
    )
    assert got is None
