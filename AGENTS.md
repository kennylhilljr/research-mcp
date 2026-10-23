# Agent instructions for Research MCP v2

This file is the repository instruction adapter. Every person and every agent reads it first. It points to the documents, the scope map and the rules; it is not organizational authority by itself. It is human-owned: agents may propose changes but never edit it without the owner's approval.

Framework: spec-driven development (SDD) 1.1.0 ([ADR 0013](docs/adr/0013-adopt-spec-driven-development.md)). Owner: Kenny Hill. Builds run under the ECC orchestrator with Claude in every role ([.orchestration/PILOT-M0.md](.orchestration/PILOT-M0.md)).

## Read first

- [docs/README.md](docs/README.md) is the doc map: the scope map, the artifact index and each document's status. The latest approved documents are the source of truth. If code and docs disagree, raise it; do not silently diverge.
- [docs/standards/spec-driven-development-v2.md](docs/standards/spec-driven-development-v2.md) defines scope, the delivery artifact chain, decision owners, gates, IDs and evidence. [docs/standards/agent-personas-v2.md](docs/standards/agent-personas-v2.md) defines the human and agent personas and the RASCI.
- [docs/scope/scope-map.yaml](docs/scope/scope-map.yaml) names the scopes this repository serves (L3 `research-mcp`).
- For a work unit: its task in [the M0 plan](docs/build/M0-plan-v1.md), the LLD sections it implements, the acceptance criteria it owns (section 2.4 of each component PRD), and any clarifications the plan lists for it.

## Documents

| Artifact | Where | Owns |
| --- | --- | --- |
| Vision | [docs/vision/vision-v1.md](docs/vision/vision-v1.md) | Why, for whom, the outcomes |
| Parent PRD | [docs/prd/PRD-v5.md](docs/prd/PRD-v5.md) | Outcomes `OUT-n`, cross-cutting `NFR-n`, invariants `INV-n`, components, milestones |
| Component PRDs | [docs/prd/components/](docs/prd/components/) | Requirements `<PREFIX>-FR-n` and acceptance criteria `<PREFIX>-n` (PLAT, SEC, SRC, SRCH, CACHE, HLTH, UI, MIG) |
| SPEC (system high level design) | [docs/spec/SPEC-v3.md](docs/spec/SPEC-v3.md) and [docs/adr/](docs/adr/) | The shape of the system and its decisions |
| LLDs, one per component | [docs/lld/](docs/lld/) | Every name (modules, classes, functions, tables, columns, settings keys, Keychain items, routes, error codes), every interface and format |
| Test plan | [docs/test/test-plan-v1.md](docs/test/test-plan-v1.md) | How each criterion is verified; owner checks; milestone exit gates |
| Milestone plan | [docs/build/M0-plan-v1.md](docs/build/M0-plan-v1.md) | Work units, their criteria, scope and dependencies |
| Runbooks and contracts | [docs/runbooks/](docs/runbooks/), [docs/contracts/](docs/contracts/) | Operating steps; the MCP prompt texts |

- **The LLDs own every name.** Code follows them. If an LLD is wrong or contradicts a PRD or the test plan, do not pick a side: record the conflict in your handoff and build everything it does not touch.
- **Clarifications from the first M0 attempt** (marked "SPEC-v2 0.6" in the LLDs and listed in the M0 plan) are requirements.
- **Docs are versioned.** To change one, add the next `-vN` file and update links; never edit an earlier version, and never edit an approved one. `docs-archive/` holds the superseded originals (PRD v4, HLD v3, SPEC v1 and v2, TEST-PLAN v3, the migration doc and the design review); it is read-only history.
- **Generated files** are never edited by hand; run their generators: `.orchestration/plan-m0.json` (`tools/gen_m0_plan.py`), `docs/README.md` doc map (`node tools/sdd/cli.mjs docmap`), `docs/guide/catalog.md` (`node tools/sdd/cli.mjs catalog`), `docs/trace/coverage.md` (`node tools/trace-check/trace-check.mjs --write`), `docs/generated/*`.

## Three separate concepts

- **Organizational scope** is L0 to L3, recorded in the scope map and in `scope_level` and `scope_name`.
- **The delivery artifact chain** is unnumbered: vision, Product specification, high level design, low level design, plans, code, tests, handoff and evidence.
- **Gates 1 to 3** are approval checkpoints. They do not correspond to scope levels L1 to L3.

