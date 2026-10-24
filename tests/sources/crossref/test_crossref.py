"""Tests for the Crossref adapter (LLD-sources-v2 5.1, 5.3; PRD-sources-v5 SRC-11).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, Crossref included, by
``tests/sources/test_conformance.py::test_conformance_passes[crossref]``. This file covers
what SRC-11 adds on top of that suite: the ``mailto`` contact parameter, DOI and issued-date
mapping, and the declared ``updates`` capability.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.crossref import ADAPTER, SPEC, CrossrefUpdate
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-11
async def test_crossref_mailto_doi_date_mapping_and_updates_capability(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-11: Crossref sends mailto, maps DOIs and issued dates, and declares updates."""
    source = _registered()

    # Declares the updates capability, needs a contact address, and calls only Crossref.
    assert Capability.UPDATES in source.spec.capabilities
    assert source.spec.needs_contact is True
    assert source.spec.hosts == frozenset({"api.crossref.org"})

    fx = fixtures_of(source)

    # search_ok.json carries DOI "10.1037/0003-066X.59.1.29" and issued date 2020-05-01.
    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="attention", limit=1))
    search_request = search_harness.requests[0]
    assert search_request.url.host == "api.crossref.org"
    assert search_request.url.params["mailto"] == "conformance@research-mcp.dev"
    assert len(page.records) == 1
    record = page.records[0]
    ident = record.ids[0]
    assert (ident.scheme, ident.value) == ("doi", "10.1037/0003-066x.59.1.29")
    assert record.published_at is not None
    assert (record.published_at.year, record.published_at.month, record.published_at.day) == (
        2020,
        5,
        1,
    )
    assert record.year == 2020

    # get_ok.json maps the same DOI and date independently of search(), and sends mailto too.
    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(Identifier("doi", "10.1037/0003-066x.59.1.29"))
    assert got is not None
    assert got.ids[0].value == "10.1037/0003-066x.59.1.29"
    assert got.published_at is not None and got.published_at.year == 2020
    get_request = get_harness.requests[0]
    assert get_request.url.params["mailto"] == "conformance@research-mcp.dev"

    # get_ok.json also carries an update-to entry: updates() maps it to a CrossrefUpdate.
    updates_harness = harness_for(source)
    updates_harness.serve(fx["get_ok"])
    notices = await updates_harness.adapter.updates(Identifier("doi", "10.1037/0003-066x.59.1.29"))
    assert len(notices) == 1
    notice = notices[0]
    assert isinstance(notice, CrossrefUpdate)
    assert notice.kind == "correction"
    assert notice.related is not None and notice.related.value == "10.1037/0003-066x.59.1.30"
    assert notice.date is not None and notice.date.year == 2021
    assert notice.source == "crossref"
