---
title: "Health, Credentials and Notifications low level design"
type: lld
version: 2
supersedes: docs/lld/LLD-health-v1.md
status: draft
owner: "Kenny Hill"
prefix: HLTH
component: health
parent: docs/spec/SPEC-v5.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# LLD: Health, Credentials and Notifications (v2)

This LLD carries over SPEC-v2 section 10 (10.1 to 10.5) and SPEC-v5 section 7. Names are copied from SPEC-v2 unchanged unless section 10 renames one. Requirements and criteria: [PRD-health v4](../prd/components/PRD-health-v4.md). System design: [SPEC-v5](../spec/SPEC-v5.md). Cross-cutting security: [PRD-security v3](../prd/components/PRD-security-v3.md) and [LLD-security v2](LLD-security-v2.md) (draft). Platform parts this LLD consumes: [LLD-platform v2](LLD-platform-v2.md) (draft). Test plan: [test plan v4](../test/test-plan-v4.md) (draft). Machine-readable contract: [health status, doctor output and webhook payload v1](../contracts/health-status-and-webhook-v1.md) (draft for the owner). Supersedes [LLD-health v1](LLD-health-v1.md).

**Changes in v2.** This version follows the approved PRD-health v4 and SPEC-v4, which win wherever v1 disagreed. History note: `skipped_budget` is now `budget_exhausted` and the `web` fallback adds `not_needed` (SRCH-FR-27); v1 cited the earlier IDs FR-HLTH-04, PLAT-39 and SRC-8 in places, which now use the current IDs. Added: HLTH-43 and HLTH-44 in the criteria (1, 9); the source and credential state rules as executable algorithms with the pure function `evaluate_source` (5.5, 5.7); the probe scheduler, passive evidence and the telemetry rollup (5.3, 5.4); the local targets (5.6); the notification rules (5.8): dedupe keys, quiet hours, the digest, the banner feed, snooze, argv and shell safety, and the webhook through the HTTP layer; `doctor` severities, `--quick`, `--notify` memory and the milestone split (5.9); readiness (5.10); the machine-readable contract. The twelve open questions of v1 are settled in section 10 from the approved sources; the two that the sources left to the owner were answered on 2026-10-22 (the account email column and what is critical) and no question is open in section 11.

**Reviewer note.** Sections 4, 8 and 9 belong to other personas (`security-reviewer`, `sre`, `test-architect`). They were drafted by the `component-designer` and have been reviewed in Gate 3 on 2026-10-23: section 4 by `security-reviewer`, section 8 by `sre` and section 9 by `test-architect`; they invent no policy, and nothing here has been verified by the owner.

In the tables, "SPEC n" means section n of SPEC-v5 and "SPEC-v2 n.m" means that section of the archived SPEC-v2. Bare numbers in this LLD's own text refer to sections of this LLD.

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

Governing sections: SPEC 7 (health, credentials and notifications), SPEC 9 (security architecture, for redaction and the webhook), SPEC 10 (data stores, for `state.db`), SPEC 12 (deployment: the watchdog and daily `doctor`) and SPEC 14 (milestones).

| Requirement | Criteria | SPEC section | Detailed in |
| --- | --- | --- | --- |
| HLTH-FR-1 | HLTH-1 (also PLAT-39) | SPEC 7 | 3, 5.3 |
| HLTH-FR-2 | HLTH-2 | SPEC 7 | 5.4 |
| HLTH-FR-3 | HLTH-3 | SPEC 7 | 5.4 |
| HLTH-FR-4 | HLTH-2 | SPEC 7 | 5.4 |
| HLTH-FR-5 | HLTH-4, HLTH-44 | SPEC 7 | 5.6 |
| HLTH-FR-10 | HLTH-10, HLTH-12 | SPEC 7 | 5.5 |
| HLTH-FR-11 | HLTH-11 | SPEC 7 | 2.1, 5.5 |
| HLTH-FR-12 | HLTH-12 (also SRCH-8, SRC-29) | SPEC 5, 7 | 5.5 |
| HLTH-FR-20 | HLTH-13, HLTH-20, HLTH-43 (also SEC-3, SEC-24) | SPEC 7, 9 | 3, 5.7 |
| HLTH-FR-21 | HLTH-20, HLTH-21, HLTH-25 | SPEC 7 | 5.7 |
| HLTH-FR-22 | HLTH-22 | SPEC 7 | 5.7 |
| HLTH-FR-23 | none in this component (verified by SEC-4) | SPEC 7, 9, 11.4 | 5.7 |
| HLTH-FR-24 | HLTH-23 | SPEC 7 | 5.7 |
| HLTH-FR-25 | HLTH-24 | SPEC 7 | 5.7 |
| HLTH-FR-30 | HLTH-13, HLTH-30 | SPEC 7 | 5.8 |
| HLTH-FR-31 | HLTH-31 | SPEC 7 | 5.8 |
| HLTH-FR-32 | HLTH-32 (also OC-03) | SPEC 7, 9 | 5.8 |
| HLTH-FR-33 | HLTH-33 | SPEC 7 | 5.8 |
| HLTH-FR-34 | HLTH-34 | SPEC 7, 9 | 5.8 |
| HLTH-FR-35 | HLTH-35 | SPEC 7 | 5.8 |
| HLTH-FR-40 | HLTH-40, HLTH-41 | SPEC 7, 12 | 5.9 |
| HLTH-FR-41 | HLTH-41 (also PLAT-81) | SPEC 7, 12 | 5.9 |
| HLTH-FR-42 | HLTH-42 (also SRC-8) | SPEC 7 | 2.2, 5.10 |
| HLTH-FR-43 | HLTH-42 (also PLAT-70) | SPEC 7 | 2.1, 5.10 |
| HLTH-INV-1 | HLTH-43 (also SEC-3) | SPEC 7, 9 | 3, 4 |
| HLTH-INV-2, HLTH-INV-3 | HLTH-34, HLTH-32 | SPEC 9 | 4, 5.8 |
| HLTH-INV-4 | HLTH-25 | SPEC 7 | 5.7 |
| HLTH-INV-5 | HLTH-24 | SPEC 7, 9 | 3, 5.7 |
| UI-FR-2 | HLTH-32 | SPEC 7, 8 | 5.8 |
| CACHE-FR-45 | HLTH-41 | SPEC 6, 7 | 5.9 |
| NFR-3 | HLTH-32, HLTH-43 | SPEC 9 | 4 |
| NFR-4 | HLTH-34 | SPEC 9 | 4 |
| NFR-12 | HLTH-41 | SPEC 12 | 5.9 |

Criteria of this component: HLTH-40, HLTH-1, HLTH-2, HLTH-3, HLTH-4, HLTH-10, HLTH-12, HLTH-13, HLTH-11, HLTH-20, HLTH-21, HLTH-22, HLTH-23, HLTH-24, HLTH-25, HLTH-30, HLTH-31, HLTH-32, HLTH-33, HLTH-34, HLTH-35, HLTH-41, HLTH-42, HLTH-43, HLTH-44. Criteria in parentheses belong to other components and also verify the requirement (test plan v4 section 2).

Shape (SPEC 7):

```
 HTTP client --telemetry--> state.db.calls --rollup--> source_health
 scheduler --probes--> adapters.probe() ----------------^
 secrets --metadata--> state.db.credentials <-- passive headers (GitHub expiry, rate limits)
 health.evaluate() -> source and credential states -> diff -> notify (macOS, OpenClaw webhook, UI banner)
 doctor (launchd: liveness every 15 min, full daily) -> same checks without the daemon -> notify on change
```

- **States** follow PRD-health v4 section 2.4.
- **Notifications** fire on state changes and roll unresolved items into a daily digest, with quiet hours.
- **Federation** consults health before selecting sources and skips `down`, `rate_limited` and `budget_exhausted` sources (HLTH-FR-12).

**Milestones** (SPEC 14; PRD-health v4 2.11). `doctor` skeleton (`daemon_alive`, `keychain_readable`, `contact_email`, `schema_versions`): M0, unit M0-16 (HLTH-40). Health, credential and notify services, `ops_status`, `research://status`, `/api/status`, and the doctor checks that need no cache service (credentials, source probes, `terminal_notifier`, `launchd_jobs`): M1. The full `doctor` set with the cache-owned checks (`archive_target`, `archive_access`, `disk`, `review_overdue`, `backup_recent`): M2, because PRD-health v4 puts HLTH-41 in M2 (section 10, decision 7).

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

The machine-readable contract is [health status, doctor output and webhook payload v1](../contracts/health-status-and-webhook-v1.md): the `StatusReport`, `OpsSummary`, `DoctorReport` and webhook shapes, with their errors. It is a draft for the owner at Gate 3. The tables below say where each shape is implemented.

### 2.1 HTTP endpoints (SPEC-v2 10.5; HLTH-FR-43)

| Endpoint | Auth | Returns |
| --- | --- | --- |
| `/healthz` | none | `{"status":"ok","version":"3.x.y"}` |
| `/readyz` | none | 200 when the stores are open, the scheduler is running and the Keychain is readable; 503 with the failed check names otherwise |
| `/api/status` | bearer token or a UI session | `StatusReport`: sources, credential metadata, quotas, jobs, cache stats, disk, the archive target and the last 20 notifications |

`app.py` provides `build_app(settings, ...)` (LLD-platform v2 2.3), which mounts `/mcp`, `/ui`, `/healthz`, `/readyz` and `/api`. The one deny-by-default gate in `app.py` runs the bearer and Host/Origin checks; this component adds no authentication code (owner decision, 2026-10-22; LLD-security v2 4.3 E3, E4, E5). The handlers call `HealthService.ready()` and `HealthService.status_report()` (5.10).

### 2.2 MCP surface (SPEC-v2 7.2, 7.3; HLTH-FR-42)

| Tool | Signature (bounds) | Service | Annotations | M |
| --- | --- | --- | --- | --- |
| `ops_status` | none | health | read-only | M1 |

| Milestone | Resources |
| --- | --- |
| M0 | `research://sources` |
| M1 | `research://status` |

`ops_status` and `research://status` return `OpsSummary`: a summary with no secret and no fingerprint (HLTH-FR-42; HLTH-42). `research://sources` belongs to the sources component. Every tool carries `@tool_boundary`, which also redacts every string of a successful result (SEC-28 proposed in PRD-security v3; LLD-platform v2 4.5).

