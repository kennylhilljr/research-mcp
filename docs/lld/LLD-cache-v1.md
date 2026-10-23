---
title: "Retrieval and Cache low level design"
type: lld
version: 1
status: draft
owner: "Kenny Hill"
prefix: CACHE
component: cache
parent: docs/spec/SPEC-v3.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# LLD: Retrieval and Cache (v1)

This LLD carries SPEC-v2 sections 8 and 9 (except 9.6) and HLD-v3 section 6 onto the LLD template, with the parts of SPEC-v2 sections 2, 3.4, 3.5, 3.6, 7.2, 7.3 and 10.1 that the cache depends on. Names are copied exactly. Text copied from SPEC-v2 keeps SPEC-v2's section numbers in its cross references (for example "3.4" or "section 9.8"). Requirements are in [PRD-cache v3](../prd/components/PRD-cache-v3.md).

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

Governing section: **SPEC-v3 section 6** (Retrieval and cache).

Criteria of this component: CACHE-1, CACHE-2, CACHE-10, CACHE-11, CACHE-12, CACHE-13, CACHE-14, CACHE-15, CACHE-16, CACHE-17, CACHE-18, CACHE-19, CACHE-20, CACHE-21, CACHE-22, CACHE-23, CACHE-24, CACHE-30, CACHE-31, CACHE-32, CACHE-33, CACHE-34, CACHE-35, CACHE-36, CACHE-40, CACHE-41, CACHE-42, CACHE-43, CACHE-44, CACHE-45, CACHE-46, CACHE-47, CACHE-60, CACHE-61, CACHE-48, CACHE-49.

Requirements of this component: CACHE-FR-1 to CACHE-FR-7, CACHE-FR-10 to CACHE-FR-18, CACHE-FR-20 to CACHE-FR-24, CACHE-FR-30 to CACHE-FR-38, CACHE-FR-45 to CACHE-FR-52, CACHE-FR-55 to CACHE-FR-59.

| Requirement | Criteria | SPEC section |
| --- | --- | --- |
| CACHE-FR-1 | CACHE-10 | SPEC-v3 6; SPEC-v2 7.2 (`fetch`); HLD-v3 6 |
| CACHE-FR-2 | CACHE-1, CACHE-2 | SPEC-v2 3.4 |
| CACHE-FR-3 | SEC-8 (security component) | SPEC-v2 3.3 |
| CACHE-FR-4 | CACHE-2, CACHE-11 | SPEC-v2 3.4, 7.2 |
| CACHE-FR-5 | CACHE-2 | SPEC-v2 3.4, 8.1 |
| CACHE-FR-6 | CACHE-12 | SPEC-v2 7.2, 9.1 |
| CACHE-FR-7 | CACHE-13 | SPEC-v2 3.6, 7.2 |
| CACHE-FR-10 | CACHE-14, SEC-23 | SPEC-v2 3.6, 8.2 |
| CACHE-FR-11 | CACHE-15 | SPEC-v2 8.2 |
| CACHE-FR-12 | CACHE-16 | SPEC-v2 8.2 |
| CACHE-FR-13 | CACHE-17 | SPEC-v2 8.1 (`extractions.needs_ocr`) |
| CACHE-FR-14 | CACHE-18 | SPEC-v2 8.1, 8.2 |
| CACHE-FR-15 | CACHE-19 | SPEC-v2 7.2 (`read`) |
| CACHE-FR-16 | CACHE-20 | SPEC-v2 8.3 |
| CACHE-FR-17 | CACHE-20 | SPEC-v2 8.1, 8.3 |
| CACHE-FR-18 | CACHE-21 | SPEC-v2 7.2 (`library`) |
| CACHE-FR-20 | CACHE-22 | SPEC-v2 8.2 |
| CACHE-FR-21 | CACHE-22 | SPEC-v2 8.1 |
| CACHE-FR-22 | CACHE-23 | SPEC-v2 8.2 |
| CACHE-FR-23 | CACHE-22 | SPEC-v2 8.1, 8.2; ADR 0008 |
| CACHE-FR-24 | CACHE-24 | SPEC-v2 8.3 |
| CACHE-FR-30 | CACHE-30, PLAT-8, PLAT-53 | SPEC-v2 2, 9.1 |
| CACHE-FR-31 | CACHE-30, CACHE-31 | SPEC-v2 9.1, 9.2 |
| CACHE-FR-32 | CACHE-31 | SPEC-v2 9.2, 10.4 |
| CACHE-FR-33 | CACHE-32 | SPEC-v2 7.2, 9.1 |
| CACHE-FR-34 | CACHE-30, CACHE-33 | SPEC-v2 9.1 |
| CACHE-FR-35 | CACHE-34, CACHE-48, PLAT-61 | SPEC-v2 7.2, 7.3, 9.2 |
| CACHE-FR-36 | CACHE-30, CACHE-36, PLAT-53 | SPEC-v2 3.4, 9.1 |
| CACHE-FR-37 | CACHE-30 | SPEC-v2 9.1 |
| CACHE-FR-38 | CACHE-35 | SPEC-v2 8.1, 11 |
| CACHE-FR-45 | CACHE-40, HLTH-41 | SPEC-v2 2, 9.3 |
| CACHE-FR-46 | CACHE-40 | SPEC-v2 9.3 |
| CACHE-FR-47 | CACHE-41 | SPEC-v2 9.3 |
| CACHE-FR-48 | CACHE-42 | SPEC-v2 9.3 |
| CACHE-FR-49 | CACHE-43 | SPEC-v2 9.3 |
| CACHE-FR-50 | CACHE-44 | SPEC-v2 9.3, 10.5 |
| CACHE-FR-51 | CACHE-60 | SPEC-v2 9.7 |
| CACHE-FR-52 | CACHE-61 | SPEC-v2 7.2 (`search_cache`), 9.3 |
| CACHE-FR-55 | CACHE-45, PLAT-53 | SPEC-v2 9.5 |
| CACHE-FR-56 | CACHE-13 | SPEC-v2 7.2 (`crawl_site`) |
| CACHE-FR-57 | CACHE-46 | SPEC-v2 2, 9.4 |
| CACHE-FR-58 | CACHE-47 | SPEC-v2 9.4 |
| CACHE-FR-59 | CACHE-49, PLAT-9 | SPEC-v2 2, 9.8 |

