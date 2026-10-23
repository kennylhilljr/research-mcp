---
title: "Health, Credentials and Notifications"
type: prd-component
version: 4
status: draft
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
prefix: HLTH
component: health
parent: docs/prd/PRD-v7.md
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
supersedes: docs/prd/components/PRD-health-v3.md
date: 2026-10-22
---

# Component PRD: Health, Credentials and Notifications (v4)

Version 4 records the owner's Gate 1 answers of 2026-10-22. It supersedes [PRD-health v3](PRD-health-v3.md), which moved [PRD-health v2](../../../docs-archive/prd/components/PRD-health-v2.md) onto the SDD component template with new IDs (section 2.16). Owner answers are cited as "(owner decision, 2026-10-22)"; changed and new IDs are listed in section 2.15. Parent: [PRD v7](../PRD-v7.md), outcomes OUT-4 and OUT-5. Vision: [vision v2](../../vision/vision-v2.md). Design: [SPEC v3](../../spec/SPEC-v3.md) section 7 and [LLD-health v1](../../lld/LLD-health-v1.md).

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

- Breadth only helps if the owner knows which sources work (PRD-health v2 section 1).
- **Breakage is silent.** Three sources are degraded by upstream changes today (OpenAlex, Semantic Scholar, Crossref) and one has an announced shutdown (Google Programmable Search, 2027-01-01). Nothing in v1 noticed (PRD-v4 2.2; REVIEW-v1 4).
- **Credentials are invisible.** Nobody is told when a key expires or stops working (PRD-v4 2.3).
- v1 has no health or readiness checks, no metrics, no per-source error rate, latency or quota tracking, and no credential-expiry detection; undocumented endpoints can return 200 with no results, which v1 reports as "0 results" (REVIEW-v1 2.6; OPS-15).
- The owner decided that v2 must be maintainable and monitored, and must notify the owner when a credential is expiring or invalid so it can be rotated (owner decision D5).
- **Why now.** v2 is being rebuilt now, and the upstream breakage is current: the live probes of 2026-10-19 found OpenAlex keyless calls rejected for budget, Semantic Scholar bulk search ignoring `limit`, Crossref throttling clients without a contact email, and Google Programmable Search closed to new customers ahead of its shutdown on 2027-01-01 (PRD-v7 1.1).

This component watches every source and every credential, tells the owner when something changes, and says exactly how to fix it (PRD-health v2 section 1).

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| The owner, passively (macOS notifications; optional OpenClaw inbox message) | Be told, for example, "GitHub token expires in 7 days" or "OpenAlex is rate limited" (PRD-v4 4) | One person (PRD-v6 1.2) |
| The owner, directly (local web UI) | Check the source board and reload a key after rotating it in the Keychain (PRD-v4 4) | One person (PRD-v6 1.2) |
| The owner, through an agent (Claude Code, Claude desktop, Codex, OpenClaw agents) | Read status through MCP resources and tools without secrets (PRD-v4 4; PRD-health v2 FR-HLTH-42) | One person (PRD-v6 1.2) |

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- Probes, source and credential states, quotas, notifications and `doctor` (PRD-v4 5).
- Call telemetry and rollups, credential metadata and validation, the daily digest and quiet hours, and the liveness and readiness endpoints (PRD-health v2 section 2).

| Non-goal | Why it is excluded |
| --- | --- |
| Remote or multi-user access | The server binds to loopback on the owner's Mac (PRD-v4 3.2) |

This component has no non-goals beyond the parent non-goals in PRD-v6 1.3 (owner decision, 2026-10-22).

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

The parent outcomes OUT-1 to OUT-8 suffice; no component outcome is added beyond the ones below (owner decision, 2026-10-22). HLTH-OUT-1 to HLTH-OUT-5 are due at the M1 exit, except measures the parent ties to 30 days after cutover (owner decision, 2026-10-22). PRD-v6 1.4 ties every OUT-5 measure to 30 days after cutover, so HLTH-OUT-4 and HLTH-OUT-5 follow that date; their behavior is still tested at M1 (HLTH-20, HLTH-30).

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |
| HLTH-OUT-1 | Sources that have a probe | v1 has no health checks (REVIEW-v1 2.6) | Every source (PRD-v4 G4) | M1 exit (PRD-v6 OUT-4; owner decision, 2026-10-22) |
| HLTH-OUT-2 | Time for a detected source state change to reach the owner | v1 notices nothing (PRD-v4 2.2) | Within 15 minutes, outside quiet hours (PRD-v4 G4) | M1 exit (PRD-v6 OUT-4; owner decision, 2026-10-22) |
| HLTH-OUT-3 | Time for the watchdog to report a dead daemon | No watchdog in v1 (REVIEW-v1 2.6) | Within 15 minutes (PRD-v4 G4) | M1 exit (PRD-v6 OUT-4; owner decision, 2026-10-22) |
| HLTH-OUT-4 | Expiring credential notices | Nobody is told (PRD-v4 2.3) | At 14, 7, 3 and 1 days (PRD-v4 G5) | 30 days after cutover, as the parent ties OUT-5 (PRD-v6 1.4; owner decision, 2026-10-22) |
| HLTH-OUT-5 | Time to an invalid credential notice | Nobody is told (PRD-v4 2.3) | Within one probe cycle (PRD-v4 G5) | 30 days after cutover, as the parent ties OUT-5 (PRD-v6 1.4; owner decision, 2026-10-22) |
| HLTH-OUT-6 | Source state changes noticed by the owner before an agent hit them | Not stated | 90% or more (PRD-v4 7) | 30 days after cutover (PRD-v4 7; PRD-v6 OUT-4) |
| HLTH-OUT-7 | Credentials that expired without a prior notice | Not stated | 0 (PRD-v4 7) | 30 days after cutover (PRD-v4 7; PRD-v6 OUT-5) |

