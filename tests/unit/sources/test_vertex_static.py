"""Static check that v2 code never opens the Google sign-in file (SRC-32; SEC-INV-11).

``gcloud`` owns the Application Default Credentials file and ``google-auth`` is its only
reader (LLD-platform-v3 4.2; SRC-FR-23). Every module under ``src/research_mcp/`` is parsed
with ``ast`` and fails on:

- a string that names the file or the places it is found: ``application_default_credentials``,
  ``GOOGLE_APPLICATION_CREDENTIALS``, ``CLOUDSDK_CONFIG`` or a ``gcloud`` config folder;
- a call of a ``google-auth`` function that loads credentials from a path or a dict.

The modules that handle the sign-in (``platform/google_adc.py`` and
``sources/vertex_search.py``) must also make no file call at all: no ``open``, no
``Path.open``, ``read_text``, ``read_bytes``, ``write_text`` or ``write_bytes``, and no
``shutil`` copy.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import research_mcp

SRC = Path(research_mcp.__file__).parent
SIGNIN_MODULES = ("platform/google_adc.py", "sources/vertex_search.py")
CREDENTIAL_FILE_TEXT = (
    "application_default_credentials",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "CLOUDSDK_CONFIG",
    ".config/gcloud",
    "AppData/Roaming/gcloud",
)
FILE_LOADERS = frozenset(
    {
        "load_credentials_from_file",
        "load_credentials_from_dict",
        "from_authorized_user_file",
        "from_authorized_user_info",
        "from_service_account_file",
        "from_service_account_info",
        "get_application_default_credentials_path",
        "_get_gcloud_sdk_credentials",
        "_get_explicit_environ_credentials",
    }
)
FILE_CALLS = frozenset({"open", "read_text", "read_bytes", "write_text", "write_bytes"})
COPY_CALLS = frozenset({"copy", "copy2", "copyfile", "copyfileobj", "move"})


def _called(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def credential_file_findings(source: str, *, signin_module: bool) -> list[str]:
    """Each place ``source`` names, loads or opens the sign-in file, as ``line: what``."""
    findings: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            findings += [
                f"{node.lineno}: names {text}"
                for text in CREDENTIAL_FILE_TEXT
                if text.lower() in node.value.lower()
            ]
        elif isinstance(node, ast.Call):
            name = _called(node)
            if name in FILE_LOADERS:
                findings.append(f"{node.lineno}: loads credentials with {name}")
            if signin_module and name in FILE_CALLS | COPY_CALLS:
                findings.append(f"{node.lineno}: file call {name}")
    return findings


def _modules() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def test_no_src_module_opens_the_credential_file() -> None:
    """@spec SRC-32: No module under ``src/research_mcp`` names, loads or opens the Google
    sign-in file; the sign-in modules make no file call at all."""
    modules = _modules()
    for name in SIGNIN_MODULES:
        assert SRC / name in modules, f"{name} is missing, so the check would pass vacuously"
    found = {
        str(path.relative_to(SRC)): hits
        for path in modules
        if (
            hits := credential_file_findings(
                path.read_text(encoding="utf-8"),
                signin_module=str(path.relative_to(SRC)) in SIGNIN_MODULES,
            )
        )
    }
    assert found == {}


@pytest.mark.parametrize(
    ("source", "signin_module"),
    [
        ('path = "~/.config/gcloud/application_default_credentials.json"', False),
        ('import os\nos.environ["GOOGLE_APPLICATION_CREDENTIALS"]', False),
        ("import google.auth\ngoogle.auth.load_credentials_from_file(p)", False),
        (
            "from google.oauth2 import credentials\ncredentials.Credentials."
            "from_authorized_user_file(p)",
            False,
        ),
        ("with open(p) as f:\n    f.read()", True),
        ("from pathlib import Path\nPath(p).read_text()", True),
        ("import shutil\nshutil.copy(a, b)", True),
    ],
)
def test_the_check_catches_each_way_of_reaching_the_file(source: str, signin_module: bool) -> None:
    """@spec SRC-32: The static check flags each way code could reach the sign-in file."""
    assert credential_file_findings(source, signin_module=signin_module)


def test_the_check_allows_the_library_default_loader() -> None:
    """@spec SRC-32: ``google.auth.default``, which lets the library read the file, passes."""
    source = (
        "import google.auth\n"
        'creds, project = google.auth.default(scopes=["https://www.googleapis.com/auth/'
        'cloud-platform"])\n'
    )
    assert credential_file_findings(source, signin_module=True) == []