Out of this component: SPEC-v2 9.6 (legacy import) belongs to the migration component; see [LLD-migration-v1](LLD-migration-v1.md).

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

No machine-readable contract exists in `docs/contracts/` yet (see 11).

**MCP tools (SPEC-v2 7.2, the cache rows).** All tools return `ToolResult[...]` and carry annotations. "RO" means read-only and "OW" means open world.

| Tool | Signature (bounds) | Service | Annotations | M |
|---|---|---|---|---|
| `fetch` | `id_or_url: str, prefer: list[str] = [], pin: bool = False` | cache | not RO, OW, idempotent | M2 |
| `read` | `doc_id: str, pages: str = None, section: str = None, chunks: str = None, max_chars: int (500..20000) = 8000, cursor: str = None` | cache | RO | M2 |
| `search_cache` | `query: str, mode: Literal["hybrid","keyword","semantic"] = "hybrid", doc_ids: list[str] = [], collection: str = None, states: list[Literal["cached","pinned","expiring","kept","archived"]] = [] (empty means all live and archived), limit: int (1..50) = 10` | cache | RO | M2 |
| `library` | `action: Literal["list","stats","pin","unpin","archive","restore"], ids: list[str] = [], state: str = None, cursor: str = None` (`restore` undoes a discard still in the trash) | lifecycle | RO for list and stats; otherwise not RO, not destructive | M2 |
| `collections` | `action: Literal["create","add","remove","list","show"], name: str = None, ids: list[str] = [], pin_members: bool = False` | lifecycle | not RO | M2 |
| `crawl_site` | `site: str (a configured docs_site id), max_pages: int (1..500) = 100` | jobs | not RO, OW | M2 |
| `jobs` | `action: Literal["status","list","cancel"], job_id: str = None` | jobs | not RO for cancel | M2 |
| `cache_review_list` | `batch_id: str = None` | lifecycle | RO | M2 |
| `cache_review_decide` | `batch_id: str, decisions: list[{doc_id, choice: Literal["archive","discard","keep","pin"]}] (1..200)` | lifecycle | not RO, destructive | M2 |

MCP and deletion:

- `library` cannot discard. The only discard through MCP is `cache_review_decide`, and only for items in an open batch.
- MCP decisions are recorded with `decided_by="agent"` and `decided_channel="mcp"`. Each MCP discard produces an immediate notification that lists the items, with an undo link.
- There is no hard-delete tool.

**Envelope (SPEC-v2 3.7).** Results use `ToolResult` (`data`, `source_status`, `warnings`, `next_cursor`, `truncated`); fetched text is wrapped in `Untrusted`. The cache uses the error code `EXTRACT_FAILED = "extract_failed"`. Every tool carries `@tool_boundary`, which applies the budget.

**MCP resources (SPEC-v2 7.3, M2 row):** `research://work/{work_id}`, `research://doc/{doc_id}/text{?page}`, `research://collection/{name}`, `research://cache/expiring`, `research://cache/index`. The prompt `review-expiring-items` is registered in M1. The server instructions say that cache review decisions must come from the owner's explicit words (SPEC-v2 7.3).

**CLI (SPEC-v2 1, 9.3, 9.7).** `research-mcp archive reindex [--dry-run]` starts the archive rebuild; `research-mcp install` runs the first archive write in the foreground; `research-mcp doctor` runs `archive_target` and `archive_access`.

**UI routes (SPEC-v2 11).** Pages `/ui/cache`, `/ui/review/<batch_id>`, `/ui/archive`, `/ui/maintenance`; actions are POST routes under the same paths, at `/action/<name>`. The review notification carries `ui_path=/review/<batch_id>` (SPEC-v2 9.2).

**Webhook message (SPEC-v2 10.4).** `POST notify.webhook_url` with JSON `{type, severity, subject, body, ui_path, ts}`.

**Archive sidecar (SPEC-v2 9.3).** `<slug>.meta.json` with the fields `title`, `authors`, `csl`, `citation_apa`, `bibtex`, `source`, `identifiers`, `original_url`, `fetched_at`, `archived_at`, `sha256`, `size_bytes`, `archived_from` = `research-mcp 3.x`.

**Archive rebuild report (SPEC-v2 9.7).** `state_dir/imports/<timestamp>/archive-reindex.json` and `.md` with counts: sidecars read, works created, documents verified, re-extracted, mismatched, files without sidecars.

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

**`cache.db` schema (SPEC-v2 8.1, migration 0001).**

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
  next_ask_at TEXT, pinned_at TEXT, archived_at TEXT, archive_path TEXT,
  archive_fallback INTEGER NOT NULL DEFAULT 0,
  archive_upload_state TEXT CHECK (archive_upload_state IN ('pending','uploaded','unknown')),
  discarded_at TEXT, trash_until TEXT, purged_at TEXT, decided_by TEXT, decided_channel TEXT,
  last_accessed_at TEXT, fetch_recipe_json TEXT NOT NULL, extract_status TEXT NOT NULL DEFAULT 'pending',
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
  content TEXT NOT NULL, content_sha256 TEXT NOT NULL, UNIQUE (extraction_id, ord));

-- External-content FTS: rows are read back from chunks, so snippet() and highlight() work on any SQLite >= 3.37.
CREATE VIRTUAL TABLE chunks_fts USING fts5(content, section,
  content='chunks', content_rowid='chunk_id', tokenize='porter unicode61 remove_diacritics 2', prefix='2 3');
CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
  INSERT INTO chunks_fts(rowid, content, section) VALUES (new.chunk_id, new.content, new.section); END;
CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, content, section) VALUES ('delete', old.chunk_id, old.content, old.section); END;
CREATE TRIGGER chunks_au AFTER UPDATE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, content, section) VALUES ('delete', old.chunk_id, old.content, old.section);
  INSERT INTO chunks_fts(rowid, content, section) VALUES (new.chunk_id, new.content, new.section); END;
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

`cache.db` lives under `paths.data_dir` in Application Support and is backed up nightly (section 9.8). Only the stored files, the trash and the model cache are left out of backups.

**`state.db` tables the cache writes or reads (SPEC-v2 10.1, migration 0001).**

```sql
CREATE TABLE review_batches (batch_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, notified_at TEXT,
  closes_at TEXT NOT NULL, closed_at TEXT, item_count INTEGER NOT NULL);
CREATE TABLE review_events (ts TEXT NOT NULL, doc_id TEXT NOT NULL, batch_id TEXT, from_state TEXT NOT NULL,
  to_state TEXT NOT NULL, decided_by TEXT, channel TEXT);
CREATE TABLE disk_samples (ts TEXT PRIMARY KEY, cache_bytes INTEGER, files_bytes INTEGER, index_bytes INTEGER,
  embeddings_bytes INTEGER, trash_bytes INTEGER, free_cache_vol INTEGER, free_archive_vol INTEGER);
CREATE TABLE maintenance_runs (ts TEXT NOT NULL, check_name TEXT NOT NULL, ok INTEGER NOT NULL, detail TEXT);
```

Retention: `disk_samples` 90 days; `review_batches`, `review_events` and `maintenance_runs` are kept (SPEC-v2 10.1).

**Stores and migrations (SPEC-v2 3.5).** `Migrator` applies `migrations/<db>/NNNN_*.sql` in order; the cache schema is `platform/migrations/cache/0001_init.sql`. Each script runs inside an explicit `BEGIN IMMEDIATE` and `COMMIT`; the Migrator sets `PRAGMA user_version` and refuses a database newer than the newest migration. `CacheStore` exposes typed methods only; no SQL appears outside `platform/stores.py` and the `services/*` repositories. The rest of `CacheStore` arrives in M2 as `services/*` repositories.

**Cross-database events (SPEC-v2 3.5).** `documents.decided_*` in `cache.db` is authoritative. Each lifecycle transition also writes a row to `cache.db.outbox` in the same transaction. A drainer copies outbox rows to `state.db.review_events` and deletes them, so neither database needs a transaction that spans both.

**File layout (SPEC-v2 2, 3.4).** `paths.data_dir` holds `cache.db`, `files/`, `trash/` and `tmp/`. Stored files live at `data_dir/files/<sha256[:2]>/<sha256>.<ext>`. Downloads stream into `data_dir/tmp/<ulid>.part`.

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

| Enforcement point | Rule | Source |
| --- | --- | --- |
| Every MCP tool | No tool accepts a local path; files are written only under the cache root | FR-CACHE-04; HLD-v3 9; CACHE-11 |
| `Downloader` | https only; host policy re-checked on every hop; public IPs only, with the connection pinned to the checked IP | SPEC-v2 3.4; CACHE-1 |
| HTTP client credential attachment | A credential is attached only when the request origin is in its spec origins | FR-CACHE-03; SPEC-v2 3.3; SEC-8 |
| `library` | Cannot discard | SPEC-v2 7.2; CACHE-48 |
| `cache_review_decide` | Checks that the `batch_id` is open and that every `doc_id` belongs to it; records `decided_by="agent"` and `decided_channel="mcp"`; discards go to the trash only and notify the owner at once with an undo link | SPEC-v2 7.2, 9.2; CACHE-34 |
| MCP surface | There is no hard-delete tool | SPEC-v2 7.2; SEC-20 |
| UI actions (discard on the Cache page, review, undo) | UI session cookie `rmcp_session`; every POST requires `X-CSRF-Token`; Host and Origin checks | SPEC-v2 11 |
| Maintenance fix actions (`rebuild_fts`, `reembed_missing`, `clean_orphans`, `backup_state`) | Can be started only from the UI or the CLI | SPEC-v2 9.4; CACHE-47 |
| `ArchiveService.reindex` | The Drive file is opened read-only and never modified | SPEC-v2 9.7; CACHE-60 |
| Server instructions | Cache review decisions must come from the owner's explicit words | SPEC-v2 7.3; PLAT-61 |

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

**Modules (SPEC-v2 1 layout).**

| Module | Holds | Owner component |
| --- | --- | --- |
| `services/cache.py` | The cache service: `fetch`, `read`, `search_cache` (SPEC-v2 7.2 service `cache`) | cache |
| `services/lifecycle.py` | `LifecycleService` [inferred from the file name]; `library`, `collections`, `cache_review_list`, `cache_review_decide` (SPEC-v2 7.2 service `lifecycle`) | cache |
| `services/archive.py` | `ArchiveService` [inferred from the file name]: `archive(doc_id)`, `reconcile()`, `reindex(root)` | cache |
| `services/extract.py` | `extract_pdf`, `extract_html` [inferred from the file name] | cache |
| `services/chunking.py` | `chunking.chunk(...)`, `CHUNKER_VERSION` | cache |
| `services/embeddings.py` | Embedding with `passage_embed` and `query_embed`; exact cosine search [inferred from the file name] | cache |
| `services/disk.py` | `DiskService` [inferred from the file name] | cache |
| `services/maintenance.py` | `MaintenanceService` [inferred from the file name] | cache |
| `services/backup.py` | `BackupService` [inferred from the file name] | cache |
| `services/legacy_import.py` | `LegacyImportService` (SPEC-v2 9.6) | migration |
| `mcp_app/tools_library.py`, `mcp_app/tools_review.py` | MCP tool wrappers for the cache tools [inferred from the file names] | mcp-app |
| `platform/download.py` | `DownloadPolicy`, `Downloader`, `Resolver`, `PinnedTransport` | platform |
| `platform/workers.py`, `platform/jobs.py`, `platform/scheduler.py`, `platform/stores.py` | `WorkerRunner`, `JobService`, `Scheduler`, `CacheStore` | platform |

