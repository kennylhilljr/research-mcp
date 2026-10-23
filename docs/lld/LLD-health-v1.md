---
title: "Health, Credentials and Notifications low level design"
type: lld
version: 1
status: draft
owner: "Kenny Hill"
prefix: HLTH
component: health
parent: docs/spec/SPEC-v3.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# LLD: Health, Credentials and Notifications (v1)

This LLD reorganizes [SPEC-v2](../../docs-archive/spec/SPEC-v2.md) section 10 (10.1 to 10.5) and [HLD-v3](../../docs-archive/design/HLD-v3.md) section 7 onto the LLD template. Names are copied from SPEC-v2 unchanged. Requirements: [PRD-health v3](../prd/components/PRD-health-v3.md).

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

Governing section: SPEC-v3 section 7 (Health, credentials and notifications).

| Requirement | Criteria | SPEC section |
| --- | --- | --- |
| HLTH-FR-1 | HLTH-1 (also PLAT-39) | SPEC-v3 section 7 |
| HLTH-FR-2 | HLTH-2 | SPEC-v3 section 7 |
| HLTH-FR-3 | HLTH-3 | SPEC-v3 section 7 |
| HLTH-FR-4 | HLTH-2 | SPEC-v3 section 7 |
| HLTH-FR-5 | HLTH-4 | SPEC-v3 section 7 |
| HLTH-FR-10 | HLTH-10, HLTH-12 | SPEC-v3 section 7 |
| HLTH-FR-11 | HLTH-11 | SPEC-v3 section 7 |
| HLTH-FR-12 | HLTH-12 (also SRCH-8, SRC-29) | SPEC-v3 section 7 |
| HLTH-FR-20 | HLTH-13, HLTH-20 (also SEC-3) | SPEC-v3 section 7 |
| HLTH-FR-21 | HLTH-20, HLTH-21, HLTH-25 | SPEC-v3 section 7 |
| HLTH-FR-22 | HLTH-22 | SPEC-v3 section 7 |
| HLTH-FR-23 | none in this component (SEC-4) | SPEC-v3 section 7 |
| HLTH-FR-24 | HLTH-23 | SPEC-v3 section 7 |
| HLTH-FR-25 | HLTH-24 | SPEC-v3 section 7 |
| HLTH-FR-30 | HLTH-13, HLTH-30 | SPEC-v3 section 7 |
| HLTH-FR-31 | HLTH-31 | SPEC-v3 section 7 |
| HLTH-FR-32 | HLTH-32 | SPEC-v3 section 7 |
| HLTH-FR-33 | HLTH-33 | SPEC-v3 section 7 |
| HLTH-FR-34 | HLTH-34 | SPEC-v3 section 7 |
| HLTH-FR-35 | HLTH-35 | SPEC-v3 section 7 |
| HLTH-FR-40 | HLTH-40, HLTH-41 | SPEC-v3 section 7 |
| HLTH-FR-41 | HLTH-41 (also PLAT-81) | SPEC-v3 section 7 |
| HLTH-FR-42 | HLTH-42 (also SRC-8) | SPEC-v3 section 7 |
| HLTH-FR-43 | HLTH-42 (also PLAT-70) | SPEC-v3 section 7 |
| UI-FR-2 | HLTH-32 | SPEC-v3 section 7 |
| CACHE-FR-45 | HLTH-41 | SPEC-v3 section 7 |
| NFR-3 | HLTH-32 | SPEC-v3 section 7 |
| NFR-4 | HLTH-34 | SPEC-v3 section 7 |

Criteria of this component: HLTH-40, HLTH-1, HLTH-2, HLTH-3, HLTH-4, HLTH-10, HLTH-12, HLTH-13, HLTH-11, HLTH-20, HLTH-21, HLTH-22, HLTH-23, HLTH-24, HLTH-25, HLTH-30, HLTH-31, HLTH-32, HLTH-33, HLTH-34, HLTH-35, HLTH-41, HLTH-42. Criteria in parentheses belong to other components and also verify the requirement (TEST-PLAN-v3 section 5).

Shape (HLD-v3 section 7):

```
 HTTP client --telemetry--> state.db.calls --rollup--> source_health
 scheduler --probes--> adapters.probe() ----------------^
 secrets --metadata--> state.db.credentials <-- passive headers (GitHub expiry, rate limits)
 health.evaluate() -> source and credential states -> diff -> notify (macOS, OpenClaw webhook, UI banner)
 doctor (launchd: liveness every 15 min, full daily) -> same checks without the daemon -> notify on change
```

