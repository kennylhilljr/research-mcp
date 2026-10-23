---
title: "Local UI"
type: prd-component
version: 4
status: draft
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
prefix: UI
component: ui
parent: docs/prd/PRD-v7.md
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
supersedes: docs/prd/components/PRD-ui-v3.md
date: 2026-10-22
---

# Component PRD: Local UI (v4)

Version 4 records the owner's Gate 1 answers of 2026-10-22. It supersedes [PRD-ui v3](PRD-ui-v3.md), which moved [PRD-ui v2](../../../docs-archive/prd/components/PRD-ui-v2.md) onto the component PRD template; earlier IDs map to the current ones in section 2.16. Owner answers are cited as "(owner decision, 2026-10-22)". Parent: [PRD v7](../PRD-v7.md), outcome OUT-8. Vision: [vision v2](../../vision/vision-v2.md). Design: [SPEC-v3](../../spec/SPEC-v3.md) section 8; [LLD-ui v1](../../lld/LLD-ui-v1.md); [ADR 0010](../../adr/0010-localhost-ui-stack.md).

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

- The owner wants a lightweight local UI to see sources, health, credentials, jobs and the cache (owner decision D6, REVIEW-v1 1).
- In v1, breakage is silent and credentials are invisible: three sources were degraded by upstream changes and nothing noticed; nobody is told when a key expires or stops working (PRD-v4 2, items 2 and 3). Nothing is monitored: there are no health checks, no quota visibility and no credential expiry detection (REVIEW-v1 2, item 6).
- The UI is a lightweight page on the owner's Mac that shows, at a glance, which sources work, which credentials need attention, what is running, and what is in the cache, and lets the owner answer the archive-or-discard review. It is read-mostly: maintenance actions exist but always ask for confirmation (PRD-ui-v2 1).
- **Why now.** v2 is a rebuild, and the upstream breakage is current: the live probes of 2026-10-19 found OpenAlex, Semantic Scholar and Crossref degraded and Google Programmable Search closing ahead of its shutdown on 2027-01-01, and nothing in v1 noticed (PRD-v7 1.1). The UI is where the owner sees that state (owner decision, 2026-10-22).
- Parent context: goal G8, "Visible" (PRD-v4 3.1), now OUT-8 in [PRD v7](../PRD-v7.md).

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| The owner, directly, through the local web UI at `http://127.0.0.1:<port>` | Check the source board, reload a key after rotating it in the Keychain, answer the "archive or discard" review (PRD-v4 4) | One person (PRD-v6 1.2; owner decision, 2026-10-22); remote and multi-user access are non-goals (PRD-v4 3.2) |
| The owner, passively, through macOS notifications | Clicking a notification opens the matching UI page (PRD-v4 4; HLTH-FR-32; PRD-health-v2) | One person, the same owner (PRD-v6 1.2; owner decision, 2026-10-22) |

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- A page served by the daemon on loopback under `/ui`, with one-time token login, CSRF protection and confirmations (PRD-ui-v2 2.1).
- Ten pages, in navigation order: source board, credentials, quota, jobs, cache, cache review, archive, maintenance, events and logs, settings (PRD-ui-v2 2.2; HLD-v3 8).

| Non-goal | Why it is excluded |
| --- | --- |
| Remote access | Out of scope (PRD-ui-v2 3); the server binds to loopback on the owner's Mac (PRD-v4 3.2) |
| Multiple users | Out of scope (PRD-ui-v2 3; PRD-v4 3.2) |
| Editing documents | Out of scope (PRD-ui-v2 3); excluded to keep v2 a working cache and one search, not a library or search engine (PRD-v6 2.10, scope creep risk; owner decision, 2026-10-22) |
| A search interface that replaces the agent | Out of scope; the cache search box is only for "do I already have this?" (PRD-ui-v2 3); excluded to keep v2 a working cache and one search, not a library or search engine (PRD-v6 2.10, scope creep risk; owner decision, 2026-10-22) |
| Rotating the daemon token from the UI | The token rotates from the CLI with `secrets rotate-token`; no page offers it (owner decision, 2026-10-22; PLAT-FR-59) |

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |
| UI-OUT-1 | UI pages render from live state (parent OUT-8, PRD-v4 G8 measure) | No UI in v1 (PRD-v6 OUT-8); v1 has no health checks, quota visibility or credential expiry detection (REVIEW-v1 2) | All UI pages in this PRD render from live state (PRD-v4 G8) | M3 exit: UI acceptance tests green and owner walkthrough (PRD-v6 2.9; PRD-v4 10) |

