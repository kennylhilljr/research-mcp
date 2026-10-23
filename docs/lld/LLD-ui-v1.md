---
title: "Local UI low level design"
type: lld
version: 1
status: draft
owner: "Kenny Hill"
prefix: UI
component: ui
parent: docs/spec/SPEC-v3.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# LLD: Local UI (v1)

Requirements: [PRD-ui v3](../prd/components/PRD-ui-v3.md). Governing section: [SPEC-v3](../spec/SPEC-v3.md) section 8. Derived from [SPEC-v2](../../docs-archive/spec/SPEC-v2.md) section 11 (UI) and the parts of sections 1, 2, 3 and 10 that define the UI's modules, routes and tokens, and from [HLD-v3](../../docs-archive/design/HLD-v3.md) section 8. Anything the platform owns (`app.py`, `daemon.py`, `cli.py`, `settings.py`, `platform/auth.py`, `platform/redact.py`, `platform/logging.py`, `platform/secrets.py`) is specified in [LLD-platform v1](LLD-platform-v1.md) and only referenced here. Names below are copied from SPEC-v2; none is renamed.

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

| Requirement | Criteria | SPEC section |
| --- | --- | --- |
| UI-FR-1 | UI-1 | SPEC-v3 section 8 |
| UI-FR-2 | UI-2 (also HLTH-32, owned by health) | SPEC-v3 section 8 |
| UI-FR-3 | UI-3 | SPEC-v3 section 8 |
| UI-FR-4 | UI-4 | SPEC-v3 section 8 |
| UI-FR-5 | UI-5 | SPEC-v3 section 8 |
| UI-FR-6 | UI-1 | SPEC-v3 section 8 |
| UI-FR-7 | UI-6 | SPEC-v3 section 8 |
| UI-FR-10 | UI-10 | SPEC-v3 section 8 |
| UI-FR-11 | UI-11 | SPEC-v3 section 8 |
| UI-FR-12 | UI-12 | SPEC-v3 section 8 |
| UI-FR-13 | UI-13 | SPEC-v3 section 8 |
| UI-FR-14 | UI-14 | SPEC-v3 section 8 |
| UI-FR-15 | UI-15 | SPEC-v3 section 8 |
| UI-FR-16 | UI-16 | SPEC-v3 section 8 |
| UI-FR-17 | UI-17 | SPEC-v3 section 8 |
| UI-FR-18 | UI-18 | SPEC-v3 section 8 |
| UI-FR-19 | UI-19 | SPEC-v3 section 8 |
| NFR-4 (parent) | UI-4 | SPEC-v3 section 8 |
| NFR-11 (parent) | UI-6 | SPEC-v3 section 8 |

Criteria satisfied: UI-1, UI-2, UI-3, UI-4, UI-5, UI-6, UI-10, UI-11, UI-12, UI-13, UI-14, UI-15, UI-16, UI-17, UI-18, UI-19.

Related criteria owned by the platform and security components, which the UI relies on: SEC-11 (`/api` requests without the bearer token get 401), SEC-12 (foreign Host or Origin refused), PLAT-71 and PLAT-10 (no non-loopback bind).

SPEC-v2 0.6 (clarifications from the first M0 attempt) has no row for this component; every row concerns units M0-01 to M0-05.

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

No machine-readable contract exists in `docs/contracts/` for the UI yet. The contracts below are the SPEC-v2 text.

### 2.1 Mount and routes

The UI is mounted at `/ui` in the daemon's Starlette app (SPEC-v2 11). `build_app(settings)` mounts `/mcp`, `/ui`, `/healthz`, `/readyz` and `/api` (SPEC-v2 1; owned by the platform). `server.port` (default `7319`) serves MCP at `/mcp` and the UI at `/ui` (SPEC-v2 2).

**Routes** (SPEC-v2 11, verbatim):

- Pages: `/ui/` (source board), `/ui/sources/<id>`, `/ui/credentials`, `/ui/quota`, `/ui/jobs`, `/ui/cache`, `/ui/review/<batch_id>`, `/ui/archive`, `/ui/maintenance`, `/ui/events`, `/ui/settings`.
- Actions: POST routes under the same paths, at `/action/<name>`.