**Fetch pipeline (HLD-v3 6).**

```
 fetch(id or url)
   -> works.resolve -> OA locations from all sources -> choose by preference
   -> downloader: https, host policy per hop, public IPs only, byte cap, magic bytes, atomic write, sha256
   -> worker: extract (PyMuPDF, limits) -> chunk (token, section aware) -> embed (passage)
   -> cache.db: document (state=cached, expires_at=+120d), file, extraction, chunks, FTS, vectors
   -> envelope {doc_id, summary, pages, chunks, coverage}
```

The lifecycle state machine (HLD-v3 6; ADR 0007, ADR 0011):

```
 cached -[3 days before expiry, daily 09:00]-> expiring -[archive]-> archived
   ^  |                                          |  |-[discard]-> discarded (7-day trash, notice 24 h before purge, then files removed)
   |  |-[pin]-> pinned                            |
   |                                             |-[no answer for 24 h]-> kept -[7 days]-> expiring
   |-[keep another 120 days]---------------------|
```

- **Archive** copies the file and a sidecar metadata JSON to the Drive sync folder, verifies the copy, then removes only the cached file. The document's text, chunks, full-text entries and embeddings stay in `cache.db`, so archived papers remain searchable and readable. If the folder is unavailable, it uses a local fallback and reconciles later. A rebuild job can re-import the archive from the Drive folder and its sidecars.
- **Metadata outlives files.** A discarded work keeps its citation snapshot and fetch recipe; an archived work keeps those plus its searchable text.
- **Local search** is hybrid: FTS5 BM25 plus exact vector similarity over embeddings stored in `cache.db`, fused by reciprocal rank ([ADR 0008](../adr/0008-sqlite-stores-and-vectors.md)).

**Downloader (SPEC-v2 3.4; code owned by the platform component).** `Downloader(resolver: Resolver, policy: DownloadPolicy, ...)`. The algorithm is a port of v1's `security.download_pdf_atomic`, with DNS pinning added:

1. Require `https`. Resolve the host through the injected `Resolver` (the system resolver in the daemon, a fake in tests). Reject private, loopback, link-local, multicast and reserved addresses, for both IPv4 and IPv6.
2. Connect through `PinnedTransport` to the **checked IP**, with SNI and the `Host` header set to the hostname. httpx never resolves the name a second time, which closes the DNS-rebinding gap.
3. Set `follow_redirects=False` and follow up to 5 redirects by hand. On every hop, repeat steps 1 and 2 and re-check the scheme and the host policy (`policy.allowed_hosts`, or `public_any`).
4. Stream into `data_dir/tmp/<ulid>.part` with a byte cap. Check `Content-Type` against `policy.media_types`, and check the first bytes: `%PDF-` for PDF; for HTML, `<` after any whitespace.
5. Run `fsync`, compute SHA-256, and move the file atomically to `data_dir/files/<sha256[:2]>/<sha256>.<ext>`. If that file already exists, reuse it.
6. Return `DownloadedFile` (section 4).

**File deletion rule:** a stored file is removed only when no `files` row with the same `sha256` belongs to a document in a non-terminal state (`cached`, `pinned`, `expiring`, `kept`), and no discard of it is still within its trash period.


**Workers and jobs (SPEC-v2 3.6, the parts the cache uses; code owned by the platform component).**

`WorkerRunner` runs every CPU-heavy task in its own subprocess. `ProcessPoolExecutor` is not used, because on macOS it cannot enforce memory limits or kill a running task.

- The task is launched with `anyio.open_process([python, "-m", "research_mcp.platform.workers", <task>])`. Input goes in as JSON on stdin; the result comes back as JSON on stdout.
- In the child, `RLIMIT_CPU` is 120 s. `RLIMIT_AS` is not relied on, because macOS does not enforce it.
- The parent enforces a 180 s wall clock and samples the child's RSS every second with `psutil`. Past 2 GB, or at the timeout, it sends SIGKILL.
- A crash or kill affects only that task, which ends with code `extract_failed`.
- Tasks: `extract_pdf`, `extract_html`, `chunk`, `embed`. At most 2 run at once.

`JobService` provides `submit(kind, params) -> job_id`, `status(job_id)`, `cancel(job_id)` and `list(state)`.

- Job state lives in `state.db.jobs`.
- Progress is pushed to MCP `Context.report_progress` while the caller waits.
- Resumable job kinds store a cursor.

`Scheduler` is driven by the wall clock, not by asyncio timers, which stall while the Mac sleeps.

- Every 60 s it compares the wall clock with each job's next due time.
- A job missed because the Mac was asleep or the daemon was down runs once at start or on wake. It never runs once per missed day.
- Daily schedules:

| Job | Local time |
|---|---|
| `review` | 09:00 |
| `digest` | 08:00 |
| `backup_state` | 03:30 |
| `maintenance_daily` | 04:00 |
| `trash_purge_notice` and `trash_purge` | 10:00 |

- Interval schedules: probes at their own cadence; `disk_sample` every 15 minutes; `outbox_drain` every 5 s.

**Extraction and chunking (SPEC-v2 8.2).**

- **`extract_pdf`** runs in the worker with PyMuPDF. Page count is `len(doc)`. Text is taken per page with `sort=True`, the outline comes from `get_toc()`, and the references section is tagged `section="References"`.
- **`extract_html`** parses with `selectolax`. It drops nav, header, footer, script and style, keeps h1 to h3 as section markers, and outputs text with paragraph breaks.
- **`chunking.chunk(text_by_page, sections, target_tokens=400, overlap_tokens=50, hard_cap_chars=4000)`:**
  - Tokens are counted with a fast whitespace-and-punctuation tokenizer.
  - Text is split on paragraphs, then on sentences (a regex with an abbreviation guard), then at the hard cap.
  - A word is never split. Page numbers and character offsets are recorded for every chunk.
  - `CHUNKER_VERSION = "2.0"`.
