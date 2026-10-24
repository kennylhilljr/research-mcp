"""The M0 discovery tools and the sources resource, through the in-memory MCP client.

LLD-search-v2 2.1 and 2.3; LLD-sources-v2 2.4. The ``contract`` fixture is in conftest.py.
"""

from __future__ import annotations

import json
from typing import Any

from mcp import types
from pydantic import AnyUrl

from research_mcp.core.ids import Identifier
from research_mcp.core.specs import AuthSpec


def keyed_auth() -> AuthSpec:
    return AuthSpec(
        secrets=("KEYED_API_KEY",),
        required=True,
        placement="header",
        param="x-api-key",
        origins=("https://api.keyed.org",),
        signup_url="https://keyed.org/signup",
    )


async def test_list_sources_and_resource_list_every_source_with_state_and_fix(
    contract: Any,
) -> None:
    """@spec SRC-8: list_sources and research://sources list every source with state and fix."""
    contract.add(contract.spec("ready"))
    contract.add(contract.spec("off"))
    contract.add(contract.spec("keyed", auth=keyed_auth()))
    contract.add(contract.spec("mailto", needs_contact=True, group="preprints"))
    services = contract.services(sources={"off": {"enabled": False}})
    expected = {
        "ready": ("ok", None),
        "off": ("disabled", "research-mcp config set sources.off.enabled true"),
        "keyed": ("unconfigured", "research-mcp/KEYED_API_KEY"),
        "mailto": ("unconfigured", "research-mcp config set contact.email"),
    }

    def check(views: list[dict[str, Any]]) -> None:
        assert sorted(v["id"] for v in views) == sorted(expected)
        for view in views:
            state, hint = expected[view["id"]]
            assert view["state"] == state
            if hint is None:
                assert view["fix_hint"] is None
            else:
                assert hint in view["fix_hint"]
                assert view["reason"]

    async with contract.connect(services) as session:
        result = await session.call("list_sources", {})
        assert not result.isError
        assert result.structuredContent is not None
        check(result.structuredContent["data"])
        assert result.structuredContent["source_status"] == []

        resources = await session.client.list_resources()
        assert "research://sources" in [str(r.uri) for r in resources.resources]
        read = await session.client.read_resource(AnyUrl("research://sources"))
        assert len(read.contents) == 1
        content = read.contents[0]
        assert isinstance(content, types.TextResourceContents)
        assert content.mimeType == "application/json"
        check(json.loads(content.text))

        by_group = await session.call("list_sources", {"group": "preprints"})
        assert by_group.structuredContent is not None
        assert [v["id"] for v in by_group.structuredContent["data"]] == ["mailto"]
        by_state = await session.call("list_sources", {"state": "unconfigured"})
        assert by_state.structuredContent is not None
        assert sorted(v["id"] for v in by_state.structuredContent["data"]) == ["keyed", "mailto"]
    assert contract.calls == []


async def test_compact_and_full_fit_budget(contract: Any) -> None:
    """@spec SRCH-22: compact trims authors and abstracts; full keeps them within the budget."""
    long_abstract = "word " * 2000
    contract.add(
        contract.spec("aa"),
        contract.page(
            *(
                contract.record("aa", f"10.1/w{n}", authors=7, abstract=long_abstract)
                for n in range(20)
            )
        ),
    )
    limit = 32_768
    services = contract.services(limits={"response_bytes": limit})
    async with contract.connect(services) as session:
        compact = await session.call("search", {"query": "q"})
        assert not compact.isError
        assert compact.structuredContent is not None
        works = compact.structuredContent["data"]
        assert len(works) == 20
        for work in works:
            assert len(work["authors"]) == 3
            assert work["author_count"] == 7
            assert work["abstract"] is not None
            assert len(work["abstract"]) < len(long_abstract.strip())
            assert work["abstract"].startswith("word word")
            assert set(work) >= {"title", "year", "venue", "ids", "oa"}
        assert compact.structuredContent["truncated"] is False

        full = await session.call("search", {"query": "q", "detail": "full"})
        assert not full.isError
        assert full.structuredContent is not None
        assert full.structuredContent["truncated"] is True
        size = len(json.dumps(full.structuredContent, separators=(",", ":")).encode())
        assert size <= limit
        first = full.structuredContent["data"][0]
        assert len(first["authors"]) == 7
        assert first["abstract"] == long_abstract
        assert [s["source"] for s in full.structuredContent["source_status"]] == ["aa"]


async def test_get_work_id_forms(contract: Any) -> None:
    """@spec SRCH-23: get_work accepts prefixed ids, bare DOIs, resolver and arXiv URLs."""
    asked: list[Identifier] = []

    async def get(ident: Identifier) -> Any:
        asked.append(ident)
        doi = ident.value if ident.scheme == "doi" else "10.1/x"
        return contract.record("aa", doi)

    contract.add(contract.spec("aa"), get=get)
    forms = {
        "doi:10.1234/ABC.5": Identifier("doi", "10.1234/abc.5"),
        "10.1234/ABC.5": Identifier("doi", "10.1234/abc.5"),
        "https://doi.org/10.1234/ABC.5": Identifier("doi", "10.1234/abc.5"),
        "arxiv:2401.01234": Identifier("arxiv", "2401.01234"),
        "https://arxiv.org/abs/2401.01234v2": Identifier("arxiv", "2401.01234", 2),
        "pmid:12345678": Identifier("pmid", "12345678"),
    }
    async with contract.connect() as session:
        for form, ident in forms.items():
            asked.clear()
            result = await session.call("get_work", {"id": form})
            assert not result.isError, form
            assert result.structuredContent is not None
            assert asked == [ident], form
            assert result.structuredContent["data"]["found_in"] == ["aa"]
            assert [s["state"] for s in result.structuredContent["source_status"]] == ["ok"]

        bad = await session.call("get_work", {"id": "not an identifier"})
        assert bad.isError
        assert contract.body(bad)["code"] == "invalid_argument"
