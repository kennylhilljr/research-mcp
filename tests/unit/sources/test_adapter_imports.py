"""Static check that adapter modules do no I/O of their own (LLD-sources-v2 5.3; SRC-7).

Every module under ``src/research_mcp/sources/`` is parsed with ``ast``. It fails on an
import of an HTTP library, ``socket``, ``urllib.request``, ``http.client`` or the secrets
module; on a call of ``time.sleep`` or ``asyncio.sleep``; and, stricter than SRC-7 (SRC-FR-3
and the XML rule of the security LLD), on an XML parser other than ``defusedxml`` and on
``open(``, ``Path.write_text`` or ``Path.write_bytes``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import research_mcp.sources as sources_pkg

PACKAGE = "research_mcp.sources"
FORBIDDEN_MODULES = (
    "httpx",
    "requests",
    "urllib.request",
    "http.client",
    "socket",
    "research_mcp.platform.secrets",
    "xml.etree",
    "xml.dom",
    "xml.sax",
    "lxml",
)
SLEEP_MODULES = ("time", "asyncio")
WRITE_METHODS = ("write_text", "write_bytes")


def _forbidden(name: str) -> bool:
    return any(name == bad or name.startswith(bad + ".") for bad in FORBIDDEN_MODULES)


def _absolute(node: ast.ImportFrom, package: str) -> str:
    if node.level == 0:
        return node.module or ""
    parts = package.split(".")
    base = parts[: len(parts) - node.level + 1]
    return ".".join([*base, node.module] if node.module else base)


def _sleep_names(tree: ast.Module) -> tuple[set[str], set[str]]:
    """Local names bound to the ``time`` or ``asyncio`` modules, and to their ``sleep``."""
    modules: set[str] = set()
    sleeps: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in SLEEP_MODULES:
                    modules.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module in SLEEP_MODULES:
            sleeps.update(a.asname or a.name for a in node.names if a.name == "sleep")
    return modules, sleeps


def _import_violations(tree: ast.Module, package: str) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [f"import {a.name}" for a in node.names if _forbidden(a.name)]
        elif isinstance(node, ast.ImportFrom):
            module = _absolute(node, package)
            if _forbidden(module):
                found.append(f"from {module} import")
                continue
            found += [
                f"from {module} import {a.name}"
                for a in node.names
                if _forbidden(f"{module}.{a.name}")
            ]
    return found


def _call_violations(tree: ast.Module) -> list[str]:
    modules, sleeps = _sleep_names(tree)
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in sleeps:
            found.append(f"call {func.id}()")
        elif isinstance(func, ast.Name) and func.id == "open":
            found.append("call open()")
        elif isinstance(func, ast.Attribute):
            owner = func.value
            if func.attr == "sleep" and isinstance(owner, ast.Name) and owner.id in modules:
                found.append(f"call {owner.id}.sleep()")
            elif func.attr in WRITE_METHODS:
                found.append(f"call .{func.attr}()")
            elif func.attr == "open" and isinstance(owner, ast.Name) and owner.id == "io":
                found.append("call io.open()")
    return found


# @spec SRC-7
def violations(source: str, package: str = PACKAGE) -> list[str]:
    """Every forbidden import and call in one module's source text."""
    tree = ast.parse(source)
    return _import_violations(tree, package) + _call_violations(tree)


def adapter_modules() -> list[Path]:
    (root,) = sources_pkg.__path__
    return sorted(Path(root).rglob("*.py"))


def test_sources_package_is_scanned() -> None:
    """The scan reaches the package's own modules, so an empty pass means something."""
    names = {path.name for path in adapter_modules()}
    assert {"__init__.py", "base.py", "registry.py"} <= names


@pytest.mark.parametrize("path", adapter_modules(), ids=lambda path: path.name)
def test_adapter_modules_have_no_forbidden_import_or_call(path: Path) -> None:
    """@spec SRC-7: No module under ``sources/`` imports or calls what adapters may not."""
    assert violations(path.read_text(encoding="utf-8")) == []


FORBIDDEN_CASES = [
    "import httpx",
    "import httpx as h",
    "from httpx import AsyncClient",
    "import requests",
    "import urllib.request",
    "from urllib import request",
    "from urllib.request import urlopen",
    "import http.client",
    "from http import client",
    "import socket",
    "from socket import create_connection",
    "import research_mcp.platform.secrets",
    "from research_mcp.platform import secrets",
    "from research_mcp.platform.secrets import SecretCache",
    "from ..platform import secrets",
    "from ..platform.secrets import Secret",
    "import xml.etree.ElementTree",
    "from xml.dom import minidom",
    "import xml.sax",
    "from lxml import etree",
    "import time\ntime.sleep(1)",
    "import time as clock\nclock.sleep(1)",
    "from time import sleep\nsleep(1)",
    "from time import sleep as nap\nnap(1)",
    "import asyncio\nasync def f():\n    await asyncio.sleep(1)",
    "from asyncio import sleep\nasync def f():\n    await sleep(1)",
    "open('x', 'w')",
    "import io\nio.open('x')",
    "from pathlib import Path\nPath('x').write_text('y')",
    "from pathlib import Path\nPath('x').write_bytes(b'y')",
]


@pytest.mark.parametrize("source", FORBIDDEN_CASES)
def test_forbidden_import_or_call_in_adapter_module_fails(source: str, tmp_path: Path) -> None:
    """@spec SRC-7: A temp adapter module with one forbidden import or call fails the check."""
    module = tmp_path / "bad_adapter.py"
    module.write_text(source + "\n", encoding="utf-8")
    assert violations(module.read_text(encoding="utf-8")) != []


ALLOWED_CASES = [
    "import urllib.parse",
    "from urllib.parse import urlsplit",
    "import urllib.robotparser",
    "from urllib import parse",
    "import defusedxml.ElementTree",
    "from defusedxml.ElementTree import fromstring",
    "from research_mcp.platform.http import HttpPort",
    "from ..core.errors import HttpError",
    "import time\ntime.monotonic()",
    "import asyncio\nasyncio.gather()",
    "from research_mcp.core.models import Sleeper",
    "def sleep(): pass\nsleep()",
    "text = 'time.sleep(1) and open()'",
]


@pytest.mark.parametrize("source", ALLOWED_CASES)
def test_allowed_imports_pass(source: str) -> None:
    """@spec SRC-7: ``urllib.parse`` and the other allowed modules pass the check."""
    assert violations(source) == []