### 2.3 CLI (SPEC-v2 12.1)

| Command | Purpose |
| --- | --- |
| `doctor [--json] [--notify] [--quick] [--liveness]` | Run health checks (5.9). |

### 2.4 Webhook (SPEC-v2 10.4; HLTH-FR-32)

`POST notify.webhook_url` with JSON `{type, severity, subject, body, ui_path, ts}` and `Authorization: Bearer <NOTIFY_WEBHOOK_TOKEN>` when that Keychain item exists. The URL scheme is `https`, or `http` for a loopback host only (owner decision, 2026-10-22; 4, 7). The request is an `HttpClient` call (5.8).

### 2.5 macOS notification (SPEC-v2 10.4; HLTH-FR-32)

```
terminal-notifier -title "Research MCP" -subtitle <subject> -message <body>
                  -group research-mcp-<dedupe_key>
                  -execute "<venv>/bin/research-mcp ui --path <ui_path>"
```

The fallback is `osascript` (5.8). The argv is a list; no value passes through a shell except the `-execute` string, which is built as in 5.8.

### 2.6 Internal types (SPEC-v2 10.2)

```python
EventKind = Literal["source_down", "credential_invalid", "credential_expiring", "quota_low",
                    "source_deprecated", "disk_warning", "archive_unavailable", "review_batch_ready",
                    "keychain_locked", "daemon_down", "doctor_summary", "digest"]

@dataclass(frozen=True)
class HealthEvent:
    kind: EventKind
    subject: str
    severity: Literal["info", "warning", "critical"]
    ui_path: str | None
    dedupe_key: str
    body: str = ""            # added in v2: the webhook and the notification need a body
    urgent: bool = False      # added in v2: bypasses quiet hours (HLTH-FR-33)
    install_critical: bool = False  # installation integrity only: bypasses quiet hours; not a PRD severity level
```

`HealthService` emits it to `NotifyService.emit(event)`. The first five fields are SPEC-v2 10.2 unchanged. Other components raise the same event: the cache component raises `archive_unavailable` and `review_batch_ready` (`ui_path=/ui/review/<batch_id>`), and `DiskService` raises `disk_warning` through the state of the `disk` local target (5.6).

### 2.7 Shared models used by this component (SPEC-v2 4)

`AuthSpec`, `ProbeSpec`, `ProbeResult` and `CallRecord` are defined once, in the sources component's LLD ([LLD-sources v1](LLD-sources-v2.md) 2.1, 3.1) and `core/specs.py` and `core/models.py`; this component reads them and does not redefine them. What it relies on:

- `AuthSpec.secrets`, `required`, `origins`, `signup_url` and `validation`. The `validation` literal stays `"probe" | "github_rate_limit" | "header_expiry" | "none"`; the other methods of SPEC-v2 10.3 are classified as in 5.7 (decision 2 of section 10).
- `ProbeSpec(cadence_s, cost, description)` and `SourceSpec.probe`, `SourceSpec.shutdown_on`. Each adapter implements `async def probe(self) -> ProbeResult`.
- `ProbeResult(ok, latency_ms, shape_ok, detail_code, quota_remaining, credential_expires_at)`. `quota_remaining` is text in the form `<left>/<limit>`, or `<left>` when the limit is unknown. `detail_code` is a short code such as `auth_failed`, `API_KEY_INVALID`, `SERVICE_DISABLED`, `PERMISSION_DENIED`, `shape_changed` or `budget_exhausted`.
- `CallRecord` fields `rl_remaining` (same text form as `quota_remaining`), `rl_reset` and `cred_expires_at`. For a `rate_limited` or `budget_exhausted` record, `rl_reset` carries the end of the cool-off as an ISO 8601 UTC time, or whole seconds after `ts` [assumption: the platform LLD does not say how the retry time reaches the record; the HTTP client sets it when it fails a call for a `Retry-After` over 60 s, LLD-platform v2 6.1].

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

`state.db` (SQLite, WAL) in `~/Library/Application Support/research-mcp/`, backed up nightly with the last 7 kept (SPEC 10; LLD-platform v2 3.3). The migration `platform/migrations/state/0001_init.sql` is created by the platform component's unit M0-08 and holds this schema (SPEC-v2 10.1, verbatim; no migration exists in the repository yet):

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
  last_validated_at TEXT, last_result TEXT, state TEXT NOT NULL, last_used_at TEXT, updated_at TEXT NOT NULL,
  account TEXT);
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
  embeddings_bytes INTEGER, trash_bytes INTEGER, model_cache_bytes INTEGER, free_cache_vol INTEGER, free_archive_vol INTEGER);
CREATE TABLE maintenance_runs (ts TEXT NOT NULL, check_name TEXT NOT NULL, ok INTEGER NOT NULL, detail TEXT);
```

This version adds two columns, both inside the `0001_init` schema (no database exists yet, so no migration is needed): `credentials.account TEXT`, nullable, holds the Google sign-in account email and is null for Keychain items (owner decision, 2026-10-22; HLTH-FR-25; HLTH-INV-5); and `disk_samples.model_cache_bytes INTEGER`, the size of the embedding model cache (CACHE-FR-57). The cache LLD and this LLD both carry `model_cache_bytes`; it is part of the `0001_init` schema and the cache LLD's column list matches this one (owner decision, 2026-10-22). Is the email a secret? Under the SEC rules it is not: `Redactor` masks registered secret values and the PLAT-FR-13 patterns, and an account email is neither a Keychain value nor a credential. It is account metadata, so the UI Credentials page and `doctor` show it, redacted only where a PLAT-FR-13 pattern matches. It is never put in a notification, the webhook payload or a log line [design choice].

**Retention** (HLTH-FR-1; PRD-health v4 2.6): `calls` 30 days; `call_rollups` 13 months; `disk_samples` 90 days (pruned by `DiskService`, 5.6); `notifications`, `source_health` and `credentials` for the life of the install.

**Tables this component reads and writes.** `calls` (written through `StateStore.record_call`, LLD-platform v2 3.1), `call_rollups`, `source_health`, `credentials`, `notifications`, `schedule_runs` (probe and job due times) and `maintenance_runs` (the memory of `doctor --notify`, 5.9). It reads `disk_samples`, `jobs` and `review_batches`. The other tables serve the search, jobs and cache components.

**Column semantics fixed by this LLD** (the schema gives names and types only):

| Column | Meaning |
| --- | --- |
| `calls.ts`, every `*_at`, `*_until`, `hour` | ISO 8601 UTC text. `hour` is the start of the hour. |
| `calls.op` | The operation name; `probe` marks a health probe, so passive evidence ignores it (5.4). |
| `source_health.source` | A registry source id, or a local target id: `local_cache_db`, `local_embeddings`, `local_archive`, `local_disk` (5.6). |
| `source_health.state` | One of `disabled`, `unconfigured`, `down`, `credential_invalid`, `budget_exhausted`, `rate_limited`, `degraded`, `credential_expiring`, `deprecated`, `ok`. The parameters (until, reset, days) are derived from other columns, not stored. |
| `source_health.updated_at`, `credentials.updated_at` | The time the `state` last changed [inferred: the schema has no state-since column, and dedupe keys need the start of the current state, 5.8]. Probe and quota fields are updated without touching it. |
| `source_health.calls_today` | A cache of the number of calls of this source since local midnight, rebuilt from `calls` at start. It is the count against `sources.<id>.budget_cap` (decision 1 of section 10). |
| `source_health.quota_remaining`, `quota_reset` | `quota_remaining` is `<left>/<limit>` or `<left>`; `quota_reset` is an ISO time or the provider's text. |
| `credentials.service` | `research-mcp/<NAME>` for a Keychain item; `gcloud_adc` for the Google sign-in. |
| `credentials.required_by` | A JSON array of source ids. |
| `credentials.fingerprint` | First 8 hex characters of the SHA-256 of the value (HLTH-FR-20); never the value. |
| `credentials.last_result` | A short code (`ok`, `auth_failed`, `SERVICE_DISABLED`, and so on). |
| `credentials.state` | One of `ok`, `expiring_soon`, `invalid`, `missing`, `keychain_locked`, `quota_low`, `unknown_expiry`. The day count is derived. |
| `notifications.channels_json` | A JSON object `{"held": bool, "delivered": [channel names], "failed": [channel names]}`. The UI banner is not a channel entry; it reads the table (5.8). |
| `notifications.dedupe_key` | Built as in 5.8; identifies the notice for the life of its state. |
| `maintenance_runs` rows of this component | `check_name` is `doctor_notify:full` or `doctor_notify:liveness`; `ok` is 1 when nothing was wrong; `detail` is a hash of the failing check codes (5.9). |

**Requirement mapping.** `calls` columns hold the fields of HLTH-FR-1. `credentials` holds the metadata of HLTH-FR-20 and has no column that can hold a credential value (HLTH-INV-1; HLTH-43). `notifications.acknowledged_at` and `snoozed_until` hold the state of HLTH-FR-35. `notifications.dedupe_key` supports once-only delivery (HLTH-FR-30).

Migrations are forward-only; the pre-upgrade backup is what makes rollback possible (LLD-platform v2 5.9).

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

Reviewed by `security-reviewer` at Gate 3 (2026-10-23). The component-designer drafts only what the sources fix; the cross-cutting table is [LLD-security v2](LLD-security-v2.md) 4.3 (E3 to E5, E11, E15, E16, E21, E38, E41, E42).

| Point | Enforcement | Source |
| --- | --- | --- |
| `/healthz`, `/readyz` | No credential; the only unauthenticated paths; loopback only. They return no detail beyond the fixed shapes. | NFR-7; LLD-security v2 E4 |
| `/api/status` | Bearer token or a UI session, decided by the single gate in `app.py`; Host and Origin checked first. This component adds no check of its own. | Owner decision, 2026-10-22; LLD-security v2 E3, E5 |
| `ops_status`, `research://status`, `research://sources` | Read-only; `OpsSummary` has no secret and no fingerprint. Every string passes the `@tool_boundary` redaction. | HLTH-FR-42; SEC-28 (PRD-security v3; owner decision, 2026-10-22) |
| macOS notification click-through | The `ui` command mints its one-time login token when the notification is clicked, so no token sits in the notification, in a process argument list or in Notification Center. `ui_path` must match `^/ui/[A-Za-z0-9/_.\-]*$` (no query, no fragment); anything else is replaced by `/ui/`. The `-execute` string is built with `shlex.quote` on the path. `/ui/login` accepts `next` for `/ui/` paths only (SEC-29). | SPEC-v2 10.4; SEC-29; owner decision, 2026-10-22; LLD-security v2 E6, E11 |
| Webhook | An `HttpClient` request (a pseudo-source `notify_webhook`) whose `policy.hosts` and `policy.auth.origins` are exactly the origin of `notify.webhook_url`. Bearer placement from Keychain `NOTIFY_WEBHOOK_TOKEN`, revealed only in `platform/http.py`. Scheme: `https`, or `http` for a loopback host only (owner decision, 2026-10-22). No redirect to another origin. Settings reject a URL with credentials, a query or a fragment. | LLD-security v2 E21, E42; SEC-31; SEC-INV-3, SEC-INV-5 |
| Credential values | `Secret.reveal()` is called only in `platform/http.py`, `platform/mcp_client.py` and `platform/auth.py`. This component handles fingerprints, states and dates only. Its tables have no value column (HLTH-43). | SPEC-v2 3.1; SEC-INV-3; LLD-security v2 E16 |
| Keychain metadata | `SecretProvider.metadata` runs the same `security` command without `-w`; only the `mdat` attribute is parsed. | SEC-3; LLD-security v2 E15 |
| Google sign-in | The access token is held in memory and revealed only by `platform/http.py` for `https://discoveryengine.googleapis.com`. This component stores the account email (`credentials.account`) and token expiry only (HLTH-INV-5; owner decision, 2026-10-22) and never opens the credential file. | SEC-INV-11; LLD-security v2 E20 |
| Notification text | `NotifyService` passes subject and body once through `Redactor.redact` and then strips any URL query, before any channel (macOS, webhook, banner, digest) sees them. | HLTH-FR-34; LLD-security v2 E41 |
| Reload paths | `app.state.reload_credentials` (UI action and `SIGHUP`) calls `CredentialService.on_reload(names)`; only names and fingerprints are logged. | LLD-platform v2 5.10; LLD-security v2 E38 |
| `doctor` | Runs as the owner without the daemon token. It reads the Keychain through the same `KeychainProvider`, probes through the `HttpClient` and writes only to `state.db`. | HLTH-FR-40; SEC-INV-6 |

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