## Decision owners

Every section of every template is tagged:

- **H** Human decision: a person supplies and approves it. Interview, organize and edit; never invent. Ask, or list it as an open question (`- [ ] Q: ...`).
- **C** Human decision with agent draft: draft options, expose assumptions, sources and tradeoffs; a person selects and approves.
- **A** Agent prepared from approved inputs: prepare it as the persona named in the template; never change approved intent; it must pass the checks.

The owner decides the problem, outcomes, scope, priorities, constraints and acceptance, and approves every gate. Agents prepare; they are never accountable.

## SDD rules

- **Approvals are human.** The intake checkpoint approves the problem framing (PRD section 1); Gate 1 the Product specification; Gate 2 the SPEC; Gate 3 the LLD for one component. Agents never set `status: approved`, `approved_by` or `approved`. Name the component when you run a gated skill (`/sdd-lld platform`).
- **Every requirement has a stable ID**, never renumbered and never reused. A change of actor, trigger, response, target or test obligation gets a new ID; the old one goes in the PRD's ID history table.
- **Tests and code cite the criteria they satisfy.** A test's docstring starts with the criterion: `"""@spec PLAT-31: ..."""`. The entry point of the behavior in code carries a comment `# @spec PLAT-31`; helpers do not. A link is structural evidence; it does not prove meaning.
- **Drift is decided by a person.** Verification reports a disagreement; the owner names the first artifact in the trace that no longer reflects approved intent; that artifact is corrected first, then what depends on it.
- **A change that crosses components stops for a person** and goes into the next SPEC version, with an ADR when the system's shape changes.
- **Never verify your own work.** The `verifier` persona checks work it did not produce.
- **Rationale inferred from existing code** is tagged `[inferred]` until the owner confirms it.

## Branches

- Every unit has one branch, `ecc/<run>/<unit>`, created by ECC from `main` after the unit's dependencies merged. Work only on the branch you are on.
- Commit your work there. Never push, never create or switch branches, never rebase or rewrite history, never commit to `main`. Only ECC's merge queue writes `main`, after review and verification pass.
- Before each attempt ECC merges the current `main` into your branch. If it did, keep both sides; your unit must pass on top of the merged `main`. If ECC reports a merge conflict, resolving it is the first part of your attempt.
- Stay inside your unit's scope (its file list). If you need a file another unit owns and it is not on your branch yet, do not create it: finish what you can, then hand off with status `blocked`, naming the file and the unit. ECC re-runs you after that unit merges.

## Repairs

- A failed attempt comes back with a brief: the failing gate output, or the reviewers' findings. Fix exactly those, keep everything that passed, and say in the handoff how each finding was addressed. Reviewers re-check the same findings.
- Never weaken, skip or delete a test to make it pass. A test that contradicts a criterion is a conflict to record, not a test to change.

## Personas

Each ECC role plays an SDD persona from `.claude/agents/` (`personas` in `.orchestration/team.json`): the coder is the `implementer`; the PR reviewer and the QA verifier are the `verifier`; the security reviewer is the `security-reviewer`; the architect is the `architect`; the product owners are the `product-writer`; the learning steward is the `doc-steward`. Stay inside your persona's limits: never write an H section, never approve, and never verify your own work.

## Skills while building (every agent)

Claude Code is the only agent that builds and reviews this repository (`.orchestration/config.yaml`). The build skills live at `.agents/skills/`, and `.claude/skills` points to that folder. They are required, not optional: skip one only when its trigger does not apply, and say so in your handoff.

| When | Skill | In Claude Code |
|---|---|---|
| While developing anything you can run (a module API, an MCP tool, the daemon, the CLI) | `run-research-mcp` | `/run`, following the skill |
| After the change works, before verifying | `simplify-change` | `/simplify` |
| After the acceptance commands and `tools/ci.sh --python-only` pass | `verify-change` | `/verify`, following the skill |
| Before your handoff (self-review), and when reviewing | `review-change` | `/code-review`, then the skill's checklist |
| High-risk units (clarification rows in the M0 plan, `platform/secrets.py`, `redact.py`, `http.py`, `stores.py`, `app.py`, `shim.py`, `tests/security/`) | `security-review` | `/security-review`, then the skill |

