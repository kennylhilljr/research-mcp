"""The shared HTTP client: retries, host policy, byte cap, user agent and telemetry.

LLD-platform-v2 4.4, 5.3 and 6.1. Every upstream is an ``httpx.MockTransport`` and every
wait goes through ``FakeSleeper``, so nothing touches the network or sleeps for real.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import timedelta
from email.utils import format_datetime

import httpx
import pytest

from research_mcp.core.context import correlation_id
from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.models import CallRecord
from research_mcp.core.specs import AuthSpec, RateSpec, SourcePolicy
from research_mcp.platform.http import HttpClient, build_user_agent
from research_mcp.platform.secrets import Secret, SecretRef
from research_mcp.testing.clock import FakeClock, FakeSleeper

Handler = Callable[[httpx.Request], httpx.Response]

CROSSREF = SourcePolicy(
    source="crossref",
    hosts=frozenset({"api.crossref.org"}),
    auth=None,
    rate=RateSpec(rps=1000.0, burst=1000, concurrency=8),
    timeout_s=10.0,
    max_bytes=1_000_000,
)
URL = "https://api.crossref.org/works"


class Policies:
    def __init__(self, *policies: SourcePolicy) -> None:
        self._policies = {policy.source: policy for policy in policies}

    def policy(self, source: str) -> SourcePolicy:
        return self._policies[source]


class Credentials:
    def __init__(self, secrets: dict[str, Secret] | None = None) -> None:
        self._secrets = secrets or {}

    def secret_for(self, source: str) -> Secret | None:
        return self._secrets.get(source)


class Sink:
    def __init__(self) -> None:
        self.records: list[CallRecord] = []

    def record(self, call: CallRecord) -> None:
        self.records.append(call)


class Harness:
    def __init__(
        self,
        handler: Handler,
        *policies: SourcePolicy,
        contact: str | None = "owner@uni.edu",
        credentials: Credentials | None = None,
    ) -> None:
        self.clock = FakeClock()
        self.sleeper = FakeSleeper(self.clock)
        self.sink = Sink()
        self.requests: list[httpx.Request] = []

        def recording(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return handler(request)

        self.client = HttpClient(
            Policies(*(policies or (CROSSREF,))),
            credentials or Credentials(),
            self.sink,
            self.clock,
            self.sleeper,
            contact,
            transport=httpx.MockTransport(recording),
        )


def replies(*responses: httpx.Response | Exception) -> Handler:
    """A handler that answers each request with the next response, or raises it."""
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return handler


def ok(body: str = '{"ok": true}', **headers: str) -> httpx.Response:
    return httpx.Response(200, text=body, headers={"Content-Type": "application/json", **headers})


async def fails(harness: Harness, url: str = URL, source: str = "crossref") -> HttpError:
    with pytest.raises(HttpError) as caught:
        await harness.client.get_json(url, source=source)
    return caught.value


# PLAT-35


async def test_retry_after_and_rate_limited() -> None:
    """@spec PLAT-35: 429 waits Retry-After; over 60 s fails at once; 3 429s are rate_limited."""
    harness = Harness(replies(httpx.Response(429, headers={"Retry-After": "2"}), ok()))
    assert await harness.client.get_json(URL, source="crossref") == {"ok": True}
    assert harness.sleeper.sleeps == [2.0]

    harness = Harness(replies(httpx.Response(429, headers={"Retry-After": "120"})))
    error = await fails(harness)
    assert error.code is ErrorCode.RATE_LIMITED
    assert error.retry_after_ms == 120_000
    assert error.status == 429
    assert len(harness.requests) == 1
    assert harness.sleeper.sleeps == []

    harness = Harness(
        replies(
            httpx.Response(429, headers={"Retry-After": "1"}),
            httpx.Response(429, headers={"Retry-After": "2"}),
            httpx.Response(429, headers={"Retry-After": "3"}),
        )
    )
    error = await fails(harness)
    assert error.code is ErrorCode.RATE_LIMITED
    assert error.retry_after_ms == 3000
    assert len(harness.requests) == 3
    assert harness.sleeper.sleeps == [1.0, 2.0]


async def test_retry_after_as_http_date() -> None:
    """@spec PLAT-35: a Retry-After date is waited for relative to the injected clock."""
    clock = FakeClock()
    when = format_datetime(clock.now() + timedelta(seconds=5), usegmt=True)
    harness = Harness(replies(httpx.Response(429, headers={"Retry-After": when}), ok()))
    await harness.client.get_json(URL, source="crossref")
    assert harness.sleeper.sleeps == [5.0]


async def test_long_retry_after_sets_rl_reset_on_the_record() -> None:
    """@spec PLAT-35: a call failed for a long Retry-After records the end of the cool-off."""
    harness = Harness(replies(httpx.Response(429, headers={"Retry-After": "600"})))
    await fails(harness)
    (record,) = harness.sink.records
    assert record.error_code == "rate_limited"
    assert record.rl_reset == "2000-01-01T00:10:00Z"


async def test_429_without_retry_after_backs_off_with_jitter() -> None:
    """@spec PLAT-35: without Retry-After a 429 waits a jittered exponential delay."""
    harness = Harness(replies(httpx.Response(429), httpx.Response(429), httpx.Response(429)))
    error = await fails(harness)
    assert error.code is ErrorCode.RATE_LIMITED
    assert error.retry_after_ms is None
    first, second = harness.sleeper.sleeps
    assert 0.0 <= first <= 0.5
    assert 0.0 <= second <= 1.0


async def test_error_classifier_runs_before_generic_mapping() -> None:
    """@spec PLAT-35: a source's classifier turns an "Insufficient budget" 429 into its own code."""

    def classify(status: int, body: bytes) -> tuple[ErrorCode, str | None] | None:
        if status == 429 and b"Insufficient budget" in body:
            return ErrorCode.BUDGET_EXHAUSTED, "daily budget"
        return None

    openalex = SourcePolicy(
        source="openalex",
        hosts=frozenset({"api.openalex.org"}),
        auth=None,
        rate=RateSpec(rps=1000.0, burst=1000),
        timeout_s=10.0,
        max_bytes=1_000_000,
        error_classifier=classify,
    )
    harness = Harness(replies(httpx.Response(429, text="Insufficient budget")), openalex)
    error = await fails(harness, "https://api.openalex.org/works", "openalex")
    assert error.code is ErrorCode.BUDGET_EXHAUSTED
    assert error.detail == "daily budget"
    assert len(harness.requests) == 1
    assert harness.sink.records[0].error_code == "budget_exhausted"