## 1.5 Leaps of faith

> **Owner:** H · **Persona:** none

Drafted from bets and risks the sources already state (owner decision, 2026-10-22, to draft them).

| Leap of faith | How we will validate it | By when |
| --- | --- | --- |
| Probes that check the response shape, not only the status, notice upstream drift before an agent hits it. The sources state the risk: upstream APIs change faster than one person can follow (PRD-v6 2.10), and three sources degraded unnoticed in v1 (PRD-v6 1.1). (proposed for owner approval) | HLTH-3 and HLTH-2 pass; afterward the 30-day metric HLTH-OUT-6 (PRD-v6 OUT-4) | M1 exit |
| Providers expose enough expiry and validity signals (expiry headers, free account or rate-limit endpoints, the Google token refresh), and `rotate_by` covers keys that never expire, so no credential expires without a notice. The sources state the target of 0 expired without a prior notice (PRD-v6 OUT-5) and the fallback for keys with no expiry (HLTH-FR-21, HLTH-FR-22). (proposed for owner approval) | HLTH-21, HLTH-22, HLTH-24 and HLTH-25 pass; afterward the 30-day metric HLTH-OUT-7 (PRD-v6 OUT-5) | M1 exit |
| The daemon can read the Keychain, and a locked or unreadable Keychain shows as one state and one notification, not a notice per key. The sources state the risk: the Keychain is locked or unreadable, for example right after login (PRD-v6 2.10). (proposed for owner approval) | Owner check OC-02 on the Mac (M0) and HLTH-13 | M1 exit |

## 1.6 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

The owner confirmed HLTH-INV-1 to HLTH-INV-5, taken from the "never" statements of PRD-health v2, as this component's invariants (owner decision, 2026-10-22). Each names at least one P1 criterion.

| ID | The system must never | Source (regulation, policy, contract) | P1 criterion |
| --- | --- | --- | --- |
| HLTH-INV-1 | Store a credential value; only metadata is stored (same rule as SEC-INV-3, for `state.db`) | PRD-health v2 FR-HLTH-20; PRD-v4 NFR-03 | HLTH-43 (new); SEC-3 checks the metadata lookup never reads a value |
| HLTH-INV-2 | Put a secret value or a full URL with query parameters in notification text (part of SEC-INV-4) | PRD-health v2 FR-HLTH-34; PRD-v4 NFR-04 | HLTH-34 |
| HLTH-INV-3 | Put a login token in a notification (part of SEC-INV-4) | PRD-health v2 FR-HLTH-32 | HLTH-32; HLTH-34 |
| HLTH-INV-4 | Spend a billed query to validate a metered source when a free method exists | PRD-health v2 FR-HLTH-21 | HLTH-25 |
| HLTH-INV-5 | Store a Google sign-in token; only the account email and the token expiry are stored (overlaps SEC-INV-11 and SRC-INV-5) | PRD-health v2 FR-HLTH-25 | HLTH-24 |

## 1.7 Known constraints and decisions

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

| Decision or constraint | Status (made or open) | Rationale or link |
| --- | --- | --- |
| v2 is monitored and notifies the owner when a credential is expiring or invalid | Made | Owner decision D5 (REVIEW-v1 1) |
| Secrets live in the macOS Keychain; configuration holds references only, including the webhook token | Made | ADR 0003; PRD-v4 NFR-03 |
| The owner's Google sign-in for Vertex AI Search is the one secret outside the Keychain; `gcloud` stores it and v2 never copies it | Made | ADR 0012; PRD-v4 NFR-03 |
| One daemon per Mac owns the HTTP clients, rate limiters, stores and the scheduler | Made | ADR 0002; PRD-v4 NFR-01 |
| Nothing listens on a non-loopback address; every HTTP request except `/healthz` and `/readyz` needs a bearer token or a UI session | Made | PRD-v4 NFR-07 |
| Web-search sources are optional, off until configured and capped per day | Made | ADR 0012 |
| Second notification channel: OpenClaw inbox through a configurable webhook | Made (O5 closed) | PRD-v6 1.6; owner decision, 2026-10-22 |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

---

## 2.1 Customer discovery

> **Owner:** A · **Persona:** `analyst`

The deep review of v1 (REVIEW-v1) is the research behind this component. Its findings:

- OPS-15: no health or readiness checks, metrics, per-source error rate, latency or quota tracking, or credential-expiry detection; format changes upstream return 200 with no results.
- OPS-16: Google Custom Search shuts down on 2027-01-01; OpenAlex needs an API key; Brave is metered. The review proposed a `deprecated` source state with a countdown and budget caps.
- OPS-23: no budgets for metered providers; the review proposed daily and monthly caps with `quota_low` alerts.
- OPS-24: Google sign-in refresh failures come back as an opaque string; the review proposed classifying `RefreshError` and notifying with the exact fix command.
- OPS-11 and OPS-14: plaintext secrets with no rotation workflow; logs without correlation ids, duration, source, status or bytes fields.
- FUNC-13: no per-source health or quota visibility.
- REVIEW-v1 section 4: live probes on 2026-10-19 found upstream changes at OpenAlex, Semantic Scholar, Crossref, Google Programmable Search, Brave and Vertex AI Search.

No study exists yet in `docs/research/`.

## 2.2 User stories and priority

> **Owner:** C for stories (`product-writer`), H for priority · **Seed question:** 3

Drafted by the product writer for owner approval (owner decision, 2026-10-22, to draft them). The stories come from the user needs in PRD-v6 1.2 and section 1.2 here. No requirement of this component serves the ECC orchestrator, so it has no story.

