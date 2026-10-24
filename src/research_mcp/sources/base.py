"""The source contract: ``SourceSpec``, the adapter protocol and its context.

LLD-sources-v2 2.1 and 5.3. Every source module defines ``SPEC: SourceSpec`` and
``ADAPTER``; the registry discovers them (2.3). Adapters only translate: the shared HTTP
client reached through ``SourceContext.http`` does the I/O, retries, waits and credentials.
"""

import functools
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass as std_dataclass
from dataclasses import field
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING, Literal, Protocol
from urllib.parse import urlsplit

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError
from pydantic import BaseModel, ConfigDict
from pydantic.dataclasses import dataclass

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.models import (
    CitationPage,
    Clock,
    FulltextCandidate,
    Identifier,
    JsonValue,
    ProbeResult,
    SearchPage,
    SearchRequest,
    WorkRecord,
)
from research_mcp.core.specs import AuthSpec, ErrorClassifier, ProbeSpec, RateSpec, SourcePolicy

if TYPE_CHECKING:
    from research_mcp.platform.http import HttpPort
    from research_mcp.settings import SourceSettings


class Capability(StrEnum):
    SEARCH = "search"
    GET = "get"
    FULLTEXT = "fulltext"
    CITATIONS = "citations"
    AUTHORS = "authors"
    UPDATES = "updates"
    CRAWL = "crawl"


GROUPS = frozenset(
    {
        "scholarly",
        "preprints",
        "biomed",
        "repositories",
        "standards",
        "vendor_docs",
        "code",
        "integrity",
        "education",
        "web",
        "reference",
    }
)
KNOWN_EXTRAS = frozenset({"pdf", "embeddings", "macos", "gcp"})

ID_PATTERN = re.compile(r"[a-z][a-z0-9_]{1,39}")
SECRET_NAME_PATTERN = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_HOST_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
HOST_PATTERN = re.compile(rf"{_HOST_LABEL}(?:\.{_HOST_LABEL})*")


def _within(value: float, low: float, high: float) -> bool:
    # Written as one chained comparison so NaN, which compares false, is out of bounds.
    return low <= value <= high


def _https_url(value: str) -> bool:
    try:
        url = urlsplit(value)
    except ValueError:
        return False
    return url.scheme == "https" and bool(url.hostname)


def _check_identity(spec: "SourceSpec") -> None:
    if not ID_PATTERN.fullmatch(spec.id):
        raise ValueError("source id must match [a-z][a-z0-9_]{1,39}")
    if not 1 <= len(spec.title) <= 120:
        raise ValueError("source title must be 1 to 120 characters")
    if spec.group not in GROUPS:
        raise ValueError("source group is not a known group")
    if not spec.capabilities:
        raise ValueError("a source declares at least one capability")
    if not spec.hosts or not all(HOST_PATTERN.fullmatch(host) for host in spec.hosts):
        raise ValueError("hosts must be lowercase bare host names, at least one")


def _check_auth(auth: AuthSpec | None, hosts: frozenset[str]) -> None:
    if auth is None:
        return
    if not auth.origins:
        raise ValueError("auth needs at least one origin")
    if any(urlsplit(origin).hostname not in hosts for origin in auth.origins):
        raise ValueError("every auth origin's host must be in hosts")
    if not auth.secrets or not all(SECRET_NAME_PATTERN.fullmatch(n) for n in auth.secrets):
        raise ValueError("auth secrets must be names matching [A-Z][A-Z0-9_]{0,63}")
    if auth.required and not _https_url(auth.signup_url):
        raise ValueError("a required credential needs an https signup_url")


def _check_rate(rate: RateSpec) -> None:
    if not (0 < rate.rps <= 50):
        raise ValueError("rate.rps must be greater than 0 and at most 50")
    if not 1 <= rate.burst <= 50:
        raise ValueError("rate.burst must be 1 to 50")
    if not 1 <= rate.concurrency <= 16:
        raise ValueError("rate.concurrency must be 1 to 16")
    if rate.daily_quota is not None and rate.daily_quota < 1:
        raise ValueError("rate.daily_quota must be None or at least 1")


def _check_limits(spec: "SourceSpec") -> None:
    if not _within(spec.timeout_s, 0.5, 60):
        raise ValueError("timeout_s must be 0.5 to 60")
    if not 1 <= spec.max_page_size <= 1000:
        raise ValueError("max_page_size must be 1 to 1000")
    if not 1024 <= spec.max_bytes <= 50_000_000:
        raise ValueError("max_bytes must be 1024 to 50000000")
    if not spec.extras <= KNOWN_EXTRAS:
        raise ValueError("extras must be known extras")
    if not 60 <= spec.probe.cadence_s <= 604_800:
        raise ValueError("probe.cadence_s must be 60 to 604800")
    if spec.probe.cost == "metered" and spec.probe.cadence_s < 3600:
        raise ValueError("a metered probe runs at most once an hour")
    if spec.docs_url and not _https_url(spec.docs_url):
        raise ValueError("docs_url must be empty or an https URL")
    if spec.group == "web" and spec.enabled_by_default:
        raise ValueError("a web source is never enabled by default")