The parent outcomes OUT-1 to OUT-8 and NFR-1 to NFR-12 suffice; no other component outcome is added (owner decision, 2026-10-22).

## 1.5 Leaps of faith

> **Owner:** H · **Persona:** none

| Leap of faith | How we will validate it | By when |
| --- | --- | --- |
| Interactivity limited to what htmx does well is enough, because the UI is a read-mostly status page (ADR 0010, consequences) (proposed for owner approval) | OC-05, the owner walkthrough of every UI page (test-plan-v2 3), with UI-5 and UI-10 to UI-19 passing | M3 exit |
| Review fatigue stays low: batching and the keep default let the owner answer the archive-or-discard review on one page (ADR 0007, "review fatigue is possible"; amended by ADR 0011) (proposed for owner approval) | UI-15 (per-item and bulk decisions with one summary confirmation) and UI-21 (unanswered items stay listed with their times asked), then OC-05 | M3 exit |
| Pages can read the same services the MCP tools use, so the UI needs no second API (ADR 0010, consequences; HLD-v3 8) (proposed for owner approval) | UI-10 to UI-19 passing against the daemon's services, with UI-OUT-1 measured as in 2.10 | M3 exit |

## 1.6 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

The owner confirmed these "never" rules as component invariants (owner decision, 2026-10-22). Each has at least one P1 criterion.

| ID | The system must never | Source (regulation, policy, contract) | P1 criterion |
| --- | --- | --- | --- |
| UI-INV-1 | Show a secret value on any page; credentials appear only as fingerprints and dates, and log lines shown are redacted (same rule as SEC-INV-4, for UI pages) | UI-FR-4; NFR-4 | UI-4 |
| UI-INV-2 | Serve the UI on anything other than `127.0.0.1` (same rule as SEC-INV-1) | UI-FR-1; NFR-7 | UI-1 (also PLAT-10, PLAT-71) |
| UI-INV-3 | Put a login token in a log or a notification (part of SEC-INV-4) | UI-FR-2 | UI-2 (logs); HLTH-32 (notifier argv) |
| UI-INV-4 | Accept a credential value typed into the browser | UI-FR-11 ("Values are never typed into the browser") | UI-11 |
| UI-INV-5 | Accept a state-changing request without a CSRF token, or run a maintenance action without explicit confirmation | UI-FR-3 | UI-3 |

## 1.7 Known constraints and decisions

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

| Decision or constraint | Status (made or open) | Rationale or link |
| --- | --- | --- |
| A lightweight local UI exists | Made | Owner decision D6 (REVIEW-v1 1) |
| Server-rendered Starlette routes and Jinja2 templates inside the daemon, one vendored htmx file, no JavaScript build | Made (ADR status: proposed, accepted when the owner approves the PRD at Gate 1, PRD-v6 1.6) | [ADR 0010](../../adr/0010-localhost-ui-stack.md); rejected Streamlit, Gradio, NiceGUI and a React single-page app |
| Same port as the MCP endpoint; no separate process, no build step, no CDN | Made | UI-FR-1 |
| Works in Safari and Chrome at laptop width; no JavaScript framework | Made | UI-FR-6 |
| UI text has no em dashes or en dashes | Made | UI-FR-7; NFR-11 |
| Cache retention is 120 days and archiving keeps a paper searchable (affects the Cache and Archive pages) | Made | Owner decision of 2026-10-19; [ADR 0011](../../adr/0011-archive-keeps-text-searchable-120-day-retention.md) |
| Review timing: unanswered items are asked again after 7 days; discards go to a 7-day trash | Made | PRD-v4 11, O8; PRD-v6 1.6 |
| The page requirements UI-FR-10 to UI-FR-18 and UI-FR-21 are P1 (UI-FR-20, polling, is P2) | Made | Owner decision, 2026-10-22 |
| Live refresh is `hx-get` polling every 10 seconds only; no server-sent events | Made | Owner decision, 2026-10-22; SPEC-v2 11 |
| The daemon token rotates from the CLI (`secrets rotate-token`); no UI page offers it | Made | Owner decision, 2026-10-22; PLAT-FR-59 |
| Job retry resubmits the job with the same parameters through `JobService.submit` | Made | Owner decision, 2026-10-22; SPEC-v2 3.6 |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

---

## 2.1 Customer discovery

> **Owner:** A · **Persona:** `analyst`

The v1 deep review (REVIEW-v1, 2026-10-19) found that nothing in v1 is monitored: no health checks, no quota visibility and no credential expiry detection (REVIEW-v1 2, item 6; finding OPS-15). Live probes found three sources degraded by upstream changes and one with an announced shutdown (REVIEW-v1 4). The owner asked for a lightweight local UI during that review (D6). No other research is recorded in `docs/research/` for this component.