| ID | As a... I want... so that... | Priority | Why this priority |
| --- | --- | --- | --- |
| HLTH-US-1 | As the owner (passively), I want every source and local target (cache, embeddings, archive folder, disk) checked by probes and real calls, with its state worked out from the results, so that I learn when one breaks, slows down or runs out of budget. | P1 | Served by HLTH-FR-2, HLTH-FR-3, HLTH-FR-5 and HLTH-FR-10, which are P1 |
| HLTH-US-2 | As the owner (passively), I want each credential tracked by its metadata and validated without spending billed queries, with fix text that names the exact step, so that I can rotate a key before it expires or as soon as it fails. | P1 | Served by HLTH-FR-20, HLTH-FR-21, HLTH-FR-24 and HLTH-FR-25, which are P1 |
| HLTH-US-3 | As the owner (directly), I want to see each source's details and reload credentials after rotating a key in the Keychain, without a restart, so that I can confirm the fix worked. | P1 | Served by HLTH-FR-11 and HLTH-FR-23, which are P1 |
| HLTH-US-4 | As the owner (through an agent), I want agents to read source and credential status without secrets, and federated search to skip sources that cannot answer, so that agents do not waste calls on broken sources. | P1 | Served by HLTH-FR-12, HLTH-FR-42 and HLTH-FR-43, which are P1 |
| HLTH-US-5 | As the owner (passively), I want `doctor` and a watchdog that run every check without the daemon, so that I am told when the daemon itself is dead. | P1 | Served by HLTH-FR-40 and HLTH-FR-41, which are P1 |
| HLTH-US-6 | As the owner (passively), I want notifications only on state changes, rolled into a daily digest, held during quiet hours and free of secrets, so that each notice is worth reading and safe to show. | P1 | Served by HLTH-FR-30, HLTH-FR-31, HLTH-FR-32 and HLTH-FR-34, which are P1 |

## 2.3 User experience

> **Owner:** C · **Persona:** `product-writer` drafts the narrative; designers own the design artifacts · **Seed question:** 3

**Credential expiring** (HLD-v3 11.4):

1. A GitHub call returns `GitHub-Authentication-Token-Expiration` 13 days out, and the credential becomes `expiring_soon(13)`.
2. The state change produces a notification: "GitHub token expires in 13 days: rotate in Keychain item research-mcp/GITHUB_TOKEN".
3. Clicking it opens the Credentials page, which links to GitHub's token page and shows the value-free `security` command.
4. After rotating, the owner presses "Reload credentials". The fingerprint changes, the next call shows the new expiry, and the state returns to `ok`.

**Passive and agent surfaces** (PRD-v4 4): the owner gets macOS notifications and an optional OpenClaw inbox message; agents read `research://status`, `research://sources` and `ops_status`. The UI pages themselves are specified in PRD-ui.

## 2.4 Functional requirements and acceptance criteria

> **Owner:** C · **Persona:** `product-writer` drafts requirements and criteria as options; the owner selects and approves · **Seed questions:** 3, 12

**Source states** (PRD-health v2 2.2). The worst applicable state wins.

| State | Rule |
| --- | --- |
| `disabled` | Turned off in configuration or the UI. |
| `unconfigured` | A required credential or extra is missing. Shown neutral, not red. |
| `down` | 3 failed probes in a row; or all of at least 5 calls in 15 minutes failed; or a probe failed its shape check. |
| `credential_invalid` | A required credential is invalid. |
| `budget_exhausted(reset)` | A metered source reported its daily or period budget spent (for example OpenAlex), or the owner's budget cap was reached; skipped until the reset time. |
| `rate_limited(until)` | The source returned 429 with a retry time beyond 60 seconds; skipped until then. |
| `degraded` | Error rate above 10% over the last 20 calls; or p95 latency above 3 times its 7-day baseline; or recent short 429s; or quota low. |
| `credential_expiring(days)` | A credential expires within 14 days. |
| `deprecated(days)` | The provider has announced a shutdown date. |
| `ok` | None of the above. |

**Credential states** (PRD-health v2 2.3).

| State | Rule |
| --- | --- |
| `ok` | Validated within its cadence; no expiry, or expiry more than 14 days away. |
| `expiring_soon(days)` | Expiry within 14 days (warning) or 3 days or fewer (critical). Expiry comes from the provider (for example GitHub's `GitHub-Authentication-Token-Expiration` header, a service-account key's `validBeforeTime`) or from a `rotate_by` date the owner sets. |
| `invalid` | Last validation or call failed authentication (401; 403 with an auth reason; Google `API_KEY_INVALID`; OAuth `invalid_grant`). |
| `missing` | Referenced in configuration but not found in the Keychain. |
| `keychain_locked` | The Keychain could not be read (locked or user interaction not allowed). Applies to every credential at once and produces one notification, not one per key. |
| `quota_low(pct)` | Less than 10% of the period allowance remains. |
| `unknown_expiry` | Valid, but the provider does not expose an expiry; shows key age and `rotate_by`. |

