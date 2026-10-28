"""Tests for ``DocsSiteAllowlist`` (LLD-sources-v3 5.11; PRD-sources-v5 SRC-23).

The allowlist matches the parsed host exactly and the parsed, cleaned path at a segment
boundary, so none of the substring tricks of v1's filters get through.
"""

from __future__ import annotations

import pytest

from research_mcp.sources.docs_allowlist import DocsSiteAllowlist

KEYCLOAK = DocsSiteAllowlist(
    allowed_hosts=frozenset({"www.keycloak.org"}),
    path_prefixes=("/docs/", "/guides/"),
)


@pytest.mark.parametrize(
    "url",
    [
        "https://keycloak.org.evil.example/docs/",
        "https://www.keycloak.org.evil.example/docs/",
        "https://evil.example/?next=www.keycloak.org/docs/",
        "https://evil.example/www.keycloak.org/docs/",
        "https://evil.example/#www.keycloak.org/docs/",
        "https://www.keycloak.org@evil.example/docs/",
        "https://user:pw@www.keycloak.org/docs/",
        "https://@www.keycloak.org/docs/",
        "https://www.keycloak.org/docs/../admin",
        "https://www.keycloak.org/docs/%2e%2e/admin",
        "https://www.keycloak.org/%2e%2e/admin",
        "https://www.keycloak.org/docsx/",
        "https://www.keycloak.org/docs%2fx",
        "https://www.keycloak.org/docs%2Fx",
        "https://www.keycloak.org/docs%5cx",
        "https://www.keycloak.org/docs/%252fx",
        "https://www.keycloak.org/docs\\x",
        "https://www.keycloak.org/admin?path=/docs/",
        "https://www.keycloak.org/admin#/docs/",
        "http://www.keycloak.org/docs/",
        "ftp://www.keycloak.org/docs/",
        "https://www.keycloak.org:8443/docs/",
        "https://www.keycloak.org:notaport/docs/",
        "https://www.keyc\tloak.org/docs/",
        "https://www.keycloak.org/docs/\nx",
        "https://keycloak.org/docs/",
        "//www.keycloak.org/docs/",
        "/docs/",
        "",
        "https://[::1]/docs/",
        "https://www.keycloak.org/docs/%ff",
    ],
)
def test_refuses_substring_tricks_traversal_and_bad_origins(url: str) -> None:
    """@spec SRC-23: Hosts and paths outside the allowlist are refused, tricks included."""
    assert KEYCLOAK.allows(url) is False
    assert KEYCLOAK.canonical(url) is None


@pytest.mark.parametrize(
    ("url", "canonical"),
    [
        ("https://www.keycloak.org/docs/", "https://www.keycloak.org/docs/"),
        ("https://www.keycloak.org/docs", "https://www.keycloak.org/docs"),
        (
            "https://www.keycloak.org/docs/latest/x.html",
            "https://www.keycloak.org/docs/latest/x.html",
        ),
        ("https://www.keycloak.org/guides/a?b=c#frag", "https://www.keycloak.org/guides/a?b=c"),
        ("https://WWW.Keycloak.ORG/docs/a", "https://www.keycloak.org/docs/a"),
        ("https://www.keycloak.org./docs/a", "https://www.keycloak.org/docs/a"),
        ("https://www.keycloak.org:443/docs/a", "https://www.keycloak.org/docs/a"),
        ("HTTPS://www.keycloak.org/docs/a", "https://www.keycloak.org/docs/a"),
        ("https://www.keycloak.org/docs/./a", "https://www.keycloak.org/docs/a"),
        ("https://www.keycloak.org/admin/../docs/a", "https://www.keycloak.org/docs/a"),
        ("https://www.keycloak.org/docs/x/%2e%2e/a", "https://www.keycloak.org/docs/a"),
        ("https://www.keycloak.org/docs/a%20b", "https://www.keycloak.org/docs/a%20b"),
        ("https://www.keycloak.org/docs/100%25", "https://www.keycloak.org/docs/100%25"),
    ],
)
def test_allows_paths_under_a_prefix_and_returns_the_cleaned_url(url: str, canonical: str) -> None:
    """@spec SRC-23: A URL on an allowed host under a prefix is allowed, in its cleaned form."""
    assert KEYCLOAK.allows(url) is True
    assert KEYCLOAK.canonical(url) == canonical


def test_prefix_without_trailing_slash_matches_at_a_segment_boundary() -> None:
    """@spec SRC-23: ``/vault/docs`` matches itself and below, never ``/vault/docsx``."""
    vault = DocsSiteAllowlist(frozenset({"developer.hashicorp.com"}), ("/vault/docs",))
    assert vault.allows("https://developer.hashicorp.com/vault/docs")
    assert vault.allows("https://developer.hashicorp.com/vault/docs/what-is-vault")
    assert not vault.allows("https://developer.hashicorp.com/vault/docsx")
    assert not vault.allows("https://developer.hashicorp.com/vault")


def test_internationalized_host_is_compared_in_its_ascii_form() -> None:
    """@spec SRC-23: A Unicode host is converted to IDNA before the exact comparison."""
    allowlist = DocsSiteAllowlist(frozenset({"xn--bcher-kva.example"}), ("/",))
    assert allowlist.canonical("https://bücher.example/a") == "https://xn--bcher-kva.example/a"
    assert not allowlist.allows("https://bücher.example.evil/a")


def test_empty_allowlist_refuses_everything() -> None:
    """@spec SRC-23: An allowlist with no hosts or no prefixes allows nothing."""
    assert not DocsSiteAllowlist(frozenset(), ("/",)).allows("https://www.keycloak.org/")
    assert not DocsSiteAllowlist(frozenset({"www.keycloak.org"}), ()).allows(
        "https://www.keycloak.org/docs/"
    )