- **States** follow PRD-health section 2 (now PRD-health v3 section 2.4).
- **Notifications** fire on state changes and roll unresolved items into a daily digest, with quiet hours.
- **Federation** consults health before selecting sources.

Milestones (HLD-v3 14; SPEC-v2 12.3, 12.4): the `doctor` skeleton is unit M0-16 (HLTH-40); the health, credential and notify services, `ops_status`, `research://status` and the full set of doctor checks are M1.

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

No machine-readable contract exists yet in `docs/contracts/` (see 11).

**HTTP endpoints** (SPEC-v2 10.5):

| Endpoint | Auth | Returns |
| --- | --- | --- |
| `/healthz` | none | `{"status":"ok","version":"3.x.y"}` |
| `/readyz` | none | Ok when the stores are open, the scheduler is running and the Keychain is readable; 503 otherwise |
| `/api/status` | bearer token or a UI session | JSON of sources, credential metadata, quotas, jobs, cache stats, disk, the archive target and the last 20 notifications |

`app.py` provides `build_app(settings) -> Starlette app (mounts /mcp, /ui, /healthz, /readyz, /api)` (SPEC-v2 1).

**MCP surface** (SPEC-v2 7.2, 7.3):

| Tool | Signature (bounds) | Service | Annotations | M |
| --- | --- | --- | --- | --- |
| `ops_status` | none | health | RO | M1 |

| Milestone | Resources |
| --- | --- |
| M0 | `research://sources` |
| M1 | `research://status` |

`ops_status` returns a summary only, with no secrets (HLTH-FR-42).

**CLI** (SPEC-v2 12.1):

| Command | Purpose |
| --- | --- |
| `doctor [--json] [--notify] [--quick] [--liveness]` | Run health checks (10.5). |

**Webhook** (SPEC-v2 10.4): `POST notify.webhook_url` with JSON `{type, severity, subject, body, ui_path, ts}` and `Authorization: Bearer <NOTIFY_WEBHOOK_TOKEN>` when that item exists.

**macOS notification** (SPEC-v2 10.4): `terminal-notifier -title "Research MCP" -subtitle <subject> -message <body> -group research-mcp-<dedupe_key> -execute "<venv>/bin/research-mcp ui --path <ui_path>"`. The fallback is `osascript -e 'display notification ...'`.

**Internal event** (SPEC-v2 10.2): `HealthEvent(kind, subject, severity, ui_path, dedupe_key)`, emitted by `HealthService` to `NotifyService`.

**Shared models used by this component** (SPEC-v2 4, verbatim):

```python
@dataclass(frozen=True)
class AuthSpec:
    secrets: tuple[str, ...]                 # Keychain names
    required: bool
    placement: Literal["header", "query", "bearer"]
    param: str                               # header or query name
    origins: tuple[str, ...]                 # credential attached only for these origins (scheme://host)
    signup_url: str
    validation: Literal["probe", "github_rate_limit", "header_expiry", "none"] = "probe"

@dataclass(frozen=True)
class ProbeSpec: cadence_s: int; cost: Literal["free", "metered"]; description: str

class ProbeResult(BaseModel): ok: bool; latency_ms: int; shape_ok: bool; detail_code: str | None = None
                              quota_remaining: str | None = None; credential_expires_at: datetime | None = None

class CallRecord(BaseModel): ts: datetime; source: str; op: str; status: int | None; error_code: str | None
                             latency_ms: int; bytes: int; rl_remaining: str | None; rl_reset: str | None
                             cred_expires_at: str | None; correlation_id: str | None; attempt: int
```

`SourceSpec` carries `probe: ProbeSpec = ProbeSpec(3600, "free", "")` and `shutdown_on: date | None = None`; each adapter implements `async def probe(self) -> ProbeResult` (SPEC-v2 4).

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

`state.db` (SQLite, WAL) in `~/Library/Application Support/research-mcp/`, backed up nightly with 7 kept (HLD-v3 10). Migration `migrations/state/0001_init.sql` (SPEC-v2 10.1, verbatim):

