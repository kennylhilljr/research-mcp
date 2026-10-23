---
title: "Research MCP v2 system design"
type: spec
version: 3
status: draft
owner: "Kenny Hill"
parent: docs/prd/PRD-v5.md
artifact_type: high-level-design
scope_level: L3
scope_name: "research-mcp"
supersedes: docs-archive/design/HLD-v3.md
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# SPEC: Research MCP v2 system design (v3)

- **Requirements:** [PRD-v5](../prd/PRD-v5.md) and its component PRDs ([platform](../prd/components/PRD-platform-v3.md), [sources](../prd/components/PRD-sources-v4.md), [search](../prd/components/PRD-search-v2.md), [cache](../prd/components/PRD-cache-v3.md), [health](../prd/components/PRD-health-v3.md), [ui](../prd/components/PRD-ui-v3.md), [migration](../prd/components/PRD-migration-v4.md), [security](../prd/components/PRD-security-v1.md)).
- **Detail:** the component LLDs in [docs/lld/](../lld/): `LLD-platform-v1`, `LLD-sources-v1`, `LLD-search-v1`, `LLD-cache-v1`, `LLD-health-v1`, `LLD-ui-v1`, `LLD-migration-v1`, `LLD-security-v1`. Section 19 says which LLD carries which part of SPEC-v2.
- **Tests:** [test plan v1](../test/test-plan-v1.md).
- **Decisions:** [ADRs 0001 to 0013](../adr/) (section 16).

## Provenance and changes

This version moves the high level design onto the spec-driven development framework ([standard v2](../standards/spec-driven-development-v2.md), [ADR 0013](../adr/0013-adopt-spec-driven-development.md), proposed). Sections 1 to 14 carry over [HLD-v3](../../docs-archive/design/HLD-v3.md) with the same numbers and titles, so documents that cite "HLD section N" still match; only references were updated (SPEC v1 and v2 sections now point to the LLD that holds them, requirement and criterion IDs use the SDD scheme). The architecture parts of [SPEC-v2](../../docs-archive/spec/SPEC-v2.md) (conventions in its section 1) move to section 15; its detailed contracts move to the LLDs. Sections 15 to 20 are new and follow the [SPEC template](../templates/SPEC-template.md).

ID scheme used here: `FR-<AREA>-nn` became `<PREFIX>-FR-n`, `NFR-nn` became `NFR-n`, goals `Gn` became `OUT-n`, and acceptance tests `AT-<AREA>-nn` became criteria `<PREFIX>-n` (`AT-SEC-nn` became `SEC-n`). Leading zeros are dropped.

Carried from HLD-v3, changes from its v2: owner decisions of 2026-10-19, second round ([ADR 0012](../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md)): the design is domain-neutral (topic coverage is configuration); every endpoint v1 calls is kept; web search returns as an optional, capped source group (`web`: Vertex AI Search, Brave, SerpAPI, Programmable Search) that runs only on request, in fallback order by default (sections 4, 5 and 9). M0 is unchanged.

Carried from HLD-v3, earlier changes (v2): owner decisions of 2026-10-19: cache retention is **120 days** instead of 30, and **archiving keeps a paper searchable**: only the PDF moves to Google Drive; extracted text, chunks, full-text entries and embeddings stay in `cache.db`, and a rebuild job can re-import the archive from Drive. See [ADR 0011](../adr/0011-archive-keeps-text-searchable-120-day-retention.md).

## 1. Scope

> **Owner:** C · **Persona:** `architect`

This document describes the shape of v2: the processes, the main components and how they talk, the data each owns, the security boundaries, and the key flows. Module names, schemas, signatures and interfaces are in the component LLDs (`docs/lld/LLD-<component>-v1.md`); section 19 maps each component to its LLD. Where the M0 work breakdown now lives is open (section 20).

## 2. System context

> **Owner:** C · **Persona:** `architect`

```
 +-------------------+   +-------------------+   +-------------------+
 | Claude Code       |   | Claude desktop    |   | OpenClaw agents,  |
 | (MCP client)      |   | (MCP client)      |   | Codex (MCP)       |
 +---------+---------+   +---------+---------+   +---------+---------+
           | stdio                 | stdio                 | stdio or loopback HTTP
           v                       v                       v
 +---------------------------------------------------------------------+
 | research-mcp stdio  (thin shim, one per client; no state)            |
 +----------------------------------+----------------------------------+
                                    | streamable HTTP, 127.0.0.1, bearer token
                                    v
 +---------------------------------------------------------------------+
 | research-mcpd  (one daemon per Mac, launchd KeepAlive)               |
 |  MCP endpoint /mcp  |  UI /ui  |  /healthz /readyz /api/status       |
 |  services: federation, works, cache, health, notify, jobs, scheduler |
 |  source registry (about 42 adapters)  |  shared async HTTP client    |
 |  stores: state.db, cache.db  |  workers (one subprocess per task)    |
 +---+--------------+-----------------+-----------------+--------------+
     |              |                 |                 |
     v              v                 v                 v
 Upstream APIs   macOS Keychain   Google Drive sync   macOS notifications,
 (arXiv, OpenAlex (secrets,       folder (archive)    OpenClaw inbox webhook
 Crossref, ...,   read only)
 upstream MCPs)
           ^
           | doctor (launchd: liveness every 15 min, full check daily; independent of the daemon)
```

Trust boundaries:

1. **Upstream content is untrusted.** Everything that comes from an API or a downloaded file is data; it is labeled untrusted when returned to a model.
2. **Local callers are authenticated.** Only the shim (with the bearer token) and the UI (with a session) can call the daemon.
3. **Secrets never leave the HTTP layer** except to the origin they belong to.