**Functional requirements.**

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| HLTH-FR-1 | Every outbound call records time, source, operation, HTTP status, classified error code, latency, bytes, parsed rate-limit headers, parsed credential-expiry header and a correlation id. Raw rows are kept 30 days; hourly rollups 13 months. | HLTH-US-1 | OUT-4, OUT-5 | P1 |
| HLTH-FR-2 | Every source has a cheap probe declared in its spec, with a cost class and cadence (default hourly for free sources, 6 to 24 hours for metered ones). Probes go through the same rate limiter as real traffic. | HLTH-US-1 | OUT-4, OUT-5 | P1 |
| HLTH-FR-3 | A probe checks the response shape, not only the status code, so an endpoint that returns 200 with a changed format is detected. | HLTH-US-1 | OUT-4, OUT-5 | P1 |
| HLTH-FR-4 | A probe is skipped when a real call in the same window already showed the source working (passive evidence first). | HLTH-US-1 | OUT-4, OUT-5 | P2 |
| HLTH-FR-5 | Local targets are probed too: cache database, embeddings, archive folder and disk. | HLTH-US-1 | OUT-4, OUT-5 | P1 |
| HLTH-FR-10 | Source states follow the source state table above and are recomputed after every probe and every call batch. | HLTH-US-1 | OUT-4, OUT-5 | P1 |
| HLTH-FR-11 | Each source exposes state, reason, fix hint, last probe time and result, calls in 24 hours, error rate, p50 and p95 latency, last classified error, quota remaining and reset, and credential badges. | HLTH-US-3 | OUT-4, OUT-5 | P1 |
| HLTH-FR-12 | Federated search reads source states to skip `down`, `rate_limited` and `budget_exhausted` sources (SRCH-FR-8). | HLTH-US-4 | OUT-4, OUT-5 | P1 |
| HLTH-FR-20 | Credential metadata is stored, never values: name, Keychain service, fingerprint (first 8 hex characters of the SHA-256 of the value, to notice rotation), Keychain modification date, `expires_at`, `rotate_by`, last validated time, last result and state. | HLTH-US-2 | OUT-4, OUT-5 | P1 |
| HLTH-FR-21 | Each credential has a validation method declared by its source: a passive header (GitHub expiry, Brave rate-limit headers), a free account or rate-limit endpoint (GitHub `/rate_limit`, the SerpAPI account endpoint), a Google sign-in token refresh (HLTH-FR-25), or a minimal probe call. Validation of a metered source never spends a billed query when a free method exists. | HLTH-US-2 | OUT-4, OUT-5 | P1 |
| HLTH-FR-22 | Keys that never expire get a default `rotate_by` of 180 days from their Keychain modification date, which the owner can change or clear. | HLTH-US-2 | OUT-4, OUT-5 | P2 |
| HLTH-FR-23 | After the owner rotates a key in the Keychain, "Reload credentials" in the UI (or `SIGHUP`) re-reads it without a restart; the fingerprint change is recorded. | HLTH-US-3 | OUT-4, OUT-5 | P1 |
| HLTH-FR-24 | The fix text for every Keychain credential state names the Keychain item, the provider's key page, and a copyable `security add-generic-password -U -s research-mcp/<NAME> -a "$USER" -w` command with no value in it. | HLTH-US-2 | OUT-4, OUT-5 | P1 |
| HLTH-FR-25 | The Google sign-in used by `vertex_search` is a credential with the usual states. It is validated by refreshing the access token (free) and by reading the engine's metadata (free). No sign-in found is `missing`; a refused refresh (for example `invalid_grant` or reauthentication required) is `invalid`; a disabled API or a missing search permission on the engine is `invalid` with that reason. The fix text gives the copyable `gcloud auth application-default login` command and, for permissions, the engine's console page. v2 stores the account email and the token expiry only, never a token. | HLTH-US-2 | OUT-4, OUT-5 | P1 |
| HLTH-FR-30 | Notifications fire on state changes only: a source becomes `down` or `credential_invalid`; a credential reaches 14, 7, 3 and 1 days before expiry; `quota_low`; `deprecated` at 60, 30 and 7 days; a disk warning; the archive folder becomes unavailable; a cache review batch is ready. | HLTH-US-6 | OUT-4, OUT-5 | P1 |
| HLTH-FR-31 | Unresolved issues roll into one daily digest instead of repeating. | HLTH-US-6 | OUT-4, OUT-5 | P1 |
| HLTH-FR-32 | Channels: macOS notification (primary; with `terminal-notifier` installed, clicking opens the matching UI page; the built-in fallback cannot be clicked through); OpenClaw inbox through a configurable webhook whose token is a Keychain item (optional; O5 closed, PRD-v6 1.6); a UI banner until resolved or acknowledged. Notifications carry no login tokens. | HLTH-US-6 | OUT-4, OUT-5 | P1 |
| HLTH-FR-33 | Quiet hours (default 21:00 to 08:00) hold non-critical notifications for the morning digest. A credential used in the last hour that becomes invalid notifies immediately. | HLTH-US-6 | OUT-4, OUT-5 | P2 |
| HLTH-FR-34 | Notification text never contains a secret value or a full URL with query parameters. | HLTH-US-6 | OUT-4, OUT-5 | P1 |
| HLTH-FR-35 | Every notification is stored with an acknowledged flag and can be snoozed for N days from the UI. | HLTH-US-6 | OUT-4, OUT-5 | P2 |
| HLTH-FR-40 | `research-mcp doctor [--json] [--notify]` runs every check without the daemon: daemon liveness, Keychain readability, credential validity, source probes, archive folder, disk, schema version and launchd job state. | HLTH-US-5 | OUT-4, OUT-5 | P1 |
| HLTH-FR-41 | Two launchd jobs watch the daemon independently: `doctor --liveness --notify` every 15 minutes (daemon alive, Keychain readable) and the full `doctor --notify` once a day. A notification is sent only when the result changes. | HLTH-US-5 | OUT-4, OUT-5 | P1 |
| HLTH-FR-42 | Agents can read status through the `research://status` and `research://sources` resources and the `ops_status` tool (summary only, no secrets). | HLTH-US-4 | OUT-4, OUT-5 | P1 |
| HLTH-FR-43 | `/healthz` (liveness) and `/readyz` (stores open, scheduler alive, Keychain readable) answer on loopback; `/api/status` returns the full JSON status to an authenticated caller. | HLTH-US-4 | OUT-4, OUT-5 | P1 |

**Acceptance criteria.** Rows follow the order of `tools/gen_test_plan.py`; HLTH-43 is new in this version and is listed last.

