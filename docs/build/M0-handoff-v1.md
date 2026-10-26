---
title: "M0 handoff"
type: handoff
version: 1
status: draft
owner: "Kenny Hill"
milestone: M0
artifact_type: handoff
date: 2026-10-25
---

# M0 handoff (v1)

The record of what M0 built and the evidence that it works, written after the product owners rejected the first milestone review of ECC run `rm-m0f` (report `rm-m0f-M0-product-v1.md` under the ECC state folder). It answers the findings of that report that can be answered in the repository. The owner checks OC-01 and OC-02 are run on the owner's Mac and recorded below when done.

## What changed

> **Owner:** A · **Persona:** `implementer`

| Task | Criteria | Files | SPEC or LLD section |
| --- | --- | --- | --- |
| M0-01 to M0-05 | as in [M0 plan v4](M0-plan-v4.md) section 2 | as in the plan | merged in run `rm-m0b` |
| M0-06 to M0-23 | as in [M0 plan v4](M0-plan-v4.md) section 2 | as in the plan | merged in run `rm-m0f`, 2026-10-23 to 2026-10-24 |
| Closing fix: doctor reads schemas through the store | HLTH-40 | `services/doctor.py`, `platform/stores.py` (`read_schema_version`), `tests/unit/test_cli.py` | LLD-platform-v2 5.1; LLD-health-v2 5.9 |
| Closing fix: the CLI installs the redacting log handlers | PLAT-40 | `cli.py` (`_settings`), `tests/unit/test_cli.py` | LLD-platform-v2 4.3 |
| Plan status | none | `docs/build/M0-plan-v4.md`: M0-06 to M0-23 set to `done`, so trace-check counts their criteria | M0 plan v4 section 2 |
| Test plan v5 (draft) | none | `docs/test/test-plan-v5.md`: the M0 gate (1.4) names plan v4, not plan v1 | test plan v4 1.4 |

## Evidence

> **Owner:** A · **Persona:** `implementer`

| Check | Result |
| --- | --- |
| Tests (command, run, result) | `tools/ci.sh` (full) on branch `m0-close` at `7317a7e`: 730 passed, coverage 95.27% (gate 85%), exit 0. |
| Typecheck or lint | ruff check, ruff format --check and strict mypy (47 source files) clean, inside the same run. |
| spec-lint | 0 errors, 12 warnings (ADR front matter only). |
| trace-check, with the test report (`--results`) | 0 errors, 14 warnings, with all 23 tasks `done`. This SDD version has no `--results` option; the full pytest run above is the test report. A separate scan of the task table found a test citing `@spec <ID>` for each of its 99 criteria. |
| Criteria passing, failing, deferred or excepted | Every criterion in the task table has a passing test that cites it. Deferred by the plan: SRCH-34 (M1; M0-13 records searches through a no-op port). |
| Code review (reviewer, link) | Each unit was reviewed by the ECC persona panel (pr_reviewer, security_reviewer, architect where the risk required it) and verified by the verifier; the per-unit record is in the product report's retrospective. |
| M0-22 verifier verdict | Recorded `inconclusive` in `rm-m0f` only because the verifier's sandbox refused to run `node tools/sdd/cli.mjs check`. Its other checks passed, including two decoy experiments: the shim sends only the Keychain token, and with no Keychain item it sends nothing and returns `auth_failed`. Re-checked here: `tests/unit/test_shim.py` and `tests/security/test_no_secret_at_rest.py` pass (7 tests), and the SDD check passes inside the full CI run above. |
| Owner check OC-01 (install, doctor green, a client searches three sources through the shim) | Not run yet. |
| Owner check OC-02 (the daemon reads every Keychain item with no prompt; doctor shows each credential state) | Not run yet. |

## Verification

> **Owner:** A · **Persona:** `verifier` (independent of the implementer)

*Left for the verifier and the product owners in the next milestone review.*

## Follow-ups

> **Owner:** A · **Persona:** `implementer`

| Item | Type | Severity or priority |
| --- | --- | --- |
| Run and record OC-01 and OC-02 | owner check | blocks the M0 review |
| Decide each minor drift finding of the architect (redact.py `reveal`, `normalize_url` trailing slashes, `build_app` seams, SecretCache load location, jobs and scheduler layer, `/api/status` fields, `log_rotate` schedule, README) | owner decision | minor |
| Correct LLD-sources-v2 5.2 selection row 8 (`skipped_unhealthy` for `rate_limited` under `auto`) | LLD correction | minor |
| SPEC-v5 sections 14 and 17 still link M0 plan v1 | doc correction | minor |
