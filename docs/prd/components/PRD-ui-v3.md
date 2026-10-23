---
title: "Local UI"
type: prd-component
version: 3
status: draft
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
prefix: UI
component: ui
parent: docs/prd/PRD-v5.md
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
supersedes: docs-archive/prd/components/PRD-ui-v2.md
date: 2026-10-22
---

# Component PRD: Local UI (v3)

This version moves [PRD-ui v2](../../../docs-archive/prd/components/PRD-ui-v2.md) onto the component PRD template. Requirements and criteria keep their meaning; IDs follow the new scheme (section 2.16). Parent: [PRD v5](../PRD-v5.md), outcome OUT-8. Design: [LLD-ui v1](../../lld/LLD-ui-v1.md); [ADR 0010](../../adr/0010-localhost-ui-stack.md).

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

- The owner wants a lightweight local UI to see sources, health, credentials, jobs and the cache (owner decision D6, REVIEW-v1 1).
- In v1, breakage is silent and credentials are invisible: three sources were degraded by upstream changes and nothing noticed; nobody is told when a key expires or stops working (PRD-v4 2, items 2 and 3). Nothing is monitored: there are no health checks, no quota visibility and no credential expiry detection (REVIEW-v1 2, item 6).
- The UI is a lightweight page on the owner's Mac that shows, at a glance, which sources work, which credentials need attention, what is running, and what is in the cache, and lets the owner answer the archive-or-discard review. It is read-mostly: maintenance actions exist but always ask for confirmation (PRD-ui-v2 1).
- Parent context: goal G8, "Visible" (PRD-v4 3.1), now OUT-8 in [PRD v5](../PRD-v5.md).

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| The owner, directly, through the local web UI at `http://127.0.0.1:<port>` | Check the source board, reload a key after rotating it in the Keychain, answer the "archive or discard" review (PRD-v4 4) | The only user; remote and multi-user access are non-goals (PRD-v4 3.2) |
| The owner, passively, through macOS notifications | Clicking a notification opens the matching UI page (PRD-v4 4; HLTH-FR-32; PRD-health-v2) | Same person |

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- A page served by the daemon on loopback under `/ui`, with one-time token login, CSRF protection and confirmations (PRD-ui-v2 2.1).
- Ten pages, in navigation order: source board, credentials, quota, jobs, cache, cache review, archive, maintenance, events and logs, settings (PRD-ui-v2 2.2; HLD-v3 8).

| Non-goal | Why it is excluded |
| --- | --- |
| Remote access | Out of scope (PRD-ui-v2 3); the server binds to loopback on the owner's Mac (PRD-v4 3.2) |
| Multiple users | Out of scope (PRD-ui-v2 3; PRD-v4 3.2) |
| Editing documents | Out of scope (PRD-ui-v2 3) |
| A search interface that replaces the agent | Out of scope; the cache search box is only for "do I already have this?" (PRD-ui-v2 3) |

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |
| UI-OUT-1 | UI pages render from live state (parent OUT-8, PRD-v4 G8 measure) | v1 has no health checks, quota visibility or credential expiry detection (REVIEW-v1 2) | All UI pages in this PRD render from live state (PRD-v4 G8) | M3 exit: UI acceptance tests green and owner walkthrough (PRD-v4 10) |

## 1.5 Leaps of faith

> **Owner:** H · **Persona:** none

| Leap of faith | How we will validate it | By when |
| --- | --- | --- |

- [ ] Q: Which two or three bets must hold for the UI to succeed (for example, that htmx interactivity is enough for a read-mostly status page, as ADR 0010 assumes), and how and by when will each be validated?

## 1.6 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

| ID | The system must never | Source (regulation, policy, contract) |
| --- | --- | --- |
| UI-INV-1 | Show a secret value on any page; credentials appear only as fingerprints and dates, and log lines shown are redacted | UI-FR-4; NFR-4 |
| UI-INV-2 | Serve the UI on anything other than `127.0.0.1` | UI-FR-1; NFR-7 |
| UI-INV-3 | Put a login token in a log or a notification | UI-FR-2 |
| UI-INV-4 | Accept a credential value typed into the browser | UI-FR-11 ("Values are never typed into the browser") |
| UI-INV-5 | Accept a state-changing request without a CSRF token, or run a maintenance action without explicit confirmation | UI-FR-3 |