```sql
CREATE TABLE calls (ts TEXT NOT NULL, source TEXT NOT NULL, op TEXT NOT NULL, status INTEGER,
  error_code TEXT, latency_ms INTEGER, bytes INTEGER, rl_remaining TEXT, rl_reset TEXT,
  cred_expires_at TEXT, correlation_id TEXT, attempt INTEGER NOT NULL DEFAULT 1);
CREATE INDEX calls_source_ts ON calls(source, ts);
CREATE TABLE call_rollups (hour TEXT NOT NULL, source TEXT NOT NULL, calls INTEGER, errors INTEGER,
  p50_ms INTEGER, p95_ms INTEGER, PRIMARY KEY (hour, source));
CREATE TABLE source_health (source TEXT PRIMARY KEY, state TEXT NOT NULL, reason TEXT, fix_hint TEXT,
  last_probe_at TEXT, last_probe_ok INTEGER, consecutive_failures INTEGER NOT NULL DEFAULT 0,
  rate_limited_until TEXT, budget_reset_at TEXT, quota_remaining TEXT, quota_reset TEXT,
  baseline_p95_ms INTEGER, calls_today INTEGER NOT NULL DEFAULT 0, api_version_seen TEXT,
  enabled INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL);
CREATE TABLE credentials (name TEXT PRIMARY KEY, service TEXT NOT NULL, required_by TEXT NOT NULL,
  fingerprint TEXT, keychain_modified_at TEXT, expires_at TEXT, rotate_by TEXT,
  last_validated_at TEXT, last_result TEXT, state TEXT NOT NULL, last_used_at TEXT, updated_at TEXT NOT NULL);
CREATE TABLE searches (search_id TEXT PRIMARY KEY, ts TEXT NOT NULL, query_hash TEXT NOT NULL,
  query_len INTEGER NOT NULL, sources_json TEXT NOT NULL, statuses_json TEXT NOT NULL, latency_ms INTEGER);
CREATE TABLE jobs (job_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('pending','running','succeeded','failed','cancelled')),
  params_json TEXT NOT NULL, progress REAL NOT NULL DEFAULT 0, cursor TEXT, result_json TEXT,
  error_code TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE schedule_runs (job TEXT PRIMARY KEY, last_run_at TEXT, next_due_at TEXT NOT NULL);
CREATE TABLE notifications (notification_id TEXT PRIMARY KEY, ts TEXT NOT NULL, kind TEXT NOT NULL,
  severity TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL, ui_path TEXT,
  channels_json TEXT NOT NULL, acknowledged_at TEXT, snoozed_until TEXT, dedupe_key TEXT NOT NULL);
CREATE TABLE review_batches (batch_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, notified_at TEXT,
  closes_at TEXT NOT NULL, closed_at TEXT, item_count INTEGER NOT NULL);
CREATE TABLE review_events (ts TEXT NOT NULL, doc_id TEXT NOT NULL, batch_id TEXT, from_state TEXT NOT NULL,
  to_state TEXT NOT NULL, decided_by TEXT, channel TEXT);
CREATE TABLE disk_samples (ts TEXT PRIMARY KEY, cache_bytes INTEGER, files_bytes INTEGER, index_bytes INTEGER,
  embeddings_bytes INTEGER, trash_bytes INTEGER, free_cache_vol INTEGER, free_archive_vol INTEGER);
CREATE TABLE maintenance_runs (ts TEXT NOT NULL, check_name TEXT NOT NULL, ok INTEGER NOT NULL, detail TEXT);
```

Retention: `calls` 30 days; `call_rollups` 13 months; `disk_samples` 90 days; everything else is kept.

Tables this component reads and writes, per SPEC-v2 10.2 to 10.4: `calls` (written through `StateStore.record_call`, SPEC-v2 3.3), `call_rollups`, `source_health`, `credentials` and `notifications`. The other tables share the migration and serve the jobs, federation and cache components [inferred].

Requirement mapping: `calls` columns hold the fields of HLTH-FR-1; `credentials` holds the metadata of HLTH-FR-20 (no value column); `notifications.acknowledged_at` and `snoozed_until` hold the state of HLTH-FR-35; `notifications.dedupe_key` supports once-only delivery (HLTH-FR-30).

Migrations are forward-only; the pre-upgrade backup is what makes rollback possible (SPEC-v2 12.2).

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

