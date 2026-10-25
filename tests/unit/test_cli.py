"""The CLI's command table and the doctor skeleton (LLD-platform-v2 2.4; LLD-health-v2 5.9)."""

from __future__ import annotations

import importlib.util
import json
import re
import sqlite3
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import anyio
import httpx
import pytest
from pydantic import ValidationError

from research_mcp import cli
from research_mcp.app import build_app
from research_mcp.platform.secrets import FakeProvider
from research_mcp.services import doctor
from research_mcp.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]


class OfflineSettings(Settings):
    """Settings built only from keyword arguments: no real config.toml or environment."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **_rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


def offline_settings(tmp_path: Path, **overrides: Any) -> Settings:
    settings = OfflineSettings(
        paths={
            "state_dir": tmp_path / "state",
            "data_dir": tmp_path / "state" / "cache",
            "model_cache_dir": tmp_path / "models",
            "log_dir": tmp_path / "logs",
        },
        **overrides,
    )
    settings.paths.create_directories()
    return settings


def _fail(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused", request=request)


def _load_gen_inventory() -> ModuleType:
    """`tools/gen_inventory.py` is a script, not a package; load it by its file path."""
    path = REPO_ROOT / "tools" / "gen_inventory.py"
    spec = importlib.util.spec_from_file_location("gen_inventory", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_help_lists_every_platform_command(capsys: pytest.CaptureFixture[str]) -> None:
    """@spec PLAT-80: `research-mcp --help` lists the ten platform commands."""
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    # The subcommand list argparse prints, `{serve,stdio,...}`, is matched by whole name,
    # so a help string that mentions "config" cannot stand in for a missing command.
    choices = re.search(r"\{([a-z,-]+)\}", out)
    assert choices is not None
    listed = set(choices.group(1).split(","))
    for name in (
        "serve",
        "stdio",
        "doctor",
        "ui",
        "sources",
        "config",
        "install",
        "upgrade",
        "secrets",
        "import-legacy",
    ):
        assert name in listed
        assert re.search(rf"^\s+{re.escape(name)}\s", out, re.MULTILINE)


async def test_doctor_runs_four_checks_with_fakes(tmp_path: Path) -> None:
    """@spec HLTH-40: with fakes, doctor runs daemon_alive, keychain_readable, contact_email
    and schema_versions, and exits 0 when every check passes."""
    settings = offline_settings(tmp_path, contact={"email": "owner@example.net"})
    app = build_app(settings, secrets=FakeProvider({"DAEMON_TOKEN": "tok"}), adapters=[])

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        runner = doctor.DoctorRunner(
            settings, provider=FakeProvider({"DAEMON_TOKEN": "tok"}), transport=transport
        )
        report = await runner.run()

    assert [c.name for c in report.checks] == [
        "daemon_alive",
        "keychain_readable",
        "contact_email",
        "schema_versions",
    ]
    assert all(c.status == "ok" for c in report.checks)
    assert report.exit_code == 0


async def test_doctor_liveness_runs_only_two_checks(tmp_path: Path) -> None:
    """@spec HLTH-40: --liveness runs only daemon_alive and keychain_readable, and a dead
    daemon is reported install_critical."""
    settings = offline_settings(tmp_path)

    runner = doctor.DoctorRunner(
        settings, provider=FakeProvider({}), transport=httpx.MockTransport(_fail)
    )
    report = await runner.run(liveness=True)

    assert [c.name for c in report.checks] == ["daemon_alive", "keychain_readable"]
    assert report.checks[0].status == "install_critical"
    assert report.checks[1].status == "ok"
    assert report.exit_code == 1


async def test_doctor_json_output_is_machine_readable(tmp_path: Path) -> None:
    """@spec HLTH-40: --json produces a report that round-trips through json.dumps/loads."""
    settings = offline_settings(tmp_path)

    runner = doctor.DoctorRunner(
        settings, provider=FakeProvider({}), transport=httpx.MockTransport(_fail)
    )
    report = await runner.run()
    payload = json.loads(json.dumps(report.to_json()))

    assert payload["exit_code"] == 1
    assert {check["name"] for check in payload["checks"]} == {
        "daemon_alive",
        "keychain_readable",
        "contact_email",
        "schema_versions",
    }


async def test_doctor_reports_db_unreadable_for_a_corrupt_database(tmp_path: Path) -> None:
    """@spec HLTH-40: a present but corrupt state.db is reported schema_versions
    install_critical db_unreadable, not an uncaught sqlite3.DatabaseError."""
    settings = offline_settings(tmp_path, contact={"email": "owner@example.net"})
    state_db = Path(settings.paths.state_dir) / "state.db"
    state_db.write_bytes(b"not a sqlite database")

    runner = doctor.DoctorRunner(
        settings, provider=FakeProvider({}), transport=httpx.MockTransport(_fail)
    )
    report = await runner.run()

    schema_check = next(c for c in report.checks if c.name == "schema_versions")
    assert schema_check.status == "install_critical"
    assert schema_check.code == "db_unreadable"


def test_settings_error_on_a_placeholder_contact_becomes_the_contact_email_check() -> None:
    """@spec HLTH-40: a settings validation error does not abort doctor; a placeholder
    contact.email becomes the contact_email check, install_critical."""
    with pytest.raises(ValidationError) as exc:
        OfflineSettings(contact={"email": "owner@example.com"})
    check = doctor._settings_check(exc.value)
    assert check.name == "contact_email"
    assert check.status == "install_critical"


def test_settings_error_elsewhere_becomes_the_settings_check() -> None:
    """@spec HLTH-40: a validation error outside contact.email becomes the settings check."""
    with pytest.raises(ValidationError) as exc:
        OfflineSettings(server={"host": "8.8.8.8"})
    check = doctor._settings_check(exc.value)
    assert check.name == "settings"
    assert check.status == "install_critical"


def _healthy(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"status": "ok"})


@pytest.mark.parametrize(
    ("handler", "expected_exit"), [(_fail, 1), (_healthy, 0)], ids=["dead", "alive"]
)
def test_main_doctor_wires_json_and_liveness_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    handler: Any,
    expected_exit: int,
) -> None:
    """@spec HLTH-40: `research-mcp doctor --json --liveness` wires the flags through
    main() and _cmd_doctor to DoctorRunner.run, printing a JSON report whose exit code
    follows the daemon's /healthz answer. The probe goes to a mock transport, never a real
    loopback port, so a daemon running on the machine cannot change the result."""
    settings = offline_settings(tmp_path)
    real_runner = doctor.DoctorRunner
    monkeypatch.setattr(cli, "Settings", lambda: settings)
    monkeypatch.setattr(
        doctor,
        "DoctorRunner",
        lambda _settings: real_runner(
            settings, provider=FakeProvider({}), transport=httpx.MockTransport(handler)
        ),
    )

    exit_code = cli.main(["doctor", "--json", "--liveness"])

    assert exit_code == expected_exit
    payload = json.loads(capsys.readouterr().out)
    assert payload["exit_code"] == expected_exit
    assert [check["name"] for check in payload["checks"]] == [
        "daemon_alive",
        "keychain_readable",
    ]


def test_gen_inventory_check_fails_on_stale_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@spec SRC-13: if the committed source inventory differs from the registry, then
    `gen_inventory --check` shall fail."""
    module = _load_gen_inventory()
    committed = tmp_path / "sources.md"
    committed.write_text("stale inventory text\n", encoding="utf-8")
    monkeypatch.setattr(module, "OUTPUT", committed)

    assert module.main(["--check"]) == 1

    committed.write_text(module.render(), encoding="utf-8")
    assert module.main(["--check"]) == 0


