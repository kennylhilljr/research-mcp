"""The shared HTTP client: host policy, scoped credentials, rate limits, retries, byte cap
and call telemetry (LLD-platform-v2 2.2, 4.4, 5.3 and 6.1).

Adapters reach the network only through ``HttpPort``. ``HttpClient`` is its one
implementation; the daemon builds one and shares it, so the per-source rate limits in its
``RateRegistry`` hold across every client of the daemon.

Nothing here puts a URL, an upstream body or exception text into an ``HttpError`` or a log
record: errors carry a code, a status and at most a fixed detail, and the log gets the
source, operation, status, error code and attempt (SEC-9, SEC-10).
"""

from __future__ import annotations

import json as _json
import logging
import math
import random
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from types import TracebackType
from typing import Protocol, cast

import anyio
import httpx

from research_mcp.core.context import correlation_id
from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.models import AuthUse, CallRecord, Clock, JsonValue, Sleeper, TextResponse
from research_mcp.core.specs import SourcePolicy
from research_mcp.platform.ratelimit import RateRegistry
from research_mcp.platform.secrets import Secret
from research_mcp.version import __version__

MAX_ATTEMPTS = 3
MAX_RETRY_AFTER_S = 60.0
BACKOFF_BASE_S = 0.5
MAX_CONNECTIONS = 50
MAX_CONNECTIONS_PER_HOST = 8
RETRIED_5XX = frozenset({500, 502, 503, 504})
CRED_EXPIRY_HEADER = "github-authentication-token-expiration"

_DEFAULT_PORTS = {"http": 80, "https": 443}
_log = logging.getLogger(__name__)


class PolicyResolver(Protocol):
    def policy(self, source: str) -> SourcePolicy: ...


class CredentialResolver(Protocol):
    def secret_for(self, source: str) -> Secret | None: ...


class CallSink(Protocol):
    def record(self, call: CallRecord) -> None: ...


class HttpPort(Protocol):
    async def get_json(
        self,
        url: str,
        *,
        source: str,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        max_bytes: int | None = None,
        auth: AuthUse = AuthUse.SPEC,
    ) -> JsonValue: ...

    async def post_json(
        self,
        url: str,
        *,
        source: str,
        json: JsonValue,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        max_bytes: int | None = None,
        auth: AuthUse = AuthUse.SPEC,
    ) -> JsonValue: ...

    async def get_text(
        self,
        url: str,
        *,
        source: str,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        max_bytes: int | None = None,
        auth: AuthUse = AuthUse.SPEC,
    ) -> TextResponse: ...


# @spec PLAT-39, PLAT-11
def build_user_agent(version: str, contact_email: str | None) -> str:
    """``research-mcp/<major>.<minor> (+mailto:<contact>)``; no mailto part without a contact."""
    major, minor = version.split(".")[:2]
    base = f"research-mcp/{major}.{minor}"
    return f"{base} (+mailto:{contact_email})" if contact_email else base


def _origin(url: httpx.URL) -> tuple[str, str, int | None]:
    scheme = url.scheme.lower()
    return scheme, url.host.lower(), url.port or _DEFAULT_PORTS.get(scheme)


def _retry_after_s(value: str | None, now: datetime) -> float | None:
    """Seconds to wait from a ``Retry-After`` header (delta seconds or an HTTP date)."""
    if value is None:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, (when - now).total_seconds())


def _rl_remaining(headers: httpx.Headers) -> str | None:
    left = headers.get("x-ratelimit-remaining") or headers.get("ratelimit-remaining")
    limit = headers.get("x-ratelimit-limit") or headers.get("ratelimit-limit")
    if left is None:
        return None
    return f"{left}/{limit}" if limit is not None else left


class _TooLargeError(Exception):
    pass


@dataclass
class _Attempt:
    """What one attempt produced; ``error`` is ``None`` for a 2xx response."""

    status: int | None = None
    headers: httpx.Headers = field(default_factory=httpx.Headers)
    content: bytes = b""
    encoding: str | None = None
    error: HttpError | None = None
    retry: bool = False
    delay_s: float | None = None
    exception: str | None = None


