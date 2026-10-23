---
title: "Local UI low level design"
type: lld
version: 2
status: approved
approved_by: "Kenny Hill (Engineering)"
approved: 2026-10-23
owner: "Kenny Hill"
prefix: UI
component: ui
parent: docs/spec/SPEC-v5.md
supersedes: docs/lld/LLD-ui-v1.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# LLD: Local UI (v2)

Requirements: [PRD-ui v4](../prd/components/PRD-ui-v4.md) (approved). Governing section: [SPEC-v5](../spec/SPEC-v5.md) section 8. Related: [PRD-security v3](../prd/components/PRD-security-v3.md) (SEC-29, SEC-32, SEC-28), [LLD-security v2](LLD-security-v2.md) (the auth gate E3, the login, session and CSRF rule in 5.3, the redaction call site E40), [LLD-platform v2](LLD-platform-v2.md) (`app.py`, `platform/auth.py`, `JobService`, `config set`, flags), [LLD-health v2](LLD-health-v2.md) (notifications, the banner feed, credentials) and [LLD-cache v2](LLD-cache-v2.md) (lifecycle, archive, maintenance, backup). Those LLDs own the names they define; this one only references them.

**Changes in v2** (Gate 3 draft, 2026-10-22). It follows PRD-ui v4, SPEC-v4, the Security LLD v2 and the owner decisions of 2026-10-22. It fixes the open questions of version 1 (section 10 records each answer with its source): action and fragment routes, the `/ui` prefix of `ui_path`, ULID batch ids, in-memory sessions and one-time tokens, the per-session CSRF token, response codes, the module interfaces, the server-side confirmation rule, job retry through `JobService.submit`, settings persistence, the Events log source, the site-sets display, and the test files. History note: version 1 cited UI-FR-5 and UI-FR-19; they are now UI-FR-20 (polling every 10 seconds only, no server-sent events) and UI-FR-21 (the Settings page also shows site sets read-only). Removed in this version: any rotation of the daemon token in the UI (PLAT-FR-59, owner decision, 2026-10-22).

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

| Requirement | Criteria | SPEC section |
| --- | --- | --- |
| UI-FR-1 | UI-1 | SPEC 8 |
| UI-FR-2 | UI-2, UI-20 (also HLTH-32, SEC-12, SEC-29, SEC-32) | SPEC 8, 9 |
| UI-FR-3 | UI-3 | SPEC 8 |
| UI-FR-4 | UI-4 | SPEC 8, 9 |
| UI-FR-6 | UI-1 | SPEC 8 |
| UI-FR-7 | UI-6 | SPEC 8 |
| UI-FR-20 | UI-5 | SPEC 8 |
| UI-FR-10 | UI-10 | SPEC 8 |
| UI-FR-11 | UI-11, UI-23 | SPEC 8, 7 |
| UI-FR-12 | UI-12 | SPEC 8 |
| UI-FR-13 | UI-13, UI-24 | SPEC 8 |
| UI-FR-14 | UI-14 | SPEC 8, 6 |
| UI-FR-15 | UI-15, UI-21 | SPEC 8, 11.3 |
| UI-FR-16 | UI-16 | SPEC 8, 6 |
| UI-FR-17 | UI-17 | SPEC 8, 10 |
| UI-FR-18 | UI-18, UI-22 (HLTH-FR-32) | SPEC 8, 7 |
| UI-FR-21 | UI-19, UI-23, UI-25 | SPEC 8, 4 |
| NFR-4 (parent) | UI-4 | SPEC 9 |
| NFR-11 (parent) | UI-6 | SPEC 8 |

Criteria satisfied: UI-1 to UI-6, UI-10 to UI-25. Implemented here and owned by the security component: SEC-29 (`next` follows only `/ui/` paths) and SEC-32 (`/ui/static/*` needs a session).

Related criteria owned elsewhere, on which the UI relies: SEC-11 (bearer token on `/api`), SEC-12 (foreign Host or Origin refused), PLAT-10 and PLAT-71 (no non-loopback bind), PLAT-70 (app composition), HLTH-32 (no token in the notifier argument list), HLTH-13 (credential service in a locked Keychain), CACHE-33 (review lifecycle). Owner check: OC-05, the walkthrough of every UI page, at M3.

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

No file in `docs/contracts/` is warranted: the UI is a local browser surface, not a public or cross-team contract. The routes, codes and interfaces below are the contract. Approval is by the owner at Gate 3.

### 2.1 Mount and routes

The UI is mounted at `/ui` in the daemon's Starlette app. `build_app(settings)` mounts `/mcp`, `/ui`, `/healthz`, `/readyz` and `/api`; one deny-by-default gate in front of every mount runs the bearer and Host/Origin checks and calls the UI guard for session and CSRF (LLD-security v2 E3; owner decision, 2026-10-22). `server.port` (default `7319`) serves MCP at `/mcp` and the UI at `/ui`.

Pages (GET; UI session required except `/ui/login`):

| Route | Page | Requirement |
| --- | --- | --- |
| `/ui/` | Source board (home) | UI-FR-10 |
| `/ui/sources/<id>` | Source detail: latency chart, recent errors by correlation id, recent calls | UI-FR-10 |
| `/ui/credentials` | Credentials | UI-FR-11 |
| `/ui/quota` | Quota | UI-FR-12 |
| `/ui/jobs` | Jobs | UI-FR-13 |
| `/ui/cache` | Cache | UI-FR-14 |
| `/ui/review/<batch_id>` | Cache review; `<batch_id>` is a ULID (26 characters of Crockford base32, `[0-9A-HJKMNP-TV-Z]{26}`); anything else is 404 | UI-FR-15 |
| `/ui/archive` | Archive | UI-FR-16 |
| `/ui/maintenance` | Maintenance | UI-FR-17 |
| `/ui/events` | Events and logs | UI-FR-18 |
| `/ui/settings` | Settings | UI-FR-21 |
| `/ui/login` | Consumes the one-time token (the only route without a session) | UI-FR-2 |
| `/ui/static/*` | `htmx.min.js`, `app.css`; needs a session (SEC-32) | UI-FR-1, UI-FR-2 |