## 2.2 User stories and priority

> **Owner:** C for stories (`product-writer`), H for priority · **Seed question:** 3

Drafted by the product writer for owner approval (owner decision, 2026-10-22, to draft them). The stories come from the user needs in PRD-v6 1.2 and in 1.2 above.

| ID | As a... I want... so that... | Priority | Why this priority |
| --- | --- | --- | --- |
| UI-US-1 | As the owner (directly), I want to see at a glance which sources work, what quota is left, what is running and what was notified, so that breakage is no longer silent. | P1 | UI-FR-10, UI-FR-12, UI-FR-13 and UI-FR-18 are P1 |
| UI-US-2 | As the owner (directly), I want to see which credentials need attention and reload a key after rotating it in the Keychain, so that no credential expires without my knowing. | P1 | UI-FR-11 is P1 |
| UI-US-3 | As the owner (passively, then directly), I want a review notification to lead me to the review page, where I archive, discard or keep cached items, so that nothing is deleted without my answer. | P1 | UI-FR-14, UI-FR-15 and UI-FR-16 are P1 |
| UI-US-4 | As the owner (directly), I want maintenance actions and setting changes to show what they will do and ask me to confirm, so that no action surprises me. | P1 | UI-FR-3, UI-FR-17 and UI-FR-21 are P1 |
| UI-US-5 | As the owner (directly), I want the UI reachable only from my Mac, entered with a one-time login and never showing a secret, so that no other process or person can use it or read a key. | P1 | UI-FR-1, UI-FR-2 and UI-FR-4 are P1 |
| UI-US-6 | As the owner (directly), I want pages that refresh on their own and read in my style in Safari or Chrome, so that the status I see is current without reloading. | P1 | UI-FR-6 and UI-FR-7 are P1 (UI-FR-20 is P2) |

## 2.3 User experience

> **Owner:** C · **Persona:** `product-writer` drafts the narrative; designers own the design artifacts · **Seed question:** 3

**Entering the UI** (UI-US-5). The owner runs `research-mcp ui`, or clicks a macOS notification, which runs that command. The command mints a one-time token at that moment and opens the matching page; the session continues in an HttpOnly, SameSite=Strict cookie (UI-FR-2; SPEC-v2 10.4, 11). Without `terminal-notifier`, the notification cannot be clicked through; the owner runs `research-mcp ui` and finds the notification in the page banner (UI-22).

**Answering a review** (UI-US-3). At 09:00 the scheduler finds documents expiring within 3 days and creates a batch. The owner gets one notification; clicking it opens the review page for that batch. The owner archives some items, discards others and may leave some unanswered. Archived items go to Drive and stay searchable; discards go to the trash for 7 days; unanswered items are kept and asked about again (HLD-v3 11.3; UI-FR-15).

**Rotating a credential** (UI-US-2). A notification says a token expires soon. Clicking it opens the Credentials page, which links to the provider's token page and shows the value-free `security` command. After rotating, the owner presses "Reload credentials"; the fingerprint changes and the state returns to `ok` (HLD-v3 11.4; UI-FR-11).

**Checking status** (UI-US-1, UI-US-6). The source board is the home page: one row per source with a state chip and counts at the top, refreshing every 10 seconds (UI-FR-20, UI-FR-10).

No design artifacts are linked yet.

## 2.4 Functional requirements and acceptance criteria

> **Owner:** C · **Persona:** `product-writer` drafts requirements and criteria as options; the owner selects and approves · **Seed questions:** 3, 12

