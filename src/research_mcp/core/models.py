"""Shared source, federation and transport data contracts."""

from datetime import date, datetime
from enum import StrEnum
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from research_mcp.core.envelope import SourceStatus
from research_mcp.core.ids import Identifier as Identifier

type JsonValue = None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]


class Clock(Protocol):
    def now(self) -> datetime: ...


class Sleeper(Protocol):
    async def sleep(self, seconds: float) -> None: ...


class AuthUse(StrEnum):
    SPEC = "spec"
    NONE = "none"


class Author(BaseModel):
    model_config = ConfigDict(defer_build=True)

    name: str
    family: str | None = None
    orcid: str | None = None


class OaLocation(BaseModel):
    model_config = ConfigDict(defer_build=True)

    url: str
    source: str
    kind: Literal["pdf", "html", "landing"]
    license: str | None = None
    version: str | None = None


class Provenance(BaseModel):
    model_config = ConfigDict(defer_build=True)

    source: str
    upstream_id: str
    adapter_version: str
    retrieved_at: datetime


class WorkRecord(BaseModel):
    model_config = ConfigDict(defer_build=True)

    ids: list[Identifier]
    title: str
    authors: list[Author] = []
    year: int | None = None
    published_at: date | None = None
    venue: str | None = None
    work_type: str = "article"
    abstract: str | None = None
    oa_locations: list[OaLocation] = []
    is_retracted: bool | None = None
    extra: dict[str, JsonValue] = {}
    provenance: Provenance


class SearchFilters(BaseModel):
    model_config = ConfigDict(defer_build=True)

    year_from: int | None = Field(default=None, ge=1800, le=2100)
    year_to: int | None = Field(default=None, ge=1800, le=2100)
    work_type: str | None = None
    oa_only: bool = False
    provider: str | None = None
    repository: str | None = None

    @model_validator(mode="after")
    def ordered_years(self) -> Self:
        if (
            self.year_from is not None
            and self.year_to is not None
            and self.year_from > self.year_to
        ):
            raise ValueError("year_from must not exceed year_to")
        return self


class SearchRequest(BaseModel):
    model_config = ConfigDict(defer_build=True)

    query: str
    filters: SearchFilters = Field(default_factory=SearchFilters)
    limit: int = 10
    cursor: str | None = None


class SearchPage(BaseModel):
    model_config = ConfigDict(defer_build=True)

    records: list[WorkRecord]
    total: int | None = None
    next_cursor: str | None = None


class FulltextCandidate(BaseModel):
    model_config = ConfigDict(defer_build=True)

    location: OaLocation
    priority: int


class CitationPage(BaseModel):
    model_config = ConfigDict(defer_build=True)

    ids: list[Identifier]
    records: list[WorkRecord] = []
    next_cursor: str | None = None


class ProbeResult(BaseModel):
    model_config = ConfigDict(defer_build=True)

    ok: bool
    latency_ms: int
    shape_ok: bool
    detail_code: str | None = None
    quota_remaining: str | None = None
    credential_expires_at: datetime | None = None


class Conflict(BaseModel):
    model_config = ConfigDict(defer_build=True)

    field: str
    values: dict[str, JsonValue]  # source -> value


class Work(BaseModel):
    model_config = ConfigDict(defer_build=True)

    work_id: str | None = None
    ids: list[Identifier]
    title: str
    authors: list[Author]
    year: int | None
    venue: str | None
    work_type: str
    abstract: str | None
    oa_locations: list[OaLocation]
    found_in: list[str]
    fuzzy: bool = False
    conflicts: list[Conflict] = []
    integrity_status: str = "unknown"
    cache_state: str = "none"


class FederatedResult(BaseModel):
    model_config = ConfigDict(defer_build=True)

    works: list[Work]
    statuses: list[SourceStatus]
    next_cursor: str | None


class TextResponse(BaseModel):
    model_config = ConfigDict(defer_build=True)

    url: str
    status: int
    content_type: str
    text: str


class DownloadedFile(BaseModel):
    model_config = ConfigDict(defer_build=True)

    sha256: str
    size: int
    media_type: str
    storage_path: str
    final_url: str
    http_status: int
    etag: str | None
    last_modified: str | None


class CallRecord(BaseModel):
    model_config = ConfigDict(defer_build=True)

    ts: datetime
    source: str
    op: str
    status: int | None
    error_code: str | None
    latency_ms: int
    bytes: int
    rl_remaining: str | None
    rl_reset: str | None
    cred_expires_at: str | None
    correlation_id: str | None
    attempt: int
