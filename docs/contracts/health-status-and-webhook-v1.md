---
title: "Health status, doctor output and webhook payload"
type: contract
version: 1
status: approved
approved_by: "Kenny Hill (Engineering)"
approved: 2026-10-23
owner: "Kenny Hill"
component: health
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
date: 2026-10-22
---

# Contract: health status, doctor output and webhook payload (v1)

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves at Gate 3 with [LLD-health-v2](../lld/LLD-health-v2.md). Approved at Gate 3 on 2026-10-23. It writes down the shapes that [PRD-health v4](../prd/components/PRD-health-v4.md) (HLTH-FR-11, HLTH-FR-32, HLTH-FR-40, HLTH-FR-42, HLTH-FR-43) and [SPEC-v5](../spec/SPEC-v5.md) section 7 imply; it adds no behavior. Shapes marked "assumption" are the designer's choice and need the owner's confirmation.

Implementations are Pydantic models in `research_mcp/services/health.py` (status shapes), `research_mcp/services/notify.py` (the webhook payload) and `research_mcp/services/doctor.py` (the doctor report). No shape here contains a credential value, a Keychain value, a login token or a URL with a query (HLTH-INV-1 to HLTH-INV-3; HLTH-42).

## Operations

### `GET /healthz` (HLTH-FR-43)

No credential. Returns `{"status":"ok","version":"3.x.y"}` with HTTP 200 whenever the process can answer.

### `GET /readyz` (HLTH-FR-43)

No credential. HTTP 200 with `{"status":"ready"}` when the stores are open, the scheduler is running and the Keychain is readable. Otherwise HTTP 503 with `{"status":"not_ready","failed":[<names>]}`, where each name is one of `stores`, `scheduler`, `keychain`. Names only; no detail text.

### `GET /api/status` (HLTH-FR-43, HLTH-42)

Bearer token or a UI session. Returns `StatusReport`:

| Field | Type | Rule |
| --- | --- | --- |
| `generated_at` | ISO 8601 UTC text | |
| `version` | text | The package version. |
| `ready` | object `{stores, scheduler, keychain}` of booleans | The same three checks as `/readyz`. |
| `sources` | list of `SourceDetail` | One per registered source (HLTH-FR-11). |
| `local_targets` | list of `LocalTargetDetail` | `cache_db`, `embeddings`, `archive`, `disk` (HLTH-FR-5). |
| `credentials` | list of `CredentialDetail` | Metadata only. |
| `quotas` | list of `QuotaDetail` | Sources that report a quota or have a daily cap. |
| `jobs` | object `{pending, running, failed}` of integers | Counts from `state.db.jobs` (assumption: `failed` counts the last 24 hours). |
| `cache` | object `{documents, files_bytes, index_bytes}` | Read from the cache component's service (assumption: field names). |
| `disk` | object `{cache_bytes, free_cache_vol, free_archive_vol, sampled_at}` or null | The latest `disk_samples` row. |
| `archive` | object `{target, state}` | `state` is `ok`, `fallback`, `unavailable` or `unknown`; `target` is a path text. |
| `notifications` | list of `NotificationItem`, at most 20, newest first | |
| `banner` | list of `NotificationItem` | Unacknowledged, unsnoozed items whose condition still holds (HLTH-FR-32). |

`SourceDetail` (HLTH-FR-11):

| Field | Type | Rule |
| --- | --- | --- |
| `id`, `title`, `group` | text | From the `SourceSpec`. |
| `state` | one of `disabled`, `unconfigured`, `down`, `credential_invalid`, `budget_exhausted`, `rate_limited`, `degraded`, `credential_expiring`, `deprecated`, `ok` | The worst applicable state (PRD-health v4 section 2.4). |
| `until`, `reset_at`, `days` | ISO 8601 UTC text, ISO 8601 UTC text, integer; each null unless the state carries it | `until` for `rate_limited`, `reset_at` for `budget_exhausted`, `days` for `credential_expiring` and `deprecated`. |
| `reason`, `fix_hint` | text or null | Never a secret, never a URL with a query. |
| `last_probe_at`, `last_probe_ok` | ISO 8601 UTC text or null, boolean or null | |
| `calls_24h` | integer | Rolling 24 hours from `calls`. |
| `error_rate` | number from 0 to 1 | Over the same 24 hours. |
| `p50_ms`, `p95_ms` | integers or null | Over the same 24 hours. |
| `last_error` | object `{code, at}` or null | The last classified error code. |
| `quota` | object `{remaining, limit, reset}` or null | Fields null when unknown. |
| `budget` | object `{cap, calls_today, reset_at}` or null | Present for metered sources with a cap. |
| `credentials` | list of `{name, state}` | The credential badges. |

`LocalTargetDetail`: `id`, `state` (`ok`, `degraded`, `down`, `unconfigured`), `reason`, `fix_hint`, `last_probe_at`.

`CredentialDetail`:

| Field | Type | Rule |
| --- | --- | --- |
| `name`, `service` | text | `service` is `research-mcp/<NAME>`, or `gcloud_adc` for the Google sign-in. |
| `required_by` | list of source ids | |
| `state` | one of `ok`, `expiring_soon`, `invalid`, `missing`, `keychain_locked`, `quota_low`, `unknown_expiry` | |
| `days` | integer or null | Days to expiry or to `rotate_by`; set for `expiring_soon`. |
| `fingerprint` | 8 hex characters or null | First 8 hex characters of the SHA-256 of the value (HLTH-FR-20). |
| `keychain_modified_at`, `expires_at`, `rotate_by`, `last_validated_at`, `last_used_at` | ISO 8601 UTC text or null | |
| `last_result` | text or null | A short code, for example `ok`, `auth_failed`, `SERVICE_DISABLED`. |
| `account` | text or null | The Google sign-in account email; null for Keychain items. Stored in the nullable `credentials.account` column in `0001_init` (owner decision, 2026-10-22). Not a secret under the SEC rules; shown in the UI and by `doctor`, redacted only where a PLAT-FR-13 pattern applies. |
| `fix` | object `{keychain_item, key_page, command, console_url}` | `command` is the value-free `security add-generic-password -U -s research-mcp/<NAME> -a "$USER" -w`, or `gcloud auth application-default login` for the Google sign-in. `console_url` is null except for Google permission problems. |

`QuotaDetail`: `source`, `remaining`, `limit`, `reset`, `calls_today`, `budget_cap`.

`NotificationItem`: `notification_id`, `ts`, `kind`, `severity` (`info`, `warning`, `critical`), `subject`, `body`, `ui_path`, `acknowledged_at`, `snoozed_until`.

### MCP tool `ops_status` (HLTH-FR-42, HLTH-42)

No arguments. Read-only annotations. Returns the standard envelope (see [envelope and errors](envelope-and-errors-v1.md)) whose `data` is `OpsSummary`, a summary with no secret and no fingerprint:

| Field | Type | Rule |
| --- | --- | --- |
| `generated_at`, `version` | text | |
| `ready` | boolean | All three readiness checks pass. |
| `source_counts` | object mapping a source state to an integer | Zero counts are omitted. |
| `attention` | list of `{kind, subject, state, since, fix_hint}`, at most 20 | Sources and local targets that are not `ok`, `disabled` or `unconfigured`, and credentials that are not `ok` or `unknown_expiry`. |
| `credential_counts` | object mapping a credential state to an integer | |
| `quotas_low` | list of `{source, remaining, limit, reset}` | Sources in `quota_low` or `budget_exhausted`. |
| `unacknowledged` | integer | Notifications not acknowledged and not snoozed. |

### MCP resource `research://status` (HLTH-FR-42)

The same `OpsSummary` as JSON text. Read-only. `research://sources` is specified by the sources component and lists every source with its state and fix hint (SRC-8); this contract adds nothing to it.

### Webhook `POST <notify.webhook_url>` (HLTH-FR-32)

Body, JSON:

| Field | Type | Rule |
| --- | --- | --- |
| `type` | text | The event kind: `source_down`, `credential_invalid`, `credential_expiring`, `quota_low`, `source_deprecated`, `disk_warning`, `archive_unavailable`, `review_batch_ready`, `keychain_locked`, `daemon_down`, `doctor_summary` or `digest`. |
| `severity` | `info`, `warning` or `critical` | The PRD-health v4 2.4 levels (for example `expiring_soon` is `warning` at 14 days and `critical` at 3 days or fewer). Not the quiet-hours bypass. |
| `install_critical` | boolean | True for installation integrity only (broken install, unreadable database, failed migration). Only `install_critical` and `urgent` events bypass quiet hours (owner decision, 2026-10-22). |
| `subject`, `body` | text | Redacted; no secret value, no URL with a query (HLTH-34). |
| `ui_path` | text or null | A path under `/ui/`, with no query and no token. |
| `ts` | ISO 8601 UTC text | |

Header `Authorization: Bearer <NOTIFY_WEBHOOK_TOKEN>` when that Keychain item exists; never in the URL. Allowed URL schemes: `https`, or `http` for a loopback host only (owner decision, 2026-10-22). Timeout 5 s, at most 2 retries, no redirect to another origin. Any 2xx answer is success.

### `research-mcp doctor --json` (HLTH-FR-40, HLTH-40, HLTH-41)

Prints `DoctorReport`:

| Field | Type | Rule |
| --- | --- | --- |
| `ok` | boolean | True when no check is `warning` or `install_critical`. |
| `install_critical` | boolean | True when any check is `install_critical` (installation integrity only: broken install, unreadable database, failed migration; owner decision, 2026-10-22); the exit code is 1 then, 0 otherwise, and an upgrade rolls back on it. Source outages and credential problems are `warning` checks. |
| `mode` | `full`, `quick` or `liveness` | |
| `checks` | list of `{name, status, code, detail, fix}` | `status` is `ok`, `warning` or `install_critical`; `code` is a short machine code; `detail` and `fix` are text with no secret and no URL query. |

Check names: `daemon_alive`, `keychain_readable`, `contact_email`, `credential:<NAME>`, `probe:<source>`, `archive_target`, `archive_access`, `disk`, `schema_versions`, `review_overdue`, `backup_recent`, `terminal_notifier`, `launchd_jobs`.

## Errors

| Surface | Condition | Result |
| --- | --- | --- |
| `/api/status` | No valid bearer token or UI session | Refused by the authorization gate with 401 (LLD-security-v2 4.3). |
| Any path | Foreign Host or Origin | Refused by the gate before any credential check (SEC-12). |
| `/readyz` | A readiness check fails | 503 with the failed check names. |
| `ops_status`, `research://status` | The status cannot be built | The standard error result with code `internal`; the traceback goes to the redacted log (PLAT-62). |
| Webhook | Non-2xx answer, timeout or connection error after the retries | Logged as a warning with the error code only; the notification is still stored and shown in the UI; no further retry. |
| `doctor` | At least one `install_critical` check (installation integrity only) | Exit code 1; the report is still printed. |
| `doctor` | A check cannot run (for example a probe times out) | That check reports `warning` with a code, not an exception text. |