- **Embeddings:**
  - The default model is `fastembed` `BAAI/bge-small-en-v1.5` (384 dimensions), cached in `paths.model_cache_dir`.
  - Chunks are encoded with `passage_embed` and queries with `query_embed`.
  - Vectors are stored as float32 little-endian BLOBs.
  - Search computes exact cosine similarity with NumPy over the cached vectors. `sqlite-vec` can replace this later behind the same function.

**Local search (SPEC-v2 8.3).**

`search_cache` has three modes:

- **Keyword:** FTS5 with `bm25(chunks_fts, 1.0, 0.5)`, plus the v1 query sanitizer and its literal fallback (ported). A hit in the References section has its score multiplied by 0.5 in Python before ranking.
- **Semantic:** the top 50 chunks by cosine similarity.
- **Hybrid:** reciprocal rank fusion of the keyword and semantic results.

Snippets come from `snippet(chunks_fts, 0, '[', ']', ' ... ', 12)` for keyword hits. Semantic hits get the 300 characters around their best sentence.

Each result reports coverage: embedded chunks divided by all chunks, for the documents in scope.

**State transitions (SPEC-v2 9.1).**

| From | Event | To | Side effects |
|---|---|---|---|
| (none) | fetch | cached | `expires_at = cached_at + 120 d` |
| cached | review run, `expires_at - now <= 3 d` | expiring | Assigned to today's batch |
| kept | review run, `next_ask_at <= now` | expiring | `reask_count += 1` |
| expiring | archive (owner in the UI, or agent through MCP) | archived | Archive job (9.3) |
| expiring | discard (owner in the UI, or agent through `cache_review_decide`) | discarded | Files to trash; `trash_until = now + 7 d`; MCP discards notify at once |
| cached, pinned or kept | owner discard on the UI Cache page (confirmed) | discarded | As above |
| expiring | keep | cached | `expires_at = now + 120 d` |
| expiring | pin, or membership in a pinning collection | pinned | `expires_at = NULL` |
| expiring | batch closes unanswered (`cache.batch_open_hours` after the notification) | kept | `next_ask_at = now + 7 d`; files stay |
| cached, pinned or kept | `library archive` | archived | Archive job; not destructive (the copy is verified before removal) |
| pinned | unpin | cached | `expires_at = now + 120 d` |
| discarded | undo before `trash_until` (UI Archive page, or `library restore`) | cached | Restore files from trash; `expires_at = now + 120 d` |
| discarded | `trash_until` passes | discarded | Purge job (below); `purged_at` set; the work, CSL and recipe are kept |

- `decided_by` is `owner` for the UI and `agent` for MCP. `decided_channel` is `ui` or `mcp`. Every transition writes an outbox row (3.5).
- **Trash purge.** At 10:00 each day, `trash_purge_notice` lists the items whose trash ends within 24 hours, in one notification with an undo link. `trash_purge` then removes items whose `trash_until` has passed: their file (subject to the file deletion rule in 3.4), their chunks and FTS rows, and any embeddings no other chunk uses.

**Review batch (SPEC-v2 9.2).**

`LifecycleService.run_review(now)` runs at `cache.review_time_local`, or once on catch-up:

1. Select the candidates.
2. Create `review_batches(batch_id, created_at, notified_at, closes_at, item_count)`.
3. Send one notification through `NotifyService`, with `ui_path=/review/<batch_id>`.
4. Post the webhook message.

`cache_review_decide` checks that the `batch_id` is open and that every `doc_id` belongs to it.

**Archive (SPEC-v2 9.3).**

`ArchiveService.archive(doc_id)`:

1. **Resolve the target.** Use `archive.confirmed_path` (required when `archive.target` is `auto`), then add `archive.subfolder` with `{year}` set to the archive year. Then check:
   - the folder exists;
   - it is writable, by writing and replacing the sentinel `.research-mcp-probe`;
   - there is free space greater than the file size plus 100 MB;
   - the `Google Drive` app process is running (`pgrep -x "Google Drive"`).
2. **Name the files.** The slug is `<first-author-family>-<year>-<title-key first 6 words>-<sha256[:6]>`. The files are `<slug>.<ext>` and `<slug>.meta.json`.
3. **Write in the target folder.** Write the hidden temporary file `.<slug>.<ext>.partial` there, then `fsync` it and rename it to `<slug>.<ext>`. Read the file back and compare its size and SHA-256. Write the sidecar the same way. Drive for desktop may upload a hidden partial file; the rename replaces it.
4. **On success:**
   - set `state=archived`, `archive_path`, `archived_at`, and `archive_upload_state='pending'`;
   - remove only the cached file (subject to the file deletion rule in 3.4). The extraction, chunks, FTS rows and embeddings **stay**, so the archived document remains searchable with `search_cache` and readable with `read` (ADR 0011). `files.storage_path` is cleared and `documents.archive_path` points to the Drive copy.
5. **If the target check fails:**
   - use `archive.fallback` and set `archive_fallback=1`;
   - raise an `archive_target_unavailable` health event.
   
   `ArchiveService.reconcile()` runs hourly when fallbacks exist. It moves the fallback files into the Drive target with the same verification.
6. **Upload confirmation.** Hourly, `reconcile()` reads `NSURLUbiquitousItemIsUploadedKey` for each pending archive. This uses pyobjc (extra `macos`); without the extra, the state is `unknown`.
   - When the key is true, the state becomes `uploaded`.
   - An item still `pending` 24 hours after archiving raises a notification.

