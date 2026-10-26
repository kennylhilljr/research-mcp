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

The record of what M0 built and the evidence that it works, written after the product owners rejected the first milestone review of ECC run `rm-m0f` (report `rm-m0f-M0-product-v1.md` under the ECC state folder). It answers the findings of that report that can be answered in the repository. The owner ran the owner checks OC-01 and OC-02 on his Mac on 2026-10-25; the results are below.

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
| Owner check OC-01 (install, doctor green, a client searches three sources through the shim) | Passed, 2026-10-25, owner's Mac, `main` at `640fbb8`. `research-mcp install` wrote the launchd jobs; with `contact.email` set in `~/.config/research-mcp/config.toml`, `research-mcp doctor` reported `daemon_alive`, `keychain_readable`, `contact_email` and `schema_versions` all `ok` (exit 0). Claude Code, registered with `claude mcp add research -- <venv>/bin/research-mcp stdio`, searched "graph neural networks" through the shim: `source_status` arxiv `ok` (10 results, 2227 ms), crossref `ok` (10, 676 ms), openalex `ok` (10, 1203 ms). |
| Owner check OC-02 (the daemon reads every Keychain item with no prompt; doctor shows each credential state) | Passed, 2026-10-25, owner's Mac. After `launchctl kickstart -k gui/$UID/local.research-mcpd` the daemon restarted and read `DAEMON_TOKEN`, the only Keychain item in M0, with no Keychain prompt; `/healthz` answered 200, `daemon.err.log` stayed empty, and doctor reported `keychain_readable: ok`. Owner decision (2026-10-25): in M0, `keychain_readable` is the credential state doctor shows, because `DAEMON_TOKEN` is the only credential; the per-credential checks (`credential:<NAME>`) arrive with the credential service in M1, as LLD-health-v2 5.9 schedules them. |

## Verification

> **Owner:** A · **Persona:** `verifier` (independent of the implementer)

*Left for the verifier and the product owners in the next milestone review.*

## Owner decisions on the architect's drift findings

> **Owner:** A · **Persona:** `implementer`

The owner decided each open drift finding of the `rm-m0f` architect report on 2026-10-25.

| Finding | Decision | Where it lands |
| --- | --- | --- |
| (major) `services/doctor.py` builds its own `httpx.AsyncClient` for `/healthz`, while LLD-health-v2 5.9 says doctor builds an `HttpClient` | Keep `httpx.AsyncClient` for the loopback `/healthz` check, as LLD-platform-v2 5.1 allows and the shim does. `HttpClient` is the port for upstream sources: it allows only listed hosts and retries three times, which breaks doctor's 3 s liveness budget. Doctor builds an `HttpClient` in M1, when it gains source probes. The SQLite part of this finding was fixed in `7317a7e`. | LLD-health-v2 next version: 5.9 says the `HttpClient` serves the source probes |
| `platform/redact.py` calls `Secret.reveal()` | Code stands: the redactor must hold the revealed value to mask it (LLD-platform-v2 4.3). | LLD-platform-v2 next version: 4.1 and PLAT-FR-11 name `redact.py` among the callers of `reveal` |
| `core/ids.py` `normalize_url` strips every trailing slash | Code stands: removing one slash is not idempotent (SRCH-15). | LLD-search-v2 next version: 5.2 says every trailing slash |
| `SecretCache` is built and loaded in the `build_app` lifespan | Code stands: it follows LLD-platform-v2 2.3. | LLD-platform-v2 next version: 5.10 step 5 matches 2.3 |
| `jobs.py` and `scheduler.py` sit in `platform/` | Code stands: it matches the layout in LLD-platform-v2 5.1. | SPEC-v5 3 and LLD-platform-v2 5.2 layer diagrams, next versions |
| `build_app` redactor seam; `launchctl` typed `Any` | Keep the redactor seam; type `launchctl` as `LaunchctlPort`. | M1 follow-up (code) and LLD-platform-v2 2.3 |
| `log_rotate` runs at start only when overdue | Run it every 15 minutes and once at start, as LLD-platform-v2 5.10 says. | M1 follow-up (code) |
| README out of date (clients over stdio or HTTP, `token_keychain`, daemon and install "planned") | Update the README. | M1 follow-up (docs) |
| `/api/status` returns fewer fields than LLD-platform-v2 4.5 | Deferred: credential metadata, quotas, cache stats, disk, archive target and notifications arrive with their components in M1 and M2. | M1 and M2 plans |

## Follow-ups

> **Owner:** A · **Persona:** `implementer`

| Item | Type | Severity or priority |
| --- | --- | --- |
| Type `launchctl` as `LaunchctlPort` in `build_app` | code | minor, M1 |
| `log_rotate` every 15 minutes and once at start | code | minor, M1 |
| Update the README (shim-only clients, no `token_keychain`, daemon and install built) | docs | minor, M1 |
| LLD corrections from the owner decisions above (LLD-health-v2 5.9, LLD-platform-v2 2.3, 4.1, 5.10, 5.2, LLD-search-v2 5.2, SPEC-v5 3) | LLD correction | minor, next versions |
| Correct LLD-sources-v2 5.2 selection row 8 (`skipped_unhealthy` for `rate_limited` under `auto`) | LLD correction | minor |
| SPEC-v5 sections 14 and 17 still link M0 plan v1 | doc correction | minor |