These invariants are verified by UI-4, UI-1, UI-2, UI-11 and UI-3 respectively.

## 1.7 Known constraints and decisions

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

| Decision or constraint | Status (made or open) | Rationale or link |
| --- | --- | --- |
| A lightweight local UI exists | Made | Owner decision D6 (REVIEW-v1 1) |
| Server-rendered Starlette routes and Jinja2 templates inside the daemon, one vendored htmx file, no JavaScript build | Made (ADR status: proposed, accepted when the owner approves the PRD) | [ADR 0010](../../adr/0010-localhost-ui-stack.md); rejected Streamlit, Gradio, NiceGUI and a React single-page app |
| Same port as the MCP endpoint; no separate process, no build step, no CDN | Made | UI-FR-1 |
| Works in Safari and Chrome at laptop width; no JavaScript framework | Made | UI-FR-6 |
| UI text has no em dashes or en dashes | Made | UI-FR-7; NFR-11 |
| Cache retention is 120 days and archiving keeps a paper searchable (affects the Cache and Archive pages) | Made | Owner decision of 2026-10-19; [ADR 0011](../../adr/0011-archive-keeps-text-searchable-120-day-retention.md) |
| Review timing: unanswered items are asked again after 7 days; discards go to a 7-day trash | Made | PRD-v4 11, O8 |

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

| ID | As a... I want... so that... | Priority | Why this priority |
| --- | --- | --- | --- |

No stories exist yet; see the first open question in 2.13.

## 2.3 User experience

> **Owner:** C · **Persona:** `product-writer` drafts the narrative; designers own the design artifacts · **Seed question:** 3

**Entering the UI.** The owner runs `research-mcp ui`, or clicks a macOS notification, which runs that command. The command mints a one-time token at that moment and opens the matching page; the session continues in an HttpOnly, SameSite=Strict cookie (UI-FR-2; SPEC-v2 10.4, 11).

**Answering a review.** At 09:00 the scheduler finds documents expiring within 3 days and creates a batch. The owner gets one notification; clicking it opens the review page for that batch. The owner archives some items, discards others and may leave some unanswered. Archived items go to Drive and stay searchable; discards go to the trash for 7 days; unanswered items are kept and asked about again (HLD-v3 11.3; UI-FR-15).

**Rotating a credential.** A notification says a token expires soon. Clicking it opens the Credentials page, which links to the provider's token page and shows the value-free `security` command. After rotating, the owner presses "Reload credentials"; the fingerprint changes and the state returns to `ok` (HLD-v3 11.4; UI-FR-11).

**Checking status.** The source board is the home page: one row per source with a state chip and counts at the top, refreshing live (UI-FR-5, UI-FR-10).

No design artifacts are linked yet.

## 2.4 Functional requirements and acceptance criteria

> **Owner:** C · **Persona:** `product-writer` drafts requirements and criteria as options; the owner selects and approves · **Seed questions:** 3, 12