### 5.1 Modules (SPEC-v2 1; `sdd.config.json`)

| Module | Role in this component |
| --- | --- |
| `services/health.py` | `HealthService`; the pure function `evaluate_source`; probe scheduling; telemetry batches, rollups and pruning; local targets; `ready()`; `status_report()` and `ops_summary()` |
| `services/credentials.py` | `CredentialService`: credential states, validation, fix text, the reload port |
| `services/notify.py` | `NotifyService`: `emit`, channels, quiet hours, the digest, acknowledge and snooze, the banner feed |
| `services/disk.py` | `DiskService.sample()` writes `disk_samples` (cache LLD 5; the file is listed under health in `sdd.config.json`) |
| `services/doctor.py` | New in v2: `DoctorRunner` and the checks (5.9). Not yet in the health paths of `sdd.config.json`; the `planner` adds it (section 10, decision 11) |
| `cli.py` | `research-mcp doctor` argument parsing and output only |
| `app.py` | `/healthz`, `/readyz`, `/api/status` handlers that call the services |
| `mcp_app/tools_ops.py`, `mcp_app/resources.py` | `ops_status`; `research://status` and `research://sources` [inferred: the SPEC maps no tool to a file; both folders are in the search paths of `sdd.config.json`] |
| `platform/secrets.py` | `SecretProvider`, `SecretCache` (state, metadata, reload) |
| `platform/google_adc.py` | `GoogleAdcProvider` (Google sign-in) |
| `platform/http.py` | `CallSink` telemetry; header parsing for `rl_remaining`, `rl_reset`, `cred_expires_at` |
| `platform/scheduler.py` | `Scheduler`: probe intervals and the jobs in 7 |
| `packaging/launchd/` | `local.research-mcp-doctor.plist.template`, `local.research-mcp-watchdog.plist.template` (LLD-platform v2 2.5) |
| `testing/notifier.py`, `testing/launchctl.py`, `testing/clock.py` | Fakes for tests |

Modules stay under about 400 lines (SPEC 13). If `services/health.py` grows past that, `evaluate_source` and its input types move to `services/health_eval.py`, a pure module with no I/O.

### 5.2 Platform interfaces consumed

From LLD-platform v2 4.1 and 4.2 (SPEC-v2 3.1):

```python
class SecretState(StrEnum): OK="ok"; MISSING="missing"; LOCKED="keychain_locked"; ERROR="error"; INVALID="invalid"
# INVALID is returned only by GoogleAdcProvider (LLD-platform v2 4.1, decision 1)

class SecretProvider(Protocol):
    def get(self, ref: SecretRef) -> tuple[SecretState, Secret | None]: ...
    def metadata(self, ref: SecretRef) -> SecretMeta | None: ...   # no value
    def set(self, ref: SecretRef, value: str) -> None: ...

class SecretCache:           # implements CredentialResolver
    def load(self) -> None: ...
    def get(self, name: str) -> Secret | None: ...
    def state(self, name: str) -> SecretState: ...
    def reload(self) -> list[str]: ...      # names whose fingerprint changed

class GoogleAdcProvider:     # implements SecretProvider for backend "gcloud_adc"; extra gcp
    def get(self, ref): ...        # cached token; refresh when < 5 min left
    def metadata(self, ref): ...   # account email, token expiry; no token
```

`Secret.fingerprint` is `sha256(value)[:8]`. `SecretCache.reload` serves "Reload credentials" and `SIGHUP`; `app.state.reload_credentials` calls the port `credentials_changed(changed)` of this component (LLD-platform v2 5.10), which is `CredentialService.on_reload`.

**Dependencies the other LLDs must follow** (this LLD does not edit them):

- `SecretMeta` today has `name` and `modified_at`. HLTH-FR-25 and LLD-platform v2 4.2 need the Google sign-in's account email and token expiry from `metadata`. The platform LLD should add `account: str | None = None` and `expires_at: datetime | None = None` to `SecretMeta`; both stay `None` for Keychain items.
- The HTTP client sets `rl_reset` for a long `Retry-After` (2.7), and writes `rl_remaining` as `<left>/<limit>` when both rate-limit headers exist.
- The scheduler lists the jobs of section 7 that are new: `health_evaluate`, `health_rollup`, `credential_sync`, and one `probe:<source>` per source.

Carried from SPEC-v2 0.6 because health reads credential metadata through `SecretProvider.metadata`:

| Unit | Section | Requirement |
| --- | --- | --- |
| M0-05 | 3.1; AT-PLAT-12, AT-SEC-13 | `SecretRef` MUST validate on construction: the name matches the allowed pattern, and a Keychain reference's service is exactly `research-mcp/<NAME>`. No control character (in particular a newline) may reach the `security -i` script. `FakeProvider.metadata` MUST behave like `KeychainProvider.metadata` (no metadata for `env:` references). |

(SPEC-v2 0.6) No other 0.6 row concerns this component.

### 5.3 Telemetry, rollups and pruning (HLTH-FR-1; HLTH-1)

- Every attempt of the HTTP client produces a `CallRecord` for the `CallSink`. In the daemon the sink is `StateStore.record_call`, buffered and flushed every second (LLD-platform v2 5.3). After each flush the sink also calls `HealthService.on_calls(batch)`.
- `on_calls(batch)`: for each affected source it updates the in-memory counters (`calls_today`, last success time, `last_used` of each credential that source uses), copies `rl_remaining`/`rl_reset` of the newest record that has them into `quota_remaining`/`quota_reset`, applies `cred_expires_at` through `CredentialService.on_expiry_header`, sets `rate_limited_until` or `budget_reset_at` from a `rate_limited` or `budget_exhausted` record (5.5), then runs `evaluate(source)`. This is why a state change reaches the owner within seconds of the call, well inside HLTH-OUT-2.
- **Rollup.** The job `health_rollup` runs hourly at minute 5. For every completed hour not yet in `call_rollups` it writes one row per source: `calls`, `errors` (rows with a non-null `error_code`, except `not_found`, 5.5), and `p50_ms`, `p95_ms` by nearest rank over `latency_ms`. The write is `INSERT OR REPLACE`, so a repeat is harmless. It then recomputes `source_health.baseline_p95_ms` (5.5) and prunes: `calls` older than 30 days, `call_rollups` older than 13 months, never an hour that is not yet rolled up.
- Missed runs: the scheduler runs a missed job once at start or on wake (LLD-platform v2 5.5), and `health_rollup` fills every missing hour in that one run.

### 5.4 Probes (HLTH-FR-2, HLTH-FR-3, HLTH-FR-4; HLTH-2, HLTH-3)

- **Schedule.** One due time per enabled, configured source, kept in `schedule_runs` with `job = "probe:<source>"`. After a probe or a skip, `next_due_at = now + cadence_s * (1 + u)` with `u` drawn uniformly from 0 to 0.1 by an injected `random.Random` (0 to 10% jitter). The default cadence is `ProbeSpec.cadence_s` (3600 for free sources; 6 to 24 hours for metered ones, set by each `SourceSpec`).
- **Passive evidence first (HLTH-FR-4).** When a probe falls due, the service looks in `calls` for a record of this source with `op != "probe"`, a 2xx status and `ts` within the last `cadence_s`. If one exists the probe is skipped and rescheduled from now. Rationale for the window: it is the interval the probe would have covered.
- **Execution.** `adapter.probe()` runs through the same `HttpClient`, so it uses the same `TokenBucket` and `ConcurrencyGate` as real traffic (HLTH-FR-2). Its calls are recorded with `op="probe"`.
- **Result handling.** `ProbeResult` updates `source_health`: `last_probe_at`, `last_probe_ok = ok and shape_ok`, `consecutive_failures` (reset to 0 on success, plus 1 otherwise), `quota_remaining`, `api_version_seen` if the adapter reports one. A result with `shape_ok = False` is a failed probe even when `ok` is true: HTTP 200 with a changed format marks the source `down` at once (5.5; HLTH-FR-3, HLTH-3). `credential_expires_at` goes to `CredentialService.on_expiry_header`. A `detail_code` in the invalid set (5.7) goes to `CredentialService.on_auth_result`.
- **Cost classes.** `cost = "free"` probes run at their cadence. A `metered` probe with no free method runs at most once per 24 hours (Brave, Programmable Search; HLTH-25). The `web` group probes are in the table below (SPEC-v2 5.5):