async def test_doctor_reads_the_schema_through_the_store_read_only(tmp_path: Path) -> None:
    """@spec HLTH-40: doctor reads PRAGMA user_version through platform.stores, opening the
    file read-only with no migration, so an old state.db is reported and left untouched
    (architect drift finding, rm-m0f; LLD-platform-v2 5.1, LLD-health-v2 5.9)."""
    settings = offline_settings(tmp_path, contact={"email": "owner@example.net"})
    state_db = Path(settings.paths.state_dir) / "state.db"
    with sqlite3.connect(state_db) as conn:
        conn.execute("PRAGMA user_version = 0")
        conn.execute("CREATE TABLE marker (x)")
    before = state_db.read_bytes()

    runner = doctor.DoctorRunner(
        settings, provider=FakeProvider({}), transport=httpx.MockTransport(_fail)
    )
    report = await runner.run()

    schema_check = next(c for c in report.checks if c.name == "schema_versions")
    assert schema_check.code == "migration_failed"
    assert state_db.read_bytes() == before
    assert not await anyio.Path(f"{state_db}-wal").exists()
    assert "aiosqlite" not in vars(doctor)


@pytest.mark.parametrize(
    "argv",
    [["install"], ["doctor"], ["secrets", "rotate-token"], ["stdio"]],
)
def test_cli_commands_install_the_redacting_log_handlers_first(
    argv: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@spec PLAT-40: install, doctor, secrets rotate-token and stdio call
    configure_logging(settings) before their work, so their log records pass the
    redacting filter (architect drift finding, rm-m0f; LLD-platform-v2 4.3)."""
    settings = offline_settings(tmp_path, contact={"email": "owner@example.net"})
    events: list[str] = []

    def fake_configure(given: Settings, **_kw: Any) -> None:
        assert given is settings
        events.append("logging")

    def work(*_a: Any, **_kw: Any) -> Any:
        events.append("work")
        raise cli.InstallError("stop")

    async def async_work(*_a: Any, **_kw: Any) -> Any:
        events.append("work")
        return doctor.DoctorReport([])

    monkeypatch.setattr(cli, "Settings", lambda: settings)
    monkeypatch.setattr(cli, "configure_logging", fake_configure)
    monkeypatch.setattr(cli, "install", work)
    monkeypatch.setattr(cli, "rotate_token", lambda *_a: events.append("work") or 0)
    real_run = anyio.run
    monkeypatch.setattr(cli.anyio, "run", lambda fn, *a: fn(*a) if a else real_run(fn))
    monkeypatch.setattr(cli.shim, "main", lambda _s: events.append("work") or 0)
    monkeypatch.setattr(cli.doctor_service.DoctorRunner, "run", async_work)
    monkeypatch.setattr(cli, "_print_doctor_report", lambda *_a, **_kw: None)
    monkeypatch.setattr(cli, "KeychainProvider", lambda *_a: None)
    monkeypatch.setattr(cli, "SystemLaunchctl", lambda: None)

    cli.main(argv)

    assert events[:2] == ["logging", "work"]
