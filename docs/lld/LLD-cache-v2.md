---
title: "Retrieval and Cache low level design"
type: lld
version: 2
status: approved
approved_by: "Kenny Hill (Engineering)"
approved: 2026-10-23
owner: "Kenny Hill"
prefix: CACHE
component: cache
parent: docs/spec/SPEC-v5.md
supersedes: docs/lld/LLD-cache-v1.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# LLD: Retrieval and Cache (v2)

This LLD carries SPEC-v2 sections 8 and 9 (except 9.6) and HLD-v3 section 6 onto the LLD template, with the parts of SPEC-v2 sections 2, 3.4, 3.5, 3.6, 7.2, 7.3 and 10.1 that the cache depends on. Requirements and criteria are in [PRD-cache v4](../prd/components/PRD-cache-v4.md); the system design is [SPEC-v5](../spec/SPEC-v5.md) section 6 (and sections 9, 10 and 12 for security, stores and backups). It supersedes [LLD-cache v1](LLD-cache-v1.md). The machine-readable contract is [cache tools, archive sidecar and rebuild report v1](../contracts/cache-tools-and-sidecar-v1.md) (draft). It cites and does not contradict [LLD-platform v2](LLD-platform-v2.md) and [LLD-security v2](LLD-security-v2.md); the test plan is [test plan v4](../test/test-plan-v4.md) (draft).

**Changes in v2.** This version follows the approved PRD-cache v4 and SPEC-v4, which win wherever v1 disagreed. Added: CACHE-62 and CACHE-63 and the invariants CACHE-INV-1 to CACHE-INV-7 with their enforcement points; the transitions that v1 left out (pin, unpin, collection pins) in 5.5; the design of the optional Drive copy of backups that LLD-platform v2 3.3 hands to this LLD (5.11); the closing of review batches and the hourly archive reconcile as scheduled jobs (5.12); SEC-28 redaction of tool results (2.2, 4); the single deny-by-default gate and the webhook scheme rule (2.5, 4); the cache feature flags (7); and the contract file. Changed: the schema gains four columns (3.2) and the fourteen open questions of v1 are answered in section 10 (thirteen rows); four questions remain in section 11, in new form. History note: the earlier criterion, requirement and invariant IDs that the platform, sources, search, ui and migration PRDs replaced (PLAT-FR-16 by PLAT-FR-59; SRC-FR-11, SRC-FR-13 and SRC-FR-16 by SRC-FR-24, SRC-FR-25 and SRC-FR-26; SRCH-FR-4 and SRCH-FR-10 by SRCH-FR-27 and SRCH-FR-28; UI-FR-5 and UI-FR-19 by UI-FR-20 and UI-FR-21; MIG-FR-23 by MIG-FR-25) do not appear in the cache design; the source state `skipped_budget` is now `budget_exhausted` and the `web` fallback adds `not_needed` (the cache only passes `source_status` through).

**Reviewer note.** Sections 4, 8 and 9 belong to other personas. The changes there were drafted by the `component-designer` and have been reviewed in Gate 3 on 2026-10-23: section 4 by `security-reviewer`, section 8 by `sre` and section 9 by `test-architect`; nothing here has been verified by the owner.

**Numbers.** Section numbers inside this LLD are bare (for example "5.5"). "SPEC n" means section n of SPEC-v5. Spec section numbers that PRD-cache v4 still cites (for example "SPEC 9.1" in CACHE-30 and "SPEC 9.3" in CACHE-40, which are SPEC-v2 numbers) are kept in the headings below and map as follows (decision 12 in section 10).

| PRD or SPEC-v2 reference | Lives in this LLD |
| --- | --- |
| SPEC-v2 8.1 (`cache.db` schema) | 3.1 |
| SPEC-v2 8.2 (extraction, chunking, embeddings) | 5.3 |
| SPEC-v2 8.3 (local search) | 5.4 |
| SPEC-v2 9.1 (transition table; "SPEC 9.1" in CACHE-30) | 5.5 |
| SPEC-v2 9.2 (review batch) | 5.6 |
| SPEC-v2 9.3 (archive; "SPEC 9.3" in CACHE-40) | 5.7 |
| SPEC-v2 9.4 (disk and integrity) | 5.8 |
| SPEC-v2 9.5 (collections) | 5.9 |
| SPEC-v2 9.7 (archive rebuild) | 5.10 |
| SPEC-v2 9.8 (backups) | 5.11 |

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

Governing section: **SPEC 6** (Retrieval and cache); also SPEC 9 (security architecture), SPEC 10 (data stores) and SPEC 12 (deployment and operations, for backups).

Criteria of this component (PRD-cache v4 2.4): CACHE-1, CACHE-2, CACHE-10 to CACHE-24, CACHE-30 to CACHE-36, CACHE-40 to CACHE-49, CACHE-60 to CACHE-63. Requirements: CACHE-FR-1 to CACHE-FR-7, CACHE-FR-10 to CACHE-FR-18, CACHE-FR-20 to CACHE-FR-24, CACHE-FR-30 to CACHE-FR-38, CACHE-FR-45 to CACHE-FR-52, CACHE-FR-55 to CACHE-FR-59. Invariants: CACHE-INV-1 to CACHE-INV-7 (PRD-cache v4 1.6). Stories: CACHE-US-1 to CACHE-US-6.

| Requirement | Criteria | SPEC section | Detailed in |
| --- | --- | --- | --- |
| CACHE-FR-1 | CACHE-10 | SPEC 6, 11.2 | 2.1, 5.2 |
| CACHE-FR-2 | CACHE-1, CACHE-2 | SPEC 6, 9 | 5.2, 5.13 |
| CACHE-FR-3 | none in PRD-cache (SEC-8, verified by the security component) | SPEC 9 | 4 |
| CACHE-FR-4 | CACHE-2, CACHE-11 | SPEC 9 | 2.1, 3.6, 4 |
| CACHE-FR-5 | CACHE-2 | SPEC 6 | 3.1, 5.2 |
| CACHE-FR-6 | CACHE-12 | SPEC 6 | 2.1, 5.2 |
| CACHE-FR-7 | CACHE-13 | SPEC 6 | 2.1, 5.12 |
| CACHE-FR-10 | CACHE-14, SEC-23 | SPEC 6, 9 | 5.3, 5.13 |
| CACHE-FR-11 | CACHE-15 | SPEC 6 | 5.3 |
| CACHE-FR-12 | CACHE-16 | SPEC 6 | 5.3 |
| CACHE-FR-13 | CACHE-17 | SPEC 6 | 5.3 |
| CACHE-FR-14 | CACHE-18 | SPEC 6 | 3.1, 5.3 |
| CACHE-FR-15 | CACHE-19 | SPEC 6 | 2.1, 5.4 |
| CACHE-FR-16 | CACHE-20 | SPEC 6 | 5.4 |
| CACHE-FR-17 | CACHE-20 | SPEC 6 | 3.1, 5.4 |
| CACHE-FR-18 | CACHE-21 | SPEC 6 | 2.1 |
| CACHE-FR-20 | CACHE-22 | SPEC 6 | 5.2, 5.3 |
| CACHE-FR-21 | CACHE-22 | SPEC 6 | 3.1 |
| CACHE-FR-22 | CACHE-23 | SPEC 6 | 5.3 |
| CACHE-FR-23 | CACHE-22 | SPEC 6, 10 | 3.1 |
| CACHE-FR-24 | CACHE-24 | SPEC 6 | 5.4, 7 |
| CACHE-FR-30 | CACHE-30, PLAT-8, PLAT-53 | SPEC 6, 10 | 5.5, 7 |
| CACHE-FR-31 | CACHE-30, CACHE-31 | SPEC 6 | 5.6 |
| CACHE-FR-32 | CACHE-31 | SPEC 6, 7 | 5.6, 2.5 |
| CACHE-FR-33 | CACHE-32 | SPEC 6 | 5.5, 5.6 |
| CACHE-FR-34 | CACHE-30, CACHE-33 | SPEC 6 | 5.5, 5.6 |
| CACHE-FR-35 | CACHE-34, CACHE-48, PLAT-61 | SPEC 6, 9 | 2.1, 4, 5.6 |
| CACHE-FR-36 | CACHE-30, CACHE-36, PLAT-53 | SPEC 6, 9 | 5.5 |
| CACHE-FR-37 | CACHE-30 | SPEC 6 | 5.5 |
| CACHE-FR-38 | CACHE-35 | SPEC 6 | 5.6 |
| CACHE-FR-45 | CACHE-40, HLTH-41, owner checks OC-04, OC-13 | SPEC 6, 12 | 5.7 |
| CACHE-FR-46 | CACHE-40 | SPEC 6 | 2.6, 5.7 |
| CACHE-FR-47 | CACHE-41, owner check OC-04 | SPEC 6 | 5.7 |
| CACHE-FR-48 | CACHE-42 | SPEC 6 | 5.7 |
| CACHE-FR-49 | CACHE-43 | SPEC 6 | 5.7 |
| CACHE-FR-50 | CACHE-44, PLAT-84 | SPEC 6, 7 | 5.7 |
| CACHE-FR-51 | CACHE-60, CACHE-62 | SPEC 6 | 5.10 |
| CACHE-FR-52 | CACHE-61 | SPEC 6 | 2.1, 5.4 |
| CACHE-FR-55 | CACHE-45, CACHE-63, PLAT-53 | SPEC 6 | 5.9 |
| CACHE-FR-56 | CACHE-13 | SPEC 6 | 5.12 |
| CACHE-FR-57 | CACHE-46 | SPEC 6, 10 | 5.8 |
| CACHE-FR-58 | CACHE-47 | SPEC 6 | 5.8 |
| CACHE-FR-59 | CACHE-49, PLAT-9 | SPEC 10, 12 | 3.6, 5.11 |

| Invariant | Criteria | Enforcement point (detail in 4) |
| --- | --- | --- |
| CACHE-INV-1 No deletion without a recorded owner decision | CACHE-33 | 5.5 (only a recorded decision reaches `discarded`; the purge acts only on `discarded`) |
| CACHE-INV-2 No removal of a file shared with a live document | CACHE-36 | 5.5 file deletion rule |
| CACHE-INV-3 No caller-chosen path | CACHE-11 | 2.1 (no tool takes a path), 3.6 |
| CACHE-INV-4 No credential on a mismatched origin | SEC-8 (security) | 4 (downloader has no credential resolver) |
| CACHE-INV-5 No cached copy removed before the archive copy is verified | CACHE-41 | 5.7 steps 3 and 4 |
| CACHE-INV-6 No change to Drive files during the rebuild | CACHE-62 | 5.10 (read-only reader) |
| CACHE-INV-7 No MCP discard except `cache_review_decide` | CACHE-48, CACHE-34 | 2.1, 4 |

Out of this component: the legacy import (SPEC-v2 9.6), which belongs to the migration component ([LLD-migration-v2](LLD-migration-v2.md)); the downloader and the worker runner code, which belong to the platform component ([LLD-platform v2](LLD-platform-v2.md) 5.4, 5.5); `cite`, `get_work` and the tool registration, which belong to the search component ([LLD-search-v2](LLD-search-v2.md)); the UI pages ([LLD-ui-v2](LLD-ui-v2.md)); `NotifyService`, `HealthService` and the webhook ([LLD-health-v2](LLD-health-v2.md)).

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

Machine-readable contract: [cache tools, archive sidecar and rebuild report v1](../contracts/cache-tools-and-sidecar-v1.md) (approved at Gate 3, 2026-10-23). It holds the tool arguments and result shapes, the error use per situation, the sidecar format and the rebuild report. This section lists what each part is for and the cross-component interfaces.

### 2.1 MCP tools (SPEC-v2 7.2, the cache rows)

| Tool | Service | Annotations | M | Criteria |
| --- | --- | --- | --- | --- |
| `fetch` | cache | not RO, OW, idempotent | M2 | CACHE-10, CACHE-11, CACHE-12 |
| `read` | cache | RO | M2 | CACHE-19 |
| `search_cache` | cache | RO | M2 | CACHE-20, CACHE-24, CACHE-61 |
| `library` | lifecycle | RO for list and stats; otherwise not RO, not destructive | M2 | CACHE-21, CACHE-48 |
| `collections` | lifecycle | not RO | M2 | CACHE-45 |
| `crawl_site` | jobs | not RO, OW | M2 | CACHE-13 |
| `jobs` | jobs (platform) | not RO for cancel | M2 | CACHE-13 |
| `cache_review_list` | lifecycle | RO | M2 | CACHE-35 |
| `cache_review_decide` | lifecycle | not RO, destructive | M2 | CACHE-34 |

Argument bounds are in the contract. Rules that bind the design:

- **Tools are thin** (SPEC 3): validate, call one service, wrap in the envelope. The wrappers are `mcp_app/tools_library.py` and `mcp_app/tools_review.py` (SPEC-v2 1); the search component's paths own the files, this component owns the services and the models they return (5.1).
- **No path, no SQL.** No argument is a local path; `id_or_url` accepts an identifier or an `https` URL, or for `fetch` a list of 1 to 20 of them, and rejects anything else with `invalid_argument` (CACHE-11; CACHE-INV-3; SEC-25).
- **`library` cannot discard.** Its `action` has no discard value. The only MCP discard is `cache_review_decide`, and only for items in an open batch (CACHE-48; CACHE-INV-7; SEC-20).
- **MCP decisions** are recorded with `decided_by="agent"` and `decided_channel="mcp"`. A discard through MCP produces an immediate notification that lists the items and links to the Archive page, where the undo is (5.6).
- **There is no hard-delete tool.** `jobs` can cancel but not submit; the maintenance fix actions have no tool (4).
- **Cursors** for `read` and `library list` are signed with the daemon cursor key (LLD-platform v2 5.6); a cursor made for another tool is `invalid_argument`.
- **Cache state for `get_work`** (CACHE-FR-49; CACHE-43). `get_work` belongs to the search component. This component provides `LifecycleService.summaries(work_ids) -> dict[str, list[DocSummary]]` with `DocSummary(doc_id, state, archive_path, archived_at, archive_fallback)`, which `get_work` calls to fill its cache state (SRCH-FR-17).

### 2.2 Envelope, resources and prompts

- Results use `ToolResult[...]` (LLD-platform v2 2.1). Document text is wrapped in `Untrusted` (SEC-22). The cache raises `extract_failed` (`EXTRACT_FAILED`) only from `read` on a document whose extraction failed; the fetch itself succeeds and reports `extract_status` (contract, Errors).
- **SEC-28** (owner decision, 2026-10-22): every string in a successful result, including `Untrusted.content`, is redacted for registered secrets in `@tool_boundary`. The cache adds nothing; a text window that contains a registered secret value is returned with that value masked, and a cursor is computed on the stored text, not the masked text.
- **MCP resources** (SPEC-v2 7.3, M2): `research://work/{work_id}`, `research://doc/{doc_id}/text{?page}`, `research://collection/{name}`, `research://cache/expiring`, `research://cache/index`. Resource text is `Untrusted` and passes the same boundary. The prompt `review-expiring-items` is registered in M1 and its text is in [prompts v3](../contracts/prompts-v3.md); the server instructions say that cache review decisions must come from the owner's explicit words (PLAT-61).

### 2.3 CLI

`research-mcp archive reindex [--dry-run]` starts the archive rebuild (5.10). `research-mcp install` runs the first archive write in the foreground and records the owner's confirmation of the detected Drive folder (5.7). `research-mcp doctor` runs `archive_target`, `archive_access`, `disk`, `schema_versions`, `review_overdue` and `backup_recent` (8). The commands `config set` and `config get` read and write the keys in 7. `archive reindex` is registered by this component's work unit in the platform command table (LLD-platform v2 2.4).

### 2.4 UI routes

Pages `/ui/cache`, `/ui/review/<batch_id>`, `/ui/archive` and `/ui/maintenance`; actions are POST routes at `/action/<name>` under the same paths. The UI calls the services in 5.1 and applies the same checks as the MCP tools: the review submission goes through `LifecycleService.decide`, the same method `cache_review_decide` calls, so the open-batch and membership checks are identical (decision 10 in section 10). The routes, session and CSRF rules are in [LLD-ui-v2](LLD-ui-v2.md) and [LLD-security v2](LLD-security-v2.md).

### 2.5 Notifications and the webhook

The cache sends notices through `NotifyService.notify(Notice)` ([LLD-health-v2](LLD-health-v2.md) 2); one call reaches every enabled channel (macOS, UI banner, webhook). `Notice(kind, severity, subject, body, ui_path, dedupe_key)`. `ui_path` is the full UI path including the `/ui` prefix (for example `/ui/review/<batch_id>`), because the UI `next` redirect accepts `/ui/` paths only (owner decision, 2026-10-22).

Webhook message (health component): `POST notify.webhook_url` with JSON `{type, severity, subject, body, ui_path, ts}`. The URL must be `https`, or `http` on a loopback host (owner decision, 2026-10-22; LLD-security v2). `NotifyService` sends the message through `HttpClient` with a 5 s timeout and at most 2 retries; the cache neither retries nor logs the token.

| `kind` | When | `ui_path` | `dedupe_key` |
| --- | --- | --- | --- |
| `cache_review` | A review batch is created | `/ui/review/<batch_id>` | `review:<batch_id>` |
| `cache_mcp_discard` | `cache_review_decide` discards at least one item | `/ui/archive` | `mcp-discard:<batch_id>:<ts>` |
| `cache_trash_purge_notice` | 10:00, items whose trash ends within 24 hours | `/ui/archive` | `purge-notice:<date>` |
| `archive_upload_stall` | An archive is `pending` 24 hours after archiving | `/ui/archive` | `upload-stall:<doc_id>` |
| `archive_target_unavailable` | A health event, below | `/ui/archive` | `archive-target` |
| `disk_warn`, `disk_critical` | A threshold is crossed | `/ui/maintenance` | `disk:<level>` |

Assumption for the health LLD to confirm: `cache_mcp_discard` and `cache_trash_purge_notice` are sent with `bypass_quiet_hours=True`, because their purpose is that the owner catches a wrong discard in time (CACHE-FR-35, CACHE-FR-36). The sources do not say; `notify.quiet_hours` is the health component's rule.

### 2.6 Archive sidecar and rebuild report

Both formats are in the contract file (sidecar fields, slug, report fields). The sidecar keeps the field list of SPEC-v2 9.3 and PRD-cache CACHE-FR-46 exactly; a reader ignores unknown fields.

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

### 3.1 `cache.db` schema (SPEC-v2 8.1, migration 0001)

The schema of v1 holds, with the four additions of 3.2 marked `-- v2` (approved (owner decision, 2026-10-22)). No code exists yet for it: `platform/migrations/cache/0001_init.sql` is created by the M2 unit, and PLAT-53 (`test_schemas_match_spec`) compares it with this section.

```sql
CREATE TABLE works (
  work_id TEXT PRIMARY KEY, work_type TEXT NOT NULL, title TEXT NOT NULL, title_key TEXT NOT NULL,
  authors_json TEXT NOT NULL DEFAULT '[]', first_author_family TEXT, year INTEGER, published_at TEXT,
  venue TEXT, abstract TEXT, csl_json TEXT NOT NULL, integrity_status TEXT NOT NULL DEFAULT 'unknown',
  integrity_checked_at TEXT, metadata_refreshed_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX works_title_key_year ON works(title_key, year);

CREATE TABLE identifiers (
  scheme TEXT NOT NULL, value TEXT NOT NULL, raw TEXT NOT NULL,
  work_id TEXT NOT NULL REFERENCES works(work_id) ON DELETE CASCADE,
  source TEXT NOT NULL, first_seen_at TEXT NOT NULL,
  PRIMARY KEY (scheme, value));
CREATE INDEX identifiers_work ON identifiers(work_id);

CREATE TABLE source_records (
  source_record_id TEXT PRIMARY KEY, work_id TEXT REFERENCES works(work_id) ON DELETE SET NULL,
  source TEXT NOT NULL, upstream_id TEXT NOT NULL, adapter_version TEXT NOT NULL,
  retrieved_at TEXT NOT NULL, payload_sha256 TEXT NOT NULL, payload_json TEXT,
  UNIQUE (source, upstream_id, payload_sha256));

CREATE TABLE documents (
  doc_id TEXT PRIMARY KEY, work_id TEXT REFERENCES works(work_id) ON DELETE SET NULL,
  kind TEXT NOT NULL CHECK (kind IN ('pdf','html','text')),
  origin_url TEXT, landing_url TEXT, source TEXT NOT NULL, license TEXT, oa_status TEXT,
  state TEXT NOT NULL CHECK (state IN ('cached','pinned','expiring','kept','archived','discarded')),
  cached_at TEXT NOT NULL, expires_at TEXT, review_batch_id TEXT, reask_count INTEGER NOT NULL DEFAULT 0,
  next_ask_at TEXT, pinned_at TEXT,
  pin_direct INTEGER NOT NULL DEFAULT 0,                              -- v2
  archived_at TEXT, archive_path TEXT,
  archive_fallback INTEGER NOT NULL DEFAULT 0,
  archive_upload_state TEXT CHECK (archive_upload_state IN ('pending','uploaded','unknown')),
  discarded_at TEXT, trash_until TEXT, purged_at TEXT, decided_by TEXT, decided_channel TEXT,
  last_accessed_at TEXT, fetch_recipe_json TEXT NOT NULL, extract_status TEXT NOT NULL DEFAULT 'pending',
  integrity_at_fetch TEXT NOT NULL DEFAULT 'unknown',                 -- v2
  CHECK (state <> 'archived' OR archive_path IS NOT NULL),
  CHECK (state <> 'discarded' OR discarded_at IS NOT NULL));
CREATE INDEX documents_state_expiry ON documents(state, expires_at);
CREATE INDEX documents_work ON documents(work_id);

CREATE TABLE files (
  file_id TEXT PRIMARY KEY, doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL, media_type TEXT NOT NULL,
  storage_path TEXT, version_label TEXT, page_count INTEGER, final_url TEXT, http_status INTEGER,
  etag TEXT, last_modified TEXT, fetched_at TEXT NOT NULL, UNIQUE (doc_id, sha256));
CREATE INDEX files_sha ON files(sha256);

CREATE TABLE extractions (
  extraction_id TEXT PRIMARY KEY, file_id TEXT NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,
  parser TEXT NOT NULL, parser_version TEXT NOT NULL, chunker_version TEXT NOT NULL,
  needs_ocr INTEGER NOT NULL DEFAULT 0, extracted_at TEXT NOT NULL);

CREATE TABLE chunks (
  chunk_id INTEGER PRIMARY KEY, extraction_id TEXT NOT NULL REFERENCES extractions(extraction_id) ON DELETE CASCADE,
  doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE, ord INTEGER NOT NULL,
  page_start INTEGER, page_end INTEGER, char_start INTEGER, char_end INTEGER, section TEXT,
  title TEXT NOT NULL DEFAULT '',                                     -- v2
  content TEXT NOT NULL, content_sha256 TEXT NOT NULL, UNIQUE (extraction_id, ord));

-- External-content FTS: rows are read back from chunks, so snippet() and highlight() work on any SQLite >= 3.37.
CREATE VIRTUAL TABLE chunks_fts USING fts5(content, section, title,   -- v2: title added
  content='chunks', content_rowid='chunk_id', tokenize='porter unicode61 remove_diacritics 2', prefix='2 3');
CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
  INSERT INTO chunks_fts(rowid, content, section, title) VALUES (new.chunk_id, new.content, new.section, new.title); END;
CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, content, section, title) VALUES ('delete', old.chunk_id, old.content, old.section, old.title); END;
CREATE TRIGGER chunks_au AFTER UPDATE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, content, section, title) VALUES ('delete', old.chunk_id, old.content, old.section, old.title);
  INSERT INTO chunks_fts(rowid, content, section, title) VALUES (new.chunk_id, new.content, new.section, new.title); END;
-- Chunks are written once per extraction; re-extraction inserts new rows. The update trigger exists for safety.

CREATE TABLE embeddings (
  content_sha256 TEXT NOT NULL, model TEXT NOT NULL, dim INTEGER NOT NULL, vector BLOB NOT NULL,
  created_at TEXT NOT NULL, PRIMARY KEY (content_sha256, model));

CREATE TABLE collections (name TEXT PRIMARY KEY, description TEXT, pin_members INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL);
CREATE TABLE collection_items (name TEXT NOT NULL REFERENCES collections(name) ON DELETE CASCADE,
  work_id TEXT NOT NULL REFERENCES works(work_id) ON DELETE CASCADE, note TEXT, added_at TEXT NOT NULL,
  PRIMARY KEY (name, work_id));

CREATE TABLE outbox (outbox_id INTEGER PRIMARY KEY, ts TEXT NOT NULL, kind TEXT NOT NULL, payload_json TEXT NOT NULL);
```

Column notes:

