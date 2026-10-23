"""The downloader: SSRF checks, DNS pinning, content checks and atomic storage.

LLD-platform-v2 5.4 and LLD-cache-v2 5.13. Every hop requires https, passes the host
policy, resolves through the injected ``Resolver`` and is refused unless every address is
public. The connection then goes through ``PinnedTransport`` to the checked address with
the hostname kept for SNI and the ``Host`` header, so httpx never resolves the name again
(DNS rebinding). Redirects are followed by hand, at most five, each checked the same way.

The downloader has no ``CredentialResolver``: a download never carries a credential
(LLD-platform-v2 4.4; SEC-INV-5). It writes only under ``data_dir`` (SEC-INV-7).
"""

from __future__ import annotations

import hashlib
import ipaddress
import os
import socket
import ssl
from collections.abc import Callable, Iterable
from contextlib import aclosing
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import anyio
import httpcore
import httpx
from ulid import ULID

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.models import DownloadedFile
from research_mcp.platform.http import build_user_agent, capped_body
from research_mcp.version import __version__

MAX_REDIRECTS = 5
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
EXTENSIONS = {"application/pdf": "pdf", "text/html": "html"}
# Enough of the body to see the magic bytes, or the first character after leading whitespace.
_HEAD_BYTES = 1024
# The NAT64 well-known prefix; its last 32 bits are the IPv4 address reached (RFC 6052).
_NAT64 = ipaddress.IPv6Network("64:ff9b::/96")


class Resolver(Protocol):
    async def resolve(self, host: str) -> list[str]: ...


class SystemResolver:
    """The daemon's resolver: the system's ``getaddrinfo``, run off the event loop."""

    async def resolve(self, host: str) -> list[str]:
        infos = await anyio.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return list(dict.fromkeys(str(info[4][0]) for info in infos))


@dataclass(frozen=True)
class DownloadPolicy:
    """What a download may fetch: ``allowed_hosts`` (or ``public_any``), types and size."""

    media_types: frozenset[str]
    max_bytes: int
    allowed_hosts: frozenset[str] = frozenset()
    public_any: bool = False
    timeout_s: float = 60.0


def is_public_address(text: str) -> bool:
    """True only for a globally routable unicast address, IPv4 or IPv6.

    An IPv6 address that carries an IPv4 address (mapped, 6to4 or NAT64) is public only
    when the carried address is public too.
    """
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            return _public(address.ipv4_mapped)
        if address.sixtofour is not None and not _public(address.sixtofour):
            return False
        if address in _NAT64 and not _public(ipaddress.IPv4Address(int(address) & 0xFFFF_FFFF)):
            return False
    return _public(address)


