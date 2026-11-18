"""The documented clone command and every link to this repository use the canonical owner.

A stale owner in the README makes the first setup command fail for new contributors, so
the README must carry the exact clone, ``cd`` and ``uv sync --frozen`` sequence, and no
text file in the repository may point at ``research-mcp`` under a different owner.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_OWNER = "kennylhilljr"
CANONICAL_REPO = "research-mcp"
CANONICAL_URL = f"https://github.com/{CANONICAL_OWNER}/{CANONICAL_REPO}.git"

# Any github.com link (https or ssh form) to a repository named research-mcp.
REPO_LINK = re.compile(
    r"github\.com[/:](?P<owner>[A-Za-z0-9_.-]+)/" + re.escape(CANONICAL_REPO) + r"(?![A-Za-z0-9_-])"
)
TEXT_SUFFIXES = {".md", ".toml", ".yaml", ".yml", ".json", ".py", ".mjs", ".sh", ".txt", ".cfg"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".mypy_cache"}


def _text_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in rel.parts):
            continue
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            files.append(path)
    return files


def test_readme_clone_command_is_canonical() -> None:
    """The README development install clones the canonical repository, then syncs it."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    expected = f"git clone {CANONICAL_URL}\ncd {CANONICAL_REPO}\nuv sync --frozen\n"
    assert expected in readme, f"README must contain the clone sequence:\n{expected}"
    clones = re.findall(r"^git clone (\S+)", readme, flags=re.MULTILINE)
    assert clones, "README has no git clone command"
    assert all(url == CANONICAL_URL for url in clones), clones


def test_no_repository_link_uses_another_owner() -> None:
    """No text file links to research-mcp under an owner other than the canonical one."""
    wrong = []
    for path in _text_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in REPO_LINK.finditer(text):
            if match.group("owner") != CANONICAL_OWNER:
                line = text.count("\n", 0, match.start()) + 1
                wrong.append(f"{path.relative_to(ROOT)}:{line}: {match.group(0)}")
    assert not wrong, "non-canonical repository links:\n" + "\n".join(wrong)


def test_repo_link_pattern_catches_a_stale_owner() -> None:
    """The guard recognizes https and ssh links under a different owner."""
    # Built from parts so this file does not itself contain a stale link.
    stale = "someone-else/" + CANONICAL_REPO
    stale_https = f"git clone https://github.com/{stale}.git"
    stale_ssh = f"git@github.com:{stale}.git"
    for sample in (stale_https, stale_ssh):
        match = REPO_LINK.search(sample)
        assert match is not None and match.group("owner") == "someone-else"
    assert REPO_LINK.search("https://github.com/someone-else/research-mcp-extras") is None