General requirements (PRD-ui-v2 2.1), then pages in navigation order (PRD-ui-v2 2.2). The page requirements UI-FR-10 to UI-FR-18 and UI-FR-21 are P1 (UI-FR-20, polling, is P2) (owner decision, 2026-10-22).

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| UI-FR-1 | Served by the daemon on `127.0.0.1` only, at the same port as the MCP endpoint, under `/ui`. No separate process, no build step, no CDN: server-rendered HTML with a vendored htmx file. | UI-US-5 | OUT-8 | P1 |
| UI-FR-2 | Access starts from a one-time token URL that `research-mcp ui` mints at the moment of use (a notification click runs that command); the session is an HttpOnly, SameSite=Strict cookie; tokens never appear in logs or notifications. Host and Origin headers are checked. | UI-US-5 | OUT-8 | P1 |
| UI-FR-3 | Every state-changing request carries a CSRF token; every maintenance action shows what it will do and needs explicit confirmation. | UI-US-4 | OUT-8 | P1 |
| UI-FR-4 | No page ever shows a secret value; credentials appear as fingerprints and dates. Log lines shown are redacted. | UI-US-5 | OUT-8 | P1 |
| UI-FR-20 | Pages refresh live data with `hx-get` polling every 10 seconds, without a full reload. | UI-US-6 | OUT-8 | P2 |
| UI-FR-6 | Pages work in Safari and Chrome at laptop width; no JavaScript framework. | UI-US-6 | OUT-8 | P1 |
| UI-FR-7 | UI text follows the owner's style: no em dashes or en dashes. | UI-US-6 | OUT-8 | P1 |
| UI-FR-10 | **Source board** (home). Shows one row per source, grouped by group, with a state chip and counts at the top ("31 ok, 2 degraded, 1 expiring, 4 unconfigured"); per row: last probe, calls in 24 h, error rate, p95 latency, quota remaining and reset, last classified error, fix hint. Actions: probe now (one or all); open source detail (latency chart, recent errors by correlation id, recent calls); enable or disable. | UI-US-1 | OUT-8 | P1 |
| UI-FR-11 | **Credentials.** Shows per credential: name, sources that use it, required or optional, fingerprint, Keychain modified date, expiry with countdown, `rotate_by`, last validated, state, and the provider's key page link. Actions: re-check; reload from Keychain; set or clear `rotate_by`; acknowledge; copy the value-free `security` command. Values are never typed into the browser. | UI-US-2 | OUT-8 | P1 |
| UI-FR-12 | **Quota.** Shows for metered sources: allowance, used, remaining, reset, projected exhaustion; GitHub remaining per resource. Actions: edit per-source budget caps (with confirmation). | UI-US-1 | OUT-8 | P1 |
| UI-FR-13 | **Jobs.** Shows running, queued and recent jobs (fetch batch, crawl, archive, reconcile, rebuild, import) with progress, timing and errors. Actions: cancel; retry (resubmits the job with the same parameters through `JobService.submit`); view log for the job. | UI-US-1 | OUT-8 | P1 |
| UI-FR-14 | **Cache.** Shows cached, pinned and archived items: title, source, size, fetched, age, days to expiry (cached only), state, archive path (archived only); totals by type and state, growth per day, free disk; a filter box and a search box over cached and archived items ("do I already have this?"). Actions: pin or unpin; archive now; discard (to trash, confirmed); open the original URL. | UI-US-3 | OUT-8 | P1 |
| UI-FR-15 | **Cache review** (`/ui/review/<batch_id>`). Shows the open batch: per item title, citation, size, age, times asked, integrity changes, and the four choices; a note that unanswered items are kept and asked about again in 7 days. Actions: submit per-item or bulk decisions; the confirmation summarizes what will be archived (and where) and what goes to the trash. | UI-US-3 | OUT-8 | P1 |
| UI-FR-16 | **Archive.** Shows archive target health and upload state; a catalog of archived items with date, Drive path, search coverage (text and embeddings present) and copy-citation; records of discarded items; trash with undo. Actions: change the archive path (confirmed); run reconcile; run the archive rebuild job (confirmed); undo a discard within 7 days; copy citation or BibTeX. | UI-US-3 | OUT-8 | P1 |
| UI-FR-17 | **Maintenance.** Shows the last run and result of each check (integrity, orphans, embedding coverage, schema version, dependency audit, state backup) and a disk panel. Actions: verify now; rebuild full-text index; re-embed missing; clean orphans; back up state now. All confirmed. | UI-US-4 | OUT-8 | P1 |
| UI-FR-18 | **Events and logs.** Shows notification history with acknowledged state, and recent warning and error log lines (redacted), searchable by correlation id, source or tool. Actions: acknowledge; snooze for N days. | UI-US-1 | OUT-8 | P1 |
| UI-FR-21 | **Settings.** Shows the effective configuration (paths, port, thresholds, quiet hours, channels, archive target), which credential references resolve (names only), versions, launchd job state, and the named site sets with their domains (read-only). Actions: edit thresholds, quiet hours and channels (confirmed); send a test notification. | UI-US-4 | OUT-8 | P1 |

Acceptance criteria, in the order of `tools/gen_test_plan.py`; UI-20 to UI-25 are new in this version.

