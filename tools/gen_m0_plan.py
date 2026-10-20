"""Builds .orchestration/plan-m0.json from SPEC-v1 section 12.3 and TEST-PLAN-v3 Appendix A.

`--check` exits 1 when the committed plan is stale (tools/ci.sh runs it)."""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = "docs/spec/SPEC-v1.md"
TEST_PLAN = "docs/test-plan/TEST-PLAN-v3.md"
spec = (ROOT / SPEC).read_text()
plan = (ROOT / TEST_PLAN).read_text()

sec = spec.split("### 12.3", 1)[1].split("### 12.4", 1)[0]
rows = [line for line in sec.splitlines() if line.startswith("| M0-")]
appx = plan.split("## Appendix A", 1)[1].split("\n## ", 1)[0]
tests = {m.group(1): m.group(2) for m in re.finditer(r"^\| (M0-\d\d) \| ([^|]+) \|", appx, re.M)}
clarified = set(re.findall(r"^\| (M0-\d\d) \|", spec.split("### 0.6", 1)[1].split("\n## ", 1)[0], re.M))

PKG = "src/research_mcp/"
TOP = ("src/", "tests/", "tools/", "docs/", ".github/")
FIXTURES = ("search_ok.{ext}", "search_empty.{ext}", "get_ok.{ext}", "err_429.json", "err_5xx.json",
            "malformed.{ext}", "oversize.marker")


def expand(path):
    path = path.strip().strip("`")
    if path.startswith(TOP) or path in ("pyproject.toml", "uv.lock", ".python-version"):
        return path
    return PKG + path


RULES = (
    "Branch rules (AGENTS.md): work only on the branch you are on and commit there; never push, never create or switch "
    "branches, never commit to main. ECC merges main into your branch before each attempt; if it did, keep both sides "
    "and make your unit pass on top. If a file your unit needs belongs to a dependency that is not merged yet, do not "
    "create it: finish what you can and report status blocked naming the missing unit; ECC re-runs you after it merges. "
    "Do not add __init__.py files under tests/ and do not edit pyproject.toml, uv.lock or any package __init__.py "
    "(M0-01 owns them). Never touch the v1 repository (my-research-mcp-server) or ~/arxiv-papers, never read real "
    "credentials or the Keychain, and use fakes and recorded fixtures for every external system; tests pass with the "
    "network blocked. A prior attempt exists read-only at ~/Documents/GitHub/my-research-mcp; you may read it, but "
    "SPEC-v1 wins wherever they differ, and section 0.6 lists defects that attempt shipped."
)

units = []
for row in rows:
    uid, title, impl, files, deps, risk = [c.strip() for c in row.strip("|").split("|")]
    file_list = []
    for f in re.findall(r"`([^`]+)`", files):
        if f.endswith("/*"):
            base = expand(f[:-2])
            ext = "xml" if "/arxiv/" in base else "json"
            file_list += [f"{base}/{n.format(ext=ext)}" for n in FIXTURES]
        else:
            file_list.append(expand(f))
    dep_list = [] if deps == "none" else [d.strip() for d in deps.split(",")]
    at = tests[uid].strip()
    test_files = [f for f in file_list if f.startswith("tests/") and f.endswith(".py") and "/test_" in f]
    if uid == "M0-01":
        cmds = ["uv sync --frozen", "uv run pytest tests/unit -q"]
    else:
        cmds = ["uv run pytest " + " ".join(test_files) + " -q"]
    m = re.match(r"src/research_mcp/sources/(\w+)\.py$", file_list[0])
    if m and m.group(1) not in ("base", "registry"):
        cmds.append(f"uv run pytest tests/sources/test_conformance.py -k {m.group(1)} -q")
    cmds.append("tools/ci.sh --python-only")
    note = " Section 0.6 has clarifications for this unit; they are requirements." if uid in clarified else ""
    nums = list(dict.fromkeys(re.findall(r"\b\d+(?:\.\d+)*\b", re.sub(r"`[^`]*`", "", impl))))
    implemented = "sections " + (", ".join(nums[:-1]) + " and " + nums[-1] if len(nums) > 1 else nums[0])
    desc = (f"Read AGENTS.md first. Build work unit {uid} exactly as {SPEC} specifies: its row in section 12.3, "
            f"{implemented}, which it implements ({impl}), and section 0 (conformance).{note} SPEC-v1 owns every "
            "name. Write the "
            f"acceptance tests {TEST_PLAN} Appendix A assigns to this unit: {at}; put each test id first in its test's "
            "docstring (test plan section 1.3). Keep tools/ci.sh --python-only green; gates run commands without a "
            "shell, so tools/ci.sh stays executable with a #!/usr/bin/env bash line. " + RULES)
    units.append({
        "schema_version": "1.0", "id": uid, "title": title, "description": desc,
        "depends_on": dep_list, "scope": {"files": file_list},
        "acceptance": {"commands": cmds}, "risk": risk,
        "capabilities": {"network": True, "secrets": []},
        "routing": {"initial_tier": {"low": 0, "medium": 1, "high": 2}[risk], "maximum_tier": 2,
                    "reviewer_must_differ_from_author": True},
        "budget": {"attempts": 4, "minutes": 240, "maximum_cost_usd": 10.0},
        "rollback": "revert the unit branch; nothing outside this repository changes",
    })

out = ROOT / ".orchestration/plan-m0.json"
text = json.dumps({"units": units}, indent=1) + "\n"
if "--check" in sys.argv:
    sys.exit(0 if out.exists() and out.read_text() == text else 1)
out.write_text(text)
print(len(units), "units")
