"""Tests for the Crossref retractions and corrections adapter (LLD-sources-v3 5.1, 5.3;
PRD-sources-v5 SRC-20, catalog row 37; LLD-search-v3 5.10).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, ``crossref_updates`` included, by
``tests/sources/test_conformance.py::test_conformance_passes[crossref_updates]``. This file
covers what SRC-20 adds on top of that suite: the updates-only capability, the ``mailto``
contact parameter, and mapping Crossref's ``update-to`` entries to the shared
``UpdateNotice`` model, skipping a kind that is neither a retraction, a correction nor an
expression of concern.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier
from research_mcp.core.models import UpdateNotice
from research_mcp.settings import SourceSettings
from research_mcp.sources.base import Capability
from research_mcp.sources.crossref_updates import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_crossref_updates_maps_notices_and_skips_unrecognized_kinds(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: crossref_updates maps retractions and corrections, skips other kinds."""
    source = _registered()

    assert source.spec.capabilities == frozenset({Capability.UPDATES})
    assert source.spec.needs_contact is True
    assert source.spec.hosts == frozenset({"api.crossref.org"})

    fx = fixtures_of(source)

    # get_ok.json carries a correction, a retraction and an unrecognized "new_version".
    harness = harness_for(source)
    harness.serve(fx["get_ok"])
    notices = await harness.adapter.updates(Identifier("doi", "10.1037/0003-066x.59.1.29"))
    request = harness.requests[0]
    assert request.url.params["mailto"] == "conformance@research-mcp.dev"
    assert len(notices) == 2
    kinds = {notice.kind for notice in notices if isinstance(notice, UpdateNotice)}
    assert kinds == {"correction", "retraction"}
    for notice in notices:
        assert isinstance(notice, UpdateNotice)
        assert notice.source == "crossref_updates"
        assert notice.related is not None
        assert notice.detail_url == f"https://doi.org/{notice.related.value}"