| Point | Enforcement | Source |
| --- | --- | --- |
| `/healthz`, `/readyz` | No auth; loopback only | SPEC-v2 10.5; NFR-7 |
| `/api/status` | Bearer token or a UI session | SPEC-v2 10.5 |
| `ops_status`, `research://status`, `research://sources` | Read-only; summary only, no secrets | SPEC-v2 7.2; HLTH-FR-42 |
| macOS notification click-through | The `ui` command mints its one-time login token when the notification is clicked, so no token sits in the notification itself, in a process argument list or in Notification Center | SPEC-v2 10.4 |
| Webhook | `Authorization: Bearer <NOTIFY_WEBHOOK_TOKEN>` from the Keychain; never in the URL | SPEC-v2 10.4; settings `notify.webhook_url` |
| Credential values | `Secret.reveal()` is called only in `platform/http.py`, `platform/mcp_client.py` and `platform/auth.py`; this component handles fingerprints and metadata only | SPEC-v2 3.1 |
| Keychain metadata | `metadata` runs the same `security` command without `-w`; only the `mdat` attribute is parsed | SPEC-v2 3.1 |
| Google sign-in | The access token is held in memory and revealed only by `platform/http.py` for `https://discoveryengine.googleapis.com`; v2's own code never opens, copies or writes the credential file | SPEC-v2 3.1.1 |
| Notification text | Passes through the one redaction filter; never a secret value or a URL with query parameters | HLD-v3 9; HLTH-FR-34 |

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

**Modules** (SPEC-v2 1):

| Module | Role in this component |
| --- | --- |
| `services/health.py` | `HealthService`: probe scheduling, `evaluate(source)`, `source_health` writes, `HealthEvent` emission |
| `services/credentials.py` | Credential states and validation (SPEC-v2 10.3); no class name is given in SPEC-v2 (see 11) |
| `services/notify.py` | `NotifyService.emit(event)` and channels |
| `cli.py` | `research-mcp doctor` |
| `app.py` | `/healthz`, `/readyz`, `/api` |
| `mcp_app/tools_ops.py`, `mcp_app/resources.py` | `ops_status`; `research://status` and `research://sources` [inferred: SPEC-v2 does not map tools to files] |
| `platform/secrets.py` | `SecretProvider`, `SecretCache` (state, metadata, reload) |
| `platform/google_adc.py` | `GoogleAdcProvider` (Google sign-in) |
| `platform/http.py` | `CallSink` telemetry; header parsing for `rl_remaining`, `rl_reset`, `cred_expires_at` |
| `platform/scheduler.py` | `Scheduler`: probe intervals and the `digest` job |
| `packaging/launchd/` | `local.research-mcp-doctor.plist.template`, `local.research-mcp-watchdog.plist.template` |
| `testing/notifier.py`, `testing/launchctl.py`, `testing/clock.py` | Fakes for tests |

**Platform interfaces consumed** (SPEC-v2 3.1, verbatim excerpt):

```python
class SecretState(StrEnum): OK="ok"; MISSING="missing"; LOCKED="keychain_locked"; ERROR="error"

class SecretProvider(Protocol):
    def get(self, ref: SecretRef) -> tuple[SecretState, Secret | None]: ...
    def metadata(self, ref: SecretRef) -> SecretMeta | None: ...   # no value
    def set(self, ref: SecretRef, value: str) -> None: ...          # value never in argv

class SecretCache:           # what the daemon uses; implements CredentialResolver with a source->names map
    def __init__(self, provider: SecretProvider, refs: Mapping[str, SecretRef]): ...
    def load(self) -> None: ...
    def get(self, name: str) -> Secret | None: ...
    def state(self, name: str) -> SecretState: ...
    def reload(self) -> list[str]: ...      # names whose fingerprint changed

class GoogleAdcProvider:                     # implements SecretProvider for backend "gcloud_adc"; extra gcp
    def get(self, ref: SecretRef) -> tuple[SecretState, Secret | None]: ...   # cached token; refresh when < 5 min left
    def metadata(self, ref: SecretRef) -> SecretMeta | None: ...              # account email, token expiry; no token
```

`Secret.fingerprint` is `sha256(value)[:8]` (HLTH-FR-20). `SecretCache.reload` serves "Reload credentials" (HLTH-FR-23).

Carried from SPEC-v2 0.6 because health reads credential metadata through `SecretProvider.metadata`:

| Unit | Section | Requirement |
| --- | --- | --- |
| M0-05 | 3.1; AT-PLAT-12, AT-SEC-13 | `SecretRef` MUST validate on construction: the name matches the allowed pattern, and a Keychain reference's service is exactly `research-mcp/<NAME>`. No control character (in particular a newline) may reach the `security -i` script. `FakeProvider.metadata` MUST behave like `KeychainProvider.metadata` (no metadata for `env:` references). |

(SPEC-v2 0.6) No other 0.6 row concerns this component.

**Probes and state evaluation** (SPEC-v2 10.2, verbatim):

- `HealthService` schedules each source's probe at `spec.probe.cadence_s`, with 0 to 10% jitter. A probe is skipped when a successful call already happened in its window (FR-HLTH-04, now HLTH-FR-4).
- `evaluate(source)` applies the table in PRD-health section 2.2 (now PRD-health v3 section 2.4), most severe state first. Its inputs are:
  - the last 20 calls from `calls`;
  - `consecutive_failures`;
  - the 7-day p95 baseline from the rollups;
  - `rate_limited_until` and `budget_reset_at`;
  - the `credentials` table;
  - `spec.shutdown_on`.
- On a state change, the service writes `source_health` and emits `HealthEvent(kind, subject, severity, ui_path, dedupe_key)` to `NotifyService`.

Probe cadences for the `web` group (SPEC-v2 5.5): `vertex_search` reads the engine metadata every 6 h (no query cost); `brave_search` has no free probe, one query every 24 h, with rate-limit headers parsed passively on every call; `serpapi` calls `GET https://serpapi.com/account.json` (free; gives searches left) every 6 h; `google_pse` has no free probe, one query every 24 h, `shutdown_on = 2027-01-01`. Each call to a web source counts against its cap; at the cap the source reports `budget_exhausted(reset=next local midnight)`.

**Credential validation** (SPEC-v2 10.3, verbatim):

| Validation | Method |
| --- | --- |
| `github_rate_limit` | `GET https://api.github.com/rate_limit`, which is free. A 401 means `invalid`. `resources.*.remaining` gives the quota, and the response header `github-authentication-token-expiration` gives the expiry. |
| `header_expiry` | The expiry header is parsed on every authenticated call (GitHub). |
| `probe` | The source probe, with credentials attached. Auth failures are classified as `invalid`. |
| Google API key | A probe to `https://developerknowledge.googleapis.com/v1/documents:searchDocumentChunks?query=documentation&pageSize=1` with the key in `x-goog-api-key`. `API_KEY_INVALID` and `SERVICE_DISABLED` map to `invalid`. The same key also serves `google_pse`, whose own probe is metered (5.5). |
| `google_adc` (Google sign-in, M1) | `GoogleAdcProvider` refreshes the token (free), then the Vertex probe reads the engine metadata (free). `missing`: no sign-in found. `invalid`: refresh refused, `SERVICE_DISABLED`, or `PERMISSION_DENIED` on the engine (the reason is kept). Fix text: `gcloud auth application-default login`, plus the engine's console page for permission problems. Token expiry is about an hour and renews itself, so it never raises `expiring_soon`. |
| `serpapi_account` | `GET https://serpapi.com/account.json` (free). 401 means `invalid`; the searches-left figure sets `quota_low`. |
| Brave | Passive: rate-limit headers on each call set quota; 401 or 403 on a call means `invalid`. |
| Missing or locked | `SecretProvider.get` returns `missing` or `keychain_locked`. If the Keychain is locked, every credential shows `keychain_locked`, and only one notification fires ("Keychain locked"); there is no per-key notice. |
| No expiry exposed | `rotate_by = keychain_modified_at + 180 d`, unless set by the owner. |

Fix text for Keychain credential states names the Keychain item `research-mcp/<NAME>`, the provider's key page (`AuthSpec.signup_url` [inferred]) and `security add-generic-password -U -s research-mcp/<NAME> -a "$USER" -w` with no value (HLTH-FR-24).

**Notifications** (SPEC-v2 10.4, verbatim):

- **`NotifyService.emit(event)`** dedupes by `dedupe_key` for the life of the state, applies quiet hours, delivers to the channels, and stores the notification in `notifications`.
- **macOS:** the `terminal-notifier` command in section 2.
  - The `ui` command mints its one-time login token when the notification is clicked, so no token sits in the notification itself, in a process argument list or in Notification Center.
  - The fallback is `osascript -e 'display notification ...'`, which cannot be clicked through.
  - `doctor` reports whether `terminal-notifier` is installed.
