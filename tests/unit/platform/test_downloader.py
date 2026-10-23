"""The downloader: SSRF checks, DNS pinning, content checks and atomic storage.

LLD-platform-v2 5.4; LLD-cache-v2 5.13. The resolver is a fake and every upstream is an
``httpx.MockTransport``, except the pinning test, which talks to a server on 127.0.0.1.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import socket
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.platform.download import Downloader, DownloadPolicy, PinnedTransport

PUBLIC = "93.184.216.34"
PUBLIC_2 = "151.101.1.69"
PDF = b"%PDF-1.7\n" + b"0" * 200
HTML = b"  \n\t<!doctype html><title>t</title>"

POLICY = DownloadPolicy(
    media_types=frozenset({"application/pdf", "text/html"}),
    max_bytes=10_000,
    allowed_hosts=frozenset({"arxiv.org", "files.arxiv.org"}),
)

Handler = Callable[[httpx.Request], httpx.Response]


class FakeResolver:
    """Answers each host with the next list of addresses from its script; the last repeats."""

    def __init__(self, answers: dict[str, list[list[str]]] | None = None) -> None:
        self.answers = answers or {}
        self.calls: list[str] = []

    async def resolve(self, host: str) -> list[str]:
        self.calls.append(host)
        script = self.answers.get(host, [[PUBLIC]])
        return script.pop(0) if len(script) > 1 else script[0]


class Upstream:
    """Routes requests by URL and records the (host, ip) of every pinned transport."""

    def __init__(self, routes: dict[str, Handler | httpx.Response]) -> None:
        self.routes = routes
        self.pins: list[tuple[str, str]] = []
        self.requests: list[httpx.Request] = []

    def factory(self, host: str, ip: str) -> httpx.AsyncBaseTransport:
        self.pins.append((host, ip))
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        route = self.routes[str(request.url)]
        return route(request) if callable(route) else route


def pdf(body: bytes = PDF, **headers: str) -> httpx.Response:
    return httpx.Response(200, content=body, headers={"Content-Type": "application/pdf", **headers})


def redirect(location: str, status: int = 302) -> httpx.Response:
    return httpx.Response(status, headers={"Location": location})


def make(
    tmp_path: Path, upstream: Upstream, resolver: FakeResolver | None = None
) -> tuple[Downloader, FakeResolver]:
    resolver = resolver or FakeResolver()
    downloader = Downloader(resolver, POLICY, tmp_path, transport_factory=upstream.factory)
    return downloader, resolver


def stored(tmp_path: Path, folder: str) -> list[Path]:
    root = tmp_path / folder
    return [p for p in root.rglob("*") if p.is_file()] if root.exists() else []


async def rejected(downloader: Downloader, url: str, **kwargs: Any) -> HttpError:
    with pytest.raises(HttpError) as caught:
        await downloader.download(url, **kwargs)
    return caught.value


# CACHE-1


@pytest.mark.parametrize(
    "address",
    [
        "10.0.0.1",
        "172.16.5.4",
        "192.168.1.1",
        "127.0.0.1",
        "169.254.169.254",
        "0.0.0.0",  # noqa: S104 (an answer to refuse, not a bind)
        "100.64.0.1",
        "224.0.0.1",
        "240.0.0.1",
        "::1",
        "fe80::1",
        "fc00::1",
        "ff02::1",
        "::ffff:10.0.0.1",
        "::",
    ],
)
async def test_rejects_http_private_loopback_linklocal_also_after_redirect(
    tmp_path: Path, address: str
) -> None:
    """@spec CACHE-1: http and non-public addresses are refused, on the first hop and after one."""
    upstream = Upstream(
        {
            "https://arxiv.org/pdf/1": redirect("https://files.arxiv.org/1.pdf"),
            "https://arxiv.org/pdf/2": redirect("http://files.arxiv.org/2.pdf"),
            "https://files.arxiv.org/1.pdf": pdf(),
        }
    )

    downloader, _ = make(tmp_path, upstream, FakeResolver({"arxiv.org": [[address]]}))
    error = await rejected(downloader, "https://arxiv.org/pdf/1")
    assert error.code is ErrorCode.BLOCKED_BY_POLICY
    assert upstream.requests == []

    downloader, _ = make(
        tmp_path, upstream, FakeResolver({"arxiv.org": [[PUBLIC]], "files.arxiv.org": [[address]]})
    )
    error = await rejected(downloader, "https://arxiv.org/pdf/1")
    assert error.code is ErrorCode.BLOCKED_BY_POLICY
    assert [str(r.url) for r in upstream.requests] == ["https://arxiv.org/pdf/1"]

    # One bad address among good ones is enough to refuse the host.
    upstream.requests.clear()
    downloader, _ = make(tmp_path, upstream, FakeResolver({"arxiv.org": [[PUBLIC, address]]}))
    error = await rejected(downloader, "https://arxiv.org/pdf/1")
    assert error.code is ErrorCode.BLOCKED_BY_POLICY
    assert upstream.requests == []

    assert stored(tmp_path, "files") == []
    assert stored(tmp_path, "tmp") == []


async def test_rejects_scheme_host_policy_and_literal_addresses(tmp_path: Path) -> None:
    """@spec CACHE-1: http, hosts outside the policy and private IP literals are refused."""
    upstream = Upstream(
        {
            "https://arxiv.org/pdf/2": redirect("http://files.arxiv.org/2.pdf"),
            "https://arxiv.org/pdf/3": redirect("https://evil.test/3.pdf"),
            "https://arxiv.org/pdf/4": redirect("/relative/4.pdf", status=301),
            "https://arxiv.org/relative/4.pdf": pdf(),
        }
    )
    downloader, resolver = make(tmp_path, upstream)

    for url in (
        "http://arxiv.org/pdf/1",
        "ftp://arxiv.org/pdf/1",
        "https://evil.test/x.pdf",
        "https://arxiv.org/pdf/2",
        "https://arxiv.org/pdf/3",
    ):
        error = await rejected(downloader, url)
        assert error.code is ErrorCode.BLOCKED_BY_POLICY, url

    anywhere = DownloadPolicy(
        media_types=frozenset({"application/pdf"}), max_bytes=10_000, public_any=True
    )
    resolver.calls.clear()
    for url in ("https://127.0.0.1/x.pdf", "https://[::1]/x.pdf", "https://10.1.2.3/x.pdf"):
        error = await rejected(downloader, url, policy=anywhere)
        assert error.code is ErrorCode.BLOCKED_BY_POLICY, url
    assert resolver.calls == []

    # A relative redirect stays on the checked host and is allowed.
    result = await downloader.download("https://arxiv.org/pdf/4")
    assert result.final_url == "https://arxiv.org/relative/4.pdf"


async def test_follows_at_most_five_redirects(tmp_path: Path) -> None:
    """@spec CACHE-1: five redirects are followed by hand; a sixth is refused."""
    routes: dict[str, Handler | httpx.Response] = {
        f"https://arxiv.org/hop/{n}": redirect(f"https://arxiv.org/hop/{n + 1}") for n in range(6)
    }
    routes["https://arxiv.org/hop/5"] = pdf()
    upstream = Upstream(routes)
    downloader, resolver = make(tmp_path, upstream)
    result = await downloader.download("https://arxiv.org/hop/0")
    assert result.final_url == "https://arxiv.org/hop/5"
    assert len(resolver.calls) == 6  # every hop is resolved and checked again

    routes["https://arxiv.org/hop/5"] = redirect("https://arxiv.org/hop/6")
    routes["https://arxiv.org/hop/6"] = pdf()
    error = await rejected(downloader, "https://arxiv.org/hop/0")
    assert error.code is ErrorCode.BLOCKED_BY_POLICY


async def test_dns_rebinding_uses_checked_ip(tmp_path: Path) -> None:
    """@spec CACHE-1: the connection is pinned to the checked IP; a later answer is never used."""
    upstream = Upstream(
        {
            "https://arxiv.org/pdf/1": pdf(),
            "https://arxiv.org/pdf/2": redirect("https://arxiv.org/pdf/1"),
        }
    )
    resolver = FakeResolver({"arxiv.org": [[PUBLIC], ["127.0.0.1"]]})
    downloader, _ = make(tmp_path, upstream, resolver)

    await downloader.download("https://arxiv.org/pdf/1")
    assert resolver.calls == ["arxiv.org"]
    assert upstream.pins == [("arxiv.org", PUBLIC)]
    (request,) = upstream.requests
    assert request.url.host == "arxiv.org"
    assert request.headers["Host"] == "arxiv.org"
    # Uncompressed, so the byte cap counts what is stored.
    assert request.headers["Accept-Encoding"] == "identity"

    # The rebound answer on the next hop is checked like the first one, and refused.
    error = await rejected(downloader, "https://arxiv.org/pdf/2")
    assert error.code is ErrorCode.BLOCKED_BY_POLICY
    assert ("arxiv.org", "127.0.0.1") not in upstream.pins


async def test_pinned_transport_connects_to_ip_with_hostname_and_never_resolves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@spec CACHE-1: PinnedTransport dials the checked IP, keeps the hostname, never resolves."""
    seen: list[bytes] = []

    async def serve(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        seen.append(await reader.readuntil(b"\r\n\r\n"))
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
        await writer.drain()
        writer.close()

    lookups: list[object] = []
    real_getaddrinfo = socket.getaddrinfo

    def recording_getaddrinfo(host: object, *args: Any, **kwargs: Any) -> Any:
        lookups.append(host)
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", recording_getaddrinfo)
    server = await asyncio.start_server(serve, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        transport = PinnedTransport("files.example.org", "127.0.0.1")
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get(f"http://files.example.org:{port}/paper.pdf")
            assert response.text == "ok"
            with pytest.raises(httpx.ConnectError):
                await client.get(f"http://other.example.org:{port}/paper.pdf")
    finally:
        server.close()
        await server.wait_closed()

    (head,) = seen
    assert head.startswith(b"GET /paper.pdf HTTP/1.1\r\n")
    assert f"Host: files.example.org:{port}\r\n".encode() in head
    assert "files.example.org" not in lookups
    assert "other.example.org" not in lookups


class CountingStream(httpx.AsyncByteStream):
    def __init__(self, chunks: int, chunk: bytes) -> None:
        self.chunks = chunks
        self.chunk = chunk
        self.pulled = 0

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for _ in range(self.chunks):
            self.pulled += 1
            yield self.chunk


async def test_rejects_media_type_magic_bytes_and_oversize(tmp_path: Path) -> None:
    """@spec CACHE-1: wrong media types, wrong magic bytes and oversize bodies are refused."""
    streamed = CountingStream(100, b"%PDF-" + b"1" * 995)
    declared = CountingStream(100, b"%PDF-" + b"1" * 995)
    upstream = Upstream(
        {
            "https://arxiv.org/plain": httpx.Response(
                200, content=b"%PDF-1.7", headers={"Content-Type": "text/plain"}
            ),
            "https://arxiv.org/none": httpx.Response(200, content=PDF),
            "https://arxiv.org/fake-pdf": pdf(b"<html>not a pdf</html>"),
            "https://arxiv.org/fake-html": httpx.Response(
                200, content=b"%PDF-1.4", headers={"Content-Type": "text/html"}
            ),
            "https://arxiv.org/empty": pdf(b""),
            "https://arxiv.org/streamed": httpx.Response(
                200, stream=streamed, headers={"Content-Type": "application/pdf"}
            ),
            "https://arxiv.org/declared": httpx.Response(
                200,
                stream=declared,
                headers={"Content-Type": "application/pdf", "Content-Length": "100000"},
            ),
            "https://arxiv.org/missing": httpx.Response(404),
        }
    )
    downloader, _ = make(tmp_path, upstream)

    for path in ("plain", "none", "fake-pdf", "fake-html", "empty"):
        error = await rejected(downloader, f"https://arxiv.org/{path}")
        assert error.code is ErrorCode.BLOCKED_BY_POLICY, path

    error = await rejected(downloader, "https://arxiv.org/streamed")
    assert error.code is ErrorCode.TOO_LARGE
    assert streamed.pulled < streamed.chunks

    error = await rejected(downloader, "https://arxiv.org/declared")
    assert error.code is ErrorCode.TOO_LARGE
    assert declared.pulled == 0

    error = await rejected(downloader, "https://arxiv.org/missing")
    assert error.code is ErrorCode.NOT_FOUND

    assert stored(tmp_path, "files") == []
    assert stored(tmp_path, "tmp") == []


async def test_accepts_html_after_whitespace_and_media_type_parameters(tmp_path: Path) -> None:
    """@spec CACHE-1: HTML may start with whitespace; Content-Type parameters are ignored."""
    upstream = Upstream(
        {
            "https://arxiv.org/page": httpx.Response(
                200, content=HTML, headers={"Content-Type": "Text/HTML; charset=utf-8"}
            ),
            "https://arxiv.org/doc": pdf(**{"Content-Type": "application/pdf; qs=1"}),
        }
    )
    downloader, _ = make(tmp_path, upstream)
    page = await downloader.download("https://arxiv.org/page")
    assert page.media_type == "text/html"
    assert page.storage_path.endswith(".html")
    doc = await downloader.download("https://arxiv.org/doc")
    assert doc.media_type == "application/pdf"


# CACHE-2


async def test_atomic_write_by_sha256_and_full_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@spec CACHE-2: the file is moved atomically to files/<sha[:2]>/<sha>.pdf with provenance."""
    upstream = Upstream(
        {
            "https://arxiv.org/pdf/1": redirect("https://files.arxiv.org/1.pdf", status=301),
            "https://files.arxiv.org/1.pdf": pdf(
                ETag='"abc123"', **{"Last-Modified": "Wed, 21 Oct 2026 07:28:00 GMT"}
            ),
        }
    )
    moves: list[tuple[str, str]] = []
    syncs: list[int] = []
    real_replace, real_fsync = os.replace, os.fsync

    def replace(src: Any, dst: Any) -> None:
        moves.append((str(src), str(dst)))
        real_replace(src, dst)

    def fsync(fd: int) -> None:
        syncs.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr(os, "fsync", fsync)
    downloader, _ = make(
        tmp_path,
        upstream,
        FakeResolver({"arxiv.org": [[PUBLIC]], "files.arxiv.org": [[PUBLIC_2]]}),
    )
    result = await downloader.download("https://arxiv.org/pdf/1")

    digest = hashlib.sha256(PDF).hexdigest()
    target = tmp_path / "files" / digest[:2] / f"{digest}.pdf"
    assert result.sha256 == digest
    assert result.size == len(PDF)
    assert result.media_type == "application/pdf"
    assert result.storage_path == str(target)
    assert result.final_url == "https://files.arxiv.org/1.pdf"
    assert result.http_status == 200
    assert result.etag == '"abc123"'
    assert result.last_modified == "Wed, 21 Oct 2026 07:28:00 GMT"
    assert target.read_bytes() == PDF

    (move,) = moves
    source = Path(move[0])
    assert source.parent == tmp_path / "tmp"
    assert source.suffix == ".part"
    assert len(source.stem) == 26  # a ULID
    assert move[1] == str(target)
    assert syncs, "the file is fsynced before the move"
    assert stored(tmp_path, "tmp") == []
    assert upstream.pins == [("arxiv.org", PUBLIC), ("files.arxiv.org", PUBLIC_2)]


async def test_existing_file_reused(tmp_path: Path) -> None:
    """@spec CACHE-2: a file already stored under its SHA-256 is reused, not rewritten."""
    digest = hashlib.sha256(PDF).hexdigest()
    target = tmp_path / "files" / digest[:2] / f"{digest}.pdf"
    target.parent.mkdir(parents=True)
    target.write_bytes(PDF)
    before = target.stat()

    upstream = Upstream({"https://arxiv.org/pdf/1": pdf()})
    downloader, _ = make(tmp_path, upstream)
    result = await downloader.download("https://arxiv.org/pdf/1")

    after = target.stat()
    assert result.storage_path == str(target)
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)
    assert stored(tmp_path, "tmp") == []
    assert stored(tmp_path, "files") == [target]
