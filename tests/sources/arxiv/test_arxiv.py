"""Tests for the arXiv adapter (LLD-sources-v2 5.1, 5.3; PRD-sources-v5 SRC-10).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, arXiv included, by
``tests/sources/test_conformance.py::test_conformance_passes[arxiv]``. This file covers what
SRC-10 adds on top of that suite: https only, arXiv version mapping on both ``search`` and
``get``, and the declared rate and concurrency.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.core.specs import RateSpec
from research_mcp.settings import SourceSettings
from research_mcp.sources.arxiv import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-10
async def test_arxiv_https_version_mapping_rate_and_concurrency(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-10: arXiv uses https, maps versions, and declares 1 req/3s at concurrency 1."""
    source = _registered()

    # Declares a spec rate of 1 request per 3 s with concurrency 1.
    assert source.spec.rate == RateSpec(rps=1 / 3, burst=1, concurrency=1)
    assert source.spec.hosts == frozenset({"export.arxiv.org"})

    fx = fixtures_of(source)

    # search_ok.xml carries .../abs/2301.00001v2: https, and the version maps to 2.
    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="research", limit=1))
    assert search_harness.requests[0].url.scheme == "https"
    assert search_harness.requests[0].url.host == "export.arxiv.org"
    assert len(page.records) == 1
    ident = page.records[0].ids[0]
    assert (ident.scheme, ident.value, ident.version) == ("arxiv", "2301.00001", 2)

    # get_ok.xml carries .../abs/2310.01234v1: get() maps the version independently of
    # search(), and the versioned id is sent back upstream as "id_list".
    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    record = await get_harness.adapter.get(Identifier("arxiv", "2310.01234", 1))
    assert record is not None
    got_ident = record.ids[0]
    assert (got_ident.scheme, got_ident.value, got_ident.version) == ("arxiv", "2310.01234", 1)
    assert get_harness.requests[0].url.scheme == "https"
    assert "id_list=2310.01234v1" in str(get_harness.requests[0].url)