**Sidecar fields:** `title`, `authors`, `csl`, `citation_apa`, `bibtex`, `source`, `identifiers`, `original_url`, `fetched_at`, `archived_at`, `sha256`, `size_bytes`, `archived_from` = `research-mcp 3.x`.

**macOS privacy (TCC).** Files in `~/Library/CloudStorage` are protected. The first archive write by the daemon's interpreter may need the owner's consent, and a background process may get no prompt at all.

- `doctor` runs `archive_access`, which writes and removes the sentinel, and reports `tcc_denied` with the fix: grant the daemon's interpreter Files and Folders access to Google Drive in System Settings, Privacy & Security.
- `research-mcp install` runs this write once in the foreground, so the prompt appears while the owner is present.

**Disk and integrity (SPEC-v2 9.4).**

`DiskService.sample()` runs every 15 minutes and writes to `state.db.disk_samples`.

`MaintenanceService.daily()` runs these checks and records each one in `maintenance_runs`:

- `PRAGMA quick_check` on both databases;
- `INSERT INTO chunks_fts(chunks_fts) VALUES('integrity-check')`;
- missing-file and orphan scans.

Fix actions (`rebuild_fts`, `reembed_missing`, `clean_orphans` and `backup_state`) are job kinds. They can be started only from the UI or the CLI.

**Collections (SPEC-v2 9.5).**

Collections do not pin by default (`pin_members` defaults to 0).

- A collection created with `pin_members=1` pins every document of its member works.
- Removing a work from the last pinning collection returns its documents to `cached`, with a fresh 120 days.

**Legacy import (SPEC-v2 9.6).** Owned by the migration component; see [LLD-migration-v1](LLD-migration-v1.md).

**Archive rebuild (SPEC-v2 9.7).**

`ArchiveService.reindex(root)` runs as the job kind `archive_reindex`, started from the UI Archive page or `research-mcp archive reindex [--dry-run]`:

1. Walk `archive.confirmed_path` plus `archive.subfolder` for every year folder (and the fallback folder), reading each `<slug>.meta.json` sidecar. Files without a sidecar are listed in the report and left alone.
2. For each sidecar, look the work up by its identifiers. Create the work, identifiers and an `archived` document (with `archive_path`) when missing; otherwise verify the stored `sha256` matches the file.
3. If the document has no extraction, chunks or embeddings for the current chunker and model, copy the PDF to `data_dir/tmp`, re-extract and embed it in the worker, then delete the temporary copy. The Drive file is opened read-only and never modified.
4. Write `state_dir/imports/<timestamp>/archive-reindex.json` and `.md` with counts: sidecars read, works created, documents verified, re-extracted, mismatched, files without sidecars.

**Backups (SPEC-v2 9.8).**

`BackupService.backup_state()` runs nightly at 03:30. It uses the SQLite online backup API to copy `state.db` and `cache.db`, and it copies `config.toml`. The copies go to `state_dir/backups/<date>/`, and `backup.keep` days are kept. The stored files and the trash are not backed up.

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

| Condition | Behavior | Source |
| --- | --- | --- |
| Worker crash, kill, CPU limit (120 s), wall clock (180 s) or RSS above 2 GB | Only that task ends, with code `extract_failed`; the daemon keeps serving | SPEC-v2 3.6; CACHE-14 |
| Download fails a check (scheme, address, host policy, media type, magic bytes, byte cap) | Rejected; at most 5 redirects, each re-checked | SPEC-v2 3.4; CACHE-1 |
| Downloaded file already stored | The existing file at `data_dir/files/<sha256[:2]>/<sha256>.<ext>` is reused | SPEC-v2 3.4 |
| `fetch` of a cached work | Returns the existing document; the tool is annotated idempotent | FR-CACHE-06; SPEC-v2 7.2; CACHE-12 |
| `fetch` of a discarded work | A new document is created from its recipe | FR-CACHE-06; CACHE-12 |
| Invalid full-text query syntax | The v1 query sanitizer falls back to a literal match | SPEC-v2 8.3; CACHE-20 |
| Embeddings extra missing | `search_cache` runs keyword-only and says so | FR-CACHE-24; CACHE-24 |
| `cache_review_decide` with a closed batch or a foreign `doc_id` | Rejected | SPEC-v2 9.2; CACHE-34 |
| Batch closes unanswered | Items become `kept` with `next_ask_at = now + 7 d`; files stay | SPEC-v2 9.1; CACHE-33 |
| Archive read-back mismatch | The cached copy is kept | FR-CACHE-47; CACHE-41 |
| Archive target check fails | `archive.fallback` with `archive_fallback=1`; an `archive_target_unavailable` health event; `reconcile()` moves the files hourly with the same verification | SPEC-v2 9.3; CACHE-42 |
| Archive still `pending` 24 hours after archiving | A notification | SPEC-v2 9.3; CACHE-44 |
| No pyobjc (extra `macos`) | Upload state is `unknown` | SPEC-v2 9.3 |
| TCC denies the archive write | `doctor` `archive_access` reports `tcc_denied` with the fix | SPEC-v2 9.3; HLTH-41 |
| Sidecar `sha256` differs from the file during rebuild | Counted as mismatched in the report | SPEC-v2 9.7; CACHE-60 |
| Archive folder file without a sidecar | Listed in the report and left alone | SPEC-v2 9.7; CACHE-60 |
| Mac asleep or daemon down at a scheduled time | The job runs once at start or on wake, never once per missed day | SPEC-v2 3.6 |
| Webhook delivery fails | 5 s timeout, at most 2 retries, failures logged | SPEC-v2 10.4 |
| Stored file shared by SHA-256 with a live document | Not removed (file deletion rule) | SPEC-v2 3.4; CACHE-36 |

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

**Settings (SPEC-v2 2, the cache rows).**