- `documents.extract_status`: `pending`, `ok`, `extract_failed`, `needs_ocr` (CACHE-FR-10, CACHE-FR-13).
- `documents.decided_by`: `owner` (UI), `agent` (MCP) or `system` (scheduler and collection changes). `decided_channel`: `ui`, `mcp`, `system` or `purge`.
- `files.size_bytes` is `DownloadedFile.size` in `core/models.py`; `files.storage_path` is cleared when the file leaves the cache (archive, purge).
- `embeddings.model` is the model name that encoded the vector (CACHE-FR-21); a change of the default model leaves old vectors usable only for their model, and `reembed_missing` (5.8) fills the new one.
- `chunks_fts` indexes `content`, `section` and `title`, as CACHE-FR-17 requires, through the `chunks.title` column (owner decision, 2026-10-22) (decision 1 in section 10).

### 3.2 Changes against the v1 schema

Each change is the smallest one that a frozen requirement needs. All four are in migration 0001, which no code has created yet, so no migration of existing data is involved. The owner approved `chunks.title`, `documents.pin_direct`, `documents.integrity_at_fetch` and `disk_samples.model_cache_bytes` (owner decision, 2026-10-22).

| Change | Requirement it serves | Why the v1 schema cannot |
| --- | --- | --- |
| `chunks.title` and `title` in `chunks_fts` | CACHE-FR-17 (full-text search indexes content, section and title) | An external-content FTS5 table can index only columns of its content table; `chunks` had no title |
| `documents.pin_direct` | CACHE-FR-37, CACHE-FR-55, CACHE-45 | Without it, leaving the last pinning collection would also unpin a document the owner pinned directly (5.9) |
| `documents.integrity_at_fetch` | CACHE-FR-38 (integrity change since caching), CACHE-35 | Only the current `works.integrity_status` is stored, so a change since caching cannot be told |
| `state.db.disk_samples.model_cache_bytes` | CACHE-FR-57 (cache size by type, including the model cache) | The table had no model cache column. The table belongs to the health component (SPEC-v2 10.1). Approved (owner decision, 2026-10-22): the cache and health LLDs both carry `model_cache_bytes`, and it is part of the `0001_init` schema ([LLD-health-v2](LLD-health-v2.md) 3) |

### 3.3 `state.db` tables the cache writes or reads (SPEC-v2 10.1, migration 0001)

```sql
CREATE TABLE review_batches (batch_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, notified_at TEXT,
  closes_at TEXT NOT NULL, closed_at TEXT, item_count INTEGER NOT NULL);
CREATE TABLE review_events (ts TEXT NOT NULL, doc_id TEXT NOT NULL, batch_id TEXT, from_state TEXT NOT NULL,
  to_state TEXT NOT NULL, decided_by TEXT, channel TEXT);
CREATE TABLE disk_samples (ts TEXT PRIMARY KEY, cache_bytes INTEGER, files_bytes INTEGER, index_bytes INTEGER,
  embeddings_bytes INTEGER, trash_bytes INTEGER, free_cache_vol INTEGER, free_archive_vol INTEGER,
  model_cache_bytes INTEGER);                                          -- v2: last column added
CREATE TABLE maintenance_runs (ts TEXT NOT NULL, check_name TEXT NOT NULL, ok INTEGER NOT NULL, detail TEXT);
```

Retention: `disk_samples` 90 days; `review_batches`, `review_events` and `maintenance_runs` are kept (SPEC-v2 10.1). `batch_id` is a ULID (SPEC 15); the example `rb-2026-11-14` in SPEC 11.3 is illustrative text.

**Which database says a batch is open.** `state.db.review_batches` is authoritative for the batch (SPEC 10 lists review batches under `state.db`). A batch is open when `closed_at IS NULL` and `now < closes_at`; a batch past `closes_at` counts as closed even if the close job has not yet run. `cache.db.documents.review_batch_id` is only the membership pointer: an item belongs to a batch when `review_batch_id = batch_id` and `state = 'expiring'`. `LifecycleService.decide` reads the batch from `state.db`, then the items from `cache.db`; it makes no write to `review_batches` (decision 5 in section 10).

### 3.4 Stores and migrations (SPEC-v2 3.5)

`Migrator` applies `migrations/<db>/NNNN_*.sql` in order, each inside an explicit `BEGIN IMMEDIATE` and `COMMIT`, sets `PRAGMA user_version` and refuses a newer database (LLD-platform v2 3.1; PLAT-50, PLAT-51). The cache schema is `platform/migrations/cache/0001_init.sql`. `CacheStore` exposes typed methods only; no SQL appears outside `platform/stores.py` and the `services/*` repositories (SEC-INV-8). In M2 the cache component adds the repositories `WorksRepo`, `DocumentsRepo`, `ChunksRepo`, `EmbeddingsRepo`, `CollectionsRepo` and `OutboxRepo` in `services/` (one module each is not required; they live with their service).

### 3.5 Cross-database events (SPEC-v2 3.5)

`documents.decided_*` in `cache.db` is authoritative. Each lifecycle transition also writes a row to `cache.db.outbox` in the same transaction (`kind = "transition"`; `payload_json` holds `doc_id`, `batch_id`, `from_state`, `to_state`, `decided_by`, `channel`, `ts`). The `outbox_drain` job (every 5 s, platform) copies rows to `state.db.review_events` and then deletes them. The copy is idempotent: the drainer writes the event with `INSERT OR IGNORE` keyed by `(ts, doc_id, to_state)` [assumption: a unique index on those columns is added in the health migration; without it a crash between insert and delete could duplicate one event], then deletes the outbox row, so neither database needs a transaction that spans both. Decisions that are accepted but take effect later (an archive request, 5.7) write a row with `kind = "decision"` at request time and the `transition` row when the archive is verified.

### 3.6 File layout (SPEC-v2 2)

`paths.data_dir` holds `cache.db`, `files/`, `trash/` and `tmp/`, mode `0700`. Stored files live at `data_dir/files/<sha256[:2]>/<sha256>.<ext>`; trashed files at `data_dir/trash/<sha256[:2]>/<sha256>.<ext>`; orphans found by maintenance at `data_dir/trash/orphans/<date>/` (5.8). Downloads stream into `data_dir/tmp/<ulid>.part`. Nothing the lifecycle depends on is in `~/Library/Caches` (PLAT-9; CACHE-FR-59).

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves. Reviewed by `security-reviewer` at Gate 3 (2026-10-23); drafted by the `component-designer` at the caller's instruction, and no policy is invented here.

| Enforcement point | Rule | Source |
| --- | --- | --- |
| Request gate | Every request to `/mcp`, `/api` and `/ui` passes the one deny-by-default gate in `app.py` (bearer, Host and Origin); UI session checks stay in `ui/`. The cache adds no route outside it | LLD-security v2 4.3; SEC-11, SEC-12 |
| Every MCP tool | No tool accepts a local path or SQL; `id_or_url` accepts an identifier or an `https` URL only; files are written only under the cache root | CACHE-FR-4; CACHE-INV-3; SEC-25; CACHE-11 |
| `@tool_boundary` | Every string in a successful result is redacted for registered secrets, including `Untrusted.content` and snippets | SEC-28 (owner decision, 2026-10-22; proposed in PRD-security v3) |
| `Downloader` | https only; host policy re-checked on every hop; public IPs only, with the connection pinned to the checked IP; no `CredentialResolver`, so a download never carries a credential | CACHE-1; CACHE-INV-4; SEC-8; LLD-platform v2 4.4 |
| `fetch` with a caller URL | The URL is downloaded under `DownloadPolicy(public_any=True)` with the same https, address, size and magic-byte checks; it is never resolved from a local path | CACHE-FR-2; CACHE-FR-4 [assumption: the sources fix the host policy only for source locations] |
| `library` | Has no discard action | CACHE-48; CACHE-INV-7 |
| `cache_review_decide` | One method, `LifecycleService.decide`, for MCP and UI: the batch must be open (3.3), every `doc_id` must belong to it, every `choice` must be one of four; otherwise the whole call is rejected before any write; records `decided_by="agent"`, `decided_channel="mcp"`; a discard goes to the trash only and notifies the owner at once | CACHE-34; CACHE-FR-35; SEC-20 |
| MCP surface | There is no hard-delete tool and no tool that submits a job of a maintenance fix kind | SEC-INV-9; SEC-20 |
| Maintenance fix jobs (`rebuild_fts`, `reembed_missing`, `clean_orphans`, `backup_state`) | `JobService.submit` accepts these kinds only with `params.confirmed_by` set to `ui` or `cli`, which only the UI action (after `hx-confirm`) and the CLI set; the retry action resubmits the same params through `JobService.submit` | CACHE-47; CACHE-FR-58; UI-FR-3; UI-FR-13 |
| UI actions (discard on the Cache page, review, undo, reconcile, rebuild) | UI session cookie `rmcp_session`; every POST requires `X-CSRF-Token`; Host and Origin checks | LLD-ui v2; LLD-security v2 E3, E7, E8 |
| `ArchiveService.reindex` | Reads the Drive folder only through `ArchiveReader`, which has no write method; opens files `rb`; copies to `tmp/` and never writes in the Drive folder | CACHE-INV-6; CACHE-60; CACHE-62 |
| Backup Drive copy | Off by default; never uses the local fallback; writes only under `_state/` in the confirmed target; a security-relevant default that is the owner's ("Other decisions of this version" in section 10) | LLD-platform v2 3.3; PLAT-FR-57 |
| Webhook URL | `https`, or `http` on loopback only; no credentials, query or fragment in the URL; the token is the Keychain item `NOTIFY_WEBHOOK_TOKEN` | LLD-security v2 E42; SEC-31 (owner decision, 2026-10-22) |
| Server instructions | Cache review decisions must come from the owner's explicit words | SPEC-v2 7.3; PLAT-61 |
| Clients | Clients reach the daemon only through the stdio shim; none holds the daemon token | SEC-INV-10; SEC-26 |

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

### 5.1 Modules and ownership (SPEC-v2 1 layout)

| Module | Holds | Owner component |
| --- | --- | --- |
| `services/cache.py` | `CacheService`: `fetch`, `read`, `search_cache` | cache |
| `services/lifecycle.py` | `LifecycleService`: `library`, `collections`, `cache_review_list`, `cache_review_decide` logic, `run_review`, `close_due_batches`, `decide`, `summaries`, `trash_purge_notice`, `trash_purge` | cache |
| `services/archive.py` | `ArchiveService`: `archive`, `reconcile`, `reindex`, `check_target`; `ArchiveReader` | cache |
| `services/extract.py` | `extract_pdf`, `extract_html` (run in the worker) | cache |
| `services/chunking.py` | `chunk(...)`, `CHUNKER_VERSION` | cache |
| `services/embeddings.py` | `EmbeddingService`: `passage_embed`, `query_embed`, exact cosine search | cache |
| `services/maintenance.py` | `MaintenanceService`: `daily`, the fix jobs | cache |
| `services/backup.py` | `BackupService`: `backup_state` | cache |
| `services/disk.py` | `DiskService`: `sample` (design in 5.8) | health (file owner in `sdd.config.json`); cache requirement CACHE-FR-57 |
| `services/cite.py` | `cite` (collection export) | search; this component supplies `CollectionsRepo.members(name)` |
| `services/legacy_import.py` | `LegacyImportService` | migration |
| `mcp_app/tools_library.py`, `mcp_app/tools_review.py` | Tool wrappers for the cache tools | search paths (`src/research_mcp/mcp_app`); design here |
| `platform/download.py`, `workers.py`, `jobs.py`, `scheduler.py`, `stores.py` | `Downloader`, `WorkerRunner`, `JobService`, `Scheduler`, `CacheStore` | platform |

Interfaces other components call (Python; models are Pydantic, `Clock` and `Sleeper` are injected):

```python
class CacheService:
    async def fetch(self, id_or_url: str | list[str], *, prefer: list[str], pin: bool) -> FetchResult | JobHandle: ...  # a list of 1..20 returns a job
    async def read(self, doc_id: str, *, pages: str | None, section: str | None,
                   chunks: str | None, max_chars: int, cursor: str | None) -> ReadWindow: ...
    async def search(self, query: str, *, mode: str, doc_ids: list[str], collection: str | None,
                     states: list[str], limit: int) -> CacheSearchResult: ...

class LifecycleService:
    async def run_review(self, now: datetime) -> str | None: ...          # batch_id, or None when nothing is due
    async def close_due_batches(self, now: datetime) -> int: ...
    async def decide(self, batch_id: str, decisions: list[Decision], *, decided_by: Literal["owner","agent"],
                     channel: Literal["ui","mcp"]) -> ReviewDecisionResult: ...
    async def set_pin(self, doc_ids: list[str], pinned: bool, *, decided_by: str, channel: str) -> list[ActionResult]: ...
    async def discard(self, doc_ids: list[str], *, decided_by: str, channel: str) -> list[ActionResult]: ...   # UI Cache page only
    async def undo_discard(self, doc_ids: list[str], *, decided_by: str, channel: str) -> list[ActionResult]: ...
    async def summaries(self, work_ids: list[str]) -> dict[str, list[DocSummary]]: ...
    async def trash_purge_notice(self, now: datetime) -> int: ...
    async def trash_purge(self, now: datetime) -> int: ...

class ArchiveService:
    async def archive(self, doc_id: str) -> ArchiveResult: ...
    async def reconcile(self) -> ReconcileResult: ...
    async def check_target(self) -> TargetHealth: ...      # exists, writable, access, drive_app_running, free_bytes
    async def reindex(self, *, dry_run: bool, progress: ProgressSink) -> ReindexReport: ...

class FileProviderPort(Protocol):      # real implementation in the macos extra; FakeFileProvider in tests
    def is_uploaded(self, path: Path) -> bool | None: ...      # None means unknown
class ProcessProbePort(Protocol):      # real: pgrep -x "Google Drive"; fake in tests
    def running(self, name: str) -> bool: ...
```

