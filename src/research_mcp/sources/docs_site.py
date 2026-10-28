"""The docs-site adapter: one source per configured documentation site (LLD-sources-v3 3.3,
5.11; PRD-sources-v5 SRC-23).

In M1 a docs site serves ``get`` only; local search over crawled pages and the crawl job
land in M2 (SPEC-v5 14). Every ``get`` passes the instance's ``DocsSiteAllowlist`` and its
``robots.txt`` before the page is fetched, and the final URL of the answer is checked again.
Instances come from settings (``instance_of = "docs_site"``); the kind itself is listed
``unconfigured`` only when no instance is configured.
"""

from __future__ import annotations

import dataclasses
import functools
from collections.abc import Sequence
from html.parser import HTMLParser
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier, normalize_url
from research_mcp.core.models import (
    CitationPage,
    FulltextCandidate,
    ProbeResult,
    Provenance,
    SearchPage,
    SearchRequest,
    WorkRecord,
)
from research_mcp.core.specs import ProbeSpec, RateSpec
from research_mcp.sources.base import (
    HOST_PATTERN,
    Capability,
    SourceContext,
    SourceSpec,
    translate_errors,
)
from research_mcp.sources.docs_allowlist import DocsSiteAllowlist
from research_mcp.sources.robots import RobotsCache

ADAPTER_VERSION = "1"

# The kind's own host is never called: the kind is listed only when no instance exists,
# and an unconfigured source is never selected. ``.invalid`` cannot resolve (RFC 2606).
_KIND_HOST = "docs-site.invalid"