Fragment routes (GET, session required, no layout, safe and read-only): `/ui/<page path>/fragment/<name>`, for example `/ui/fragment/board`, `/ui/jobs/fragment/list`, `/ui/fragment/banner`. They exist so that `hx-get` can reload one part of a page (UI-FR-20). The fragment names are in 5.4.

Action routes (POST, session and `X-CSRF-Token` required): `/ui/<page path>/action/<name>`, so "POST routes under the same paths, at `/action/<name>`" (SPEC v2 11) reads as the page path followed by `/action/<name>`. The table:

| Route | Inputs (form fields) | Confirmed | Calls |
| --- | --- | --- | --- |
| `/ui/action/probe` | `source_id` (omitted: all) | no | `HealthService` probe scheduling |
| `/ui/sources/<id>/action/enable`, `/disable` | none | no | settings writer, key `sources.<id>.enabled` |
| `/ui/credentials/action/recheck` | `name` | no | `CredentialService` re-validation |
| `/ui/credentials/action/reload` | none | no | `app.state.reload_credentials` |
| `/ui/credentials/action/set_rotate_by`, `/clear_rotate_by` | `name`, `rotate_by` (date) | no | settings writer, key `credentials.<NAME>.rotate_by` |
| `/ui/credentials/action/acknowledge` | `notification_id` | no | `NotifyService.acknowledge` |
| `/ui/quota/action/set_budget_cap` | `source_id`, `cap` | yes | settings writer, key `sources.<id>.budget_cap` |
| `/ui/jobs/action/cancel` | `job_id` | yes | `JobService.cancel` |
| `/ui/jobs/action/retry` | `job_id` | no | `JobService.submit` (5.4) |
| `/ui/cache/action/pin`, `/unpin` | `doc_id` | no | `LifecycleService.set_pin` |
| `/ui/cache/action/archive` | `doc_id` | no | `ArchiveService.archive` through its job |
| `/ui/cache/action/discard` | `doc_id` | yes | `LifecycleService.discard` |
| `/ui/review/<batch_id>/action/preview` | `choice[<doc_id>]`, `bulk` | no | builds the summary (5.4) |
| `/ui/review/<batch_id>/action/decide` | `choice[<doc_id>]` | yes | `LifecycleService.decide` |
| `/ui/archive/action/set_path` | `path` | yes | settings writer, key `archive.confirmed_path` |
| `/ui/archive/action/reconcile` | none | no | `ArchiveService.reconcile` |
| `/ui/archive/action/reindex` | none | yes | `JobService.submit("archive_reindex", ...)` |
| `/ui/archive/action/undo` | `doc_id` | no | `LifecycleService.undo_discard` |
| `/ui/maintenance/action/verify` | none | yes | `MaintenanceService.daily` |
| `/ui/maintenance/action/rebuild_fts`, `/reembed_missing`, `/clean_orphans`, `/backup_state` | none | yes | `JobService.submit(<kind>, {})` |
| `/ui/events/action/acknowledge` | `notification_id` | no | `NotifyService.acknowledge` |
| `/ui/events/action/snooze` | `notification_id`, `days` | no | `NotifyService.snooze` |
| `/ui/settings/action/set` | `key`, `value` (keys in 3.3) | yes | settings writer |
| `/ui/settings/action/test_notification` | none | no | `NotifyService.emit` |

No action rotates the daemon token and none starts a migration command (LLD-security v2 E36, E43).

### 2.2 Login and session

- `research-mcp ui [--path P]` calls `POST /api/ui-token` with the daemon bearer token and opens `http://127.0.0.1:<port>/ui/login?t=<token>&next=P`. `P` includes the `/ui` prefix and defaults to `/ui/`. A notification's `ui_path` is the same form, for example `/ui/review/<batch_id>` (LLD-health v2 decision 15). The platform owns the command and the mint; the CLI rejects a `P` that does not start with `/ui/` before it opens the browser.
- `GET /ui/login` consumes the token, creates the session, sets the cookie `rmcp_session` (HttpOnly, SameSite=Strict, `Path=/`, `Max-Age` 12 hours, no `Secure` flag because the origin is plain loopback HTTP [inferred]) and answers 303 to `safe_next(next)`.
- `safe_next` (SEC-29; owner decision, 2026-10-22) returns the value only if it starts with `/ui/`, has a single leading slash (the second character is not `/`), contains no backslash, no control character and no `%2f` or `%5c` after one round of percent-decoding at the start, and is at most 512 characters; otherwise it returns `/ui/`. A scheme or host cannot occur because the value must begin with `/ui/`.
- Uvicorn access logging is off (LLD-security v2 E10), so tokens never reach a log.
- A daemon restart ends every session and pending token; the owner runs `research-mcp ui` again (3.2).

### 2.3 Request checks and responses

The order for a UI request follows LLD-security v2 5.2. The gate refuses first on Host and Origin; the UI guard then checks the session and, for a POST, the CSRF token. Responses carry a code and no exception text (LLD-security v2 6).

| Situation | Status | Body | Criterion |
| --- | --- | --- | --- |
| Host other than `127.0.0.1:<port>` or `localhost:<port>`, or a present Origin that does not match | 403 | plain page, code `bad_host` | UI-20, SEC-12 |
| `/ui` page, fragment or `/ui/static/*` with no valid session | 401 | plain page: "Run `research-mcp ui` to sign in", code `no_session`; no redirect, because the only way in is a token | SEC-32, UI-2 |
| `/ui/login` with a wrong, expired or reused token | 401, no cookie set | plain page, code `bad_token` | UI-2 |
| POST with a valid session and a missing or wrong `X-CSRF-Token` | 403, no state change | plain page, code `csrf_failed` | UI-3 |
| POST to a confirmed action without `confirmed=1` | 400, no state change | code `confirmation_required` | UI-3, UI-17 |
| Unknown route or batch, or a doc not in the batch | 404 | code `not_found` | |
| Invalid field | 400 | code `invalid_argument` | |
| Service refusal (for example a closed batch) | 409 | the service's `ErrorCode` string (LLD-platform v2 2.1) | UI-15 |

