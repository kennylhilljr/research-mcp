"""``research-mcp``: the platform CLI (LLD-platform-v2 2.4; SPEC-v5 12).

``research-mcp = research_mcp.cli:main``; ``research-mcpd = research_mcp.daemon:main`` is
its own entry point. ``install`` and ``secrets rotate-token`` are fully built here
(PLAT-81, PLAT-82, PLAT-83, SEC-30); ``doctor`` wraps ``services/doctor.py`` (HLTH-40).
``ui``, ``sources``, ``config``, ``upgrade`` and the rest of ``secrets``/``import-legacy``
are named so ``--help`` lists the full command table (PLAT-80); their components ship in
later milestones.
"""

from __future__ import annotations

import argparse
import getpass
import json
import re
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import anyio

from research_mcp import daemon, shim
from research_mcp.platform import auth
from research_mcp.platform.secrets import (
    KeychainProvider,
    SecretProvider,
    SecretRef,
    SecretState,
)
from research_mcp.services import doctor as doctor_service
from research_mcp.settings import Settings
from research_mcp.shim import DAEMON_LABEL, LaunchctlPort, SystemLaunchctl

DOCTOR_LABEL = "local.research-mcp-doctor"
WATCHDOG_LABEL = "local.research-mcp-watchdog"
LABELS = (DAEMON_LABEL, DOCTOR_LABEL, WATCHDOG_LABEL)

TEMPLATES_DIR = Path(__file__).with_name("packaging") / "launchd"
_PLACEHOLDER = re.compile(r"__[A-Z0-9_]+__")


class InstallError(RuntimeError):
    """Install cannot finish safely; the message says why and holds no secret."""


def _template(label: str) -> str:
    return (TEMPLATES_DIR / f"{label}.plist.template").read_text(encoding="utf-8")


def default_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def default_venv_root() -> Path:
    """The venv's root (``sys.prefix``).

    ``sys.executable`` is not safe for this: a ``uv``-managed venv's ``bin/python`` is a
    symlink to a shared base interpreter outside the venv, so resolving it walks past
    ``<venv>/bin/research-mcp`` entirely. ``sys.prefix`` is always the venv root.
    """
    return Path(sys.prefix)


def render_plist(text: str, *, venv_root: Path, logs: Path, home: Path | None = None) -> str:
    """Fill ``__VENV__``, ``__LOGS__`` and ``__HOME__``; raise if any ``__...__`` is left
    unfilled (PLAT-81; LLD-platform-v2 2.5)."""
    rendered = (
        text.replace("__VENV__", str(venv_root))
        .replace("__LOGS__", str(logs))
        .replace("__HOME__", str(home or Path.home()))
    )
    left = _PLACEHOLDER.search(rendered)
    if left is not None:
        raise ValueError(f"unfilled placeholder in plist template: {left.group()}")
    return rendered


# @spec PLAT-81, PLAT-83, SEC-24
def install(
    settings: Settings,
    *,
    provider: SecretProvider,
    agents_dir: Path | None = None,
    venv_root: Path | None = None,
) -> list[Path]:
    """Render the three launchd plists and generate ``DAEMON_TOKEN`` if it is absent.

    Writes nothing secret: the token lives only in the Keychain, never in a plist. Only a
    ``missing`` token is minted; a locked or unreadable Keychain raises ``InstallError``
    instead, because minting then would silently replace a valid token and break every
    configured shim.
    """
    settings.paths.create_directories()
    resolved_venv = venv_root or default_venv_root()
    resolved_agents_dir = agents_dir or default_agents_dir()
    resolved_agents_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    written: list[Path] = []
    for label in LABELS:
        text = render_plist(_template(label), venv_root=resolved_venv, logs=settings.paths.log_dir)
        path = resolved_agents_dir / f"{label}.plist"
        path.write_text(text, encoding="utf-8")
        path.chmod(0o600)
        written.append(path)

    ref = SecretRef.parse(settings.server.token)
    state, _ = provider.get(ref)
    if state is SecretState.MISSING:
        provider.set(ref, auth.mint_token())  # @spec SEC-30
    elif state is not SecretState.OK:
        raise InstallError(
            f"DAEMON_TOKEN could not be read from the Keychain ({state}); unlock the login "
            "Keychain and run `research-mcp install` again."
        )
    return written


async def load_jobs(launchctl: LaunchctlPort, plists: list[Path]) -> None:
    """Load each plist with launchd; a job already loaded is bootout first (idempotent)."""
    for plist in plists:
        label = plist.stem
        if await launchctl.is_loaded(label):
            await launchctl.bootout(label)
        await launchctl.bootstrap(plist)


# @spec PLAT-82
def client_config_json(venv_root: Path) -> str:
    """The client config: ``research-mcp stdio`` entries only, no secret (PLAT-82)."""
    config = {
        "mcpServers": {
            "research": {
                "command": str(venv_root / "bin" / "research-mcp"),
                "args": ["stdio"],
            }
        }
    }
    return json.dumps(config, indent=2)


