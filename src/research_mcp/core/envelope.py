"""Typed tool envelopes and explicit untrusted content."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from research_mcp.core.errors import ErrorCode


class SourceStatus(BaseModel):
    model_config = ConfigDict(defer_build=True)

    source: str
    state: Literal[
        "ok",
        "empty",
        "timeout",
        "rate_limited",
        "error",
        "unconfigured",
        "disabled",
        "skipped_unhealthy",
        "skipped_budget",
    ]
    count: int = 0
    latency_ms: int | None = None
    retry_after_ms: int | None = None
    error_code: ErrorCode | None = None


# @spec PLAT-33
class Untrusted(BaseModel):
    model_config = ConfigDict(defer_build=True)

    untrusted: Literal[True] = True
    source: str
    content: str


# @spec PLAT-30
class ToolResult[T](BaseModel):
    model_config = ConfigDict(defer_build=True)

    data: T
    source_status: list[SourceStatus] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_cursor: str | None = None
    truncated: bool = False
