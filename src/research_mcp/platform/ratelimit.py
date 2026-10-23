"""Per-source rate limits shared by every caller in the daemon (LLD-platform-v2 5.3).

Each source gets one ``TokenBucket(rate, burst)`` and one ``ConcurrencyGate(n)`` from its
``RateSpec``. ``RateRegistry`` keeps them, so two clients calling the same source share
both. Time comes from the injected ``Clock`` and every wait goes through the injected
``Sleeper``, so tests run on a fake clock.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import TracebackType

import anyio

from research_mcp.core.models import Clock, Sleeper
from research_mcp.core.specs import RateSpec

# Float arithmetic on refills may land a hair under a whole token.
_EPSILON = 1e-9


class TokenBucket:
    """``rate`` tokens per second, holding at most ``burst``; it starts full."""

    def __init__(self, rate: float, burst: int, clock: Clock, sleeper: Sleeper) -> None:
        if rate <= 0 or burst < 1:
            raise ValueError("a token bucket needs a positive rate and a burst of at least 1")
        self._rate = rate
        self._burst = float(burst)
        self._tokens = float(burst)
        self._clock = clock
        self._sleeper = sleeper
        self._last = clock.now()
        # Waiters queue in order, so concurrent callers are spaced one token apart.
        self._lock = anyio.Lock()

    def _refill(self) -> None:
        now = self._clock.now()
        # A wall clock that steps back adds nothing rather than taking tokens away.
        elapsed = max(0.0, (now - self._last).total_seconds())
        self._last = now
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)

    # @spec PLAT-37
    async def acquire(self) -> None:
        async with self._lock:
            self._refill()
            while self._tokens < 1 - _EPSILON:
                await self._sleeper.sleep((1 - self._tokens) / self._rate)
                self._refill()
            self._tokens = max(0.0, self._tokens - 1)


class ConcurrencyGate:
    """At most ``n`` callers inside at once."""

    def __init__(self, n: int) -> None:
        if n < 1:
            raise ValueError("a concurrency gate needs n of at least 1")
        self._semaphore = anyio.Semaphore(n)

    async def __aenter__(self) -> None:
        await self._semaphore.acquire()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._semaphore.release()


class RateRegistry:
    """One bucket and one gate per source for the whole daemon (PLAT-37)."""

    def __init__(self, clock: Clock, sleeper: Sleeper) -> None:
        self._clock = clock
        self._sleeper = sleeper
        self._buckets: dict[str, TokenBucket] = {}
        self._gates: dict[str, ConcurrencyGate] = {}

    def bucket(self, source: str, rate: RateSpec) -> TokenBucket:
        bucket = self._buckets.get(source)
        if bucket is None:
            bucket = TokenBucket(rate.rps, rate.burst, self._clock, self._sleeper)
            self._buckets[source] = bucket
        return bucket

    def gate(self, source: str, rate: RateSpec) -> ConcurrencyGate:
        gate = self._gates.get(source)
        if gate is None:
            gate = ConcurrencyGate(rate.concurrency)
            self._gates[source] = gate
        return gate

    @asynccontextmanager
    async def slot(self, source: str, rate: RateSpec) -> AsyncIterator[None]:
        """Enter the source's gate, then take one token: one call may start."""
        async with self.gate(source, rate):
            await self.bucket(source, rate).acquire()
            yield