# @spec PLAT-83, SEC-30
async def rotate_token(
    settings: Settings, provider: SecretProvider, launchctl: LaunchctlPort
) -> int:
    """Mint a new ``DAEMON_TOKEN``, store it, and signal a running daemon to reload it.

    The only rotation path (no UI action, no MCP tool). If the daemon is not loaded, the
    signal is skipped; the next start reads the new token (LLD-platform-v2 4.5).
    """
    ref = SecretRef.parse(settings.server.token)
    provider.set(ref, auth.mint_token())
    if await launchctl.is_loaded(DAEMON_LABEL):
        await launchctl.kill("SIGHUP", DAEMON_LABEL)
    _, secret = provider.get(ref)
    fingerprint = "" if secret is None else secret.fingerprint
    print(f"DAEMON_TOKEN rotated (fingerprint {fingerprint})")
    return 0


def _print_doctor_report(report: doctor_service.DoctorReport, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report.to_json()))
        return
    for check in report.checks:
        line = f"{check.name}: {check.status}"
        if check.code:
            line += f" ({check.code})"
        print(line)
        print(f"  {check.detail}")
        if check.fix:
            print(f"  fix: {check.fix}")


def _cmd_doctor(args: argparse.Namespace) -> int:
    async def run() -> doctor_service.DoctorReport:
        return await doctor_service.DoctorRunner().run(liveness=args.liveness, quick=args.quick)

    report = anyio.run(run)
    _print_doctor_report(report, as_json=args.json)
    if args.notify:
        # HLTH-41 (the notification side of --notify) ships with the health component in M2.
        print("research-mcp doctor --notify: not yet available in M0", file=sys.stderr)
    return report.exit_code


def _cmd_install(args: argparse.Namespace) -> int:
    settings = Settings()
    provider = KeychainProvider(getpass.getuser())
    launchctl = SystemLaunchctl()
    try:
        written = install(settings, provider=provider)
    except InstallError as exc:
        print(f"research-mcp install: {exc}", file=sys.stderr)
        return 1
    anyio.run(load_jobs, launchctl, written)
    if args.print_client_config:
        print(client_config_json(default_venv_root()))
    return 0


def _cmd_secrets(args: argparse.Namespace) -> int:
    if args.secrets_command == "rotate-token":
        settings = Settings()
        provider = KeychainProvider(getpass.getuser())
        return anyio.run(rotate_token, settings, provider, SystemLaunchctl())
    print(f"research-mcp secrets {args.secrets_command}: not yet available in M0", file=sys.stderr)
    return 2


def _cmd_serve(_args: argparse.Namespace) -> int:
    return daemon.main()


def _cmd_stdio(_args: argparse.Namespace) -> int:
    return shim.main(Settings())


def _unavailable(name: str) -> Callable[[argparse.Namespace], int]:
    def handler(_args: argparse.Namespace) -> int:
        print(f"research-mcp {name}: not yet available in M0", file=sys.stderr)
        return 2

    return handler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research-mcp")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("serve", help="Run the daemon in the foreground.")
    sub.add_parser("stdio", help="The stdio shim for MCP clients.")

    doctor_p = sub.add_parser("doctor", help="Run health checks.")
    doctor_p.add_argument("--json", action="store_true")
    doctor_p.add_argument("--notify", action="store_true")
    doctor_p.add_argument("--quick", action="store_true")
    doctor_p.add_argument("--liveness", action="store_true")

    ui_p = sub.add_parser("ui", help="Open the UI with a one-time login.")
    ui_p.add_argument("--path")

    sources_p = sub.add_parser("sources", help="Source inventory and live checks.")
    sources_sub = sources_p.add_subparsers(dest="sources_command")
    check_p = sources_sub.add_parser("check")
    check_p.add_argument("--live", action="store_true")
    check_p.add_argument("--id")
    check_p.add_argument("--refresh-fixtures", action="store_true")

    config_p = sub.add_parser("config", help="Read or change config.")
    config_sub = config_p.add_subparsers(dest="config_command")
    get_p = config_sub.add_parser("get")
    get_p.add_argument("key")
    set_p = config_sub.add_parser("set")
    set_p.add_argument("key")
    set_p.add_argument("value", nargs="?")

    install_p = sub.add_parser("install", help="Install the launchd jobs and print client config.")
    install_p.add_argument("--print-client-config", action="store_true")

    sub.add_parser("upgrade", help="Upgrade with rollback.")

    secrets_p = sub.add_parser("secrets", help="Manage Keychain items.")
    secrets_sub = secrets_p.add_subparsers(dest="secrets_command", required=True)
    secrets_sub.add_parser("list")
    import_p = secrets_sub.add_parser("import")
    import_p.add_argument("--dry-run", action="store_true")
    secrets_sub.add_parser("scrub-client-configs")
    secrets_sub.add_parser("rotate-token")

    import_legacy_p = sub.add_parser("import-legacy", help="Import the v1 corpus.")
    import_legacy_p.add_argument("path")
    import_legacy_p.add_argument("--dry-run", action="store_true")
    import_legacy_p.add_argument("--mode")

    return parser


_HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "serve": _cmd_serve,
    "stdio": _cmd_stdio,
    "doctor": _cmd_doctor,
    "ui": _unavailable("ui"),
    "sources": _unavailable("sources"),
    "config": _unavailable("config"),
    "install": _cmd_install,
    "upgrade": _unavailable("upgrade"),
    "secrets": _cmd_secrets,
    "import-legacy": _unavailable("import-legacy"),
}


# @spec PLAT-80
def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return _HANDLERS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
