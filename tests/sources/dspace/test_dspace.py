"""Tests for the DSpace adapter (LLD-sources-v3 2.3, 3.3, 5.12; PRD-sources-v5 SRC-20, SRC-21).

Generic conformance (search_ok/search_empty/429/5xx/malformed/oversize/host policy/probe) runs
against the bare ``dspace`` kind, which is what the registry lists when no instance is
configured, by ``tests/sources/test_conformance.py::test_conformance_passes[dspace]``. This
file covers what that run cannot: the four instances ``defaults.toml`` ships from one adapter
module (SRC-21), a configured instance passing the same checks with the shared fixtures
(SRC-20), and the item-to-``WorkRecord`` mapping and ``fulltext_candidates`` details.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier
from research_mcp.core.models import Provenance, SearchRequest, WorkRecord
from research_mcp.settings import Settings
from research_mcp.sources.dspace import ADAPTER, DspaceInstance
from research_mcp.sources.registry import RegisteredSource, SourceRegistry

DSPACE_HOSTS = {
    "dspace_mit": "dspace.mit.edu",
    "dspace_harvard": "dash.harvard.edu",
    "dspace_cornell": "ecommons.cornell.edu",
    "dspace_penn": "repository.upenn.edu",
}


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A real ``Settings()`` with no config file, so only ``defaults.toml`` supplies instances."""
    monkeypatch.setenv("HOME", str(tmp_path))
    for name in os.environ:
        if name.startswith("RESEARCH_MCP_"):
            monkeypatch.delenv(name)


def _no_context(spec: Any) -> Any:
    raise AssertionError("the registry built here never builds an adapter")


def _dspace_registry() -> SourceRegistry:
    return SourceRegistry(
        Settings(),
        _no_context,
        has_credential=lambda name: True,
        has_extra=lambda extra: True,
        modules=["research_mcp.sources.dspace"],
    )


def _registered(instance_id: str) -> RegisteredSource:
    source = _dspace_registry().get(instance_id)
    assert source is not None
    return source


class _JsonBody(httpx.AsyncByteStream):
    """A body that arrives unread, as from a network transport (mirrors conftest.WireBody)."""

    def __init__(self, data: Any) -> None:
        self.content = json.dumps(data).encode()

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.content

    async def aclose(self) -> None:
        return None


def _json_response(data: Any) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "application/json"}, stream=_JsonBody(data))


# @spec SRC-21
def test_dspace_creates_four_instances_from_defaults_with_one_adapter_module() -> None:
    """@spec SRC-21: The registry creates four DSpace instances from configuration."""
    sources = {s.spec.id: s for s in _dspace_registry().all()}
    assert set(sources) == set(DSPACE_HOSTS)
    for instance_id, host in DSPACE_HOSTS.items():
        source = sources[instance_id]
        assert source.adapter_cls is ADAPTER
        assert source.spec.instance_of == "dspace"
        assert source.spec.hosts == frozenset({host})
    assert sources["dspace_mit"].spec.title == "DSpace@MIT"
    assert sources["dspace_harvard"].spec.title == "DASH (Harvard)"


