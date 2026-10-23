"""Per-source rate limits shared by every caller of the HTTP client (LLD-platform-v2 5.3)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from datetime import datetime
from typing import cast

import anyio
import anyio.lowlevel
import httpx

from research_mcp.core.models import CallRecord
from research_mcp.core.specs import RateSpec, SourcePolicy
from research_mcp.platform.http import HttpClient
from research_mcp.platform.ratelimit import ConcurrencyGate, RateRegistry, TokenBucket
from research_mcp.platform.secrets import Secret
from research_mcp.testing.clock import FakeClock, FakeSleeper

ARXIV = SourcePolicy(
    source="arxiv",
    hosts=frozenset({"export.arxiv.org"}),
    auth=None,
    rate=RateSpec(rps=1 / 3, burst=1, concurrency=1),
    timeout_s=10.0,
    max_bytes=1_000_000,
)


class _Policies:
    def policy(self, source: str) -> SourcePolicy:
        assert source == "arxiv"
        return ARXIV


class _NoCredentials:
    def secret_for(self, source: str) -> Secret | None:
        return None


class _Wire(httpx.AsyncByteStream):
    def __init__(self, body: bytes) -> None:
        self.body = body

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.body


class _WireTransport(httpx.MockTransport):
    """``httpx.MockTransport`` whose bodies arrive unread, as a network transport's do."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await super().handle_async_request(request)
        raw = b"".join(cast(Iterable[bytes], response.stream))
        return httpx.Response(response.status_code, headers=response.headers, stream=_Wire(raw))


class _Sink:
    def __init__(self) -> None:
        self.records: list[CallRecord] = []

    def record(self, call: CallRecord) -> None:
        self.records.append(call)


async def test_shared_bucket_spaces_arxiv_calls() -> None:
    """@spec PLAT-37: two concurrent arXiv calls through one client are 3 s apart (fake clock)."""
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    sent_at: list[datetime] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_at.append(clock.now())
        return httpx.Response(200, text="<feed/>", headers={"Content-Type": "application/xml"})

    client = HttpClient(
        _Policies(),
        _NoCredentials(),
        _Sink(),
        clock,
        sleeper,
        "owner@uni.edu",
        transport=_WireTransport(handler),
    )
    url = "https://export.arxiv.org/api/query"
    async with client, anyio.create_task_group() as group:
        group.start_soon(lambda: client.get_text(url, source="arxiv"))
        group.start_soon(lambda: client.get_text(url, source="arxiv"))

    assert len(sent_at) == 2
    assert (sent_at[1] - sent_at[0]).total_seconds() == 3.0
    assert sleeper.sleeps == [3.0]


async def test_registry_shares_one_limiter_per_source() -> None:
    """@spec PLAT-37: the registry hands every caller the same bucket and gate for a source."""
    clock = FakeClock()
    registry = RateRegistry(clock, FakeSleeper(clock))
    spec = RateSpec(rps=1 / 3, burst=1, concurrency=1)

    assert registry.bucket("arxiv", spec) is registry.bucket("arxiv", spec)
    assert registry.gate("arxiv", spec) is registry.gate("arxiv", spec)
    assert registry.bucket("arxiv", spec) is not registry.bucket("crossref", spec)


async def test_token_bucket_burst_then_refill() -> None:
    """@spec PLAT-37: a bucket spends its burst at once, then waits for each refilled token."""
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    bucket = TokenBucket(rate=2.0, burst=3, clock=clock, sleeper=sleeper)

    for _ in range(3):
        await bucket.acquire()
    assert sleeper.sleeps == []

    await bucket.acquire()
    await bucket.acquire()
    assert sleeper.sleeps == [0.5, 0.5]

    clock.advance(10)  # idle time refills up to the burst, never beyond it
    for _ in range(3):
        await bucket.acquire()
    assert sleeper.sleeps == [0.5, 0.5]
    await bucket.acquire()
    assert sleeper.sleeps == [0.5, 0.5, 0.5]


async def test_concurrency_gate_limits_calls_in_flight() -> None:
    """@spec PLAT-37: the gate lets at most n callers in at once."""
    gate = ConcurrencyGate(2)
    in_flight = 0
    peak = 0

    async def call() -> None:
        nonlocal in_flight, peak
        async with gate:
            in_flight += 1
            peak = max(peak, in_flight)
            await anyio.lowlevel.checkpoint()
            in_flight -= 1

    async with anyio.create_task_group() as group:
        for _ in range(6):
            group.start_soon(call)

    assert peak == 2
