---
name: review-change
description: Review a unit's changes against the component's LLD (docs/lld, newest version), its PRD acceptance criteria, the test plan (docs/test) and AGENTS.md, and report findings by severity. Use as the author's self-review before handoff, and as the PR reviewer or verifier.
metadata:
  version: 1.1.0
---

# Review a change

Review `git diff $(git merge-base HEAD main)...HEAD` for the unit named in the branch (`ecc/<run>/<unit>`).

## Checklist

1. **Contract.** Every name, signature, field, table, setting and error code matches the LLD sections the unit implements (the LLDs own every name; AGENTS.md). Anything the LLD does not mention is not added.
2. **Clarifications.** Every LLD clarification marked (SPEC-v2 0.6) that concerns this unit holds.
3. **Tests and trace.** Each acceptance criterion the unit owns (its task in docs/build/M0-plan-v1.md) has a test whose docstring starts with `@spec <ID>:` and that tests the behavior the criterion states, including refusals; the behavior's entry point in code carries `@spec <ID>`; `node tools/sdd/cli.mjs check` passes. No test was weakened, skipped or deleted.
4. **Scope.** Only the unit's files changed; no `__init__.py` under `tests/`; no edits to `pyproject.toml`, `uv.lock` or package `__init__.py` outside M0-01.
5. **Rules.** Adapters only translate; nothing blocks the event loop; no secrets in code, logs or fixtures; tests pass with the network blocked.
6. **Simplicity.** Nothing the simplify-change skill would remove.

## Report

One finding per line: `severity | file:line | what is wrong and what the LLD or criterion requires`. Severities: `blocker` (violates the LLD, a criterion or a rule), `major` (a likely defect or a missing case), `minor` (clarity). If there are none, say so. When reviewing for ECC, end with the verdict line the prompt specifies.

## Changelog

| Version | Date | Change |
| --- | --- | --- |
| 1.1.0 | 2026-10-22 | SDD adoption: LLDs own names, tests and code cite criteria with `@spec`, clarifications live in the LLDs |
| 1.0.0 | 2026-10-20 | First release |
