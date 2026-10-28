"""Site-set query building for the ``web`` group (LLD-sources-v3 5.8; SRC-FR-22, SRC-31).

Pure functions: no I/O, no secrets, no adapter state. Federation resolves a ``site_set``
before any source is called, so an unknown name never reaches the network.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from research_mcp.core.errors import ErrorCode, ToolError


@dataclass(frozen=True)
class SiteBatches:
    queries: list[str]
    truncated: bool


# @spec SRC-31
def resolve_site_set(name: str, site_sets: Mapping[str, Sequence[str]]) -> tuple[str, ...]:
    """The set's domains, or ``invalid_argument`` for an unknown or empty set."""
    domains = site_sets.get(name)
    if not domains:
        raise ToolError(ErrorCode.INVALID_ARGUMENT, f"unknown site set: {name}")
    return tuple(domains)


def site_query(query: str, domains: Sequence[str]) -> str:
    """``(<query>) (site:a OR site:b ...)``, as v1 built it."""
    sites = " OR ".join(f"site:{domain}" for domain in domains)
    return f"({query}) ({sites})"


def _label(domain: str) -> str:
    """The domain's registrable label: ``keycloak`` for ``docs.keycloak.org``."""
    parts = domain.split(".")
    return parts[-2] if len(parts) >= 2 else parts[0]


def _ranked(query: str, domains: Sequence[str]) -> list[str]:
    """The query-named domains first, the rest in their given order."""
    lowered = query.lower()
    named = [domain for domain in domains if _label(domain) in lowered]
    rest = [domain for domain in domains if domain not in named]
    return named + rest


# @spec SRC-31
def site_batches(
    query: str, domains: Sequence[str], max_chars: int, max_batches: int
) -> SiteBatches:
    """Pack ``domains`` greedily into at most ``max_batches`` queries of ``max_chars``.

    Query-named domains are packed first. ``truncated`` is set when domains remain after
    ``max_batches`` queries; a domain that cannot fit alone in a fresh query is a caller
    error, not a truncation.
    """
    remaining = _ranked(query, domains)
    queries: list[str] = []
    while remaining and len(queries) < max_batches:
        batch: list[str] = []
        for domain in list(remaining):
            if len(site_query(query, [*batch, domain])) > max_chars:
                if not batch:
                    raise ToolError(
                        ErrorCode.INVALID_ARGUMENT,
                        f"no room for one domain in {max_chars} characters",
                    )
                break
            batch.append(domain)
            remaining.remove(domain)
        queries.append(site_query(query, batch))
    return SiteBatches(queries=queries, truncated=bool(remaining))


def host_matches(host: str, domains: Sequence[str]) -> bool:
    """A host matches a domain exactly or as a subdomain, never by substring."""
    return any(host == domain or host.endswith(f".{domain}") for domain in domains)


# @spec SRC-31
def filter_by_host(urls: Sequence[str], domains: Sequence[str]) -> list[str]:
    """The URLs whose host matches a ``site_set`` domain (Vertex, which ignores the query)."""
    return [url for url in urls if host_matches(urlsplit(url).hostname or "", domains)]