| Source | Probe | Cadence |
| --- | --- | --- |
| `vertex_search` | Reads the engine metadata (free, no query cost) | 6 h |
| `brave_search` | One query, metered; the rate-limit headers are also parsed passively on every call | 24 h |
| `serpapi` | `GET https://serpapi.com/account.json` (free; gives searches left) | 6 h |
| `google_pse` | One query, metered; `shutdown_on = 2027-01-01` | 24 h |

- **Cap.** Every call to a web source counts against its cap (5.5). A probe that would be a metered query is skipped, not run, when the source is `budget_exhausted`.

### 5.5 Source state evaluation (HLTH-FR-10, HLTH-FR-11, HLTH-FR-12; HLTH-10, HLTH-11, HLTH-12)

`evaluate(source)` reads the inputs from the stores and calls the pure function:

```python
@dataclass(frozen=True)
class CallSummary: ts: datetime; status: int | None; error_code: str | None; latency_ms: int

@dataclass(frozen=True)
class EvalInputs:
    enabled: bool
    unconfigured_reason: str | None          # from SourceRegistry: missing credential, extra or contact
    last_calls: Sequence[CallSummary]        # newest first, at most 20, probes excluded
    calls_15m: Sequence[CallSummary]         # last 15 minutes, probes excluded
    consecutive_failures: int
    last_probe_shape_ok: bool | None
    rate_limited_until: datetime | None
    budget_reset_at: datetime | None
    calls_today: int
    budget_cap: int | None
    baseline_p95_ms: int | None
    quota_pct: float | None                  # from quota_remaining, when the limit is known
    required_credentials: Mapping[str, CredentialStateView]   # name -> state, days_left
    shutdown_on: date | None
    now: datetime

def evaluate_source(inp: EvalInputs) -> Evaluation: ...   # state, reason, fix_hint, until/reset/days
```

**Rules, most severe first; the first that applies wins** (the table in PRD-health v4 2.4):

| Order | State | Applies when |
| --- | --- | --- |
| 1 | `disabled` | `enabled` is false (`sources.<id>.enabled`, or the spec default). |
| 2 | `unconfigured` | `unconfigured_reason` is set: a required credential is `missing` or `keychain_locked`, a required extra is not installed, or the source needs the contact email and none is set. Shown neutral. |
| 3 | `down` | `consecutive_failures >= 3`; or `calls_15m` has at least 5 calls and all failed; or the last probe failed its shape check. |
| 4 | `credential_invalid` | A required credential (`AuthSpec.required`) is `invalid`. An invalid optional credential does not change the source state (the source runs keyless); the credential itself still notifies. |
| 5 | `budget_exhausted(reset)` | `budget_reset_at > now` (a provider budget response), or `budget_cap` is set and `calls_today >= budget_cap`, in which case `reset` is the next local midnight. |
| 6 | `rate_limited(until)` | `rate_limited_until > now`. |
| 7 | `degraded` | Error rate above 10% over `last_calls` (at least 5 calls); or the p95 of `last_calls` above 3 times `baseline_p95_ms`; or at least one 429 in `last_calls` whose wait was 60 s or less; or `quota_pct < 10`. |
| 8 | `credential_expiring(days)` | A required credential is `expiring_soon` (expiry or `rotate_by` within 14 days); `days` is the smallest. |
| 9 | `deprecated(days)` | `shutdown_on` is set; `days` is the days left. |
| 10 | `ok` | None of the above. |

Details the PRD leaves to design:

- An error is a call with a non-null `error_code`, except `not_found` (a missing record is not a failing source) [assumption]. The minimum of 5 calls for the degraded rules keeps one failed call from flapping the state [assumption].
- `baseline_p95_ms` is the median of the hourly `p95_ms` values over the 7 days ending one hour ago, and is `None` (the latency rule is off) with fewer than 24 rollup rows [assumption: SPEC-v2 says "the 7-day p95 baseline from the rollups" without a formula].
- **Clearing.** `rate_limited` and `budget_exhausted` clear when their time passes. `evaluate` is a function of `now`, so `HealthService.state(source)` is correct at read time (HLTH-12); the job `health_evaluate` (every 60 s) also re-runs it for every source, writes any change and emits the events.
- **Writes and events.** If the new state differs from `source_health.state`, the service writes the row (setting `updated_at`) and emits events by the rules of 5.8. The unchanged case writes only the probe and quota fields.
- **Local targets** use the same function with a smaller input (5.6).
- **Federation.** `HealthService.state(source)` is the call `SourceRegistry.select` makes; federation skips `down` and `rate_limited` with `skipped_unhealthy` and `budget_exhausted` with `budget_exhausted` (SRCH-FR-27; HLTH-FR-12). An explicit request for such a source tries it once (SRCH-FR-8).
- **Source detail (HLTH-FR-11).** `HealthService.detail(source)` returns the `SourceDetail` of the contract. `calls_24h`, `error_rate`, `p50_ms`, `p95_ms` and `last_error` are computed from `calls` over a rolling 24 hours (decision 4 of section 10); the state rules use the windows above, which are different.

### 5.6 Local targets (HLTH-FR-5; HLTH-4, HLTH-44)

`HealthService` probes four local targets every 15 minutes (the cadence of `disk_sample`) and writes each as a `source_health` row with the ids of section 3. They are not registry sources: `research://sources` does not list them, and `StatusReport.local_targets` does.

| Target | Probe | States |
| --- | --- | --- |
| `local_cache_db` | Opens a read connection to `cache.db` and runs `SELECT 1`; reads `PRAGMA user_version` | `ok`; `down` when it cannot open or the version is newer than the code |
| `local_embeddings` | The `embeddings` extra imports (`importlib.util.find_spec("fastembed")`) and the model folder `paths.model_cache_dir` holds files. It loads no model and embeds nothing [assumption: a lightweight probe; the embedding service arrives in M2] | `ok`; `unconfigured` when the extra is not installed; `down` when the extra is installed and the model files are absent |
| `local_archive` | `ArchiveService` target check: the confirmed folder is available (CACHE-FR-45) | `ok`; `degraded` while the local fallback is in use; `down` when unavailable; `unconfigured` before the owner confirms the target |
| `local_disk` | Reads the latest `disk_samples` row. Warn when `cache_bytes > disk.cache_warn_bytes` or a free figure is below `disk.free_warn_bytes`; `down` when a free figure is below `disk.free_crit_bytes` (never `install_critical`; owner decision, 2026-10-22) | `ok`; `degraded` (warn); `down` (below the crit figure) |

`ArchiveService` and `DiskService` are the cache component's and health's services (`sdd.config.json`); until they exist (M2), `HealthService` is given `None` for their ports and reports `local_archive` and `local_disk` as `unconfigured`. This keeps HLTH-4 testable at M1 with fakes. A transition to `degraded` or `down` of `local_disk` raises `disk_warning`; of `local_archive` to `down`, `archive_unavailable` (HLTH-FR-30). `DiskService.sample()` also prunes `disk_samples` older than 90 days.

### 5.7 Credentials (HLTH-FR-20 to HLTH-FR-25; HLTH-13, HLTH-20 to HLTH-25, HLTH-43)

`CredentialService` (`services/credentials.py`; the class name is new, SPEC-v2 names none, decision 10 of section 10):

```python
class CredentialService:
    def __init__(self, store: StateStore, secrets: SecretCache, provider: SecretProvider,
                 registry: SourceRegistry, clock: Clock, settings: Settings,
                 reload: Callable[[], Awaitable[list[str]]], emit: Callable[[HealthEvent], Awaitable[None]]): ...
    async def sync(self) -> None                       # job credential_sync, hourly and at start
    async def on_reload(self, changed: list[str]) -> None   # the port credentials_changed
    async def on_expiry_header(self, name: str, expires_at: datetime) -> None
    async def on_auth_result(self, name: str, detail_code: str | None, ok: bool) -> None
    def evaluate(self, name: str) -> CredentialStateView
    def fix_text(self, name: str) -> FixText
```

**What is stored.** One `credentials` row per name in the registry's credential map (every `AuthSpec.secrets`, plus `GOOGLE_SIGNIN`): name, service, `required_by`, `fingerprint`, `keychain_modified_at`, `expires_at`, `rotate_by`, `last_validated_at`, `last_result`, `state`, `last_used_at`, `updated_at`, and `account` (the Google sign-in email, null otherwise; shown in the UI and by `doctor`; owner decision, 2026-10-22). No value, and no column that could hold one (HLTH-FR-20; HLTH-43). The fingerprint comes from `Secret.fingerprint`; `keychain_modified_at` from `SecretProvider.metadata`.

**Credential states, most severe first** (PRD-health v4 2.4):

| Order | State | Applies when |
| --- | --- | --- |
| 1 | `keychain_locked` | Any Keychain read gave `keychain_locked` (below). Applies to every credential at once. |
| 2 | `missing` | `SecretCache.state` is `MISSING`, or `GoogleAdcProvider` found no sign-in. |
| 3 | `invalid` | The last validation or call failed authentication (below). |
| 4 | `expiring_soon(days)` | The effective expiry is within 14 days. `days` is 14 or fewer; row severity is `warning`, and `critical` at 3 days or fewer (PRD-health v4 2.4; owner decision, 2026-10-22). This is row severity, not `install_critical` (5.8). |
| 5 | `quota_low(pct)` | The quota of a source that uses it is below 10% (`<left>/<limit>` known). |
| 6 | `unknown_expiry` | Valid, but the provider exposes no expiry and `rotate_by` is more than 14 days away. |
| 7 | `ok` | Validated within its cadence, with an expiry more than 14 days away. |

The effective expiry is the provider's `expires_at` when known, else `rotate_by`. A Google sign-in is never `expiring_soon`: its token renews itself, so the stored token expiry is shown and ignored by the rule (HLTH-FR-25; HLTH-24).