| ID | Criterion | Requirement | Priority | Level | Milestone |
| --- | --- | --- | --- | --- | --- |
| HLTH-40 | When run with fakes, the `doctor` skeleton shall run `daemon_alive`, `keychain_readable`, `contact_email` and `schema_versions`, run only the first two under `--liveness`, produce `--json` output, and return an exit code that reflects criticals. | HLTH-FR-40 | P1 | unit | M0 |
| HLTH-1 | The health service shall write call telemetry rows and hourly rollups and prune them on schedule. | HLTH-FR-1 | P1 | integration | M1 |
| HLTH-2 | The health service shall run probes at their cadence with jitter through the rate limiter, and skip the probe when a recent call succeeded. | HLTH-FR-2, HLTH-FR-4 | P1 | integration | M1 |
| HLTH-3 | When a probe gets a 200 response with a changed shape, the health service shall mark the source down. | HLTH-FR-3 | P1 | integration | M1 |
| HLTH-4 | The health service shall probe the local targets (cache db, archive folder, disk). | HLTH-FR-5 | P1 | integration | M1 |
| HLTH-10 | The health service shall evaluate the source state table (PRD-health v2 section 2.2, carried into section 2.4 here) so that each rule produces its state and the worst state wins. | HLTH-FR-10 | P1 | unit | M1 |
| HLTH-12 | When a 429 or a budget response arrives, the health service shall set the `rate_limited(until)` or `budget_exhausted(reset)` state and clear it at its time. | HLTH-FR-10, HLTH-FR-12 | P1 | unit | M1 |
| HLTH-13 | If the Keychain is locked, then the credential service shall give every credential `keychain_locked` and produce exactly one notification. | HLTH-FR-20, HLTH-FR-30 | P1 | unit | M1 |
| HLTH-11 | The health service shall expose every field in HLTH-FR-11 in the source detail. | HLTH-FR-11 | P1 | integration | M1 |
| HLTH-20 | The credential service shall derive the credential states `ok`, `expiring_soon`, `invalid`, `missing`, `quota_low` and `unknown_expiry` from fixtures. | HLTH-FR-20, HLTH-FR-21 | P1 | unit | M1 |
| HLTH-21 | When a GitHub call carries the expiry header or `/rate_limit` answers, the credential service shall update `expires_at` and the quota. | HLTH-FR-21 | P1 | integration | M1 |
| HLTH-22 | Where a key has no expiry, the credential service shall set `rotate_by` to 180 days after its Keychain modification unless overridden. | HLTH-FR-22 | P2 | unit | M1 |
| HLTH-23 | The credential service shall give fix text that names the Keychain item, the provider page and a `security` command with no value. | HLTH-FR-24 | P1 | unit | M1 |
| HLTH-24 | With fakes, the credential service shall report no Google sign-in as `missing`, report a refused refresh, `SERVICE_DISABLED` and `PERMISSION_DENIED` as `invalid` with their reason, give fix text with `gcloud auth application-default login`, hold only the account email and token expiry as metadata, and never raise `expiring_soon` on token renewal. | HLTH-FR-25 | P1 | unit | M1 |
| HLTH-25 | The credential service shall validate metered sources with free methods where they exist (SerpAPI account endpoint, Vertex engine metadata), run Brave and Programmable Search probes at most once per 24 h, and update quota from Brave rate-limit headers. | HLTH-FR-21 | P1 | integration | M1 |
| HLTH-30 | When a state change or an expiry milestone (14, 7, 3, 1 days) occurs, the notify service shall fire its notification only once each. | HLTH-FR-30 | P1 | integration | M1 |
| HLTH-31 | The notify service shall roll unresolved items into one daily digest. | HLTH-FR-31 | P1 | integration | M1 |
| HLTH-32 | The notify service shall build the macOS notifier argv with `terminal-notifier -execute research-mcp ui --path` (no token anywhere in argv), fall back to `osascript`, and send the webhook payload with the Keychain token in a header, never in the URL. | HLTH-FR-32, UI-FR-2, NFR-3 | P1 | unit | M1 |
| HLTH-33 | While quiet hours are in effect, the notify service shall hold non-critical notifications, except that a recently used invalid credential notifies immediately. | HLTH-FR-33 | P2 | unit | M1 |
| HLTH-34 | The notify service shall never put secret values or URLs with queries in notification subjects and bodies. | HLTH-FR-34, NFR-4 | P1 | unit | M1 |
| HLTH-35 | The notify service shall store the acknowledged and snoozed state of notifications. | HLTH-FR-35 | P2 | unit | M1 |
| HLTH-41 | When run with fakes, `doctor` shall run every check in SPEC-v2 section 10.5 (including `archive_access` with a simulated TCC denial, `review_overdue` and `backup_recent`), and under `--notify` send one summary only when the result changes. | HLTH-FR-40, HLTH-FR-41, CACHE-FR-45 | P1 | integration | M2 |
| HLTH-42 | The `ops_status` tool, the `research://status` resource and the `/api/status` endpoint shall expose status without secrets. | HLTH-FR-42, HLTH-FR-43 | P1 | contract | M1 |
| HLTH-43 | The credential service shall store each credential as the HLTH-FR-20 metadata only, with no column or field that holds a credential value. | HLTH-FR-20 | P1 | unit | M1 |
| HLTH-44 | The health service shall probe the embeddings local target named in HLTH-FR-5. | HLTH-FR-5 | P1 | integration | M1 |

**Verified elsewhere (owner decision, 2026-10-22):**