- **Webhook:** `POST notify.webhook_url` with JSON `{type, severity, subject, body, ui_path, ts}` and `Authorization: Bearer <NOTIFY_WEBHOOK_TOKEN>` when that item exists. The timeout is 5 s, there are at most 2 retries, and failures are logged.
- **Digest:** at 08:00 local time, one notification summarizes the unresolved items.

Notification triggers are the list in HLTH-FR-30. A cache review batch notice is sent through `NotifyService` with `ui_path=/review/<batch_id>` (SPEC-v2 9.2).

**Doctor** (SPEC-v2 10.5, verbatim). `research-mcp doctor` runs these checks, each with a code and fix text:

| Check | What it verifies |
| --- | --- |
| `daemon_alive` | `GET /healthz` answers. |
| `keychain_readable` | The Keychain can be read, and is not locked. |
| `contact_email` | A contact email is set. |
| one check per credential | The credential's current state. |
| one probe per enabled source | The source responds; with `--quick`, only free probes run. |
| `archive_target` and `archive_access` | The archive folder is available; TCC access is granted. |
| `disk` | Disk thresholds. |
| `schema_versions` | Database schema versions match the code. |
| `review_overdue` | No review missed by more than 24 hours. |
| `backup_recent` | A backup ran in the last 48 hours. |
| `terminal_notifier` | terminal-notifier is installed. |
| `launchd_jobs` | `launchctl print gui/$UID/local.research-mcpd` and the other two jobs. |

- **Flags:**
  - `--liveness` checks only `daemon_alive` and `keychain_readable`.
  - `--notify` sends one summary notification when anything is not ok, and only when the result changed since the last notify.
- **Exit code:** 0 when no check is critical.

`archive_access` writes and removes the sentinel `.research-mcp-probe` and reports `tcc_denied` with the fix: grant the daemon's interpreter Files and Folders access to Google Drive in System Settings, Privacy & Security (SPEC-v2 9.3). The M0-16 skeleton runs `daemon_alive`, `keychain_readable`, `contact_email` and `schema_versions` (HLTH-40).

**launchd jobs** (SPEC-v2 12.2, verbatim):

| Template | Runs | Schedule and options |
| --- | --- | --- |
| `local.research-mcp-doctor.plist.template` | `research-mcp doctor --notify` | `StartCalendarInterval` Hour 8 Minute 52 |
| `local.research-mcp-watchdog.plist.template` | `research-mcp doctor --liveness --notify` | `StartInterval` 900 |

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

| Situation | Handling | Source |
| --- | --- | --- |
| 429 with `Retry-After` over 60 s | The call is not waited for; it fails with `rate_limited` and `retry_after_ms`, which sets `rate_limited_until` | SPEC-v2 3.3; HLTH-12 |
| Budget responses | `policy.error_classifier` maps them, for example OpenAlex "Insufficient budget" 429 to `budget_exhausted` with `detail="daily budget"`, which sets `budget_reset_at` | SPEC-v2 3.3 |
| Keychain read | 5 s timeout; exit 44 maps to `missing`; exit 36 or 51, or "User interaction is not allowed", maps to `keychain_locked`; anything else maps to `error`; stderr text is never logged or returned | SPEC-v2 3.1 |
| Google sign-in | `DefaultCredentialsError` maps to `missing`; `RefreshError` maps to `invalid`; the exception text is never logged or returned; loading and refreshing run through `anyio.to_thread.run_sync` | SPEC-v2 3.1.1 |
| Webhook delivery | Timeout 5 s, at most 2 retries, failures logged | SPEC-v2 10.4 |
| Repeated events | `NotifyService.emit` dedupes by `dedupe_key` for the life of the state | SPEC-v2 10.4 |
| Repeated `doctor --notify` | One summary only when the result changed since the last notify | SPEC-v2 10.5 |
| Missed schedules (Mac asleep, daemon down) | The wall-clock `Scheduler` runs a missed job once at start or on wake, never once per missed day | SPEC-v2 3.6 |
| Readiness failure | `/readyz` returns 503 | SPEC-v2 10.5 |
| `doctor` exit | 0 when no check is critical | SPEC-v2 10.5 |
| Telemetry | Every attempt produces a `CallRecord`; the sink is non-blocking and buffered, flushed every second | SPEC-v2 3.3 |

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

