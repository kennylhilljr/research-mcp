# Agent instructions for Research MCP v2

Read this file, then [SPEC v1](docs/spec/SPEC-v1.md) section 0 and the sections your work unit names, before changing anything. The specification is the contract; the [PRD](docs/prd/PRD-v4.md) says why and the [HLD](docs/design/HLD-v3.md) gives the shape.

## Documents

- **SPEC v1** owns every name (modules, classes, functions, tables, columns, settings keys, Keychain items, routes), every interface and format, and the work breakdown. Code follows it. If it is wrong or contradicts the PRD or the test plan, do not pick a side: record the conflict in your handoff and build everything it does not touch (SPEC 0.3).
- **TEST-PLAN v3** owns test ids. Put each acceptance test id first in its test's docstring (`"""AT-SRCH-11: ..."""`).
- **Section 0.6** of the specification lists defects the first M0 attempt shipped. They are requirements.
- Docs are versioned: to change one, add the next `-vN` file and update links; never edit an earlier version. Do not edit generated files (`docs/test-plan/TEST-PLAN-v3.md` sections 4 to 6 and Appendix A, `docs/generated/*`, `.orchestration/plan-m0.json`); run their generators.

## Branches

- Every unit has one branch, `ecc/<run>/<unit>`, created by ECC from `main` after the unit's dependencies merged. Work only on the branch you are on.
- Commit your work there. Never push, never create or switch branches, never rebase or rewrite history, never commit to `main`. Only ECC's merge queue writes `main`, after review and verification pass.
- Before each attempt ECC merges the current `main` into your branch. If it did, keep both sides; your unit must pass on top of the merged `main`. If ECC reports a merge conflict, resolving it is the first part of your attempt.
- Stay inside your unit's scope (its file list). If you need a file another unit owns and it is not on your branch yet, do not create it: finish what you can, then hand off with status `blocked`, naming the file and the unit. ECC re-runs you after that unit merges.

## Repairs

- A failed attempt comes back with a brief: the failing gate output, or the reviewers' findings. Fix exactly those, keep everything that passed, and say in the handoff how each finding was addressed. Reviewers re-check the same findings.
- Never weaken, skip or delete a test to make it pass. A test that contradicts the specification is a conflict to record, not a test to change.

## Skills while building (every agent)

The skills live in the repository at `.agents/skills/` (Codex and Gemini read that folder; `.claude/skills` points to it for Claude Code). They are required, not optional: skip one only when its trigger does not apply, and say so in your handoff.

| When | Skill | Claude Code | Codex | Gemini |
|---|---|---|---|---|
| While developing anything you can run (a module API, an MCP tool, the daemon, the CLI) | `run-research-mcp` | `/run`, following the skill | `$run-research-mcp` | ask for the run-research-mcp skill |
| After the change works, before verifying | `simplify-change` | `/simplify` | `$simplify-change` | ask for the simplify-change skill |
| After the acceptance commands and `tools/ci.sh --python-only` pass | `verify-change` | `/verify`, following the skill | `$verify-change` | ask for the verify-change skill |
| Before your handoff (self-review), and when reviewing | `review-change` | `/code-review`, then the skill's checklist | `codex review --base main`, then `$review-change` | the skill (plus the `code-review` extension if installed) |
| High-risk units (SPEC 0.6 rows, `platform/secrets.py`, `redact.py`, `http.py`, `stores.py`, `app.py`, `shim.py`, `tests/security/`) | `security-review` | `/security-review`, then the skill | `$security-review` | the skill (plus `/security:analyze` if installed) |

**When Claude Code's own skills are not available.** Codex and Gemini have no built-in simplify, verify or run, so the repository skills carry those steps for them. In addition, when a unit is written by any agent other than Claude Code, ECC runs a **Claude skills pass** after the author's attempt and before the gates: a fresh Claude Code session in the unit's worktree runs `/simplify`, `/verify` and `/code-review` (and `/security-review` for high-risk units) with these skills, and commits any fixes within the unit's scope. Outside ECC (for example a Gemini build in Antigravity), run the same pass by hand before handing off:

```sh
claude -p "Read AGENTS.md. For this branch's changes against main, run /simplify, /verify and /code-review (and /security-review if the unit is high risk), using the skills in .agents/skills. Fix what they find within the unit's scope and commit on this branch."
```

Later these skills will also be distributed from ctxd's shared skill library; the files here stay the source of truth.

## Rules

- Work only inside this repository. v1 (`~/Documents/GitHub/my-research-mcp-server`) and `~/arxiv-papers` are read-only: never edit them, and never open the v1 database except through the legacy import job.
- A prior attempt at M0 lives read-only in `~/Documents/GitHub/my-research-mcp`. You may read it for ideas; never copy from it without checking against the specification, and never edit it.
- Never read the Keychain, client configs or any real credential. Use `FakeProvider`, recorded fixtures and the fakes in `research_mcp.testing`. Tests pass with the network blocked.
- Never print, log, commit or put in fixtures any secret, token or password. Fixtures are recorded with credentials removed.
- Adapters (`src/research_mcp/sources/`) only translate: no HTTP library imports, no sleeping, no retries, no secrets, no file writes.
- No tool may block the event loop; CPU work goes to worker subprocesses (`platform/workers.py`).
- Every change needs tests. Test folders have no `__init__.py` (pytest runs in importlib mode); never add one.
- Keep `tools/ci.sh --python-only` green.
- Do not use em dashes or en dashes in prose, comments or UI text.
- Never run `git push`, `security`, `launchctl` or anything that changes the Mac outside this repository.

## Commands

```sh
uv sync --frozen
tools/ci.sh --python-only
uv run pytest -q
python3 tools/gen_test_plan.py      # after changing the test list
python3 tools/gen_m0_plan.py        # after changing SPEC 12.3 or Appendix A
```
