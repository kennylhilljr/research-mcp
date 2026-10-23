---
title: "Adopt spec-driven development fully, before the next build"
status: proposed
owner: "Kenny Hill"
date: 2026-10-22
---

# ADR 0013: Adopt spec-driven development fully, before the next build

> **Owner:** C · **Persona:** `architect` drafts; the owner decides.

## Context

Research MCP v2 had a PRD (v4), seven component PRDs, an HLD (v3), a detailed SPEC (v2) and a generated test plan (v3), none in the SDD framework's format. Its first ECC run built five small M0 units (M0-01 to M0-05: scaffold, identifiers, core contracts, settings, secrets) and stopped. The owner wants the repository on the latest sdd_framework before ECC runs again, and judged that nothing built so far is large enough to justify incremental adoption.

## Options

| Option | Benefits | Costs |
| --- | --- | --- |
| 1. Adopt incrementally: write specs for components as they change; checks stay advisory until components reach AUDITED | No big-bang effort | Two styles coexist; ECC units would cite both |
| 2. Adopt fully now: restructure every document onto the SDD templates, then build | One trace from criterion to test to code before the next run; ECC roles play SDD personas | Upfront restructure; every document needs the owner's review at the gates |
| 3. Do not adopt | No cost | Agents keep two ID schemes and no checked trace |

## Decision

Option 2, as directed by the owner on 2026-10-22, pending the owner's acceptance of this ADR:

- The SDD toolkit (skills, personas, hooks, spec-lint, trace-check, templates) is installed with `sdd adopt`, and the checks run in enforced mode in `tools/ci.sh`.
- The documents are rewritten as the next versions on the SDD templates: `docs/vision/vision-v1.md`, the parent `docs/prd/PRD-v5.md`, eight component PRDs, `docs/spec/SPEC-v3.md` (the system high level design), one LLD per component, `docs/test/test-plan-v1.md` and the milestone plan `docs/build/M0-plan-v1.md`. The superseded originals move unchanged to `docs-archive/`.
- IDs keep their numbers in the SDD format: `FR-PLAT-15` becomes `PLAT-FR-15`; acceptance tests `AT-PLAT-31` become acceptance criteria `PLAT-31` in EARS; goals G1 to G8 become `OUT-1` to `OUT-8`; `NFR-01` becomes `NFR-1`. Each PRD lists its earlier IDs.
- Tests cite criteria in the first line of their docstring (`"""@spec PLAT-31: ..."""`) and behavior entry points carry `@spec`.
- `tools/gen_m0_plan.py` reads the milestone plan; `tools/gen_test_plan.py` is retired, because the criteria now live in the PRDs and trace-check derives coverage.
- ECC's team roles play the SDD personas through the `personas` map in `.orchestration/team.json`.

## Consequences

- Every new document is a draft. Before the next ECC run, the owner approves the problem framing (intake checkpoint), the PRDs (Gate 1), the SPEC (Gate 2) and each LLD (Gate 3).
- The unmerged branches of the first run (`ecc/rm-m0b/M0-06`, `ecc/rm-m0b/M0-08`, `ecc/rm-m0b/practices-1`) cite the old IDs and are not merged; the next run rebuilds those units from the new plan.
- Approved documents become frozen: a change produces the next numbered version, and the protect-approved hook blocks edits to approved files.