Settings keys (SPEC-v2 2, verbatim rows):

| Key | Default | Notes |
| --- | --- | --- |
| `notify.macos` | `true` | `terminal-notifier` if present, else `osascript` (no click-through) |
| `notify.webhook_url` | none | OpenClaw inbox (open decision O5); any token goes in Keychain `NOTIFY_WEBHOOK_TOKEN`, never in the URL |
| `notify.quiet_hours` | `"21:00-08:00"` | |
| `contact.email` | none | Crossref `mailto`, Unpaywall `email`, user agent. Placeholder domains (`example.com`, `example.org`, `test`, `invalid`) are rejected. If unset, sources with `needs_contact` are `unconfigured`; the daemon still starts. |
| `disk.cache_warn_bytes` | `5368709120` | |
| `disk.free_warn_bytes` / `free_crit_bytes` | `16106127360` / `5368709120` | |
| `sources.<id>.enabled` | spec default | |
| `sources.<id>.budget_cap` | none (`100` for `web` sources) | Daily call cap for metered sources (UI Quota page); resets at local midnight |
| `credentials.<NAME>.rotate_by` | none | Optional override |

Scheduler (SPEC-v2 3.6): `digest` at 08:00 local time; probes at their own cadence.

| Flag | Default | Safe to switch off? |
| --- | --- | --- |
| `notify.macos` | `true` | Not stated in SPEC-v2 (see 11) |
| `notify.webhook_url` | none (channel off) | Not stated in SPEC-v2 (see 11) |
| `sources.<id>.enabled` | spec default | Yes for the source: a disabled source shows `disabled` (PRD-health v3 2.4) |

## 8. Observability

> **Owner:** A · **Persona:** `sre`

| Signal | Where | Threshold or use | Traces to |
| --- | --- | --- | --- |
| Call telemetry | `calls`, `call_rollups` | Error rate above 10% over the last 20 calls, or p95 above 3 times the 7-day baseline, gives `degraded` | HLTH-FR-1, HLTH-FR-10 |
| Probe results | `source_health.last_probe_at`, `last_probe_ok`, `consecutive_failures` | 3 failed probes in a row gives `down` | HLTH-FR-10 |
| Credential state | `credentials` | 14 days (warning) and 3 days (critical) before expiry; quota below 10% | HLTH-FR-30; OUT-5 |
| Notifications | `notifications`; last 20 in `/api/status` | State change reaches the owner within 15 minutes outside quiet hours | HLTH-OUT-2; OUT-4 |
| Watchdog | `local.research-mcp-watchdog`, every 900 s | Dead daemon reported within 15 minutes | HLTH-OUT-3; OUT-4 |
| Logs | `log_dir/research-mcp.jsonl`, JSON lines through `RedactingFilter`, `correlation_id` per call and job | Recent warnings and errors shown in the UI | SPEC-v2 3.2; HLD-v3 12 |
| Status | `/healthz`, `/readyz`, `/api/status`, `ops_status`, `research://status` | | HLTH-FR-42, HLTH-FR-43 |

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

No test in `tests/` cites an HLTH criterion yet. HLTH-40's file is named by SPEC-v2 12.3 (unit M0-16); the other criteria have no file named by SPEC-v2 or TEST-PLAN-v3.

| Criterion | Planned tests | Level | Status |
| --- | --- | --- | --- |
| HLTH-40 | `tests/unit/test_cli.py` | unit | planned |
| HLTH-1 | planned | integration | planned |
| HLTH-2 | planned | integration | planned |
| HLTH-3 | planned | integration | planned |
| HLTH-4 | planned | integration | planned |
| HLTH-10 | planned | unit | planned |
| HLTH-12 | planned | unit | planned |
| HLTH-13 | planned | unit | planned |
| HLTH-11 | planned | integration | planned |
| HLTH-20 | planned | unit | planned |
| HLTH-21 | planned | integration | planned |
| HLTH-22 | planned | unit | planned |
| HLTH-23 | planned | unit | planned |
| HLTH-24 | planned | unit | planned |
| HLTH-25 | planned | integration | planned |
| HLTH-30 | planned | integration | planned |
| HLTH-31 | planned | integration | planned |
| HLTH-32 | planned | unit | planned |
| HLTH-33 | planned | unit | planned |
| HLTH-34 | planned | unit | planned |
| HLTH-35 | planned | unit | planned |
| HLTH-41 | planned | integration | planned |
| HLTH-42 | planned | contract | planned |