The adapter count in the diagram is carried over as written; the source count differs between documents (section 20).

## 3. Component architecture

> **Owner:** C · **Persona:** `architect`

The daemon is one Python process built in layers. Each layer depends only on the layers below it.

```
 transport    mcp_app (tools, resources, prompts)      ui (pages)      http_api (status)
                 |                                        |                 |
 services     federation   works   cache   health   notify   jobs   scheduler
                 |            |       |       |        |
 sources      registry -> adapters (one module per source; SourceSpec)
                 |
 platform     http client (rate limits, retries, redaction, telemetry)   secrets (Keychain)
              stores (state.db, cache.db; migrations)   workers (subprocess per task)   settings   logging
 core         ids, models, errors, envelope, time (no I/O)
```

Rules ([ADR 0004](../adr/0004-modular-core-composition-root.md), [ADR 0005](../adr/0005-async-io-cpu-off-loop.md)):

- `core` has no I/O and no third-party service dependencies.
- Adapters translate only; they never retry, sleep, read secrets or write files ([ADR 0006](../adr/0006-source-adapter-contract.md)).
- Tools are thin: validate arguments, call one service, wrap the result in the envelope.
- One composition root, `build_app(settings)`, creates everything inside a lifespan. Nothing happens at import.
- Network I/O is async; CPU-heavy work (PDF parsing, chunking, embedding) runs in one short-lived subprocess per task, killed on timeout or memory limit; SQLite access runs in a thread with one writer per database.

**Detail:** package layout, composition root and workers in [LLD-platform-v1](../lld/LLD-platform-v1.md) §5 (from SPEC-v2 sections 1, 3.6 and 7.4). Requirements: PLAT-FR-1 to PLAT-FR-6; NFR-1, NFR-2.

## 4. Sources

> **Owner:** C · **Persona:** `architect`

