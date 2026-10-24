"""`install` and `secrets rotate-token` (LLD-platform-v2 2.5, 4.5, 5.9; LLD-security-v2 5.2)."""

from __future__ import annotations

import base64
import json
import plistlib
import re
from pathlib import Path
from typing import Any

import anyio
import pytest

from research_mcp import cli
from research_mcp.platform import auth
from research_mcp.platform.secrets import FakeProvider, SecretRef
from research_mcp.settings import Settings
from research_mcp.shim import DAEMON_LABEL
from research_mcp.testing.launchctl import FakeLaunchctl

_PLACEHOLDER = re.compile(r"__[A-Z]+__")


class OfflineSettings(Settings):
    """Settings built only from keyword arguments: no real config.toml or environment."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **_rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


def offline_settings(tmp_path: Path) -> Settings:
    settings = OfflineSettings(
        paths={
            "state_dir": tmp_path / "state",
            "data_dir": tmp_path / "state" / "cache",
            "model_cache_dir": tmp_path / "models",
            "log_dir": tmp_path / "logs",
        }
    )
    settings.paths.create_directories()
    return settings


def do_install(settings: Settings, provider: Any, tmp_path: Path) -> list[Path]:
    return cli.install(
        settings,
        provider=provider,
        agents_dir=tmp_path / "LaunchAgents",
        venv_root=tmp_path / "venv",
    )


def test_install_renders_every_plist_with_no_placeholder_left(tmp_path: Path) -> None:
    """@spec PLAT-81: install renders the three plists with every placeholder filled, such
    that plistlib parses them, and writes nothing secret."""
    settings = offline_settings(tmp_path)
    provider = FakeProvider({})
    agents_dir = tmp_path / "LaunchAgents"
    venv_root = tmp_path / "venv"

    written = cli.install(settings, provider=provider, agents_dir=agents_dir, venv_root=venv_root)

    assert {path.name for path in written} == {
        "local.research-mcpd.plist",
        "local.research-mcp-doctor.plist",
        "local.research-mcp-watchdog.plist",
    }
    daemon_token = provider.items["DAEMON_TOKEN"]
    for path in written:
        text = path.read_text(encoding="utf-8")
        assert _PLACEHOLDER.search(text) is None
        assert daemon_token not in text
        parsed = plistlib.loads(text.encode("utf-8"))
        assert parsed["Label"] == path.stem
        assert "EnvironmentVariables" not in parsed


def test_install_generates_daemon_token_only_when_absent(tmp_path: Path) -> None:
    """@spec PLAT-83, SEC-30: install mints DAEMON_TOKEN (32 bytes, URL-safe base64, 43
    characters) through the provider if it is absent, and never replaces an existing one."""
    settings = offline_settings(tmp_path)
    provider = FakeProvider({})

    do_install(settings, provider, tmp_path)

    minted = provider.items["DAEMON_TOKEN"]
    assert len(minted) == 43
    assert "=" not in minted
    assert len(base64.urlsafe_b64decode(minted + "==")) == 32

    do_install(settings, provider, tmp_path)
    assert provider.items["DAEMON_TOKEN"] == minted


def test_install_print_client_config_has_no_secret(tmp_path: Path) -> None:
    """@spec PLAT-82: install --print-client-config prints entries that launch
    `research-mcp stdio` and contain no secret."""
    settings = offline_settings(tmp_path)
    provider = FakeProvider({})
    venv_root = tmp_path / "venv"

    do_install(settings, provider, tmp_path)
    text = cli.client_config_json(venv_root)
    config = json.loads(text)

    research = config["mcpServers"]["research"]
    assert research["args"] == ["stdio"]
    assert research["command"] == str(venv_root / "bin" / "research-mcp")
    assert provider.items["DAEMON_TOKEN"] not in text
    assert "Authorization" not in text and "Bearer" not in text


def test_rotate_token_replaces_the_old_token_and_signals_the_daemon(tmp_path: Path) -> None:
    """@spec PLAT-83: secrets rotate-token replaces DAEMON_TOKEN, through the provider, so
    the old token stops working, and signals a running daemon to reload it."""
    settings = offline_settings(tmp_path)
    old_token = auth.mint_token()
    provider = FakeProvider({"DAEMON_TOKEN": old_token})
    launchctl = FakeLaunchctl(loaded=True)

    exit_code = anyio.run(cli.rotate_token, settings, provider, launchctl)

    assert exit_code == 0
    new_token = provider.items["DAEMON_TOKEN"]
    assert new_token != old_token
    assert len(new_token) == 43 and "=" not in new_token  # @spec SEC-30
    _, new_secret = provider.get(SecretRef.parse(settings.server.token))
    assert not auth.token_matches(old_token, new_secret)
    assert auth.token_matches(new_token, new_secret)
    assert ("kill", "SIGHUP", DAEMON_LABEL) in launchctl.calls


def test_rotate_token_skips_the_signal_when_the_daemon_is_not_loaded(tmp_path: Path) -> None:
    """@spec PLAT-83: when the daemon is not running, rotate-token still stores the new
    token but sends no signal; the next start reads it."""
    settings = offline_settings(tmp_path)
    provider = FakeProvider({"DAEMON_TOKEN": auth.mint_token()})
    launchctl = FakeLaunchctl(loaded=False)

    anyio.run(cli.rotate_token, settings, provider, launchctl)

    assert ("kill", "SIGHUP", DAEMON_LABEL) not in launchctl.calls
    assert provider.items["DAEMON_TOKEN"]


def test_load_jobs_boots_out_an_already_loaded_job_first(tmp_path: Path) -> None:
    """install is idempotent: loading an already-loaded job first removes it (5.9)."""
    settings = offline_settings(tmp_path)
    provider = FakeProvider({})
    written = do_install(settings, provider, tmp_path)
    launchctl = FakeLaunchctl(loaded=True)

    anyio.run(cli.load_jobs, launchctl, written)

    bootouts = [call for call in launchctl.calls if call[0] == "bootout"]
    bootstraps = [call for call in launchctl.calls if call[0] == "bootstrap"]
    assert {call[1] for call in bootouts} == {path.stem for path in written}
    assert len(bootstraps) == len(written)


_LABELS = [DAEMON_LABEL, "local.research-mcp-doctor", "local.research-mcp-watchdog"]


@pytest.mark.parametrize("label", _LABELS)
def test_every_plist_label_matches_its_filename(tmp_path: Path, label: str) -> None:
    """@spec PLAT-81: each rendered plist's Label matches the launchd job name."""
    settings = offline_settings(tmp_path)
    do_install(settings, FakeProvider({}), tmp_path)
    parsed = plistlib.loads((tmp_path / "LaunchAgents" / f"{label}.plist").read_bytes())
    assert parsed["Label"] == label