| Route | Page (PRD-ui v3) | Requirement |
| --- | --- | --- |
| `/ui/` | Source board (home) | UI-FR-10 |
| `/ui/sources/<id>` | Source detail (latency chart, recent errors by correlation id, recent calls) | UI-FR-10 |
| `/ui/credentials` | Credentials | UI-FR-11 |
| `/ui/quota` | Quota | UI-FR-12 |
| `/ui/jobs` | Jobs | UI-FR-13 |
| `/ui/cache` | Cache | UI-FR-14 |
| `/ui/review/<batch_id>` | Cache review | UI-FR-15 |
| `/ui/archive` | Archive | UI-FR-16 |
| `/ui/maintenance` | Maintenance | UI-FR-17 |
| `/ui/events` | Events and logs | UI-FR-18 |
| `/ui/settings` | Settings | UI-FR-19 |
| `/ui/login` | Login (consumes the one-time token) | UI-FR-2 |

### 2.2 Login and session

From SPEC-v2 11, verbatim:

- `research-mcp ui [--path P]` creates a one-time token (32 random bytes, valid for 5 minutes) through `POST /api/ui-token`, using the daemon bearer token, and opens `http://127.0.0.1:<port>/ui/login?t=...&next=P` in the browser.
- `GET /ui/login` consumes the token, sets the session cookie `rmcp_session` (HttpOnly, SameSite=Strict, `Path=/`, 12-hour life), and redirects to `next`.
- Uvicorn access logging is off, so tokens never reach a log.

| Element | Contract | Owner |
| --- | --- | --- |
| `research-mcp ui [--path P]` | CLI subcommand "Open the UI with a one-time login" (SPEC-v2 12.1) | Platform (`cli.py`) |
| `POST /api/ui-token` | Mints the one-time token; requires the daemon bearer token (`server.token`, `keychain:research-mcp/DAEMON_TOKEN`) | Platform (`platform/auth.py`: "UI one-time tokens", SPEC-v2 1) |
| `GET /ui/login?t=...&next=P` | Consumes the token once, sets `rmcp_session`, redirects to `next` | UI (`ui/auth.py`) |
| `rmcp_session` cookie | HttpOnly, SameSite=Strict, `Path=/`, 12-hour life | UI (`ui/auth.py`) |
| Notifier click-through | `terminal-notifier ... -execute "<venv>/bin/research-mcp ui --path <ui_path>"`; the `ui` command mints its one-time login token when the notification is clicked, so no token sits in the notification itself, in a process argument list or in Notification Center (SPEC-v2 10.4) | Health (`services/notify.py`) |
| `/api/status` | Auth: "bearer token or a UI session"; returns JSON of sources, credential metadata, quotas, jobs, cache stats, disk, the archive target and the last 20 notifications (SPEC-v2 10.5) | Platform and health |

### 2.3 Request checks

From SPEC-v2 11, verbatim:

- Every POST requires the header `X-CSRF-Token`, which htmx sends from a meta tag.
- The Host must be `127.0.0.1:<port>` or `localhost:<port>`. If an Origin header is present, it must match.

### 2.4 Partial refresh and confirmation

From SPEC-v2 11, verbatim: page fragments reload with `hx-get` every 10 s. Confirmations use `hx-confirm` with a summary rendered by the server.

Every maintenance action shows what it will do and needs explicit confirmation (UI-FR-3). The review confirmation summarizes what will be archived (and where) and what goes to the trash (UI-FR-15).

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

The UI owns no table and no migration. "No SQL appears outside `platform/stores.py` and the `services/*` repositories" (SPEC-v2 3.5), so `ui/` reads and writes only through services. Pages read the same services the MCP tools use, so there is no second API (HLD-v3 8).