General requirements (PRD-ui-v2 2.1), then pages in navigation order (PRD-ui-v2 2.2).

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| UI-FR-1 | Served by the daemon on `127.0.0.1` only, at the same port as the MCP endpoint, under `/ui`. No separate process, no build step, no CDN: server-rendered HTML with a vendored htmx file. | | OUT-8 | P1 |
| UI-FR-2 | Access starts from a one-time token URL that `research-mcp ui` mints at the moment of use (a notification click runs that command); the session is an HttpOnly, SameSite=Strict cookie; tokens never appear in logs or notifications. Host and Origin headers are checked. | | OUT-8 | P1 |
| UI-FR-3 | Every state-changing request carries a CSRF token; every maintenance action shows what it will do and needs explicit confirmation. | | OUT-8 | P1 |
| UI-FR-4 | No page ever shows a secret value; credentials appear as fingerprints and dates. Log lines shown are redacted. | | OUT-8 | P1 |
| UI-FR-5 | Pages refresh live data every 10 seconds (or on a server-sent event) without a full reload. | | OUT-8 | P2 |
| UI-FR-6 | Pages work in Safari and Chrome at laptop width; no JavaScript framework. | | OUT-8 | P1 |
| UI-FR-7 | UI text follows the owner's style: no em dashes or en dashes. | | OUT-8 | P1 |
| UI-FR-10 | **Source board** (home). Shows one row per source, grouped by group, with a state chip and counts at the top ("31 ok, 2 degraded, 1 expiring, 4 unconfigured"); per row: last probe, calls in 24 h, error rate, p95 latency, quota remaining and reset, last classified error, fix hint. Actions: probe now (one or all); open source detail (latency chart, recent errors by correlation id, recent calls); enable or disable. | | OUT-8 | P1 |
| UI-FR-11 | **Credentials.** Shows per credential: name, sources that use it, required or optional, fingerprint, Keychain modified date, expiry with countdown, `rotate_by`, last validated, state, and the provider's key page link. Actions: re-check; reload from Keychain; set or clear `rotate_by`; acknowledge; copy the value-free `security` command. Values are never typed into the browser. | | OUT-8 | P1 |
| UI-FR-12 | **Quota.** Shows for metered sources: allowance, used, remaining, reset, projected exhaustion; GitHub remaining per resource. Actions: edit per-source budget caps (with confirmation). | | OUT-8 | P1 |
| UI-FR-13 | **Jobs.** Shows running, queued and recent jobs (fetch batch, crawl, archive, reconcile, rebuild, import) with progress, timing and errors. Actions: cancel; retry; view log for the job. | | OUT-8 | P1 |
| UI-FR-14 | **Cache.** Shows cached, pinned and archived items: title, source, size, fetched, age, days to expiry (cached only), state, archive path (archived only); totals by type and state, growth per day, free disk; a filter box and a search box over cached and archived items ("do I already have this?"). Actions: pin or unpin; archive now; discard (to trash, confirmed); open the original URL. | | OUT-8 | P1 |
| UI-FR-15 | **Cache review** (`/ui/review/<batch_id>`). Shows the open batch: per item title, citation, size, age, times asked, integrity changes, and the four choices; a note that unanswered items are kept and asked about again in 7 days. Actions: submit per-item or bulk decisions; the confirmation summarizes what will be archived (and where) and what goes to the trash. | | OUT-8 | P1 |
| UI-FR-16 | **Archive.** Shows archive target health and upload state; a catalog of archived items with date, Drive path, search coverage (text and embeddings present) and copy-citation; records of discarded items; trash with undo. Actions: change the archive path (confirmed); run reconcile; run the archive rebuild job (confirmed); undo a discard within 7 days; copy citation or BibTeX. | | OUT-8 | P1 |
| UI-FR-17 | **Maintenance.** Shows the last run and result of each check (integrity, orphans, embedding coverage, schema version, dependency audit, state backup) and a disk panel. Actions: verify now; rebuild full-text index; re-embed missing; clean orphans; back up state now. All confirmed. | | OUT-8 | P1 |
| UI-FR-18 | **Events and logs.** Shows notification history with acknowledged state, and recent warning and error log lines (redacted), searchable by correlation id, source or tool. Actions: acknowledge; snooze for N days. | | OUT-8 | P1 |
| UI-FR-19 | **Settings.** Shows the effective configuration (paths, port, thresholds, quiet hours, channels, archive target), which credential references resolve (names only), versions, and launchd job state. Actions: edit thresholds, quiet hours and channels (confirmed); send a test notification. | | OUT-8 | P1 |

Acceptance criteria, in the order of `tools/gen_test_plan.py`.

| ID | Criterion | Requirement | Priority | Level | Milestone |
| --- | --- | --- | --- | --- | --- |
| UI-1 | The UI shall be served only on loopback under /ui with no external assets. | UI-FR-1, UI-FR-6 | P1 | integration | M3 |
| UI-2 | When `research-mcp ui` runs, the UI login flow shall mint a one-time token at use time, set an HttpOnly SameSite=Strict cookie with Path=/ at login, and use tokens that expire, cannot be reused and never appear in access logs (uvicorn access log off). | UI-FR-2 | P1 | integration | M3 |
| UI-3 | The UI shall refuse POSTs without a valid CSRF token and require confirmation for maintenance actions. | UI-FR-3 | P1 | integration | M3 |
| UI-4 | The UI shall render no page that contains a registered secret value, as checked by scanning every page with fake secrets. | UI-FR-4, NFR-4 | P1 | integration | M3 |
| UI-5 | The UI shall refresh page fragments through htmx endpoints. | UI-FR-5 | P2 | integration | M3 |
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
| UI-19 | The Settings page shall show the effective config with names only for credentials and provide a test notification that works. | UI-FR-19 | P1 | integration | M3 |

Related criteria owned by other components: HLTH-32 also verifies UI-FR-2 (no token in the notifier argv; TEST-PLAN-v3 traceability). OC-05, the owner walkthrough of every UI page, covers UI-FR-10 and UI-FR-19 (TEST-PLAN-v3).

## 2.5 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |

Parent NFRs that apply to this component: NFR-4 (no secret in any output, including UI pages), NFR-7 (loopback only; every request except the health checks needs a bearer token or a UI session) and NFR-11 (no em dashes or en dashes in UI text) (PRD-v4 6). The 10 second refresh is a functional requirement (UI-FR-5).

- [ ] Q: Does the UI have its own latency, availability or browser-support targets beyond the parent NFRs and UI-FR-6 (for example a page render time)? If so, what are they?

## 2.6 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

| Data | Classification | Source or owner | Retention | Notes |
| --- | --- | --- | --- | --- |
| Credential metadata: name, fingerprint, Keychain modified date, expiry, `rotate_by`, state | | Health and credentials component | | Values are never shown or typed into the browser (UI-FR-4, UI-FR-11) |
| Log lines (warnings and errors) | | Platform logging | | Shown redacted (UI-FR-4, UI-FR-18) |
| Cached, pinned, archived and discarded items | | Retrieval and cache component | 120 days in the cache (ADR 0011); 7-day trash | Read and acted on through the Cache, Review and Archive pages |
| Notifications and their acknowledged state | | Health and credentials component | | Shown on the Events page |
| One-time login token and session cookie | | This component and platform | Token valid for a short time; see the LLD | Never in logs or notifications (UI-FR-2) |

- [ ] Q: How is each data item above classified, and what retention applies where none is stated?

## 2.7 Integrations and owners

> **Owner:** H confirms owners and SLAs · **Persona:** `architect` may draft · **Seed question:** 8

| System | Owner | Relationship (depends on, feeds, replaces) | SLA |
| --- | --- | --- | --- |
| Daemon (`research-mcpd`), the same services the MCP tools use | Platform component and each service's component | Depends on: pages read those services, so there is no second API (HLD-v3 8) | |
| `research-mcp ui` command and the macOS notifier | Platform; health and credentials | Depends on: entry point that mints the one-time token (SPEC-v2 10.4, 11) | |
| macOS Keychain (`/usr/bin/security`) | The owner's Mac | Depends on: the UI shows a value-free command; reload re-reads keys (UI-FR-11) | |
| Google Drive sync folder (archive target) | The owner's Google account | Depends on: shown on the Archive page (UI-FR-16) | |
| Safari and Chrome | The owner's Mac | Client (UI-FR-6) | |

- [ ] Q: Are the owners above correct, and is any SLA needed for these integrations?

## 2.8 Product risks

> **Owner:** H · **Persona:** none

| Risk | Question | Assessment | Mitigation |
| --- | --- | --- | --- |
| Value | Will customers choose to use this? | | |
| Usability | Can customers use it, including with accessibility needs? | | |
| Viability | Does it work for the business: economics, legal, compliance, operations? | | |

- [ ] Q: What is your assessment and mitigation for the value, usability (including accessibility) and viability risks of the UI?

## 2.9 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | Milestone M3 delivers all UI pages (PRD-v4 10) |
| Business conditions that must halt the rollout | |
| Support owner and escalation path | |
| Response targets by severity (S0 to S4) | |