# @spec SRC-21
async def test_dspace_probe_records_each_instances_own_version(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-21: Each instance's probe records its own DSpace version, not another's."""
    mit = _registered("dspace_mit")
    harvard = _registered("dspace_harvard")
    fx = fixtures_of(mit)

    mit_harness = harness_for(mit)
    mit_harness.serve(fx["get_ok"])
    mit_result = await mit_harness.adapter.probe()

    harvard_harness = harness_for(harvard)
    harvard_harness.respond = lambda request: _json_response({"dspaceVersion": "7.5"})
    harvard_result = await harvard_harness.adapter.probe()

    assert mit_result.ok and mit_result.shape_ok
    assert mit_result.api_version == "7.6.1"
    assert harvard_result.api_version == "7.5"
    assert mit_result.api_version != harvard_result.api_version
    assert mit_harness.requests[0].url.host == "dspace.mit.edu"
    assert harvard_harness.requests[0].url.host == "dash.harvard.edu"


# @spec SRC-20
async def test_dspace_conformance_for_a_configured_instance(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: ``dspace_mit`` passes the conformance checks with the shared fixtures."""
    source = _registered("dspace_mit")
    fx = fixtures_of(source)

    ok = harness_for(source)
    ok.serve(fx["search_ok"])
    page = await ok.adapter.search(SearchRequest(query="research", limit=5))
    assert page.records
    assert ok.requests[0].url.host == "dspace.mit.edu"

    empty = harness_for(source)
    empty.serve(fx["search_empty"])
    empty_page = await empty.adapter.search(SearchRequest(query="research", limit=5))
    assert empty_page.records == []

    got = harness_for(source)
    got.serve(fx["get_ok"])
    record = await got.adapter.get(Identifier("doi", "10.5555/conformance.1"))
    assert record is not None

    rate_limited = harness_for(source)
    rate_limited.serve_error(fx["err_429"])
    with pytest.raises(HttpError) as caught:
        await rate_limited.adapter.search(SearchRequest(query="research", limit=5))
    assert caught.value.code is ErrorCode.RATE_LIMITED

    bad = harness_for(source)
    bad.serve(fx["malformed"])
    with pytest.raises(HttpError) as caught:
        await bad.adapter.search(SearchRequest(query="research", limit=5))
    assert caught.value.code is ErrorCode.UPSTREAM_ERROR

    probed = harness_for(source)
    probed.serve(fx["get_ok"])
    result = await probed.adapter.probe()
    assert result.ok and result.shape_ok


async def test_dspace_maps_metadata_authors_doi_date_and_type(
    harness_for: Any, fixtures_of: Any
) -> None:
    """The item mapping reads authors, the issued date, DOI and type from DSpace metadata."""
    source = _registered("dspace_mit")
    fx = fixtures_of(source)
    harness = harness_for(source)
    harness.serve(fx["get_ok"])
    record = await harness.adapter.get(Identifier("doi", "10.5555/conformance.1"))
    assert record is not None
    assert record.work_type == "thesis"
    assert record.year == 2020
    assert record.published_at is not None
    assert (record.published_at.month, record.published_at.day) == (11, 15)
    assert record.abstract == "Another abstract."
    assert [a.name for a in record.authors] == ["Jane Doe"]
    assert any(ident.scheme == "doi" for ident in record.ids)
    assert record.extra["dspace_uuid"] == "22222222-2222-2222-2222-222222222222"


async def test_dspace_fulltext_candidates_reads_bitstreams_from_the_original_bundle(
    harness_for: Any,
) -> None:
    """``fulltext_candidates`` lists the ORIGINAL bundle's bitstreams as fulltext locations."""
    source = _registered("dspace_mit")
    harness = harness_for(source)
    harness.respond = lambda request: _json_response(
        {
            "_embedded": {
                "bundles": [
                    {
                        "name": "ORIGINAL",
                        "_embedded": {
                            "bitstreams": [
                                {
                                    "_links": {
                                        "content": {
                                            "href": (
                                                "https://dspace.mit.edu/server/api/core/"
                                                "bitstreams/b1/content"
                                            )
                                        }
                                    }
                                }
                            ]
                        },
                    },
                    {"name": "THUMBNAIL", "_embedded": {"bitstreams": []}},
                ]
            }
        }
    )
    work = WorkRecord(
        ids=[Identifier("handle", "1721.1/1")],
        title="x",
        extra={"dspace_uuid": "22222222-2222-2222-2222-222222222222"},
        provenance=Provenance(
            source="dspace_mit",
            upstream_id="x",
            adapter_version="1",
            retrieved_at=datetime(2026, 10, 23, 12, tzinfo=UTC),
        ),
    )
    candidates = await harness.adapter.fulltext_candidates(work)
    assert len(candidates) == 1
    assert candidates[0].location.url.endswith("/content")
    assert candidates[0].location.kind == "pdf"


async def test_dspace_fulltext_candidates_without_a_known_uuid_is_empty(
    harness_for: Any,
) -> None:
    """A work with no ``dspace_uuid`` extra is never looked up for bitstreams."""
    source = _registered("dspace_mit")
    harness = harness_for(source)
    work = WorkRecord(
        ids=[Identifier("handle", "1721.1/1")],
        title="x",
        provenance=Provenance(
            source="dspace_mit",
            upstream_id="x",
            adapter_version="1",
            retrieved_at=datetime(2026, 10, 23, 12, tzinfo=UTC),
        ),
    )
    assert await harness.adapter.fulltext_candidates(work) == []
    assert harness.requests == []


def test_dspace_instance_model_rejects_a_bad_base_url() -> None:
    """``DspaceInstance`` rejects a non-https ``base_url`` and one with credentials or a query."""
    with pytest.raises(ValidationError):
        DspaceInstance(base_url="http://dspace.example.edu/server/api", title="x")
    with pytest.raises(ValidationError):
        DspaceInstance(base_url="https://user:pass@dspace.example.edu/server/api", title="x")
    with pytest.raises(ValidationError):
        DspaceInstance(base_url="https://dspace.example.edu/server/api?x=1", title="x")