**State the UI shows, by page.** The tables are defined in SPEC-v2 8.1 (`cache.db`) and 10.1 (`state.db`). The mapping from page fields to tables is [inferred] from column names; SPEC-v2 does not state it.

| Page | Tables read through services [inferred] |
| --- | --- |
| Source board, source detail | `source_health`, `call_rollups`, `calls` |
| Credentials | `credentials` |
| Quota | `source_health` (`quota_remaining`, `quota_reset`, `budget_reset_at`, `calls_today`) |
| Jobs | `jobs` |
| Cache | `documents`, `files`, `works`, `disk_samples` |
| Cache review | `review_batches`, `documents` |
| Archive | `documents` (`archive_path`, `archive_upload_state`, `archive_fallback`, `discarded_at`, `trash_until`) |
| Maintenance | `maintenance_runs`, `disk_samples` |
| Events and logs | `notifications` (`acknowledged_at`, `snoozed_until`) |

**Lifecycle writes made from the UI** (SPEC-v2 9.1, verbatim rows):

| From | Event | To | Side effects |
|---|---|---|---|
| expiring | archive (owner in the UI, or agent through MCP) | archived | Archive job (9.3) |
| expiring | discard (owner in the UI, or agent through `cache_review_decide`) | discarded | Files to trash; `trash_until = now + 7 d`; MCP discards notify at once |
| cached, pinned or kept | owner discard on the UI Cache page (confirmed) | discarded | As above |
| discarded | undo before `trash_until` (UI Archive page, or `library restore`) | cached | Restore files from trash; `expires_at = now + 120 d` |

- `decided_by` is `owner` for the UI and `agent` for MCP. `decided_channel` is `ui` or `mcp`. Every transition writes an outbox row (3.5). (SPEC-v2 9.1)

**Settings the UI changes** (SPEC-v2 2):

| Key | Notes from SPEC-v2 2 |
| --- | --- |
| `archive.confirmed_path` | Set when the owner confirms the detected target in the UI or with `config set`; archiving to `auto` waits for this confirmation |
| `sources.<id>.budget_cap` | Daily call cap for metered sources (UI Quota page); resets at local midnight |
| `sources.<id>.enabled` | Spec default; a source is `disabled` when turned off in configuration or the UI (PRD-health-v2 2.2) |
| `credentials.<NAME>.rotate_by` | Optional override; set or cleared on the Credentials page (UI-FR-11) |
| `notify.quiet_hours`, `notify.macos`, `notify.webhook_url` | Quiet hours and channels, edited on the Settings page (UI-FR-19) |

The one-time token and the session have no storage defined in SPEC-v2 (section 11).

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

| Point | Enforcement | Where | Criterion |
| --- | --- | --- | --- |
| Bind | `server.host` default `127.0.0.1`; validation rejects any non-loopback value; the daemon runs uvicorn on 127.0.0.1 | Platform (`settings.py`, `daemon.py`) | UI-1; PLAT-10, PLAT-71 |
| Token mint | `POST /api/ui-token` requires the daemon bearer token; the comparison uses `hmac.compare_digest` | Platform (`platform/auth.py`) | UI-2; SEC-11 |
| Token use | `GET /ui/login` consumes the token (32 random bytes, valid for 5 minutes); a token cannot be reused | `ui/auth.py` | UI-2 |
| Session | `rmcp_session`: HttpOnly, SameSite=Strict, `Path=/`, 12-hour life | `ui/auth.py` | UI-2 |
| CSRF | Every POST requires `X-CSRF-Token`, sent by htmx from a meta tag | `ui/csrf.py` | UI-3 |
| Host and Origin | Host must be `127.0.0.1:<port>` or `localhost:<port>`; a present Origin must match | `ui/auth.py` [inferred]; SEC-12 covers the daemon | UI-3; SEC-12 |
| Confirmation | Every maintenance action needs explicit confirmation (`hx-confirm` with a server-rendered summary) | `ui/routes.py` | UI-3, UI-17 |
| No secret on a page | `Secret.reveal` is called only in `platform/http.py`, `platform/mcp_client.py` and `platform/auth.py` (SPEC-v2 3.1), so `ui/` never reveals a value; credentials appear as fingerprints and dates; one redaction filter covers UI pages (PLAT-FR-13; HLD-v3 9) | `ui/` templates; platform `Redactor` | UI-4 |
| No value typed in the browser | Credentials page offers the value-free `security add-generic-password -U -s research-mcp/<NAME> -a "$USER" -w` command (HLTH-FR-24); "Values are never typed into the browser" (UI-FR-11) | `ui/` | UI-11 |
| Owner-only operations | Fix actions (`rebuild_fts`, `reembed_missing`, `clean_orphans` and `backup_state`) are job kinds that can be started only from the UI or the CLI (SPEC-v2 9.4) | `ui/routes.py` | UI-17 |