def _public(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return address.is_global and not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


class _PinnedBackend(httpcore.AsyncNetworkBackend):
    """Dials the checked address for the one host it was pinned for, and nothing else."""

    def __init__(self, host: str, ip: str, inner: httpcore.AsyncNetworkBackend) -> None:
        self._host = host.lower()
        self._ip = ip
        self._inner = inner

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,  # noqa: ASYNC109 (httpcore's backend signature)
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        if host.lower() != self._host:
            raise httpcore.ConnectError("connection is pinned to another host")
        return await self._inner.connect_tcp(
            self._ip,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,  # noqa: ASYNC109 (httpcore's backend signature)
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise httpcore.ConnectError("connection is pinned to a TCP address")

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


class PinnedTransport(httpx.AsyncHTTPTransport):
    """An httpx transport whose connections go to ``ip`` for requests to ``host``.

    The request URL keeps the hostname, so TLS verifies the certificate for it, SNI names
    it and the ``Host`` header carries it; only the TCP connect uses the checked address.
    """

    def __init__(self, host: str, ip: str, *, verify: ssl.SSLContext | bool = True) -> None:
        super().__init__(verify=verify, trust_env=False)
        # Replaces the pool built by the parent with one that dials the pinned address.
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=httpx.create_ssl_context(verify=verify, trust_env=False),
            http1=True,
            http2=False,
            network_backend=_PinnedBackend(host, ip, httpcore.AnyIOBackend()),
        )


TransportFactory = Callable[[str, str], httpx.AsyncBaseTransport]


def _blocked(detail: str) -> HttpError:
    return HttpError(ErrorCode.BLOCKED_BY_POLICY, detail=detail)


def _remaining(deadline: float) -> float:
    left = deadline - anyio.current_time()
    if left <= 0:
        raise HttpError(ErrorCode.UPSTREAM_TIMEOUT)
    return left


def _status_error(status: int) -> HttpError | None:
    if 200 <= status < 300:
        return None
    if status in (401, 403):
        return HttpError(ErrorCode.AUTH_FAILED, status=status)
    if status == 404:
        return HttpError(ErrorCode.NOT_FOUND, status=status)
    if status == 429:
        return HttpError(ErrorCode.RATE_LIMITED, status=status)
    return HttpError(ErrorCode.UPSTREAM_ERROR, status=status)


def _magic_ok(media_type: str, head: bytes) -> bool:
    if media_type == "application/pdf":
        return head.startswith(b"%PDF-")
    if media_type == "text/html":
        return head.lstrip().startswith(b"<")
    return True


def _place(part: Path, final: Path) -> None:
    """Move the finished part file into place, or drop it when the same file is stored."""
    final.parent.mkdir(parents=True, exist_ok=True)
    if final.exists():
        part.unlink()
        return
    os.replace(part, final)
    directory = os.open(final.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


class Downloader:
    """Fetches one file under a ``DownloadPolicy`` into ``data_dir/files`` by SHA-256."""

    def __init__(
        self,
        resolver: Resolver,
        policy: DownloadPolicy,
        data_dir: Path,
        *,
        user_agent: str | None = None,
        transport_factory: TransportFactory = PinnedTransport,
    ) -> None:
        self._resolver = resolver
        self._policy = policy
        self._data_dir = data_dir
        self._user_agent = user_agent or build_user_agent(__version__, None)
        self._transport_factory = transport_factory

    # @spec CACHE-1, CACHE-2
    async def download(self, url: str, *, policy: DownloadPolicy | None = None) -> DownloadedFile:
        """Download ``url``; raise ``HttpError`` (``blocked_by_policy``, ``too_large``, ...)."""
        policy = policy or self._policy
        # timeout_s bounds the whole download, redirects included, not each read.
        deadline = anyio.current_time() + policy.timeout_s
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            code: ErrorCode | None = None
            try:
                outcome = await self._hop(current, policy, deadline)
            except httpx.TimeoutException:
                code = ErrorCode.UPSTREAM_TIMEOUT
            except httpx.HTTPError:
                code = ErrorCode.UPSTREAM_ERROR
            if code is not None:
                raise HttpError(code)
            if isinstance(outcome, DownloadedFile):
                return outcome
            current = outcome
        raise _blocked("too many redirects")

    async def _check(self, url: str, policy: DownloadPolicy) -> tuple[httpx.URL, str]:
        """Scheme, host policy and address checks for one hop; returns the address to dial."""
        try:
            target = httpx.URL(url)
        except (httpx.InvalidURL, TypeError, ValueError):
            target = None
        if target is None or target.scheme != "https" or not target.host:
            raise _blocked("scheme")
        host = target.host.lower()
        if not policy.public_any and host not in policy.allowed_hosts:
            raise _blocked("host")
        try:
            ipaddress.ip_address(host)
            addresses = [host]
        except ValueError:
            try:
                addresses = await self._resolver.resolve(host)
            except OSError:
                raise HttpError(ErrorCode.UPSTREAM_ERROR, detail="resolve") from None
        if not addresses or not all(is_public_address(a) for a in addresses):
            raise _blocked("address")
        return target, addresses[0]

    async def _hop(self, url: str, policy: DownloadPolicy, deadline: float) -> DownloadedFile | str:
        """One checked request: the stored file, or the next URL of a redirect."""
        target, ip = await self._check(url, policy)
        transport = self._transport_factory(target.host, ip)
        async with (
            httpx.AsyncClient(
                transport=transport, follow_redirects=False, timeout=_remaining(deadline)
            ) as client,
            # A server may encode the body anyway; capped_body inflates it under the cap.
            client.stream(
                "GET",
                target,
                headers={"User-Agent": self._user_agent, "Accept-Encoding": "identity"},
            ) as response,
        ):
            if response.status_code in REDIRECT_STATUSES:
                location = response.headers.get("location")
                if not location:
                    raise HttpError(ErrorCode.UPSTREAM_ERROR, status=response.status_code)
                return str(target.join(location))
            error = _status_error(response.status_code)
            if error is not None:
                raise error
            return await self._store(response, target, policy, deadline)

    async def _store(
        self, response: httpx.Response, target: httpx.URL, policy: DownloadPolicy, deadline: float
    ) -> DownloadedFile:
        media_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if media_type not in policy.media_types:
            raise _blocked("media type")

        tmp = self._data_dir / "tmp"
        await anyio.Path(tmp).mkdir(parents=True, exist_ok=True)
        part = tmp / f"{ULID()}.part"
        digest = hashlib.sha256()
        size = 0
        head = b""
        try:
            async with (
                await anyio.open_file(part, "xb") as out,
                aclosing(capped_body(response, policy.max_bytes)) as body,
            ):
                async for chunk in body:
                    if anyio.current_time() > deadline:
                        raise HttpError(ErrorCode.UPSTREAM_TIMEOUT)
                    size += len(chunk)
                    if len(head) < _HEAD_BYTES:
                        head += chunk[: _HEAD_BYTES - len(head)]
                    digest.update(chunk)
                    await out.write(chunk)
                await out.flush()
                await anyio.to_thread.run_sync(os.fsync, out.wrapped.fileno())
            if not _magic_ok(media_type, head):
                raise _blocked("magic bytes")
            sha256 = digest.hexdigest()
            final = (
                self._data_dir
                / "files"
                / sha256[:2]
                / f"{sha256}.{EXTENSIONS.get(media_type, 'bin')}"
            )
            await anyio.to_thread.run_sync(_place, part, final)
        finally:
            await anyio.Path(part).unlink(missing_ok=True)

        return DownloadedFile(
            sha256=sha256,
            size=size,
            media_type=media_type,
            storage_path=str(final),
            final_url=str(target),
            http_status=response.status_code,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )
