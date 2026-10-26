"""Builds the ECC plans from the task tables of the milestone plans: .orchestration/plan-m0.json from
docs/build/M0-plan-v4.md and .orchestration/plan-m1.json from docs/build/M1-plan-v1.md.

Tasks whose status is `done` are already on main: they are left out, and so are dependencies on them.
A scope entry ending in `/` is a folder the unit owns whole (ECC scopes cover a folder's subtree).

`--check` exits 1 when a committed plan is stale (tools/ci.sh runs it)."""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLANS = (
    ("M0", "docs/build/M0-plan-v4.md", ".orchestration/plan-m0.json", "(M0-01 owns them)"),
    ("M1", "docs/build/M1-plan-v1.md", ".orchestration/plan-m1.json",
     "(M0-01 created them; in M1 only M1-01, which has pyproject.toml and uv.lock in its scope, edits them)"),
)

CONFIG = json.loads((ROOT / "sdd.config.json").read_text())
PREFIX_PRD = {}
for _name, _comp in CONFIG["components"].items():
    _versions = sorted((ROOT / "docs/prd/components").glob(f"PRD-{_name}-v*.md"),
                       key=lambda p: int(re.search(r"-v(\d+)\.md$", p.name).group(1)))
    if _versions:
        PREFIX_PRD[_comp["prefix"]] = _versions[-1].relative_to(ROOT).as_posix()

PKG = "src/research_mcp/"
TOP = ("src/", "tests/", "tools/", "docs/", ".github/")
SOURCE_IDS = {"core_ac": "core"}  # module name to source id where they differ (LLD-sources-v2 5.1)
NOT_ADAPTERS = ("base", "registry", "mcp_upstream", "robots", "docs_allowlist", "sitequery", "doi_resolver")
FIXTURES = ("search_ok.{ext}", "search_empty.{ext}", "get_ok.{ext}", "err_429.json", "err_5xx.json",
            "malformed.{ext}", "oversize.marker")


def expand(path):
    path = path.strip().strip("`")
    if path.startswith(TOP) or path in ("pyproject.toml", "uv.lock", ".python-version", "README.md"):
        return path
    return PKG + path


def rules(owner):
    return (
        "Branch rules (AGENTS.md): work only on the branch you are on and commit there; never push, never create or "
        "switch branches, never commit to main. ECC merges main into your branch before each attempt; if it did, keep "
        "both sides and make your unit pass on top. If a file your unit needs belongs to a dependency that is not "
        "merged yet, do not create it: finish what you can and report status blocked naming the missing unit; ECC "
        "re-runs you after it merges. Do not add __init__.py files under tests/ and do not edit pyproject.toml, "
        f"uv.lock or any package __init__.py {owner}. Never touch the v1 repository (my-research-mcp-server) or "
        "~/arxiv-papers, never read real credentials or the Keychain, and use fakes and recorded fixtures for every "
        "external system; tests pass with the network blocked. A prior attempt exists read-only at "
        "~/Documents/GitHub/my-research-mcp; you may read it, but the LLDs win wherever they differ, and the plan's "
        "clarifications list defects that attempt shipped."
    )


def build(milestone, plan_path, owner):
    plan = (ROOT / plan_path).read_text()
    tasks = plan.split("## 2. Tasks", 1)[1].split("\n### ", 1)[0]
    rows = [line for line in tasks.splitlines() if line.startswith(f"| {milestone}-")]
    done = {r.strip("|").split("|")[0].strip() for r in rows if r.strip("|").split("|")[-1].strip() == "done"}
    clar = re.split(r"^### 2\.2 Clarifications[^\n]*$", plan, maxsplit=1, flags=re.M)[1].split("\n## ", 1)[0]
    clarified = set(re.findall(rf"^\| ({milestone}-\d\d) \|", clar, re.M))
    for_all = re.search(r"^\| every unit \|", clar, re.M) is not None
    for_adapters = re.search(r"^\| every adapter unit \|", clar, re.M) is not None

    units = []
    for row in rows:
        uid, title, criteria, deps, _persona, impl, files, risk, _status = [c.strip() for c in row.strip("|").split("|")]
        if uid in done:
            continue
        file_list = []
        for f in re.findall(r"`([^`]+)`", files):
            if f.endswith("/*"):
                base = expand(f[:-2])
                ext = "xml" if "/arxiv/" in base else "json"
                file_list += [f"{base}/{n.format(ext=ext)}" for n in FIXTURES]
            else:
                file_list.append(expand(f))
        dep_list = [] if deps == "none" else [d.strip() for d in deps.split(",") if d.strip() not in done]
        ids = criteria.strip()
        tests = [f for f in file_list if f.startswith("tests/")
                 and (f.endswith("/") or (f.endswith(".py") and "/test_" in f))]
        if uid == "M0-01":
            cmds = ["uv sync --frozen", "uv run pytest tests/unit -q"]
        else:
            cmds = ["uv run pytest " + " ".join(tests) + " -q"]
        adapters = [m.group(1) for m in (re.match(r"src/research_mcp/sources/(\w+)\.py$", f) for f in file_list)
                    if m and m.group(1) not in NOT_ADAPTERS]
        if adapters:
            ids_k = " or ".join(SOURCE_IDS.get(a, a) for a in adapters)
            cmds.append(f'uv run pytest tests/sources/test_conformance.py -k "{ids_k}" -q')
        cmds.append("tools/ci.sh --python-only")
        has_note = uid in clarified or for_all or (for_adapters and adapters)
        note = (f" {plan_path} section 2.2 lists clarifications for this unit; they are "
                "requirements." if has_note else "")
        prds = list(dict.fromkeys(PREFIX_PRD[i.split("-")[0]] for i in ids.split(", ") if i))
        implemented = impl.replace("`", "")
        desc = (f"Read AGENTS.md first. Build work unit {uid} exactly as {plan_path} specifies: its task row and the "
                f"low level designs it implements: {implemented}.{note} The LLDs own every name. Write a test for each "
                f"acceptance criterion this unit owns: {ids} (their text is in {', '.join(prds)} section 2.4); start "
                "each test's docstring with `@spec <ID>:` and put a `# @spec <ID>` comment on the behavior's entry "
                "point in code. Keep tools/ci.sh --python-only green, including `node tools/sdd/cli.mjs check`; gates "
                "run commands without a shell, so tools/ci.sh stays executable with a #!/usr/bin/env bash line. "
                + rules(owner))
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
    return units


stale = False
for milestone, plan_path, out_path, owner in PLANS:
    out = ROOT / out_path
    text = json.dumps({"units": build(milestone, plan_path, owner)}, indent=1) + "\n"
    if "--check" in sys.argv:
        stale |= not (out.exists() and out.read_text() == text)
    else:
        out.write_text(text)
        print(out_path, len(json.loads(text)["units"]), "units")
if "--check" in sys.argv:
    sys.exit(1 if stale else 0)