class HttpClient:
    """The one ``HttpPort`` implementation (LLD-platform-v2 2.2)."""

    def __init__(
        self,
        policies: PolicyResolver,
        credentials: CredentialResolver,
        sink: CallSink,
        clock: Clock,
        sleeper: Sleeper,
        contact_email: str | None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._policies = policies
        self._credentials = credentials
        self._sink = sink
        self._clock = clock
        self._sleeper = sleeper
        self._user_agent = build_user_agent(__version__, contact_email)
        self._rates = RateRegistry(clock, sleeper)
        self._host_gates: dict[str, anyio.Semaphore] = {}
        self._client = httpx.AsyncClient(
            http2=True,
            limits=httpx.Limits(max_connections=MAX_CONNECTIONS),
            follow_redirects=False,
            transport=transport,
        )

    async def __aenter__(self) -> HttpClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_json(
        self,
        url: str,
        *,
        source: str,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        max_bytes: int | None = None,
        auth: AuthUse = AuthUse.SPEC,
    ) -> JsonValue:
        result, _ = await self._request(
            "GET", "get_json", url, source, params, headers, None, max_bytes, auth
        )
        return self._parse_json(result)

    async def post_json(
        self,
        url: str,
        *,
        source: str,
        json: JsonValue,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        max_bytes: int | None = None,
        auth: AuthUse = AuthUse.SPEC,
    ) -> JsonValue:
        result, _ = await self._request(
            "POST", "post_json", url, source, params, headers, json, max_bytes, auth
        )
        return self._parse_json(result)

    async def get_text(
        self,
        url: str,
        *,
        source: str,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        max_bytes: int | None = None,
        auth: AuthUse = AuthUse.SPEC,
    ) -> TextResponse:
        result, public_url = await self._request(
            "GET", "get_text", url, source, params, headers, None, max_bytes, auth
        )
        try:
            text = result.content.decode(result.encoding or "utf-8", errors="replace")
        except LookupError:
            text = result.content.decode("utf-8", errors="replace")
        return TextResponse(
            url=public_url,
            status=result.status or 0,
            content_type=result.headers.get("content-type", ""),
            text=text,
        )

    @staticmethod
    def _parse_json(result: _Attempt) -> JsonValue:
        try:
            return cast(JsonValue, _json.loads(result.content))
        except ValueError:
            raise HttpError(ErrorCode.UPSTREAM_ERROR, status=result.status) from None

    # @spec PLAT-35, PLAT-36, PLAT-38, PLAT-39, SEC-10
    async def _request(
        self,
        method: str,
        op: str,
        url: str,
        source: str,
        params: Mapping[str, str] | None,
        headers: Mapping[str, str] | None,
        json: JsonValue | None,
        max_bytes: int | None,
        auth: AuthUse,
    ) -> tuple[_Attempt, str]:
        """Send with up to three attempts; return the 2xx result and the URL without secrets."""
        policy = self._policies.policy(source)
        target = self._checked_url(policy, op, url, params)
        public_url = str(target)
        send_headers = httpx.Headers(headers or {})
        send_headers["User-Agent"] = self._user_agent
        target = self._attach(policy, source, target, send_headers, auth)
        request = self._client.build_request(
            method,
            target,
            headers=send_headers,
            json=json if method == "POST" else None,
            timeout=policy.timeout_s,
        )
        cap = max_bytes if max_bytes is not None else policy.max_bytes
        for attempt in range(1, MAX_ATTEMPTS + 1):
            result = await self._attempt(request, policy, op, cap, attempt)
            if result.error is None:
                return result, public_url
            if not result.retry or attempt == MAX_ATTEMPTS:
                _log.warning(
                    "upstream call failed",
                    extra={
                        "source": source,
                        "operation": op,
                        "status": result.status,
                        "error_code": result.error.code.value,
                        "attempt": attempt,
                        "exception": result.exception,
                    },
                )
                raise result.error
            delay = result.delay_s
            if delay is None:
                # Full jitter: uniform over [0, base * 2^(attempt - 1)]; not a security use.
                delay = random.uniform(0.0, BACKOFF_BASE_S * 2 ** (attempt - 1))  # noqa: S311
            await self._sleeper.sleep(delay)
        raise AssertionError("unreachable")  # pragma: no cover

    def _checked_url(
        self, policy: SourcePolicy, op: str, url: str, params: Mapping[str, str] | None
    ) -> httpx.URL:
        """The request URL with the caller's params, or ``blocked_by_policy`` (PLAT-36)."""
        try:
            target = httpx.URL(url)
            if params:
                target = target.copy_merge_params(dict(params))
        except (httpx.InvalidURL, TypeError, ValueError):
            target = None
        if (
            target is None
            or target.scheme not in _DEFAULT_PORTS
            or target.host.lower() not in policy.hosts
        ):
            _log.warning(
                "request blocked by host policy",
                extra={
                    "source": policy.source,
                    "operation": op,
                    "error_code": ErrorCode.BLOCKED_BY_POLICY.value,
                },
            )
            raise HttpError(ErrorCode.BLOCKED_BY_POLICY)
        return target

    # @spec SEC-8, SEC-9
    def _attach(
        self,
        policy: SourcePolicy,
        source: str,
        target: httpx.URL,
        headers: httpx.Headers,
        auth: AuthUse,
    ) -> httpx.URL:
        """Attach the source's secret only for a request to one of its spec origins."""
        spec = policy.auth
        if auth is AuthUse.NONE or spec is None:
            return target
        if _origin(target) not in {_origin(httpx.URL(origin)) for origin in spec.origins}:
            return target
        secret = self._credentials.secret_for(source)
        if secret is None:
            return target
        if spec.placement == "header":
            headers[spec.param] = secret.reveal()
        elif spec.placement == "bearer":
            headers["Authorization"] = f"Bearer {secret.reveal()}"
        else:
            # Query placement only where the API offers nothing else; the URL is never logged.
            target = target.copy_merge_params({spec.param: secret.reveal()})
        return target

    def _host_gate(self, host: str) -> anyio.Semaphore:
        gate = self._host_gates.get(host)
        if gate is None:
            gate = anyio.Semaphore(MAX_CONNECTIONS_PER_HOST)
            self._host_gates[host] = gate
        return gate

    async def _attempt(
        self, request: httpx.Request, policy: SourcePolicy, op: str, cap: int, attempt: int
    ) -> _Attempt:
        async with self._rates.slot(policy.source, policy.rate), self._host_gate(request.url.host):
            ts = self._clock.now()
            started = time.perf_counter()
            result = await self._send(request, cap)
            latency_ms = int((time.perf_counter() - started) * 1000)
        if result.error is None and result.status is not None and not 200 <= result.status < 300:
            self._classify(policy, result, ts)
        self._record(policy.source, op, attempt, ts, latency_ms, result)
        return result

    async def _send(self, request: httpx.Request, cap: int) -> _Attempt:
        """One exchange, streamed under the byte cap; transport failures become codes."""
        result = _Attempt()
        try:
            response = await self._client.send(request, stream=True)
            try:
                result.status = response.status_code
                result.headers = response.headers
                result.encoding = response.charset_encoding
                result.content = await self._read_capped(response, cap)
            finally:
                await response.aclose()
        except _TooLargeError:
            result.error = HttpError(ErrorCode.TOO_LARGE, status=result.status)
        except httpx.TimeoutException as exc:
            result.error = HttpError(ErrorCode.UPSTREAM_TIMEOUT)
            result.exception = type(exc).__name__
        except httpx.TransportError as exc:
            result.error = HttpError(ErrorCode.UPSTREAM_ERROR)
            result.retry = True
            result.exception = type(exc).__name__
        except httpx.HTTPError as exc:
            result.error = HttpError(ErrorCode.UPSTREAM_ERROR, status=result.status)
            result.exception = type(exc).__name__
        return result

    @staticmethod
    async def _read_capped(response: httpx.Response, cap: int) -> bytes:
        declared = response.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > cap:
            raise _TooLargeError
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > cap:
                raise _TooLargeError
            chunks.append(chunk)
        return b"".join(chunks)

    def _classify(self, policy: SourcePolicy, result: _Attempt, now: datetime) -> None:
        """Map a non-2xx status to a code, whether to retry and how long to wait (6.1)."""
        status = cast(int, result.status)
        if policy.error_classifier is not None:
            hit = policy.error_classifier(status, result.content)
            if hit is not None:
                result.error = HttpError(hit[0], status=status, detail=hit[1])
                return
        wait = _retry_after_s(result.headers.get("retry-after"), now)
        wait_ms = None if wait is None else math.ceil(wait * 1000)
        too_long = wait is not None and wait > MAX_RETRY_AFTER_S
        if status == 429:
            result.error = HttpError(ErrorCode.RATE_LIMITED, status=status, retry_after_ms=wait_ms)
        elif status in RETRIED_5XX:
            result.error = HttpError(ErrorCode.UPSTREAM_ERROR, status=status)
        elif status in (401, 403):
            result.error = HttpError(ErrorCode.AUTH_FAILED, status=status)
            return
        elif status == 404:
            result.error = HttpError(ErrorCode.NOT_FOUND, status=status)
            return
        else:
            result.error = HttpError(ErrorCode.UPSTREAM_ERROR, status=status)
            return
        result.retry = not too_long
        result.delay_s = wait

    def _record(
        self,
        source: str,
        op: str,
        attempt: int,
        ts: datetime,
        latency_ms: int,
        result: _Attempt,
    ) -> None:
        code = None if result.error is None else result.error.code
        rl_reset = result.headers.get("x-ratelimit-reset") or result.headers.get("ratelimit-reset")
        if code in (ErrorCode.RATE_LIMITED, ErrorCode.BUDGET_EXHAUSTED):
            wait = _retry_after_s(result.headers.get("retry-after"), ts)
            if wait is not None:
                until = ts + timedelta(seconds=wait)
                rl_reset = until.isoformat(timespec="seconds").replace("+00:00", "Z")
        self._sink.record(
            CallRecord(
                ts=ts,
                source=source,
                op=op,
                status=result.status,
                error_code=None if code is None else code.value,
                latency_ms=latency_ms,
                bytes=len(result.content),
                rl_remaining=_rl_remaining(result.headers),
                rl_reset=rl_reset,
                cred_expires_at=result.headers.get(CRED_EXPIRY_HEADER),
                correlation_id=correlation_id.get(),
                attempt=attempt,
            )
        )
