"""Tests for the docs-site adapter (LLD-sources-v3 3.3, 5.11; PRD-sources-v5 SRC-20, SRC-23).

In M1 a docs site serves ``get`` only: the allowlist and ``robots.txt`` are checked before
any page is fetched. The generic checks run in ``tests/sources/test_conformance.py``; this
file covers what SRC-23 adds and how the six default instances are built.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier
from research_mcp.core.models import TextResponse
from research_mcp.sources.base import Capability, SourceContext
from research_mcp.sources.docs_site import ADAPTER, INSTANCE_MODEL, SPEC, instance_spec
from research_mcp.sources.registry import RegisteredSource, SourceRegistry
from research_mcp.testing.clock import FakeClock

DEFAULT_INSTANCES = {
    "docs_site_keycloak": "www.keycloak.org",
    "docs_site_ory": "www.ory.sh",
    "docs_site_opa": "www.openpolicyagent.org",
    "docs_site_vault": "developer.hashicorp.com",
    "docs_site_syncope": "syncope.apache.org",
    "docs_site_freeipa": "www.freeipa.org",
}
ROBOTS = "User-agent: *\nDisallow: /docs/private/\n"
TRICKS = [
    "https://keycloak.org.evil.example/docs/",
    "https://www.keycloak.org.evil.example/docs/",
    "https://evil.example/?next=www.keycloak.org/docs/",
    "https://evil.example/www.keycloak.org/docs/",
    "https://www.keycloak.org@evil.example/docs/",
    "https://www.keycloak.org/docs/../admin",
    "https://www.keycloak.org/%2e%2e/admin",
    "https://www.keycloak.org/docsx/",
    "http://www.keycloak.org/docs/",
]


def keycloak(conformance: SourceRegistry) -> RegisteredSource:
    source = conformance.get("docs_site_keycloak")
    assert source is not None
    return source


def page(title: str) -> bytes:
    return f"<!doctype html><html><head><title>{title}</title></head><body/></html>".encode()


def serve_site(harness: Any, robots: str = ROBOTS) -> None:
    """``robots.txt`` and one page for every other path."""

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, stream=httpx.ByteStream(robots.encode()))
        return httpx.Response(200, stream=httpx.ByteStream(page("Server Administration Guide")))

    harness.respond = respond


async def test_allowlist_substring_traversal_and_robots_disallow_refused(
    conformance: SourceRegistry, harness_for: Any
) -> None:
    """@spec SRC-23: Hosts and paths outside the allowlist, substring tricks included, and
    paths ``robots.txt`` disallows are refused before any page is fetched."""
    harness = harness_for(keycloak(conformance))
    serve_site(harness)

    for url in TRICKS:
        with pytest.raises(HttpError) as caught:
            await harness.adapter.get(Identifier("url", url))
        assert caught.value.code is ErrorCode.BLOCKED_BY_POLICY, url
    assert harness.requests == [], "a refused URL reached the network"

    with pytest.raises(HttpError) as caught:
        await harness.adapter.get(Identifier("url", "https://www.keycloak.org/docs/private/a"))
    assert (caught.value.code, caught.value.detail) == (ErrorCode.BLOCKED_BY_POLICY, "robots")
    assert [str(r.url) for r in harness.requests] == ["https://www.keycloak.org/robots.txt"]

    record = await harness.adapter.get(
        Identifier("url", "https://www.keycloak.org/docs/latest/server_admin/")
    )
    assert record is not None and record.title == "Server Administration Guide"
    assert [str(r.url) for r in harness.requests] == [
        "https://www.keycloak.org/robots.txt",
        "https://www.keycloak.org/docs/latest/server_admin/",
    ]
    assert {r.url.host for r in harness.requests} <= harness.adapter.spec.hosts


async def test_robots_is_checked_against_the_cleaned_path(
    conformance: SourceRegistry, harness_for: Any
) -> None:
    """@spec SRC-23: A dot segment cannot step around a ``robots.txt`` rule."""
    harness = harness_for(keycloak(conformance))
    serve_site(harness)
    with pytest.raises(HttpError) as caught:
        await harness.adapter.get(Identifier("url", "https://www.keycloak.org/docs/x/../private/a"))
    assert caught.value.detail == "robots"
    assert len(harness.requests) == 1


class RedirectingHttp:
    """An ``HttpPort`` whose answer arrives from another URL, as after a redirect."""

    def __init__(self, final_url: str) -> None:
        self.final_url = final_url
        self.calls: list[str] = []

    async def get_text(self, url: str, *, source: str, **kwargs: Any) -> TextResponse:
        self.calls.append(url)
        if url.endswith("/robots.txt"):
            return TextResponse(url=url, status=200, content_type="text/plain", text="")
        return TextResponse(
            url=self.final_url,
            status=200,
            content_type="text/html",
            text=page("Admin console").decode(),
        )


@pytest.mark.parametrize(
    "final_url",
    ["https://www.keycloak.org/admin/console", "https://evil.example/docs/"],
)
async def test_a_redirect_outside_the_allowlist_is_refused_and_the_body_discarded(
    conformance: SourceRegistry, final_url: str
) -> None:
    """@spec SRC-23: A final URL outside the allowlist is ``blocked_by_policy``."""
    source = keycloak(conformance)
    http = RedirectingHttp(final_url)
    ctx = SourceContext(
        http=http,  # type: ignore[arg-type]
        mcp=None,
        settings=source.settings,
        clock=FakeClock(datetime(2026, 10, 28, tzinfo=UTC)),
        contact_email=None,
    )
    adapter = ADAPTER(source.spec, ctx)
    with pytest.raises(HttpError) as caught:
        await adapter.get(Identifier("url", "https://www.keycloak.org/docs/"))
    assert caught.value.code is ErrorCode.BLOCKED_BY_POLICY
    assert http.calls[-1] == "https://www.keycloak.org/docs/"


async def test_get_maps_a_page_to_a_webpage_record(
    conformance: SourceRegistry, harness_for: Any, fixtures_of: Any
) -> None:
    """@spec SRC-20: ``get_ok`` maps to a ``webpage`` record keyed by its URL."""
    source = keycloak(conformance)
    harness = harness_for(source)
    harness.serve(fixtures_of(source)["get_ok"])
    url = "https://www.keycloak.org/docs/latest/server_admin/index.html"
    record = await harness.adapter.get(Identifier("url", url))
    assert record is not None
    assert [(i.scheme, i.value) for i in record.ids] == [("url", url)]
    assert record.title == "Server Administration Guide"
    assert record.work_type == "webpage"
    assert record.abstract and "Keycloak" in record.abstract
    assert record.provenance.source == "docs_site_keycloak"
    assert record.provenance.upstream_id == url
    assert record.provenance.retrieved_at == harness.clock.now()


async def test_get_ignores_identifiers_that_are_not_urls(
    conformance: SourceRegistry, harness_for: Any
) -> None:
    """@spec SRC-20: A docs site serves ``url`` identifiers only and calls nothing else."""
    harness = harness_for(keycloak(conformance))
    assert await harness.adapter.get(Identifier("doi", "10.5555/x")) is None
    assert harness.requests == []


def test_six_default_instances_are_get_only_and_allow_only_their_hosts(
    conformance: SourceRegistry, fixtures_of: Any
) -> None:
    """@spec SRC-20: The six default docs sites register as ``get``-only instances with
    their allowed hosts as ``hosts`` and share the kind's seven fixtures."""
    found = {s.spec.id: s for s in conformance.all() if s.spec.instance_of == "docs_site"}
    assert set(found) == set(DEFAULT_INSTANCES)
    for instance_id, host in DEFAULT_INSTANCES.items():
        spec = found[instance_id].spec
        assert spec.capabilities == frozenset({Capability.GET})
        assert spec.hosts == frozenset({host})
        assert spec.id_schemes == frozenset({"url"})
        assert spec.group == "vendor_docs"
        assert len(fixtures_of(found[instance_id])) == 7
    assert conformance.get(SPEC.id) is None, "the kind is listed only when unconfigured"