| Key | Default | Notes |
|---|---|---|
| `paths.data_dir` | `~/Library/Application Support/research-mcp/cache` | `cache.db`, `files/`, `trash/`, `tmp/` (not in `~/Library/Caches`, which macOS and cleaners may purge) |
| `paths.model_cache_dir` | `~/Library/Caches/research-mcp/models` | Embedding model files only (re-downloadable) |
| `limits.download_bytes` | `52428800` | |
| `limits.pdf_pages` | `500` | |
| `limits.chunk_hard_cap_chars` | `4000` | |
| `cache.retention_days` | `120` | Fixed from fetch (ADR 0011) |
| `cache.review_lead_days` | `3` | |
| `cache.review_time_local` | `"09:00"` | |
| `cache.batch_open_hours` | `24` | Unanswered items become `kept` when the batch closes |
| `cache.reask_days` | `7` | |
| `cache.trash_days` | `7` | |
| `archive.target` | `auto` | `auto` finds the single `~/Library/CloudStorage/GoogleDrive-*/My Drive`; else an absolute path |
| `archive.confirmed_path` | none | Set when the owner confirms the detected target in the UI or with `config set`; archiving to `auto` waits for this confirmation |
| `archive.subfolder` | `Research Archive/{year}` | |
| `archive.fallback` | `~/Research Archive/{year}` | |
| `notify.webhook_url` | none | OpenClaw inbox (open decision O5); any token goes in Keychain `NOTIFY_WEBHOOK_TOKEN`, never in the URL |
| `disk.cache_warn_bytes` | `5368709120` | |
| `disk.free_warn_bytes` / `free_crit_bytes` | `16106127360` / `5368709120` | |
| `backup.keep` | `7` | Nightly copies of `state.db`, `cache.db` and `config.toml` |

Directories are created at daemon start with mode `0700` (SPEC-v2 2).

**Clarification from the first M0 attempt (SPEC-v2 0.6).**

| Unit | Section | Requirement |
|---|---|---|
| M0-04 | 2; AT-PLAT-08, AT-PLAT-09 | Paths MUST be normalized (resolving `..`) before the durable-location check. Credential names MUST keep their canonical case across TOML and `RESEARCH_MCP_` environment overrides, so an environment override updates the same credential the TOML defines. |

(SPEC-v2 0.6) This row is built by the settings unit; it governs the durable-location check behind CACHE-FR-59.

**Optional behaviors.** The sources define no feature flags for this component. These switches exist:

| Flag | Default | Safe to switch off? |
| --- | --- | --- |
| `embeddings` extra (`fastembed`) | Not in the base dependencies (PLAT-4) | Yes: `search_cache` runs keyword-only and says so (FR-CACHE-24) |
| `pdf` extra (`pymupdf`) | Not in the base dependencies (PLAT-4) | Not stated (see 11) |
| `macos` extra (pyobjc) | Not stated | Yes: the archive upload state is `unknown` (SPEC-v2 9.3) |
| `notify.webhook_url` | none | Yes: the webhook message is optional (FR-CACHE-32) |

## 8. Observability

> **Owner:** A · **Persona:** `sre`

| Signal | Detail | Source |
| --- | --- | --- |
| `state.db.disk_samples` | `DiskService.sample()` every 15 minutes: cache, files, index, embeddings and trash bytes; free space on the cache and archive volumes. Thresholds `disk.cache_warn_bytes`, `disk.free_warn_bytes`, `disk.free_crit_bytes` (FR-CACHE-57) | SPEC-v2 9.4, 10.1; CACHE-46 |
| `state.db.maintenance_runs` | One row per daily check: `PRAGMA quick_check`, FTS `integrity-check`, missing-file and orphan scans | SPEC-v2 9.4; CACHE-47 |
| `state.db.review_events` | Copied from `cache.db.outbox` for every lifecycle transition, with `decided_by` and `channel` | SPEC-v2 3.5, 10.1 |
| Notifications | Review batch (one per batch); MCP discard (immediate, with undo link); trash purge notice (10:00, items leaving within 24 hours); archive upload stall (24 hours); disk thresholds | SPEC-v2 9.1, 9.2, 9.3, 9.4 |
| Health event | `archive_target_unavailable` when the archive target check fails | SPEC-v2 9.3 |
| `doctor` checks | `archive_target`, `archive_access`, `disk`, `schema_versions`, `review_overdue` (no review missed by more than 24 hours), `backup_recent` (a backup in the last 48 hours) | SPEC-v2 10.5; HLTH-41 |
| `/api/status` | Cache stats, disk and the archive target | SPEC-v2 10.5 |
| `search_cache` coverage | Embedded chunks divided by all chunks, for the documents in scope | SPEC-v2 8.3 |

No threshold here traces to a parent NFR; the disk thresholds trace to CACHE-FR-57.

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

No test in `tests/` cites a cache criterion yet. The planned file for CACHE-1 and CACHE-2 is named by SPEC-v2 12.3 (unit M0-07); the M2 units and their test files are not yet written (SPEC-v2 12.4).

| Criterion | Planned tests | Level | Status |
| --- | --- | --- | --- |
| CACHE-1 | `tests/unit/platform/test_downloader.py` (SPEC-v2 12.3, unit M0-07) | unit | planned |
| CACHE-2 | `tests/unit/platform/test_downloader.py` (SPEC-v2 12.3, unit M0-07) | unit | planned |
| CACHE-10 | planned | integration | planned |
| CACHE-11 | planned | contract | planned |
| CACHE-12 | planned | integration | planned |
| CACHE-13 | planned | integration | planned |
| CACHE-14 | planned | integration | planned |
| CACHE-15 | planned | unit | planned |
| CACHE-16 | planned | unit | planned |
| CACHE-17 | planned | unit | planned |
| CACHE-18 | planned | unit | planned |
| CACHE-19 | planned | contract | planned |
| CACHE-20 | planned | integration | planned |
| CACHE-21 | planned | contract | planned |
| CACHE-22 | planned | integration | planned |
| CACHE-23 | planned | unit | planned |
| CACHE-24 | planned | integration | planned |
| CACHE-30 | planned | unit | planned |
| CACHE-31 | planned | integration | planned |
| CACHE-32 | planned | integration | planned |
| CACHE-33 | planned | integration | planned |
| CACHE-34 | planned | contract | planned |
| CACHE-35 | planned | integration | planned |
| CACHE-36 | planned | integration | planned |
| CACHE-40 | planned | integration | planned |
| CACHE-41 | planned | integration | planned |
| CACHE-42 | planned | integration | planned |
| CACHE-43 | planned | integration | planned |
| CACHE-44 | planned | integration | planned |
| CACHE-45 | planned | integration | planned |
| CACHE-46 | planned | integration | planned |
| CACHE-47 | planned | integration | planned |
| CACHE-60 | planned | integration | planned |
| CACHE-61 | planned | contract | planned |
| CACHE-48 | planned | contract | planned |
| CACHE-49 | planned | integration | planned |