- HLTH-FR-23 (reload credentials without a restart) is verified by SEC-4 in the security component.
- HLTH-FR-43: `/healthz` and `/readyz` are verified by PLAT-70 in the platform component; `/api/status` by HLTH-42 here.
- HLTH-FR-20: SEC-3 in the security component also checks that the Keychain metadata lookup never reads a value.
- Owner checks add live evidence on the Mac and stay owner checks: OC-03 for HLTH-FR-32 (a real notification opens the right UI page) and OC-14 for HLTH-FR-25 (the Google sign-in shows `ok` in `doctor`).

## 2.5 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |

The parent outcomes OUT-1 to OUT-8 and NFR-1 to NFR-12 suffice; no component NFR target is added (owner decision, 2026-10-22). Design defaults such as probe cadence, timeouts and notification delivery stay in the LLD. Parent NFRs that bind this component: NFR-3 (no secrets at rest outside the Keychain, including the webhook token), NFR-4 (no secret in notifications or any output), NFR-7 (loopback only; `/healthz` and `/readyz` are the only unauthenticated requests), NFR-9 (testable offline) and NFR-12 (the watchdog reports a dead daemon within 15 minutes) (PRD-v6 2.3). Retention targets are part of HLTH-FR-1.

## 2.6 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

Every item is personal and confidential (PRD-v6 2.4). Retention follows the parent rule for the same kind of data, or the nearest parent rule where the parent does not list it (owner decision, 2026-10-22).

| Data | Classification | Source or owner | Retention | Notes |
| --- | --- | --- | --- | --- |
| Call telemetry rows | Personal, confidential (PRD-v6 2.4) | HTTP client, every outbound call | 30 days (HLTH-FR-1) | Includes a correlation id |
| Hourly call rollups | Personal, confidential (PRD-v6 2.4) | Health service | 13 months (HLTH-FR-1) | |
| Credential metadata | Personal, confidential (PRD-v6 2.4) | Keychain metadata and validation results | Until revoked or replaced (PRD-v6 2.4; owner decision, 2026-10-22) | Never values (HLTH-FR-20; HLTH-INV-1) |
| Google sign-in metadata | Personal, confidential (PRD-v6 2.4) | `gcloud` application default credentials | Until revoked or replaced (owner decision, 2026-10-22) | Account email and token expiry only (HLTH-FR-25; HLTH-INV-5) |
| Notifications | Personal, confidential (PRD-v6 2.4); must contain no secret (NFR-4) | Notify service | The life of the install (PRD-v6 2.4, daemon state; owner decision, 2026-10-22) | Acknowledged and snoozed state (HLTH-FR-35) |
| Source health | Personal, confidential (PRD-v6 2.4) | Health service | The life of the install (PRD-v6 2.4, daemon state; owner decision, 2026-10-22) | |

## 2.7 Integrations and owners

> **Owner:** H confirms owners and SLAs · **Persona:** `architect` may draft · **Seed question:** 8

Kenny Hill owns every integration. No integration has an SLA: upstream services are best effort and tracked by probes (PRD-v6 2.5; owner decision, 2026-10-22).

| System | Owner | Relationship (depends on, feeds, replaces) | SLA |
| --- | --- | --- | --- |
| macOS Keychain (`/usr/bin/security`) | Kenny Hill | Depends on: credential values and metadata (ADR 0003) | None (PRD-v6 2.5) |
| `gcloud` application default credentials | Kenny Hill | Depends on: Google sign-in for `vertex_search` (ADR 0012) | None (PRD-v6 2.5) |
| Source providers' free validation endpoints (GitHub `/rate_limit`, SerpAPI account endpoint, Vertex engine metadata) | Kenny Hill | Depends on (HLTH-FR-21, HLTH-FR-25) | None; best effort, tracked by probes (PRD-v6 2.5) |
| macOS notifications (`terminal-notifier`, `osascript` fallback) | Kenny Hill | Feeds (HLTH-FR-32) | None (PRD-v6 2.5) |
| OpenClaw inbox webhook | Kenny Hill | Feeds, optional (HLTH-FR-32; O5 closed, PRD-v6 1.6) | None (PRD-v6 2.5) |
| launchd | Kenny Hill | Depends on: runs the watchdog and daily `doctor` (HLTH-FR-41) | None (PRD-v6 2.5) |
| Federated search (PRD-search) | Kenny Hill (PRD-v6 2.1) | Feeds: source states (HLTH-FR-12; SRCH-FR-8) | Not applicable |
| Local UI (PRD-ui) | Kenny Hill (PRD-v6 2.1) | Feeds: status, banner and click-through pages (HLTH-FR-32; UI-FR-2) | Not applicable |
| Retrieval and cache (PRD-cache) | Kenny Hill (PRD-v6 2.1) | Depends on: review batch notices, archive and disk checks (HLTH-FR-30; CACHE-FR-45) | Not applicable |

## 2.8 Product risks

> **Owner:** H · **Persona:** none

| Risk | Question | Assessment | Mitigation |
| --- | --- | --- | --- |
| Value | Will customers choose to use this? | The owner asked for it: v2 must be monitored and must notify when a credential is expiring or invalid (D5). The open part is whether notices reach the owner before an agent hits the problem (HLTH-OUT-6). (proposed for owner approval) | Notices fire on state changes only and unresolved issues roll into one daily digest (HLTH-FR-30, HLTH-FR-31); HLTH-OUT-6 is measured 30 days after cutover (PRD-v6 OUT-4) |
| Usability | Can customers use it, including with accessibility needs? | Each fix text names the Keychain item, the provider's key page and a copyable command with no value (HLTH-FR-24, HLTH-FR-25). Without `terminal-notifier` the built-in notification cannot be clicked through (HLTH-FR-32). The sources state no accessibility need. (proposed for owner approval) | HLTH-23 and HLTH-24 check the fix text; OC-03 checks that a real notification opens the right UI page; the UI banner stays until resolved or acknowledged (HLTH-FR-32) |
| Viability | Does it work for the business: economics, legal, compliance, operations? | One person on one Mac (PRD-v6 1.2; NFR-12). The cost exposure is metered spend, the parent risk in the metered spend row below (PRD-v6 2.10). (proposed for owner approval) | Validation never spends a billed query when a free method exists (HLTH-FR-21; HLTH-INV-4) |
| Upstream drift | Upstream APIs change faster than one person can follow (PRD-v4 12) | From PRD-v4 12 | Probes check response shape, not just status; recorded fixtures; each source can be disabled with a flag |
| Metered spend | Metered sources run out mid-task or cost more than expected (PRD-v4 12) | From PRD-v4 12 | `quota_low`, `rate_limited` and `budget_exhausted` states; federation skips exhausted sources and says so |
| Keychain locked | The Keychain is locked or unreadable, for example right after login (PRD-v4 12) | From PRD-v4 12 | Reads through `/usr/bin/security` with a timeout; one `keychain_locked` state and one notification; `doctor` gives the fix |

