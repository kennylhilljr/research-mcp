-- state.db, migration 0001 (SPEC-v5 10; LLD-health-v2 3, plus searches.filters_json from LLD-search-v2 3).
-- The Migrator wraps this script in BEGIN IMMEDIATE and COMMIT and sets user_version.

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
  query_len INTEGER NOT NULL, sources_json TEXT NOT NULL, statuses_json TEXT NOT NULL, latency_ms INTEGER,
  filters_json TEXT NOT NULL DEFAULT '{}');

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
  embeddings_bytes INTEGER, trash_bytes INTEGER, model_cache_bytes INTEGER, free_cache_vol INTEGER,
  free_archive_vol INTEGER);

CREATE TABLE maintenance_runs (ts TEXT NOT NULL, check_name TEXT NOT NULL, ok INTEGER NOT NULL, detail TEXT);
