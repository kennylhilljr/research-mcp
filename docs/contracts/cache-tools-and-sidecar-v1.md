---
title: "Cache tools, archive sidecar and rebuild report"
type: contract
version: 1
status: approved
approved_by: "Kenny Hill (Engineering)"
approved: 2026-10-23
owner: "Kenny Hill"
component: cache
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
date: 2026-10-22
---

# Contract: cache tools, archive sidecar and rebuild report (v1)

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves at Gate 3 with [LLD-cache-v2](../lld/LLD-cache-v2.md). Approved at Gate 3 on 2026-10-23. It writes down the shapes that [PRD-cache-v4](../prd/components/PRD-cache-v4.md) and [SPEC-v5](../spec/SPEC-v5.md) 6 already require, and the one on-disk format (the sidecar) that outlives the code. The envelope and the error codes are in [envelope and errors v1](envelope-and-errors-v1.md); this file does not repeat them.

The Pydantic models in `research_mcp/services/cache.py` and `research_mcp/services/lifecycle.py` are the code form; the MCP SDK emits the JSON Schema from them (PLAT-30). Every tool carries `@tool_boundary` (PLAT-FR-30). Every string in a successful result is redacted for registered secrets there (SEC-28, owner decision, 2026-10-22). Text taken from a document (text windows, snippets, summaries) is returned only inside `Untrusted` (PLAT-FR-25; SEC-22).

## Operations

Annotations: RO read-only, OW open world, ID idempotent. Bounds are enforced by the tool schema and give `invalid_argument` when broken (PLAT-FR-31). No tool accepts a local path (CACHE-11).

### Tools

| Tool | Arguments (bounds) | `data` on success | Annotations |
| --- | --- | --- | --- |
| `fetch` | `id_or_url: str (1..2000) or list[str] (1..20 items, each 1..2000)`, `prefer: list[str] = []`, `pin: bool = False` | `FetchResult` for a string; `JobHandle` for a list (owner decision, 2026-10-22) | not RO, OW, ID |
| `read` | `doc_id: str`, `pages: str = None`, `section: str = None`, `chunks: str = None`, `max_chars: int (500..20000) = 8000`, `cursor: str = None` | `ReadWindow` | RO |
| `search_cache` | `query: str (1..500)`, `mode: "hybrid"\|"keyword"\|"semantic" = "hybrid"`, `doc_ids: list[str] (0..100) = []`, `collection: str = None`, `states: list["cached"\|"pinned"\|"expiring"\|"kept"\|"archived"] = []`, `limit: int (1..50) = 10` | `CacheSearchResult` | RO |
| `library` | `action: "list"\|"stats"\|"pin"\|"unpin"\|"archive"\|"restore"`, `ids: list[str] (0..200) = []`, `state: str = None`, `cursor: str = None` | `LibraryList`, `LibraryStats` or `LibraryActionResult` | RO for list and stats; otherwise not RO, not destructive |
| `collections` | `action: "create"\|"add"\|"remove"\|"list"\|"show"`, `name: str = None`, `ids: list[str] (0..200) = []`, `pin_members: bool = False` | `CollectionList`, `CollectionView` or `CollectionActionResult` | not RO |
| `crawl_site` | `site: str`, `max_pages: int (1..500) = 100` | `JobHandle` | not RO, OW |
| `jobs` | `action: "status"\|"list"\|"cancel"`, `job_id: str = None` | `JobStatus` or `JobList` (platform) | not RO for cancel |
| `cache_review_list` | `batch_id: str = None` | `ReviewBatchView` | RO |
| `cache_review_decide` | `batch_id: str`, `decisions: list[Decision] (1..200)` | `ReviewDecisionResult` | not RO, destructive |

`library` has no discard action and no tool other than `cache_review_decide` discards (CACHE-48; CACHE-INV-7). `pin_members` is honored only by `create`. `states` empty means every state except `discarded`.

### Result shapes

| Type | Fields |
| --- | --- |
| `FetchResult` | `doc_id`, `work_id`, `state`, `title`, `kind` (`pdf`, `html`, `text`), `source`, `final_url`, `license`, `oa_status`, `expires_at`, `pages`, `chunks`, `coverage` (0.0 to 1.0), `extract_status`, `summary` (`Untrusted`), `reused` (true when an existing document was returned) |
| `ReadWindow` | `doc_id`, `state`, `window` (`{kind, start, end}`), `text` (`Untrusted`), `archive_path` (set for archived documents), `next_cursor` is in the envelope |
| `CacheSearchResult` | `mode_used`, `coverage`, `embeddings_available`, `hits: list[CacheHit]` |
| `CacheHit` | `doc_id`, `work_id`, `state`, `title`, `section`, `page_start`, `page_end`, `score`, `snippet` (`Untrusted`), `archive_path` (archived hits only) |
| `LibraryItem` | `doc_id`, `work_id`, `title`, `state`, `size_bytes`, `cached_at`, `age_days`, `expires_at`, `days_to_expiry` (null when pinned or archived), `archive_path`, `archived_at`, `last_accessed_at`, `trash_until` |
| `LibraryStats` | `by_state: {state: {count, size_bytes}}`, `total_count`, `total_bytes`, `expiring_within_lead_days` |
| `LibraryActionResult` | `results: list[{id, ok, state, job_id, code}]` (`job_id` set for `archive`, which runs as a job; `code` is an error code when `ok` is false) |
| `ReviewBatchView` | `batch_id`, `created_at`, `closes_at`, `open`, `items: list[ReviewItem]` |
| `ReviewItem` | `doc_id`, `title`, `citation` (`Untrusted`), `source`, `size_bytes`, `age_days`, `times_asked`, `last_accessed_at`, `integrity_change` (null or text), `decision` (null or the choice already recorded) |
| `Decision` | `doc_id`, `choice: "archive"\|"discard"\|"keep"\|"pin"` |
| `ReviewDecisionResult` | `applied: list[{doc_id, choice, state, job_id}]`, `notified_discards: int` |

