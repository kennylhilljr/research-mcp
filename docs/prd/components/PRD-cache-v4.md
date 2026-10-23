---
title: "Retrieval and Cache"
type: prd-component
version: 4
status: approved
approved_by: "Kenny Hill (Product)"
approved: 2026-10-22
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
prefix: CACHE
component: cache
parent: docs/prd/PRD-v7.md
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
supersedes: docs/prd/components/PRD-cache-v3.md
date: 2026-10-22
---

# Component PRD: Retrieval and Cache (v4)

This version supersedes [PRD-cache v3](PRD-cache-v3.md), which moved [PRD-cache v2](../../../docs-archive/prd/components/PRD-cache-v2.md) onto the SDD templates with new IDs (section 2.16). Version 4 records the owner's Gate 1 answers of 2026-10-22. The parent is [PRD v7](../PRD-v7.md); the vision is [vision-v2](../../vision/vision-v2.md); the design is [LLD-cache v1](../../lld/LLD-cache-v1.md), governed by [SPEC-v3](../../spec/SPEC-v3.md) section 6.

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

- Papers and documents are fetched for a one-time need; the local index is a working cache, not a library (owner decision D2; PRD-cache-v2 1).
- In v1 the local corpus grows without purpose: papers fetched for one-off needs are kept forever, duplicated, and never cleaned up (PRD-v4 2, problem 6; ADR 0007, amended by ADR 0011).
- v1 downloads follow redirects anywhere, accept http and private IPs, have no size or PDF check, and the model can choose any path; fetch works for only 3 of about 25 sources (REVIEW-v1 3, findings 8 and 9).
- v1 semantic search covers at most about 7% of chunks, and vectors are orphaned on every re-index (REVIEW-v1 3, finding 11; ADR 0008).
- The cache makes fetched items readable, searchable and citable for 120 days, then asks the owner whether to archive or discard each one. Archives go to Google Drive and stay searchable. Nothing is deleted without an answer (PRD-cache-v2 1; owner decisions D3, amended by ADR 0011, and D4; ADR 0011).
- **Why now.** v2 is a rebuild, and the upstream breakage is current: the live probes of 2026-10-19 found several sources degraded, and the review found v1 is not a sound base for the next year of use (PRD-v7 1.1). The cache is the M2 milestone of that rebuild (PRD-v6 2.9) (owner decision, 2026-10-22).

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| The owner, through an agent (Claude Code, Claude desktop, Codex, OpenClaw agents) over MCP | Fetch, read, search and cite papers; answer a review from an agent chat (PRD-v4 4; PRD-cache-v2 FR-CACHE-35) | One person; personal server (PRD-v6 1.2; owner decision, 2026-10-22) |
| The owner, directly, in the local web UI | Answer the "archive or discard" review (PRD-v4 4) | One person (PRD-v6 1.2; owner decision, 2026-10-22) |
| The owner, passively, through macOS notifications and the optional OpenClaw inbox | Be told "6 cached papers expire Friday: review" (PRD-v4 4) | One person (PRD-v6 1.2; owner decision, 2026-10-22) |

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- Fetch, read, cite, local search, the 120-day lifecycle, the owner review and the searchable Drive archive (PRD-v4 5).
- Extraction, chunking and embeddings; collections; crawl jobs; disk monitoring; integrity checks; the archive rebuild job; nightly backup of `cache.db` (PRD-cache-v2 2.2 to 2.7).

| Non-goal | Why it is excluded |
| --- | --- |
| OCR | Out of scope for v1 of v2 (PRD-cache-v2 3; FR-CACHE-13) |
| Annotation and highlighting | Excluded to keep v2 a working cache and one search, not a library or search engine (PRD-v6 2.10, scope creep risk; owner decision, 2026-10-22) |
| Syncing the archive back into the cache automatically | Excluded to keep v2 a working cache and one search, not a library or search engine (PRD-v6 2.10, scope creep risk; owner decision, 2026-10-22) |
| A reference-manager feature set | A curated paper library, reference manager or note-taking tool is a parent non-goal: "Zotero does that" (PRD-cache-v2 3; PRD-v4 3.2) |

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |
| CACHE-OUT-1 | Items deleted without a recorded owner decision (carries parent OUT-6, "Cache, not library") | v1 has no lifecycle: nothing is reviewed or deleted, and the corpus only grows (ADR 0007, amended by ADR 0011; owner decision, 2026-10-22) | 0 | Measured 30 days after cutover (PRD-v4 3.1 G6, 7) |

The parent outcomes OUT-1 to OUT-8 and NFR-1 to NFR-12 suffice; no component outcome beyond CACHE-OUT-1 is added (owner decision, 2026-10-22).

## 1.5 Leaps of faith

> **Owner:** H · **Persona:** none

| Leap of faith | How we will validate it | By when |
| --- | --- | --- |
| Papers are usually fetched for a one-time need, so a 120-day working cache with a review serves the owner and no library is needed (D2; PRD-v6 1.3 non-goals) | The CACHE-OUT-1 measure in 2.10: the `state.db.review_events` log shows each archive, discard, keep and pin decision with `decided_by` and `channel` | M4 exit; read again 30 days after cutover (PRD-v6 1.4) |
| The owner keeps answering review batches; review fatigue stays low because of batching and the keep default (ADR 0007, amended by ADR 0011: "Review fatigue is possible") | CACHE-31 (one batch, one notification) and CACHE-33 (unanswered items are kept, nothing deleted), then the same `review_events` log in the 30-day review | M2 exit for the criteria; 30 days after cutover for the log |
| The locally synced Google Drive folder works as the archive without a Drive API credential, although a local write only means Drive will upload (ADR 0007 consequences, amended by ADR 0011; PRD-v6 2.10, Drive sync risk) | Owner checks OC-13 and OC-04; CACHE-44 (upload state and 24-hour stall report) | M2 exit |

## 1.6 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

The owner confirmed these drafted "never" rules as component invariants (owner decision, 2026-10-22). Each names at least one P1 criterion that checks it.

