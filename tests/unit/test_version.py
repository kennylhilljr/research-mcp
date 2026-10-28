"""Package version, packaging metadata and the CI script."""

from __future__ import annotations

import dataclasses
import importlib.util
import os
import stat
import subprocess
import sys
import tomllib
from importlib.metadata import requires, version
from pathlib import Path
from typing import Any

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

import research_mcp
from research_mcp.core.specs import AuthSpec
from research_mcp.settings import Settings
from research_mcp.sources.base import SourceContext, SourceSpec
from research_mcp.sources.registry import SourceRegistry, default_has_extra
from research_mcp.testing.adapters import FAKE_SPEC, FakeAdapter
from research_mcp.version import __version__

REPO = Path(__file__).resolve().parents[2]


def _pyproject() -> dict[str, Any]:
    with (REPO / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def _names(requirements: list[str]) -> set[str]:
    return {canonicalize_name(Requirement(text).name) for text in requirements}


def test_version_is_3x_and_matches_metadata() -> None:
    """@spec PLAT-1: package version is 3.x and matches pyproject and installed metadata."""
    assert __version__.split(".")[0] == "3"
    assert research_mcp.__version__ == __version__
    assert _pyproject()["project"]["version"] == __version__
    assert version("research-mcp") == __version__


def test_ci_script_is_executable_bash() -> None:
    """@spec PLAT-2: tools/ci.sh exists, is executable and starts with #!/usr/bin/env bash."""
    script = REPO / "tools" / "ci.sh"
    assert script.is_file()
    assert script.stat().st_mode & stat.S_IXUSR
    assert os.access(script, os.X_OK)
    assert script.read_text(encoding="utf-8").splitlines()[0] == "#!/usr/bin/env bash"


def test_heavy_dependencies_are_extras() -> None:
    """@spec PLAT-4: pyproject declares extras pdf and embeddings; base excludes heavy deps."""
    project = _pyproject()["project"]
    extras = project["optional-dependencies"]
    assert "pymupdf" in _names(extras["pdf"])
    assert {"fastembed", "numpy"} <= _names(extras["embeddings"])

    base = _names(project["dependencies"])
    assert base.isdisjoint({"pymupdf", "fastembed", "numpy", "duckdb"})


class _OfflineSettings(Settings):
    """Settings from keyword arguments only: no config file, no environment."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


def _vertex_stand_in() -> SourceSpec:
    """A spec shaped like vertex_search (LLD-sources-v3 4, 5.7); the real one is M1-14's."""
    origin = "https://discoveryengine.googleapis.com"
    return dataclasses.replace(
        FAKE_SPEC,
        id="vertex_search",
        title="Vertex AI Search",
        group="web",
        hosts=frozenset({"discoveryengine.googleapis.com"}),
        auth=AuthSpec(
            secrets=("GOOGLE_SIGNIN",),
            required=True,
            placement="bearer",
            param="",
            origins=(origin,),
            signup_url="https://cloud.google.com/sdk/gcloud/reference/auth/application-default",
        ),
        extras=frozenset({"gcp"}),
        enabled_by_default=False,
    )


def test_gcp_extra_is_optional_and_vertex_unconfigured_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@spec PLAT-13: the gcp extra holds google-auth, the base install does not, importing
    the package loads none of it, and without it vertex_search is unconfigured with the
    install command."""
    project = _pyproject()["project"]
    assert "google-auth" in _names(project["optional-dependencies"]["gcp"])
    assert "google-auth" not in _names(project["dependencies"])
    installed = [Requirement(text) for text in requires("research-mcp") or []]
    gcp = {canonicalize_name(r.name) for r in installed if r.marker and "gcp" in str(r.marker)}
    base = {canonicalize_name(r.name) for r in installed if r.marker is None}
    assert "google-auth" in gcp
    assert "google-auth" not in base
    overrides = _pyproject()["tool"]["mypy"]["overrides"]
    assert any("google.*" in override["module"] for override in overrides)

    # A search-only install imports none of google-auth, the provider module included.
    probe = (
        "import sys, research_mcp, research_mcp.app, research_mcp.platform.google_adc;"
        "print(sorted(m for m in sys.modules if m == 'google' or m.startswith('google.')))"
    )
    done = subprocess.run(  # noqa: S603 - fixed argv, this interpreter
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True, timeout=60
    )
    assert done.stdout.strip() == "[]"

    # The extra is missing: find_spec finds no google.auth, so the registry's own
    # detection reports the source unconfigured and names the install command.
    real_find_spec = importlib.util.find_spec

    def find_spec(name: str, *args: Any) -> Any:
        return None if name == "google.auth" else real_find_spec(name, *args)

    monkeypatch.setattr(importlib.util, "find_spec", find_spec)
    assert default_has_extra("gcp") is False
    settings = _OfflineSettings(sources={"vertex_search": {"enabled": True}})

    def no_context(spec: SourceSpec) -> SourceContext:
        raise AssertionError("listing a source never builds its adapter")

    registry = SourceRegistry(
        settings,
        no_context,
        has_credential=lambda name: True,
        modules=[],
        extra_adapters=[(_vertex_stand_in(), FakeAdapter)],
    )
    (view,) = registry.view("vertex_search")
    assert view.state == "unconfigured"
    assert view.reason == "The optional extra `gcp` is not installed."
    assert view.fix_hint == "Install the extra: `uv tool install 'research-mcp[gcp]'`"