# PLAT-36


@pytest.mark.parametrize("status", [500, 502, 503, 504])
async def test_retries_5xx_and_policy_block(status: int) -> None:
    """@spec PLAT-36: 5xx and connection errors get 3 jittered attempts; other hosts are blocked."""
    harness = Harness(replies(*(httpx.Response(status) for _ in range(3))))
    error = await fails(harness)
    assert error.code is ErrorCode.UPSTREAM_ERROR
    assert error.status == status
    assert len(harness.requests) == 3
    first, second = harness.sleeper.sleeps
    assert 0.0 <= first <= 0.5
    assert 0.0 <= second <= 1.0

    harness = Harness(replies(httpx.Response(status), ok()))
    assert await harness.client.get_json(URL, source="crossref") == {"ok": True}
    assert len(harness.requests) == 2

    request = httpx.Request("GET", URL)
    harness = Harness(replies(*(httpx.ConnectError("refused", request=request),) * 3))
    error = await fails(harness)
    assert error.code is ErrorCode.UPSTREAM_ERROR
    assert error.status is None
    assert len(harness.requests) == 3

    harness = Harness(replies(ok()))
    for url in (
        "https://evil.example.net/works",
        "https://api.crossref.org.evil.example.net/works",
        "file:///etc/passwd",
    ):
        error = await fails(harness, url)
        assert error.code is ErrorCode.BLOCKED_BY_POLICY
    assert harness.requests == []


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, ErrorCode.UPSTREAM_ERROR),
        (401, ErrorCode.AUTH_FAILED),
        (403, ErrorCode.AUTH_FAILED),
        (404, ErrorCode.NOT_FOUND),
        (410, ErrorCode.UPSTREAM_ERROR),
        (422, ErrorCode.UPSTREAM_ERROR),
        (302, ErrorCode.UPSTREAM_ERROR),
    ],
)
async def test_other_statuses_are_not_retried(status: int, code: ErrorCode) -> None:
    """@spec PLAT-36: 4xx other than 429 are mapped once and never retried."""
    harness = Harness(replies(httpx.Response(status, headers={"Location": "https://x.test/"})))
    error = await fails(harness)
    assert error.code is code
    assert error.status == status
    assert len(harness.requests) == 1
    assert harness.sleeper.sleeps == []


