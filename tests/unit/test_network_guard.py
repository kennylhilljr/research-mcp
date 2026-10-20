"""The socket guard in tests/conftest.py and the default deselection of live tests.

Every refusal is checked against CPython's socket audit events. The C socket functions
raise those events just before the system call, so a refusal that leaves no event proves
the guard stopped the call before any I/O. The loopback tests show the recorder does see
the events when a call reaches the OS.
"""

from __future__ import annotations

import socket
import sys
import textwrap
import tomllib
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import tomli_w

REPO = Path(__file__).resolve().parents[2]

# TEST-NET-1 (RFC 5737): never routed, so a guard failure cannot reach a real host.
UNROUTABLE = "192.0.2.1"
PUBLIC_NAME = "example.org"

IO_EVENTS = frozenset(
    {
        "socket.connect",
        "socket.sendto",
        "socket.sendmsg",
        "socket.getaddrinfo",
        "socket.gethostbyname",
        "socket.gethostbyaddr",
    }
)

_recording: list[str] | None = None


def _audit(event: str, args: tuple[Any, ...]) -> None:
    if _recording is not None and event in IO_EVENTS:
        _recording.append(event)


# Audit hooks cannot be removed; this one only records while a test asks it to.
sys.addaudithook(_audit)


@pytest.fixture
def socket_events() -> Iterator[list[str]]:
    global _recording
    _recording = []
    try:
        yield _recording
    finally:
        _recording = None


def _assert_refused_before_io(call: Callable[[], object], events: list[str]) -> None:
    with pytest.raises(RuntimeError, match="network blocked"):
        call()
    assert events == [], f"the guard let {events} reach the OS before refusing"


def test_blocks_connect_before_io(socket_events: list[str]) -> None:
    """AT-PLAT-05: connect and connect_ex to a non-loopback address are refused before I/O."""
    for family, address in (
        (socket.AF_INET, (UNROUTABLE, 80)),
        (socket.AF_INET6, ("2001:db8::1", 80, 0, 0)),
        (socket.AF_INET6, (f"::ffff:{UNROUTABLE}", 80, 0, 0)),
    ):
        try:
            sock = socket.socket(family, socket.SOCK_STREAM)
        except OSError:
            continue  # no IPv6 on this host
        with sock:
            sock.settimeout(0.5)
            _assert_refused_before_io(lambda s=sock, a=address: s.connect(a), socket_events)
            _assert_refused_before_io(lambda s=sock, a=address: s.connect_ex(a), socket_events)


def test_blocks_create_connection_before_io(socket_events: list[str]) -> None:
    """AT-PLAT-05: socket.create_connection to a non-loopback host is refused before I/O."""
    for host in (UNROUTABLE, PUBLIC_NAME):
        _assert_refused_before_io(
            lambda h=host: socket.create_connection((h, 80), timeout=0.5), socket_events
        )