@pytest.mark.parametrize(
    "fields",
    [
        {"title": "x", "allowed_hosts": [], "path_prefixes": ["/"], "sitemap": "https://a.b/s"},
        {"title": "x", "allowed_hosts": ["a.b"], "path_prefixes": [], "sitemap": "https://a.b/s"},
        {"title": "x", "allowed_hosts": ["a.b"], "path_prefixes": ["docs/"], "sitemap": None},
        {"title": "x", "allowed_hosts": ["a.b"], "path_prefixes": ["/"]},
        {
            "title": "x",
            "allowed_hosts": ["a.b"],
            "path_prefixes": ["/"],
            "sitemap": "https://a.b/s",
            "seed_urls": ["https://a.b/"],
        },
        {"title": "x", "allowed_hosts": ["a.b"], "path_prefixes": ["/"], "sitemap": "http://a.b/s"},
        {
            "title": "x",
            "allowed_hosts": ["a.b"],
            "path_prefixes": ["/"],
            "sitemap": "https://c.d/s",
        },
        {
            "title": "x",
            "allowed_hosts": ["a.b"],
            "path_prefixes": ["/"],
            "seed_urls": ["https://u@a.b/"],
        },
        {
            "title": "x",
            "allowed_hosts": ["https://a.b"],
            "path_prefixes": ["/"],
            "seed_urls": ["https://a.b/"],
        },
        {
            "title": "x",
            "allowed_hosts": ["a.b"],
            "path_prefixes": ["/"],
            "seed_urls": ["https://a.b/"],
            "extra": 1,
        },
    ],
    ids=[
        "no-hosts",
        "no-prefixes",
        "relative-prefix",
        "no-seed",
        "sitemap-and-seeds",
        "http-sitemap",
        "sitemap-off-host",
        "seed-userinfo",
        "host-with-scheme",
        "unknown-field",
    ],
)
def test_invalid_instance_settings_are_rejected(fields: dict[str, Any]) -> None:
    """@spec SRC-23: An instance can only allow https pages on hosts it names."""
    with pytest.raises(ValidationError):
        INSTANCE_MODEL.model_validate(fields)


