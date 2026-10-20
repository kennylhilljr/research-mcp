"""Shared pytest setup: every test not marked ``live`` runs with the network blocked.

The guard is installed in ``pytest_configure``, before collection, and stays installed for
the whole session, so module level code, fixtures of every scope and every test share it.
It is lifted only while a test marked ``live`` runs. Live tests are deselected by default
through ``-m 'not live'`` in pyproject.toml and run only with ``pytest -m live``.

Each guarded call checks its address or host name first and raises
``NetworkBlockedError`` before the real function runs, so a refused call does no I/O.
Loopback addresses, ``localhost`` and Unix sockets stay open for local test servers.

The guard patches this process only. It stops accidents in Python code; it is not a
sandbox, and child processes started by a test do not inherit it.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Generator
from typing import Any

import pytest

pytest_plugins = ["pytester"]

LOOKUPS = ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr")


class NetworkBlockedError(RuntimeError):
    """A test that is not marked live tried to reach a non-loopback host."""


_live_running = False
_originals: dict[tuple[object, str], Any] = {}


def _is_loopback_host(host: object) -> bool:
    if host is None:  # getaddrinfo(None, ...) asks for a local address
        return True
    if isinstance(host, bytes | bytearray):
        host = bytes(host).decode("ascii", "replace")
    if not isinstance(host, str):
        return False
    if host.lower().rstrip(".") == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped.is_loopback
    return address.is_loopback


def _check_address(family: int, address: Any) -> None:
    if _live_running or family == getattr(socket, "AF_UNIX", None):
        return
    host = address[0] if isinstance(address, tuple) and address else address
    if not _is_loopback_host(host):
        raise NetworkBlockedError(
            f"network blocked in tests: {address!r}; mark the test live to allow it"
        )


def _check_lookup(host: object) -> None:
    if not _live_running and not _is_loopback_host(host):
        raise NetworkBlockedError(
            f"network blocked in tests: lookup of {host!r}; mark the test live to allow it"
        )


def _guard_lookup(real: Callable[..., Any]) -> Callable[..., Any]:
    def lookup(host: Any, *args: Any, **kwargs: Any) -> Any:
        _check_lookup(host)
        return real(host, *args, **kwargs)

    return lookup


def _install_guard() -> None:
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_sendto = socket.socket.sendto
    real_sendmsg = socket.socket.sendmsg
    real_create_connection = socket.create_connection

    def connect(self: socket.socket, address: Any) -> None:
        _check_address(self.family, address)
        real_connect(self, address)

    def connect_ex(self: socket.socket, address: Any) -> int:
        _check_address(self.family, address)
        return real_connect_ex(self, address)

    def sendto(self: socket.socket, data: Any, *args: Any) -> int:
        if args:  # sendto(data, address) or sendto(data, flags, address)
            _check_address(self.family, args[-1])
        return real_sendto(self, data, *args)

    def sendmsg(self: socket.socket, buffers: Any, *args: Any) -> int:
        if len(args) >= 3 and args[2] is not None:  # (ancdata, flags, address)
            _check_address(self.family, args[2])
        return real_sendmsg(self, buffers, *args)

    def create_connection(address: Any, *args: Any, **kwargs: Any) -> socket.socket:
        _check_lookup(address[0] if isinstance(address, tuple) and address else address)
        return real_create_connection(address, *args, **kwargs)

    patches: dict[tuple[object, str], Any] = {
        (socket.socket, "connect"): connect,
        (socket.socket, "connect_ex"): connect_ex,
        (socket.socket, "sendto"): sendto,
        (socket.socket, "sendmsg"): sendmsg,
        (socket, "create_connection"): create_connection,
    }
    for name in LOOKUPS:
        patches[(socket, name)] = _guard_lookup(getattr(socket, name))
    for (owner, name), replacement in patches.items():
        _originals[(owner, name)] = getattr(owner, name)
        setattr(owner, name, replacement)


def _remove_guard() -> None:
    for (owner, name), original in _originals.items():
        setattr(owner, name, original)
    _originals.clear()


def pytest_configure(config: pytest.Config) -> None:
    _install_guard()


def pytest_unconfigure(config: pytest.Config) -> None:
    _remove_guard()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(
    item: pytest.Item, nextitem: pytest.Item | None
) -> Generator[None, object, object]:
    global _live_running
    _live_running = item.get_closest_marker("live") is not None
    try:
        return (yield)
    finally:
        _live_running = False