The status codes for UI refusals are not stated in SPEC-v5; they follow LLD-security v2 6 (401 for a bad token, 403 for CSRF and a foreign Host) and are otherwise this LLD's choice [inferred].

### 2.4 Partial refresh and confirmation

- **Refresh.** Fragments reload with `hx-get` and `hx-trigger="every 10s"`, and nothing else: no server-sent events, no `hx-ext="sse"`, no other interval (UI-FR-20; owner decision, 2026-10-22). Forms are never refreshed, so the review page and open edit fields keep what the owner typed (5.4).
- **Confirmation.** A confirmed action carries `hx-confirm` with a summary text rendered by the server into the attribute and `hx-vals='{"confirmed": "1"}'`; the server refuses the POST without `confirmed=1` (2.3). The review page uses a two-step form because its summary depends on the choices made (5.4).
- **CSRF header.** Every page has `<meta name="csrf-token" content="...">` and `hx-headers` on `<body>` that sends it as `X-CSRF-Token` on every htmx request (LLD-security v2 5.3).

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

### 3.1 No table, no migration

The UI owns no table and no migration. No SQL appears outside `platform/stores.py` and the `services/*` repositories (SPEC-v2 3.5), so `ui/` calls services only. The pages read the same services the MCP tools use (SPEC 8). The mapping from page to tables below is [inferred] from column names:

| Page | Tables read through services |
| --- | --- |
| Source board, source detail | `source_health`, `call_rollups`, `calls` |
| Credentials | `credentials` |
| Quota | `source_health` (`quota_remaining`, `quota_reset`, `budget_reset_at`, `calls_today`) |
| Jobs | `jobs` |
| Cache | `documents`, `files`, `works`, `disk_samples` |
| Cache review | `review_batches`, `documents` |
| Archive | `documents` (`archive_path`, `archive_upload_state`, `archive_fallback`, `discarded_at`, `trash_until`) |
| Maintenance | `maintenance_runs`, `disk_samples` |
| Events and logs | `notifications`; the log files (5.4) |

### 3.2 In memory only

The one-time login tokens (a SHA-256 digest and an expiry) and the sessions (a digest of the session id, the CSRF token, an expiry) live in the daemon's memory and are never persisted (LLD-security v2 3). A restart ends them. SPEC-v5 defines no storage for them, so adding one would be a persisted-secret change for the owner. The session table is pruned of expired entries on every lookup and at most 1,000 live sessions are kept (the oldest is dropped) [assumption: a bound for a one-user daemon].

### 3.3 Writes the UI makes

Lifecycle writes (SPEC 6 lifecycle rows, made through `LifecycleService`, never directly): owner archive, owner discard (confirmed) and undo of a discard before `trash_until` (UI Archive page). `decided_by` is `owner` and `decided_channel` is `ui` for every UI call; every transition writes an outbox row. The UI cannot change stored state except through the service that owns it (SPEC-v2 3.5).

Settings the UI changes go through the same validated writer as `config set`: the whole resulting settings model is validated before `config.toml` is written, so an invalid value is never saved (LLD-platform v2 2.4; PLAT-8). The keys the UI may write (any other key gets `invalid_argument`):

| Key | Where in the UI | Confirmed |
| --- | --- | --- |
| `archive.confirmed_path` | Archive, "change the archive path" | yes |
| `sources.<id>.budget_cap` | Quota | yes |
| `sources.<id>.enabled` | Source board and detail | no |
| `credentials.<NAME>.rotate_by` | Credentials, set or clear | no |
| `notify.quiet_hours`, `notify.macos`, `notify.webhook_url` | Settings | yes |
| `disk.cache_warn_bytes`, `disk.free_warn_bytes`, `disk.free_crit_bytes` | Settings ("thresholds"; the keys are [inferred] as the only numeric thresholds in the settings model) | yes |

Never writable from the UI: `server.*`, `server.token`, `contact.email`, `site_sets.*` (read-only display, UI-FR-21), any `keychain:` reference, and any credential value. A value typed into the browser is never accepted for a credential (UI-INV-4; UI-11).

A setting saved on the Settings page writes `config.toml` and the page shows "applies after the daemon restarts"; there is no live reload and no new platform function (owner decision, 2026-10-23). `SIGHUP` re-reads secrets only (LLD-platform v2 5.10).

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

Reviewed by `security-reviewer` at Gate 3 (2026-10-23). The controls are decided in [LLD-security v2](LLD-security-v2.md); this table says where `ui/` implements each one. It adds no policy.

