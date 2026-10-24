"""``research-mcpd``: settings, logging, ``build_app``, uvicorn on loopback (LLD-platform-v2 5.10).

Start order: (1) load ``Settings``, the only place the environment is read; a validation
error is printed without the rejected value and the process exits 2; (2) create the
directories; (3) configure logging and replace ``sys.stderr`` with ``RedactingStream``;
(4) assert the host is loopback; (5, 6) ``build_app``, whose lifespan loads the secrets,
opens the stores and runs the migrations; (7) serve with uvicorn beside the ``SIGHUP``
receiver, which reloads credentials.
"""

from __future__ import annotations

import ipaddress
import logging
import signal
import sys
from typing import Any

import anyio
from pydantic import ValidationError

from research_mcp.app import build_app
from research_mcp.platform.logging import configure_logging
from research_mcp.platform.redact import RedactingStream
from research_mcp.settings import Settings

_log = logging.getLogger(__name__)

EXIT_CONFIG = 2


class NotLoopbackError(RuntimeError):
    """The daemon was asked to bind an address that is not loopback."""


# @spec PLAT-71
def assert_loopback(host: str) -> None:
    """Refuse any host that is not a literal loopback IP address (SEC-INV-1)."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise NotLoopbackError("server.host must be a loopback IP address") from None
    if not address.is_loopback or "%" in host:  # a scope suffix names an interface
        raise NotLoopbackError("server.host must be a loopback IP address")


async def reload_on_sighup(app: Any, ready: anyio.Event | None = None) -> None:
    """Reload credentials on each ``SIGHUP``; a failed reload never stops the daemon."""
    with anyio.open_signal_receiver(signal.SIGHUP) as signals:
        if ready is not None:
            ready.set()
        async for _ in signals:
            try:
                await app.state.reload_credentials()
            except Exception:  # noqa: BLE001 - logged without exception text (5.10)
                _log.warning("reload_credentials.failed", extra={"operation": "reload"})


async def serve(app: Any, settings: Settings) -> None:
    """Run uvicorn and the ``SIGHUP`` receiver in one task group."""
    import uvicorn

    host = settings.server.host
    assert_loopback(host)  # again, immediately before binding: settings may be unvalidated
    config = uvicorn.Config(
        app,
        host=host,
        port=settings.server.port,
        access_log=False,
        log_config=None,
        lifespan="on",
    )
    server = uvicorn.Server(config)
    async with anyio.create_task_group() as tasks:
        tasks.start_soon(reload_on_sighup, app)
        await server.serve()
        tasks.cancel_scope.cancel()


def _print_invalid(exc: ValidationError) -> None:
    # Settings errors carry no input; only the key path and the fixed message are printed.
    for error in exc.errors(include_url=False, include_input=False, include_context=False):
        where = ".".join(str(part) for part in error["loc"])
        print(f"research-mcpd: invalid setting {where}: {error['msg']}", file=sys.stderr)


# @spec SEC-24
def main() -> int:
    try:
        settings = Settings()
    except ValidationError as exc:
        _print_invalid(exc)
        return EXIT_CONFIG
    settings.paths.create_directories()
    redactor = configure_logging(settings)
    sys.stderr = RedactingStream(sys.stderr, redactor)
    try:
        assert_loopback(settings.server.host)
    except NotLoopbackError as exc:
        print(f"research-mcpd: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    app = build_app(settings, redactor=redactor)
    anyio.run(serve, app, settings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
