"""Site-set query building: batching, truncation and host filtering (LLD-sources-v3 5.8).

Every function here is pure: no network, no clock, no secrets.
"""

from __future__ import annotations

import pytest

from research_mcp.core.errors import ErrorCode, ToolError
from research_mcp.sources.sitequery import (
    filter_by_host,
    resolve_site_set,
    site_batches,
    site_query,
)

SITE_SETS = {"v1_docs": ("docs.keycloak.org", "www.openssl.org", "docs.nginx.com")}


def test_resolve_site_set_returns_the_named_domains() -> None:
    """``resolve_site_set`` gives the configured set's domains in order."""
    assert resolve_site_set("v1_docs", SITE_SETS) == (
        "docs.keycloak.org",
        "www.openssl.org",
        "docs.nginx.com",
    )


def test_unknown_site_set_is_invalid_argument_with_no_call() -> None:
    """@spec SRC-31: An unknown or empty site set is ``invalid_argument``; nothing is built."""
    with pytest.raises(ToolError) as unknown:
        resolve_site_set("no_such_set", SITE_SETS)
    assert unknown.value.code is ErrorCode.INVALID_ARGUMENT
    with pytest.raises(ToolError) as empty:
        resolve_site_set("empty_set", {"empty_set": []})
    assert empty.value.code is ErrorCode.INVALID_ARGUMENT


def test_site_query_builds_the_v1_form() -> None:
    """``site_query`` wraps the query and ORs the domains as ``site:`` terms."""
    assert site_query("keycloak config", ["docs.keycloak.org", "www.openssl.org"]) == (
        "(keycloak config) (site:docs.keycloak.org OR site:www.openssl.org)"
    )


def test_brave_batches_at_most_3_of_380_chars_query_domains_first() -> None:
    """@spec SRC-31: Brave splits into at most 3 batches of at most 380 chars, named first."""
    query = "keycloak upgrade guide"
    domains = [f"example-site-{i:02d}.org" for i in range(40)]
    domains.insert(0, "docs.keycloak.org")  # not named by position; ranked by the label match
    result = site_batches(query, domains, max_chars=380, max_batches=3)
    assert len(result.queries) <= 3
    assert all(len(q) <= 380 for q in result.queries)
    assert result.truncated is True
    assert result.queries[0].startswith(f"({query}) (site:docs.keycloak.org")


def test_brave_batches_fit_without_truncation_when_domains_are_few() -> None:
    """With few domains, every domain appears and nothing is truncated."""
    query = "nginx config"
    domains = ["docs.nginx.com", "www.openssl.org"]
    result = site_batches(query, domains, max_chars=380, max_batches=3)
    assert result.truncated is False
    assert len(result.queries) == 1
    for domain in domains:
        assert domain in result.queries[0]


def test_site_batches_raises_when_a_single_domain_cannot_fit() -> None:
    """A domain that cannot fit alone in a fresh query is a caller error, not a truncation."""
    with pytest.raises(ToolError) as caught:
        site_batches(
            "q", ["a-domain-too-long-for-the-budget.example.org"], max_chars=20, max_batches=1
        )
    assert caught.value.code is ErrorCode.INVALID_ARGUMENT


def test_serpapi_and_pse_single_query_with_truncated() -> None:
    """@spec SRC-31: SerpAPI and Programmable Search use one query and flag dropped domains."""
    query = "openssl advisory"
    domains = [f"example-site-{i:02d}.org" for i in range(20)]
    domains.insert(0, "www.openssl.org")
    result = site_batches(query, domains, max_chars=380, max_batches=1)
    assert len(result.queries) == 1
    assert result.truncated is True
    assert "www.openssl.org" in result.queries[0]

    fits = site_batches(query, ["www.openssl.org", "docs.nginx.com"], max_chars=380, max_batches=1)
    assert fits.truncated is False
    assert len(fits.queries) == 1


def test_vertex_filters_results_by_host() -> None:
    """@spec SRC-31: Vertex results are kept only when their host matches a set domain.

    A match is exact or a subdomain, never a substring trick.
    """
    domains = ("keycloak.org", "docs.nginx.com")
    urls = [
        "https://keycloak.org/guides/upgrade",
        "https://docs.keycloak.org/guides/upgrade",  # a subdomain of keycloak.org
        "https://docs.nginx.com/install",
        "https://notkeycloak.org/phish",  # a lookalike host, not a subdomain
        "https://keycloak.org.evil.example/phish",  # the domain as a path/host prefix trick
        "https://evil.example/keycloak.org",  # the domain in the path, not the host
    ]
    assert filter_by_host(urls, domains) == [
        "https://keycloak.org/guides/upgrade",
        "https://docs.keycloak.org/guides/upgrade",
        "https://docs.nginx.com/install",
    ]