Threat context (HLD-v3 9): other local processes calling the daemon are controlled by loopback only, bearer token, Host and Origin checks, and the UI session cookie plus CSRF.

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

### 5.1 Files

From the SPEC-v2 1 layout:

```
src/research_mcp/
  app.py                      # build_app(settings) -> Starlette app (mounts /mcp, /ui, /healthz, /readyz, /api)
  platform/
    auth.py                   # daemon token: mint, compare (hmac.compare_digest), HKDF cursor key, UI one-time tokens
  ui/
    routes.py auth.py csrf.py
    templates/*.html  static/htmx.min.js  static/app.css
tests/
  ui/
```

- Templates live in `ui/templates`, one per page in PRD-ui section 2.2, plus a base layout with navigation and a banner slot (SPEC-v2 11).
- The banner slot carries the UI banner channel: a notification shows as a UI banner until resolved or acknowledged (HLTH-FR-32).
- Package data includes `research_mcp/ui/templates/*.html` and `research_mcp/ui/static/*` (SPEC-v2 12.1). Dependencies include `starlette`, `jinja2` and `uvicorn` (SPEC-v2 12.1).
- `src/research_mcp/ui/__init__.py` is created by unit M0-01 (SPEC-v2 12.3).
- `platform/auth.py`, `app.py` and the `ui` CLI command belong to the platform; see [LLD-platform v1](LLD-platform-v1.md).

### 5.2 Services the pages use

Named in SPEC-v2; the UI calls them and never reaches the stores directly.

| Service or type | Members named in SPEC-v2 | Used by |
| --- | --- | --- |
| `JobService` | `submit(kind, params) -> job_id`, `status(job_id)`, `cancel(job_id)`, `list(state)` (3.6) | Jobs; Maintenance and Archive actions that start jobs |
| `SecretCache` | `reload() -> list[str]` (names whose fingerprint changed) (3.1) | Credentials "reload from Keychain" |
| `LifecycleService` | `run_review(now)` (9.2) | Cache review data |
| `ArchiveService` | `archive(doc_id)`, `reconcile()`, `reindex(root)` (job kind `archive_reindex`) (9.3, 9.7) | Archive, Cache |
| `MaintenanceService` | `daily()`; results in `maintenance_runs` (9.4) | Maintenance |
| `BackupService` | `backup_state()` (9.8) | Maintenance "back up state now" |
| `DiskService` | `sample()`; writes `disk_samples` (9.4) | Cache, Maintenance disk panel |
| `NotifyService` | `emit(event)` (10.4) | Settings "send a test notification" |
| `HealthService` | Probe scheduling (10.2) | Source board "probe now" |

Job kinds the UI starts: `rebuild_fts`, `reembed_missing`, `clean_orphans`, `backup_state` (9.4) and `archive_reindex` (9.7).

### 5.3 Pages