async def test_timeout_is_upstream_timeout() -> None:
    """@spec PLAT-36: a timeout fails with upstream_timeout."""
    request = httpx.Request("GET", URL)
    harness = Harness(replies(httpx.ReadTimeout("slow", request=request)))
    error = await fails(harness)
    assert error.code is ErrorCode.UPSTREAM_TIMEOUT


async def test_invalid_json_is_upstream_error() -> None:
    """@spec PLAT-36: a 200 whose body is not JSON fails with upstream_error."""
    harness = Harness(replies(ok("<html>not json</html>")))
    error = await fails(harness)
    assert error.code is ErrorCode.UPSTREAM_ERROR


# PLAT-38


class CountingStream(httpx.AsyncByteStream):
    def __init__(self, chunks: int, size: int) -> None:
        self.chunks = chunks
        self.size = size
        self.pulled = 0

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for _ in range(self.chunks):
            self.pulled += 1
            yield b"x" * self.size


async def test_byte_cap_aborts_before_full_body() -> None:
    """@spec PLAT-38: a streamed body past the byte cap aborts with too_large before it ends."""
    stream = CountingStream(chunks=100, size=500)
    harness = Harness(lambda request: httpx.Response(200, stream=stream))
    with pytest.raises(HttpError) as caught:
        await harness.client.get_text(URL, source="crossref", max_bytes=1000)
    assert caught.value.code is ErrorCode.TOO_LARGE
    assert stream.pulled < stream.chunks
    assert len(harness.requests) == 1

    declared = CountingStream(chunks=100, size=500)
    harness = Harness(
        lambda request: httpx.Response(200, headers={"Content-Length": "50000"}, stream=declared)
    )
    with pytest.raises(HttpError) as caught:
        await harness.client.get_text(URL, source="crossref", max_bytes=1000)
    assert caught.value.code is ErrorCode.TOO_LARGE
    assert declared.pulled == 0


async def test_byte_cap_defaults_to_the_policy() -> None:
    """@spec PLAT-38: without max_bytes the policy's cap applies."""
    small = SourcePolicy(
        source="crossref",
        hosts=CROSSREF.hosts,
        auth=None,
        rate=CROSSREF.rate,
        timeout_s=10.0,
        max_bytes=10,
    )
    harness = Harness(replies(ok('{"much": "longer than ten bytes"}')), small)
    error = await fails(harness)
    assert error.code is ErrorCode.TOO_LARGE


# PLAT-39 and PLAT-11


async def test_user_agent_and_call_record_per_attempt() -> None:
    """@spec PLAT-39: every request carries the contact user agent; every attempt is recorded."""
    harness = Harness(
        replies(
            httpx.Response(503),
            ok(**{"X-RateLimit-Remaining": "5", "X-RateLimit-Limit": "10"}),
        )
    )
    token = correlation_id.set("corr-1")
    try:
        await harness.client.get_json(URL, source="crossref", params={"query": "x"})
    finally:
        correlation_id.reset(token)

    agents = [request.headers["User-Agent"] for request in harness.requests]
    assert agents == ["research-mcp/3.0 (+mailto:owner@uni.edu)"] * 2

    first, second = harness.sink.records
    assert (first.attempt, second.attempt) == (1, 2)
    assert (first.status, second.status) == (503, 200)
    assert (first.error_code, second.error_code) == ("upstream_error", None)
    assert {first.source, second.source} == {"crossref"}
    assert {first.correlation_id, second.correlation_id} == {"corr-1"}
    assert first.op == second.op == "get_json"
    assert second.bytes == len(b'{"ok": true}')
    assert second.rl_remaining == "5/10"
    assert first.rl_remaining is None


async def test_failed_attempts_without_a_response_are_recorded() -> None:
    """@spec PLAT-39: connection errors and timeouts still produce one record per attempt."""
    request = httpx.Request("GET", URL)
    harness = Harness(
        replies(httpx.ConnectError("refused", request=request), httpx.ReadTimeout("slow"))
    )
    await fails(harness)
    first, second = harness.sink.records
    assert (first.status, first.error_code, first.attempt) == (None, "upstream_error", 1)
    assert (second.status, second.error_code, second.attempt) == (None, "upstream_timeout", 2)