**`keychain_locked` (HLTH-13).** `sync()` reads one reference with `provider.get` (the `DAEMON_TOKEN` item) once an hour and `SecretCache.state` for the rest. If any read gives `LOCKED`, every credential gets `keychain_locked` and exactly one `HealthEvent(kind="keychain_locked", dedupe_key="keychain_locked:<since>")` is emitted. While it holds, no per-credential event is emitted. Sources whose required credential cannot be read show `unconfigured` with the reason `keychain_locked`, not `credential_invalid` [assumption]. When the Keychain reads again, `sync()` calls `reload()` so the daemon has the values, then re-evaluates.

**Validation methods** (SPEC-v2 10.3):

| Credential | Method | Classified by |
| --- | --- | --- |
| GitHub | `AuthSpec.validation = "github_rate_limit"`: the source probe calls `GET https://api.github.com/rate_limit` (free). A 401 is `invalid`. `resources.*.remaining` and `limit` give the quota; the header `github-authentication-token-expiration` gives the expiry. Also `"header_expiry"` behavior: the header is parsed on every authenticated call (`CallRecord.cred_expires_at`). | HLTH-21 |
| Google API key | The `google_devknowledge` probe `GET https://developerknowledge.googleapis.com/v1/documents:searchDocumentChunks?query=documentation&pageSize=1` with the key in `x-goog-api-key`. `API_KEY_INVALID` and `SERVICE_DISABLED` map to `invalid`. `GOOGLE_DEVKNOWLEDGE_API_KEY` also serves `google_pse`, whose own probe is metered (5.4). `validation = "probe"` | HLTH-20 |
| Google sign-in (`google_adc`, M1) | `GoogleAdcProvider` refreshes the token (free), then the Vertex probe reads the engine metadata (free). `missing`: no sign-in found. `invalid`: refresh refused (`SecretState.INVALID`), `SERVICE_DISABLED`, or `PERMISSION_DENIED` on the engine; the reason is kept in `last_result`. This credential has `AuthSpec.secrets = ()` on the Vertex spec; the credential service maps it by the `gcloud_adc` reference. | HLTH-24 |
| SerpAPI | `validation = "probe"`; the probe is `GET https://serpapi.com/account.json` (free). 401 is `invalid`; searches left set `quota_low`. | HLTH-25 |
| Brave | `validation = "probe"` with a metered one-per-24-hour probe; the rate-limit headers on each call set the quota passively; 401 or 403 on a call is `invalid`. | HLTH-25 |
| Programmable Search | Shares the Google API key; its own probe is metered, one per 24 hours. | HLTH-25 |
| Any other credential | `validation = "probe"`: the source probe with credentials attached; an authentication failure is `invalid`. `"none"`: no validation beyond presence. | HLTH-20 |
| No expiry exposed | `rotate_by = keychain_modified_at + 180 days` unless `credentials.<NAME>.rotate_by` is set (HLTH-FR-22; HLTH-22). Clearing the override on the Credentials page restores the default [assumption: "change or clear" is read as returning to the default]. | HLTH-22 |

The `validation` literal does not grow (decision 2 of section 10). `invalid` is set by `on_auth_result` when `detail_code` or the call's `error_code` is in `{auth_failed, API_KEY_INVALID, SERVICE_DISABLED, PERMISSION_DENIED, invalid_grant}` for a source that attaches this credential; the code is kept in `last_result`. A later successful probe or 2xx call with the credential sets `last_validated_at`, `last_result = "ok"` and clears `invalid`. **No billed query is spent to validate when a free method exists** (HLTH-INV-4; HLTH-25): Vertex and SerpAPI validate through free calls; only Brave and Programmable Search, which have none, use a metered probe, at most once per 24 hours.

**Reload (HLTH-FR-23).** `on_reload(changed)` receives the names whose fingerprint changed, from the UI action or `SIGHUP`. For each it stores the new `fingerprint` and `keychain_modified_at`, logs the name and the new fingerprint (never a value), clears `last_result`, and runs `HealthService.run_probe` for the sources that use it, so the state returns to `ok` or `invalid` within seconds. The criterion that checks `reload` is SEC-4.

**Expiry milestones** (HLTH-FR-30). With `days_left = ceil((effective_expiry - now) / 1 day)`, the milestone is the smallest of 14, 7, 3, 1 that is at least `days_left`. A milestone event is emitted when `days_left` is 14 or fewer and its dedupe key is new. A credential first seen at 2 days therefore notifies once, at milestone 3, not three times.

**Fix text** (HLTH-FR-24; HLTH-23). `fix_text(name)` returns the Keychain item `research-mcp/<NAME>`, the provider key page (`AuthSpec.signup_url` of the first source that uses the credential) and the command `security add-generic-password -U -s research-mcp/<NAME> -a "$USER" -w` with no value. For the Google sign-in it returns `gcloud auth application-default login` and, for a permission problem, the engine's console page; that URL has no query and is built by the Vertex adapter's instance settings [assumption: the sources LLD owns the engine fields; this LLD only passes the URL through].

### 5.8 Notifications (HLTH-FR-30 to HLTH-FR-35; HLTH-30 to HLTH-35)

**Triggers** are exactly the list in HLTH-FR-30; a rate limit or an exhausted budget is not a trigger (decision 8 of section 10):

| Trigger | `EventKind` | When | Dedupe key |
| --- | --- | --- | --- |
| A source becomes `down` | `source_down` | State change | `source_down:<source>:<since>` |
| A credential becomes `invalid` | `credential_invalid` | State change | `credential_invalid:<NAME>:<since>` |
| A credential reaches 14, 7, 3, 1 days | `credential_expiring` | Milestone (5.7) | `credential_expiring:<NAME>:<expiry date>:<milestone>` |
| `quota_low` | `quota_low` | State change | `quota_low:<source>:<quota_reset or since>` |
| A source is `deprecated` at 60, 30, 7 days | `source_deprecated` | Milestone, same rule as expiry | `source_deprecated:<source>:<shutdown_on>:<milestone>` |
| A disk warning | `disk_warning` | `local_disk` leaves `ok` | `disk_warning:<since>` |
| The archive folder becomes unavailable | `archive_unavailable` | `local_archive` becomes `down` | `archive_unavailable:<since>` |
| A cache review batch is ready | `review_batch_ready` | Raised by the cache component | `review_batch_ready:<batch_id>` |
| The Keychain is locked | `keychain_locked` | 5.7 | `keychain_locked:<since>` |
| The daemon is dead | `daemon_down` | Raised by `doctor` | `daemon_down:<hash>` (5.9) |

`<since>` is the compact form of `updated_at` of the row, the time the state began. A new episode has a new `since` and a new key, so a repeat of the same state never notifies twice and a recurrence does (HLTH-30).

**`NotifyService.emit(event)`**, in order:

1. Redact: `subject` and `body` pass once through `Redactor.redact`, then any URL in them is cut at `?` or `#` (HLTH-FR-34; HLTH-INV-2).
2. Dedupe: if a `notifications` row with this `dedupe_key` exists, stop. Nothing is stored or sent.
3. Quiet hours: if the time is inside `notify.quiet_hours` and the event is not `install_critical` and not `urgent`, store the row with `channels_json = {"held": true, ...}` and stop. The digest delivers it (HLTH-FR-33).
4. Deliver to the channels: macOS (if `notify.macos`), then the webhook (if `notify.webhook_url`). A channel failure is logged by code and recorded in `channels_json`; it never raises into the caller.
5. Store the row (`notification_id` a ULID) with `ack` and `snooze` empty.

**Two severity meanings (owner decision, 2026-10-22; PRD-health v4 2.4 stands).** (1) `severity` on a status row, notification, webhook body and digest line keeps the PRD levels: for example `expiring_soon` is `warning` at 14 days and `critical` at 3 days or fewer; `credential_invalid` and `down` follow the PRD table. The UI, the status tool and the morning digest use these. `review_batch_ready` and `digest` are `info`. (2) `install_critical` is a separate boolean on `HealthEvent` and a check status in `doctor`. It means installation integrity only: a broken install (the dead daemon or a missing launchd job), an unreadable database and a failed migration. Only `install_critical` and `urgent` bypass quiet hours; only `install_critical` sets the `doctor` exit code and the upgrade rollback. A credential `critical` by row severity is held in quiet hours like any other, except an `invalid` credential used in the last hour (`credentials.last_used_at`), which is emitted with `urgent=True` (HLTH-FR-33; HLTH-33).

**Quiet hours.** `notify.quiet_hours` is `"HH:MM-HH:MM"` in local time and may cross midnight (default `21:00-08:00`). Equal start and end means no quiet hours [assumption]. The time is read from the injected `Clock` and converted with the local zone given to `NotifyService`, so tests can fix it.

**Digest (HLTH-FR-31).** The scheduler job `digest` runs at 08:00 local time. It builds one `digest` event from: held notifications, and unresolved items (sources not `ok`, `disabled` or `unconfigured`; credentials not `ok` or `unknown_expiry`; local targets not `ok`), minus acknowledged and snoozed ones. It lists at most 20 lines. It is sent even if the quiet window is still open, because it is the morning delivery. If nothing is unresolved and nothing is held, no digest is sent. Dedupe key `digest:<local date>`. After sending, held rows get `held: false`.

**Resolved and the banner (HLTH-FR-32).** A notification is *active* while its condition holds: `HealthService.active_keys()` rebuilds the dedupe keys of current states from `source_health`, `credentials` and the local targets (the keys are deterministic, above). `NotifyService.banners()` returns rows that are active, not acknowledged and not snoozed; the UI banner slot calls it (decision 6 of section 10). No column is added.

**Acknowledge and snooze (HLTH-FR-35).** `acknowledge(notification_id)` sets `acknowledged_at`. `snooze(notification_id, days)` sets `snoozed_until = now + days` for 1 to 30 days [assumption: the sources say "N days" and no bound]. Both are UI actions (a POST with CSRF); neither is an MCP tool. Acknowledged and snoozed rows are left out of the banner and the digest.