def test_instance_spec_takes_id_title_and_hosts_from_the_settings() -> None:
    """@spec SRC-23: An instance's ``hosts`` are its ``allowed_hosts``, normalized."""
    cfg = INSTANCE_MODEL.model_validate(
        {
            "title": "Example docs",
            "allowed_hosts": ["Docs.Example.ORG."],
            "path_prefixes": ["/docs/"],
            "seed_urls": ["https://docs.example.org/docs/"],
            "follow_links": True,
        }
    )
    spec = instance_spec(SPEC, "docs_site_example", cfg)
    assert (spec.id, spec.title, spec.instance_of) == (
        "docs_site_example",
        "Example docs",
        "docs_site",
    )
    assert spec.hosts == frozenset({"docs.example.org"})


def conformance_suite() -> ModuleType:
    """A private copy of ``tests/sources/test_conformance.py``; the original is untouched."""
    path = Path(__file__).parent.parent / "test_conformance.py"
    spec = importlib.util.spec_from_file_location("docs_site_conformance_copy", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("instance_id", sorted(DEFAULT_INSTANCES))
async def test_conformance_checks_pass_for_a_url_inside_the_allowlist(
    instance_id: str,
    conformance: SourceRegistry,
    harness_for: Any,
    fixtures_of: Any,
    counting_stream: Any,
) -> None:
    """@spec SRC-20: Each default docs site passes the conformance checks (``get``, 429,
    5xx, malformed, oversize, hosts, probe) when the identifier is a page it may fetch.

    The suite's own identifier, ``https://conformance.invalid/1``, is outside every
    allowlist, so SRC-23 refuses it; this copy swaps in the instance's first page.
    """
    source = conformance.get(instance_id)
    assert source is not None
    adapter = ADAPTER(source.spec, harness_for(source).adapter.ctx)
    assert adapter.instance is not None
    first_page = f"https://{adapter.instance.allowed_hosts[0]}{adapter.instance.path_prefixes[0]}"
    suite = conformance_suite()
    suite.CONFORMANCE_IDS["url"] = first_page
    await suite.run_conformance(source, harness_for, fixtures_of, counting_stream)