## 2.9 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | As the parent: v1 stays read-only and running until cutover; cutover (M4) switches client configs; v1 is archived after 14 days of daily use on v2 with no fallback to v1 (PRD-v6 2.6) |
| Business conditions that must halt the rollout | The PRD-v7 2.6 conditions: any deletion without a recorded owner decision (INV-1), any secret in an output (INV-2), a fallback to v1 during the 14-day window, or a breach of any invariant, which includes HLTH-INV-1 to HLTH-INV-5 (PRD-v7 2.6; owner decision, 2026-10-22) |
| Support owner and escalation path | The owner is the only support; there is no escalation path (PRD-v6 2.6) |
| Response targets by severity (S0 to S4) | None (PRD-v6 2.6). Detection targets are HLTH-OUT-2 to HLTH-OUT-5. |

## 2.10 Measurement and experimentation

> **Owner:** C · **Persona:** `product-writer` drafts; the owner decides

| Outcome | Measured by | Experiment (if any) |
| --- | --- | --- |
| HLTH-OUT-1 | Criteria HLTH-2 (probes run at their cadence) and SRC-20 (every M1 adapter passes conformance) at the M1 exit. (proposed for owner approval) | None |
| HLTH-OUT-2 | Criterion HLTH-30, then a notification log query at the M1 exit: the time from each source state change in `source_health` to its row in `notifications`, outside quiet hours. (proposed for owner approval) | None |
| HLTH-OUT-3 | Criterion HLTH-41 and the 15-minute watchdog cadence of HLTH-FR-41, then a notification log query at the M1 exit: the time from the daemon stopping to the watchdog's notice in `notifications`. (proposed for owner approval) | None |
| HLTH-OUT-4 | Criterion HLTH-30 at M1, then a notification log query at the parent 30-day review: each expiring credential has a notice at 14, 7, 3 and 1 days. (proposed for owner approval) | None |
| HLTH-OUT-5 | Criterion HLTH-20 at M1, then a notification log query at the parent 30-day review: the time from a credential becoming `invalid` to its notice, against the probe cycle. (proposed for owner approval) | None |
| HLTH-OUT-6 | The parent 30-day review: for each source state change, compare the notification time with the first failed agent call to that source in `calls`. (proposed for owner approval) | None |
| HLTH-OUT-7 | The parent 30-day review: count credentials that reached expiry with no earlier expiry notice in `notifications`. (proposed for owner approval) | None |

## 2.11 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

The component is done when every P1 criterion in section 2.4 passes and the exit of the milestone that delivers it is met (PRD-v6 2.9; owner decision, 2026-10-22). HLTH-40 belongs to M0, HLTH-41 to M2 and the rest to M1; the M1 exit includes source board data available through `research://sources` and notifications verified on the Mac (PRD-v6 2.9). The owner checks listed for this component in `docs/test/test-plan-v2.md` section 3 count: OC-03 and OC-14 (M1). There is no extra demonstration (owner decision, 2026-10-22).

## 2.12 Edge cases and error behavior

> **Owner:** A · **Persona:** `product-writer`

| Case | Behavior | Criterion |
| --- | --- | --- |
| The Keychain is locked or user interaction is not allowed | Every credential is `keychain_locked`; one notification, not one per key (credential states table) | HLTH-13 |
| An endpoint returns 200 with a changed format | The probe's shape check fails and the source is `down` (HLTH-FR-3) | HLTH-3 |
| A 429 with a retry time beyond 60 seconds | The source is `rate_limited(until)` and skipped until then (source states table) | HLTH-12 |
| A metered budget or the owner's cap is spent | The source is `budget_exhausted(reset)` and skipped until the reset time (source states table) | HLTH-12 |
| A provider exposes no expiry | `rotate_by` defaults to 180 days from the Keychain modification date (HLTH-FR-22) | HLTH-22 |
| The Google sign-in access token renews itself | Token renewal never raises `expiring_soon` (HLTH-24) | HLTH-24 |
| `terminal-notifier` is not installed | The built-in fallback is used and cannot be clicked through (HLTH-FR-32) | HLTH-32 |
| A credential used in the last hour becomes invalid during quiet hours | It notifies immediately (HLTH-FR-33) | HLTH-33 |
| A metered source with no free validation method | Its probe runs at most once per 24 h (HLTH-25) | HLTH-25 |
| An issue stays unresolved | It rolls into the daily digest instead of repeating (HLTH-FR-31) | HLTH-31 |
| The daemon is dead | The watchdog `doctor --liveness --notify` runs every 15 minutes without the daemon (HLTH-FR-41) | HLTH-41 |

## 2.13 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves before Gate 1

- Assumption: each requirement's Parent is OUT-4 and OUT-5, the goals the PRD-health v2 header names (G4 and G5); a finer mapping per requirement is the owner's choice.