`discard` has no MCP caller: the `library` tool never calls it and `cache_review_decide` reaches a discard only through `decide` (CACHE-INV-7).

### 5.2 Fetch pipeline (HLD-v3 6; SPEC 6, 11.2; CACHE-FR-1 to CACHE-FR-7, CACHE-FR-20)

```
 fetch(id or url)
   -> works.resolve -> OA locations from all sources -> choose by preference
   -> downloader: https, host policy per hop, public IPs only, byte cap, magic bytes, atomic write, sha256
   -> worker: extract (PyMuPDF, limits) -> chunk (token, section aware) -> embed (passage)
   -> cache.db: document (state=cached, expires_at=+120d), file, extraction, chunks, FTS, vectors
   -> envelope {doc_id, summary, pages, chunks, coverage}
```

1. **Normalize the input.** An `https` URL, or an identifier that `core.ids` can parse; anything else is `invalid_argument` (a path, `file:`, `http:`). A list of 1 to 20 items is validated item by item (one bad item rejects the whole call) and submitted as one `fetch_many` job; the call returns a `JobHandle` (`job_id`, `state`) (owner decision, 2026-10-22). A list of one item also returns a job.
2. **Existing document.** Look the work up by identifier. If a document of that work is `cached`, `pinned`, `expiring`, `kept` or `archived`, return it (`reused = true`); with `pin = true`, also pin it (5.5). If its `extract_status` is `extract_failed`, run extraction again on the stored file (an archived document without a cached file is not re-extracted). A work whose only documents are `discarded` gets a new document built from the stored `fetch_recipe_json` (CACHE-12; CACHE-FR-6).
3. **Choose a location.** `WorksService.resolve(id_or_url)` returns the work and its OA locations from all sources (SRCH-FR-17). The service orders them by `prefer` if given, else by the configured preference order (publisher OA, arXiv, PMC, repository, Unpaywall or OpenAlex location, CORE, OSF; CACHE-FR-1) and tries them in order until one downloads. The location's `host policy` comes from its source (`policy.allowed_hosts`); a caller URL uses `public_any` (4).
4. **Check, then download** through `Downloader` (5.13). When the chosen location is a PDF (its media type or `.pdf` path) and the `pdf` extra is missing, the pipeline stops before any download with `unconfigured` and the install command, and records nothing (owner decision, 2026-10-22). A file found to be a PDF only at the magic-byte check stops the same way and the `.part` file is removed [assumption: a mislabelled file falls back to the same result] (decision 9).
5. **Record.** In one `cache.db` transaction: the `works`/`identifiers`/`source_records` rows (the works component merges; this service writes through `WorksRepo`), a `documents` row (`state = 'cached'`, `expires_at = cached_at + cache.retention_days`, `fetch_recipe_json` with the identifier, the chosen location URL, the source and the `prefer` list, `integrity_at_fetch = works.integrity_status`), a `files` row with the provenance of CACHE-FR-5 (`final_url`, `http_status`, `etag`, `last_modified`, `fetched_at`; `license` and `oa_status` go to the document), and an outbox row (`(none)` to `cached`).
6. **Extract, chunk, embed** in worker tasks (5.3), each its own subprocess, at most two at once. A crash, kill or timeout sets `extract_status = 'extract_failed'` and the document stays stored (CACHE-FR-10; CACHE-14). On success, one transaction writes the `extractions` row, the `chunks` (the trigger fills `chunks_fts`) and the `embeddings`, then sets `extract_status = 'ok'` or `'needs_ocr'`.
7. **Return** `FetchResult`. `summary` is the work's abstract, or the first 600 characters of the text, inside `Untrusted`. `coverage` is embedded chunks divided by all chunks of the document.

`fetch` for one item runs inline and reports progress through `Context.report_progress`. A list of items, and every crawl, runs as a job (5.12; CACHE-FR-7; owner decision, 2026-10-22).

### 5.3 Extraction, chunking and embeddings (SPEC-v2 8.2; CACHE-FR-10 to CACHE-FR-14, CACHE-FR-20 to CACHE-FR-23)