**macOS (HLTH-32).** If `terminal-notifier` is found (`shutil.which`), the argv is the list of 2.5, with `-group research-mcp-<dedupe_key>` and `-execute` set to `"<venv>/bin/research-mcp ui --path " + shlex.quote(ui_path)`. `ui_path` is checked against the allow-list pattern of section 4. Subject and body are separate argv elements. No login token appears in any argument; the `ui` command mints it at click time (UI-FR-2). If the tool is absent, the fallback is `osascript` with the text passed as arguments to a fixed script, not spliced into it:

```
osascript -e 'on run argv' -e 'display notification (item 2 of argv) with title "Research MCP" subtitle (item 1 of argv)' -e 'end run' <subject> <body>
```

It cannot be clicked through. SPEC-v2 writes `osascript -e 'display notification ...'`; passing the text as arguments is the same call without a quoting hazard. `doctor` reports whether `terminal-notifier` is installed (`terminal_notifier`).

**Webhook (HLTH-FR-32).** The payload is the contract's. The call is `HttpClient.post_json(url, source="notify_webhook", json=payload)`. The pseudo-source's policy is built from `notify.webhook_url`: `hosts` and `auth.origins` are its origin, `auth = AuthSpec(("NOTIFY_WEBHOOK_TOKEN",), required=False, placement="bearer", ...)`, `timeout_s = 5.0`. The client's three attempts are the "at most 2 retries" of SPEC-v2 10.4. The token goes in the header and never in the URL. `notify_webhook` rows are excluded from source evaluation.

### 5.9 `doctor` (HLTH-FR-40, HLTH-FR-41; HLTH-40, HLTH-41)

`research-mcp doctor [--json] [--notify] [--quick] [--liveness]` runs without the daemon. `DoctorRunner` in `services/doctor.py` loads `Settings` itself, builds a `KeychainProvider`, an `HttpClient` and the registry, opens `state.db` with the 5 s busy timeout and no migration, and runs the checks. A settings validation error does not abort it: it becomes the `contact_email` or a `settings` check result.

| Check | What it verifies | M |
| --- | --- | --- |
| `daemon_alive` | `GET /healthz` answers within 3 s. | M0 |
| `keychain_readable` | The Keychain can be read and is not locked. | M0 |
| `contact_email` | A contact email is set and is not a placeholder. Unset: `warning` (only `needs_contact` sources are `unconfigured`). Placeholder: `install_critical`, because the daemon does not start. | M0 |
| `schema_versions` | `state.db` and `cache.db` open for reading, and `PRAGMA user_version` equals the newest migration of the code. Unreadable database (`db_unreadable`) or a failed migration (`migration_failed`): `install_critical`. | M0 |
| one `credential:<NAME>` per credential | The credential's current state and fix text. | M1 |
| one `probe:<source>` per enabled source | The source responds; with `--quick`, only free probes run. Local targets are included. | M1 |
| `terminal_notifier` | terminal-notifier is installed. | M1 |
| `launchd_jobs` | `launchctl print gui/$UID/local.research-mcpd` and the other two jobs, through `LaunchctlPort`. | M1 |
| `archive_target`, `archive_access` | The archive folder is available; TCC access is granted. `archive_access` writes and removes the sentinel `.research-mcp-probe` and reports `tcc_denied` with the fix: grant the daemon's interpreter Files and Folders access to Google Drive in System Settings, Privacy & Security. | M2 |
| `disk` | Disk thresholds (5.6). | M2 |
| `review_overdue` | No review missed by more than 24 hours. | M2 |
| `backup_recent` | A backup ran in the last 48 hours. | M2 |

- **Each check** returns `{name, status, code, detail, fix}` with `status` one of `ok`, `warning`, `install_critical`; the codes and fix text are fixed strings with no secret and no URL query.
- **`--liveness`** runs only `daemon_alive` and `keychain_readable` and finishes in well under 10 s (3 s for the HTTP check, 5 s for the Keychain read).
- **`--quick`** skips metered probes. The upgrade command runs `doctor --quick --json` (LLD-platform v2 5.9), so an upgrade spends no billed query (HLTH-INV-4).
- **Exit code:** 0 when no check is `install_critical`, otherwise 1. `install_critical` means installation integrity only (owner decision, 2026-10-22): `daemon_alive`, the `contact_email` placeholder, `schema_versions` (unreadable database or failed migration) and `launchd_jobs` with a missing job. Everything else is at most `warning`: `keychain_readable`, credentials, source probes (outages), `archive_access` with `tcc_denied`, `disk`, `review_overdue`, `backup_recent` and `terminal_notifier`. An expired key or a source outage never rolls back an upgrade (LLD-platform v2 5.9).
- **`--notify` (HLTH-41).** After the run, compute `h = sha256(sorted "name:status:code" of every non-ok check)[:12]` and read the last `maintenance_runs` row with `check_name = doctor_notify:full` (or `:liveness`). If the result has a problem and `h` differs from that row's `detail`, send one `doctor_summary` event (or `daemon_down` when `daemon_alive` failed; `dedupe_key = doctor:<mode>:<h>`, `install_critical=True` for `daemon_down`; `doctor_summary` sets it only when a check is `install_critical`) through `NotifyService`, which writes `notifications` directly because the daemon may be dead. Then write the new `maintenance_runs` row. If the result is all ok, write the row with `ok = 1` and send nothing. Same result twice: no second notice.
- **Watchdog (HLTH-FR-41).** launchd runs `doctor --liveness --notify` every 900 s and `doctor --notify` at 08:52 (LLD-platform v2 2.5). The dead-daemon notice is `install_critical` and bypasses quiet hours, so it reaches the owner within one watchdog interval of the daemon dying (HLTH-OUT-3; NFR-12).

### 5.10 Readiness and status (HLTH-FR-42, HLTH-FR-43; HLTH-42)

- `HealthService.ready() -> ReadyReport(stores, scheduler, keychain)` is cheap: `stores` pings both databases, `scheduler` checks the scheduler's last tick is under 3 minutes old, `keychain` is the result cached by `credential_sync` and each reload, not a new `security` call per request.
- `status_report()` builds the `StatusReport`; `ops_summary()` builds `OpsSummary` from the same data. Both read the stores and the in-memory state; neither calls an upstream or the Keychain.
- Both are passed through the redaction of the `@tool_boundary` (tools) or the response path (`/api/status`) before leaving the process.

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

| Situation | Handling | Source |
| --- | --- | --- |
| 429 with `Retry-After` over 60 s | The call is not waited for; it fails with `rate_limited` and `retry_after_ms`, and the record's `rl_reset` sets `rate_limited_until` | LLD-platform v2 6.1; HLTH-12 |
| 429 with a short wait | Retried by the client; each 429 attempt is a record and counts toward `degraded` | LLD-platform v2 6.1; 5.5 |
| Budget responses | `policy.error_classifier` maps them (OpenAlex "Insufficient budget" 429 to `budget_exhausted`, `detail="daily budget"`), which sets `budget_reset_at`; with no reset time the next local midnight is used [assumption] | LLD-platform v2 6.1 |
| Daily cap reached | `calls_today >= budget_cap` gives `budget_exhausted(reset=next local midnight)` | SRC-29; 5.5 |
| Keychain read | 5 s timeout; exit 44 is `missing`; exit 36 or 51, or "User interaction is not allowed", is `keychain_locked`; anything else is `error`; stderr text is never logged or returned | LLD-platform v2 4.1 |
| Google sign-in | `DefaultCredentialsError` is `missing`; `RefreshError` is `SecretState.INVALID`, shown as `invalid`; the exception text is never logged or returned | LLD-platform v2 4.2; HLTH-24 |
| A probe raises or times out | Recorded as a failed probe (`consecutive_failures + 1`) with `detail_code = "error"`; the exception text is never stored | 5.4 |
| Probe shape changed | `shape_ok = False` is a failed probe; the source is `down` at once | HLTH-3 |
| Webhook delivery | Timeout 5 s, at most 2 retries (3 attempts), failure logged by code, recorded in `channels_json`; the notification is still stored and shown in the UI | SPEC-v2 10.4; 5.8 |
| macOS notification fails | `terminal-notifier` exit code non-zero: logged by code; the `osascript` fallback is tried once | 5.8 |
| Repeated events | `NotifyService.emit` stops when the `dedupe_key` exists; a recurrence has a new `since` and so a new key | SPEC-v2 10.4; 5.8 |
| Repeated `doctor --notify` | One summary only when the result hash changed since the last notify; a recovery writes the row and sends nothing | SPEC-v2 10.5; 5.9 |
| Missed schedules (Mac asleep, daemon down) | The wall-clock `Scheduler` runs a missed job once at start or on wake, never once per missed day; `health_rollup` fills every missing hour in that one run | LLD-platform v2 5.5 |
| Locked Keychain at start | Credentials show `keychain_locked`; one notice; sources that need them are `unconfigured` with that reason; recovery reloads | 5.7 |
| Reload while the Keychain is locked | The cache keeps the previous values and reports the new state | LLD-platform v2 4.1 |
| Readiness failure | `/readyz` returns 503 with the failed check names | 5.10 |
| `doctor` exit | 0 when no check is `install_critical`, else 1 | 5.9 |
| Telemetry | Every attempt produces a `CallRecord`; the sink is non-blocking, buffered and flushed every second; a failed flush is retried and logged without row content | LLD-platform v2 5.3 |
| State database busy | `busy_timeout=5000`; `doctor` reports `warning` with a code if it cannot write its notification | LLD-platform v2 3.1 |

**Idempotency.** `health_rollup` is `INSERT OR REPLACE` per hour and source. `evaluate` is a pure function of its inputs and `now`; running it twice writes nothing the second time. Probe due times in `schedule_runs` survive a restart. `emit` is idempotent per `dedupe_key`. `sync()` and `on_reload` can be repeated without a state change when nothing changed.

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

Settings keys. The authoritative table is [LLD-platform v2](LLD-platform-v2.md) 7.1; this component adds no key. Rows it reads:

| Key | Default | Notes |
| --- | --- | --- |
| `notify.macos` | `true` | `terminal-notifier` if present, else `osascript` (no click-through) |
| `notify.webhook_url` | none | OpenClaw inbox (O5 closed, PRD-v7 1.6). `https`, or `http` for a loopback host only (owner decision, 2026-10-22). Any token goes in Keychain `NOTIFY_WEBHOOK_TOKEN`, never in the URL; a URL with credentials, a query or a fragment is rejected |
| `notify.quiet_hours` | `"21:00-08:00"` | Equal start and end means none (5.8) |
| `contact.email` | none | A placeholder (`example.com`, `example.org`, `test`, `invalid`, and subdomains) is a settings error and the daemon does not start; if unset, only `needs_contact` sources are `unconfigured` and the daemon starts (SRC-FR-24; PLAT-11) (owner decision, 2026-10-22) |
| `disk.cache_warn_bytes` | `5368709120` | |
| `disk.free_warn_bytes` / `free_crit_bytes` | `16106127360` / `5368709120` | |
| `sources.<id>.enabled` | spec default | |
| `sources.<id>.budget_cap` | none (`100` for `web` sources) | Daily call cap for metered sources; resets at local midnight; the count is `source_health.calls_today` |
| `credentials.<NAME>.rotate_by` | none | Optional override; clearing it restores the 180 day default |
| `paths.model_cache_dir` | `~/Library/Caches/research-mcp/models` | Read by the embeddings local target |

**Scheduler jobs** (wall clock; LLD-platform v2 5.5). `digest` at 08:00 local time. Interval jobs this component needs: probes at their own cadence (`probe:<source>`); local target probes every 15 minutes; `health_evaluate` every 60 s; `health_rollup` hourly at minute 5; `credential_sync` hourly and at start. The last three and the probe jobs are not in the platform list yet (5.2).

**Feature flags.** No feature-flag PRD exists in this repository, so no registration rule applies; this table follows the platform LLD's list of optional behavior (LLD-platform v2 7.2). Every optional behavior of this component is covered by an existing key; none is added. All are safe to switch off: no data is lost, the MCP tool list does not change, and hooks and the daemon still start.

| Flag | Default | Safe to switch off? |
| --- | --- | --- |
| `notify.macos` | `true` | Yes, with one cost (LLD-platform v2 7.2). Off: no macOS notification. Notices are still stored (HLTH-FR-35), shown in the UI banner and sent to the webhook if set. The cost: the dead-daemon notice then reaches the owner only through the webhook, because the UI is down with the daemon; `doctor` still prints it. |
| `notify.webhook_url` | none (channel off) | Yes: the macOS notification and the UI banner remain; nothing is queued for the webhook. |
| `notify.quiet_hours` | `"21:00-08:00"` | Yes: set equal start and end to switch it off; all notices are then delivered at once. |
| `sources.<id>.enabled` | spec default; every `web` source is off until configured (ADR 0012) | Yes for the source: it shows `disabled`, its probes stop and no state or credential event is raised for it. |
| `sources.<id>.budget_cap` | none (`100` for `web` sources) | Yes: unset on a non-web source means no cap and no `budget_exhausted` from the cap; a provider budget response still sets the state. |
| `credentials.<NAME>.rotate_by` | none | Yes: it is an override; without it the 180 day default applies. |

The metered probes (Brave, Programmable Search) run only while their source is enabled and configured, which `sources.<id>.enabled` switches off.

## 8. Observability

> **Owner:** A · **Persona:** `sre`

Reviewed by `sre` at Gate 3 (2026-10-23) against SPEC-v5 12, PRD-v8 OUT-4 and NFR-12, and consistent with LLD-platform v2 8; not approved. The thresholds below trace to HLTH requirements and PRD-v8 outcomes; no NFR gives a numeric alert threshold except the 15-minute dead-daemon report (NFR-12; OUT-4). The state rules are in the state table of the evaluation section; this table only restates them.

| Signal | Where | Threshold or use | Traces to |
| --- | --- | --- | --- |
| Call telemetry | `calls`, `call_rollups` | Error rate above 10% over `last_calls` (at least 5 calls), or p95 above 3 times the 7-day baseline, gives `degraded`; at least 5 calls in 15 minutes that all failed gives `down` (state table, rows 3 and 7) | HLTH-FR-1, HLTH-FR-10 |
| Probe results | `source_health.last_probe_at`, `last_probe_ok`, `consecutive_failures` | 3 failed probes in a row, or a failed shape check, gives `down` | HLTH-FR-3, HLTH-FR-10; HLTH-OUT-1 |
| Credential state | `credentials` | 14, 7, 3 and 1 days before expiry; quota below 10%; invalid within one probe cycle | HLTH-FR-30; HLTH-OUT-4, HLTH-OUT-5, HLTH-OUT-7 |
| Notifications | `notifications`; last 20 in `/api/status` | A state change reaches the owner within 15 minutes outside quiet hours; the query is the time from `source_health.updated_at` to the `notifications.ts` of the matching key | HLTH-OUT-2 |
| Watchdog | `local.research-mcp-watchdog`, every 900 s; `maintenance_runs` rows `doctor_notify:liveness` | A dead daemon is reported within 15 minutes | HLTH-OUT-3; NFR-12 |
| Missed notices | `notifications` against `calls` | For each source state change, the first failed agent call to that source compared with the notice time | HLTH-OUT-6 |
| Logs | `log_dir/research-mcp.jsonl`, JSON lines through `RedactingFilter`, with `correlation_id` per call and job | Recent warnings and errors shown in the UI; this component logs names, codes and fingerprints, never values or exception text | LLD-platform v2 4.3 |
| Status | `/healthz`, `/readyz`, `/api/status`, `ops_status`, `research://status` | No threshold; there is no uptime or response-time target (NFR-12) | HLTH-FR-42, HLTH-FR-43 |

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

Reviewed by `test-architect` at Gate 3 (2026-10-23). Planned files follow [test plan v4](../test/test-plan-v4.md) 2.6, which names a file only for HLTH-43 and HLTH-44; for the rest the file is chosen by best fit [inferred]. No test in `tests/` cites an HLTH criterion yet. Integration tests use the fakes in `research_mcp.testing` (`FakeProvider`, `FakeClock`, `FakeSleeper`, a fake `launchctl`, a fake notifier) and a blocked network. New tests cite their criterion with `@spec` (AGENTS.md).

| Criterion | Planned tests | Level | Status |
| --- | --- | --- | --- |
| HLTH-40 | `tests/unit/test_cli.py::test_doctor_skeleton_runs_four_checks`, `test_liveness_runs_two_checks`, `test_json_output`, `test_exit_code_reflects_install_critical`, `test_only_installation_integrity_is_install_critical` (a down source, an invalid key, an expiry within 3 days and a full disk exit 0), `test_install_critical_fails_upgrade_check` (owner decision, 2026-10-22) | unit | planned |
| HLTH-1 | `tests/services/test_health.py::test_calls_rollups_and_pruning` | integration | planned |
| HLTH-2 | `tests/services/test_health.py::test_probe_cadence_jitter_and_passive_skip` | integration | planned |
| HLTH-3 | `tests/services/test_health.py::test_probe_shape_change_marks_down` | integration | planned |
| HLTH-4 | `tests/services/test_health.py::test_probes_local_targets` | integration | planned |
| HLTH-44 | `tests/services/test_health.py::test_probes_embeddings_local_target` (named in test plan v4) | integration | planned |
| HLTH-10 | `tests/unit/services/test_health_eval.py::test_each_rule_produces_its_state`, `test_worst_state_wins` | unit | planned |
| HLTH-12 | `tests/unit/services/test_health_eval.py::test_rate_limited_and_budget_clear_at_their_time` | unit | planned |
| HLTH-13 | `tests/unit/services/test_credentials.py::test_locked_keychain_gives_one_notification` | unit | planned |
| HLTH-11 | `tests/services/test_health.py::test_source_detail_has_every_field` | integration | planned |
| HLTH-20 | `tests/unit/services/test_credentials.py::test_credential_states_from_fixtures` | unit | planned |
| HLTH-21 | `tests/services/test_credentials.py::test_github_expiry_header_and_rate_limit_update` | integration | planned |
| HLTH-22 | `tests/unit/services/test_credentials.py::test_rotate_by_default_and_override` | unit | planned |
| HLTH-23 | `tests/unit/services/test_credentials.py::test_fix_text_names_item_page_and_value_free_command` | unit | planned |
| HLTH-24 | `tests/unit/services/test_credentials.py::test_google_signin_states_and_metadata_only`, `test_google_signin_account_stored_in_credentials_account` | unit | planned |
| HLTH-25 | `tests/services/test_credentials.py::test_metered_validation_uses_free_methods` | integration | planned |
| HLTH-43 | `tests/unit/services/test_credentials.py::test_credentials_store_metadata_only` (named in test plan v4) | unit | planned |
| HLTH-30 | `tests/services/test_notify.py::test_state_change_and_expiry_milestones_fire_once` | integration | planned |
| HLTH-31 | `tests/services/test_notify.py::test_unresolved_items_roll_into_one_digest` | integration | planned |
| HLTH-32 | `tests/unit/services/test_notify.py::test_macos_argv_has_no_token`, `test_osascript_fallback`, `test_webhook_payload_and_header` | unit | planned |
| HLTH-33 | `tests/unit/services/test_notify.py::test_quiet_hours_hold_all_but_install_critical_urgent_and_recent_invalid`, `test_expiry_critical_row_is_held_in_quiet_hours_and_in_digest` | unit | planned |
| HLTH-34 | `tests/unit/services/test_notify.py::test_text_has_no_secret_or_url_query` | unit | planned |
| HLTH-35 | `tests/unit/services/test_notify.py::test_ack_and_snooze_persist` | unit | planned |
| HLTH-41 | `tests/integration/test_doctor.py::test_every_check_runs_with_simulated_tcc_denial`, `test_notify_only_when_result_changes`, `test_daemon_down_install_critical_bypasses_quiet_hours` | integration | planned |
| HLTH-42 | `tests/contract/test_status_contract.py::test_ops_status_resource_and_api_status_hold_no_secret` | contract | planned |

Design element behind each row: HLTH-40 to HLTH-41 are 5.9; HLTH-1 is 5.3; HLTH-2 to HLTH-4 and HLTH-44 are 5.4 and 5.6; HLTH-10 to HLTH-12 are 5.5; HLTH-13, HLTH-20 to HLTH-25 and HLTH-43 are 5.7; HLTH-30 to HLTH-35 are 5.8; HLTH-42 is 5.10 and the contract.

Notes on what the tests must cover beyond the criterion text:

- HLTH-10 builds one `EvalInputs` per rule and one with two rules true, and asserts the order of 5.5. HLTH-12 uses `FakeClock` to cross `rate_limited_until` and `budget_reset_at`, and to cross local midnight for the cap (SRC-29).
- HLTH-30 includes a first sighting at 2 days (one notice, milestone 3) and a rotation that changes the expiry date (new keys).
- HLTH-32 asserts that no argument contains the one-time token or `NOTIFY_WEBHOOK_TOKEN`, that a `ui_path` with a query is replaced by `/ui/`, and that the webhook scheme rule rejects `http` to a non-loopback host.
- HLTH-34 feeds a registered secret and a URL with a query and asserts both are gone from subject, body, webhook payload and stored row.
- HLTH-42 walks every string of the three outputs for registered fake secrets and fingerprints (the summary has none).

Related evidence in other components: SEC-3 (`tests/unit/platform/test_secrets.py::test_keychain_metadata_never_passes_w` and three more, already linked) and SEC-4 (`tests/unit/platform/test_secrets.py`, the reload test, already linked) verify HLTH-FR-20 and HLTH-FR-23; SEC-24 (no secret at rest) scans `state.db`; SEC-28 (proposed in PRD-security v3) covers the tool results; PLAT-70 covers `/healthz` and `/readyz`; PLAT-39 covers the call record. Owner checks OC-03 (a real macOS notification opens the right UI page) and OC-14 (doctor shows the Google sign-in ok) are owner checks, not tests (test plan v4 section 3).

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| Credential values stay in the Keychain; `state.db` holds metadata and fingerprints only | No secrets at rest outside the Keychain (ADR 0003; NFR-3; HLTH-INV-1) | Plaintext client configs, as in v1 (REVIEW-v1 OPS-11) |
| `doctor` runs without the daemon, driven by two launchd jobs | A dead daemon must still be reported (HLTH-FR-41; ADR 0002) | Not stated |
| The scheduler follows the wall clock | asyncio timers stall while the Mac sleeps (LLD-platform v2 5.5) | asyncio timers |
| The notification click runs `research-mcp ui --path`, which mints the login token on click | No token in the notification, an argument list or Notification Center (SPEC-v2 10.4; UI-FR-2) | Not stated |
| The Google sign-in stays with `gcloud` | v2 holds only a short-lived token in memory (ADR 0012) | Dropping the Vertex provider (REVIEW-v1 OPS-24) |
| Probes check response shape | Upstream drift can return 200 with wrong data (SPEC 9; REVIEW-v1 OPS-15) | Status code only, as in v1 |
| `evaluate_source` is a pure function of its inputs and `now` | The rules can be tested rule by rule, and a state clears at its time with no timer (HLTH-10, HLTH-12) | A state machine driven by timers |
| Dedupe keys carry the start of the state (`since`) or the milestone and expiry date | Once-only delivery with no new column, and a recurrence notifies again (HLTH-30) | A `resolved_at` column on `notifications` (a schema change) |
| The webhook is an `HttpClient` request | One path for origin scoping, redaction and telemetry; the token is revealed only in `platform/http.py` (LLD-security v2 E42) | A separate `urllib` call |
| The `osascript` fallback takes the text as arguments | No quoting hazard from a subject or body (HLTH-INV-2) | Splicing the text into the script string (SPEC-v2 wording) |
| Two names: row `severity` keeps the PRD levels; `install_critical` (installation integrity only) drives the `doctor` exit code, the quiet-hours bypass and the upgrade rollback | PRD-health v4 2.4 stands; an expired key or a source outage must not fail `doctor` or roll back an otherwise good upgrade (owner decision, 2026-10-22; LLD-platform v2 5.9) | One word `critical` with two meanings; treating an invalid credential or a `down` source as `install_critical` |

**Decisions that settle the open questions of LLD-health v1** (each answered from the approved sources; the question is deleted from section 11):

| # | Question in v1 | Decision and source |
| --- | --- | --- |
| 1 | `quota_used` against `calls_today` | `source_health.calls_today` is the contract: the schema has no `quota_used` and SPEC-v5 10 and the PRD add no column. The count is rebuilt from `calls` at start and compared with `budget_cap`; it resets at local midnight (SRC-29; 3, 5.5). The sources and search LLDs that wrote `quota_used` must follow. |
| 2 | `AuthSpec.validation` allows four values; SPEC-v2 10.3 names `google_adc` and `serpapi_account` | The literal does not grow. Both are probes: SerpAPI's `account.json` is its free `probe()`, and the Google sign-in is validated by `GoogleAdcProvider` plus the Vertex engine-metadata probe, keyed by the `gcloud_adc` reference, not by `AuthSpec.validation`. `ProbeSpec.cost` already distinguishes free from metered (5.7; HLTH-FR-21, HLTH-25). |
| 3 | Where is the Google sign-in account email held? | In a nullable `credentials.account` column in `0001_init`, shown in the UI and by `doctor` (owner decision, 2026-10-22; HLTH-FR-25; HLTH-INV-5). |
| 4 | Is "calls in 24 hours" rolling or the calendar day? | Rolling 24 hours (HLTH-FR-11 says "in 24 hours"). It is computed from `calls`. `calls_today` is a separate count, from local midnight, used only for the cap (5.5). |
| 5 | Is an embeddings probe required? | Yes: HLTH-FR-5 lists embeddings and PRD-health v4 adds HLTH-44 (owner decision, 2026-10-22). It is the `local_embeddings` target (5.6). HLTH-4 keeps its wording and HLTH-44 verifies this one. |
| 6 | Which module feeds the UI banner? | `NotifyService.banners()` reads active, unacknowledged, unsnoozed rows of `notifications`; the UI banner slot calls it (LLD-ui v1 5.3 names the slot). "Active" is derived from current states by `HealthService.active_keys()`, with no new column (5.8). |
| 7 | Which milestone holds the full `doctor`? | PRD-health v4 2.4 gives HLTH-41 the milestone M2 and HLTH-40 M0, and a PRD wins over SPEC-v2 12.4. SPEC-v5 14 puts "doctor" in M1. Both hold: M1 ships every check that needs no cache service, M2 adds the archive, disk, review and backup checks (1, 5.9). |
| 8 | Is a rate limit or an exhausted budget a notification? | No. HLTH-FR-30 lists the triggers and these are not among them; they reach the owner in the digest as unresolved items and in the UI. PRD-health v4 1.2 gives "OpenAlex is rate limited" as an example of what the owner hears; if the owner wants it pushed, it is a PRD change to HLTH-FR-30. |
| 9 | What are the HLD-v3 13 and ADR 0012 statements on paid search? | SPEC-v5 13 (Cost) is current: paid web-search providers are optional, off until configured, capped per day and called only when asked for (SPEC-v5 section 13; ADR 0012). HLD-v3 is archived. This component tracks their quotas and caps. |
| 10 | What are the names for `services/credentials.py`, `ops_status` and `research://status`? | `CredentialService` in `services/credentials.py`; `ops_status` in `mcp_app/tools_ops.py` and `research://status` in `mcp_app/resources.py`, calling `HealthService.ops_summary()`. SPEC-v2 names none, so the names are the designer's [inferred]. |
| 11 | Where does `doctor` live? | `services/doctor.py`, new; `cli.py` parses arguments and prints. `sdd.config.json` lists four health files and not this one, so the `planner` adds `src/research_mcp/services/doctor.py` to the health paths. |
| 12 | Which behaviors need a flag, and are `notify.macos` and `notify.webhook_url` safe to switch off? | Table in 7, which follows LLD-platform v2 7.2 (no feature-flag PRD exists). Yes, both are safe to switch off. |
| 13 | Do `/api/status`, `ops_status`, `research://status` and the webhook need a contract? | Yes: the shapes cross components and are read by agents and OpenClaw. [Health status, doctor output and webhook payload v1](../contracts/health-status-and-webhook-v1.md), a draft for the owner. `list_sources` and `research://sources` stay with the sources component. |
| 14 | Webhook scheme, contact address and placeholder behavior | `https`, or `http` for a loopback host only; a placeholder `contact.email` is a settings error and the daemon does not start, while an unset address leaves only `needs_contact` sources `unconfigured` (owner decision, 2026-10-22; LLD-security v2 4.3; LLD-platform v2 7.1). |
| 15 | What is the status of the old `/review/<batch_id>` path in v1? | v1 wrote `ui_path=/review/<batch_id>`. The UI route is `/ui/review/<batch_id>` (SPEC 11.3), and `ui --path` and `/ui/login` accept `/ui/` paths only (owner decision, 2026-10-22), so the event uses `/ui/review/<batch_id>`. |

**Code divergences implementers must fix** (the repository has only `settings.py`, `platform/secrets.py` and `core/`):

- `NotifySettings.webhook_url` accepts any `http` or `https` URL; it must reject `http` unless the host is loopback.
- `SecretState` has four members; add `INVALID` (LLD-platform v2 4.1). `SecretMeta` has no `account` or `expires_at` (5.2); `CredentialService` copies `account` into `credentials.account`.
- `BackupSettings` has no `drive_copy` (platform LLD 7.1; not this component's).
- `AuthSpec.validation` already matches this LLD; do not extend it.
- **For the platform LLD owner (LLD-platform v2) to take from this LLD and the cache LLD:** (1) scheduler jobs `review_close`, `archive_reconcile`, `health_evaluate`, `health_rollup`, `credential_sync` and `probe:<source>`; (2) flags `cache.crawl_enabled`, `cache.collections_enabled` and `archive.reindex_enabled` in the flag registry (the health flags stay as in section 7); (3) the webhook validator (`https`, or `http` for a loopback host only; no credentials, query or fragment); (4) `0001_init` carries `credentials.account` and `disk_samples.model_cache_bytes`; (5) `sdd.config.json` paths: add `src/research_mcp/services/doctor.py` to health, and the cache tool wrappers, tests, `services/disk.py` and `mcp_app` to the paths of their components; (6) LLD-platform v2 5.9 rolls back an upgrade only on an `install_critical` `doctor` check (installation integrity only). LLD-security v2 needs no change: `credentials.account` is not a secret (section 3).
- `sdd.config.json` health paths omit `services/doctor.py` (decision 11).

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

None open. Q1 (account email column) and Q2 (what is critical) were answered on 2026-10-22 and are recorded in 3, 5.8, 5.9 and 10.

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