| ID | The system must never | Source (regulation, policy, contract) | P1 criterion |
| --- | --- | --- | --- |
| CACHE-INV-1 | Delete an item without a recorded owner decision | Owner decision D3 (amended by ADR 0011); PRD-v4 G6; FR-CACHE-34; ADR 0007 (amended by ADR 0011) | CACHE-33 |
| CACHE-INV-2 | Remove a file shared with another live document | FR-CACHE-36; ADR 0007 (amended by ADR 0011) | CACHE-36 |
| CACHE-INV-3 | Let a caller choose where files are written or which local files are parsed (same rule as SEC-INV-7, for the cache's files) | FR-CACHE-04; PRD-v4 G7; ADR 0009 | CACHE-11 |
| CACHE-INV-4 | Attach a credential to a request whose origin does not match the credential's source (same rule as SEC-INV-5) | FR-CACHE-03; PRD-v4 G7 | SEC-8 (Security component) |
| CACHE-INV-5 | Remove the cached copy of a file before its archive copy is verified | FR-CACHE-47; PRD-v4 12; ADR 0007 (amended by ADR 0011) | CACHE-41 |
| CACHE-INV-6 | Modify the Drive files during the archive rebuild | FR-CACHE-51; ADR 0011 | CACHE-62 |
| CACHE-INV-7 | Discard through any MCP tool other than `cache_review_decide` | FR-CACHE-35; HLD-v3 9 | CACHE-48, CACHE-34 |

## 1.7 Known constraints and decisions

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

| Decision or constraint | Status (made or open) | Rationale or link |
| --- | --- | --- |
| Papers are fetched for a one-time need; the index is a working cache, not a library (D2) | Made | REVIEW-v1 1 |
| Before an item expires the owner is asked whether to archive or discard it; nothing is deleted without an answer (D3, amended by ADR 0011; D3 said 30 days) | Made; retention amended to 120 days by ADR 0011 | REVIEW-v1 1; ADR 0011 |
| The archive is the owner's Google Drive through the locally synced folder `My Drive/Research Archive/<year>/` (D4) | Made | REVIEW-v1 1; ADR 0007 (amended by ADR 0011) |
| Cache with owner review; archive to the Google Drive sync folder | ADR 0007 (amended by ADR 0011): Proposed; accepted when the owner approves this PRD at Gate 1 (PRD-v6 1.6; owner decision, 2026-10-22) | ADR 0007 |
| Two SQLite files; vectors stored in SQLite, not a persisted DuckDB index | ADR 0008: Proposed; accepted when the owner approves this PRD at Gate 1 (PRD-v6 1.6; owner decision, 2026-10-22) | ADR 0008 |
| 120-day retention counted from fetch; archiving moves only the file, so archived papers stay searchable; a rebuild job can re-create the archive from Drive | Made (Accepted, owner decision 2026-10-19) | ADR 0011 |
| Retention fixed from fetch, not from last use (O7) | Made: fixed from fetch; keep, unpin, undo and collection changes grant a fresh 120 days | PRD-v6 1.6; FR-CACHE-30; ADR 0011 |
| Review timing: ask 3 days before expiry; re-ask unanswered items after 7 days; discards go to a 7-day trash (O8) | Made: closed as recommended (PRD-v6 1.6; owner decision, 2026-10-22) | PRD-v4 11; ADR 0011 |
| PDF parser (O3) | Made: closed as recommended; PyMuPDF in a worker process, AGPL acceptable for personal, non-distributed use (PRD-v6 1.6; owner decision, 2026-10-22) | PRD-v4 11 |
| Second notification channel (O5) | Made: closed as recommended; the OpenClaw inbox through a configurable webhook (PRD-v6 1.6; owner decision, 2026-10-22) | PRD-v4 11 |
| No tool blocks the event loop; PDF parsing, extraction and embedding run in worker processes | Made (parent NFR-2) | PRD-v4 6; ADR 0005 |
| No free-form SQL; fetched content is labeled untrusted | Made (parent NFR-6) | PRD-v4 6; ADR 0009 |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| Kenny Hill (Product) | 2026-10-22 | Approved in chat; recorded by Claude in the owner's name at his direction |

---

## 2.1 Customer discovery

> **Owner:** A · **Persona:** `analyst`

The deep review of v1 ([REVIEW-v1](../../../docs-archive/review/REVIEW-v1.md)) is the research for this component:

- **Live data (REVIEW-v1 5).** `~/arxiv-papers` holds 307 MB. `arxiv_index.db` (34 MB) has 186 rows in `papers` and 11,403 chunks, with nothing indexed since 2026-04-16. 123 PDFs are on disk; 176 rows point at 122 distinct files (54 duplicate pairs), and 10 rows are web documentation pages. `embeddings.duckdb` is 1.3 MB, far smaller than full coverage would need.
- **Findings that drive this component (REVIEW-v1 3).** Downloads are unsafe and caller-pathed (finding 8: OPS-05, OPS-08, FUNC-15, FUNC-33). Fetch works for only 3 of about 25 sources (finding 9: FUNC-08). Semantic search covers at most about 7% of chunks and vectors are orphaned on re-index (finding 11: FUNC-29, FUNC-30, ARCH-12, OPS-17). A crawled 36 KB web page becomes one unbounded chunk (finding 14: FUNC-22, FUNC-23, ARCH-11).
- **Kept from v1 (REVIEW-v1 6).** The FTS5 query sanitizer with literal fallback; the safe downloader, confined paths and scoped credentials in `research_mcp/security.py`; the works, identifiers and documents schema ideas. Dropped: caller-chosen download and index paths; the persisted DuckDB HNSW index.
- **Archive growth (ADR 0011).** At the v1 corpus size, keeping archived text and vectors in `cache.db` costs tens of megabytes (about 34 MB of index for 186 papers, against 307 MB of PDFs).
- Review findings addressed by PRD-cache-v2: FUNC-08, FUNC-15, FUNC-16, FUNC-22 to FUNC-31, FUNC-33, FUNC-34, FUNC-39, OPS-05, OPS-08, OPS-17, OPS-18, OPS-20, ARCH-11, ARCH-12, ARCH-16.

## 2.2 User stories and priority

> **Owner:** C for stories (`product-writer`), H for priority · **Seed question:** 3

Drafted by the product writer and approved by the owner at Gate 1, 2026-10-22 (owner decision, 2026-10-22, to draft them). The stories rest on the user needs in PRD-v6 1.2 and 1.2 above. No requirement serves the ECC orchestrator, so it has no story.

| ID | As a... I want... so that... | Priority | Why this priority |
| --- | --- | --- | --- |
| CACHE-US-1 | As the owner (through an agent), I want to fetch the best legal open-access copy of a work safely and read it in bounded windows, so that I can use a paper for a one-time need without managing files. | P1 | CACHE-FR-1, CACHE-FR-2 and CACHE-FR-15 are P1 |
| CACHE-US-2 | As the owner (through an agent), I want to search, list and cite what I have fetched, including archived papers, so that earlier reading stays findable after the file leaves the Mac. | P1 | CACHE-FR-16 and CACHE-FR-49 are P1 |
| CACHE-US-3 | As the owner (passively), I want one notification when cached papers are due for review, so that I decide before anything expires without checking the cache myself. | P1 | CACHE-FR-31 and CACHE-FR-32 are P1 |
| CACHE-US-4 | As the owner (directly), I want to answer archive, discard, keep or pin for each item or the whole batch in the local UI, and have no answer mean keep, so that the cache stays small and nothing is deleted without my decision. | P1 | CACHE-FR-33 and CACHE-FR-34 are P1 |
| CACHE-US-5 | As the owner (through an agent), I want to answer a review batch from an agent chat, with any discard sent to the trash and announced to me with an undo link, so that I can review without opening the UI and still catch a wrong discard. | P1 | CACHE-FR-35 is P1 |
| CACHE-US-6 | As the owner (passively), I want archived papers copied to my Google Drive and verified, and the cache's disk use, integrity and backups watched, so that I lose nothing and am warned before a problem grows. | P1 | CACHE-FR-47, CACHE-FR-50 and CACHE-FR-57 are P1 |

## 2.3 User experience

> **Owner:** C · **Persona:** `product-writer` drafts the narrative; designers own the design artifacts · **Seed question:** 3

**Fetch and read (HLD-v3 11.2).** An agent calls `fetch("doi:10.1145/3649835")`. The cache resolves open-access locations from Unpaywall, OpenAlex and the publisher, picks the best one and downloads it safely. A worker extracts, chunks and embeds the document, which is stored as `cached` until a date 120 days out. The agent then calls `read(doc_id, pages="3-5")` and gets a bounded window with a cursor.

**Expiry review and archive (HLD-v3 11.3).** At 09:00 the scheduler finds 6 documents expiring within 3 days and creates batch `rb-2026-11-14`. The owner gets one macOS notification. Clicking it opens `/ui/review/rb-2026-11-14`. The owner archives 2, discards 3 and leaves 1 unanswered. The archive job copies 2 files plus sidecars to Drive, verifies them, and removes the cached PDFs; both papers stay searchable through their text in `cache.db`. The 3 discards go to the trash for 7 days. When the batch closes 24 hours later, the unanswered item becomes `kept` and is asked about again on 2026-11-22.

**Review from an agent chat (FR-CACHE-35).** The owner can answer the same batch through `cache_review_list(batch_id)` and `cache_review_decide(batch_id, decisions)`. Any discard made this way goes to the 7-day trash and the owner is notified at once with an undo link.

No design artifacts are linked yet; the UI pages are in PRD-ui.

## 2.4 Functional requirements and acceptance criteria

> **Owner:** C · **Persona:** `product-writer` drafts requirements and criteria as options; the owner selects and approves · **Seed questions:** 3, 12

Parent outcomes for every requirement: OUT-6 and OUT-7 (PRD-cache-v2 header: goals G6 and G7). Lifecycle states: `cached`, `pinned`, `expiring`, `kept`, `archived`, `discarded`.

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| CACHE-FR-1 | `fetch` takes a work identifier or URL, finds the best legal open-access copy across all sources (preference order configurable: publisher OA, arXiv, PMC, repository, Unpaywall or OpenAlex location, CORE, OSF), downloads it, extracts text, chunks it, embeds it, and returns a document handle with a short summary. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-2 | Every download goes through one safe downloader: https only, every redirect hop re-checked against the source's host policy, public IP addresses only, a byte cap (default 50 MB), a content-type and magic-byte check (`%PDF-` for PDFs), atomic write into the cache folder, and a full SHA-256. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-3 | Credentials are attached only to requests whose origin matches the credential's source (for example the CORE key only to `api.core.ac.uk`). | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-4 | Callers cannot choose where files are written or which local files are parsed. All files live under the cache root. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-5 | Every document records provenance: source, final URL, HTTP status, ETag, license, open-access status, fetch time and a fetch recipe that can re-fetch it later. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-6 | A fetch of a work already cached returns the existing document; a fetch of a discarded work creates a new document from its recipe. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-7 | Fetching more than one document, or any crawl, runs as a job that reports progress and can be cancelled. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-10 | PDF parsing runs in a worker process with limits on CPU time, memory, wall time and page count. A crash or timeout marks the document `extract_failed` without affecting the daemon. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-11 | Chunks target 300 to 500 tokens with 10 to 15% overlap, break on paragraph then sentence boundaries, never cut a word, and carry page range, character offsets and section heading (from the PDF outline when present). | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-12 | HTML documents keep heading structure (h1 to h3) and are chunked by section and length. No chunk exceeds the hard cap (default 4,000 characters) whatever the input. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-13 | Documents with no extractable text are flagged `needs_ocr`; OCR itself is out of scope for v1 of v2. | CACHE-US-1 | OUT-6, OUT-7 | P2 |
| CACHE-FR-14 | Extractions record parser, parser version and chunker version so a later chunker can re-extract selectively. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-15 | `read` returns a bounded window of a document by page range, section or chunk range, with a cursor for the rest. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-16 | `search_cache` searches cached documents by keyword (BM25), meaning (vectors) or both (hybrid, default, fused by reciprocal rank), optionally restricted to documents or a collection, and returns snippets with page numbers and the embedding coverage. | CACHE-US-2 | OUT-6, OUT-7 | P1 |
| CACHE-FR-17 | Full-text search indexes content, section and title, supports prefix queries, and falls back to a literal match when the query has invalid syntax. | CACHE-US-2 | OUT-6, OUT-7 | P1 |
| CACHE-FR-18 | `library` lists cached items with state, size, age and days to expiry, and reports totals. | CACHE-US-2 | OUT-6, OUT-7 | P1 |
| CACHE-FR-20 | Every chunk is embedded at fetch time (in the worker), so coverage is complete without a manual step. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-21 | Embeddings are keyed by chunk content hash and model, store the model name and dimension, and are removed with their chunks. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-22 | Queries use the model's query encoding and passages its passage encoding. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-23 | Embeddings live in the cache database file; there is no persisted approximate index that can corrupt on an unclean shutdown. | CACHE-US-1 | OUT-6, OUT-7 | P1 |
| CACHE-FR-24 | Embeddings are an optional extra; without it, `search_cache` runs keyword-only and says so. | CACHE-US-1 | OUT-6, OUT-7 | P2 |
| CACHE-FR-30 | A fetched document is `cached` with `expires_at` = fetch time + 120 days (`cache.retention_days`, fixed from fetch per decision O7, now closed). | CACHE-US-3 | OUT-6, OUT-7 | P1 |
| CACHE-FR-31 | A daily check at 09:00 local time moves documents whose expiry is within 3 days, plus `kept` items due for another ask, into one review batch and marks them `expiring`. | CACHE-US-3 | OUT-6, OUT-7 | P1 |
| CACHE-FR-32 | A review batch produces one macOS notification ("6 cached papers expire Friday: review") that opens the UI review page, and one optional OpenClaw inbox message. | CACHE-US-3 | OUT-6, OUT-7 | P1 |
| CACHE-FR-33 | For each item in a batch the owner can choose Archive, Discard, Keep (another 120 days), or Pin; bulk choices apply to the whole batch. | CACHE-US-4 | OUT-6, OUT-7 | P1 |
| CACHE-FR-34 | No answer means keep. An unanswered item stays with its files, becomes `kept`, and is asked about again after 7 days. Nothing is ever deleted without a recorded owner decision. | CACHE-US-4 | OUT-6, OUT-7 | P1 |
| CACHE-FR-35 | The owner can also answer from an agent chat: `cache_review_list(batch_id)` and `cache_review_decide(batch_id, decisions)`. Decisions must name an open batch and only its items; MCP decisions are recorded as made by an agent on the owner's behalf; a discard through MCP goes to the 7-day trash and immediately notifies the owner with an undo link. No other MCP tool can discard. | CACHE-US-5 | OUT-6, OUT-7 | P1 |
| CACHE-FR-36 | Discard removes the file, chunks and embeddings after a 7-day trash period (undo possible in the UI), and keeps the work's metadata, citation snapshot and fetch recipe. The owner is notified 24 hours before items leave the trash. A file shared with another live document is never removed. | CACHE-US-4 | OUT-6, OUT-7 | P1 |
| CACHE-FR-37 | Pin keeps an item indefinitely; unpin returns it to `cached` with a fresh 120 days. | CACHE-US-4 | OUT-6, OUT-7 | P1 |
| CACHE-FR-38 | A review shows, for each item: title, citation, source, size, age, times already asked, last access, and any integrity change since caching (for example a retraction). | CACHE-US-4 | OUT-6, OUT-7 | P1 |
| CACHE-FR-45 | The archive target is the locally synced Google Drive folder, default `My Drive/Research Archive/<year>/`; the daemon finds the `GoogleDrive-*` folder and the owner confirms it once. No Drive API credential is used. The first write happens during install, in the foreground, so any macOS privacy prompt appears while the owner is present. | CACHE-US-6 | OUT-6, OUT-7 | P1 |
| CACHE-FR-46 | Archiving writes the file and a sidecar `<slug>.meta.json` (title, authors, CSL-JSON, formatted citation, BibTeX, source, identifiers, original URL, fetched and archived times, SHA-256, size). | CACHE-US-6 | OUT-6, OUT-7 | P1 |
| CACHE-FR-47 | The archive copy is written to a temporary name, flushed, renamed, read back and checked (size and SHA-256) before the cached copy of the file is removed. | CACHE-US-6 | OUT-6, OUT-7 | P1 |
| CACHE-FR-48 | If the Drive folder is missing or not writable, the item is archived to a local fallback folder (default `~/Research Archive/<year>/`), marked as fallback, and the owner is warned; a reconcile job moves fallback items to Drive when the folder is healthy again. | CACHE-US-6 | OUT-6, OUT-7 | P1 |
| CACHE-FR-49 | Archived items stay findable and searchable: only the file moves to Drive; the extracted text, chunks, full-text index entries and embeddings stay in `cache.db`, so `search_cache` and `read` work on archived items exactly as on cached ones. `library` and `get_work` report the archive path and date; `cite` works from the stored metadata. | CACHE-US-2 | OUT-6, OUT-7 | P1 |
| CACHE-FR-50 | The archive folder's health (exists, writable, macOS privacy access granted, Drive app running, free space) is a monitored target on the source board. Each archived file's upload state is checked; an archive not uploaded within 24 hours is reported. | CACHE-US-6 | OUT-6, OUT-7 | P1 |
| CACHE-FR-51 | A rebuild job (`research-mcp archive reindex`) walks the Drive archive folder and, for each file with a sidecar, re-creates or verifies its work, identifiers and archived document, re-extracting text and embeddings where they are missing, so the searchable archive can be rebuilt if `cache.db` is lost. It never modifies the Drive files. | CACHE-US-6 | OUT-6, OUT-7 | P2 |
| CACHE-FR-52 | `search_cache` results say whether each hit is cached, pinned or archived; filtering by state is possible. Reading the original PDF of an archived item points to its Drive path. | CACHE-US-2 | OUT-6, OUT-7 | P1 |
| CACHE-FR-55 | Collections are named sets of works; a collection pins its members only when created with pinning on (off by default, so collections do not turn the cache into a library). `collections` supports create, add, remove, list, show and export (through `cite`). | CACHE-US-2 | OUT-6, OUT-7 | P2 |
| CACHE-FR-56 | `crawl_site` crawls an allowlisted docs site into the cache as a job, under the same 120-day lifecycle. | CACHE-US-1 | OUT-6, OUT-7 | P2 |
| CACHE-FR-57 | Disk use is measured every 15 minutes: cache size by type (files, index, embeddings, model cache, trash) and free space on the cache and archive volumes. Warning above 5 GB of cache or below 15 GB free; critical below 5 GB free. | CACHE-US-6 | OUT-6, OUT-7 | P1 |
| CACHE-FR-58 | Integrity checks run daily: database quick check, full-text index integrity, files missing on disk, orphan files and orphan embeddings. Failures appear on the Maintenance page with a fix action that needs confirmation. | CACHE-US-6 | OUT-6, OUT-7 | P1 |
| CACHE-FR-59 | Cache data (`cache.db`, stored files, trash) lives in Application Support, not in `~/Library/Caches`, so macOS or cleaning tools cannot purge pinned, kept or expiring items without an answer. `cache.db` is backed up nightly with `state.db`. | CACHE-US-6 | OUT-6, OUT-7 | P1 |

Acceptance criteria, in the order of `tools/gen_test_plan.py`. Priority is P1 when any verified requirement is Must (P1), or when the criterion is the P1 check of an invariant in 1.6 (owner decision, 2026-10-22, that every invariant has a P1 criterion); otherwise P2.

| ID | Criterion | Requirement | Priority | Level | Milestone |
| --- | --- | --- | --- | --- | --- |
| CACHE-1 | The downloader, with an injected resolver, shall reject http, private, loopback and link-local IPs, also after a redirect, pin the connection to the checked IP so that a second resolution to a private IP (DNS rebinding) is never used, and reject wrong media types, wrong magic bytes and oversize bodies. | CACHE-FR-2 | P1 | unit | M0 |
| CACHE-2 | The downloader shall write atomically under data_dir/files by SHA-256 and return full provenance. | CACHE-FR-2, CACHE-FR-4, CACHE-FR-5 | P1 | unit | M0 |
| CACHE-10 | When `fetch` is called, the cache service shall pick the best OA location by preference across sources and return a doc handle with summary. | CACHE-FR-1 | P1 | integration | M2 |
| CACHE-11 | The system shall accept no local path in any tool and write files from `fetch` only under the cache root. | CACHE-FR-4, PLAT-FR-21 | P1 | contract | M2 |
| CACHE-12 | When `fetch` is called, the cache service shall return the existing document for a cached work and re-fetch a discarded work from its recipe. | CACHE-FR-6 | P1 | integration | M2 |
| CACHE-13 | The cache service shall run multi-document fetch and crawl as jobs with progress and cancel. | CACHE-FR-7, CACHE-FR-56 | P1 | integration | M2 |
| CACHE-14 | If a parser crashes or times out in a worker, then the system shall mark the document extract_failed while the daemon keeps serving. | CACHE-FR-10 | P1 | integration | M2 |
| CACHE-15 | The chunker shall pass golden tests for target size, overlap, paragraph and sentence boundaries, no split words, offsets and pages. | CACHE-FR-11 | P1 | unit | M2 |
| CACHE-16 | The HTML extractor shall keep h1 to h3 sections and, for a 36 KB single-line page, yield bounded chunks under the hard cap. | CACHE-FR-12 | P1 | unit | M2 |
| CACHE-17 | When a PDF is image-only, the extractor shall flag it needs_ocr. | CACHE-FR-13 | P2 | unit | M2 |
| CACHE-18 | The extractor shall record parser, parser version and chunker version in extractions. | CACHE-FR-14 | P1 | unit | M2 |
| CACHE-19 | The `read` tool shall return bounded windows by page, section and chunk with a cursor. | CACHE-FR-15 | P1 | contract | M2 |
| CACHE-20 | The `search_cache` tool shall support keyword, semantic and hybrid modes, fall back to a literal match when the FTS syntax is invalid, and report coverage. | CACHE-FR-16, CACHE-FR-17 | P1 | integration | M2 |
| CACHE-21 | The `library` tool shall report states, sizes, ages and expiry in its list and stats actions. | CACHE-FR-18 | P1 | contract | M2 |
| CACHE-22 | The cache service shall embed every chunk at fetch, key vectors by content hash and model, and remove them with their chunks. | CACHE-FR-20, CACHE-FR-21, CACHE-FR-23 | P1 | integration | M2 |
| CACHE-23 | The embeddings service shall encode queries with the query encoding and passages with the passage encoding, as recorded by a fake model that records calls. | CACHE-FR-22 | P1 | unit | M2 |
| CACHE-24 | Where the embeddings extra is not installed, the `search_cache` tool shall run keyword-only and say so. | CACHE-FR-24 | P2 | integration | M2 |
| CACHE-30 | The lifecycle service shall implement the transition table of SPEC 9.1, with one test per row and a fake clock. | CACHE-FR-30, CACHE-FR-31, CACHE-FR-34, CACHE-FR-36, CACHE-FR-37 | P1 | unit | M2 |
| CACHE-31 | When the daily review runs, the lifecycle service shall build one batch, send one notification and send one webhook message. | CACHE-FR-31, CACHE-FR-32 | P1 | integration | M2 |
| CACHE-32 | The lifecycle service shall apply archive, discard, keep and pin through both per-item and bulk decisions. | CACHE-FR-33 | P1 | integration | M2 |
| CACHE-33 | If items are left unanswered, then the lifecycle service shall delete nothing, as shown by 90 simulated days with no answers. | CACHE-FR-34 | P1 | integration | M2 |
| CACHE-34 | The `cache_review_decide` tool shall reject closed batches and items outside the batch, record decided_by=agent and channel=mcp, send discards to trash only, and immediately notify the owner of MCP discards with an undo link. | CACHE-FR-35, PLAT-FR-27 | P1 | contract | M2 |
| CACHE-35 | The review shall show, for each item, its citation, size, age, times asked, last access and integrity changes. | CACHE-FR-38, SRCH-FR-26 | P1 | integration | M2 |
| CACHE-36 | When a document is discarded, the lifecycle service shall keep the work metadata, CSL and recipe, restore the files on an undo within 7 days, notify the owner 24 hours before purge, remove the files after 7 days, and never remove a file shared by SHA-256 with another live document. | CACHE-FR-36, SRCH-FR-23 | P1 | integration | M2 |
| CACHE-40 | The archive service shall auto-detect the GoogleDrive folder as the archive target and write the file plus a sidecar with the fields in SPEC 9.3. | CACHE-FR-45, CACHE-FR-46 | P1 | integration | M2 |
| CACHE-41 | The archive service shall verify the archive by reading back size and SHA-256 before removing the cached copy, and keep the cache copy when the verify fails. | CACHE-FR-47 | P1 | integration | M2 |
| CACHE-42 | If the archive target is unavailable, then the archive service shall use the fallback, warn, and move the items later through reconcile. | CACHE-FR-48 | P1 | integration | M2 |
| CACHE-43 | The cache service shall keep the extraction, chunks, FTS rows and embeddings of archived items, so that `search_cache` and `read` return them after archiving, `library` and `get_work` report the Drive path and date, and `cite` works. | CACHE-FR-49 | P1 | integration | M2 |
| CACHE-44 | The archive service shall check target health for exists, writable, privacy access, Drive app running and free space, move the upload state from pending to uploaded through a fake file-provider check, and notify on a 24-hour stall. | CACHE-FR-50 | P1 | integration | M2 |
| CACHE-45 | The `collections` tool shall support create, add, remove, list and show, pin no members unless the collection was created with pin_members, and pin and unpin the members of pinning collections. | CACHE-FR-55 | P2 | integration | M2 |
| CACHE-46 | The disk service shall take disk samples, apply thresholds and send notifications. | CACHE-FR-57 | P1 | integration | M2 |
| CACHE-47 | The maintenance service shall detect corrupt FTS, missing files and orphans, and run fixes only as confirmed jobs. | CACHE-FR-58 | P1 | integration | M2 |
| CACHE-60 | When archive reindex runs over a temp Drive folder of PDFs and sidecars, the archive service shall rebuild works, identifiers and archived documents, re-extract missing text, verify sha256, report files without sidecars, and leave the Drive files byte-for-byte unchanged. | CACHE-FR-51 | P2 | integration | M2 |
| CACHE-61 | The `search_cache` tool shall mark each hit cached, pinned or archived, filter by states, and point an archived hit to its Drive path. | CACHE-FR-52 | P1 | contract | M2 |
| CACHE-48 | The `library` tool shall offer no discard action, so that only `cache_review_decide` and the UI can discard. | CACHE-FR-35 | P1 | contract | M2 |
| CACHE-49 | The backup service shall copy state.db, cache.db and config.toml nightly with the online backup API and keep 7. | PLAT-FR-57, CACHE-FR-59 | P1 | integration | M2 |
| CACHE-62 | When archive reindex runs over a temp Drive folder that holds files with sidecars and files without sidecars, the archive service shall leave every file in the folder byte-for-byte unchanged. | CACHE-FR-51 | P1 | integration | M2 |
| CACHE-63 | When `cite` is called with a `collection`, the system shall export every item in that collection in the requested format. | CACHE-FR-55, SRCH-FR-22 | P2 | integration | M2 |

Requirements of this component that are also verified by criteria of other components (TEST-PLAN-v3 5): CACHE-FR-3 by SEC-8; CACHE-FR-10 by SEC-23; CACHE-FR-30 by PLAT-8 and PLAT-53; CACHE-FR-35 by PLAT-61; CACHE-FR-36 and CACHE-FR-55 by PLAT-53; CACHE-FR-45 by HLTH-41 and owner checks OC-13 and OC-04; CACHE-FR-47 by OC-04; CACHE-FR-59 by PLAT-9.

Verified elsewhere (owner decision, 2026-10-22):

- CACHE-FR-3 is verified by SEC-8 of the Security component; this component has no criterion of its own for it.
- The collection export action of CACHE-FR-55 ("export (through `cite`)") is verified by CACHE-63 in this component; CACHE-45 covers the other actions (owner decision, 2026-10-22).
- CACHE-FR-45 is also verified by owner checks OC-13 and OC-04, and CACHE-FR-47 by owner check OC-04 (`docs/test/test-plan-v2.md` section 3). These stay owner checks.

## 2.5 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

Parent NFRs that bind this component (PRD-v6 2.3, carried from PRD-v4 6): NFR-1 (single daemon owns the stores and scheduler), NFR-2 (PDF parsing, extraction and embedding run in worker processes), NFR-5 (every tool result fits a byte budget, default 64 KB, and pages with a cursor), NFR-6 (fetched text is returned inside an untrusted envelope), NFR-9 (the default test run makes no network calls) and NFR-11 (no em dashes or en dashes).

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |

The parent outcomes OUT-1 to OUT-8 and NFR-1 to NFR-12 suffice; no component NFR target is added (owner decision, 2026-10-22). Limits stated inside requirements (the 50 MB byte cap, the 4,000-character chunk hard cap, the disk thresholds) stay where they are, and design defaults such as timeouts stay in the LLD.

## 2.6 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

Every item is personal and confidential (PRD-v6 2.4). Retention follows the parent rule for the same kind of data, or the nearest parent rule where the parent lists none (owner decision, 2026-10-22).

| Data | Classification | Source or owner | Retention | Notes |
| --- | --- | --- | --- | --- |
| `cache.db`: works, identifiers, source records, documents and lifecycle, files, extractions, chunks, FTS, embeddings, collections, outbox | Personal, confidential; extracted text is untrusted content (NFR-6) | This component (HLD-v3 10) | Extracted text, chunks, FTS entries and embeddings: 120 days from fetch; keep, unpin, undo and collection changes grant a fresh 120 days; pinned and archived items never expire (PRD-v6 2.4; ADR 0011). Work metadata, citation snapshot, fetch recipe and the lifecycle record: the life of the install; they survive file removal (PRD-v6 2.4; HLD-v3 10; ADR 0008). Nightly backups: the last 7 kept (PLAT-FR-57; CACHE-49; PRD-v7 2.4) | `~/Library/Application Support/research-mcp/cache/` |
| Stored files (cached PDFs and HTML) and `trash/` | Personal, confidential; untrusted content (NFR-6) | Fetched from open-access sources (FR-CACHE-01) | 120 days from fetch, then by owner decision; discarded items stay 7 days in the trash, then are deleted (PRD-v6 2.4; ADR 0011; FR-CACHE-36) | Not backed up; re-fetchable (HLD-v3 10) |
| Model cache (embedding model files) | Personal, confidential | Downloaded model (SPEC-v2 8.2) | The life of the install (nearest parent rule, PRD-v6 2.4; owner decision, 2026-10-22) | `~/Library/Caches/research-mcp/models/`; re-downloadable, not backed up (HLD-v3 10) |
| Archive: archived files and sidecars | Personal, confidential | Owner's Google Drive (D4) | Never expire (PRD-v6 2.4; ADR 0011 decision 4) | Backed up by Google Drive; source for the archive rebuild job (HLD-v3 10) |
| Fetched text returned to agents | Personal, confidential; untrusted content (NFR-6) | Internet sources | As the document it comes from (PRD-v6 2.4) | Labeled untrusted (NFR-6; ADR 0009) |

## 2.7 Integrations and owners

> **Owner:** H confirms owners and SLAs · **Persona:** `architect` may draft · **Seed question:** 8

Kenny Hill owns every integration. No integration has an SLA; upstream services are best effort, tracked by probes (PRD-v6 2.5; owner decision, 2026-10-22).

| System | Owner | Relationship (depends on, feeds, replaces) | SLA |
| --- | --- | --- | --- |
| Google Drive for desktop, synced folder `~/Library/CloudStorage/GoogleDrive-*/My Drive` | Kenny Hill | Feeds: receives archived files and sidecars; no Drive API credential (FR-CACHE-45; ADR 0007, amended by ADR 0011) | None; best effort, tracked by the archive target health check (CACHE-FR-50) |
| Sources and search component (open-access locations, `get_work`, `cite`, integrity checks) | Kenny Hill | Depends on (FR-CACHE-01, FR-CACHE-38, FR-CACHE-49; HLD-v3 6) | None; upstream sources are best effort, tracked by probes |
| Health and notifications (macOS notifications, OpenClaw inbox webhook, source board) | Kenny Hill | Feeds: review batch notices, archive target health (FR-CACHE-32, FR-CACHE-50) | None |
| Local UI (review, cache, archive and maintenance pages) | Kenny Hill | Feeds and depends on (FR-CACHE-32, FR-CACHE-58; PRD-ui) | None |
| Platform (downloader, workers, jobs, scheduler, stores) | Kenny Hill | Depends on (HLD-v3 6) | None |
| v1 corpus `~/arxiv-papers` | Kenny Hill | Replaces, through the optional legacy import owned by the migration component (REVIEW-v1 5) | None |

## 2.8 Product risks

> **Owner:** H · **Persona:** none

| Risk | Question | Assessment | Mitigation |
| --- | --- | --- | --- |
| Value | Will customers choose to use this? | The owner may pin or keep everything, so the cache turns back into a library and the review loses its point (D2; PRD-v6 2.10, scope creep risk) | Collections pin only when created with pinning on; the non-goals in 1.3 keep library features out; the `review_events` log in 2.10 shows the decisions taken (PRD-v6 2.10; CACHE-FR-55) |
| Usability | Can customers use it, including with accessibility needs? | Review fatigue is possible (ADR 0007, amended by ADR 0011) | One batch and one notification a day; no answer means keep; the review can be answered in the UI or from an agent chat (ADR 0007, amended by ADR 0011; CACHE-FR-31, CACHE-FR-34, CACHE-FR-35) |
| Viability | Does it work for the business: economics, legal, compliance, operations? | PyMuPDF's AGPL license is acceptable for personal, non-distributed use (O3, PRD-v6 1.6) | Parsing stays in a worker process (CACHE-FR-10); the server is personal and not distributed (PRD-v6 1.2) |
| Drive sync folder unavailable, blocked by macOS privacy controls, or not uploading (PRD-v4 12) | | Stated risk | Install performs the first archive write in the foreground; `doctor` checks access; local fallback with a warning and reconcile; nothing leaves the cache until the archive copy is verified; upload state is checked and a stall is reported (PRD-v4 12) |
| PyMuPDF crashes on hostile PDFs (PRD-v4 12) | | Stated risk | Parsing in a worker process with CPU, memory, page and time limits (PRD-v4 12) |
| Scope creep toward a library manager (PRD-v4 12) | | Stated risk | Non-goals in PRD-v4 3.2; collections stay minimal (PRD-v4 12) |
| Review fatigue (ADR 0007, amended by ADR 0011) | | Possible | Batching and the keep default keep it low (ADR 0007, amended by ADR 0011) |
| `cache.db` grows with every archived paper's text and vectors (ADR 0011) | | Tens of megabytes at the v1 corpus size (ADR 0011) | Disk monitoring covers it; `cache.db` is backed up nightly (ADR 0011) |

## 2.9 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | As in PRD-v6 2.6: v1 stays read-only and running until cutover; cutover (M4) switches client configs; v1 is archived after 14 days of daily use on v2 with no fallback to v1 (owner decision, 2026-10-22) |
| Business conditions that must halt the rollout | The PRD-v7 2.6 conditions: any deletion without a recorded owner decision (INV-1), any secret in an output (INV-2), a fallback to v1 during the 14-day window, or a breach of any invariant, which includes CACHE-INV-1 to CACHE-INV-7 (PRD-v7 2.6; owner decision, 2026-10-22) |
| Support owner and escalation path | The owner is the only support; there is no escalation path (PRD-v6 2.6; owner decision, 2026-10-22) |
| Response targets by severity (S0 to S4) | None (PRD-v6 2.6; owner decision, 2026-10-22) |

The component ships in milestone M2 ("Retrieval and cache"); cutover to v2 is M4 (PRD-v6 2.9).

## 2.10 Measurement and experimentation

> **Owner:** C · **Persona:** `product-writer` drafts; the owner decides

| Outcome | Measured by | Experiment (if any) |
| --- | --- | --- |
| CACHE-OUT-1 | Count of items deleted without a recorded owner decision, 30 days after cutover (PRD-v4 7). Draft for the owner: every lifecycle transition writes an outbox row copied to `state.db.review_events` with `decided_by` and `channel` (SPEC-v2 3.5, 9.1), which can be compared with purges. | None |

## 2.11 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

The component is done when every P1 criterion in 2.4 passes and the exit of the milestone that delivers it is met (PRD-v6 2.9; owner decision, 2026-10-22):

- M0 exit for CACHE-1 and CACHE-2: all M0 tests green; a client can search three sources through the shim on the owner's Mac.
- M2 exit for every other criterion: lifecycle tests green; one real archive written to Drive and verified.
- The owner checks listed for this component in `docs/test/test-plan-v2.md` section 3 count: OC-13 (install triggers the Google Drive privacy prompt in the foreground; `doctor` `archive_access` passes afterward) and OC-04 (one real archive written to the Drive folder, visible in Drive on the web).
- No extra demonstration is required.

## 2.12 Edge cases and error behavior

> **Owner:** A · **Persona:** `product-writer`

| Case | Behavior | Criterion |
| --- | --- | --- |
| Redirect to an http URL or a private, loopback or link-local address; DNS rebinding | Rejected; the connection stays pinned to the checked IP | CACHE-1 |
| Wrong media type, wrong magic bytes or oversize body | Rejected | CACHE-1 |
| A caller passes a local path | No tool accepts it | CACHE-11 |
| Fetch of a work already cached, or of a discarded work | Returns the existing document; re-fetches the discarded one from its recipe | CACHE-12 |
| Parser crash or timeout | Document marked `extract_failed`; the daemon keeps serving | CACHE-14 |
| A 36 KB single-line HTML page | Bounded chunks under the hard cap | CACHE-16 |
| Image-only PDF | Flagged `needs_ocr` | CACHE-17 |
| Invalid full-text query syntax | Falls back to a literal match | CACHE-20 |
| Embeddings extra not installed | Keyword-only search, stated in the result | CACHE-24 |
| Items never answered | Become `kept`, re-asked after 7 days; nothing deleted over 90 simulated days | CACHE-33 |
| Decision for a closed batch or an item outside the batch | Rejected | CACHE-34 |
| A discarded file shared by SHA-256 with another live document | Never removed | CACHE-36 |
| Archive read-back fails | The cache copy is kept | CACHE-41 |
| Drive folder missing or not writable | Local fallback, warning, later reconcile | CACHE-42 |
| Archive not uploaded within 24 hours | The owner is notified | CACHE-44 |
| Archive folder file without a sidecar during rebuild | Reported and left alone; every Drive file stays byte-for-byte unchanged | CACHE-60, CACHE-62 |

## 2.13 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves before Gate 1

**Resolved on 2026-10-22.** The owner answered every open question in v3 (owner decision, 2026-10-22): why now (1.1); group sizes (1.2); the reasons for the annotation and archive-sync non-goals (1.3); the CACHE-OUT-1 baseline and no further component outcomes (1.4); the leaps of faith, drafted for approval (1.5); the invariants, each with a P1 criterion, including the new CACHE-62 (1.6, 2.4); ADR 0007 and ADR 0008 accepted at Gate 1, and O3, O5 and O8 closed as recommended (1.7); the user stories, drafted for approval, and the Story column (2.2, 2.4); collection export covered by CACHE-63 and CACHE-FR-3 verified by SEC-8 (2.4, "Verified elsewhere"); no component NFR targets (2.5); classification and retention (2.6); integration owners and SLAs (2.7); value, usability and viability risks, drafted for approval (2.8); rollout and support (2.9); done (2.11); and D3 and ADR 0007 marked "amended by ADR 0011" wherever they are listed.

- Requirement IDs from other areas keep their area code as the prefix (`FR-PLAT-21` became `PLAT-FR-21`, `FR-SRCH-26` became `SRCH-FR-26`), as the sibling PRDs now confirm.

**Gate 1 follow-up (owner decision, 2026-10-22).** Backups follow the sources: the last 7 are kept, as CACHE-49 and PLAT-FR-57 say (PRD-v7 2.4; 2.6 above). CACHE-INV-4 is the same rule as SEC-INV-5, and CACHE-INV-3 applies SEC-INV-7 to the cache's files; the Security component owns both. A breach of any invariant halts the rollout (PRD-v7 2.6).

## 2.14 Glossary

> **Owner:** A · **Persona:** `product-writer`

| Term | Definition |
| --- | --- |
| `cached` | A fetched document with `expires_at` 120 days after fetch (FR-CACHE-30) |
| `expiring` | A document in an open review batch (FR-CACHE-31) |
| `kept` | A document whose review went unanswered; it keeps its files and is asked about again after 7 days (FR-CACHE-34) |
| `pinned` | A document kept on the Mac indefinitely; it never expires (FR-CACHE-37; ADR 0011) |
| `archived` | A document whose file moved to the Drive archive; its text, chunks, FTS entries and embeddings stay in `cache.db` (FR-CACHE-49) |
| `discarded` | A document whose file is in the 7-day trash or purged; its work metadata, citation snapshot and fetch recipe are kept (FR-CACHE-36) |
| Review batch | The set of documents the daily review asks the owner about, announced by one notification (FR-CACHE-31, FR-CACHE-32) |
| Trash | The 7-day holding period for discarded files, during which undo is possible (FR-CACHE-36) |
| Fetch recipe | The stored instructions that can re-fetch a document later (FR-CACHE-05) |
| Sidecar | `<slug>.meta.json`, the metadata file written next to each archived file (FR-CACHE-46) |
| Fallback folder | The local folder used when the Drive folder is unavailable, default `~/Research Archive/<year>/` (FR-CACHE-48) |
| Reconcile | The job that moves fallback items to Drive and confirms uploads (FR-CACHE-48; SPEC-v2 9.3) |
| Coverage | Embedded chunks divided by all chunks, for the documents in scope (SPEC-v2 8.3) |

## 2.15 ID history

> **Owner:** C · **Persona:** `product-writer` records; the owner confirms

No ID left this PRD in version 4.

| ID | Status | Replaced by | Reason |
| --- | --- | --- | --- |

New IDs and editorial changes in this version; these rows are not definitions.

| Changed or new ID | Change | Date | Reason |
| --- | --- | --- | --- |
| CACHE-63 | New criterion: `cite` with a `collection` exports every item in that collection in the requested format | 2026-10-22 | owner decision, 2026-10-22 |
| CACHE-US-1 to CACHE-US-6 | New user stories, drafted by the product writer and approved by the owner at Gate 1, 2026-10-22; the Story column of every CACHE-FR row now names one of them | 2026-10-22 | owner decision, 2026-10-22 |
| CACHE-62 | New P1 criterion: archive reindex leaves every Drive file unchanged, the P1 check of CACHE-INV-6 | 2026-10-22 | owner decision, 2026-10-22 |
| CACHE-FR-30 | Editorial: "per open decision O7" now reads "per decision O7, now closed"; behavior unchanged | 2026-10-22 | owner decision, 2026-10-22 |
| CACHE-OUT-1 | Baseline added: v1 has no lifecycle; nothing is reviewed or deleted, and the corpus only grows | 2026-10-22 | owner decision, 2026-10-22 |
| CACHE-INV-1 to CACHE-INV-7 | Confirmed as component invariants; each names a P1 criterion | 2026-10-22 | owner decision, 2026-10-22 |

### Gate 1: Requirements approved

| Approver | Date | Notes |
| --- | --- | --- |
| Kenny Hill (Product) | 2026-10-22 | Approved in chat; recorded by Claude in the owner's name at his direction |

## 2.16 Earlier IDs

> **Owner:** A · **Persona:** `product-writer`

| Earlier ID | New ID |
| --- | --- |
| FR-CACHE-01 | CACHE-FR-1 |
| FR-CACHE-02 | CACHE-FR-2 |
| FR-CACHE-03 | CACHE-FR-3 |
| FR-CACHE-04 | CACHE-FR-4 |
| FR-CACHE-05 | CACHE-FR-5 |
| FR-CACHE-06 | CACHE-FR-6 |
| FR-CACHE-07 | CACHE-FR-7 |
| FR-CACHE-10 | CACHE-FR-10 |
| FR-CACHE-11 | CACHE-FR-11 |
| FR-CACHE-12 | CACHE-FR-12 |
| FR-CACHE-13 | CACHE-FR-13 |
| FR-CACHE-14 | CACHE-FR-14 |
| FR-CACHE-15 | CACHE-FR-15 |
| FR-CACHE-16 | CACHE-FR-16 |
| FR-CACHE-17 | CACHE-FR-17 |
| FR-CACHE-18 | CACHE-FR-18 |
| FR-CACHE-20 | CACHE-FR-20 |
| FR-CACHE-21 | CACHE-FR-21 |
| FR-CACHE-22 | CACHE-FR-22 |
| FR-CACHE-23 | CACHE-FR-23 |
| FR-CACHE-24 | CACHE-FR-24 |
| FR-CACHE-30 | CACHE-FR-30 |
| FR-CACHE-31 | CACHE-FR-31 |
| FR-CACHE-32 | CACHE-FR-32 |
| FR-CACHE-33 | CACHE-FR-33 |
| FR-CACHE-34 | CACHE-FR-34 |
| FR-CACHE-35 | CACHE-FR-35 |
| FR-CACHE-36 | CACHE-FR-36 |
| FR-CACHE-37 | CACHE-FR-37 |
| FR-CACHE-38 | CACHE-FR-38 |
| FR-CACHE-45 | CACHE-FR-45 |
| FR-CACHE-46 | CACHE-FR-46 |
| FR-CACHE-47 | CACHE-FR-47 |
| FR-CACHE-48 | CACHE-FR-48 |
| FR-CACHE-49 | CACHE-FR-49 |
| FR-CACHE-50 | CACHE-FR-50 |
| FR-CACHE-51 | CACHE-FR-51 |
| FR-CACHE-52 | CACHE-FR-52 |
| FR-CACHE-55 | CACHE-FR-55 |
| FR-CACHE-56 | CACHE-FR-56 |
| FR-CACHE-57 | CACHE-FR-57 |
| FR-CACHE-58 | CACHE-FR-58 |
| FR-CACHE-59 | CACHE-FR-59 |
| AT-CACHE-01 | CACHE-1 |
| AT-CACHE-02 | CACHE-2 |
| AT-CACHE-10 | CACHE-10 |
| AT-CACHE-11 | CACHE-11 |
| AT-CACHE-12 | CACHE-12 |
| AT-CACHE-13 | CACHE-13 |
| AT-CACHE-14 | CACHE-14 |
| AT-CACHE-15 | CACHE-15 |
| AT-CACHE-16 | CACHE-16 |
| AT-CACHE-17 | CACHE-17 |
| AT-CACHE-18 | CACHE-18 |
| AT-CACHE-19 | CACHE-19 |
| AT-CACHE-20 | CACHE-20 |
| AT-CACHE-21 | CACHE-21 |
| AT-CACHE-22 | CACHE-22 |
| AT-CACHE-23 | CACHE-23 |
| AT-CACHE-24 | CACHE-24 |
| AT-CACHE-30 | CACHE-30 |
| AT-CACHE-31 | CACHE-31 |
| AT-CACHE-32 | CACHE-32 |
| AT-CACHE-33 | CACHE-33 |
| AT-CACHE-34 | CACHE-34 |
| AT-CACHE-35 | CACHE-35 |
| AT-CACHE-36 | CACHE-36 |
| AT-CACHE-40 | CACHE-40 |
| AT-CACHE-41 | CACHE-41 |
| AT-CACHE-42 | CACHE-42 |
| AT-CACHE-43 | CACHE-43 |
| AT-CACHE-44 | CACHE-44 |
| AT-CACHE-45 | CACHE-45 |
| AT-CACHE-46 | CACHE-46 |
| AT-CACHE-47 | CACHE-47 |
| AT-CACHE-60 | CACHE-60 |
| AT-CACHE-61 | CACHE-61 |
| AT-CACHE-48 | CACHE-48 |
| AT-CACHE-49 | CACHE-49 |