Rules:

- **`fetch`** returns the existing document for a work that is already `cached`, `pinned`, `expiring`, `kept` or `archived` (`reused` true). For a `discarded` work it creates a new document from the stored recipe. If extraction failed earlier it tries extraction again (CACHE-12; CACHE-FR-6). A list of items runs as a `fetch_many` job and returns a `JobHandle` (`job_id`, `state`); progress and cancel go through `jobs` (CACHE-13; owner decision, 2026-10-22). `prefer` is a list of source ids that overrides the configured preference order for this call.
- **`read`** accepts at most one of `pages` (for example `3-5`), `section` (a heading, matched case-insensitively and exactly) and `chunks` (for example `10-20`); none means from the start. The cursor continues the same selection. A document with `extract_status = "needs_ocr"` returns an empty window and the warning `needs_ocr`. Archived documents read exactly as cached ones (CACHE-43).
- **`search_cache`** without the embeddings extra runs keyword-only: `mode_used` is `keyword`, `embeddings_available` is false, `coverage` is 0.0 and `warnings` carries `embeddings_unavailable` (CACHE-24). A query with invalid full-text syntax falls back to a literal match and `warnings` carries `query_literal_fallback` (CACHE-20).
- **`library restore`** undoes a discard still inside the trash period; after the purge it returns `not_found` for that item. `library archive` is accepted for `cached`, `pinned` and `kept` documents.
- **`cache_review_decide`** validates every decision first. If the batch is closed, or any `doc_id` is outside the batch, or a `choice` is not one of the four, the whole call is rejected and nothing is applied. It records `decided_by="agent"` and `decided_channel="mcp"`, sends discards to the trash only, and sends one notification at once that lists the discarded items, with a link to the Archive page where the undo is (CACHE-34).
- **`crawl_site`** returns a `JobHandle` (`job_id`, `state`); progress and cancel go through `jobs` (CACHE-13).

## Errors

The codes are those of the [platform contract](envelope-and-errors-v1.md). The messages stay fixed and generic (SEC-10).

| Situation | Code | Retryable |
| --- | --- | --- |
| Out-of-bounds argument, two of `pages`/`section`/`chunks`, a tampered or foreign cursor, a path or a non-https URL in `id_or_url` (or in any item of a list; one bad item rejects the whole call) | `invalid_argument` | no |
| `cache_review_decide` on a closed batch, a `doc_id` outside the batch, or an unknown `choice` | `invalid_argument` | no |
| Unknown `batch_id`, `doc_id`, collection, site or job; `read` or `search_cache` on a discarded document; `library restore` after the purge | `not_found` | no |
| `fetch` of a PDF when the `pdf` extra is missing (checked before the download; the result names the install command and nothing is recorded; owner decision, 2026-10-22); `crawl_site` for a site that is not configured | `unconfigured` | no |
| The feature flag of the tool is off (`cache.crawl_enabled`, `cache.collections_enabled`) | `disabled` | no |
| The download failed a check (scheme, address, host policy, media type, magic bytes) | `blocked_by_policy` | no |
| The download exceeded `limits.download_bytes` | `too_large` | no |
| An upstream returned an error while resolving or downloading | the HTTP client codes (`upstream_error`, `upstream_timeout`, `rate_limited`, `auth_failed`) | per code |
| `read` of a document whose extraction failed | `extract_failed` | no |
| Anything else | `internal` | no |

A `fetch` whose download succeeded but whose extraction failed is not an error result: the document is stored with `extract_status = "extract_failed"` and `warnings` carries `extract_failed`.

## Archive sidecar

`<slug>.meta.json` is written next to each archived file (CACHE-FR-46; CACHE-40). UTF-8 JSON, one object. A reader (the rebuild job) must ignore unknown fields. A change of a field name or meaning needs a new version of this contract.

| Field | Type | Meaning |
| --- | --- | --- |
| `title` | text | |
| `authors` | list of `{family, given}` | |
| `csl` | object | CSL-JSON item |
| `citation_apa` | text | Formatted citation |
| `bibtex` | text | |
| `source` | text | Source id that supplied the file |
| `identifiers` | list of `{scheme, value}` | |
| `original_url` | text | Where the file was fetched from |
| `fetched_at` | text | ISO 8601 UTC |
| `archived_at` | text | ISO 8601 UTC |
| `sha256` | text | Lowercase hex of the archived file |
| `size_bytes` | integer | |
| `archived_from` | text | `research-mcp 3.x` |

The slug is `<first-author-family>-<year>-<first six words of the title key>-<sha256[:6]>`, lowercase ASCII with `-` separators; the file is `<slug>.<ext>`.

## Archive rebuild report

`state_dir/imports/<timestamp>/archive-reindex.json` and `archive-reindex.md` (CACHE-FR-51; CACHE-60). The JSON object has these integer fields: `sidecars_read`, `works_created`, `documents_verified`, `re_extracted`, `mismatched`, `files_without_sidecars`; the boolean `dry_run`; and `files_without_sidecars_list` (relative paths). The Markdown file shows the same counts and lists.