| ID | Criterion | Requirement | Priority | Level | Milestone |
| --- | --- | --- | --- | --- | --- |
| UI-1 | The UI shall be served only on loopback under /ui with no external assets. | UI-FR-1, UI-FR-6 | P1 | integration | M3 |
| UI-2 | When `research-mcp ui` runs, the UI login flow shall mint a one-time token at use time, set an HttpOnly SameSite=Strict cookie with Path=/ at login, and use tokens that expire, cannot be reused and never appear in access logs (uvicorn access log off). | UI-FR-2 | P1 | integration | M3 |
| UI-3 | The UI shall refuse POSTs without a valid CSRF token and require confirmation for maintenance actions. | UI-FR-3 | P1 | integration | M3 |
| UI-4 | The UI shall render no page that contains a registered secret value, as checked by scanning every page with fake secrets. | UI-FR-4, NFR-4 | P1 | integration | M3 |
| UI-5 | The UI shall refresh page fragments through htmx endpoints. | UI-FR-20 | P2 | integration | M3 |
| UI-6 | The UI shall use strings that contain no em dashes or en dashes. | UI-FR-7, NFR-11 | P1 | unit | M3 |
| UI-10 | The source board shall show counts, groups, state chips and per-row fields and provide probe and enable actions that work. | UI-FR-10 | P1 | integration | M3 |
| UI-11 | The Credentials page shall show metadata only and the value-free security command. | UI-FR-11 | P1 | integration | M3 |
| UI-12 | The Quota page shall show allowance, used, remaining, reset and projection. | UI-FR-12 | P1 | integration | M3 |
| UI-13 | The Jobs page shall list jobs and cancel a job with confirmation. | UI-FR-13 | P1 | integration | M3 |
| UI-14 | The Cache page shall list items with totals and provide the do-I-have-this search. | UI-FR-14 | P1 | integration | M3 |
| UI-15 | The Review page shall submit per-item and bulk decisions with a summary confirmation. | UI-FR-15 | P1 | integration | M3 |
| UI-16 | The Archive page shall show target health, the catalog, discards and trash undo. | UI-FR-16 | P1 | integration | M3 |
| UI-17 | The Maintenance page shall run confirmed actions. | UI-FR-17 | P1 | integration | M3 |
| UI-18 | The Events page shall list notifications and redacted logs searchable by correlation id. | UI-FR-18 | P1 | integration | M3 |
| UI-19 | The Settings page shall show the effective config with names only for credentials and provide a test notification that works. | UI-FR-21 | P1 | integration | M3 |
| UI-20 | If a request to `/ui` carries a Host other than `127.0.0.1:<port>` or `localhost:<port>`, or an Origin that does not match, then the UI shall refuse it. | UI-FR-2 | P1 | integration | M3 |
| UI-21 | If a review submission leaves an item unanswered, then the Review page shall keep listing that item with its times asked. | UI-FR-15 | P1 | integration | M3 |
| UI-22 | When the owner opens the UI after a notification was delivered through the built-in fallback, the UI shall show that notification in the page banner until it is resolved or acknowledged. | UI-FR-18, HLTH-FR-32 | P1 | integration | M3 |
| UI-23 | If the Keychain is locked, then the Credentials and Settings pages shall each show one `keychain_locked` state rather than a `missing` state per credential. | UI-FR-11, UI-FR-21 | P1 | integration | M3 |
| UI-24 | When the owner retries a job on the Jobs page, the UI shall resubmit it through `JobService.submit` with the same kind and parameters. | UI-FR-13 | P1 | integration | M3 |
| UI-25 | The Settings page shall list each named site set with its domains, read-only. | UI-FR-21 | P1 | integration | M3 |

Verified elsewhere (owner decision, 2026-10-22):

- UI-FR-2: also HLTH-32 (no token in the notifier argv; the `osascript` fallback) and SEC-12 (the daemon refuses a foreign Host or Origin), alongside UI-2 and UI-20 here.
- UI-FR-10 and UI-FR-21: also OC-05, the owner walkthrough of every UI page (test-plan-v2 3). It stays an owner check.
- UI-FR-11 (locked Keychain): the credential service state is verified by HLTH-13; UI-23 verifies what the pages show.

## 2.5 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |

The parent outcomes OUT-1 to OUT-8 and NFR-1 to NFR-12 suffice; no component latency, availability or browser-support target is added beyond UI-FR-6 (owner decision, 2026-10-22). Parent NFRs that apply to this component: NFR-4 (no secret in any output, including UI pages), NFR-7 (loopback only; every request except the health checks needs a bearer token or a UI session), NFR-11 (no em dashes or en dashes in UI text) and NFR-12 (personal, best effort availability) (PRD-v6 2.3). The 10 second refresh is a functional requirement (UI-FR-20). Design defaults such as the token and session lifetimes stay in the LLD.

## 2.6 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

Every item is personal and confidential (PRD-v6 2.4). Retention follows the parent rule for the same kind of data, or the nearest parent rule (owner decision, 2026-10-22).

