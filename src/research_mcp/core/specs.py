"""Immutable source and HTTP policy types."""

from collections.abc import Callable
from typing import Literal
from urllib.parse import urlsplit

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from research_mcp.core.errors import ErrorCode


# @spec PLAT-6
@dataclass(frozen=True, config=ConfigDict(defer_build=True))
class AuthSpec:
    secrets: tuple[str, ...]
    required: bool
    placement: Literal["header", "query", "bearer"]
    param: str
    origins: tuple[str, ...]
    signup_url: str
    validation: Literal["probe", "github_rate_limit", "header_expiry", "none"] = "probe"

    def __post_init__(self) -> None:
        for origin in self.origins:
            url = urlsplit(origin)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or origin != f"{url.scheme}://{url.netloc}"
                or any(c.isspace() for c in origin)
            ):
                raise ValueError("Expected an HTTP origin without credentials or path")
            # .port parses lazily and raises ValueError on a non-numeric port (e.g. ":bad").
            _ = url.port


@dataclass(frozen=True, config=ConfigDict(defer_build=True))
class RateSpec:
    rps: float
    burst: int = 1
    concurrency: int = 2
    daily_quota: int | None = None


@dataclass(frozen=True, config=ConfigDict(defer_build=True))
class ProbeSpec:
    cadence_s: int
    cost: Literal["free", "metered"]
    description: str


ErrorClassifier = Callable[[int, bytes], tuple[ErrorCode, str | None] | None]


# @spec PLAT-6
@dataclass(frozen=True, config=ConfigDict(defer_build=True))
class SourcePolicy:
    source: str
    hosts: frozenset[str]
    auth: AuthSpec | None
    rate: RateSpec
    timeout_s: float
    max_bytes: int
    error_classifier: ErrorClassifier | None = None