| Point | Enforcement | Where | Criterion |
| --- | --- | --- | --- |
| Bind | Loopback only; validation rejects any other `server.host` | platform (`settings.py`, `daemon.py`); E1 | UI-1; PLAT-10, PLAT-71 |
| Gate | Host and Origin on every path, bearer on `/mcp` and `/api/ui-token`, bearer or session on `/api/status`, deny by default; only `/healthz`, `/readyz` and `/ui/login` (one-time token) answer without a credential; calls `ui_guard` for `/ui/*` and `/api/status` | `app.py` (E3) | UI-20; SEC-11, SEC-12 |
| Token mint | `POST /api/ui-token` with the bearer token; the session cookie is not accepted | `platform/auth.py` (E6) | UI-2 |
| Token use | `GET /ui/login` consumes the digest once, deleting the entry whether or not the rest succeeds; expired or unknown gets 401 | `ui/auth.py` `login` (E6) | UI-2 |
| `next` | Followed only if `safe_next` accepts it (2.2) | `ui/auth.py` | SEC-29 |
| Session | Cookie `rmcp_session`, 32-byte id, server holds its SHA-256 digest; HttpOnly, SameSite=Strict, `Path=/`, 12 hours | `ui/auth.py` `SessionStore` (E7) | UI-2 |
| Static files | `/ui/static/*` behind the same session check; `login` serves no asset | `ui_guard` | SEC-32 |
| CSRF | Per-session token compared with `hmac.compare_digest`; missing header, mismatch or no session gives 403 | `ui/csrf.py` (E8) | UI-3 |
| Confirmation | Server refuses a confirmed action without `confirmed=1` | `ui/routes.py` | UI-3, UI-17 |
| No secret on a page | Pages read services that return fingerprints and dates; the rendered HTML and the Events log lines pass `Redactor.redact` before they are sent (E40); `Secret.reveal` is never called in `ui/` | `ui/routes.py` `render` | UI-4 |
| No value typed | The Credentials page shows the value-free `security add-generic-password -U -s research-mcp/<NAME> -a "$USER" -w` command and has no input for a value | templates | UI-11 |
| Owner-only operations | The fix jobs (`rebuild_fts`, `reembed_missing`, `clean_orphans`, `backup_state`) start only from the UI or the CLI; no MCP tool starts them | `ui/routes.py` | UI-17 |
| Response headers (proposal) | Pages answer with `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; form-action 'self'`, `Referrer-Policy: no-referrer` and `Cache-Control: no-store`; htmx is configured with `includeIndicatorStyles=false` and `allowEval=false` so no inline style or script is needed | `ui/routes.py` middleware | UI-1, UI-2 [proposal for `security-reviewer`] |

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

### 5.1 Files

```
src/research_mcp/
  app.py                      # build_app(settings): the gate (E3) calls ui.auth.ui_guard for /ui/* and /api/status
  platform/auth.py            # LoginTokens (one-time tokens), daemon token (platform LLD)
  ui/
    __init__.py               # exists
    routes.py                 # build_ui(services, sessions, tokens, settings) -> Starlette; handlers; render()
    auth.py                   # SessionStore, UiSession, ui_guard, login, safe_next
    csrf.py                   # new_csrf_token, csrf_ok
    templates/                # base.html, one template per page, source_detail.html, fragments/*.html
    static/htmx.min.js  static/app.css
tests/ui/
```

The SPEC layout lists `routes.py`, `auth.py` and `csrf.py`; this LLD adds no module. Handlers for the eleven pages stay in `routes.py`, grouped by page; splitting it into a package would change the SPEC layout [inferred: no reason to].

Templates: `base.html` (navigation, the banner slot, the meta tag, `hx-headers`), `board.html`, `source_detail.html`, `credentials.html`, `quota.html`, `jobs.html`, `cache.html`, `review.html`, `archive.html`, `maintenance.html`, `events.html`, `settings.html`, and `fragments/*.html` for each polled part. The source detail page has its own template: PRD-ui section 2.2 lists ten pages, and `/ui/sources/<id>` is a sub-page of the board (UI-FR-10). The latency chart is inline SVG built by the server; no JavaScript library and no external asset (UI-1) [inferred]. Package data includes `research_mcp/ui/templates/*.html`, `research_mcp/ui/templates/fragments/*.html` and `research_mcp/ui/static/*`.