| Data | Classification | Source or owner | Retention | Notes |
| --- | --- | --- | --- | --- |
| Credential metadata: name, fingerprint, Keychain modified date, expiry, `rotate_by`, state | Personal, confidential; never a secret value (NFR-4) | Health and credentials component | Until revoked or replaced (nearest parent rule, PRD-v6 2.4; owner decision, 2026-10-22) | Values are never shown or typed into the browser (UI-FR-4, UI-FR-11) |
| Log lines (warnings and errors) | Personal, confidential; must contain no secret (NFR-4) | Platform logging | Rotated by size: 5 files of 10 MB (PLAT-FR-40; owner decision, 2026-10-22) | Shown redacted (UI-FR-4, UI-FR-18) |
| Cached, pinned, archived and discarded items | Personal, confidential; untrusted content (NFR-6) | Retrieval and cache component | 120 days from fetch in the cache; pinned and archived items never expire; discards 7 days in the trash, then deleted (PRD-v6 2.4; ADR 0011) | Read and acted on through the Cache, Review and Archive pages |
| Notifications and their acknowledged state | Personal, confidential | Health and credentials component (`state.db`) | Life of the install (daemon state, PRD-v6 2.4; owner decision, 2026-10-22) | Shown on the Events page and in the page banner |
| One-time login token and session cookie | Personal, confidential; never in logs or notifications (UI-FR-2) | This component and platform | Token: one use, valid for 5 minutes; session: 12 hours (SPEC-v2 11, in LLD-ui-v1 2.2) | Not stored by the UI beyond those lifetimes |

## 2.7 Integrations and owners

> **Owner:** H confirms owners and SLAs · **Persona:** `architect` may draft · **Seed question:** 8

Kenny Hill owns every integration. No integration has an SLA; upstream services are best effort, tracked by probes (PRD-v6 2.5; owner decision, 2026-10-22).