| Page | Route | Shows | Actions |
| --- | --- | --- | --- |
| Source board | `/ui/` | One row per source, grouped by group, with a state chip and counts at the top; per row: last probe, calls in 24 h, error rate, p95 latency, quota remaining and reset, last classified error, fix hint | Probe now (one or all); open source detail; enable or disable |
| Credentials | `/ui/credentials` | Name, sources that use it, required or optional, fingerprint, Keychain modified date, expiry with countdown, `rotate_by`, last validated, state, provider's key page link | Re-check; reload from Keychain; set or clear `rotate_by`; acknowledge; copy the value-free `security` command |
| Quota | `/ui/quota` | Allowance, used, remaining, reset, projected exhaustion; GitHub remaining per resource | Edit per-source budget caps (confirmed) |
| Jobs | `/ui/jobs` | Running, queued and recent jobs with progress, timing and errors | Cancel; retry; view log for the job |
| Cache | `/ui/cache` | Cached, pinned and archived items; totals by type and state, growth per day, free disk; filter and search boxes | Pin or unpin; archive now; discard (to trash, confirmed); open the original URL |
| Cache review | `/ui/review/<batch_id>` | The open batch: per item title, citation, size, age, times asked, integrity changes, the four choices; the note that unanswered items are kept and asked about again in 7 days | Per-item or bulk decisions with a summary confirmation |
| Archive | `/ui/archive` | Target health and upload state; catalog with date, Drive path, search coverage and copy-citation; discarded items; trash with undo | Change the archive path (confirmed); run reconcile; run the archive rebuild job (confirmed); undo a discard within 7 days; copy citation or BibTeX |
| Maintenance | `/ui/maintenance` | Last run and result of each check; disk panel | Verify now; rebuild full-text index; re-embed missing; clean orphans; back up state now; all confirmed |
| Events and logs | `/ui/events` | Notification history with acknowledged state; recent warning and error log lines (redacted), searchable by correlation id, source or tool | Acknowledge; snooze for N days |
| Settings | `/ui/settings` | Effective configuration, credential references that resolve (names only), versions, launchd job state | Edit thresholds, quiet hours and channels (confirmed); send a test notification |

The full field lists are in PRD-ui v3 2.4 (UI-FR-10 to UI-FR-19).

### 5.4 Algorithms

**Login** (SPEC-v2 11, 10.4):

1. The owner runs `research-mcp ui [--path P]`, directly or through a notification click.
2. The command calls `POST /api/ui-token` with the daemon bearer token; the daemon creates a one-time token (32 random bytes, valid for 5 minutes).
3. The command opens `http://127.0.0.1:<port>/ui/login?t=...&next=P`.
4. `GET /ui/login` consumes the token, sets `rmcp_session` and redirects to `next`.

**State-changing request** (SPEC-v2 11):

1. Check the Host (`127.0.0.1:<port>` or `localhost:<port>`) and, if present, the Origin.
2. Check the session cookie.
3. Check `X-CSRF-Token`.
4. For a maintenance action, the request follows an `hx-confirm` showing the server-rendered summary.

**Review decision** (SPEC-v2 9.1, 9.2): the batch comes from `review_batches`; decisions apply the 9.1 transitions with `decided_by = owner` and `decided_channel = ui`. Unanswered items become `kept` when the batch closes (`cache.batch_open_hours` after the notification) and are asked again after `cache.reask_days`.

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

- A POST without a valid CSRF token is refused (UI-3). A request with a foreign Host, or an Origin that does not match, is refused (SPEC-v2 11).
- A one-time token is consumed at login, so it cannot be reused, and it expires after 5 minutes (SPEC-v2 11; UI-2).
- Errors carry codes, not exception text (HLD-v3 9). The error codes are the `ErrorCode` values of SPEC-v2 3.7.
- Lifecycle actions follow the 9.1 transition table; the archive copy is verified before the cached file is removed (SPEC-v2 9.1, 9.3).
- SPEC-v2 defines no HTTP status codes or error pages for UI refusals, and no retry behavior for UI actions (section 11).

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

| Flag | Default | Safe to switch off? |
| --- | --- | --- |
| None defined in SPEC-v2 for the UI | | |

Settings the UI depends on (SPEC-v2 2):

