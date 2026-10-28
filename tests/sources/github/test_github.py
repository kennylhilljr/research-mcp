"""Tests for the GitHub adapter (LLD-sources-v3 5.1, 5.3; PRD-sources-v5 SRC-20, catalog
row 35).

Generic conformance (``search_ok``/``search_empty``/429/5xx/malformed/oversize/host policy/
probe) is already checked for every registered adapter, GitHub included, by
``tests/sources/test_conformance.py::test_conformance_passes[github]``. This file covers
what SRC-20 adds on top of that suite for GitHub: the bearer token, the repository mapping
to a ``url`` identifier, and resolving that identifier back to ``owner/repo`` on ``get``.
"""

from __future__ import annotations

from typing import Any

from research_mcp.core.ids import Identifier, normalize_url
from research_mcp.core.models import SearchRequest
from research_mcp.settings import SourceSettings
from research_mcp.sources.github import ADAPTER, SPEC
from research_mcp.sources.registry import RegisteredSource


def _registered() -> RegisteredSource:
    return RegisteredSource(
        spec=SPEC, adapter_cls=ADAPTER, settings=SourceSettings(), instance=None
    )


# @spec SRC-20
async def test_github_bearer_token_and_repository_mapping(
    harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: GitHub sends its token as a bearer header and maps a repo to a url id."""
    source = _registered()

    assert source.spec.auth is not None
    assert source.spec.auth.placement == "bearer"
    assert source.spec.auth.required is True
    assert source.spec.hosts == frozenset({"api.github.com"})
    key_name = source.spec.auth.secrets[0]

    fx = fixtures_of(source)

    # search_ok.json carries octocat/Hello-World: the request is paged and bears the token.
    search_harness = harness_for(source)
    search_harness.serve(fx["search_ok"])
    page = await search_harness.adapter.search(SearchRequest(query="hello world", limit=1))
    search_request = search_harness.requests[0]
    assert search_request.url.host == "api.github.com"
    assert search_request.headers["authorization"] == f"Bearer fake-{key_name.lower()}"
    assert search_request.url.params["q"] == "hello world"
    assert len(page.records) == 1
    record = page.records[0]
    ident = record.ids[0]
    assert ident.scheme == "url"
    assert ident.value == normalize_url("https://github.com/octocat/Hello-World")
    assert record.authors[0].name == "octocat"
    assert record.year == 2011

    # get_ok.json maps the same repository independently of search(), and sends the token
    # too; the url identifier search() produced resolves back to "owner/repo" on get().
    get_harness = harness_for(source)
    get_harness.serve(fx["get_ok"])
    got = await get_harness.adapter.get(ident)
    assert got is not None
    assert got.ids[0].value == ident.value
    get_request = get_harness.requests[0]
    assert get_request.headers["authorization"] == f"Bearer fake-{key_name.lower()}"
    assert str(get_request.url).endswith("/repos/octocat/Hello-World")

    # get() also accepts a bare "owner/repo" value, not only a url identifier.
    bare_harness = harness_for(source)
    bare_harness.serve(fx["get_ok"])
    bare = await bare_harness.adapter.get(Identifier("url", "octocat/Hello-World"))
    assert bare is not None
    assert str(bare_harness.requests[0].url).endswith("/repos/octocat/Hello-World")
