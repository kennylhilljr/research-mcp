"""The GitHub adapter: JSON over https, a required token (LLD-sources-v3 5.1; PRD-sources-v5
SRC-20, catalog row 35). Sends the token as an ``Authorization: Bearer`` header, maps a
repository to a normalized ``url`` identifier (its ``full_name`` has no registered
identifier scheme of its own) and its owner login to an ``Author``.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.ids import Identifier, normalize_url
from research_mcp.core.models import (
    Author,
    CitationPage,
    FulltextCandidate,
    ProbeResult,
    Provenance,
    SearchPage,
    SearchRequest,
    WorkRecord,
)
from research_mcp.core.specs import AuthSpec, RateSpec
from research_mcp.sources.base import Capability, SourceContext, SourceSpec, translate_errors

ADAPTER_VERSION = "1"

_HOST = "api.github.com"
_SEARCH_URL = f"https://{_HOST}/search/repositories"
_REPOS_URL = f"https://{_HOST}/repos"
_PROBE_REPO = "octocat/hello-world"


# @spec SRC-20
@functools.cache
def _spec() -> SourceSpec:
    # Built on first use, not at import: validating a SourceSpec at import time would read
    # the environment (pydantic's plugin switch), and importing research_mcp does no work
    # (PLAT-3; the same reason SourceSpec.probe uses a default_factory in sources/base.py).
    return SourceSpec(
        id="github",
        title="GitHub",
        group="code",
        capabilities=frozenset({Capability.SEARCH, Capability.GET}),
        id_schemes=frozenset({"url"}),
        hosts=frozenset({_HOST}),
        auth=AuthSpec(
            secrets=("GITHUB_TOKEN",),
            required=True,
            placement="bearer",
            param="",
            origins=(f"https://{_HOST}",),
            signup_url="https://github.com/settings/tokens",
            validation="github_rate_limit",
        ),
        # GitHub's search endpoint publishes 30 requests/minute for an authenticated
        # caller; the repos endpoint is far more generous, so the search rate is
        # the binding one [assumption].
        rate=RateSpec(rps=0.5, burst=5, concurrency=2),
        max_page_size=100,
        docs_url="https://docs.github.com/en/rest",
    )


def __getattr__(name: str) -> SourceSpec:
    if name == "SPEC":
        return _spec()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _repo_identifier(full_name: str) -> Identifier:
    return Identifier("url", normalize_url(f"https://github.com/{full_name}"))


def _full_name_from_ident(ident: Identifier) -> str:
    """``owner/repo`` from a ``url`` identifier (``github`` has no identifier scheme of its
    own, 5.1); a bare value is used as is, for a caller that already holds ``owner/repo``."""
    value = ident.value
    if value.startswith("http://") or value.startswith("https://"):
        return urlsplit(value).path.lstrip("/")
    return value


def _author(entry: Any) -> Author:
    owner = entry.get("owner") or {}
    return Author(name=owner.get("login") or "")


def _work_record(data: Any, source_id: str, retrieved_at: datetime) -> WorkRecord:
    full_name = data["full_name"]
    title = full_name
    created_at = data.get("created_at")
    published_at = date.fromisoformat(created_at[:10]) if created_at else None
    return WorkRecord(
        ids=[_repo_identifier(full_name)],
        title=title,
        authors=[_author(data)],
        year=published_at.year if published_at else None,
        published_at=published_at,
        work_type="repository",
        abstract=data.get("description"),
        extra={"stars": data.get("stargazers_count"), "language": data.get("language")},
        provenance=Provenance(
            source=source_id,
            upstream_id=full_name,
            adapter_version=ADAPTER_VERSION,
            retrieved_at=retrieved_at,
        ),
    )


class GithubAdapter:
    """Translates the GitHub REST API; it sleeps, retries and reads secrets never."""

    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
        self.spec = spec
        self.ctx = ctx

    async def _fetch_repo(self, full_name: str) -> Any:
        """``repos/<full_name>``; ``None`` for a 404."""
        try:
            data: Any = await self.ctx.http.get_json(
                f"{_REPOS_URL}/{full_name}", source=self.spec.id
            )
        except HttpError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise
        return data

    # @spec SRC-20
    @translate_errors
    async def search(self, req: SearchRequest) -> SearchPage:
        limit = min(req.limit, self.spec.max_page_size)
        page = int(req.cursor) if req.cursor else 1
        params = {"q": req.query, "per_page": str(limit), "page": str(page)}
        data: Any = await self.ctx.http.get_json(_SEARCH_URL, source=self.spec.id, params=params)
        total = data["total_count"]
        records = [_work_record(item, self.spec.id, self.ctx.clock.now()) for item in data["items"]]
        next_cursor = str(page + 1) if page * limit < total else None
        return SearchPage(records=records, total=total, next_cursor=next_cursor)

    # @spec SRC-20
    @translate_errors
    async def get(self, ident: Identifier) -> WorkRecord | None:
        data = await self._fetch_repo(_full_name_from_ident(ident))
        if data is None:
            return None
        return _work_record(data, self.spec.id, self.ctx.clock.now())

    async def fulltext_candidates(self, work: WorkRecord) -> list[FulltextCandidate]:
        return [
            FulltextCandidate(location=location, priority=index)
            for index, location in enumerate(work.oa_locations)
        ]

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
        started = self.ctx.clock.now()
        try:
            data = await self._fetch_repo(_PROBE_REPO)
        except HttpError as exc:
            return ProbeResult(ok=False, latency_ms=0, shape_ok=False, detail_code=exc.code.value)
        elapsed = self.ctx.clock.now() - started
        try:
            shape_ok = bool((data or {}).get("full_name")) and bool((data or {}).get("id"))
        except (KeyError, TypeError):
            shape_ok = False
        return ProbeResult(
            ok=True, latency_ms=int(elapsed.total_seconds() * 1000), shape_ok=bool(shape_ok)
        )


ADAPTER = GithubAdapter
