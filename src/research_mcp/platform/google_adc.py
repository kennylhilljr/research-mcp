"""The owner's Google sign-in for ``vertex_search`` (LLD-platform-v3 4.2; SEC-INV-11).

``gcloud`` owns the sign-in. ``google-auth`` (the ``gcp`` extra) is the only reader of its
credential file: nothing here opens, copies or writes it, and the access token stays in
memory as a ``Secret``. The library is imported only when a sign-in is loaded, so a
search-only install imports none of it (PLAT-13).

Loading and refreshing block, so the daemon calls ``get`` and ``metadata`` through
``anyio.to_thread.run_sync``. The token request goes through ``TokenTransport``, which
sends only to ``https://oauth2.googleapis.com`` and records each attempt as a
``CallRecord`` with ``source="google_signin"``. Exception text from the library is never
logged or returned: it can quote the credential file.
"""

from __future__ import annotations

import importlib
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx

from research_mcp.core.context import correlation_id
from research_mcp.core.errors import ErrorCode
from research_mcp.core.models import CallRecord, Clock
from research_mcp.core.timeutil import SystemClock
from research_mcp.platform.http import CallSink, status_code
from research_mcp.platform.secrets import Secret, SecretMeta, SecretRef, SecretState

SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)
TOKEN_ORIGIN = ("https", "oauth2.googleapis.com", 443)
SIGNIN_SOURCE = "google_signin"
REFRESH_MARGIN = timedelta(minutes=5)
TOKEN_TIMEOUT_S = 10.0
SYSTEM_CLOCK = SystemClock()


class Credentials(Protocol):
    """The part of ``google.auth.credentials.Credentials`` the provider uses."""

    token: str | None
    expiry: datetime | None

    def refresh(self, request: Any) -> None: ...


Loader = Callable[[], tuple[Credentials, str | None]]


@dataclass(frozen=True)
class _Response:
    """The response shape ``google.auth.transport.Response`` describes."""

    status: int
    headers: Mapping[str, str]
    data: bytes


def _google(module: str) -> Any:
    """A ``google.auth`` module, imported on first use; ``ImportError`` without the extra."""
    return importlib.import_module(module)


def _transport_error() -> Exception:
    error: Exception = _google("google.auth.exceptions").TransportError("token request refused")
    return error