Related evidence in other components: SEC-3 (`tests/unit/platform/test_secrets.py::test_keychain_metadata_never_passes_w` and three more) and SEC-4 (`tests/unit/platform/test_secrets.py::test_secret_cache_reload_returns_changed_names`) are linked tests for HLTH-FR-20 and HLTH-FR-23. Owner checks OC-03 (a real macOS notification opens the right UI page) and OC-14 (doctor shows the Google sign-in ok) also cover this component (TEST-PLAN-v3 section 6). Integration tests use the fakes in `research_mcp.testing`: `FakeProvider`, `FakeClock`, fake sleeper, fake `launchctl` and fake notifier (TEST-PLAN-v3 2).

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| Credential values stay in the Keychain; `state.db` holds metadata and fingerprints only | No secrets at rest outside the Keychain (ADR 0003; NFR-3) | Plaintext client configs, as in v1 (REVIEW-v1 OPS-11) |
| `doctor` runs without the daemon, driven by two launchd jobs | A dead daemon must still be reported (HLTH-FR-41; ADR 0002) | Not stated |
| The scheduler follows the wall clock | asyncio timers stall while the Mac sleeps (SPEC-v2 3.6) | asyncio timers |
| The notification click runs `research-mcp ui --path`, which mints the login token on click | No token in the notification, an argument list or Notification Center (SPEC-v2 10.4) | Not stated |
| The Google sign-in stays with `gcloud` | v2 holds only a short-lived token in memory (ADR 0012; HLD-v3 9) | Dropping the Vertex provider (REVIEW-v1 OPS-24) |
| Probes check response shape | Upstream drift can return 200 with wrong data (HLD-v3 9; REVIEW-v1 OPS-15) | Status code only, as in v1 |

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

- [ ] Q: SPEC-v2 5.5 says each web-source call counts against its cap through `quota_used` in `source_health`, but the 10.1 schema has no `quota_used` column (it has `calls_today`). Which column is the contract?
- [ ] Q: `AuthSpec.validation` allows only `"probe"`, `"github_rate_limit"`, `"header_expiry"` and `"none"` (SPEC-v2 4), while SPEC-v2 10.3 also names `google_adc` and `serpapi_account` validations. Should the literal grow, or are these classified another way?
- [ ] Q: HLTH-FR-25 and SPEC-v2 3.1.1 store the Google sign-in account email and token expiry, but `SecretMeta` has only `name` and `modified_at`, and the `credentials` table has no account email column. Where is the account email held?
- [ ] Q: HLTH-FR-23 names `SIGHUP` as a reload trigger; SPEC-v2 defines `SecretCache.reload` but no signal handler. Is `SIGHUP` in the contract?
- [ ] Q: HLTH-FR-11 exposes "calls in 24 hours", while `source_health` stores `calls_today`. Is the figure a rolling 24 hours or the calendar day?
- [ ] Q: HLTH-FR-5 lists embeddings as a local probe target; SPEC-v2 10.5 has no embeddings check and HLTH-4 omits it. Is an embeddings probe required?
- [ ] Q: SPEC-v2 12.4 places "the full set of doctor checks" in M1, but HLTH-41 is milestone M2 (TEST-PLAN-v3). Which milestone holds the full doctor?
- [ ] Q: HLTH-FR-32 names a UI banner channel; SPEC-v2 10.4 lists only macOS, webhook and digest delivery, and SPEC-v2 11 only a banner slot. Which module feeds the banner?
- [ ] Q: SPEC-v2 names no class in `services/credentials.py`, and no file for `ops_status` and `research://status`. What are the names?
- [ ] Q: Which health behaviors need a registered feature flag, and are `notify.macos` and `notify.webhook_url` safe to switch off?
- [ ] Q: No machine-readable contract exists in `docs/contracts/` for `/api/status`, `ops_status`, `research://status` or the webhook payload. Should they be added?
- [ ] Q: HLD-v3 13 says "no paid search providers" under Cost, while ADR 0012 and SPEC-v2 5.5 add metered web-search sources whose quotas this component tracks. Which statement is current?

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