# @spec SRC-1
@dataclass(frozen=True, config=ConfigDict(defer_build=True))
class SourceSpec:
    id: str
    title: str
    group: str
    capabilities: frozenset[Capability]
    id_schemes: frozenset[str]
    hosts: frozenset[str]
    auth: AuthSpec | None
    rate: RateSpec
    timeout_s: float = 5.0
    max_page_size: int = 50
    max_bytes: int = 5_000_000
    needs_contact: bool = False
    extras: frozenset[str] = frozenset()
    # A factory, so no ProbeSpec is validated (and no environment read) at import (PLAT-3).
    probe: ProbeSpec = field(default_factory=lambda: ProbeSpec(3600, "free", ""))
    enabled_by_default: bool = True
    shutdown_on: date | None = None
    docs_url: str = ""
    instance_of: str | None = None
    error_classifier: ErrorClassifier | None = None

    def __post_init__(self) -> None:
        _check_identity(self)
        _check_auth(self.auth, self.hosts)
        _check_rate(self.rate)
        _check_limits(self)

    def policy(self, *, daily_quota: int | None = None) -> SourcePolicy:
        """The HTTP policy; ``daily_quota`` (the source's ``budget_cap``) replaces the spec's."""
        quota = self.rate.daily_quota if daily_quota is None else daily_quota
        return SourcePolicy(
            source=self.id,
            hosts=self.hosts,
            auth=self.auth,
            rate=RateSpec(
                rps=self.rate.rps,
                burst=self.rate.burst,
                concurrency=self.rate.concurrency,
                daily_quota=quota,
            ),
            timeout_s=self.timeout_s,
            max_bytes=self.max_bytes,
            error_classifier=self.error_classifier,
        )

    def deprecated_days(self, today: date) -> int | None:
        if self.shutdown_on is None:
            return None
        return max(0, (self.shutdown_on - today).days)


class McpUpstreamPort(Protocol):
    async def call_tool(
        self, server: str, tool: str, arguments: Mapping[str, JsonValue], *, source: str
    ) -> JsonValue: ...


@std_dataclass(frozen=True)
class SourceContext:
    """What each adapter instance is given; it holds no secret."""

    http: "HttpPort"
    mcp: McpUpstreamPort | None
    settings: "SourceSettings"
    clock: Clock
    contact_email: str | None


class SourceAdapter(Protocol):
    """An adapter. ``search_authors`` and ``updates`` are called only for the capability.

    ``AuthorRecord`` and ``UpdateNotice`` are not in ``core/models.py`` yet (LLD-sources-v2
    2.1 and 5.13), so those two return a sequence of models until they are.
    """

    spec: SourceSpec

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None: ...
    async def search(self, req: SearchRequest) -> SearchPage: ...
    async def get(self, ident: Identifier) -> WorkRecord | None: ...
    async def fulltext_candidates(self, work: WorkRecord) -> list[FulltextCandidate]: ...
    async def citations(
        self,
        ident: Identifier,
        direction: Literal["citing", "cited"],
        cursor: str | None,
        limit: int,
    ) -> CitationPage: ...
    async def search_authors(
        self, query: str | None, orcid: str | None, limit: int
    ) -> Sequence[BaseModel]: ...
    async def updates(self, ident: Identifier) -> Sequence[BaseModel]: ...
    async def probe(self) -> ProbeResult: ...


_MALFORMED = (KeyError, TypeError, ValueError, ParseError, DefusedXmlException)


# @spec SRC-6
def translate_errors[**P, R](fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Turn a parse failure in an adapter method into ``upstream_error``.

    ``KeyError``, ``TypeError``, ``ValueError`` (which covers ``pydantic.ValidationError``
    and ``DefusedXmlException``) and the XML ``ParseError`` become
    ``HttpError(UPSTREAM_ERROR, detail="malformed_body")``; an ``HttpError`` passes through.
    """

    @functools.wraps(fn)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await fn(*args, **kwargs)
        except _MALFORMED:
            # from None: the upstream body must not ride along in the exception context.
            raise HttpError(ErrorCode.UPSTREAM_ERROR, detail="malformed_body") from None

    return wrapper