Interfaces (Python; `Clock` is the platform's injected clock):

```python
# ui/auth.py
SESSION_COOKIE = "rmcp_session"
SESSION_TTL = timedelta(hours=12)

@dataclass(frozen=True)
class UiSession:
    csrf_token: str
    expires_at: datetime

class SessionStore:
    def __init__(self, clock: Clock) -> None: ...
    def create(self) -> tuple[str, UiSession]: ...          # cookie value (32 random bytes, URL-safe), session; stores sha256(cookie value)
    def lookup(self, cookie_value: str | None) -> UiSession | None: ...   # digest lookup; prunes expired entries
    def revoke_all(self) -> None: ...                       # tests and daemon stop

def safe_next(value: str | None) -> str: ...                # SEC-29
async def login(request: Request) -> Response: ...          # GET /ui/login
def ui_guard(request: Request, sessions: SessionStore) -> Response | None:
    """None to pass; else the 401 or 403 response (2.3). Session first, then CSRF for POST. Sets request.state.ui_session."""

# ui/csrf.py
CSRF_HEADER = "X-CSRF-Token"
def new_csrf_token() -> str: ...                            # secrets.token_urlsafe(32)
def csrf_ok(session: UiSession, header_value: str | None) -> bool: ...   # hmac.compare_digest on encoded bytes

# platform/auth.py (names proposed for LLD-platform to confirm)
class LoginTokens:
    def mint(self) -> str: ...                              # 32 random bytes, URL-safe; stores sha256 digest with a 5 minute expiry
    def consume(self, token: str) -> bool: ...              # deletes the entry whether or not it is valid; True only if unexpired and present

# ui/routes.py
@dataclass(frozen=True)
class UiServices:
    health: HealthService; credentials: CredentialService; notify: NotifyService
    jobs: JobService; secrets: SecretCache; reload_credentials: Callable[[], Awaitable[list[str]]]
    lifecycle: LifecycleService; archive: ArchiveService; cache: CacheService
    maintenance: MaintenanceService; backup: BackupService; disk: DiskService
    settings_writer: SettingsWriter; redactor: Redactor; clock: Clock

def build_ui(services: UiServices, sessions: SessionStore, tokens: LoginTokens, settings: Settings) -> Starlette: ...
def render(request: Request, template: str, **context: object) -> HTMLResponse: ...   # adds csrf token, banners, headers; redacts the HTML (E40)
```

`SettingsWriter` stands for the validated writer behind `config set` (LLD-platform v2 2.4); its name is the platform's to give. The `ui_guard` is called by the gate, not by each handler, so a new route cannot forget the check (deny by default).

### 5.2 Services the pages use

The UI calls services and never reaches the stores. Members named in the approved LLDs:

| Service | Members | Used by |
| --- | --- | --- |
| `JobService` (platform) | `submit(kind, params) -> job_id`, `status(job_id)`, `cancel(job_id)`, `list(state)` | Jobs; Maintenance; Archive |
| `SecretCache` and `reload_credentials` (platform) | `state(name)`, `reload() -> list[str]` (names only) | Credentials "reload", `keychain_locked` state |
| `NotifyService` (health) | `banners()`, `acknowledge(notification_id)`, `snooze(notification_id, days)`, `emit(event)` | Banner, Events, Credentials, Settings test |
| `CredentialService` (health) | `evaluate(name)`, `fix_text(name)`, `sync()` | Credentials |
| `HealthService` (health) | probe scheduling, `active_keys()` | Source board |
| `LifecycleService` (cache) | `decide`, `set_pin`, `discard`, `undo_discard`, `summaries` | Cache, Review, Archive |
| `ArchiveService` (cache) | `archive`, `reconcile`, `check_target`, `reindex` | Archive, Cache |
| `CacheService` (cache) | `search` (the do-I-have-this box) | Cache |
| `MaintenanceService`, `BackupService`, `DiskService` | `daily`, `backup_state`, `sample` | Maintenance, Cache |

Read views the pages need and the owning LLDs have not named (the UI asks; it does not define them): the source board rows and the source detail (health), the quota rows with GitHub per-resource remaining (health), the cache listing with totals and growth per day (cache), the open review batch with its items (cache; `cache_review_list` logic), the archive catalog, discard records and trash (cache), and the last result of each maintenance check (cache). Each returns plain view models with fingerprints and dates, never a secret; `ui/` renders them.

Job kinds the UI starts: `rebuild_fts`, `reembed_missing`, `clean_orphans`, `backup_state` and `archive_reindex`.

### 5.3 Pages

| Page | Route | Shows | Actions |
| --- | --- | --- | --- |
| Source board | `/ui/` | One row per source grouped by group, a state chip and counts at the top ("31 ok, 2 degraded, 1 expiring, 4 unconfigured"); per row: last probe, calls in 24 h, error rate, p95 latency, quota remaining and reset, last classified error, fix hint | Probe now (one or all); open detail; enable or disable |
| Credentials | `/ui/credentials` | Name, sources that use it, required or optional, fingerprint, Keychain modified date, expiry with countdown, `rotate_by`, last validated, state, provider key page link. If any state is `keychain_locked`, one `keychain_locked` notice replaces the per-credential `missing` states (UI-23) | Re-check; reload from Keychain; set or clear `rotate_by`; acknowledge; copy the value-free `security` command |
| Quota | `/ui/quota` | Allowance, used, remaining, reset, projected exhaustion; GitHub remaining per resource | Edit per-source budget caps (confirmed) |
| Jobs | `/ui/jobs` | Running, queued and recent jobs with progress, timing and errors | Cancel (confirmed); retry; view log for the job |
| Cache | `/ui/cache` | Cached, pinned and archived items; totals by type and state, growth per day, free disk; filter and search boxes | Pin or unpin; archive now; discard (confirmed); open the original URL |
| Cache review | `/ui/review/<batch_id>` | The open batch: per item title, citation, size, age, times asked, integrity changes, the four choices (archive, discard, keep, pin); the note that unanswered items are kept and asked again in 7 days | Per-item or bulk decisions with a summary confirmation |
| Archive | `/ui/archive` | Target health and upload state; catalog; discarded items; trash with undo | Change the archive path (confirmed); reconcile; rebuild job (confirmed); undo a discard within 7 days; copy citation or BibTeX |
| Maintenance | `/ui/maintenance` | Last run and result of each check; disk panel | Verify now; rebuild full-text index; re-embed missing; clean orphans; back up state now; all confirmed |
| Events and logs | `/ui/events` | Notification history with acknowledged state; recent warning and error log lines (redacted), searchable by correlation id, source or tool | Acknowledge; snooze for N days |
| Settings | `/ui/settings` | Effective configuration (paths, port, thresholds, quiet hours, channels, archive target), credential references that resolve (names only; one `keychain_locked` state when the Keychain is locked), versions, launchd job state, and each named site set with its domains, read-only | Edit thresholds, quiet hours and channels (confirmed); send a test notification |

The banner slot in `base.html` shows `NotifyService.banners()`: active, unacknowledged, unsnoozed notifications, including those delivered by the built-in fallback, until resolved or acknowledged (UI-22; LLD-health v2 decision 6). The full field lists are in PRD-ui v4 2.4.

### 5.4 Algorithms and procedures

**Login** (2.2): the CLI mints a token; the browser requests `/ui/login?t=...&next=P`; `login` calls `LoginTokens.consume(t)`; on failure it returns 401 and sets nothing; on success it calls `SessionStore.create()`, sets the cookie and answers 303 to `safe_next(P)`. The page the owner lands on carries no token in its URL.

**Request pipeline** for `/ui/*`: gate (Host, Origin) then `ui_guard` (session lookup, then CSRF for a POST) then the handler. A handler reads `request.state.ui_session`. GET handlers change nothing.

**Polled fragments (UI-FR-20).** Polled: the banner (`/ui/fragment/banner`), the source board rows and counts (`/ui/fragment/board`), quota rows (`/ui/quota/fragment/rows`), the job list (`/ui/jobs/fragment/list`), the cache totals and list (`/ui/cache/fragment/list`), the archive upload state (`/ui/archive/fragment/state`), maintenance results (`/ui/maintenance/fragment/results`) and the events list (`/ui/events/fragment/list`). Each container has `hx-get`, `hx-trigger="every 10s"` and `hx-swap="outerHTML"`. Not polled: the review form, the credentials edit controls and the settings form. If the session has expired, a poll gets 401 and htmx swaps nothing.

**Confirmation.** `confirmed_summary(action, params) -> str` builds the text the server writes into `hx-confirm`, for example "Rebuild the full-text index. This runs a job and may take a few minutes." Every action marked confirmed in 2.1 goes through `require_confirmed(form)`, which returns `confirmation_required` (400) when `confirmed` is not `1`.

**Review decision** (UI-FR-15, UI-21). The page lists every item of the open batch with a choice per item and a bulk selector. `action/preview` returns a fragment: how many items will be archived (and to which target path), how many go to the trash for 7 days, how many are kept and pinned, and how many are unanswered (kept and asked again in 7 days). Its Confirm button posts to `action/decide` with `confirmed=1`. `decide` builds the `Decision` list from the answered items and calls `LifecycleService.decide(batch_id, decisions, decided_by="owner", channel="ui")`, the same function `cache_review_decide` uses, so the same checks apply: an unknown batch is `not_found`, and a closed batch, a foreign or repeated `doc_id` or an unknown choice is `invalid_argument` and nothing is applied (LLD-cache v2 5; CACHE-34). Unanswered items are not sent: they stay listed with their times asked until the batch closes, then become `kept` and are asked again after `cache.reask_days` (UI-21; CACHE-33).

**Job retry** (UI-FR-13, UI-24; owner decision, 2026-10-22). `retry(job_id)`: read `JobService.status(job_id)`; allowed only for a job in a final failed or cancelled state; call `JobService.list` for a queued or running job of the same kind and parameters and return its id if one exists (a double click does not start two jobs); otherwise call `JobService.submit(kind, params)` with the stored kind and parameters and show the new job id. The UI never starts a job kind that the original did not have.

**Job log.** "View log for the job" shows the warning and error log lines whose `correlation_id` equals the job's correlation id (the job row carries it [assumption: LLD-platform v2 5.5 jobs]).

**Events log search** (UI-FR-18). `read_log_lines(query)` reads `log_dir/research-mcp.jsonl` and its rotated files (newest first, at most 5 files), scans the last 5,000 lines, keeps levels `WARNING` and above, and when a query is given keeps lines whose JSON fields `correlation_id`, `source` or `tool` equal it (a prefix match on `correlation_id`). It shows at most 200 lines, each passed through `Redactor.redact`. The directory is the configured log directory; no path comes from the request.

**Credentials re-check and reload.** Re-check calls `CredentialService` validation for one name; reload calls `app.state.reload_credentials`, which returns names only and registers new values with the `Redactor` (LLD-platform v2 5.10; E38). Fingerprints are shown from the service. The page also shows the `security add-generic-password -U -s research-mcp/<NAME> -a "$USER" -w` command with a copy button; it has no field for a value.

**Settings write.** `action/set` checks that `key` is in the table of 3.3, calls the validated writer, and on `invalid_argument` shows the validator's fixed message (no input echoed); on success it shows "applies after the daemon restarts" (owner decision, 2026-10-23). Site sets are rendered from `settings.site_sets` as name and domain list, with no form control.

**Redaction of pages (E40).** `render` produces the HTML, then runs `Redactor.redact` over it before the response. This covers the Events lines and any text from a service. The pattern `token=` in `Redactor` must not damage the markup: no attribute or URL generated by the templates contains the patterns of PLAT-FR-13 (checked by the UI-4 test against a full render).

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

- Refusals and their statuses are in 2.3. Errors carry codes, never exception text (LLD-security v2 6, E23). A service `ToolError` or `HttpError` becomes the 409 or 400 of 2.3 with its `ErrorCode` string; any other exception becomes 500 with code `internal`, logged through the redactor.
- A one-time token is consumed once, even when the rest of the login fails, and expires after 5 minutes (UI-2).
- A POST without a valid CSRF token, or without `confirmed=1` where required, changes nothing (UI-3).
- Idempotency: login tokens and credential reload are safe to repeat; retry returns the existing active job instead of submitting twice (5.4); pin, unpin, undo and acknowledge are repeatable and answer with the current state; a repeated `decide` on a decided item is refused by the lifecycle service and nothing is applied twice (CACHE-34).
- The UI has no retry of its own for failed service calls: the owner repeats the action. htmx polling fetches again every 10 seconds, which is a refresh, not a retry of a write.
- If a service is unavailable (for example the archive target is missing), the page shows its state from the service (Archive target health) and the action returns the service's code; the page itself still renders.
- Lifecycle actions follow the transition table of SPEC 6; the archive copy is verified before the cached file is removed (LLD-cache v2).

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

| Flag | Default | Safe to switch off? |
| --- | --- | --- |
| `ui.live_refresh` (proposed; register in LLD-platform v2 7.2 and `settings.py`) | `true` | Yes. Off: pages render without the `hx-trigger="every 10s"` attributes; the owner reloads a page by hand. No data is lost, no tool changes, hooks and the daemon are unaffected. It is read at render time. UI-FR-20 is P2, which is why it is optional. |

No other UI behavior is optional: the UI itself, login, CSRF and confirmation are required by P1 criteria and carry no flag. No feature-flag PRD exists; this follows the platform LLD's table (7.2).

Settings the UI depends on (LLD-platform v2 7.1):

| Key | Default | Notes |
| --- | --- | --- |
| `server.host` | `127.0.0.1` | Validation rejects any non-loopback value |
| `server.port` | `7319` | MCP at `/mcp`, UI at `/ui`; the Host check uses it |
| `server.token` | `keychain:research-mcp/DAEMON_TOKEN` | Bearer for the shim and API; never shown or edited in the UI |
| `cache.batch_open_hours`, `cache.reask_days`, `cache.trash_days` | `24`, `7`, `7` | Shown on the Review and Archive pages |
| `archive.target`, `archive.confirmed_path` | `auto`, none | The UI sets `confirmed_path` (confirmed); archiving to `auto` waits for it |
| `notify.quiet_hours`, `notify.macos`, `notify.webhook_url` | `"21:00-08:00"`, `true`, none | Edited on the Settings page; the webhook allows `https`, or `http` on loopback only (LLD-security v2 E42) |
| `disk.cache_warn_bytes`, `disk.free_warn_bytes`, `disk.free_crit_bytes` | `5368709120`, `16106127360`, `5368709120` | Thresholds on the Settings page |
| `sources.<id>.enabled`, `sources.<id>.budget_cap` | spec default; none (`100` for `web` sources) | Source board and Quota |
| `credentials.<NAME>.rotate_by` | none | Credentials |
| `site_sets.<name>` | `v1_docs` | Displayed read-only |
| `ui.live_refresh` | `true` | Proposed flag above |

Fixed values, not settings: one-time token 32 random bytes valid 5 minutes; session cookie 12 hours; fragment refresh every 10 seconds.

## 8. Observability

> **Owner:** A · **Persona:** `sre`

Reviewed by `sre` at Gate 3 (2026-10-23) against SPEC-v5 12, PRD-v8 NFR-4 and NFR-12, and consistent with LLD-platform v2 8 and LLD-security v2 8; not approved. Nothing here sets policy.

- Uvicorn access logging is off, so tokens never reach a log; `configure_logging` sets `uvicorn.access` to `WARNING` (LLD-security v2 E10, E22). `RedactingFilter` covers every handler, so UI records are redacted.
- The UI logs refusals and actions through the normal logger, with no token, cookie, CSRF value or form value: `ui.login_refused` (code only), `ui.csrf_refused`, `ui.host_refused`, `ui.action` (route name and result code); the `ui.` prefix keeps them apart from the `migration.` events (NFR-4; LLD-security v2 8). Each record carries a `correlation_id` from the contextvar set per request.
- The Events page reads the JSON log (5.4). The log is `research-mcp.jsonl`, 10 MB, 5 files in all (PLAT-FR-40; LLD-platform v2 8).
- No UI metric or alert is defined and no NFR threshold applies to the UI (PRD-ui v4 2.5; NFR-12 sets no response target). A dead daemon takes the UI down with it; the watchdog reports that within 15 minutes through the macOS and webhook channels (NFR-12; OUT-4; HLTH-FR-41; LLD-platform v2 2.5).

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

Reviewed by `test-architect` at Gate 3 (2026-10-23). Test plan v4 adopts these names for UI-1 to UI-25, SEC-29 and SEC-32. All files live in `tests/ui/` (the `ui` paths of `sdd.config.json`). A test that verifies a criterion names its ID in the title or a comment.

| Criterion | Planned tests | Level | Status |
| --- | --- | --- | --- |
| UI-1 | `tests/ui/test_serving.py::test_ui_is_loopback_only_and_pages_load_no_external_assets` (every page: no `http(s)://` source in `src`, `href`, CSS `url()`; CSP header present) | integration | planned |
| UI-2 | `tests/ui/test_login.py::test_one_time_token_expires_is_single_use_and_sets_strict_httponly_cookie` (also: token never in a captured log; access log off); with `test_next_accepts_only_ui_paths` for SEC-29 | integration | planned |
| UI-3 | `tests/ui/test_csrf.py::test_post_without_valid_csrf_is_refused_and_maintenance_needs_confirmation` (missing, wrong, other-session token; missing `confirmed=1`) | integration | planned |
| UI-4 | `tests/ui/test_no_secrets.py::test_no_page_contains_a_registered_secret` (fake secrets, every page and fragment, the Events lines) | integration | planned |
| UI-5 | `tests/ui/test_refresh.py::test_fragments_poll_every_10s_and_nothing_else` (each fragment route returns a partial; no `sse`; no other interval; `ui.live_refresh=false` removes the triggers) | integration | planned |
| UI-6 | `tests/ui/test_strings.py::test_templates_and_strings_have_no_em_or_en_dashes` | unit | planned |
| UI-10 | `tests/ui/test_board.py::test_board_counts_groups_chips_and_probe_and_enable_actions` | integration | planned |
| UI-11 | `tests/ui/test_credentials.py::test_credentials_show_metadata_and_value_free_command_and_no_value_field` | integration | planned |
| UI-12 | `tests/ui/test_quota.py::test_quota_shows_allowance_used_remaining_reset_and_projection` | integration | planned |
| UI-13 | `tests/ui/test_jobs.py::test_jobs_list_and_cancel_needs_confirmation` | integration | planned |
| UI-14 | `tests/ui/test_cache.py::test_cache_lists_items_with_totals_and_search_finds_cached` | integration | planned |
| UI-15 | `tests/ui/test_review.py::test_per_item_and_bulk_decisions_with_summary_confirmation` | integration | planned |
| UI-16 | `tests/ui/test_archive.py::test_archive_shows_target_catalog_discards_and_undo` | integration | planned |
| UI-17 | `tests/ui/test_maintenance.py::test_each_action_requires_confirmation_and_starts_its_job` | integration | planned |
| UI-18 | `tests/ui/test_events.py::test_events_list_notifications_and_redacted_logs_searchable_by_correlation_id` | integration | planned |
| UI-19 | `tests/ui/test_settings.py::test_settings_show_effective_config_names_only_and_test_notification_works` | integration | planned |
| UI-20 | `tests/ui/test_host_origin.py::test_foreign_host_or_origin_is_refused` | integration | planned |
| UI-21 | `tests/ui/test_review.py::test_unanswered_item_stays_listed_with_times_asked` | integration | planned |
| UI-22 | `tests/ui/test_banner.py::test_fallback_notification_shows_in_banner_until_resolved` | integration | planned |
| UI-23 | `tests/ui/test_keychain_locked.py::test_credentials_and_settings_show_one_keychain_locked_state` | integration | planned |
| UI-24 | `tests/ui/test_jobs.py::test_retry_resubmits_same_kind_and_parameters` | integration | planned |
| UI-25 | `tests/ui/test_settings.py::test_lists_site_sets_read_only` | integration | planned |
| SEC-29 (security) | `tests/ui/test_login.py::test_next_accepts_only_ui_paths` (`/ui/x`, `//evil`, `/\evil`, `https://evil`, `/ui/../x`, `%2f`) | integration | planned |
| SEC-32 (security) | `tests/ui/test_static.py::test_static_needs_a_session` | integration | planned |

Also relevant: OC-05, the owner walkthrough of every UI page (UI-FR-10, UI-FR-21), at M3. Tests use a fake clock for token and session expiry, `FakeProvider` for the Keychain, and fake services.

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| Server-rendered Starlette and Jinja2 in the daemon, one vendored htmx file, no build ([ADR 0010](../adr/0010-localhost-ui-stack.md)) | No second process, API or build chain | Streamlit, Gradio, NiceGUI; a React single-page app (rejected in the ADR) |
| The gate calls `ui_guard` for every `/ui/*` request (owner decision, 2026-10-22; E3) | Deny by default: a new route cannot skip the session check | Each handler calls the check (a route could forget it) |
| In-memory sessions and one-time tokens, digests only; a restart ends sessions (LLD-security v2 3) | No persisted secret; a one-user daemon | A signed cookie (the key would need storage); a table in `state.db` (a persisted secret) |
| Per-session CSRF token in a meta tag and `hx-headers` (LLD-security v2 5.3) | Works with htmx fragments; bound to the session | A token per request (breaks fragments); double-submit cookie |
| `confirmed=1` enforced on the server, plus `hx-confirm` on the client | `hx-confirm` alone is a browser dialog and cannot be tested server-side (UI-3) | Client-side confirm only |
| The review page uses a preview step | The summary depends on the choices made, which the server learns only on submit | `hx-confirm` with a script that builds the text (needs inline JavaScript) |
| 401 page with no redirect for a missing session | There is no login form; the only way in is a token from the CLI | Redirect to `/ui/login` (it needs a token anyway) |
| Polling only for fragments, never forms | A refresh must not discard what the owner is typing | Poll whole pages |
| Polling `hx-get` every 10 s only (UI-FR-20; owner decision, 2026-10-22) | SPEC 8 | Server-sent events (removed from the PRD) |
| Job retry through `JobService.submit` (owner decision, 2026-10-22) | No new service member; the job table stays the record | A `JobService.retry` method (changes a platform contract) |
| Settings go through the `config set` writer | One validation path (PLAT-8, PLAT-10, PLAT-11) | A second store for UI settings (two sources of truth) |
| No rotation of the daemon token in the UI (owner decision, 2026-10-22; PLAT-FR-59) | Rotation changes the cursor key and needs the CLI's Keychain write and daemon reload | A UI action (rejected by the owner) |
| Pages read the same services as the MCP tools | No second API | A separate JSON API for the UI |
| The `ui` command mints the token when the notification is clicked (E11) | No token in the notification, in an argument list or in Notification Center | None recorded |

**Version 1 questions resolved in version 2.**

| Version 1 question | Answer | Source |
| --- | --- | --- |
| Is the notification `ui_path` relative to `/ui`? | No: it includes `/ui` (for example `/ui/review/<batch_id>`); `next` accepts `/ui/` paths only; `research-mcp ui --path` rejects other values. LLD-cache v2 writes `/review/<batch_id>` and must change | LLD-health v2 decision 15; LLD-security v2 2; SEC-29 (owner decision, 2026-10-22) |
| Form of `<batch_id>` | A ULID. The example `rb-2026-11-14` in SPEC-v5 11.3 is illustrative | SPEC-v5 15 ("IDs: ULIDs for internal rows ... batches") |
| Action route names | `/ui/<page path>/action/<name>` with the names in 2.1 | SPEC v2 11 text, completed here |
| Storage of sessions and tokens; restart | In memory, digests only; a restart ends them | LLD-security v2 3, 5.3 |
| CSRF generation, binding, lifetime | Per session, `secrets.token_urlsafe(32)`, lives as long as the session | LLD-security v2 5.3 |
| Names of functions and classes | 5.1 | This LLD; the platform confirms `LoginTokens` |
| Template for source detail | Yes, `source_detail.html` | 5.1 |
| Routes without a session; what a request without a session gets | `/ui/login` only; `/ui/static/*` needs a session; 401 | LLD-security v2 4.3 request classes; SEC-32 |
| Statuses for expired token, CSRF, foreign Host | 401, 403, 403 | LLD-security v2 6; 2.3 |
| Server-sent events | Dropped | UI-FR-20 (owner decision, 2026-10-22) |
| Token rotation in the UI | Not offered | PLAT-FR-59; SPEC-v5 8 (owner decision, 2026-10-22) |
| How retry works | Resubmit through `JobService.submit` | UI-FR-13; UI-24 (owner decision, 2026-10-22) |
| How UI settings persist | Through the `config set` writer to `config.toml` | LLD-platform v2 2.4 |
| Does the review submission apply the `cache_review_decide` checks | Yes, both call `LifecycleService.decide` | LLD-cache v2 5; CACHE-34 |
| Source of Events log lines and search | `research-mcp.jsonl` and its rotated files, filtered by `correlation_id`, `source` or `tool` | LLD-platform v2 4.3, 8; 5.4 |
| Feature flag for the UI | `ui.live_refresh`, proposed | 7; LLD-platform v2 7.2 |
| UI metrics or alerts | None | PRD-ui v4 2.5 |
| Test files | `tests/ui/` as in 9 | `sdd.config.json`; test plan v4 |
| PRD-ui header inconsistencies | Resolved: PRD-ui v4 names PRD-v7 as parent and supersedes PRD-ui v3; this LLD cites PRD-ui v4 and SPEC-v5 | PRD-ui v4 |

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

None open. Resolved (owner decision, 2026-10-23): a setting saved on the Settings page writes `config.toml` and the page shows "applies after the daemon restarts"; no live reload (3.3, 5.4).

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| Kenny Hill (Engineering) | 2026-10-23 | approved (no contract) | approved: none (owns no table, no migration) | approved (security-reviewer persona drafted/reviewed; control owner Kenny Hill) | Approved in chat; recorded by Claude in the owner's name at his direction |
