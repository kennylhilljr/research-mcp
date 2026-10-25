"""`research-mcp doctor`: installation checks that run without the daemon.

LLD-health-v2 2.3 and 5.9. M0 ships four checks: ``daemon_alive``, ``keychain_readable``,
``contact_email`` and ``schema_versions``. Credential, probe, archive, disk and backup
checks arrive with their components in M1 and M2 (HLTH-FR-40). A settings validation
error does not abort the run; it becomes the ``contact_email`` or ``settings`` check.
"""

from __future__ import annotations

import getpass
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import anyio
import httpx
from pydantic import ValidationError

from research_mcp.platform.secrets import (
    KeychainProvider,
    SecretProvider,
    SecretRef,
    SecretState,
)
from research_mcp.platform.stores import (
    CACHE_MIGRATIONS,
    STATE_MIGRATIONS,
    Migrator,
    read_schema_version,
)
from research_mcp.settings import Settings

CheckStatus = Literal["ok", "warning", "install_critical"]

HEALTHZ_TIMEOUT_S = 3.0


@dataclass(frozen=True)
class CheckResult:
    """One row of a doctor run: ``{name, status, code, detail, fix}`` (LLD-health-v2 5.9)."""

    name: str
    status: CheckStatus
    code: str | None
    detail: str
    fix: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "code": self.code,
            "detail": self.detail,
            "fix": self.fix,
        }


@dataclass(frozen=True)
class DoctorReport:
    checks: list[CheckResult]

    @property
    def exit_code(self) -> int:
        """0 when no check is ``install_critical``, otherwise 1 (LLD-health-v2 5.9)."""
        return 1 if any(c.status == "install_critical" for c in self.checks) else 0

    def to_json(self) -> dict[str, Any]:
        return {"exit_code": self.exit_code, "checks": [c.to_json() for c in self.checks]}


def _settings_check(exc: ValidationError) -> CheckResult:
    """A validation error becomes the ``contact_email`` or ``settings`` check, not an abort."""
    errors = exc.errors(include_url=False, include_input=False, include_context=False)
    name = (
        "contact_email"
        if any(tuple(e["loc"][:2]) == ("contact", "email") for e in errors)
        else "settings"
    )
    detail = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in errors)
    return CheckResult(
        name,
        "install_critical",
        "invalid_settings",
        detail,
        "Fix config.toml or the RESEARCH_MCP_ environment variables.",
    )


async def _daemon_alive(
    settings: Settings, transport: httpx.AsyncBaseTransport | None
) -> CheckResult:
    """``GET /healthz`` answers within 3 s (LLD-health-v2 5.9)."""
    url = f"http://{settings.server.host}:{settings.server.port}/healthz"
    ok = False
    try:
        async with httpx.AsyncClient(transport=transport, timeout=HEALTHZ_TIMEOUT_S) as client:
            response = await client.get(url)
        ok = response.status_code == 200
    except httpx.HTTPError:
        ok = False
    if ok:
        return CheckResult("daemon_alive", "ok", None, "The daemon answered /healthz.")
    return CheckResult(
        "daemon_alive",
        "install_critical",
        "daemon_unreachable",
        "The daemon did not answer /healthz within 3 seconds.",
        "Run `research-mcp install`, or `launchctl kickstart gui/$UID/local.research-mcpd`.",
    )


def _keychain_readable(settings: Settings, provider: SecretProvider) -> CheckResult:
    """The Keychain can be read and is not locked; at most a ``warning`` (LLD-health-v2 5.9)."""
    ref = SecretRef.parse(settings.server.token)
    state, _ = provider.get(ref)
    if state is SecretState.LOCKED:
        return CheckResult(
            "keychain_readable",
            "warning",
            "keychain_locked",
            "The login Keychain is locked.",
            "Unlock the login Keychain in Keychain Access.",
        )
    if state is SecretState.ERROR:
        return CheckResult(
            "keychain_readable",
            "warning",
            "keychain_error",
            "The Keychain could not be read.",
            "Unlock the login Keychain in Keychain Access.",
        )
    return CheckResult("keychain_readable", "ok", None, "The Keychain answered.")


def _contact_email(settings: Settings) -> CheckResult:
    """Unset is a ``warning``; a placeholder never reaches here (it fails settings validation)."""
    if settings.contact.email is None:
        return CheckResult(
            "contact_email",
            "warning",
            "contact_email_unset",
            "No contact email is configured.",
            "Set contact.email in config.toml.",
        )
    return CheckResult("contact_email", "ok", None, "A contact email is configured.")


def _db_unreadable(label: str) -> CheckResult:
    return CheckResult(
        "schema_versions",
        "install_critical",
        "db_unreadable",
        f"{label} could not be opened.",
        "Restore a backup, or reinstall.",
    )


async def _schema_check(label: str, path: Path, migrations: Path) -> CheckResult | None:
    """``None`` when ``label`` is at the current schema; a result otherwise.

    The store reads the version read-only with no migration; a corrupt file raises
    ``sqlite3.DatabaseError`` from the first ``PRAGMA`` and becomes ``db_unreadable``.
    """
    if not await anyio.to_thread.run_sync(path.exists):
        return CheckResult(
            "schema_versions",
            "install_critical",
            "db_unreadable",
            f"{label} does not exist yet.",
            "Run `research-mcp install` and start the daemon.",
        )
    try:
        version = await read_schema_version(path)
    except sqlite3.Error:
        return _db_unreadable(label)
    latest = Migrator(migrations).latest
    if version != latest:
        return CheckResult(
            "schema_versions",
            "install_critical",
            "migration_failed",
            f"{label} is at schema {version}, expected {latest}.",
            "Run `research-mcp upgrade`, or restart the daemon.",
        )
    return None


async def _schema_versions(settings: Settings) -> CheckResult:
    """``state.db`` and ``cache.db`` open for reading, at the newest migration (5.9)."""
    paths = settings.paths
    databases = (
        ("state.db", Path(paths.state_dir) / "state.db", STATE_MIGRATIONS),
        ("cache.db", Path(paths.data_dir) / "cache.db", CACHE_MIGRATIONS),
    )
    for label, path, migrations in databases:
        result = await _schema_check(label, path, migrations)
        if result is not None:
            return result
    return CheckResult(
        "schema_versions", "ok", None, "state.db and cache.db are at the current schema."
    )


class DoctorRunner:
    """Runs the M0 doctor checks without the daemon (LLD-health-v2 5.9).

    ``settings``, ``provider`` and ``transport`` are the test seams; omitted, ``run``
    builds the real ``Settings`` and a real ``KeychainProvider``, and probes the real
    network for ``daemon_alive``.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        provider: SecretProvider | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._provider = provider
        self._transport = transport

    # @spec HLTH-40
    async def run(self, *, liveness: bool = False, quick: bool = False) -> DoctorReport:
        """``--liveness`` runs only ``daemon_alive`` and ``keychain_readable``. ``--quick``
        skips metered probes; M0 has none, so it changes nothing yet (HLTH-FR-41 arrives
        in M1)."""
        del quick
        try:
            settings = self._settings or Settings()
        except ValidationError as exc:
            return DoctorReport([_settings_check(exc)])

        provider = self._provider or KeychainProvider(getpass.getuser())
        checks = [
            await _daemon_alive(settings, self._transport),
            _keychain_readable(settings, provider),
        ]
        if liveness:
            return DoctorReport(checks)
        checks.append(_contact_email(settings))
        checks.append(await _schema_versions(settings))
        return DoctorReport(checks)