- A **`SourceSpec`** declares each source: capabilities, identifier schemes, auth, rate policy, timeouts, page size, extras, probe, shutdown date, default enabled.
- An **adapter** implements `search`, `get`, `fulltext_candidates`, `citations` and `probe` for the capabilities it declares, returning normalized `WorkRecord`s with provenance.
- The **registry** discovers adapters, creates configured instances (four DSpace repositories, docs sites, Vertex AI Search engines), applies enable and disable settings, and answers "which sources can do X for group Y right now", combining configuration with live health.
- **Upstream MCP servers** (AWS Knowledge, Microsoft Learn) are adapters that use an MCP client instead of HTTP JSON.
- **Site sets** are named domain lists in configuration (v1's docs-domain list ships as `v1_docs`). Topic coverage, in any subject area, is added by configuring docs sites, site sets and search engines, not by code.
- **Web search** is the `web` group: four optional, metered sources, each off until configured and capped per day. It is never in the default fan-out.
- **Testing:** every adapter has seven recorded fixtures and runs through one conformance suite; an opt-in live check refreshes fixtures.

**Detail:** the source contract, registry, fixtures, conformance, live check, new-source checklist, site sets and web search in [LLD-sources-v1](../lld/LLD-sources-v1.md) §2 and §5 (from SPEC-v2 sections 4 and 5.1 to 5.5). Requirements: SRC-FR-1 to SRC-FR-23 ([PRD-sources-v4](../prd/components/PRD-sources-v4.md)); OUT-1, OUT-3.

## 5. Federation and identity

> **Owner:** C · **Persona:** `architect`

```
 search(query, sources, filters, limit, cursor)
   -> registry.select(groups, filters, health)          # auto selection, skips down/unconfigured
   -> fan out: one task per source, per-source timeout, overall deadline
   -> per source: SearchPage(records, cursor) or SourceStatus(error)
   -> identity.resolve(records)                          # normalize ids, union-find on shared ids
   -> merge(records -> works), fuzzy merge flagged
   -> rank: reciprocal rank fusion + found-in-more-sources boost
   -> budget: trim to response budget, build combined cursor
   -> envelope {data: works, source_status: [...], next_cursor, truncated}
```

- **Identity:** `core.ids` normalizes identifiers (pure functions); `services/works.py` groups records by any shared identifier; if no identifier is shared, fall back to normalized title, year and first-author surname, flagged `fuzzy`.
- **`get_work`** resolves an identifier against every source that understands its scheme, merges the records, and adds open-access locations, integrity status and cache state.
- **The `web` group** runs in `fallback` order by default: the configured web sources are tried one at a time (Vertex, Brave, SerpAPI, Programmable Search) until one answers, so a request spends at most one paid query per page. With `strategy = "all"` they fan out like any other group. A `site_set` restricts the domains.
- **Citations, authors, cite and integrity** are services over the same registry and identity layer.

**Detail:** identity, federation, the tool catalog, resources and prompts in [LLD-search-v1](../lld/LLD-search-v1.md) §2 and §5 (from SPEC-v2 sections 6, 7.1, 7.2 and 7.3); the envelope and budget in [LLD-platform-v1](../lld/LLD-platform-v1.md) §2 (from SPEC-v2 section 3.7). Requirements: SRCH-FR-1 to SRCH-FR-26 ([PRD-search-v2](../prd/components/PRD-search-v2.md)), SRC-FR-21, SRC-FR-22; OUT-2; NFR-5.

## 6. Retrieval and cache

> **Owner:** C · **Persona:** `architect`

```
 fetch(id or url)
   -> works.resolve -> OA locations from all sources -> choose by preference
   -> downloader: https, host policy per hop, public IPs only, byte cap, magic bytes, atomic write, sha256
   -> worker: extract (PyMuPDF, limits) -> chunk (token, section aware) -> embed (passage)
   -> cache.db: document (state=cached, expires_at=+120d), file, extraction, chunks, FTS, vectors
   -> envelope {doc_id, summary, pages, chunks, coverage}
```

The lifecycle state machine ([ADR 0007](../adr/0007-cache-lifecycle-and-drive-archive.md), [ADR 0011](../adr/0011-archive-keeps-text-searchable-120-day-retention.md)):

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

**Detail:** the `cache.db` schema in [LLD-cache-v1](../lld/LLD-cache-v1.md) §3 (from SPEC-v2 section 8.1); extraction, chunking, local search, state transitions, review batch, archive, disk and integrity, collections and archive rebuild in LLD-cache-v1 §5 (from SPEC-v2 sections 8.2, 8.3, 9.1 to 9.5 and 9.7); the downloader in [LLD-platform-v1](../lld/LLD-platform-v1.md) §5 (from SPEC-v2 section 3.4). Requirements: CACHE-FR-1 to CACHE-FR-59 ([PRD-cache-v3](../prd/components/PRD-cache-v3.md)); OUT-6.

## 7. Health, credentials and notifications

> **Owner:** C · **Persona:** `architect`

```
 HTTP client --telemetry--> state.db.calls --rollup--> source_health
 scheduler --probes--> adapters.probe() ----------------^
 secrets --metadata--> state.db.credentials <-- passive headers (GitHub expiry, rate limits)
 health.evaluate() -> source and credential states -> diff -> notify (macOS, OpenClaw webhook, UI banner)
 doctor (launchd: liveness every 15 min, full daily) -> same checks without the daemon -> notify on change
```

- **States** follow [PRD-health-v3](../prd/components/PRD-health-v3.md): source states HLTH-FR-10 to HLTH-FR-12 and credential states HLTH-FR-20 to HLTH-FR-25 (section 2 of PRD-health-v2).
- **Notifications** fire on state changes and roll unresolved items into a daily digest, with quiet hours.
- **Federation** consults health before selecting sources.

**Detail:** the `state.db` schema in [LLD-health-v1](../lld/LLD-health-v1.md) §3 (from SPEC-v2 section 10.1); probes, state evaluation, credential validation and notifications in LLD-health-v1 §5 (from SPEC-v2 sections 10.2 to 10.4); doctor and the status endpoints in LLD-health-v1 §2 (from SPEC-v2 section 10.5). Requirements: HLTH-FR-1 to HLTH-FR-43; OUT-4, OUT-5.

## 8. Local UI

> **Owner:** C · **Persona:** `architect`

- **Stack:** Starlette routes and Jinja2 templates in the daemon, with a vendored htmx file for partial refresh and confirmation dialogs ([ADR 0010](../adr/0010-localhost-ui-stack.md)).
- **Data access:** pages read the same services the MCP tools use, so there is no second API.
- **Sessions:** a session starts from a one-time token URL. All writes need CSRF tokens and confirmation.
- **Pages:** source board, credentials, quota, jobs, cache, review, archive, maintenance, events, settings.

**Detail:** [LLD-ui-v1](../lld/LLD-ui-v1.md) (from SPEC-v2 section 11). Requirements: UI-FR-1 to UI-FR-19 ([PRD-ui-v3](../prd/components/PRD-ui-v3.md)); OUT-8.

## 9. Security architecture

> **Owner:** C · **Persona:** `security-reviewer`

| Threat | Control |
|---|---|
| Prompt-injected model tries to read local files | No SQL tool; no caller-chosen paths; files only under the cache root; DuckDB (if used internally) locked down ([ADR 0009](../adr/0009-no-sql-untrusted-content.md)). |
| Prompt-injected model tries to delete data | No hard delete in MCP; the only MCP discard is a review decision inside an open batch, recorded as an agent decision, sent to a 7-day trash and announced to the owner at once with an undo link; the owner is notified again 24 hours before any purge; annotations mark state-changing tools. |
| Secret leaks into chat or logs | Keychain (the Google sign-in excepted, see below); `Secret` type; origin-scoped attachment; header placement; one redaction filter on logs, errors, UI and notifications; errors carry codes, not exception text. |
| Paid web-search spend runs away | Web sources off until configured, never in the default fan-out, fallback order (one paid query per page), daily caps that switch a source to `budget_exhausted`. |
| Google sign-in token misuse | `gcloud` owns the sign-in; v2 holds only a short-lived access token in memory and attaches it only to `discoveryengine.googleapis.com`. |
| SSRF and hostile downloads | One downloader: https, per-hop host policy, public IPs only with the connection pinned to the checked IP (no second DNS lookup), byte cap, magic bytes, atomic write. |
| Hostile PDFs | Parsing in a separate subprocess per document with a CPU limit, an RSS watchdog, a wall-clock timeout and a page cap; a crash affects only that document. |
| Other local processes call the daemon | Loopback only, bearer token, Host and Origin checks; UI session cookie plus CSRF. |
| Upstream drift returns wrong data | Probes check response shape; fixtures pinned in tests; per-source disable. |
| Supply chain | Lock file, weekly dependency audit, SHA-pinned CI actions, secret scan. |

**Detail:** secrets, the Google sign-in and redaction in [LLD-security-v1](../lld/LLD-security-v1.md) §4 (from SPEC-v2 sections 3.1, 3.1.1 and 3.2); the downloader and HTTP client in [LLD-platform-v1](../lld/LLD-platform-v1.md) §5 (from SPEC-v2 sections 3.3 and 3.4). Requirements: [PRD-security-v1](../prd/components/PRD-security-v1.md), criteria SEC-1 to SEC-23; OUT-7; NFR-3, NFR-4, NFR-6, NFR-7.

## 10. Data stores

> **Owner:** C · **Persona:** `architect`

| Store | Location | Owns | Backed up |
|---|---|---|---|
| `state.db` (SQLite, WAL) | `~/Library/Application Support/research-mcp/` | Credential metadata, source health, call telemetry and rollups, searches, jobs, schedule runs, notifications, review batches and a copy of review events | Nightly, 7 kept |
| `cache.db` (SQLite, WAL, FTS5, vector BLOBs) | `~/Library/Application Support/research-mcp/cache/` | Works, identifiers, source records, documents and lifecycle (including pins, decisions and archive paths), files, extractions, chunks, FTS, embeddings, collections, outbox | Nightly, 7 kept |
| Files | `~/Library/Application Support/research-mcp/cache/files/` (by SHA-256) and `trash/` | Cached PDFs and HTML | No (re-fetchable; archived copies live in Drive) |
| Model cache | `~/Library/Caches/research-mcp/models/` | Embedding model files | No (re-downloadable) |
| Archive | Drive sync folder `My Drive/Research Archive/<year>/` | Archived files and sidecars (their text stays in `cache.db`) | By Google Drive; also the source for the archive rebuild job |
| Config | `~/.config/research-mcp/config.toml` | Settings and secret references | Nightly with `state.db` |
| Secrets | macOS login Keychain, `research-mcp/<NAME>` | Credential values and the daemon token | By Keychain |

Nothing the lifecycle depends on lives in `~/Library/Caches`, which macOS and cleaning tools may purge. Both databases are backed up; only re-fetchable files are not.

**Detail:** settings, paths, stores, migrations and backups in [LLD-platform-v1](../lld/LLD-platform-v1.md) §3 (from SPEC-v2 sections 2, 3.5 and 9.8); `cache.db` in [LLD-cache-v1](../lld/LLD-cache-v1.md) §3 (from SPEC-v2 section 8.1); `state.db` in [LLD-health-v1](../lld/LLD-health-v1.md) §3 (from SPEC-v2 section 10.1). Requirements: PLAT-FR-8, PLAT-FR-9, PLAT-FR-56, PLAT-FR-57.

## 11. Key flows

> **Owner:** C · **Persona:** `architect`

### 11.1 Cross-source search

1. The agent calls `search("policy-as-code adoption", sources="auto", filters={year_from: 2023})`.
2. The registry selects `openalex`, `crossref`, `semantic_scholar`, `arxiv`, `core`, `dblp` and `ssrn` from the default groups, and reports `ads` as `disabled`. (Had OpenAlex's budget been spent, it would be reported `skipped_budget` instead of selected.)
3. Seven tasks run with 5 s source timeouts inside an 8 s deadline.
4. The returned records are normalized, grouped by shared identifiers, merged and ranked.
5. The agent gets 20 works with `found_in`, plus seven `source_status` entries; one says `timeout`.

### 11.2 Fetch and read

1. `fetch("doi:10.1145/3649835")` resolves OA locations from Unpaywall, OpenAlex and the publisher, picks the best one and downloads it safely.
2. A worker extracts, chunks and embeds the document.
3. The document is stored as `cached` until a date 120 days out.
4. `read(doc_id, pages="3-5")` returns a bounded window with a cursor.

### 11.3 Expiry review and archive

1. At 09:00 the scheduler finds 6 documents expiring within 3 days and creates batch `rb-2026-11-14`.
2. The owner gets one macOS notification.
3. Clicking it opens `/ui/review/rb-2026-11-14`. The owner archives 2, discards 3 and leaves 1 unanswered.
4. The archive job copies 2 files plus sidecars to Drive, verifies them, and removes the cached PDFs; both papers stay searchable through their text in `cache.db`.
5. The 3 discards go to the trash for 7 days.
6. When the batch closes 24 hours later, the unanswered item becomes `kept` and is asked about again on 2026-11-22.

### 11.4 Credential expiring

1. A GitHub call returns `GitHub-Authentication-Token-Expiration` 13 days out, and the credential becomes `expiring_soon(13)`.
2. The state change produces a notification: "GitHub token expires in 13 days: rotate in Keychain item research-mcp/GITHUB_TOKEN".
3. Clicking it opens the Credentials page, which links to GitHub's token page and shows the value-free `security` command.
4. After rotating, the owner presses "Reload credentials". The fingerprint changes, the next call shows the new expiry, and the state returns to `ok`.

## 12. Deployment and operations

> **Owner:** C · **Persona:** `sre`

| Topic | Approach |
|---|---|
| **Install** | `uv tool install` (or a venv) for the package, then `research-mcp install`. Install writes three LaunchAgents (`local.research-mcpd` with KeepAlive; `local.research-mcp-watchdog` every 15 minutes; `local.research-mcp-doctor` daily at 08:52), creates the folders, generates the daemon token in Keychain, makes the first archive write in the foreground (for the macOS privacy prompt), and prints the client configs. |
| **Upgrade** | `research-mcp upgrade` with rollback on a failed `doctor`. |
| **Logs** | JSON lines with rotation. The UI shows recent warnings and errors. |
| **Backups** | Nightly copy of `state.db`, `cache.db` and the config. |
| **Parallel run with v1** | v1 stays installed under its old client entry, disabled at cutover, until retirement ([ADR 0001](../adr/0001-new-repo-v1-read-only.md)). |

**Detail:** packaging, CI, the CLI, launchd templates, install and upgrade in [LLD-platform-v1](../lld/LLD-platform-v1.md) §5 and §7 (from SPEC-v2 sections 12.1 and 12.2); legacy import and cutover in [LLD-migration-v1](../lld/LLD-migration-v1.md) (from SPEC-v2 section 9.6 and [MIGRATION-v2](../../docs-archive/migration/MIGRATION-v2.md)). Requirements: PLAT-FR-40 to PLAT-FR-42, PLAT-FR-50 to PLAT-FR-58, MIG-FR-1 to MIG-FR-24 ([PRD-migration-v4](../prd/components/PRD-migration-v4.md)).

## 13. Quality attributes

> **Owner:** C · **Persona:** `architect`

| Attribute | How it is met |
|---|---|
| Maintainability | One adapter module per source; conformance suite; generated inventory; strict typing; no module over about 400 lines. |
| Reliability | Per-source isolation in fan-out; retries with backoff; circuit-breaking through health states; worker isolation for parsing. |
| Performance | Concurrent fan-out with deadlines; shared connection pools; response budgets; FTS5 and exact vectors at personal-corpus scale (thousands of chunks). |
| Observability | Call telemetry, probes, states, notifications, structured logs, status endpoints, UI. |
| Security | Section 9. |
| Cost | Global rate limits and budgets for metered sources; quota states; no paid search providers. |

The Cost row is carried over as written in HLD-v3; it conflicts with the optional paid `web` group (section 20).

## 14. Milestones and where they land

> **Owner:** C · **Persona:** `architect`

| Milestone | Components built |
|---|---|
| M0 | core, platform (settings, secrets, HTTP, downloader, stores, logging, jobs, scheduler), sources (contract, registry, arXiv, Crossref, OpenAlex), federation, tools `search`, `get_work`, `list_sources`, daemon, shim, install, CI |
| M1 | all other adapters; citations, authors, cite, integrity; health, credentials, notifications, doctor |
| M2 | workers, extraction, cache lifecycle, review, searchable archive and its rebuild job, collections, crawl jobs, disk and integrity checks |
| M3 | UI |
| M4 | secrets import, legacy import, client cutover, v1 retirement |

The M0 unit list and the later milestone outlines were in SPEC-v2 sections 12.3 and 12.4, with the M0 unit to criterion map in TEST-PLAN-v3 Appendix A; their new home is an open question (section 20).

## 15. Architecture principles and approved stack

> **Owner:** H · **Persona:** none · **Seed question:** 9

This section is an H section. Its content is carried over unchanged from owner-approved sources (SPEC-v2 section 1 conventions and the architectural rules in [AGENTS.md](../../AGENTS.md)); nothing here is new. The owner confirms it at Gate 2 (section 20).

**Stack and conventions** (from SPEC-v2 section 1):

- Python 3.12 (uv-managed interpreter, which bundles a current SQLite), `uv`, `src/` layout, package `research_mcp`, version `3.0.0`.
- Typing: mypy strict on `src/`; Pydantic v2 models for everything that crosses a module boundary or the MCP boundary.
- Async: `anyio`; HTTP with `httpx.AsyncClient`; SQLite with `aiosqlite` through the store classes only.
- Time: UTC everywhere (`datetime` with `tzinfo=UTC`), stored as ISO 8601 text; the scheduler converts to local time for 09:00 and quiet hours.
- IDs: ULIDs for internal rows (`works.work_id`, `documents.doc_id`, jobs, batches).
- Tests: pytest with `--import-mode=importlib`; test folders have no `__init__.py`; shared test helpers live in the package `research_mcp.testing` so tests import them by absolute name.
- No em dashes or en dashes in code comments, docs or UI strings (NFR-11).

Further stack choices already recorded as decisions: macOS Keychain for secrets ([ADR 0003](../adr/0003-secrets-in-keychain.md)); two SQLite files with FTS5 and vectors in SQLite ([ADR 0008](../adr/0008-sqlite-stores-and-vectors.md)); Starlette, Jinja2 and htmx for the UI ([ADR 0010](../adr/0010-localhost-ui-stack.md)). Dependencies, extras and tool settings are in [LLD-platform-v1](../lld/LLD-platform-v1.md) (from SPEC-v2 section 12.1).

**Architectural rules** (from AGENTS.md):

- Adapters (`src/research_mcp/sources/`) only translate: no HTTP library imports, no sleeping, no retries, no secrets, no file writes.
- No tool may block the event loop; CPU work goes to worker subprocesses (`platform/workers.py`).
- Tests pass with the network blocked; use `FakeProvider`, recorded fixtures and the fakes in `research_mcp.testing`.
- Never print, log, commit or put in fixtures any secret, token or password. Fixtures are recorded with credentials removed.
- Every change needs tests.

## 16. Key decisions

> **Owner:** C · **Persona:** `architect` drafts ADR options; the owner decides · **Seed question:** 10

Statuses are copied from each ADR file as of 2026-10-22.

| ADR | Decision | Status |
| --- | --- | --- |
| [ADR 0001](../adr/0001-new-repo-v1-read-only.md) | v2 is a new repository; v1 stays read-only and running until cutover | proposed (accepted when the owner approves PRD v1) |
| [ADR 0002](../adr/0002-one-daemon-with-stdio-shims.md) | One daemon per Mac; clients use a stdio shim | proposed (accepted when the owner approves PRD v1) |
| [ADR 0003](../adr/0003-secrets-in-keychain.md) | Secrets live in the macOS Keychain; configuration holds references | proposed (accepted when the owner approves PRD v1) |
| [ADR 0004](../adr/0004-modular-core-composition-root.md) | Modular core built by one composition root; no work at import | proposed (accepted when the owner approves PRD v1) |
| [ADR 0005](../adr/0005-async-io-cpu-off-loop.md) | Async I/O end to end; CPU work in worker processes | proposed (accepted when the owner approves PRD v1) |
| [ADR 0006](../adr/0006-source-adapter-contract.md) | Every source is an adapter with a declarative `SourceSpec` | proposed (accepted when the owner approves PRD v1) |
| [ADR 0007](../adr/0007-cache-lifecycle-and-drive-archive.md) | Cache with owner review; archive to the Google Drive sync folder | proposed; amended by ADR 0011 |
| [ADR 0008](../adr/0008-sqlite-stores-and-vectors.md) | Two SQLite files; vectors stored in SQLite | proposed (accepted when the owner approves PRD v1) |
| [ADR 0009](../adr/0009-no-sql-untrusted-content.md) | No free-form SQL; fetched content is labeled untrusted | proposed (accepted when the owner approves PRD v1) |
| [ADR 0010](../adr/0010-localhost-ui-stack.md) | The UI is server-rendered inside the daemon | proposed (accepted when the owner approves PRD v1) |
| [ADR 0011](../adr/0011-archive-keeps-text-searchable-120-day-retention.md) | 120-day retention; archived papers stay searchable (amends 0007) | accepted (owner decision, 2026-10-19) |
| [ADR 0012](../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md) | Domain-neutral scope; every v1 endpoint kept; web search as optional sources | accepted (owner decision, 2026-10-19) |
| [ADR 0013](../adr/0013-adopt-spec-driven-development.md) | Adopt spec-driven development | proposed |

## 17. Testing strategy

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 2

Carried over from TEST-PLAN-v3 sections 2, 3 and 8 for the `test-architect` to review. How each criterion is verified is in the [test plan v1](../test/test-plan-v1.md); per-criterion coverage is generated in `docs/trace/coverage.md`.

**Test levels and environments** (TEST-PLAN-v3 section 2):

| Level | Runs | Network | External systems |
|---|---|---|---|
| unit | every work unit and commit (`tools/ci.sh --python-only`) | blocked | none |
| integration | every commit | blocked | fakes from `research_mcp.testing`: `httpx.MockTransport` with recorded fixtures, `FakeProvider`, `FakeClock` and fake sleeper, fake `launchctl`, fake notifier, injected resolver, temp folders for Drive |
| contract | every commit | blocked | in-memory MCP client (`mcp.shared.memory`) against `build_mcp` |
| live | opt-in (`pytest -m live`), nightly on the Mac later | allowed | real upstreams, no credentials unless the owner runs it locally |

Network blocking: `tests/conftest.py` installs a socket guard that fails any test opening a non-loopback connection unless it is marked `live`; `pyproject.toml` deselects `live` tests by default (`-m 'not live'`). Tests run with `--import-mode=importlib`; test folders have no `__init__.py`.

Secrets in tests: only `FakeProvider` with generated values; the security suite registers those values with the redactor and scans every output.

**Cross-cutting criteria that every milestone keeps green** (TEST-PLAN-v3 section 3):

| Area | Rule | Criteria |
|---|---|---|
| No secret in any output | Logs, errors, tool results, UI pages, notifications and process argument lists never contain a registered secret | SEC-1, SEC-5, SEC-6, SEC-7, SEC-9, SEC-10, SEC-13, SEC-14, HLTH-32, HLTH-34, UI-4 |
| Loopback and auth | Nothing binds beyond loopback; every request is authenticated | PLAT-10, PLAT-71, SEC-11, SEC-12, UI-2, UI-3 |
| Async discipline | The event loop never blocks | PLAT-75, SRCH-1, ruff ASYNC rules |
| Bounded output | No result exceeds the budget | PLAT-31, PLAT-63 |
| Untrusted content | Fetched text is always enveloped | PLAT-33, SEC-22 |
| Adapter isolation | Adapters do no I/O of their own | SRC-7, conformance |
| No silent deletion | Nothing is deleted without an owner decision; MCP discards are announced; shared files survive | CACHE-33, CACHE-34, CACHE-36, CACHE-48, SEC-20 |
| Docs follow code | Generated inventory and test plan are current | SRC-13, `tools/gen_test_plan.py` in CI |

**Milestone exit gates** (TEST-PLAN-v3 section 8; owner checks keep their TEST-PLAN-v3 `OC-nn` numbers):

| Milestone | Gate |
|---|---|
| M0 | Every M0 criterion assigned to an M0 work unit (TEST-PLAN-v3 Appendix A) passes; full `tools/ci.sh` green (lint, strict mypy, coverage 85% on `src/`, build, `--help`); owner checks OC-01 and OC-02. |
| M1 | All M1 criteria pass; all 38 sources registered and passing conformance; OC-03, OC-08 (once a remote exists), OC-11, OC-12. |
| M2 | All M2 criteria pass, including the hostile PDF corpus; OC-04, OC-10 and OC-13. |
| M3 | All M3 criteria pass; OC-05 and OC-09. |
| M4 | All M4 criteria pass; OC-06 then OC-07. |

The M1 source count conflicts with the PRD (section 20).

## 18. Risks and mitigations

> **Owner:** A · **Persona:** `architect`; the owner ranks them at Gate 2

Likelihood and impact are not rated in the source documents; the owner rates them at Gate 2.

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Upstream APIs change faster than one person can follow (PRD-v4 section 12). | not rated | not rated | Probes check response shape, not just status; recorded fixtures make breakage visible in tests; each source can be disabled with a flag (sections 4, 7, 9). |
| Metered sources (OpenAlex budget, web-search providers) run out mid-task or cost more than expected (PRD-v4 section 12). | not rated | not rated | Budget tracking with `quota_low`, `rate_limited` and `budget_exhausted` states; federation skips exhausted sources and says so; web-search sources are off until configured, capped per day, and never in the default fan-out (sections 4, 5, 9). |
| Keychain locked or unreadable, for example right after login (PRD-v4 section 12). | not rated | not rated | Reads go through `/usr/bin/security` with a timeout; a locked Keychain is one `keychain_locked` state and one notification, not a notice per key; `doctor` gives the fix (sections 7, 9). |
| Drive sync folder unavailable, blocked by macOS privacy controls, or not uploading (PRD-v4 section 12). | not rated | not rated | Install performs the first archive write in the foreground so the privacy prompt appears; `doctor` checks access; local fallback with a warning and reconcile; nothing leaves the cache until the archive copy is verified; upload state is checked and a stalled upload is reported (sections 6, 12). |
| PyMuPDF crashes on hostile PDFs (PRD-v4 section 12). | not rated | not rated | Parsing in a worker process with CPU, memory, page and time limits (sections 3, 9). |
| Scope creep toward a library manager (PRD-v4 section 12). | not rated | not rated | Non-goals in PRD section 3.2; collections stay minimal. |
| macOS or cleaning tools purge `~/Library/Caches` (HLD-v3 section 10). | not rated | not rated | Nothing the lifecycle depends on lives there; only the re-downloadable model cache does; both databases live in Application Support and are backed up nightly (section 10). |
| Five-source search p95 depends on upstream latency the project does not control (TEST-PLAN-v3 section 9). | not rated | not rated | If OC-12 fails, the deadline or default source set is tuned rather than the gate removed (sections 5, 13). |

## 19. Traceability

> **Owner:** A · **Persona:** `architect`

**Components.** The SPEC-v2 split across LLDs is this document's assumption until the LLDs are reviewed (section 20).

| Component | Prefix | PRD | LLD | SPEC sections | Carries SPEC-v2 sections |
| --- | --- | --- | --- | --- | --- |
| Platform | PLAT | [PRD-platform-v3](../prd/components/PRD-platform-v3.md) | [LLD-platform-v1](../lld/LLD-platform-v1.md) | 2, 3, 5, 10, 12, 15 | 1, 2, 3.3 to 3.7, 7.4, 9.8, 12.1, 12.2 |
| Sources | SRC | [PRD-sources-v4](../prd/components/PRD-sources-v4.md) | [LLD-sources-v1](../lld/LLD-sources-v1.md) | 4, 5, 9 | 4, 5.1 to 5.5 |
| Search and identity | SRCH | [PRD-search-v2](../prd/components/PRD-search-v2.md) | [LLD-search-v1](../lld/LLD-search-v1.md) | 5, 11.1 | 6, 7.1 to 7.3 |
| Retrieval and cache | CACHE | [PRD-cache-v3](../prd/components/PRD-cache-v3.md) | [LLD-cache-v1](../lld/LLD-cache-v1.md) | 6, 10, 11.2, 11.3 | 8, 9.1 to 9.5, 9.7 |
| Health and credentials | HLTH | [PRD-health-v3](../prd/components/PRD-health-v3.md) | [LLD-health-v1](../lld/LLD-health-v1.md) | 7, 10, 11.4 | 10 |
| Local UI | UI | [PRD-ui-v3](../prd/components/PRD-ui-v3.md) | [LLD-ui-v1](../lld/LLD-ui-v1.md) | 8 | 11 |
| Migration and cutover | MIG | [PRD-migration-v4](../prd/components/PRD-migration-v4.md) | [LLD-migration-v1](../lld/LLD-migration-v1.md) | 12, 14 | 9.6 |
| Security | SEC | [PRD-security-v1](../prd/components/PRD-security-v1.md) | [LLD-security-v1](../lld/LLD-security-v1.md) | 2, 9 | 3.1, 3.1.1, 3.2 |

**Component requirements** (groups follow the subsections of the previous component PRDs).

| Component requirements | Area | SPEC section |
| --- | --- | --- |
| PLAT-FR-1 to PLAT-FR-6 | Process and transport | 2, 3, 12 |
| PLAT-FR-8 to PLAT-FR-16 | Configuration and secrets | 9, 10 |
| PLAT-FR-20 to PLAT-FR-27 | Local access and untrusted content | 2, 9 |
| PLAT-FR-30 to PLAT-FR-33 | Results, errors and HTTP | 3, 5 |
| PLAT-FR-40 to PLAT-FR-42 | Logging | 9, 12 |
| PLAT-FR-50 to PLAT-FR-58 | Packaging, CI and upgrades | 12, 15 |
| SRC-FR-1 to SRC-FR-18 | Contract, registry, fixtures, catalog, site sets | 4 |
| SRC-FR-19 to SRC-FR-23 | The `web` group, caps, fallback, `site_set`, Google sign-in | 4, 5, 9 |
| SRCH-FR-1 to SRCH-FR-9 | Federated search | 5, 11.1 |
| SRCH-FR-10 to SRCH-FR-14 | Identity and dedupe | 5 |
| SRCH-FR-15 to SRCH-FR-17 | Work lookup | 5 |
| SRCH-FR-20 to SRCH-FR-23 | Citations, authors and export | 5 |
| SRCH-FR-25, SRCH-FR-26 | Integrity | 5 |
| CACHE-FR-1 to CACHE-FR-7 | Fetch | 6, 9, 11.2 |
| CACHE-FR-10 to CACHE-FR-14 | Extraction and chunking | 3, 6, 9 |
| CACHE-FR-15 to CACHE-FR-18 | Reading and local search | 6, 11.2 |
| CACHE-FR-20 to CACHE-FR-24 | Embeddings | 6, 10 |
| CACHE-FR-30 to CACHE-FR-38 | Lifecycle and owner review | 6, 11.3 |
| CACHE-FR-45 to CACHE-FR-50 | Archive to Google Drive | 6, 10, 12 |
| CACHE-FR-51, CACHE-FR-52, CACHE-FR-55 to CACHE-FR-59 | Collections, crawl jobs, disk | 10, 14 |
| HLTH-FR-1 to HLTH-FR-5 | Telemetry and probes | 7 |
| HLTH-FR-10 to HLTH-FR-12 | Source states | 5, 7 |
| HLTH-FR-20 to HLTH-FR-25 | Credential states | 7, 11.4 |
| HLTH-FR-30 to HLTH-FR-35 | Notifications | 7, 11.3, 11.4 |
| HLTH-FR-40 to HLTH-FR-43 | Doctor and agent access | 7, 12 |
| UI-FR-1 to UI-FR-7 | General | 8, 9 |
| UI-FR-10 to UI-FR-19 | Pages | 8 |
| MIG-FR-1 to MIG-FR-6 | Credentials | 12, 14 |
| MIG-FR-10 to MIG-FR-15 | Optional corpus import | 12, 14 |
| MIG-FR-20 to MIG-FR-24 | Client cutover and v1 retirement | 12, 14 |
| SEC-1 to SEC-23 (criteria) | Security suite | 9, 17 |

**Parent requirements.**

| Parent requirement | Component requirements | SPEC section |
| --- | --- | --- |
| OUT-1 Breadth | SRC-FR-1 to SRC-FR-23 | 4 |
| OUT-2 One search | SRCH-FR-1 to SRCH-FR-9 | 5, 11.1, 13 |
| OUT-3 Cheap to maintain | SRC-FR-16 | 3, 4, 13 |
| OUT-4 Monitored | HLTH-FR-1 to HLTH-FR-12, HLTH-FR-40 to HLTH-FR-43 | 7, 12 |
| OUT-5 Credential care | HLTH-FR-20 to HLTH-FR-35 | 7, 11.4 |
| OUT-6 Cache, not library | CACHE-FR-30 to CACHE-FR-50 | 6, 11.3 |
| OUT-7 Safe by default | PLAT-FR-10 to PLAT-FR-27; SEC criteria | 9 |
| OUT-8 Visible | UI-FR-1 to UI-FR-19 | 8 |
| NFR-1 Single process | PLAT-FR-1, PLAT-FR-2 | 2, 3 |
| NFR-2 Async | PLAT-FR-5 | 3 |
| NFR-3 No secrets at rest outside the Keychain | PLAT-FR-10 | 9, 10 |
| NFR-4 No secret in any output | PLAT-FR-11, PLAT-FR-13, PLAT-FR-14 | 9, 17 |
| NFR-5 Bounded output | PLAT-FR-30 to PLAT-FR-33 | 5 |
| NFR-6 Untrusted content is labeled | PLAT-FR-25 | 2, 9 |
| NFR-7 Loopback only | PLAT-FR-3 | 2, 9 |
| NFR-8 Respect upstream terms | SRC-FR-11 | 3, 13 |
| NFR-9 Testable offline | SRC-FR-8 | 4, 17 |
| NFR-10 Docs follow code | SRC-FR-13 | 13, 17 |
| NFR-11 Prose style | | 15 |

## 20. Open questions

> **Owner:** A · **Persona:** `architect`

- [ ] Q: How many sources does v2 register? PRD-v4 (OUT-1, section 7, and the 45-row catalog in PRD-sources-v3) says 45; the HLD-v3 diagram (section 2) says "about 42 adapters"; SPEC-v2 section 12.4 says "39 adapter modules (42 sources)" for M1; the TEST-PLAN-v3 M1 gate (section 17) says 38.
- [ ] Q: Seven or six fixtures per adapter? HLD-v3 section 4, ADR 0006 and FR-SRC-08 (SRC-FR-8) say seven; PRD-sources-v3 section 4 says "at least the six conformance fixtures (FR-SRC-08)".
- [ ] Q: The section 13 Cost row says "no paid search providers", which contradicts the optional, metered `web` group (ADR 0012; sections 4, 5 and 9). Should the row read as section 9's paid web-search control?
- [ ] Q: The old security tests (AT-SEC) verified platform requirements (FR-PLAT-10 to FR-PLAT-27 and others). Which PLAT-FR requirements move into PRD-security-v1, and with which SEC-FR IDs? Section 19 lists SEC by criteria only until that is known.
- [ ] Q: LLD section citations (for example "LLD-cache-v1 §3") assume the LLD template's numbering and the SPEC-v2 split in section 19 (notably SPEC-v2 3.1 to 3.2 in security, 3.3 to 3.4 and 9.8 in platform). Confirm against the LLDs written in parallel.
- [ ] Q: ADRs 0001 to 0010 say "Proposed (accepted when the owner approves PRD v1)". PRD v1 was superseded long ago; are they accepted now? ADR 0007's title still says "30-day cache", amended by ADR 0011.
- [ ] Q: SPEC-v2 section 0 (conformance, precedence and change control, and the 0.6 clarifications from the first M0 attempt, which are stated as requirements) has no place in the SPEC template and was not carried here. Which LLDs take the 0.6 rows?
- [ ] Q: Section 15 is an H section; its content is carried verbatim from SPEC-v2 section 1 and AGENTS.md. Does the owner confirm it as the approved stack?
- [ ] Q: Section 17 belongs to the `test-architect` persona and was carried over by the `architect`; it needs the `test-architect`'s review before Gate 2.
- [ ] Q: Section 18 risks carry no likelihood or impact rating in the sources; the owner rates and ranks them.
- [ ] Q: Requirement and goal IDs here (OUT-n, NFR-n, <PREFIX>-FR-n) are mechanical renames of PRD-v4 and the previous component PRDs; confirm they match PRD-v5 and the new component PRDs once those are written.

### Gate 2: Design approved

| Approver | Date | ADRs chosen | Notes |
| --- | --- | --- | --- |
| | | | |