| System | Owner | Relationship (depends on, feeds, replaces) | SLA |
| --- | --- | --- | --- |
| Daemon (`research-mcpd`), the same services the MCP tools use | Kenny Hill | Depends on: pages read those services (platform and each service's component), so there is no second API (HLD-v3 8) | None |
| `research-mcp ui` command and the macOS notifier | Kenny Hill | Depends on: entry point that mints the one-time token (platform; health and credentials) (SPEC-v2 10.4, 11) | None |
| macOS Keychain (`/usr/bin/security`) | Kenny Hill | Depends on: the UI shows a value-free command; reload re-reads keys (UI-FR-11) | None |
| Google Drive sync folder (archive target) | Kenny Hill | Depends on: shown on the Archive page (UI-FR-16) | None |
| Safari and Chrome | Kenny Hill | Client (UI-FR-6) | None |

## 2.8 Product risks

> **Owner:** H · **Persona:** none

| Risk | Question | Assessment | Mitigation |
| --- | --- | --- | --- |
| Value | Will customers choose to use this? | The owner asked for the UI (D6), and the review and credential flows send him to it (SPEC-v3 11.3, 11.4); without it, breakage stays silent as in v1 (PRD-v6 1.1, item 2) (proposed for owner approval) | Notifications open the matching page (HLTH-FR-32; OC-03); the owner walks every page at M3 (OC-05) |
| Usability | Can customers use it, including with accessibility needs? | Review fatigue is possible (ADR 0007, amended by ADR 0011); interactivity is limited to what htmx does well (ADR 0010). The sources state no accessibility need for the one user (proposed for owner approval) | Batching and the keep default (ADR 0007, amended by ADR 0011); bulk decisions with one summary confirmation (UI-FR-15, UI-15); Safari and Chrome at laptop width (UI-FR-6) |
| Viability | Does it work for the business: economics, legal, compliance, operations? | Operations: the Keychain may be locked right after login, and the Drive sync folder may be unavailable or not uploading (PRD-v6 2.10) (proposed for owner approval) | One `keychain_locked` state on the pages that read credentials (UI-23); archive target health and upload state on the Archive page (UI-FR-16, UI-16) |

## 2.9 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | As in PRD-v6 2.6: v1 stays read-only and running until cutover; v1 is archived after 14 days of daily use on v2 with no fallback. Milestone M3 delivers all UI pages (PRD-v6 2.9) |
| Business conditions that must halt the rollout | The PRD-v7 2.6 conditions: any deletion without a recorded owner decision (INV-1), any secret in an output (INV-2), a fallback to v1 during the 14-day window, or a breach of any invariant, which includes UI-INV-1 to UI-INV-5 (PRD-v7 2.6; owner decision, 2026-10-22) |
| Support owner and escalation path | The owner is the only support; there is no escalation path (PRD-v6 2.6; owner decision, 2026-10-22) |
| Response targets by severity (S0 to S4) | None (PRD-v6 2.6; owner decision, 2026-10-22) |

## 2.10 Measurement and experimentation

> **Owner:** C · **Persona:** `product-writer` drafts; the owner decides

| Outcome | Measured by | Experiment (if any) |
| --- | --- | --- |
| UI-OUT-1 | UI acceptance criteria UI-1 to UI-6 and UI-10 to UI-25 passing, and the owner walkthrough of every UI page (OC-05, test-plan-v2 3) | None |

## 2.11 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

Every P1 criterion of this component passes (UI-1 to UI-4, UI-6 and UI-10 to UI-25), and the M3 exit is met: UI acceptance tests green and the owner walkthrough (PRD-v6 2.9). The owner check listed for this component in `docs/test/test-plan-v2.md` section 3, OC-05, counts. No extra demonstration is required (owner decision, 2026-10-22).

## 2.12 Edge cases and error behavior

> **Owner:** A · **Persona:** `product-writer`

| Edge case | Behavior | Criterion |
| --- | --- | --- |
| A login token is reused or presented after it expires | Refused | UI-2 |
| A POST arrives without a valid CSRF token | Refused | UI-3 |
| A request to `/ui` carries a foreign Host or Origin | Refused: the Host must be `127.0.0.1:<port>` or `localhost:<port>`, and a present Origin must match (UI-FR-2; SPEC-v2 11; LLD-ui-v1 2.3) | UI-20 (SEC-12 covers the daemon) |
| A review item is left unanswered | It stays listed with its times asked; it is kept and asked about again in 7 days (UI-FR-15; CACHE-FR-34) | UI-21 (CACHE-33 covers the lifecycle) |
| A discard is undone within 7 days | Restored from the trash (UI-FR-16) | UI-16 |
| `terminal-notifier` is not installed | The built-in fallback (`osascript`) shows the notification but cannot be clicked through, so it does not open the UI (HLTH-FR-32; LLD-health-v1 5). When the owner opens the UI with `research-mcp ui`, the notification shows in the page banner until resolved or acknowledged, and in the Events page history (HLTH-FR-32; UI-FR-18) | UI-22 (HLTH-32 covers the fallback) |
| The Keychain is locked | One `keychain_locked` state, not a missing state per key (ADR 0003; PRD-v6 2.10), shown on the Credentials and Settings pages | UI-23 (HLTH-13 covers the credential service) |

## 2.13 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves before Gate 1

**Resolved on 2026-10-22.** The owner answered every open question in v3. The stories are drafted for approval (2.2) and each requirement names one (2.4). The page requirements UI-FR-10 to UI-FR-18 and UI-FR-21 are P1, and UI-FR-20 (polling) is P2, so the priority assumption is removed (2.4, 1.7). The daemon token rotates from the CLI and no page offers it (1.3, 1.7). Refresh is `hx-get` polling every 10 seconds only (UI-FR-20). Job retry resubmits through `JobService.submit` (UI-FR-13, UI-24). The leaps of faith (1.5) and product risks (2.8) are drafted for approval. No component NFR is added (2.5). Data classification and retention (2.6), integration owners and SLAs (2.7), rollout and support (2.9) and the definition of done (2.11) follow the parent. The edge cases without a UI criterion now have UI-20 to UI-23 (2.12). UI-INV-1 and UI-INV-2 apply SEC-INV-4 and SEC-INV-1, which the Security component owns, and a breach of any invariant halts the rollout (PRD-v7 2.6).

- Assumption: the "four choices" on the review page (UI-FR-15) are archive, discard, keep and pin, the decisions SPEC-v2 9.1 allows for an `expiring` item.

## 2.14 Glossary

> **Owner:** A · **Persona:** `product-writer`

| Term | Definition |
| --- | --- |
| One-time token | A short-lived login token minted by `research-mcp ui` at the moment of use and consumed at login (UI-FR-2) |
| Session cookie | The HttpOnly, SameSite=Strict cookie that carries the UI session after login (UI-FR-2) |
| CSRF token | A token every state-changing request carries (UI-FR-3) |
| Fragment | A part of a page reloaded through htmx without a full reload (UI-FR-20) |
| Review batch | The set of cached items the owner is asked to archive or discard, opened at `/ui/review/<batch_id>` (UI-FR-15) |
| Fingerprint | The first 8 hex characters of the SHA-256 of a credential value, shown instead of the value (HLTH-FR-20; PRD-health-v2) |
| Page banner | The slot on every page that shows a notification until it is resolved or acknowledged (HLTH-FR-32; UI-22) |
| Built-in fallback | The `osascript` notification used when `terminal-notifier` is not installed; it cannot be clicked through (HLTH-FR-32) |
| `keychain_locked` | The one credential state shown when the Keychain cannot be read, instead of a missing state per key (ADR 0003; UI-23) |

## 2.15 ID history

> **Owner:** C · **Persona:** `product-writer` records; the owner confirms

Two requirements left this PRD in this version: each was superseded by a new ID because its behavior changed (owner decision, 2026-10-22).

| ID | Status | Replaced by | Reason |
| --- | --- | --- | --- |
| UI-FR-19 | superseded | UI-FR-21 | The response changed: the Settings page also shows the named site sets read-only, as SRC-FR-18 says (owner decision, 2026-10-22) |
| UI-FR-5 | superseded | UI-FR-20 | The response changed: refresh is `hx-get` polling every 10 seconds only; the server-sent event option is removed (owner decision, 2026-10-22) |

Changes and new IDs in version 4. Editorial changes keep their ID; new IDs are listed once.

| Changed or new ID | Change | Date | Reason |
| --- | --- | --- | --- |
| UI-FR-21 | New: replaces UI-FR-19; the Settings page also shows the named site sets read-only (SRC-FR-18) | 2026-10-22 | owner decision, 2026-10-22 |
| UI-25 | New criterion: the Settings page lists each named site set with its domains, read-only | 2026-10-22 | owner decision, 2026-10-22 |
| UI-FR-20 | New: replaces UI-FR-5; the response changed: refresh is `hx-get` polling every 10 seconds only; the server-sent event option is removed | 2026-10-22 | owner decision, 2026-10-22 |
| UI-FR-13 | Text changed: retry resubmits the job with the same parameters through `JobService.submit` | 2026-10-22 | owner decision, 2026-10-22 |
| UI-20 | New: a foreign Host or Origin on `/ui` is refused | 2026-10-22 | owner decision, 2026-10-22 |
| UI-21 | New: an unanswered review item stays listed with its times asked | 2026-10-22 | owner decision, 2026-10-22 |
| UI-22 | New: a notification from the built-in fallback shows in the page banner | 2026-10-22 | owner decision, 2026-10-22 |
| UI-23 | New: a locked Keychain shows one `keychain_locked` state on the Credentials and Settings pages | 2026-10-22 | owner decision, 2026-10-22 |
| UI-24 | New: job retry resubmits through `JobService.submit` | 2026-10-22 | owner decision, 2026-10-22 |
| UI-US-1 to UI-US-6 | New: stories drafted for owner approval | 2026-10-22 | owner decision, 2026-10-22 |

### Gate 1: Requirements approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

## 2.16 Earlier IDs

> **Owner:** A · **Persona:** `product-writer`

| Earlier ID | New ID |
| --- | --- |
| FR-UI-01 | UI-FR-1 |
| FR-UI-02 | UI-FR-2 |
| FR-UI-03 | UI-FR-3 |
| FR-UI-04 | UI-FR-4 |
| FR-UI-05 | UI-FR-5 (superseded by UI-FR-20) |
| FR-UI-06 | UI-FR-6 |
| FR-UI-07 | UI-FR-7 |
| FR-UI-10 | UI-FR-10 |
| FR-UI-11 | UI-FR-11 |
| FR-UI-12 | UI-FR-12 |
| FR-UI-13 | UI-FR-13 |
| FR-UI-14 | UI-FR-14 |
| FR-UI-15 | UI-FR-15 |
| FR-UI-16 | UI-FR-16 |
| FR-UI-17 | UI-FR-17 |
| FR-UI-18 | UI-FR-18 |
| FR-UI-19 | UI-FR-19 (superseded by UI-FR-21) |
| AT-UI-01 | UI-1 |
| AT-UI-02 | UI-2 |
| AT-UI-03 | UI-3 |
| AT-UI-04 | UI-4 |
| AT-UI-05 | UI-5 |
| AT-UI-06 | UI-6 |
| AT-UI-10 | UI-10 |
| AT-UI-11 | UI-11 |
| AT-UI-12 | UI-12 |
| AT-UI-13 | UI-13 |
| AT-UI-14 | UI-14 |
| AT-UI-15 | UI-15 |
| AT-UI-16 | UI-16 |
| AT-UI-17 | UI-17 |
| AT-UI-18 | UI-18 |
| AT-UI-19 | UI-19 |
