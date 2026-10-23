-- cache.db, migration 0001 (SPEC-v5 10; LLD-cache-v2 3.1). Columns marked v2 are LLD-cache-v2 3.2.
-- The Migrator wraps this script in BEGIN IMMEDIATE and COMMIT and sets user_version.

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