| Key | Default | Notes |
| --- | --- | --- |
| `server.host` | `127.0.0.1` | Validation rejects any non-loopback value. |
| `server.port` | `7319` | MCP at `/mcp`, UI at `/ui`. |
| `server.token` | `keychain:research-mcp/DAEMON_TOKEN` | Bearer for the shim and API. |
| `cache.batch_open_hours` | `24` | Unanswered items become `kept` when the batch closes |
| `cache.reask_days` | `7` | |
| `cache.trash_days` | `7` | |
| `archive.target` | `auto` | `auto` finds the single `~/Library/CloudStorage/GoogleDrive-*/My Drive`; else an absolute path |
| `archive.confirmed_path` | none | Set when the owner confirms the detected target in the UI or with `config set`; archiving to `auto` waits for this confirmation |
| `notify.quiet_hours` | `"21:00-08:00"` | |
| `sources.<id>.enabled` | spec default | |
| `sources.<id>.budget_cap` | none (`100` for `web` sources) | Daily call cap for metered sources (UI Quota page); resets at local midnight |
| `credentials.<NAME>.rotate_by` | none | Optional override |

Fixed values from SPEC-v2 11: one-time token 32 random bytes, valid for 5 minutes; session cookie 12-hour life; fragment refresh every 10 s.

## 8. Observability

> **Owner:** A · **Persona:** `sre`

- Uvicorn access logging is off, so tokens never reach a log (SPEC-v2 11). `configure_logging(settings)` sets the `uvicorn.access` logger to `WARNING` (SPEC-v2 3.2; platform).
- `RedactingFilter` is attached to every handler, so records from the UI are redacted (SPEC-v2 3.2; platform).
- `correlation_id` comes from a `contextvars.ContextVar` set per tool call and per job (SPEC-v2 3.2). The Events page searches log lines by correlation id, source or tool (UI-FR-18).
- Log file: `RotatingFileHandler(log_dir/research-mcp.jsonl, 10 MB, 5)` with a JSON formatter (SPEC-v2 3.2). The UI shows recent warnings and errors (HLD-v3 12).
- SPEC-v2 defines no UI metrics or alerts, and no NFR threshold applies to the UI.

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

No test in `tests/` cites an `AT-UI` id yet. SPEC-v2 1 names the test folder `tests/ui/`; neither SPEC-v2 nor TEST-PLAN-v3 names a test file for these criteria (TEST-PLAN-v3 4.7 lists their unit as "later").

| Criterion | Planned tests | Level | Status |
| --- | --- | --- | --- |
| UI-1 | planned (`tests/ui/`) | integration | planned |
| UI-2 | planned (`tests/ui/`) | integration | planned |
| UI-3 | planned (`tests/ui/`) | integration | planned |
| UI-4 | planned (`tests/ui/`) | integration | planned |
| UI-5 | planned (`tests/ui/`) | integration | planned |
| UI-6 | planned (`tests/ui/`) | unit | planned |
| UI-10 | planned (`tests/ui/`) | integration | planned |
| UI-11 | planned (`tests/ui/`) | integration | planned |
| UI-12 | planned (`tests/ui/`) | integration | planned |
| UI-13 | planned (`tests/ui/`) | integration | planned |
| UI-14 | planned (`tests/ui/`) | integration | planned |
| UI-15 | planned (`tests/ui/`) | integration | planned |
| UI-16 | planned (`tests/ui/`) | integration | planned |
| UI-17 | planned (`tests/ui/`) | integration | planned |
| UI-18 | planned (`tests/ui/`) | integration | planned |
| UI-19 | planned (`tests/ui/`) | integration | planned |

Also relevant: OC-05, the owner walkthrough of every UI page (TEST-PLAN-v3), at M3.

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| Server-rendered Starlette routes and Jinja2 templates in the daemon, one vendored htmx file, no JavaScript build ([ADR 0010](../adr/0010-localhost-ui-stack.md)) | No second process, API or build chain; htmx fits a read-mostly status page | Streamlit, Gradio and NiceGUI (second process or their own app model); a React single-page app (build chain, more upkeep) |
| The `ui` command mints the login token when the notification is clicked (SPEC-v2 10.4) | No token sits in the notification itself, in a process argument list or in Notification Center | None recorded |
| Uvicorn access logging off (SPEC-v2 11) | Tokens never reach a log | None recorded |
| Pages read the same services the MCP tools use (HLD-v3 8) | No second API | None recorded |
| Partial refresh with `hx-get` every 10 s (SPEC-v2 11) | Live data without a full reload (UI-FR-5) | Server-sent events, allowed by UI-FR-5 but not specified |

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