- **`extract_pdf`** runs in the worker with PyMuPDF (extra `pdf`). Page count is `len(doc)`. Text is taken per page with `sort=True`, the outline from `get_toc()`, and the references section is tagged `section="References"`. A document over `limits.pdf_pages` ends as `extract_failed` and the reason `page_cap` goes to the log [assumption: the sources say only that page count is limited]. A document with no extractable text on any page sets `needs_ocr` on the extraction and `documents.extract_status = 'needs_ocr'`; OCR itself is out of scope (CACHE-FR-13; CACHE-17).
- **`extract_html`** parses with `selectolax` (a base dependency). It drops nav, header, footer, script and style, keeps h1 to h3 as section markers, and outputs text with paragraph breaks. A single-line page of 36 KB yields chunks under the hard cap (CACHE-16).
- **`chunking.chunk(text_by_page, sections, target_tokens=400, overlap_tokens=50, hard_cap_chars=settings.limits.chunk_hard_cap_chars)`**, `CHUNKER_VERSION = "2.0"`:
  - tokens are counted with a fast whitespace-and-punctuation tokenizer; 400 target tokens with 50 overlap is 12.5 percent, inside 300 to 500 tokens and 10 to 15 percent (CACHE-FR-11);
  - the text is split on paragraphs, then on sentences (a regex with an abbreviation guard), then at the hard cap; a word is never split;
  - page numbers, character offsets, the section heading and the document title are recorded for every chunk (`chunks.title` receives the work's title, so the title is searchable);
  - the cap holds for any input, including text with no whitespace, which is split at the cap on a character boundary after the last safe break (CACHE-FR-12).
- **Extraction record.** Each `extractions` row stores `parser` (`pymupdf` or `selectolax`), `parser_version`, `chunker_version`, `needs_ocr` and `extracted_at` (CACHE-FR-14; CACHE-18). A later chunker version re-extracts selectively: `MaintenanceService` lists extractions whose `chunker_version` differs from `CHUNKER_VERSION` and re-runs them through the same worker tasks; the old chunks are deleted in the transaction that inserts the new ones.
- **Embeddings** (extra `embeddings`):
  - the default model is `fastembed` `BAAI/bge-small-en-v1.5` (384 dimensions), cached in `paths.model_cache_dir`; the name is a constant `DEFAULT_EMBEDDING_MODEL` in `services/embeddings.py`, and each stored vector records its model;
  - chunks are encoded with `passage_embed` and queries with `query_embed` (CACHE-FR-22; CACHE-23, verified with a fake model that records calls);
  - every chunk of a fetched document is embedded in the `embed` worker task, one task per document, in batches (CACHE-FR-20); vectors are keyed by `(content_sha256, model)`, so identical chunk text shares one vector (CACHE-FR-21);
  - vectors are float32 little-endian BLOBs; they are removed with their chunks when no remaining chunk has the same `content_sha256` (CACHE-22);
  - without the extra, the document is stored without vectors and `coverage` is 0.0; `reembed_missing` (5.8) fills them after the extra is installed.
  - search computes exact cosine similarity with NumPy over the stored vectors. `sqlite-vec` can replace it later behind the same function (ADR 0008).

### 5.4 Local search (SPEC-v2 8.3; CACHE-FR-16, CACHE-FR-17, CACHE-FR-24, CACHE-FR-52)

`CacheService.search` has three modes. A document is a candidate when its `state` is in `states` (empty means all states except `discarded`) and, when given, its id is in `doc_ids` or its work is a member of `collection`.

- **Keyword.** FTS5 with `bm25(chunks_fts, 1.0, 0.5, 0.5)` over `content`, `section` and `title`, with prefix queries (`prefix='2 3'`). The v1 query sanitizer is ported; if FTS5 raises a syntax error the query is retried as a quoted literal and `warnings` carries `query_literal_fallback` (CACHE-20). A hit in a chunk whose section is `References` has its score multiplied by 0.5 in Python before ranking. The candidate filter is part of the SQL (a join with `documents`), so a filtered query still returns up to `limit` hits.
- **Semantic.** The top 50 chunks by cosine similarity between the `query_embed` vector and the stored vectors of candidate chunks.
- **Hybrid** (default). Reciprocal rank fusion of the keyword and semantic lists, `1 / (60 + rank)` summed per chunk, then the best chunk per document is kept [inferred: the constant 60 is the usual value; the sources name only reciprocal rank fusion].

Snippets come from `snippet(chunks_fts, 0, '[', ']', ' ... ', 12)` for keyword hits and the 300 characters around the best sentence for semantic hits; each is wrapped in `Untrusted`. Each hit carries `state` and, for archived documents, `archive_path` (CACHE-61). The result reports `coverage` (embedded chunks divided by all chunks of the candidate documents), `mode_used` and `embeddings_available`.

**Without the embeddings extra** a `semantic` or `hybrid` request runs keyword-only: `mode_used = "keyword"`, `embeddings_available = false`, `coverage = 0.0`, and `warnings` carries `embeddings_unavailable` (decision 7 in section 10; CACHE-24).

**`read`** (CACHE-FR-15; CACHE-19): exactly one selector or none; `pages` and `chunks` are inclusive ranges; `section` is an exact, case-insensitive heading match (several chunks may share it). The window joins whole chunks in `ord` order until `max_chars` is reached, never cutting a chunk, except that one chunk longer than `max_chars` is cut at a word boundary. The cursor holds the extraction id and the next `ord`. `read` sets `documents.last_accessed_at`. Archived documents read from `cache.db` and report `archive_path`; the original PDF is read from Drive by the owner, not through a tool (CACHE-FR-52).

### 5.5 State transitions (SPEC-v2 9.1; CACHE-FR-30, CACHE-FR-33, CACHE-FR-34, CACHE-FR-36, CACHE-FR-37; CACHE-30)

The lifecycle state machine (ADR 0007, ADR 0011):

```
 cached -[3 days before expiry, daily 09:00]-> expiring -[archive]-> archived
   ^  |                                          |  |-[discard]-> discarded (7-day trash, notice 24 h before purge, then files removed)
   |  |-[pin]-> pinned                            |
   |                                             |-[no answer for 24 h]-> kept -[7 days]-> expiring
   |-[keep another 120 days]---------------------|
```

`LifecycleService` implements the table below, one method path per row, and the test has one case per row with a `FakeClock` (CACHE-30). Rows 12 to 16 are new in v2 (decision 3 in section 10): v1 had no row for the pin transitions that CACHE-FR-37, CACHE-FR-33 and CACHE-FR-55 and the tools `library pin`, `fetch(pin=True)` and `collections` need.

| # | From | Event | To | Side effects |
| --- | --- | --- | --- | --- |
| 1 | (none) | fetch | cached | `expires_at = cached_at + 120 d`; if the work is in a pinning collection, goes straight to `pinned` (row 14) |
| 2 | cached | review run, `expires_at - now <= 3 d` (also if already past) | expiring | `review_batch_id` set; decided_by `system` |
| 3 | kept | review run, `next_ask_at <= now` | expiring | `reask_count += 1` |
| 4 | expiring | archive requested (owner in the UI, or agent through `cache_review_decide`) | archived (when the archive job verifies) | Archive job (5.7); `decided_*` recorded at request time |
| 5 | expiring | discard (owner in the UI, or agent through `cache_review_decide`) | discarded | File to trash; `trash_until = now + 7 d`; MCP discards notify at once |
| 6 | cached, pinned or kept | owner discard on the UI Cache page (confirmed) | discarded | As row 5 |
| 7 | expiring | keep | cached | `expires_at = now + 120 d`; the choice "keep" |
| 8 | expiring | pin, or membership in a pinning collection | pinned | `expires_at = NULL`; `pin_direct = 1` for a pin choice |
| 9 | expiring | batch closes with no decision recorded (`now >= closes_at`) | kept | `next_ask_at = now + 7 d`; files stay; decided_by `system` |
| 10 | cached, pinned or kept | `library archive` | archived (when verified) | Archive job; not destructive (the copy is verified before removal) |
| 11 | discarded | undo before `trash_until` (UI Archive page, or `library restore`) | cached | Restore files from trash; `expires_at = now + 120 d`; `trash_until`, `discarded_at` cleared |
| 12 | cached or kept | `library pin`, `fetch(pin=True)`, UI Pin | pinned | `pinned_at = now`; `expires_at = NULL`; `pin_direct = 1` |
| 13 | pinned | `library unpin`, UI Unpin | cached, unless a pinning collection still holds the work | `pin_direct = 0`; `expires_at = now + 120 d`; if a pinning collection holds the work the state stays `pinned` and the result says so |
| 14 | cached, kept or expiring | work added to a pinning collection | pinned | `pin_direct` unchanged; decided_by `system`, channel `system` |
| 15 | pinned | work removed from its last pinning collection | cached, if `pin_direct = 0`; stays pinned if `pin_direct = 1` | `expires_at = now + 120 d` when it returns to cached |
| 16 | discarded | `trash_until` passes | discarded | Purge job (below); `purged_at` set; the work, CSL and recipe are kept |

- `decided_by` is `owner` for the UI and `agent` for MCP, `system` for rows 2, 3, 9, 14 and 15; `decided_channel` is `ui`, `mcp`, `system`, or `purge` for row 16. Every transition writes an outbox row (3.5).
- **Expiry never deletes.** A document past `expires_at` waits for the next review run; row 2 selects it whatever its age, so a Mac that slept for weeks produces one batch and no silent loss (CACHE-INV-1; CACHE-33).
- **Discard** moves the file to `trash/`, keeps chunks and vectors until the purge (so an undo is complete), and removes the document from `search_cache` and `read` at once (`not_found`).
- **Trash purge.** At 10:00 each day, `trash_purge_notice` lists the items whose trash ends within 24 hours in one notification with a link to the Archive page. `trash_purge` then, for each document whose `trash_until` has passed: removes its file (subject to the file deletion rule below), deletes its chunks (the trigger clears the FTS rows) and any embeddings no other chunk uses, sets `files.storage_path = NULL` and `purged_at`, and keeps the work, the CSL snapshot, the fetch recipe, the `files` row and the lifecycle record. Only a document in `discarded` can be purged, and `discarded` is reachable only through a recorded decision (rows 5 and 6), so the purge cannot delete an unreviewed item (CACHE-INV-1).
- **File deletion rule** (CACHE-FR-36; CACHE-INV-2): a stored file is removed only when no `files` row with the same `sha256` belongs to a document in a non-terminal state (`cached`, `pinned`, `expiring`, `kept`), and no other discard of it is still within its trash period. A discard whose file is shared does not move the file; its undo restores nothing. When an undo finds the file already back in `files/` (a later fetch stored the same bytes), it drops the redundant trash copy.
- **Undo window** is `cache.trash_days` (7) from `discarded_at`; the notice is 24 hours before.

### 5.6 Review batch (SPEC-v2 9.2; CACHE-FR-31 to CACHE-FR-35, CACHE-FR-38; CACHE-31, CACHE-32, CACHE-35)

`LifecycleService.run_review(now)` runs as the job `review` at `cache.review_time_local`, or once on catch-up:

1. Run `close_due_batches(now)` first (below).
2. Select candidates: rows 2 and 3 of 5.5. If none, stop: no batch, no notification.
3. In one `cache.db` transaction set the candidates `expiring` with the new `review_batch_id` (a ULID); then insert `state.db.review_batches(batch_id, created_at, notified_at, closes_at, item_count)` with `closes_at = notified_at + cache.batch_open_hours`. If the second write fails, the first is rolled back by a compensating update on the next run [assumption: two databases, no shared transaction; the next run finds `expiring` items with no matching batch row and creates the row].
4. Send one `Notice(kind="cache_review", ...)` through `NotifyService` with `ui_path=/ui/review/<batch_id>`; the same call reaches the webhook channel, which is the one optional message (CACHE-FR-32; CACHE-31).

`close_due_batches(now)`, run by the interval job `review_close` and at the start of each review: for each batch with `closed_at IS NULL` and `closes_at <= now`, set `closed_at`, and move every item of the batch that is still `expiring` with no recorded decision to `kept` (row 9). Items with a recorded decision (an archive request still running) are left to their job. Closing is idempotent.

`decide(batch_id, decisions, decided_by, channel)`:

1. Load the batch from `state.db`; unknown id is `not_found`; closed (3.3) is `invalid_argument`.
2. Validate every decision: the `doc_id` belongs to the batch, the `choice` is one of `archive`, `discard`, `keep`, `pin`, and no `doc_id` repeats. Any failure rejects the whole call before a write (CACHE-34).
3. Apply per item in one transaction: `keep` (row 7), `pin` (row 8), `discard` (row 5), `archive` (row 4: record `decided_*`, write a `decision` outbox row, submit the job `archive`). Bulk decisions from the UI are the same call with one decision per item (CACHE-32).
4. For `channel = "mcp"` and at least one discard, send `Notice(kind="cache_mcp_discard")` listing the titles (at most 10, then a count) with `ui_path=/ui/archive` (CACHE-34).

`cache_review_list(batch_id)` returns the batch (default: the newest open one) with, for each item: title, citation, source, size, age, times asked (`reask_count`), last access, and the integrity change (CACHE-FR-38; CACHE-35). The integrity change is text such as `retracted since caching` when `works.integrity_status` differs from `documents.integrity_at_fetch` and is not `unknown`.

### 5.7 Archive (SPEC-v2 9.3; CACHE-FR-45 to CACHE-FR-50; CACHE-40 to CACHE-44)

`ArchiveService.archive(doc_id)` runs as the job kind `archive` (one job per request, many documents allowed, resumable by document):

1. **Resolve the target.** Use `archive.confirmed_path` (required when `archive.target` is `auto`), then add `archive.subfolder` with `{year}` set to the year of archiving. If `archive.target` is `auto` and nothing is confirmed, the job ends `awaiting_confirmation`, the documents keep their state, and one notice asks the owner to confirm the folder; nothing goes to the fallback (the sources say that archiving waits for the confirmation). `check_target()` then checks:
   - the folder exists;
   - it is writable, by writing and replacing the sentinel `.research-mcp-probe`;
   - free space is greater than the file size plus 100 MB;
   - the `Google Drive` app process is running (`ProcessProbePort.running("Google Drive")`, `pgrep -x "Google Drive"`).
2. **Name the files.** The slug is `<first-author-family>-<year>-<title-key first 6 words>-<sha256[:6]>`, the files `<slug>.<ext>` and `<slug>.meta.json` (contract). An existing file with the same name and the same SHA-256 is reused.
3. **Write in the target folder.** Write the hidden temporary file `.<slug>.<ext>.partial` there, `fsync` it, rename it to `<slug>.<ext>`, read the file back and compare its size and SHA-256 with the cached copy. Write the sidecar the same way. Drive for desktop may upload a hidden partial file; the rename replaces it. A mismatch deletes the new Drive copy, keeps the cached copy and leaves the document in its state (CACHE-41; CACHE-INV-5).
4. **On success**, in one transaction: `state = 'archived'`, `archive_path`, `archived_at`, `archive_upload_state = 'pending'` (or `unknown`, step 6), `expires_at = NULL`; clear `files.storage_path`; write the outbox row. Then remove only the cached file, subject to the file deletion rule in 5.5. The extraction, chunks, FTS rows and embeddings **stay**, so `search_cache` and `read` work on the archived document as before (ADR 0011; CACHE-43). `library list`, `get_work` (through `summaries`) and `cite` report the archive path and date and work from stored metadata.
5. **If the target check fails** (missing, not writable, TCC denial, Drive app not running): use `archive.fallback` with `{year}` filled, set `archive_fallback = 1`, and emit the `archive_target_unavailable` health event through the `HealthEventPort` (`HealthEvent(kind, subject, severity, ui_path, dedupe_key)`, LLD-health-v2) (CACHE-42; CACHE-FR-48). The same write and verify steps apply. `ArchiveService.reconcile()` runs hourly as the job `archive_reconcile` and moves fallback files into the Drive target with the same verification, then sets `archive_fallback = 0` and updates `archive_path`; it does nothing when no fallback exists.
6. **Upload confirmation.** In the same hourly `reconcile()`, for each `pending` archive read `FileProviderPort.is_uploaded(path)` (real implementation: `NSURLUbiquitousItemIsUploadedKey` through pyobjc, extra `macos`). True sets `uploaded`. Without the extra, or when the key is unavailable, the state is `unknown` and no stall is reported (PLAT-84). An item still `pending` 24 hours after `archived_at` sends `Notice(kind="archive_upload_stall")` once (CACHE-44). `[inferred]` whether the Google Drive File Provider answers this key is confirmed only on the Mac by owner check OC-04.

**Sidecar** fields are in the contract. **Target health** (`check_target`) is the data that `HealthService` probes for the archive-folder local target of the source board (HLTH-FR-5) and that `doctor` reports as `archive_target` and `archive_access` (CACHE-FR-50; decision 8 in section 10): `exists`, `writable`, `access` (`granted`, `tcc_denied` or `unknown`), `drive_app_running` and `free_bytes`. The cache adds no row of its own to the board.

**macOS privacy (TCC).** Files in `~/Library/CloudStorage` are protected. The first archive write by the daemon's interpreter may need the owner's consent, and a background process may get no prompt at all. `research-mcp install` runs the sentinel write once in the foreground, so the prompt appears while the owner is present, and shows the detected folder for the owner to confirm (it then runs `config set archive.confirmed_path`). `doctor` runs `archive_access`, which writes and removes the sentinel, and reports `tcc_denied` with the fix: grant the daemon's interpreter Files and Folders access to Google Drive in System Settings, Privacy & Security (OC-13; HLTH-41).

### 5.8 Disk and integrity (SPEC-v2 9.4; CACHE-FR-57, CACHE-FR-58; CACHE-46, CACHE-47)

**`DiskService.sample()`** (file `services/disk.py` is the health component's; the sampling rules are this component's requirement) runs every 15 minutes as the job `disk_sample` and writes one row to `state.db.disk_samples`: bytes of `cache.db` (`cache_bytes`), of `files/` (`files_bytes`), of the FTS and index pages (`index_bytes`, from `dbstat` when available, else the FTS shadow tables' size), of the embeddings table (`embeddings_bytes`), of `trash/` (`trash_bytes`), of the model cache (`model_cache_bytes`), and free space on the cache volume and on the archive volume. Thresholds: a warning when the cache total is above `disk.cache_warn_bytes` (5 GB) or free space is below `disk.free_warn_bytes` (15 GB); a critical level below `disk.free_crit_bytes` (5 GB). A notice (`disk_warn` or `disk_critical`) is sent when the level changes, not at every sample; both have `warning` severity, because critical means installation integrity only ([LLD-health-v2](LLD-health-v2.md) 5.8; owner decision, 2026-10-22).

**`MaintenanceService.daily()`** runs as the job `maintenance_daily` and records each check in `maintenance_runs`:

- `PRAGMA quick_check` on both databases;
- `INSERT INTO chunks_fts(chunks_fts) VALUES('integrity-check')`;
- missing-file scan: a `files` row with a `storage_path` that does not exist (documents not `archived` or purged);
- orphan-file scan: a file under `files/` with no `files` row;
- orphan-embedding scan: an `embeddings` row whose `content_sha256` no chunk uses.

Failures appear on the Maintenance page with a fix action. Fix actions are job kinds that need `params.confirmed_by` (4):

| Job kind | Does |
| --- | --- |
| `rebuild_fts` | `INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')`; also refreshes `chunks.title` from the work title |
| `reembed_missing` | Embeds chunks that have no vector for the current model, in batches in the worker; resumable by cursor |
| `clean_orphans` | Moves orphan files to `trash/orphans/<date>/` (purged after `cache.trash_days` by the normal purge) and deletes orphan embeddings (derived data, rebuildable) [assumption: orphans are moved, not deleted, to honor CACHE-INV-1 in spirit] |
| `backup_state` | Runs `BackupService.backup_state()` now (5.11) |

### 5.9 Collections (SPEC-v2 9.5; CACHE-FR-55; CACHE-45, CACHE-63)

Collections do not pin by default (`pin_members` defaults to 0). `collections` supports `create`, `add`, `remove`, `list` and `show` (CACHE-45); the export is `cite` with `collection=<name>` (CACHE-63), which calls `CollectionsRepo.members(name) -> list[str]` (work ids in `added_at` order) and formats every member.

- `pin_members` is fixed at creation. A collection created with `pin_members=1` pins every document of its member works that is `cached`, `kept` or `expiring` (row 14), and a work fetched later into that collection is pinned at creation.
- Removing a work from its last pinning collection returns its documents to `cached` with a fresh 120 days if `pin_direct = 0` (row 15). A document the owner pinned directly stays pinned (decision 4 in section 10; (owner decision, 2026-10-22)).
- `unpin` on a document that a pinning collection still holds keeps it `pinned` and says so in the result.

### 5.10 Archive rebuild (SPEC-v2 9.7; CACHE-FR-51; CACHE-60, CACHE-62)

`ArchiveService.reindex(dry_run, progress)` runs as the job kind `archive_reindex`, started from the UI Archive page or `research-mcp archive reindex [--dry-run]`. It is a resumable job (cursor: the last relative path processed).

1. **Walk read-only.** `ArchiveReader` is constructed with the confirmed target and the fallback folder. It exposes `iter_files() -> Iterator[ArchiveEntry]` (year folders matching the `archive.subfolder` pattern, and the fallback folder; the `_state/` folder of the backup copy is skipped), `read_sidecar(entry) -> dict` and `copy_to(entry, dest_in_tmp)`; it has no write, rename or delete method and opens files `rb`. Files without a sidecar are listed in the report and left alone (CACHE-INV-6).
2. **Per sidecar**, look the work up by its identifiers. If it is missing, create the work, identifiers and an `archived` document (`archive_path`, `archived_at`, `kind` from the extension, `source`, `origin_url` from `original_url`, `fetch_recipe_json` built from `original_url`, `license` and `oa_status` NULL, `cached_at = fetched_at`). Otherwise verify that the stored `sha256` equals the sidecar's `sha256` and the file's; a difference is counted as mismatched and nothing is changed.
3. **Re-extract** when the document has no extraction, chunks or embeddings for the current chunker and model: copy the file to `data_dir/tmp`, run extraction and embedding in the worker, write the rows, delete the temporary copy.
4. **Report.** Write `state_dir/imports/<timestamp>/archive-reindex.json` and `.md` with the counts of the contract. With `dry_run`, no `cache.db` row is written and the report says `dry_run: true`.

The Drive folder is byte-for-byte unchanged after the job, including files without sidecars (CACHE-62): the test hashes every file and compares the folder listing and modification times before and after.

### 5.11 Backups (SPEC-v2 9.8; CACHE-FR-59, CACHE-49; PLAT-FR-57)

`BackupService.backup_state()` runs as the job `backup_state` nightly at 03:30. The platform requirement and the keys are in LLD-platform v2 3.3; this is the service design.

1. Create `state_dir/backups/.tmp-<local date>/` (mode `0700`).
2. In a worker thread (`anyio.to_thread`), copy `state.db` and `cache.db` with the SQLite online backup API (`sqlite3.Connection.backup`, in steps so writers continue), then copy `config.toml`. Files are mode `0600`. Stored files and the trash are not backed up.
3. Open each database copy and run `PRAGMA integrity_check`; a failure keeps the folder for inspection under `.failed-<date>`, writes a `maintenance_runs` row `backup_state` with `ok = 0`, and prunes nothing.
4. Rename the temporary folder to `state_dir/backups/<local date>/`, replacing a folder of the same date.
5. **Prune** nightly folders (names that match `YYYY-MM-DD`) beyond `backup.keep` (7), oldest first (owner decision, 2026-10-22). `pre-upgrade-*` folders belong to `research-mcp upgrade` and are not touched here.
6. **Drive copy** (only when `backup.drive_copy = true`; default `false`; owner decision, 2026-10-22). After step 4, copy the day's folder to `<state folder>/<date>/` in the confirmed archive target, where `<state folder>` is `archive.subfolder` with its trailing `{year}` component replaced by `_state` (default `Research Archive/_state`). It uses the same discipline as an archive write (hidden partial name, `fsync`, rename, read back size and SHA-256 for each file), never uses the local fallback, and touches nothing outside `_state/`. If the target is unconfirmed or `check_target` fails, it skips the copy and logs a warning; the local backup still counts. After a verified copy it prunes `_state/` to the newest `backup.keep` date folders. The copy sends `cache.db` (the cached text of papers) and `state.db` to the owner's Drive, which is why it is off by default.

`doctor` `backup_recent` passes when the newest nightly folder is less than 48 hours old (8). Verified by CACHE-49 and owner check OC-10.

### 5.12 Jobs and schedules (SPEC-v2 3.6; CACHE-FR-7, CACHE-FR-56; CACHE-13)

`JobService.submit(kind, params)` is the only way a job starts, including a retry from the UI (UI-FR-13). Job kinds of this component and their params (all JSON):

| Kind | Params | Resumable cursor | Started by |
| --- | --- | --- | --- |
| `fetch_many` | `ids: list[str]`, `prefer`, `pin` | index of the next id | `fetch` with a list of ids (owner decision, 2026-10-22), the legacy import |
| `crawl_site` | `site`, `max_pages` | the frontier of unvisited URLs | tool `crawl_site` |
| `archive` | `doc_ids` | index of the next document | review decisions, `library archive`, UI |
| `archive_reindex` | `dry_run` | last relative path | UI, CLI |
| `rebuild_fts`, `reembed_missing`, `clean_orphans`, `backup_state` | `confirmed_by` | `reembed_missing` only | UI, CLI |

**`crawl_site`** (CACHE-FR-56): `site` must be a configured docs site id (`sources.<id>` with `kind = "docs_site"`, [LLD-sources-v2](LLD-sources-v2.md)); otherwise `unconfigured`. The crawl fetches pages of that site only (the site's allowlisted hosts), HTML only, through the same `Downloader`, with the site's rate policy; each page becomes a `cached` document under the same 120-day lifecycle. Progress is reported per page and the job honors cancel between pages.

Schedules (wall clock, run once on catch-up; LLD-platform v2 5.5). The platform table lists `review`, `digest`, `backup_state`, `maintenance_daily`, `trash_purge_notice` and `trash_purge` (daily), and `disk_sample` and `outbox_drain` (interval). This component needs two more interval jobs, which the platform table must list (decision 6 in section 10):

| Job | Cadence | Does |
| --- | --- | --- |
| `review_close` | every 15 minutes | `close_due_batches(now)` |
| `archive_reconcile` | hourly | `ArchiveService.reconcile()` |

### 5.13 Downloader and workers (platform code; SPEC-v2 3.4, 3.6)

The downloader (`Downloader`, `PinnedTransport`, `DownloadPolicy`, `Resolver`) and the worker runner are owned by the platform component and specified in LLD-platform v2 5.4 and 5.5; they are not repeated. What the cache relies on:

- `Downloader` requires https, resolves through the injected `Resolver`, rejects non-public addresses, pins the connection to the checked IP, follows at most 5 redirects by hand and re-checks scheme, address and host policy on every hop, streams into `data_dir/tmp/<ulid>.part` under the byte cap, checks `Content-Type` and the first bytes (`%PDF-`; `<` for HTML), then `fsync`, SHA-256 and an atomic move to `data_dir/files/<sha256[:2]>/<sha256>.<ext>`, reusing an existing file. It returns `DownloadedFile(sha256, size, media_type, storage_path, final_url, http_status, etag, last_modified)` (CACHE-1, CACHE-2).
- `WorkerRunner` runs `extract_pdf`, `extract_html`, `chunk` and `embed` in one subprocess each: `RLIMIT_CPU` 120 s, wall clock 180 s, RSS sampled every second and SIGKILL past 2 GB, at most 2 at once; a crash ends the task with `extract_failed` (CACHE-14; SEC-23).

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

| Condition | Behavior | Source |
| --- | --- | --- |
| Worker crash, kill, CPU limit (120 s), wall clock (180 s) or RSS above 2 GB | Only that task ends, with `extract_failed`; the document is stored with `extract_status = 'extract_failed'`; the daemon keeps serving | SPEC-v2 3.6; CACHE-14 |
| Document over `limits.pdf_pages` | `extract_failed`; reason `page_cap` in the log | CACHE-FR-10 [assumption] |
| Download fails a check (scheme, address, host policy, media type, magic bytes, byte cap) | Rejected (`blocked_by_policy`, or `too_large` for the cap); at most 5 redirects, each re-checked; the next OA location is tried | CACHE-1 |
| `fetch` argument is a path or non-https URL | `invalid_argument` | CACHE-11 |
| Downloaded file already stored | The existing file is reused | CACHE-2 |
| `fetch` of a cached work | Returns the existing document (`reused`); retries extraction if it had failed; idempotent | CACHE-12 |
| `fetch` of a discarded work | A new document is created from its recipe | CACHE-12 |
| PDF fetched without the `pdf` extra | `unconfigured` with the install command; the `.part` file is removed; nothing is recorded; the check runs before the download (owner decision, 2026-10-22) | PLAT-FR-51 |
| Invalid full-text query syntax | Retried as a literal match; warning `query_literal_fallback` | CACHE-20 |
| Embeddings extra missing | `search_cache` runs keyword-only and says so; stored documents have no vectors until `reembed_missing` | CACHE-24 |
| `cache_review_decide` with an unknown batch | `not_found` | CACHE-34 |
| `cache_review_decide` with a closed batch, a foreign `doc_id`, a repeated `doc_id` or an unknown `choice` | `invalid_argument`; nothing is applied | CACHE-34 |
| Two decisions race for one item | The second finds the item no longer `expiring` and is reported `invalid_argument` for that item; both run in a transaction per call | CACHE-34 |
| Batch closes unanswered | Items without a recorded decision become `kept` with `next_ask_at = now + 7 d`; files stay | CACHE-33 |
| Mac asleep at 09:00 for many days | One review on wake selects everything due; one batch | SPEC-v2 3.6 |
| Archive read-back mismatch | The new Drive copy is deleted; the cached copy and state are kept | CACHE-41 |
| Archive target check fails | `archive.fallback`, `archive_fallback = 1`, `archive_target_unavailable` event; `reconcile` moves the files hourly with the same verification | CACHE-42 |
| Archive folder unconfirmed (`auto`) | Job ends `awaiting_confirmation`; no fallback; one notice | CACHE-FR-45 |
| Archive still `pending` 24 hours after archiving | One `archive_upload_stall` notice | CACHE-44 |
| No pyobjc (extra `macos`) | Upload state `unknown`; no stall reported | PLAT-84 |
| TCC denies the archive write | Treated as a failed target check; `doctor` `archive_access` reports `tcc_denied` with the fix | HLTH-41 |
| Sidecar `sha256` differs from the file during rebuild | Counted as mismatched; nothing changed | CACHE-60 |
| Archive folder file without a sidecar | Listed in the report and left alone | CACHE-60, CACHE-62 |
| Rebuild interrupted | The job resumes from its cursor; re-running is safe (rows are looked up by identifier) | CACHE-60 |
| Trash purge interrupted | Resumes at the next 10:00 run or on catch-up; each document purges in one transaction and the file is removed after the commit, so a crash leaves at worst an orphan file for maintenance | CACHE-36 |
| Stored file shared by SHA-256 with a live document | Not removed (file deletion rule) | CACHE-36; CACHE-INV-2 |
| Backup integrity check fails or the backup fails | Nothing is pruned; a failed `maintenance_runs` row is written | PLAT-FR-57 |
| Backup Drive copy target unconfirmed or unavailable | Copy skipped with a warning; the local backup stands | LLD-platform v2 3.3 |
| Webhook delivery fails | 5 s timeout, at most 2 retries by `NotifyService`; failures logged without the token | LLD-health-v2 |
| Two jobs touch one document (archive and discard) | The transition checks `from_state` inside its transaction; the loser reports the current state | CACHE-30 |

**Idempotency.** `fetch` of an existing work, `library pin` on a pinned document, `close_due_batches`, `reconcile`, `outbox_drain` (3.5), `backup_state` on the same day and the purge are safe to repeat. `cache_review_decide` repeated with the same decisions on the same batch is rejected for items no longer `expiring`.

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

**Settings (SPEC-v2 2; LLD-platform v2 7.1).** The cache keys and defaults are unchanged from v1 and are those of the platform table: `paths.data_dir`, `paths.model_cache_dir`, `limits.download_bytes` (52428800), `limits.pdf_pages` (500), `limits.chunk_hard_cap_chars` (4000), `cache.retention_days` (120, fixed from fetch, ADR 0011), `cache.review_lead_days` (3), `cache.review_time_local` (`"09:00"`), `cache.batch_open_hours` (24), `cache.reask_days` (7), `cache.trash_days` (7), `archive.target` (`auto`), `archive.confirmed_path`, `archive.subfolder` (`Research Archive/{year}`), `archive.fallback` (`~/Research Archive/{year}`), `notify.webhook_url`, `disk.cache_warn_bytes`, `disk.free_warn_bytes`, `disk.free_crit_bytes`, `backup.keep` (7) and `backup.drive_copy` (`false`). Directories are created at daemon start with mode `0700`.

Keys this LLD adds (the platform settings model must add them; decision 11 in section 10):

| Key | Default | Notes |
| --- | --- | --- |
| `cache.crawl_enabled` | `true` | Flag for `crawl_site`. Off: the tool stays listed and returns `disabled` |
| `cache.collections_enabled` | `true` | Flag for the `collections` tool and `cite` with `collection`. Off: `disabled` |
| `archive.reindex_enabled` | `true` | Flag for the archive rebuild job and `research-mcp archive reindex`. Off: the job is refused with `disabled` |

**Clarification from the first M0 attempt (SPEC-v2 0.6).** This row is built by the settings unit; it governs the durable-location check behind CACHE-FR-59. Verbatim; it keeps the old IDs.

| Unit | Section | Requirement |
| --- | --- | --- |
| M0-04 | 2; AT-PLAT-08, AT-PLAT-09 | Paths MUST be normalized (resolving `..`) before the durable-location check. Credential names MUST keep their canonical case across TOML and `RESEARCH_MCP_` environment overrides, so an environment override updates the same credential the TOML defines. |

**Optional behaviors.** No feature-flag PRD exists in this repository, so no registration rule applies; this table follows the platform LLD v2 7.2 form. Every row is safe to switch off: no data is lost, the MCP tool list does not change, and hooks and the daemon still start.

| Flag | Default | Safe to switch off? |
| --- | --- | --- |
| Extra `embeddings` (`fastembed`, NumPy) | Not installed (PLAT-FR-51) | Yes: `search_cache` runs keyword-only and says so (CACHE-24); documents stored without vectors are filled by `reembed_missing` |
| Extra `pdf` (`pymupdf`) | Not installed (PLAT-FR-51) | Yes: a PDF fetch returns `unconfigured` with the install command; HTML fetch and everything already stored are unaffected; checked before the download (owner decision, 2026-10-22) |
| Extra `macos` (pyobjc) | Not installed | Yes: the archive upload state is `unknown` and no stall is reported (PLAT-84) |
| `notify.webhook_url` | none | Yes: the macOS notice and UI banner remain; nothing is queued for the webhook (CACHE-FR-32) |
| `backup.drive_copy` | `false` | Yes: backups stay in `state_dir/backups/`; nothing already in Drive is removed |
| `cache.crawl_enabled` | `true` | Yes: `crawl_site` returns `disabled`; crawled pages already cached keep their lifecycle |
| `cache.collections_enabled` | `true` | Yes: `collections` returns `disabled`; pins already set stay pinned |
| `archive.reindex_enabled` | `true` | Yes: the rebuild is unavailable; the archive and its search are unaffected |
| `archive.confirmed_path` | none | Yes (a setting, not a switch): archiving waits for the owner's confirmation and nothing leaves the cache |

## 8. Observability

> **Owner:** A · **Persona:** `sre`. Reviewed by `sre` at Gate 3 (2026-10-23) against SPEC-v5 12 and 9, PRD-v8 NFR-4 and NFR-12 and PRD-cache; consistent with LLD-platform v2 8 (backups: the last 7 kept, a failed backup prunes nothing, `backup_recent` within 48 hours; PLAT-FR-57); not approved. The thresholds are those of the PRD; no new policy is invented here.

| Signal | Detail | Source |
| --- | --- | --- |
| `state.db.disk_samples` | `DiskService.sample()` every 15 minutes: cache, files, index, embeddings, trash and model cache bytes; free space on the cache and archive volumes. Thresholds `disk.cache_warn_bytes`, `disk.free_warn_bytes`, `disk.free_crit_bytes`; a notice on a level change | CACHE-FR-57; CACHE-46 |
| `state.db.maintenance_runs` | One row per daily check (`PRAGMA quick_check`, FTS `integrity-check`, missing-file, orphan-file, orphan-embedding scans) and per backup | CACHE-FR-58; CACHE-47 |
| `state.db.review_events` | Copied from `cache.db.outbox` for every transition, with `decided_by` and `channel`; the CACHE-OUT-1 measure counts `purge` events with no earlier recorded discard decision for the same document | PRD-cache 2.10; CACHE-OUT-1 |
| Notifications | `cache_review` (one per batch), `cache_mcp_discard` (immediate), `cache_trash_purge_notice` (10:00), `archive_upload_stall` (24 hours), disk levels, `archive_target_unavailable` | 2.5 |
| Health event | `archive_target_unavailable` when the target check fails; the archive-folder local target on the source board comes from `check_target()` | HLTH-FR-5; CACHE-FR-50 |
| `doctor` checks | `archive_target`, `archive_access`, `disk`, `schema_versions`, `review_overdue` (no review missed by more than 24 hours), `backup_recent` (a nightly backup less than 48 hours old) | HLTH-41 |
| `/api/status` | Cache stats (counts and bytes by state), disk, the archive target and its upload states | HLTH-FR-43 |
| Job state | Jobs of 5.12 report progress and failures in `state.db.jobs`; log fields follow PLAT-FR-41 | PLAT-74 |
| `search_cache` coverage | Embedded chunks divided by all chunks of the candidate documents | CACHE-20 |
| Log hygiene | Document text and titles are not logged; the log holds ids, counts, codes and durations only [assumption: derives from NFR-4 and the query-text rule PLAT-FR-42]; a secret in a log line is a breach, not a threshold (NFR-4) | PLAT-FR-42; NFR-4 |

No threshold here traces to a parent NFR; the disk thresholds trace to CACHE-FR-57 and the 24-hour and 48-hour checks to CACHE-FR-50 and HLTH-41.

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3. Reviewed by `test-architect` at Gate 3 (2026-10-23); the file names are planned, not written.

No test in `tests/` cites a cache criterion yet. New and changed tests start their docstring with the criterion (`"""@spec CACHE-30: ..."""`) and the entry point in code carries `# @spec CACHE-30` (AGENTS.md). The downloader tests are written in M0 (unit M0-07); the rest arrive with the M2 units. Fakes: `FakeClock`, a fake `Sleeper`, `FakeProvider`, `FakeNotifier`, an injected `Resolver`, a fake embedding model that records calls, `FakeFileProvider`, `FakeProcessProbe`, `FakeWorkerRunner` where a test does not need a subprocess, the temp Drive folder (`tmp_path/CloudStorage/GoogleDrive-test/My Drive`) and the hostile PDF corpus (`tests/fixtures/pdf/hostile/`) (test plan v4 1.3). The default run makes no network call (NFR-9).

| Criterion | Planned tests | Level | Status |
| --- | --- | --- | --- |
| CACHE-1 | `tests/unit/platform/test_downloader.py::test_rejects_http_private_loopback_linklocal_also_after_redirect`, `test_dns_rebinding_uses_checked_ip`, `test_rejects_media_type_magic_bytes_and_oversize` (test plan v4 2.5, unit M0-07) | unit | planned |
| CACHE-2 | `tests/unit/platform/test_downloader.py::test_atomic_write_by_sha256_and_full_provenance`, `test_existing_file_reused` | unit | planned |
| CACHE-10 | `tests/services/test_cache_fetch.py::test_fetch_picks_best_oa_location_by_preference`, `test_pdf_without_extra_is_unconfigured_before_download` | integration | planned |
| CACHE-11 | `tests/contract/test_tools_cache.py::test_no_cache_tool_accepts_a_local_path` (with SEC-25 in `tests/security/test_path_arguments.py`) | contract | planned |
| CACHE-12 | `tests/services/test_cache_fetch.py::test_cached_work_returns_existing_and_discarded_work_refetches_from_recipe` | integration | planned |
| CACHE-13 | `tests/services/test_cache_jobs.py::test_multi_fetch_and_crawl_run_as_jobs_with_progress_and_cancel`, `test_fetch_list_returns_job_handle_and_bad_item_rejects_all` | integration | planned |
| CACHE-14 | `tests/services/test_extract_worker.py::test_crashing_or_hanging_parser_marks_extract_failed_and_daemon_serves` | integration | planned |
| CACHE-15 | `tests/unit/services/test_chunking.py::test_golden_target_overlap_boundaries_no_split_words_offsets_pages`, `tests/unit/services/test_chunking.py::test_property_no_chunk_over_cap_no_split_word` (Hypothesis) | unit | planned |
| CACHE-16 | `tests/unit/services/test_extract_html.py::test_headings_kept_and_36kb_single_line_page_is_bounded` | unit | planned |
| CACHE-17 | `tests/unit/services/test_extract_pdf.py::test_image_only_pdf_flags_needs_ocr` | unit | planned |
| CACHE-18 | `tests/unit/services/test_extract_pdf.py::test_extraction_records_parser_and_versions` | unit | planned |
| CACHE-19 | `tests/contract/test_tools_cache.py::test_read_windows_by_page_section_chunk_with_cursor_and_bounds` | contract | planned |
| CACHE-20 | `tests/services/test_cache_search.py::test_keyword_semantic_hybrid_literal_fallback_and_coverage` | integration | planned |
| CACHE-21 | `tests/contract/test_tools_cache.py::test_library_list_and_stats_report_state_size_age_expiry` | contract | planned |
| CACHE-22 | `tests/services/test_embeddings.py::test_every_chunk_embedded_keyed_by_hash_and_model_removed_with_chunks` | integration | planned |
| CACHE-23 | `tests/unit/services/test_embeddings.py::test_query_encoding_for_queries_passage_encoding_for_chunks` | unit | planned |
| CACHE-24 | `tests/services/test_cache_search.py::test_without_embeddings_extra_runs_keyword_only_and_says_so` | integration | planned |
| CACHE-30 | `tests/unit/services/test_lifecycle_transitions.py::test_lifecycle_transition_row` (parametrized, one case id per row of 5.5, `FakeClock`) | unit | planned |
| CACHE-31 | `tests/services/test_review.py::test_daily_review_builds_one_batch_one_notification_one_webhook` | integration | planned |
| CACHE-32 | `tests/services/test_review.py::test_per_item_and_bulk_decisions_apply_archive_discard_keep_pin` | integration | planned |
| CACHE-33 | `tests/services/test_review.py::test_ninety_simulated_days_without_answers_delete_nothing` | integration | planned |
| CACHE-34 | `tests/contract/test_tools_cache.py::test_review_decide_rejects_closed_foreign_and_records_agent_mcp_and_notifies_discards` | contract | planned |
| CACHE-35 | `tests/services/test_review.py::test_review_items_show_citation_size_age_asks_access_and_integrity_change` | integration | planned |
| CACHE-36 | `tests/services/test_trash.py::test_discard_keeps_metadata_undo_restores_notice_before_purge_shared_file_survives` | integration | planned |
| CACHE-40 | `tests/services/test_archive.py::test_auto_detects_drive_folder_and_writes_file_and_sidecar_fields` | integration | planned |
| CACHE-41 | `tests/services/test_archive.py::test_readback_verifies_before_cached_copy_removed_and_mismatch_keeps_it` | integration | planned |
| CACHE-42 | `tests/services/test_archive.py::test_unavailable_target_uses_fallback_warns_and_reconcile_moves` | integration | planned |
| CACHE-43 | `tests/services/test_archive.py::test_archived_document_stays_searchable_readable_and_citable` | integration | planned |
| CACHE-44 | `tests/services/test_archive.py::test_target_health_fields_upload_state_moves_to_uploaded_and_24h_stall_notifies` | integration | planned |
| CACHE-45 | `tests/services/test_collections.py::test_create_add_remove_list_show_and_pinning_collections` | integration | planned |
| CACHE-46 | `tests/services/test_disk.py::test_samples_thresholds_and_notices` | integration | planned |
| CACHE-47 | `tests/services/test_maintenance.py::test_detects_corrupt_fts_missing_orphans_and_fixes_only_as_confirmed_jobs` | integration | planned |
| CACHE-48 | `tests/contract/test_tools_cache.py::test_library_offers_no_discard_action` | contract | planned |
| CACHE-49 | `tests/services/test_backup.py::test_nightly_online_backup_of_state_cache_and_config_keeps_seven` | integration | planned |
| CACHE-60 | `tests/services/test_archive.py::test_reindex_rebuilds_works_documents_reextracts_verifies_and_reports` | integration | planned |
| CACHE-61 | `tests/contract/test_tools_cache.py::test_search_cache_marks_state_filters_states_and_points_archived_hit_to_drive_path` | contract | planned |
| CACHE-62 | `tests/services/test_archive.py::test_reindex_leaves_drive_files_unchanged` (test plan v4 2.5) | integration | planned |
| CACHE-63 | `tests/services/test_cite.py::test_cite_collection_exports_every_item` (test plan v4 2.5; file in the search component's area) | integration | planned |

Further tests for the design in this version. They cite existing criteria; no criterion ID is created.

| Behavior | Planned test | Cites |
| --- | --- | --- |
| A successful `read` or `search_cache` result holds no registered secret value, including inside `Untrusted` | `tests/security/test_no_secret_in_tool_results.py` (the security suite calls every tool) | SEC-28 |
| Direct pin survives leaving the last pinning collection | `tests/services/test_collections.py::test_direct_pin_survives_collection_removal` | CACHE-45, CACHE-30 |
| An undecided batch closes to `kept`; a batch past `closes_at` rejects decisions even before the close job runs | `tests/services/test_review.py::test_batch_closes_by_clock_and_rejects_late_decisions` | CACHE-33, CACHE-34 |
| Backup prunes to 7, a failed backup prunes nothing, the Drive copy is skipped when the target is unavailable and writes only under `_state/` | `tests/services/test_backup.py::test_prune_failure_and_drive_copy_rules` | CACHE-49 (owner check OC-10) |
| Flags off: `crawl_site`, `collections` return `disabled`; the tool list is unchanged | `tests/contract/test_tools_cache.py::test_flags_off_keep_tool_list_and_return_disabled` | CACHE-13, CACHE-45 |
| Maintenance fix jobs are refused without `confirmed_by`; no tool submits them | `tests/services/test_maintenance.py::test_fix_jobs_need_confirmation_and_have_no_tool` | CACHE-47 |
| The outbox drain is idempotent after a crash between copy and delete | `tests/integration/test_outbox.py::test_drain_is_idempotent` | CACHE-30 |
| The `cache.db` schema created by migration 0001 matches 3.1 | `tests/unit/platform/test_stores.py::test_schemas_match_spec` | PLAT-53 |
| FTS finds a word that only the title holds (through `chunks.title`) | `tests/services/test_cache_search.py::test_title_only_match` | CACHE-20 |

Related evidence from other components: SEC-8 (CACHE-FR-3), SEC-20, SEC-23 (CACHE-FR-10, hostile PDF corpus), SEC-25, SEC-28, PLAT-8, PLAT-9, PLAT-53, PLAT-61, PLAT-84, HLTH-41, owner checks OC-04, OC-10 and OC-13 (test plan v4 3). The test files and the tool wrapper files of this component are not in the cache paths of `sdd.config.json`, which lists only the `services/` files; the gap is for the owner to close in the configuration.

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| Cache with owner review; no answer means keep; discards go to a 7-day trash (ADR 0007) | The owner fetches for one-time needs and wants nothing deleted silently (D2, D3) | v1 keeps everything forever |
| 120-day retention, fixed from fetch (ADR 0011; O7 closed) | 30 days judged too short; fixed from fetch is predictable | 30 days (ADR 0007); 120 days from last use |
| Archive moves only the file; text, chunks, FTS and embeddings stay in `cache.db` (ADR 0011) | Archived papers stay searchable and readable | Delete the text with the archive (ADR 0007 before amendment) |
| Archive through the locally synced Drive folder (ADR 0007) | No Google OAuth credential is needed | Drive API with a credential [inferred from ADR 0007 consequences] |
| Two SQLite files in WAL mode; vectors as float32 BLOBs in `cache.db`; exact NumPy search (ADR 0008) | One transaction covers chunks and their vectors; exact search is correct at personal scale | A DuckDB file with a persisted HNSW index (corruption risk); `sqlite-vec` later behind the same function |
| External-content FTS5 kept in sync by triggers | `snippet()` and `highlight()` work on any SQLite >= 3.37 | Not stated |
| One subprocess per CPU task | Memory limits and kill must work on macOS | `ProcessPoolExecutor` |
| Connection pinned to the checked IP | Closes the DNS-rebinding gap | Not stated |
| Wall-clock scheduler | Asyncio timers stall while the Mac sleeps | asyncio timers |
| Cache data in Application Support (ADR 0008) | macOS and cleaning tools may purge `~/Library/Caches` | `~/Library/Caches` |
| One `LifecycleService.decide` for MCP and UI | The same checks cannot drift between channels (CACHE-34) | Separate UI and MCP code paths |
| Archive is a job and records the decision at request time | A slow or failing copy must not hold a tool call, and the cached file stays until the copy is verified (CACHE-INV-5) | Archive inline in the call |

**Decisions that settle the open questions of LLD-cache v1** (each answered from the approved sources; the question is deleted from section 11).

| # | Question in v1 | Decision and source |
| --- | --- | --- |
| 1 | CACHE-FR-17 says full-text search indexes content, section and title, but `chunks_fts` indexed only content and section | The PRD is frozen and wins (task rule; PRD-cache v4 CACHE-FR-17). `chunks` gains a `title` column and `chunks_fts` indexes it (3.1, 3.2). Option A (a `chunks.title` column in the chunk FTS index) was chosen (owner decision, 2026-10-22) |
| 2 | CACHE-FR-57 measures the model cache but `disk_samples` had no column | The requirement wins. `state.db.disk_samples` gains `model_cache_bytes` (3.2); the health LLD v2 must add it. Approved (owner decision, 2026-10-22); the health LLD v2 carries it too and it is part of `0001_init` |
| 3 | SPEC-v2 9.1 had no transition from `cached` or `kept` to `pinned` | Rows 8 and 12 to 15 are added to 5.5. Sources: CACHE-FR-33 (Pin in a review), CACHE-FR-37 (pin and unpin), CACHE-FR-55 (pinning collections), the tool rows `library pin` and `fetch(pin=True)` (SPEC-v2 7.2), and HLD-v3 6 (`cached -[pin]-> pinned`) |
| 4 | Does leaving the last pinning collection also unpin a document the owner pinned directly? | No. `documents.pin_direct` records a direct pin; row 15 keeps such a document `pinned`. Sources: CACHE-FR-37 ("Pin keeps an item indefinitely") and CACHE-FR-55 (a collection pins only when created with pinning on). This is an assumption on a point the sources leave open; the column was approved (owner decision, 2026-10-22) |
| 5 | Which database is authoritative for whether a batch is open? | `state.db.review_batches` (SPEC 10 lists review batches under `state.db`); `documents.review_batch_id` is the membership pointer (3.3) |
| 6 | Who closes a batch that went unanswered? | A batch closes by the clock (`now >= closes_at`) for every check, and the interval job `review_close` (15 minutes) and the start of each review make the `expiring` to `kept` change (row 9, 5.6). v1 named no job and the batch would otherwise close a few seconds after the next 09:00 review. The hourly `archive_reconcile` job (5.7) is likewise needed and absent from the platform table; both must be added there |
| 7 | Which `ErrorCode` for a closed batch or a foreign `doc_id`, and how does `search_cache` "say so" without embeddings? | Closed batch, foreign `doc_id` and unknown `choice`: `invalid_argument`; unknown batch: `not_found` (contract Errors; platform codes). Without embeddings: `mode_used = "keyword"`, `embeddings_available = false`, `coverage = 0.0` and the warning `embeddings_unavailable` (contract; CACHE-FR-24, PLAT-FR-30 warnings) |
| 8 | CACHE-FR-49 requires `get_work` to report the archive path and date; CACHE-FR-50 calls the archive folder a source-board target | `get_work` stays in the search LLD; this LLD provides `LifecycleService.summaries` (2.1; SRCH-FR-17). The source-board row is the local target of HLTH-FR-5 ("archive folder"), probed by `HealthService` through `ArchiveService.check_target()`; no cache-side board row exists (5.7) |
| 9 | What happens to fetch when the `pdf` extra is missing? | PLAT-FR-51 makes `pdf` an extra and PLAT-4 keeps it out of the base install. A PDF fetch returns `unconfigured` before anything is recorded; HTML needs no extra. The check runs before the download and reports `unconfigured` (owner decision, 2026-10-22) |
| 10 | Does the UI review submission apply the same open-batch check as `cache_review_decide`? (raised in LLD-ui v1) | Yes. Both call `LifecycleService.decide` (2.4, 5.6). CACHE-34 and CACHE-FR-35 require the check for MCP; one method keeps the UI identical |
| 11 | Should the optional behaviors get feature flags? | Yes: `cache.crawl_enabled`, `cache.collections_enabled` and `archive.reindex_enabled`, beside the extras, `notify.webhook_url` and `backup.drive_copy` (7). The form follows LLD-platform v2 7.2; no flag registry exists. Defaults: the three new flags `true` (each is bounded: an allowlisted site, owner-created collections, a read-only rebuild); `backup.drive_copy` `false` (owner decision, 2026-10-22) |
| 12 | CACHE-30 and CACHE-40 cite "SPEC 9.1" and "SPEC 9.3" (SPEC-v2 numbers) | The PRD is frozen. The SPEC-v2 numbers are kept in the headings and mapped in the table at the top of this LLD. SPEC-v5 section 6 points to LLD sections 2, 3 and 5 |
| 13 | Header versions of PRD-cache v2, and a contract in `docs/contracts/` | The PRD is now v4 and cites SPEC-v3 and LLD-cache v1 (which this version supersedes); this LLD cites PRD-cache v4 and SPEC-v5. A contract is warranted for the tool surface and for the sidecar, which outlives the code: [cache tools, archive sidecar and rebuild report v1](../contracts/cache-tools-and-sidecar-v1.md) |

**Other decisions of this version.**

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| Backups keep the last 7 nightly folders (owner decision, 2026-10-22) | PLAT-FR-57, CACHE-49, SPEC 10 and 12 | A day count (`backup.keep` as days) |
| The Drive copy of backups is `backup.drive_copy`, default off, written only to `_state/` (owner decision, 2026-10-22) | PLAT-FR-57 and OC-10 make it optional; the copy sends personal data to Drive | On by default; not built |
| Every string in a successful tool result is redacted in `@tool_boundary` (SEC-28; owner decision, 2026-10-22) | Closes the gap in SEC-INV-4; the cache needs no extra code | Redaction in each service |
| Daemon token never reaches a client and clients use the shim (owner decision, 2026-10-22) | SEC-INV-10; the cache tools are reached only through the shim | Direct loopback HTTP for clients |
| A batch id is a ULID (SPEC 15); `rb-2026-11-14` is example text | SPEC 15 fixes ULIDs for batches; PRD-ui and the UI LLD raised the example | `rb-<date>` ids |
| `ui_path` carries the full path with the `/ui` prefix | The UI `next` redirect accepts `/ui/` paths only (owner decision, 2026-10-22) | A path relative to `/ui` with the prefix added by the CLI |
| `clean_orphans` moves orphan files to `trash/orphans/` | Honors CACHE-INV-1 in spirit for files with no database row [assumption] | Delete at once |
| The upload check uses `NSURLUbiquitousItemIsUploadedKey` (SPEC-v2 9.3) | The sources name it; whether the Google Drive File Provider answers it is [inferred] and is checked by OC-04. If it does not, the state is `unknown` and the 24-hour stall cannot fire | A Drive API check (rejected: no credential, ADR 0007) |

**Divergences for the platform LLD owner (LLD-platform v2) to take from this LLD and the health LLD:** (1) scheduler jobs `review_close`, `archive_reconcile`, `health_evaluate`, `health_rollup`, `credential_sync` and `probe:<source>`; (2) flags `cache.crawl_enabled`, `cache.collections_enabled` and `archive.reindex_enabled`; (3) the webhook validator (`https`, or `http` for a loopback host only); (4) `0001_init` carries `chunks.title`, `documents.pin_direct`, `documents.integrity_at_fetch` and `disk_samples.model_cache_bytes`; (5) `sdd.config.json` path additions for the cache tool wrappers (`mcp_app/tools_library.py`, `mcp_app/tools_review.py`), their tests, `services/disk.py`, `mcp_app`, and health `services/doctor.py`; (6) the `fetch` tool takes a string or a list of 1 to 20 and may return a `JobHandle`, so the tool-result union and the footprint test change.

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

None open. The four owner questions (title in full-text search, other schema additions, PDF fetch without the `pdf` extra, fetching more than one item) were answered on 2026-10-22 and are recorded in 3.2, 5.2, 5.12, 6 and 7.

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| Kenny Hill (Engineering) | 2026-10-23 | approved (cache-tools-and-sidecar-v1) | approved: adds `chunks.title` (and `title` in `chunks_fts`), `documents.pin_direct`, `documents.integrity_at_fetch`, `disk_samples.model_cache_bytes` (inside the 0001 migration) | approved (security-reviewer persona drafted/reviewed; control owner Kenny Hill) | Approved in chat; recorded by Claude in the owner's name at his direction |