Because the author runs these skills in its own session, ECC's separate skills pass is off. Reviewers are also Claude: their independence comes from their persona and their own session, not from a different provider.

The SDD skills (`sdd-intake`, `sdd-spec`, `sdd-clarify`, `sdd-hld`, `sdd-lld`, `sdd-tasks`, `sdd-implement`, `sdd-verify`, `sdd-triage`, `sdd-adopt`) produce and check the documents:

| Step | Skill | Persona | Human checkpoint |
| --- | --- | --- | --- |
| Capture intent | `/sdd-intake` | `analyst` | The owner answers the seed questions; intake checkpoint |
| Write the PRDs | `/sdd-spec` | `product-writer` | |
| Close gaps | `/sdd-clarify` | `product-writer`, `verifier` | Gate 1: approve the Product specification |
| High level design | `/sdd-hld` | `architect`, `security-reviewer`, `sre` | Gate 2: choose ADRs, approve the SPEC |
| Low level design | `/sdd-lld <component>` | `component-designer`, `test-architect` | Gate 3: approve contracts, schema, authorization, test strategy |
| Plan | `/sdd-tasks <component>` | `planner` | |
| Build | ECC, or `/sdd-implement <milestone>` | `implementer` | Review by the team; the owner accepts the milestone |
| Verify | `/sdd-verify` | `verifier` | The owner decides each disagreement |
| Triage support work | `/sdd-triage` | `sre`, `verifier`, `planner` | The owner confirms S0 and S1 |

Later these skills will also be distributed from ctxd's shared skill library; the files here stay the source of truth.

## Lessons

The team's practices evolve during a build (TEAM-DELIVERY v7). Every reviewer, the verifier, the architect and the designer may add `lessons` to their verdicts; when you hand off, add a `Lesson:` line to your handoff `notes` for anything future units should do differently (for example "Lesson: the LLD does not say whether trailing dots are part of a DOI; I assumed not"). The delivery lead turns lessons that generalize into this file, the skills and [.agents/LESSONS.md](.agents/LESSONS.md), and those changes are reviewed and merged like code. Read the ledger before you start; it records why each rule exists.

## Rules

- Work only inside this repository. v1 (`~/Documents/GitHub/my-research-mcp-server`) and `~/arxiv-papers` are read-only: never edit them, and never open the v1 database except through the legacy import job.
- A prior attempt at M0 lives read-only in `~/Documents/GitHub/my-research-mcp`. You may read it for ideas; never copy from it without checking against the LLDs, and never edit it.
- Never read the Keychain, client configs or any real credential. Use `FakeProvider`, recorded fixtures and the fakes in `research_mcp.testing`. Tests pass with the network blocked.
- Never print, log, commit or put in fixtures any secret, token or password. Fixtures are recorded with credentials removed.
- Adapters (`src/research_mcp/sources/`) only translate: no HTTP library imports, no sleeping, no retries, no secrets, no file writes.
- No tool may block the event loop; CPU work goes to worker subprocesses (`platform/workers.py`).
- Every change needs tests. Test folders have no `__init__.py` (pytest runs in importlib mode); never add one.
- Keep `tools/ci.sh --python-only` green; it includes `node tools/sdd/cli.mjs check`.
- Do not use em dashes or en dashes in prose, comments or UI text.
- Never start another agent CLI (`claude` or any other) inside a unit: the unit sandbox cannot run it, and ECC's reviewers review every unit.
- Never run `git push`, `security`, `launchctl` or anything that changes the Mac outside this repository.

## Commands

```sh
uv sync --frozen
tools/ci.sh --python-only               # lint, types, tests, generator checks, SDD checks
uv run pytest -q
python3 tools/gen_m0_plan.py            # after changing the task table in docs/build/M0-plan-v1.md
node tools/sdd/cli.mjs check            # spec-lint and trace-check
node tools/sdd/cli.mjs docmap           # after adding or versioning a document
node tools/sdd/cli.mjs new --next <path>  # the next version of a document
node tools/sdd/cli.mjs doctor           # check the local environment (Node 20 or later)
```

## Definition of done

A change is done when `tools/ci.sh --python-only` passes (including the SDD checks), every new or changed behavior cites its criterion with `@spec` in its test and at its entry point, the build skills ran (or the handoff says why one did not apply), the docs and the doc map are current, and the handoff records what was verified and the test results.
