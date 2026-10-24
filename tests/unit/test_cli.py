"""The CLI's command table and the doctor skeleton (LLD-platform-v2 2.4; LLD-health-v2 5.9)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

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
        assert name in out


async def test_doctor_runs_four_checks_with_fakes(tmp_path: Path) -> None:
    """@spec HLTH-40: with fakes, doctor runs daemon_alive, keychain_readable, contact_email
    and schema_versions, and exits 0 when every check passes."""
    settings = offline_settings(tmp_path, contact={"email": "owner@example.net"})
    app = build_app(settings, secrets=FakeProvider({"DAEMON_TOKEN": "tok"}), adapters=[])

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        report = await doctor.run_doctor(
            settings, provider=FakeProvider({"DAEMON_TOKEN": "tok"}), transport=transport
        )

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

    report = await doctor.run_doctor(
        settings,
        provider=FakeProvider({}),
        transport=httpx.MockTransport(_fail),
        liveness=True,
    )

    assert [c.name for c in report.checks] == ["daemon_alive", "keychain_readable"]
    assert report.checks[0].status == "install_critical"
    assert report.checks[1].status == "ok"
    assert report.exit_code == 1


async def test_doctor_json_output_is_machine_readable(tmp_path: Path) -> None:
    """@spec HLTH-40: --json produces a report that round-trips through json.dumps/loads."""
    settings = offline_settings(tmp_path)

    report = await doctor.run_doctor(
        settings, provider=FakeProvider({}), transport=httpx.MockTransport(_fail)
    )
    payload = json.loads(json.dumps(report.to_json()))

    assert payload["exit_code"] == 1
    assert {check["name"] for check in payload["checks"]} == {
        "daemon_alive",
        "keychain_readable",
        "contact_email",
        "schema_versions",
    }


def test_settings_error_on_a_placeholder_contact_becomes_the_contact_email_check() -> None:
    """LLD-health-v2 5.9: a settings validation error does not abort doctor; a placeholder
    contact.email becomes the contact_email check, install_critical."""
    with pytest.raises(ValidationError) as exc:
        OfflineSettings(contact={"email": "owner@example.com"})
    check = doctor._settings_check(exc.value)
    assert check.name == "contact_email"
    assert check.status == "install_critical"


def test_settings_error_elsewhere_becomes_the_settings_check() -> None:
    """LLD-health-v2 5.9: a validation error outside contact.email becomes the settings check."""
    with pytest.raises(ValidationError) as exc:
        OfflineSettings(server={"host": "8.8.8.8"})
    check = doctor._settings_check(exc.value)
    assert check.name == "settings"
    assert check.status == "install_critical"


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