@dataclass
class TokenTransport:
    """A ``google.auth.transport.Request`` that reaches ``oauth2.googleapis.com`` only.

    Any other URL raises ``TransportError`` before anything is sent, so finding the sign-in
    never calls the network either (for example the GCE metadata server).
    """

    sink: CallSink | None = None
    clock: Clock = SYSTEM_CLOCK
    transport: httpx.BaseTransport | None = None
    _sent: int = field(default=0, init=False)

    def __call__(
        self,
        url: str,
        method: str = "GET",
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> _Response:
        target = httpx.URL(url)
        origin = (target.scheme, target.host, target.port or 443)
        if origin != TOKEN_ORIGIN:
            raise _transport_error()
        self._sent += 1
        ts = self.clock.now()
        started = time.perf_counter()
        reply: httpx.Response | None = None
        code: ErrorCode | None = None
        try:
            with httpx.Client(transport=self.transport, follow_redirects=False) as client:
                reply = client.request(
                    method,
                    target,
                    content=body,
                    headers=dict(headers or {}),
                    timeout=timeout or TOKEN_TIMEOUT_S,
                )
            if not 200 <= reply.status_code < 300:
                code = status_code(reply.status_code)
        except httpx.TimeoutException:
            code = ErrorCode.UPSTREAM_TIMEOUT
        except httpx.HTTPError:
            code = ErrorCode.UPSTREAM_ERROR
        self._record(ts, started, reply, code)
        if reply is None:
            raise _transport_error() from None
        return _Response(reply.status_code, dict(reply.headers), reply.content)

    def _record(
        self, ts: datetime, started: float, reply: httpx.Response | None, code: ErrorCode | None
    ) -> None:
        if self.sink is None:
            return
        self.sink.record(
            CallRecord(
                ts=ts,
                source=SIGNIN_SOURCE,
                op="refresh",
                status=None if reply is None else reply.status_code,
                error_code=None if code is None else code.value,
                latency_ms=int((time.perf_counter() - started) * 1000),
                bytes=0 if reply is None else len(reply.content),
                rl_remaining=None,
                rl_reset=None,
                cred_expires_at=None,
                correlation_id=correlation_id.get(),
                attempt=self._sent,
            )
        )


# @spec PLAT-13
def default_loader() -> tuple[Credentials, str | None]:
    """The owner's sign-in as ``google-auth`` finds it; ``ImportError`` without the extra."""
    creds, project = _google("google.auth").default(scopes=list(SCOPES), request=TokenTransport())
    return creds, project


def _state_for(exc: Exception) -> SecretState:
    """The state for a load or refresh failure; the exception text is dropped."""
    if isinstance(exc, ImportError):
        return SecretState.MISSING  # the gcp extra is not installed
    try:
        exceptions = _google("google.auth.exceptions")
    except ImportError:
        return SecretState.ERROR
    if isinstance(exc, exceptions.RefreshError):
        return SecretState.INVALID  # for example invalid_grant: sign in again
    if isinstance(exc, exceptions.DefaultCredentialsError):
        return SecretState.MISSING
    return SecretState.ERROR


def _aware(when: datetime | None) -> datetime | None:
    # google-auth keeps expiry as a naive UTC time.
    if when is None or when.tzinfo is not None:
        return when
    return when.replace(tzinfo=UTC)


def _account(creds: Credentials) -> str | None:
    for attr in ("account", "service_account_email"):
        value = getattr(creds, attr, None)
        if isinstance(value, str) and value:
            return value
    return None


# @spec SEC-27
class GoogleAdcProvider:
    """``SecretProvider`` for the ``gcloud_adc`` backend (extra ``gcp``).

    ``get`` returns the cached access token and refreshes it when less than five minutes
    are left. ``transport`` replaces the network for the token request in tests.
    """

    def __init__(
        self,
        loader: Loader = default_loader,
        sink: CallSink | None = None,
        clock: Clock = SYSTEM_CLOCK,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._loader = loader
        self._sink = sink
        self._clock = clock
        self._transport = transport
        self._creds: Credentials | None = None
        self._lock = threading.Lock()

    def _load(self) -> Credentials:
        if self._creds is None:
            self._creds, _project = self._loader()
        return self._creds

    def _stale(self, creds: Credentials) -> bool:
        if not creds.token:
            return True
        expiry = _aware(creds.expiry)
        return expiry is not None and expiry - self._clock.now() < REFRESH_MARGIN

    def get(self, ref: SecretRef) -> tuple[SecretState, Secret | None]:
        if ref.backend != "gcloud_adc":
            return SecretState.MISSING, None
        with self._lock:
            try:
                creds = self._load()
                if self._stale(creds):
                    creds.refresh(TokenTransport(self._sink, self._clock, self._transport))
                token = creds.token
            except Exception as exc:  # noqa: BLE001 - any failure is a state, never text
                return _state_for(exc), None
        if not isinstance(token, str) or not token:
            return SecretState.ERROR, None
        return SecretState.OK, Secret(ref, token)

    def metadata(self, ref: SecretRef) -> SecretMeta | None:
        """The account email and the token expiry; no token, and no refresh."""
        if ref.backend != "gcloud_adc":
            return None
        with self._lock:
            try:
                creds = self._load()
            except Exception:  # noqa: BLE001 - no sign-in means no metadata
                return None
            return SecretMeta(
                ref.name, None, account=_account(creds), expires_at=_aware(creds.expiry)
            )

    def set(self, ref: SecretRef, value: str) -> None:
        raise NotImplementedError("gcloud owns the Google sign-in; v2 never writes it")
