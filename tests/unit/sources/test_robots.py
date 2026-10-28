"""Tests for ``RobotsCache`` (LLD-sources-v3 5.11; PRD-sources-v5 SRC-23).

A fake ``HttpPort`` answers ``get_text`` from a table, so the tests see each fetch of
``robots.txt``: its URL, the source it is charged to, and how often it happens.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.models import TextResponse
from research_mcp.sources.robots import RobotsCache
from research_mcp.testing.clock import FakeClock

ROBOTS = """\
User-agent: *
Disallow: /docs/private/

User-agent: research-mcp
Disallow: /docs/internal/
"""


class FakeHttp:
    """``get_text`` only; every answer is a body or an ``HttpError`` per URL."""

    def __init__(self, answers: dict[str, str | HttpError]) -> None:
        self.answers = answers
        self.calls: list[tuple[str, str]] = []

    async def get_text(self, url: str, *, source: str, **kwargs: Any) -> TextResponse:
        self.calls.append((url, source))
        answer = self.answers[url]
        if isinstance(answer, HttpError):
            raise answer
        return TextResponse(url=url, status=200, content_type="text/plain", text=answer)


def _cache(http: FakeHttp, clock: FakeClock | None = None) -> RobotsCache:
    clock = clock or FakeClock(datetime(2026, 10, 28, 12, tzinfo=UTC))
    return RobotsCache(http, clock, "docs_site_keycloak")  # type: ignore[arg-type]


async def test_disallowed_paths_are_refused_and_others_allowed() -> None:
    """@spec SRC-23: ``robots.txt`` rules decide, including the rules for our user agent."""
    http = FakeHttp({"https://www.keycloak.org/robots.txt": ROBOTS})
    robots = _cache(http)
    assert await robots.allowed("https://www.keycloak.org/docs/latest/") is True
    assert await robots.allowed("https://www.keycloak.org/docs/internal/a") is False
    assert http.calls == [("https://www.keycloak.org/robots.txt", "docs_site_keycloak")]


async def test_robots_is_fetched_once_per_host_until_the_ttl_passes() -> None:
    """@spec SRC-23: The rules are kept in memory for ``ttl_s`` by the injected clock."""
    http = FakeHttp(
        {
            "https://www.keycloak.org/robots.txt": ROBOTS,
            "https://www.ory.sh/robots.txt": "User-agent: *\nDisallow: /\n",
        }
    )
    clock = FakeClock(datetime(2026, 10, 28, 12, tzinfo=UTC))
    robots = _cache(http, clock)
    await robots.allowed("https://www.keycloak.org/docs/a")
    await robots.allowed("https://www.keycloak.org/docs/b")
    assert await robots.allowed("https://www.ory.sh/docs/") is False
    assert len(http.calls) == 2
    clock.advance(86_399)
    await robots.allowed("https://www.keycloak.org/docs/c")
    assert len(http.calls) == 2
    http.answers["https://www.keycloak.org/robots.txt"] = "User-agent: *\nDisallow: /docs/\n"
    clock.advance(1)
    assert await robots.allowed("https://www.keycloak.org/docs/c") is False
    assert len(http.calls) == 3


@pytest.mark.parametrize("status", [404, 403, 410])
async def test_a_4xx_robots_means_everything_is_allowed(status: int) -> None:
    """@spec SRC-23: A missing ``robots.txt`` (404 or another 4xx) allows every path."""
    error = HttpError(ErrorCode.NOT_FOUND if status == 404 else ErrorCode.AUTH_FAILED, status)
    http = FakeHttp({"https://www.keycloak.org/robots.txt": error})
    robots = _cache(http)
    assert await robots.allowed("https://www.keycloak.org/docs/a") is True
    assert await robots.allowed("https://www.keycloak.org/anything") is True
    assert len(http.calls) == 1


@pytest.mark.parametrize(
    "error",
    [
        HttpError(ErrorCode.UPSTREAM_ERROR, status=503),
        HttpError(ErrorCode.UPSTREAM_TIMEOUT),
        HttpError(ErrorCode.TOO_LARGE, status=200),
    ],
    ids=["5xx", "timeout", "too_large"],
)
async def test_an_unreachable_robots_disallows_everything_until_the_next_refresh(
    error: HttpError,
) -> None:
    """@spec SRC-23: A 5xx, timeout or oversize ``robots.txt`` disallows every path.

    The call that met the failure reports it; later calls within the TTL get False without
    another fetch, and the next refresh after the TTL tries again.
    """
    http = FakeHttp({"https://www.keycloak.org/robots.txt": error})
    clock = FakeClock(datetime(2026, 10, 28, 12, tzinfo=UTC))
    robots = _cache(http, clock)
    with pytest.raises(HttpError) as caught:
        await robots.allowed("https://www.keycloak.org/docs/a")
    assert caught.value is error
    assert await robots.allowed("https://www.keycloak.org/docs/a") is False
    assert len(http.calls) == 1
    http.answers["https://www.keycloak.org/robots.txt"] = ""
    clock.advance(86_400)
    assert await robots.allowed("https://www.keycloak.org/docs/a") is True
    assert len(http.calls) == 2


async def test_a_url_without_a_host_is_not_allowed() -> None:
    """@spec SRC-23: Nothing without a host is allowed, and nothing is fetched for it."""
    http = FakeHttp({})
    robots = _cache(http)
    assert await robots.allowed("/docs/a") is False
    assert http.calls == []