# @spec SRC-20, SRC-23
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import (PLAT-3), as in sources/arxiv.py.
    return SourceSpec(
        id="docs_site",
        title="Documentation sites",
        group="vendor_docs",
        capabilities=frozenset({Capability.GET}),
        id_schemes=frozenset({"url"}),
        hosts=frozenset({_KIND_HOST}),
        auth=None,
        # One page a second, one at a time: these are other people's web servers.
        rate=RateSpec(rps=1.0, burst=1, concurrency=1),
        timeout_s=10.0,
        probe=ProbeSpec(86_400, "free", "GET the first allowed page"),
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _host(value: str) -> str:
    host = value.strip().lower().removesuffix(".")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        raise ValueError("allowed_hosts holds bare host names") from None
    if not HOST_PATTERN.fullmatch(host):
        raise ValueError("allowed_hosts holds bare host names")
    return host


class DocsSiteInstance(BaseModel):
    """``sources.<name>`` with ``instance_of = "docs_site"`` (LLD-sources-v3 3.3)."""

    model_config = ConfigDict(strict=True, extra="forbid", defer_build=True)

    title: str = Field(min_length=1, max_length=120)
    allowed_hosts: list[str] = Field(min_length=1)
    path_prefixes: list[str] = Field(min_length=1)
    sitemap: str | None = None
    seed_urls: list[str] = Field(default_factory=list)
    follow_links: bool = False

    @model_validator(mode="after")
    def _check(self) -> DocsSiteInstance:
        self.allowed_hosts = [_host(host) for host in self.allowed_hosts]
        if not all(prefix.startswith("/") for prefix in self.path_prefixes):
            raise ValueError("path_prefixes start with /")
        if (self.sitemap is None) == (not self.seed_urls):
            raise ValueError("set either sitemap or seed_urls")
        seeds = [self.sitemap] if self.sitemap is not None else self.seed_urls
        for seed in seeds:
            url = urlsplit(seed)
            if url.scheme != "https" or "@" in url.netloc or url.hostname not in self.allowed_hosts:
                raise ValueError("seeds are https URLs on an allowed host")
        return self

    def allowlist(self) -> DocsSiteAllowlist:
        return DocsSiteAllowlist(frozenset(self.allowed_hosts), tuple(self.path_prefixes))


INSTANCE_MODEL = DocsSiteInstance


def instance_spec(base: SourceSpec, instance_id: str, cfg: BaseModel) -> SourceSpec:
    """The instance's spec: its id, title and hosts (``allowed_hosts``) on the kind's."""
    if not isinstance(cfg, DocsSiteInstance):
        # ValueError, which the registry turns into an `unconfigured` instance.
        raise ValueError("a docs_site instance needs DocsSiteInstance settings")
    return dataclasses.replace(
        base,
        id=instance_id,
        title=cfg.title,
        hosts=frozenset(cfg.allowed_hosts),
        instance_of=base.id,
    )


def _instance(ctx: SourceContext) -> DocsSiteInstance | None:
    fields: dict[str, Any] = dict(ctx.settings.model_extra or {})
    fields.pop("instance_of", None)
    try:
        return DocsSiteInstance.model_validate(fields)
    except ValidationError:
        return None


class _PageParser(HTMLParser):
    """The ``<title>`` (or first ``<h1>``) and the meta description of a page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: list[str] = []
        self.heading: list[str] = []
        self.description: str | None = None
        self._in: str | None = None
        self._headings = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title" or (tag == "h1" and self._headings == 0):
            self._in = tag
        if tag == "h1":
            self._headings += 1
        if tag == "meta" and self.description is None:
            values = dict(attrs)
            if (values.get("name") or "").lower() == "description":
                self.description = values.get("content")

    def handle_endtag(self, tag: str) -> None:
        if tag == self._in:
            self._in = None

    def handle_data(self, data: str) -> None:
        if self._in == "title":
            self.title.append(data)
        elif self._in == "h1":
            self.heading.append(data)


def _clean(parts: list[str]) -> str:
    return " ".join("".join(parts).split())


def _record(url: str, text: str, source: str, ctx: SourceContext) -> WorkRecord:
    parser = _PageParser()
    parser.feed(text)
    parser.close()
    title = _clean(parser.title) or _clean(parser.heading)
    if not title:
        raise ValueError("the page has no title")
    abstract = " ".join((parser.description or "").split()) or None
    return WorkRecord(
        ids=[Identifier("url", normalize_url(url))],
        title=title,
        work_type="webpage",
        abstract=abstract,
        provenance=Provenance(
            source=source,
            upstream_id=url,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=ctx.clock.now(),
        ),
    )


class DocsSiteAdapter:
    """Fetches allowed pages of one docs site; it sleeps, retries and reads secrets never."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx
        self.instance = _instance(ctx)
        # Without valid instance settings the allowlist is empty and refuses every URL.
        self.allowlist = (
            self.instance.allowlist()
            if self.instance is not None
            else DocsSiteAllowlist(frozenset(), ())
        )
        self.robots = RobotsCache(ctx.http, ctx.clock, spec.id)

    async def _page(self, url: str) -> WorkRecord:
        target = self.allowlist.canonical(url)
        if target is None:
            raise HttpError(ErrorCode.BLOCKED_BY_POLICY, detail="allowlist")
        if not await self.robots.allowed(target):
            raise HttpError(ErrorCode.BLOCKED_BY_POLICY, detail="robots")
        response = await self.ctx.http.get_text(target, source=self.spec.id)
        final = self.allowlist.canonical(response.url)
        if final is None:
            # A redirect left the allowlist: the body is dropped unread.
            raise HttpError(ErrorCode.BLOCKED_BY_POLICY, detail="allowlist")
        return _record(final, response.text, self.spec.id, self.ctx)

    # @spec SRC-23
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        if ident.scheme != "url":
            return None
        return await self._page(ident.value)

    async def search(self, req: SearchRequest) -> SearchPage:
        # Not declared in M1 (local search lands in M2), so the registry never calls it.
        return SearchPage(records=[])

    async def fulltext_candidates(self, work: WorkRecord) -> list[FulltextCandidate]:
        return []

    async def citations(
        self,
        ident: Identifier,
        direction: Literal["citing", "cited"],
        cursor: str | None,
        limit: int,
    ) -> CitationPage:
        return CitationPage(ids=[])

    async def search_authors(
        self, query: str | None, orcid: str | None, limit: int
    ) -> Sequence[BaseModel]:
        return []

    async def updates(self, ident: Identifier) -> Sequence[BaseModel]:
        return []

    async def probe(self) -> ProbeResult:
        """Fetch the first allowed page: the first host under the first prefix."""
        if self.instance is None:
            return ProbeResult(
                ok=False,
                latency_ms=0,
                shape_ok=False,
                detail_code=ErrorCode.BLOCKED_BY_POLICY.value,
            )
        target = f"https://{self.instance.allowed_hosts[0]}{self.instance.path_prefixes[0]}"
        started = self.ctx.clock.now()
        try:
            await self._page(target)
            shape_ok = True
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        except (ValueError, TypeError):
            shape_ok = False
        elapsed = self.ctx.clock.now() - started
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=shape_ok
        )


ADAPTER = DocsSiteAdapter