def test_blocks_datagrams_before_io(socket_events: list[str]) -> None:
    """AT-PLAT-05: sendto and sendmsg with a non-loopback address are refused before I/O."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        target = (UNROUTABLE, 53)
        _assert_refused_before_io(lambda: sock.sendto(b"x", target), socket_events)
        _assert_refused_before_io(lambda: sock.sendto(b"x", 0, target), socket_events)
        _assert_refused_before_io(lambda: sock.sendmsg([b"x"], [], 0, target), socket_events)


@pytest.mark.parametrize("name", ["getaddrinfo", "gethostbyname", "gethostbyname_ex"])
def test_blocks_name_lookup_before_io(name: str, socket_events: list[str]) -> None:
    """AT-PLAT-05: resolving a public host name is refused before any lookup."""
    lookup = getattr(socket, name)
    args = (PUBLIC_NAME, 443) if name == "getaddrinfo" else (PUBLIC_NAME,)
    _assert_refused_before_io(lambda: lookup(*args), socket_events)


def test_blocks_reverse_lookup_before_io(socket_events: list[str]) -> None:
    """AT-PLAT-05: gethostbyaddr for a non-loopback name or address is refused before I/O."""
    for host in (PUBLIC_NAME, UNROUTABLE):
        _assert_refused_before_io(lambda h=host: socket.gethostbyaddr(h), socket_events)


# Names that start like loopback but that the OS would hand to the resolver whole.
LOOPBACK_LOOKALIKES = (f"127.0.0.1%{PUBLIC_NAME}", f"::1%{PUBLIC_NAME}", "localhost.")


@pytest.mark.parametrize("host", LOOPBACK_LOOKALIKES)
def test_blocks_loopback_lookalikes_before_io(host: str, socket_events: list[str]) -> None:
    """AT-PLAT-05: a loopback prefix with a scope suffix or trailing dot is refused before I/O."""
    _assert_refused_before_io(lambda: socket.getaddrinfo(host, 443), socket_events)
    _assert_refused_before_io(lambda: socket.gethostbyname(host), socket_events)
    _assert_refused_before_io(lambda: socket.gethostbyname_ex(host), socket_events)
    _assert_refused_before_io(lambda: socket.gethostbyaddr(host), socket_events)
    _assert_refused_before_io(
        lambda: socket.create_connection((host, 80), timeout=0.5), socket_events
    )
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        _assert_refused_before_io(lambda: sock.connect((host, 80)), socket_events)
        _assert_refused_before_io(lambda: sock.connect_ex((host, 80)), socket_events)


def _blocked(error: BaseException) -> bool:
    if isinstance(error, BaseExceptionGroup):
        return any(_blocked(inner) for inner in error.exceptions)
    return isinstance(error, RuntimeError) and "network blocked" in str(error)


async def test_blocks_async_http_client(socket_events: list[str]) -> None:
    """AT-PLAT-05: the guard also stops httpx on the event loop, before any I/O."""
    async with httpx.AsyncClient(timeout=0.5) as client:
        # anyio may wrap the guard error in an exception group.
        with pytest.raises((RuntimeError, BaseExceptionGroup)) as info:
            await client.get(f"http://{UNROUTABLE}/")
    assert _blocked(info.value)
    assert "socket.connect" not in socket_events


def test_passes_loopback_through(socket_events: list[str]) -> None:
    """AT-PLAT-05: loopback connects and lookups reach the OS instead of being refused."""
    for host in ("127.0.0.1", "localhost"):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            # Port 9 (discard) normally refuses, and a sandbox may deny the connect. Either
            # way connect_ex returns the OS error code; the guard would raise instead.
            assert isinstance(sock.connect_ex((host, 9)), int)
    assert socket_events.count("socket.connect") == 2
    assert socket.getaddrinfo("localhost", 80)
    assert "socket.getaddrinfo" in socket_events


def test_allows_loopback_server() -> None:
    """AT-PLAT-05: loopback connections stay open for local test servers."""
    try:
        server = socket.create_server(("127.0.0.1", 0))
    except PermissionError:
        pytest.skip("this sandbox denies binding to 127.0.0.1")
    with server:
        port = server.getsockname()[1]
        with socket.create_connection(("localhost", port), timeout=2) as client:
            peer, _ = server.accept()
            with peer:
                client.sendall(b"ok")
                assert peer.recv(2) == b"ok"


def _copy_pytest_setup(pytester: pytest.Pytester, **files: str) -> None:
    with (REPO / "pyproject.toml").open("rb") as handle:
        ini_options = tomllib.load(handle)["tool"]["pytest"]["ini_options"]
    pytester.makefile(
        ".toml", pyproject=tomli_w.dumps({"tool": {"pytest": {"ini_options": ini_options}}})
    )
    pytester.makeconftest((REPO / "tests" / "conftest.py").read_text(encoding="utf-8"))
    pytester.makepyfile(**{name: textwrap.dedent(body) for name, body in files.items()})


MARKER_TESTS = f"""
import contextlib
import socket

import pytest


def _udp_connect():
    # A UDP connect only sets the default peer; it sends nothing.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(("{UNROUTABLE}", 9))


@pytest.mark.live
def test_live():
    with contextlib.suppress(OSError):
        _udp_connect()


def test_offline():
    with pytest.raises(RuntimeError, match="network blocked"):
        _udp_connect()
"""


def test_live_tests_deselected_by_default(pytester: pytest.Pytester) -> None:
    """AT-PLAT-05: live tests are deselected by default; the guard covers the rest."""
    _copy_pytest_setup(pytester, test_markers=MARKER_TESTS)
    result = pytester.runpytest_subprocess("-v")
    result.assert_outcomes(passed=1, deselected=1)
    result.stdout.fnmatch_lines(["*test_offline PASSED*"])


def test_live_tests_run_unguarded_when_selected(pytester: pytest.Pytester) -> None:
    """AT-PLAT-05: with -m live, live tests run without the socket guard."""
    _copy_pytest_setup(pytester, test_markers=MARKER_TESTS)
    result = pytester.runpytest_subprocess("-m", "live", "-v")
    result.assert_outcomes(passed=1, deselected=1)
    result.stdout.fnmatch_lines(["*test_live PASSED*"])


def test_guard_covers_session_fixtures(pytester: pytest.Pytester) -> None:
    """AT-PLAT-05: a session-scoped fixture set up for an offline test is guarded."""
    _copy_pytest_setup(
        pytester,
        test_session=f"""
        import socket

        import pytest


        @pytest.fixture(scope="session")
        def remote():
            return socket.gethostbyname("{PUBLIC_NAME}")


        def test_uses_remote(remote):
            pass
        """,
    )
    result = pytester.runpytest_subprocess("-v")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines([f"*network blocked in tests: lookup of '{PUBLIC_NAME}'*"])


def test_guard_covers_collection(pytester: pytest.Pytester) -> None:
    """AT-PLAT-05: network calls made while a test module is imported are guarded."""
    _copy_pytest_setup(
        pytester,
        test_import_time=f"""
        import socket

        ADDRESS = socket.getaddrinfo("{PUBLIC_NAME}", 443)


        def test_nothing():
            pass
        """,
    )
    result = pytester.runpytest_subprocess("-v")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines([f"*network blocked in tests: lookup of '{PUBLIC_NAME}'*"])