- [ ] Q: SPEC-v2 9.2 sends the review notification with `ui_path=/review/<batch_id>`, and `research-mcp ui --path P` redirects to `next=P`, but the route is `/ui/review/<batch_id>` (SPEC-v2 11; HLD-v3 11.3). Is `P` relative to `/ui`, or must `ui_path` include the `/ui` prefix?
- [ ] Q: HLD-v3 11.3 shows a batch id `rb-2026-11-14` in `/ui/review/rb-2026-11-14`, but SPEC-v2 1 says batches use ULIDs. Which form does `<batch_id>` take?
- [ ] Q: The action route rule "POST routes under the same paths, at `/action/<name>`" (SPEC-v2 11) does not list the action names or show a full path (for example whether it is `/ui/jobs/action/<name>`). What are the action routes?
- [ ] Q: SPEC-v2 11 does not say how sessions and one-time tokens are stored or validated (server-side store or signed cookie), or whether a daemon restart ends sessions.
- [ ] Q: SPEC-v2 11 does not say how the CSRF token is generated, whether it is bound to the session, or how long it lives.
- [ ] Q: SPEC-v2 names no functions or classes in `ui/routes.py`, `ui/auth.py`, `ui/csrf.py`, or for the UI one-time tokens in `platform/auth.py`, and no template file names. What are they?
- [ ] Q: SPEC-v2 11 says one template per page in PRD-ui section 2.2 (ten pages), but the routes include an eleventh page, `/ui/sources/<id>`. Does source detail get its own template?
- [ ] Q: Which routes need no session (for example `/ui/login` and `/ui/static/*`), and what does a request without a session get (redirect, 401 or 403)?
- [ ] Q: What HTTP status and page does the UI return for an expired or reused token, a missing or invalid CSRF token, and a foreign Host or Origin?
- [ ] Q: UI-FR-5 allows "every 10 seconds (or on a server-sent event)"; SPEC-v2 11 specifies only `hx-get` every 10 s. Is the server-sent event option dropped?
- [ ] Q: PLAT-FR-16 (PRD-platform-v2) says the daemon bearer token "can be rotated from the UI", but no UI page or route offers it; only the CLI has `secrets rotate-token` (SPEC-v2 12.1).
- [ ] Q: UI-FR-13 offers "retry" for jobs, but `JobService` defines only `submit`, `status`, `cancel` and `list` (SPEC-v2 3.6). How is retry implemented?
- [ ] Q: How do settings changed in the UI (budget caps, `rotate_by`, quiet hours, channels, `archive.confirmed_path`, `sources.<id>.enabled`) persist: written to `config.toml` the same way as `config set`, or stored elsewhere?
- [ ] Q: `cache_review_decide` checks that the batch is open and that every `doc_id` belongs to it (SPEC-v2 9.2). Does the UI review submission apply the same check?
- [ ] Q: Where does the Events page read log lines from (the `research-mcp.jsonl` file, or another source), and how is the search over correlation id, source or tool done?
- [ ] Q: No feature flag is defined for the UI or for optional UI behavior (for example the live refresh). Does the UI need one, and is it safe to switch off?
- [ ] Q: No UI metrics or alerts are defined. Are any needed?
- [ ] Q: TEST-PLAN-v3 assigns no unit or test file to the UI criteria ("later"). Which test files should hold them?
- [ ] Q: The header of PRD-ui-v2 names its parent "PRD v2" but links PRD-v4, says it supersedes "v1" but links itself, and cites "SPEC v1" section 11 while SPEC-v2 is current. Which versions were intended?

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