**Resolved on 2026-10-22.** The owner answered every open question in v3. The answers now live here: non-goals (1.3), user group sizes (1.2), outcome dates (1.4), leaps of faith (1.5, proposed), invariants and their criteria (1.6, with the new HLTH-43), decision O5 (1.7 and HLTH-FR-32), user stories and the Story column (2.2 and 2.4, proposed), the embeddings probe (HLTH-44, a new criterion, so HLTH-4 keeps its wording), the home of HLTH-FR-23 (SEC-4, "Verified elsewhere" in 2.4), component NFRs (2.5), data classification and the Google sign-in retention (2.6), integration owners and SLAs (2.7), value, usability and viability (2.8, proposed), rollout and support (2.9), measurement (2.10, proposed) and the definition of done (2.11).

## 2.14 Glossary

> **Owner:** A · **Persona:** `product-writer`

| Term | Definition |
| --- | --- |
| Probe | A cheap call declared in a source's spec, with a cost class and cadence, that checks status and response shape (HLTH-FR-2, HLTH-FR-3) |
| Passive evidence | A real call in the probe's window that already showed the source working, so the probe is skipped (HLTH-FR-4) |
| Source state | One of the states in the source state table; the worst applicable state wins (2.4) |
| Credential state | One of the states in the credential state table (2.4) |
| Fingerprint | The first 8 hex characters of the SHA-256 of a credential value, used to notice rotation (HLTH-FR-20) |
| `rotate_by` | A date by which the owner intends to rotate a key; defaults to 180 days from the Keychain modification date for keys that never expire (HLTH-FR-22) |
| Digest | One daily notification that summarizes unresolved issues (HLTH-FR-31) |
| Quiet hours | A daily window (default 21:00 to 08:00) that holds non-critical notifications for the morning digest (HLTH-FR-33) |
| `doctor` | The `research-mcp doctor` command that runs every check without the daemon (HLTH-FR-40) |
| Watchdog | The launchd job that runs `doctor --liveness --notify` every 15 minutes (HLTH-FR-41) |

## 2.15 ID history

> **Owner:** C · **Persona:** `product-writer` records; the owner confirms

| ID | Status | Replaced by | Reason |
| --- | --- | --- | --- |

Changes and new IDs in version 4; these rows are not definitions.

| Changed or new ID | Change | Date | Reason |
| --- | --- | --- | --- |
| HLTH-44 | New criterion: The health service shall probe the embeddings local target named in HLTH-FR-5. | 2026-10-22 | owner decision, 2026-10-22 |
| HLTH-43 | Added, 2026-10-22: P1 criterion for HLTH-INV-1 (no stored credential value) | 2026-10-22 | Owner decision, 2026-10-22 |
| HLTH-FR-32 | Changed (keeps its ID), 2026-10-22: "open decision O5" replaced by "O5 closed, PRD-v6 1.6"; editorial, no change of behavior | 2026-10-22 | Owner decision, 2026-10-22 |

### Gate 1: Requirements approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

## 2.16 Earlier IDs

> **Owner:** A · **Persona:** `product-writer`

| Earlier ID | New ID |
| --- | --- |
| FR-HLTH-01 | HLTH-FR-1 |
| FR-HLTH-02 | HLTH-FR-2 |
| FR-HLTH-03 | HLTH-FR-3 |
| FR-HLTH-04 | HLTH-FR-4 |
| FR-HLTH-05 | HLTH-FR-5 |
| FR-HLTH-10 | HLTH-FR-10 |
| FR-HLTH-11 | HLTH-FR-11 |
| FR-HLTH-12 | HLTH-FR-12 |
| FR-HLTH-20 | HLTH-FR-20 |
| FR-HLTH-21 | HLTH-FR-21 |
| FR-HLTH-22 | HLTH-FR-22 |
| FR-HLTH-23 | HLTH-FR-23 |
| FR-HLTH-24 | HLTH-FR-24 |
| FR-HLTH-25 | HLTH-FR-25 |
| FR-HLTH-30 | HLTH-FR-30 |
| FR-HLTH-31 | HLTH-FR-31 |
| FR-HLTH-32 | HLTH-FR-32 |
| FR-HLTH-33 | HLTH-FR-33 |
| FR-HLTH-34 | HLTH-FR-34 |
| FR-HLTH-35 | HLTH-FR-35 |
| FR-HLTH-40 | HLTH-FR-40 |
| FR-HLTH-41 | HLTH-FR-41 |
| FR-HLTH-42 | HLTH-FR-42 |
| FR-HLTH-43 | HLTH-FR-43 |
| AT-HLTH-40 | HLTH-40 |
| AT-HLTH-01 | HLTH-1 |
| AT-HLTH-02 | HLTH-2 |
| AT-HLTH-03 | HLTH-3 |
| AT-HLTH-04 | HLTH-4 |
| AT-HLTH-10 | HLTH-10 |
| AT-HLTH-12 | HLTH-12 |
| AT-HLTH-13 | HLTH-13 |
| AT-HLTH-11 | HLTH-11 |
| AT-HLTH-20 | HLTH-20 |
| AT-HLTH-21 | HLTH-21 |
| AT-HLTH-22 | HLTH-22 |
| AT-HLTH-23 | HLTH-23 |
| AT-HLTH-24 | HLTH-24 |
| AT-HLTH-25 | HLTH-25 |
| AT-HLTH-30 | HLTH-30 |
| AT-HLTH-31 | HLTH-31 |
| AT-HLTH-32 | HLTH-32 |
| AT-HLTH-33 | HLTH-33 |
| AT-HLTH-34 | HLTH-34 |
| AT-HLTH-35 | HLTH-35 |
| AT-HLTH-41 | HLTH-41 |
| AT-HLTH-42 | HLTH-42 |