Related evidence from other components: SEC-8 (CACHE-FR-3), SEC-23 (CACHE-FR-10, hostile PDF corpus in `tests/fixtures/pdf/hostile/`), PLAT-8, PLAT-9, PLAT-53, PLAT-61, HLTH-41, and owner checks OC-04 and OC-13 (TEST-PLAN-v3 4, 6, 7).

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| Cache with owner review; no answer means keep; discards go to a 7-day trash (ADR 0007) | The owner fetches for one-time needs and wants nothing deleted silently (D2, D3) | v1 keeps everything forever |
| 120-day retention, fixed from fetch (ADR 0011; O7) | 30 days judged too short; fixed from fetch is predictable | 30 days (ADR 0007); 120 days from last use (O7) |
| Archive moves only the file; text, chunks, FTS and embeddings stay in `cache.db` (ADR 0011) | Archived papers stay searchable and readable | Delete the text with the archive (ADR 0007 before amendment) |
| Archive through the locally synced Drive folder (ADR 0007) | No Google OAuth credential is needed | Drive API with a credential [inferred from ADR 0007 consequences] |
| Two SQLite files in WAL mode; vectors as float32 BLOBs in `cache.db`; exact NumPy search (ADR 0008) | One transaction covers chunks and their vectors; exact search is correct for tens of thousands of chunks | A DuckDB file with a persisted HNSW index (corruption risk after an unclean shutdown); `sqlite-vec` later behind the same function |
| External-content FTS5 kept in sync by triggers (SPEC-v2 8.1) | `snippet()` and `highlight()` work on any SQLite >= 3.37 | Not stated |
| One subprocess per CPU task (SPEC-v2 3.6) | Memory limits and kill must work on macOS | `ProcessPoolExecutor` |
| Connection pinned to the checked IP (SPEC-v2 3.4) | Closes the DNS-rebinding gap | Not stated |
| Wall-clock scheduler (SPEC-v2 3.6) | Asyncio timers stall while the Mac sleeps | asyncio timers |
| Cache data in Application Support (HLD-v3 10; ADR 0008) | macOS and cleaning tools may purge `~/Library/Caches` | `~/Library/Caches` |

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

- [ ] Q: CACHE-FR-17 says full-text search indexes "content, section and title", but `chunks_fts` in SPEC-v2 8.1 indexes only `content` and `section`. Which is right?
- [ ] Q: CACHE-FR-57 measures cache size by type including the model cache, but `disk_samples` (SPEC-v2 10.1) has no model cache column. Add a column, or drop the model cache from the requirement?
- [ ] Q: SPEC-v2 9.1 has no transition from `cached` or `kept` to `pinned`, though HLD-v3 6 draws `cached -[pin]-> pinned` and SPEC-v2 7.2 offers `library` `pin`, `fetch(pin=True)` and pinning collections. Which rows should be added?
- [ ] Q: SPEC-v2 9.5 returns a work's documents to `cached` when it leaves its last pinning collection. Does that also unpin a document the owner pinned directly?
- [ ] Q: `review_batches` lives in `state.db` (SPEC-v2 10.1; HLD-v3 10) while `documents.review_batch_id` lives in `cache.db`, and ADR 0008 lists only "a copy of review events" in `state.db`. Which database is authoritative for whether a batch is open when `cache_review_decide` checks it?
- [ ] Q: Which `ErrorCode` does `cache_review_decide` return for a closed batch or a foreign `doc_id`? SPEC-v2 9.2 says only that it checks.
- [ ] Q: How does `search_cache` "say so" when the embeddings extra is missing (a `warnings` entry, a coverage value, or both)? SPEC-v2 does not say.
- [ ] Q: CACHE-FR-49 requires `get_work` to report the archive path and date, but `get_work` belongs to the search component and SPEC-v2 defines no such field. Which LLD owns it?
- [ ] Q: CACHE-FR-50 calls the archive folder health a monitored target on the source board, but SPEC-v2 9.3 defines only the `archive_target_unavailable` health event and the `doctor` checks. Is a source board row needed?
- [ ] Q: What happens to fetch and extraction when the `pdf` extra is not installed? The sources do not say.
- [ ] Q: Should the optional behaviors of this component (`crawl_site`, collections, the webhook, the archive rebuild) get feature flags? The sources define none.
- [ ] Q: CACHE-30 and CACHE-40 cite "SPEC 9.1" and "SPEC 9.3" (SPEC-v2 numbering). SPEC-v3 keeps HLD-v3 numbering, so these sections now live in this LLD under SPEC-v3 section 6. Should the criteria be reworded to point here?
- [ ] Q: The PRD-cache-v2 header names "PRD v2", "HLD v2", "SPEC v1" and "TEST-PLAN v1" while its links go to PRD-v4, HLD-v3, SPEC-v1 and TEST-PLAN-v3; TEST-PLAN-v3 also names SPEC v1 as its contract. Which versions were meant?
- [ ] Q: No machine-readable contract exists in `docs/contracts/` for the cache tools, the sidecar or the webhook message. Should they be added?

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