async def test_github_token_expiry_header_is_recorded() -> None:
    """@spec PLAT-39: the credential expiry header is copied to the call record."""
    expiry = "2026-12-01 10:00:00 UTC"
    harness = Harness(replies(ok(**{"github-authentication-token-expiration": expiry})))
    await harness.client.get_json(URL, source="crossref")
    assert harness.sink.records[0].cred_expires_at == expiry


def test_build_user_agent() -> None:
    """@spec PLAT-39: the user agent names the major and minor version and the contact."""
    assert build_user_agent("3.0.0", "owner@uni.edu") == "research-mcp/3.0 (+mailto:owner@uni.edu)"
    assert build_user_agent("3.12.7", "a@b.org") == "research-mcp/3.12 (+mailto:a@b.org)"


async def test_user_agent_without_contact() -> None:
    """@spec PLAT-11: with contact.email unset the user agent has no mailto and no invented one."""
    assert build_user_agent("3.0.0", None) == "research-mcp/3.0"
    harness = Harness(replies(ok()), contact=None)
    await harness.client.get_json(URL, source="crossref")
    assert harness.requests[0].headers["User-Agent"] == "research-mcp/3.0"


# Placement (SEC-9; the scoping and leak checks are in tests/security/test_scoped_credentials.py)

KEY = Secret(SecretRef("keychain", "TEST_KEY", "research-mcp/TEST_KEY"), "k-test-0123456789")


def keyed(placement: str, param: str) -> SourcePolicy:
    return SourcePolicy(
        source="keyed",
        hosts=frozenset({"api.keyed.test"}),
        auth=AuthSpec(
            secrets=("TEST_KEY",),
            required=True,
            placement=placement,  # type: ignore[arg-type]
            param=param,
            origins=("https://api.keyed.test",),
            signup_url="https://keyed.test/signup",
        ),
        rate=RateSpec(rps=1000.0, burst=1000),
        timeout_s=10.0,
        max_bytes=1_000_000,
    )


@pytest.mark.parametrize(
    ("placement", "param", "header", "query"),
    [
        ("header", "x-goog-api-key", ("x-goog-api-key", "k-test-0123456789"), None),
        ("bearer", "", ("authorization", "Bearer k-test-0123456789"), None),
        ("query", "api_key", None, ("api_key", "k-test-0123456789")),
    ],
)
async def test_credential_placement(
    placement: str, param: str, header: tuple[str, str] | None, query: tuple[str, str] | None
) -> None:
    """@spec SEC-9: the credential goes in the header, bearer or query slot the spec names."""
    harness = Harness(
        replies(ok()), keyed(placement, param), credentials=Credentials({"keyed": KEY})
    )
    await harness.client.get_json("https://api.keyed.test/v1", source="keyed", params={"q": "a"})
    (request,) = harness.requests
    if header is not None:
        assert request.headers[header[0]] == header[1]
        assert "k-test" not in str(request.url)
    if query is not None:
        assert request.url.params[query[0]] == query[1]
        assert request.url.params["q"] == "a"
        assert "authorization" not in request.headers


async def test_post_json_sends_body_and_parses_reply() -> None:
    """@spec PLAT-39: post_json goes through the same path and carries the user agent."""
    harness = Harness(replies(ok('{"id": 7}')))
    assert await harness.client.post_json(URL, source="crossref", json={"a": [1]}) == {"id": 7}
    (request,) = harness.requests
    assert request.method == "POST"
    assert request.content == b'{"a":[1]}'
    assert request.headers["User-Agent"].startswith("research-mcp/3.0")
    assert harness.sink.records[0].op == "post_json"


async def test_get_text_returns_text_response() -> None:
    """@spec PLAT-39: get_text returns the final URL, status, content type and decoded text."""
    harness = Harness(
        replies(
            httpx.Response(
                200,
                content="hé".encode("latin-1"),
                headers={"Content-Type": "text/plain; charset=latin-1"},
            )
        )
    )
    response = await harness.client.get_text(URL, source="crossref")
    assert response.text == "hé"
    assert response.status == 200
    assert response.content_type == "text/plain; charset=latin-1"
    assert response.url == URL
