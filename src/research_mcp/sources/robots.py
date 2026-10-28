"""``robots.txt`` rules for docs sites, kept in memory (LLD-sources-v3 5.11; SRC-FR-15).

``robots.txt`` is fetched through the source's ``HttpPort`` under the docs-site instance id,
so host policy, rate limits and call records apply to it like any other call. Nothing is
written to disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.models import Clock

if TYPE_CHECKING:
    from research_mcp.platform.http import HttpPort

# Failures that mean the rules are unknown, not absent: everything is disallowed.
_UNREACHABLE = frozenset({ErrorCode.TOO_LARGE, ErrorCode.UPSTREAM_TIMEOUT})


@dataclass(frozen=True)
class _Rules:
    fetched_at: datetime
    parser: RobotFileParser | None  # None: no rules apply, so ``everything`` decides
    everything: bool

    def allows(self, user_agent: str, url: str) -> bool:
        if self.parser is None:
            return self.everything
        return self.parser.can_fetch(user_agent, url)


def _absent(error: HttpError) -> bool:
    """A 4xx for ``robots.txt``: the site has no rules, so every path is allowed."""
    return error.code not in _UNREACHABLE and error.status is not None and 400 <= error.status < 500


class RobotsCache:
    """One parsed ``robots.txt`` per host, refreshed after ``ttl_s`` by the injected clock."""

    def __init__(
        self,
        http: HttpPort,
        clock: Clock,
        source: str,
        user_agent: str = "research-mcp",
        ttl_s: int = 86400,
    ) -> None:
        self._http = http
        self._clock = clock
        self._source = source
        self._user_agent = user_agent
        self._ttl = timedelta(seconds=ttl_s)
        self._rules: dict[str, _Rules] = {}

    # @spec SRC-23
    async def allowed(self, url: str) -> bool:
        """Whether ``robots.txt`` lets this user agent fetch ``url``.

        A 4xx for ``robots.txt`` allows everything. A 5xx, a timeout or a body that is too
        large disallows everything until the next refresh; the call that met the failure
        raises it, so the caller sees why, and later calls get False.
        """
        host = urlsplit(url).hostname
        if not host:
            return False
        now = self._clock.now()
        rules = self._rules.get(host)
        if rules is None or now - rules.fetched_at >= self._ttl:
            rules = await self._fetch(host, now)
        return rules.allows(self._user_agent, url)

    async def _fetch(self, host: str, now: datetime) -> _Rules:
        try:
            response = await self._http.get_text(f"https://{host}/robots.txt", source=self._source)
        except HttpError as error:
            rules = _Rules(now, None, everything=_absent(error))
            self._rules[host] = rules
            if rules.everything:
                return rules
            raise
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        rules = _Rules(now, parser, everything=False)
        self._rules[host] = rules
        return rules