- [ ] Q: What conditions must halt the M3 rollout, who supports the UI, and what response targets apply by severity?

## 2.10 Measurement and experimentation

> **Owner:** C · **Persona:** `product-writer` drafts; the owner decides

| Outcome | Measured by | Experiment (if any) |
| --- | --- | --- |
| UI-OUT-1 | UI acceptance criteria UI-1 to UI-19 passing, and the owner walkthrough of every UI page (OC-05, TEST-PLAN-v3) | None |

## 2.11 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

M3 exit: UI acceptance tests green; owner walkthrough (PRD-v4 10).

## 2.12 Edge cases and error behavior

> **Owner:** A · **Persona:** `product-writer`

| Edge case | Behavior | Criterion |
| --- | --- | --- |
| A login token is reused or presented after it expires | Refused | UI-2 |
| A POST arrives without a valid CSRF token | Refused | UI-3 |
| A request carries a foreign Host or Origin | Refused (UI-FR-2; verified for the daemon by SEC-12) | none in this PRD |
| A review item is left unanswered | Kept and asked about again in 7 days (UI-FR-15) | none in this PRD |
| A discard is undone within 7 days | Restored from the trash (UI-FR-16) | UI-16 |
| `terminal-notifier` is not installed | The built-in notification fallback cannot be clicked through, so it does not open the UI (HLTH-FR-32; PRD-health-v2) | none in this PRD |
| The Keychain is locked | Every credential is `keychain_locked` at once (PRD-health-v2 2.3) | none in this PRD |

- [ ] Q: Should the edge cases above that have no UI criterion (foreign Host or Origin on `/ui`, unanswered review items, the non-clickable fallback notification, a locked Keychain) get their own UI criteria?

## 2.13 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves before Gate 1

- [ ] Q: Which user stories does the UI serve, and with what priority? Requirements UI-FR-1 to UI-FR-19 have no story yet.
- [ ] Q: Assumption to confirm: the page requirements UI-FR-10 to UI-FR-19 came from a table with no priority column (PRD-ui-v2 section 2, "Pages"). This draft marks each page P1, so criteria UI-10 to UI-19 are P1 too. Which pages are P1, P2 or P3?
- [ ] Q: PLAT-FR-16 (PRD-platform-v2) says the daemon bearer token "can be rotated from the UI", but no UI page in this PRD offers that action (the CLI has `secrets rotate-token`). Should a page offer it, and which one?
- [ ] Q: UI-FR-5 allows refresh "every 10 seconds (or on a server-sent event)"; SPEC-v2 11 specifies only `hx-get` polling every 10 s. Is the server-sent event option still wanted?
- [ ] Q: UI-FR-13 offers "retry" for jobs, but SPEC-v2 3.6 `JobService` defines only `submit`, `status`, `cancel` and `list`. Is retry a resubmit with the same parameters?
- Assumption: the "four choices" on the review page (UI-FR-15) are archive, discard, keep and pin, the decisions SPEC-v2 9.1 allows for an `expiring` item.

## 2.14 Glossary

> **Owner:** A · **Persona:** `product-writer`

| Term | Definition |
| --- | --- |
| One-time token | A short-lived login token minted by `research-mcp ui` at the moment of use and consumed at login (UI-FR-2) |
| Session cookie | The HttpOnly, SameSite=Strict cookie that carries the UI session after login (UI-FR-2) |
| CSRF token | A token every state-changing request carries (UI-FR-3) |
| Fragment | A part of a page reloaded through htmx without a full reload (UI-FR-5) |
| Review batch | The set of cached items the owner is asked to archive or discard, opened at `/ui/review/<batch_id>` (UI-FR-15) |
| Fingerprint | The first 8 hex characters of the SHA-256 of a credential value, shown instead of the value (HLTH-FR-20; PRD-health-v2) |

## 2.15 ID history

> **Owner:** C · **Persona:** `product-writer` records; the owner confirms

| ID | Status | Replaced by | Reason |
| --- | --- | --- | --- |

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
| FR-UI-05 | UI-FR-5 |
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
| FR-UI-19 | UI-FR-19 |
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
