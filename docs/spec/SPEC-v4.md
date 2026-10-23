---
title: "Research MCP v2 system design"
type: spec
version: 4
status: approved
approved_by: "Kenny Hill (Engineering)"
approved: 2026-10-22
owner: "Kenny Hill"
parent: docs/prd/PRD-v7.md
artifact_type: high-level-design
scope_level: L3
scope_name: "research-mcp"
supersedes: docs/spec/SPEC-v3.md
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# SPEC: Research MCP v2 system design (v4)

- **Requirements:** [PRD-v7](../prd/PRD-v7.md) and its component PRDs ([platform](../prd/components/PRD-platform-v4.md), [sources](../prd/components/PRD-sources-v5.md), [search](../prd/components/PRD-search-v3.md), [cache](../prd/components/PRD-cache-v4.md), [health](../prd/components/PRD-health-v4.md), [ui](../prd/components/PRD-ui-v4.md), [migration](../prd/components/PRD-migration-v5.md), [security](../prd/components/PRD-security-v2.md)), all approved at Gate 1 on 2026-10-22.
- **Detail:** the component LLDs in [docs/lld/](../lld/): `LLD-platform-v1`, `LLD-sources-v1`, `LLD-search-v1`, `LLD-cache-v1`, `LLD-health-v1`, `LLD-ui-v1`, `LLD-migration-v1`, `LLD-security-v1`. Section 19 says which LLD carries which part of SPEC-v2.
- **Tests:** [test plan v3](../test/test-plan-v3.md).
- **Decisions:** [ADRs 0001 to 0013](../adr/) (section 16).

## Provenance and changes

**Changes in v4** (Gate 2 draft, 2026-10-22). This version follows the approved [PRD-v7](../prd/PRD-v7.md), its component PRDs and [test plan v3](../test/test-plan-v3.md); where SPEC-v3 disagreed with an approved PRD, the PRD wins. It records the owner's Gate 2 answers: the section 13 Cost row, section 15 confirmed as written, and the section 18 risks rated and ranked (owner decision, 2026-10-22). It applies the Gate 1 decisions: 45 sources and seven fixtures per adapter (sections 2, 4, 17); MCP clients only through the stdio shim (section 2); `cite` in M1 (section 14); ADRs 0001 to 0013 accepted (section 16); the source states `budget_exhausted` and `not_needed` (sections 5, 11.1); token rotation from the CLI only, UI polling, job retry and read-only site sets (sections 8, 12); the placeholder contact address and the generated inventory (section 4); backup and log retention (sections 10, 12); the scrub backup exception (sections 9, 10, 17); and the rollout halt conditions (section 12). It also records this round's decisions (owner decision, 2026-10-22): an exception to INV-4 and SEC-INV-7 for owner-run migration commands, scoped per command (`secrets import` and `scrub-client-configs` read only the MCP client configs; only the legacy import reads the v1 folder, under INV-10 and MIG-INV-1); the scrub backups live outside v2's config, Application Support and log folders and never in a synced folder (section 9); the accepted residual risk that same-user processes sit inside trust boundary 2 (section 9); OC-14 in the M1 gate and the "No secret at rest" cross-cutting row (section 17); and test plan v3. LLD citations were checked against the LLD headings and corrected. Section 19 now maps every requirement, criterion and invariant to a SPEC section and an LLD, and says where the SPEC-v2 0.6 clarification rows live. History note: superseded requirement IDs were replaced by their successors (PLAT-FR-16 by PLAT-FR-59; SRC-FR-11, SRC-FR-13 and SRC-FR-16 by SRC-FR-24, SRC-FR-25 and SRC-FR-26; SRCH-FR-4 and SRCH-FR-10 by SRCH-FR-27 and SRCH-FR-28; UI-FR-5 and UI-FR-19 by UI-FR-20 and UI-FR-21; MIG-FR-23 by MIG-FR-25), MIG-FR-26 is new, and the source state `skipped_budget` of SPEC-v3 11.1 is now `budget_exhausted` (SRCH-FR-27).

**Changes in v3.** Version 3 moved the high level design onto the spec-driven development framework ([ADR 0013](../adr/0013-adopt-spec-driven-development.md); the current standard is [v3](../standards/spec-driven-development-v3.md)). Sections 1 to 14 carry over [HLD-v3](../../docs-archive/design/HLD-v3.md) with the same numbers and titles, so documents that cite "HLD section N" still match; only references were updated (SPEC v1 and v2 sections now point to the LLD that holds them, requirement and criterion IDs use the SDD scheme). The architecture parts of [SPEC-v2](../../docs-archive/spec/SPEC-v2.md) (conventions in its section 1) moved to section 15; its detailed contracts moved to the LLDs. Sections 15 to 20 follow the [SPEC template](../templates/SPEC-template.md).

ID scheme used here: `FR-<AREA>-nn` became `<PREFIX>-FR-n`, `NFR-nn` became `NFR-n`, goals `Gn` became `OUT-n`, and acceptance tests `AT-<AREA>-nn` became criteria `<PREFIX>-n` (`AT-SEC-nn` became `SEC-n`). Leading zeros are dropped.

Carried from HLD-v3, changes from its v2: owner decisions of 2026-10-19, second round ([ADR 0012](../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md)): the design is domain-neutral (topic coverage is configuration); every endpoint v1 calls is kept; web search returns as an optional, capped source group (`web`: Vertex AI Search, Brave, SerpAPI, Programmable Search) that runs only on request, in fallback order by default (sections 4, 5 and 9). M0 is unchanged.

Carried from HLD-v3, earlier changes (v2): owner decisions of 2026-10-19: cache retention is **120 days** instead of 30, and **archiving keeps a paper searchable**: only the PDF moves to Google Drive; extracted text, chunks, full-text entries and embeddings stay in `cache.db`, and a rebuild job can re-import the archive from Drive. See [ADR 0011](../adr/0011-archive-keeps-text-searchable-120-day-retention.md).

## 1. Scope

> **Owner:** C · **Persona:** `architect`

This document describes the shape of v2: the processes, the main components and how they talk, the data each owns, the security boundaries, and the key flows. Module names, schemas, signatures and interfaces are in the component LLDs (`docs/lld/LLD-<component>-v1.md`); section 19 maps each component to its LLD. The M0 work breakdown is in the [M0 plan](../build/M0-plan-v1.md) (section 14).

## 2. System context

> **Owner:** C · **Persona:** `architect`

```
 +-------------------+   +-------------------+   +-------------------+
 | Claude Code       |   | Claude desktop    |   | OpenClaw agents,  |
 | (MCP client)      |   | (MCP client)      |   | Codex (MCP)       |
 +---------+---------+   +---------+---------+   +---------+---------+
           | stdio                 | stdio                 | stdio
           v                       v                       v
 +---------------------------------------------------------------------+
 | research-mcp stdio  (thin shim, one per client; no state)            |
 | the daemon token comes from the Keychain; clients never hold it      |
 +----------------------------------+----------------------------------+
                                    | streamable HTTP, 127.0.0.1, bearer token
                                    v
 +---------------------------------------------------------------------+
 | research-mcpd  (one daemon per Mac, launchd KeepAlive)               |
 |  MCP endpoint /mcp  |  UI /ui  |  /healthz /readyz /api/status       |
 |  services: federation, works, cache, health, notify, jobs, scheduler |
 |  source registry (45 sources)  |  shared async HTTP client           |
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

MCP clients connect only through the stdio shim. Loopback streamable HTTP is the transport between the shim and the daemon, and the UI's transport: the owner's browser reaches `/ui` on `127.0.0.1` with a UI session, and the CLI reaches `/api` with the bearer token (for example to mint a UI login token). No MCP client is offered direct loopback HTTP, and no client holds the daemon token (PRD-v7 1.2, NFR-1; PLAT-FR-2; SEC-INV-10).

Trust boundaries:

1. **Upstream content is untrusted.** Everything that comes from an API or a downloaded file is data; it is labeled untrusted when returned to a model.
2. **Local callers are authenticated.** Only the shim (with the bearer token it reads from the Keychain) and the UI (with a session) can call the daemon; the CLI uses the same bearer token.
3. **Secrets never leave the HTTP layer** except to the origin they belong to.

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

**Detail:** the MCP transport and composition root in [LLD-platform-v1](../lld/LLD-platform-v1.md) §2.3 (from SPEC-v2 section 7.4); conventions and package layout in §5.1 (from SPEC-v2 section 1); layers in §5.2 (from HLD-v3 section 3); workers, jobs and the scheduler in §5.5 (from SPEC-v2 section 3.6); the stdio shim in §5.7. Requirements: PLAT-FR-1 to PLAT-FR-6; NFR-1, NFR-2.

## 4. Sources

> **Owner:** C · **Persona:** `architect`

- A **`SourceSpec`** declares each source: capabilities, identifier schemes, auth (including its Keychain names and signup URL), rate policy, timeouts, page size, extras, probe, shutdown date, default enabled.
- An **adapter** implements `search`, `get`, `fulltext_candidates`, `citations` and `probe` for the capabilities it declares, returning normalized `WorkRecord`s with provenance.
- The **registry** discovers adapters, creates configured instances (four DSpace repositories, docs sites, Vertex AI Search engines), applies enable and disable settings, and answers "which sources can do X for group Y right now", combining configuration with live health. v2 registers 45 sources at the M1 exit (PRD-v7 OUT-1; PRD-sources-v5 1.3).
- **Upstream MCP servers** (AWS Knowledge, Microsoft Learn) are adapters that use an MCP client instead of HTTP JSON.
- **Site sets** are named domain lists in configuration (v1's docs-domain list ships as `v1_docs`). Topic coverage, in any subject area, is added by configuring docs sites, site sets and search engines, not by code. Site sets are edited in the config file or with `research-mcp config set`; the UI shows them read-only (SRC-FR-18; UI-FR-21).
- **Web search** is the `web` group: four optional, metered sources, each off until configured and capped per day. It is never in the default fan-out.
- **Contact address.** Sources that ask for a contact email get the configured owner contact. A placeholder `contact.email` (example.com, example.org, .test, .invalid) is a settings validation error with a clear message, so the daemon does not start until it is fixed; with no address set, only the `needs_contact` sources are `unconfigured` and the daemon starts (SRC-FR-24; PLAT-11).
- **Inventory and new sources.** The source inventory is generated from the registry by `tools/gen_inventory.py`, and its `--check` flag gates CI (SRC-FR-25). A new source is one adapter module, one fixtures folder and its tests; its Keychain name lives in its `SourceSpec` and the generated inventory, so the new-source checklist has no "edit the SPEC" step (SRC-FR-26).
- **Testing:** every adapter has seven recorded fixtures and runs through one conformance suite (SRC-FR-8); an opt-in live check refreshes fixtures.

**Detail:** in [LLD-sources-v1](../lld/LLD-sources-v1.md): the source contract and policy types in §2.1 and §2.2 (from SPEC-v2 section 4); shared models in §3.1; settings keys in §3.2; default data and site sets in §3.3; fixtures on disk in §3.4; the registry in §5.2 (SPEC-v2 5.1); conformance in §5.3 (SPEC-v2 5.2); the live check in §5.4 (SPEC-v2 5.3); the new-source checklist in §5.5 (SPEC-v2 5.4, whose step 5 SRC-FR-26 supersedes); upstream MCP adapters in §5.6; web sources, site sets in queries and the `web` group federation in §5.7 to §5.9 (SPEC-v2 5.5); the inventory in §5.10. The contact-address validation is in [LLD-platform-v1](../lld/LLD-platform-v1.md) §7.1. Requirements: SRC-FR-1 to SRC-FR-10, SRC-FR-12, SRC-FR-14, SRC-FR-15, SRC-FR-17 to SRC-FR-26 ([PRD-sources-v5](../prd/components/PRD-sources-v5.md)); OUT-1, OUT-3.

## 5. Federation and identity

> **Owner:** C · **Persona:** `architect`

```
 search(query, sources, filters, limit, cursor)
   -> registry.select(groups, filters, health)          # auto selection; skips disabled, unconfigured, down, rate_limited, budget_exhausted
   -> fan out: one task per source, per-source timeout, overall deadline
   -> per source: SearchPage(records, cursor) or SourceStatus(error)
   -> identity.resolve(records)                          # normalize ids, union-find on shared ids
   -> merge(records -> works), fuzzy merge flagged
   -> rank: reciprocal rank fusion + found-in-more-sources boost
   -> budget: trim to response budget, build combined cursor
   -> envelope {data: works, source_status: [...], next_cursor, truncated}
```

- **Identity:** `core.ids` normalizes identifiers (pure functions), including GitHub identifiers and URL trailing slashes (SRCH-FR-28); `services/works.py` groups records by any shared identifier; if no identifier is shared, fall back to normalized title, year and first-author surname, flagged `fuzzy`.
- **Source status:** every selected source gets one `source_status` entry, and a failing source never fails the search (SRCH-FR-27; SRCH-INV-1). A source whose budget or daily cap is spent reports `budget_exhausted`; a `web` source the fallback chain did not need reports `not_needed` (SRCH-FR-27).
- **`get_work`** resolves an identifier against every source that understands its scheme, merges the records, and adds open-access locations, integrity status and cache state.
- **The `web` group** runs in `fallback` order by default: the configured web sources are tried one at a time (Vertex, Brave, SerpAPI, Programmable Search) until one answers, so a request spends at most one paid query per page. With `strategy = "all"` they fan out like any other group. A `site_set` restricts the domains.
- **Citations, authors, cite and integrity** are services over the same registry and identity layer; they ship in M1 (PRD-v7 2.9).

**Detail:** in [LLD-search-v1](../lld/LLD-search-v1.md): the tool catalog in §2.1 (from SPEC-v2 section 7.2); resources and prompts in §2.3 (SPEC-v2 7.3); identity in §5.2 and grouping in §5.3 (SPEC-v2 6); federation in §5.4 (SPEC-v2 7.1); citations, authors, cite and integrity in §5.5. The `web` group federation rules are in [LLD-sources-v1](../lld/LLD-sources-v1.md) §5.9; the envelope and budget in [LLD-platform-v1](../lld/LLD-platform-v1.md) §2.1 and §5.6 (SPEC-v2 3.7). Requirements: SRCH-FR-1 to SRCH-FR-3, SRCH-FR-5 to SRCH-FR-9, SRCH-FR-11 to SRCH-FR-17, SRCH-FR-20 to SRCH-FR-23, SRCH-FR-25 to SRCH-FR-28 ([PRD-search-v3](../prd/components/PRD-search-v3.md)), SRC-FR-21, SRC-FR-22, HLTH-FR-12; OUT-2; NFR-5.

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

- **Archive** copies the file and a sidecar metadata JSON to the Drive sync folder, verifies the copy, then removes only the cached file. The document's text, chunks, full-text entries and embeddings stay in `cache.db`, so archived papers remain searchable and readable. If the folder is unavailable, it uses a local fallback and reconciles later. A rebuild job can re-import the archive from the Drive folder and its sidecars, and never modifies the Drive files (CACHE-INV-6).
- **Metadata outlives files.** A discarded work keeps its citation snapshot and fetch recipe; an archived work keeps those plus its searchable text.
- **Local search** is hybrid: FTS5 BM25 plus exact vector similarity over embeddings stored in `cache.db`, fused by reciprocal rank ([ADR 0008](../adr/0008-sqlite-stores-and-vectors.md)).
- **Collections** export through `cite` (CACHE-63).

**Detail:** in [LLD-cache-v1](../lld/LLD-cache-v1.md): contracts in §2; the `cache.db` schema in §3 (from SPEC-v2 section 8.1); extraction and chunking, local search, state transitions, the review batch, archive, disk and integrity, collections, the archive rebuild and backups in §5 (SPEC-v2 sections 8.2, 8.3, 9.1 to 9.5, 9.7 and 9.8). The downloader is in [LLD-platform-v1](../lld/LLD-platform-v1.md) §5.4 (SPEC-v2 3.4) and the workers in §5.5 (SPEC-v2 3.6); the legacy import into the cache is in [LLD-migration-v1](../lld/LLD-migration-v1.md) §5.1 (SPEC-v2 9.6). Requirements: CACHE-FR-1 to CACHE-FR-7, CACHE-FR-10 to CACHE-FR-18, CACHE-FR-20 to CACHE-FR-24, CACHE-FR-30 to CACHE-FR-38, CACHE-FR-45 to CACHE-FR-52, CACHE-FR-55 to CACHE-FR-59 ([PRD-cache-v4](../prd/components/PRD-cache-v4.md)); OUT-6.

## 7. Health, credentials and notifications

> **Owner:** C · **Persona:** `architect`

```
 HTTP client --telemetry--> state.db.calls --rollup--> source_health
 scheduler --probes--> adapters.probe() ----------------^
 secrets --metadata--> state.db.credentials <-- passive headers (GitHub expiry, rate limits)
 health.evaluate() -> source and credential states -> diff -> notify (macOS, OpenClaw webhook, UI banner)
 doctor (launchd: liveness every 15 min, full daily) -> same checks without the daemon -> notify on change
```

- **States** follow [PRD-health-v4](../prd/components/PRD-health-v4.md) section 2.4: source states HLTH-FR-10 to HLTH-FR-12 and credential states HLTH-FR-20 to HLTH-FR-25. Credential rows hold metadata only, never values (HLTH-INV-1).
- **Notifications** fire on state changes and roll unresolved items into a daily digest, with quiet hours.
- **Federation** consults health before selecting sources and skips `down`, `rate_limited` and `budget_exhausted` sources (HLTH-FR-12).

**Detail:** in [LLD-health-v1](../lld/LLD-health-v1.md): the HTTP endpoints, MCP surface, CLI and webhook contracts in §2 (from SPEC-v2 sections 10.4 and 10.5); the `state.db` schema in §3 (SPEC-v2 10.1); probes, state evaluation, credential validation, notifications and `doctor` in §5 (SPEC-v2 10.2 to 10.5). Requirements: HLTH-FR-1 to HLTH-FR-5, HLTH-FR-10 to HLTH-FR-12, HLTH-FR-20 to HLTH-FR-25, HLTH-FR-30 to HLTH-FR-35, HLTH-FR-40 to HLTH-FR-43; OUT-4, OUT-5.

## 8. Local UI

> **Owner:** C · **Persona:** `architect`

- **Stack:** Starlette routes and Jinja2 templates in the daemon, with a vendored htmx file for partial refresh and confirmation dialogs ([ADR 0010](../adr/0010-localhost-ui-stack.md)).
- **Data access:** pages read the same services the MCP tools use, so there is no second API.
- **Sessions:** a session starts from a one-time token URL. All writes need CSRF tokens and confirmation.
- **Refresh:** pages refresh live data with `hx-get` polling every 10 seconds only (UI-FR-20).
- **Pages:** source board, credentials, quota, jobs, cache, review, archive, maintenance, events, settings. A job retry resubmits the job through `JobService.submit` with the same parameters (UI-FR-13). The Settings page shows the named site sets read-only (UI-FR-21).
- **No token rotation in the UI:** the daemon token rotates only from the CLI with `research-mcp secrets rotate-token` (PLAT-FR-59).

**Detail:** in [LLD-ui-v1](../lld/LLD-ui-v1.md) (from SPEC-v2 section 11): routes, login and session, request checks and partial refresh in §2.1 to §2.4; enforcement points in §4; files, services and pages in §5.1 to §5.3. Platform-owned parts (the daemon token and loopback checks) are in [LLD-platform-v1](../lld/LLD-platform-v1.md) §4.5. Requirements: UI-FR-1 to UI-FR-4, UI-FR-6, UI-FR-7, UI-FR-10 to UI-FR-18, UI-FR-20, UI-FR-21 ([PRD-ui-v4](../prd/components/PRD-ui-v4.md)); OUT-8.

## 9. Security architecture

> **Owner:** C · **Persona:** `security-reviewer`

| Threat | Control |
|---|---|
| Prompt-injected model tries to read local files | No SQL tool; no caller-chosen paths; files only under the cache root; DuckDB (if used internally) locked down ([ADR 0009](../adr/0009-no-sql-untrusted-content.md)). Approved exception, scoped per owner-run migration command: `secrets import` (MIG-FR-1) and `scrub-client-configs` (MIG-FR-5) read only the MCP client configs; only the legacy import (MIG-FR-10) reads the v1 folder (`~/arxiv-papers`, the v1 database), and only through that job (INV-10; MIG-INV-1). MCP tools and anything an agent can trigger stay bound by INV-4 and SEC-INV-7. It is recorded in [test plan v3](../test/test-plan-v3.md) section 4, not a PRD change (owner decision, 2026-10-22). |
| Prompt-injected model tries to delete data | No hard delete in MCP; the only MCP discard is a review decision inside an open batch, recorded as an agent decision, sent to a 7-day trash and announced to the owner at once with an undo link; the owner is notified again 24 hours before any purge; annotations mark state-changing tools. |
| Secret leaks into chat or logs | Keychain (the Google sign-in and the scrub backups excepted, see below); `Secret` type; origin-scoped attachment; header placement; one redaction filter on logs, errors, UI and notifications; errors carry codes, not exception text. |
| Paid web-search spend runs away | Web sources off until configured, never in the default fan-out, fallback order (one paid query per page), daily caps that switch a source to `budget_exhausted`. |
| Google sign-in token misuse | `gcloud` owns the sign-in; v2 holds only a short-lived access token in memory and attaches it only to `discoveryengine.googleapis.com`. |
| Plaintext v1 keys in scrub backups | An approved exception to INV-6, NFR-3 and SEC-INV-3 (not SEC-INV-6) until v1 is retired: `scrub-client-configs` writes each backup owner-only (mode 0600); the backups serve only to restore the v1 entries on rollback; retiring v1 deletes them (PRD-v7 1.5; MIG-FR-25, MIG-FR-26; MIG-25, MIG-26). The backups live outside v2's config, Application Support and log folders, so SEC-24 and the NFR-3 scan apply without exception, and never inside a synced folder (Google Drive, iCloud), so the keys never leave the Mac; the migration LLD sets the exact path at Gate 3 (owner decision, 2026-10-22). |
| SSRF and hostile downloads | One downloader: https, per-hop host policy, public IPs only with the connection pinned to the checked IP (no second DNS lookup), byte cap, magic bytes, atomic write. |
| Hostile PDFs | Parsing in a separate subprocess per document with a CPU limit, an RSS watchdog, a wall-clock timeout and a page cap; a crash affects only that document. |
| Other local processes call the daemon | Loopback only, bearer token, Host and Origin checks; UI session cookie plus CSRF. MCP clients reach the daemon only through the stdio shim, which reads the token from the Keychain; no client holds it (SEC-INV-10; SEC-26). Accepted residual risk: any process running as the owner can launch `research-mcp stdio` or read the Keychain item without a prompt, so same-user code sits inside trust boundary 2; SEC-INV-10 keeps the token out of client configs, not away from same-user processes. This is accepted on one personal Mac (owner decision, 2026-10-22). |
| Daemon token exposed | The token rotates only from the CLI with `research-mcp secrets rotate-token`, never from the UI; the new value is written through `security -i` on stdin (PLAT-FR-59; SEC-13). |
| Upstream drift returns wrong data | Probes check response shape; fixtures pinned in tests; per-source disable. |
| Supply chain | Lock file, weekly dependency audit, SHA-pinned CI actions, secret scan. |

Two exceptions keep secrets outside the Keychain. The owner's Google sign-in is a standing exception written into INV-6 and SEC-INV-3: `gcloud` stores it and v2 never copies it (ADR 0012; SEC-INV-11). The scrub backups hold many v1 keys and are a time-boxed exception outside that text, lasting until v1 is retired (PRD-v7 1.5; MIG-FR-26). INV-6 and SEC-INV-3 themselves are unchanged.

The Security component owns the shared invariants SEC-INV-1 to SEC-INV-11 and defines no `SEC-FR` IDs: the controls stay requirements of the platform, cache, health, sources (SRC-FR-23) and migration (MIG-FR-26) components, and the SEC criteria cite them (PRD-security-v2 1.7, 2.4).

**Detail:** trust boundaries, the threat model, enforcement points and invariant coverage in [LLD-security-v1](../lld/LLD-security-v1.md) §4.1 to §4.4 (from HLD-v3 sections 2 and 9). Those sections predate Gate 1: LLD-security-v2 must add the scrub backup row and the shim sentence to §4.2, an enforcement point for MIG-25 and MIG-26 to §4.3, and SEC-24 to SEC-27 to the §4.4 coverage in place of its gaps. Secrets, the Google sign-in and redaction are owned by [LLD-platform-v1](../lld/LLD-platform-v1.md) §4.1 to §4.3 (SPEC-v2 3.1, 3.1.1 and 3.2) and quoted in LLD-security-v1 §5; credential scoping and the HTTP client in LLD-platform-v1 §4.4 and §5.3 (SPEC-v2 3.3); loopback, the daemon token and endpoints in §4.5; local files and destructive actions in §4.6; the downloader in §5.4 (SPEC-v2 3.4); the scrub backups in [LLD-migration-v1](../lld/LLD-migration-v1.md) §5.3. Requirements: [PRD-security-v2](../prd/components/PRD-security-v2.md), criteria SEC-1 to SEC-14 and SEC-20 to SEC-27, invariants SEC-INV-1 to SEC-INV-11; MIG-FR-26; OUT-7; NFR-3, NFR-4, NFR-6, NFR-7.

## 10. Data stores

> **Owner:** C · **Persona:** `architect`

| Store | Location | Owns | Backed up |
|---|---|---|---|
| `state.db` (SQLite, WAL) | `~/Library/Application Support/research-mcp/` | Credential metadata, source health, call telemetry and rollups, searches, jobs, schedule runs, notifications, review batches and a copy of review events | Nightly, the last 7 kept |
| `cache.db` (SQLite, WAL, FTS5, vector BLOBs) | `~/Library/Application Support/research-mcp/cache/` | Works, identifiers, source records, documents and lifecycle (including pins, decisions and archive paths), files, extractions, chunks, FTS, embeddings, collections, outbox | Nightly, the last 7 kept |
| Files | `~/Library/Application Support/research-mcp/cache/files/` (by SHA-256) and `trash/` | Cached PDFs and HTML | No (re-fetchable; archived copies live in Drive) |
| Model cache | `~/Library/Caches/research-mcp/models/` | Embedding model files | No (re-downloadable) |
| Archive | Drive sync folder `My Drive/Research Archive/<year>/` | Archived files and sidecars (their text stays in `cache.db`) | By Google Drive; also the source for the archive rebuild job |
| Config | `~/.config/research-mcp/config.toml` | Settings and secret references | Nightly with `state.db` |
| Logs | `~/Library/Logs/research-mcp/` | JSON lines, redacted | No; `research-mcp.jsonl` rotated by size, 5 files of 10 MB; `daemon.err.log` rotation is designed in the platform LLD at Gate 3 (PLAT-FR-40) |
| Secrets | macOS login Keychain, `research-mcp/<NAME>` | Credential values and the daemon token | By Keychain |

Nothing the lifecycle depends on lives in `~/Library/Caches`, which macOS and cleaning tools may purge. Both databases are backed up nightly and the last 7 backups are kept (PLAT-FR-57); only re-fetchable files are not. The scrub backups of the v1 client configs are the one temporary store of plaintext keys outside the Keychain; they are owner-only and deleted when v1 is retired (section 9; MIG-FR-26).

**Detail:** settings and paths in [LLD-platform-v1](../lld/LLD-platform-v1.md) §7.1 (from SPEC-v2 section 2) and §3.2 (HLD-v3 10); stores and migrations in §3.1 (SPEC-v2 3.5); backups in [LLD-cache-v1](../lld/LLD-cache-v1.md) §5 (SPEC-v2 9.8), summarized in LLD-platform-v1 §3.3; logging in LLD-platform-v1 §4.3 and §8; `cache.db` in LLD-cache-v1 §3 (SPEC-v2 8.1); `state.db` in [LLD-health-v1](../lld/LLD-health-v1.md) §3 (SPEC-v2 10.1). Requirements: PLAT-FR-8, PLAT-FR-9, PLAT-FR-40, PLAT-FR-56, PLAT-FR-57, CACHE-FR-59.

## 11. Key flows

> **Owner:** C · **Persona:** `architect`

### 11.1 Cross-source search

1. The agent calls `search("policy-as-code adoption", sources="auto", filters={year_from: 2023})`.
2. The registry selects `openalex`, `crossref`, `semantic_scholar`, `arxiv`, `core`, `dblp` and `ssrn` from the default groups, and reports `ads` as `disabled`. (Had OpenAlex's budget been spent, it would be selected and reported `budget_exhausted`, without a call; SRCH-FR-27, HLTH-FR-12.)
3. Seven tasks run with 5 s source timeouts inside an 8 s deadline.
4. The returned records are normalized, grouped by shared identifiers, merged and ranked.
5. The agent gets 20 works with `found_in`, plus eight `source_status` entries: one for each of the seven selected sources, one of which says `timeout`, and one for `ads`, which says `disabled`.

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
| **Install** | `uv tool install` (or a venv) for the package, then `research-mcp install`. Install writes three LaunchAgents (`local.research-mcpd` with KeepAlive; `local.research-mcp-watchdog` every 15 minutes; `local.research-mcp-doctor` daily at 08:52), creates the folders, generates the daemon token in Keychain, makes the first archive write in the foreground (for the macOS privacy prompt), and prints the client configs, which launch `research-mcp stdio` and contain no secret (PLAT-FR-54; MIG-FR-20). |
| **Upgrade** | `research-mcp upgrade` with rollback on a failed `doctor` (PLAT-FR-55). |
| **Daemon token** | Generated at install; rotated only from the CLI with `research-mcp secrets rotate-token`, never from the UI (PLAT-FR-59; PLAT-83). |
| **Logs** | JSON lines in `~/Library/Logs/research-mcp/research-mcp.jsonl`, rotated by size: 5 files of 10 MB; stderr receives warnings and errors only (PLAT-FR-40). The UI's Events page shows recent warning and error lines, redacted (UI-FR-18; HLD-v3 12). launchd also writes the daemon's stderr to `daemon.err.log` in the same folder ([LLD-platform-v1](../lld/LLD-platform-v1.md) §2.5); `RotatingFileHandler` does not rotate that file, and its rotation is designed in the platform LLD at Gate 3. |
| **Availability** | Best effort on one Mac: launchd KeepAlive restarts the daemon when it exits, and the watchdog (`doctor --liveness --notify`, every 15 minutes) reports a dead daemon within 15 minutes. There is no uptime percentage and no response target (NFR-12; OUT-4; HLTH-FR-41; PRD-v7 2.6). |
| **Backups** | Nightly copy of `state.db`, `cache.db` and the config; the last 7 are kept (PLAT-FR-57; CACHE-49). The optional copy to `Research Archive/_state/` in Drive (PLAT-FR-57) is not yet designed ([LLD-platform-v1](../lld/LLD-platform-v1.md) §3.3). |
| **Parallel run with v1** | v1 stays installed and read-only under its old client entry, disabled (not deleted) at cutover, until retirement ([ADR 0001](../adr/0001-new-repo-v1-read-only.md); MIG-FR-21; INV-10). |
| **Cutover and rollback** | Cutover (M4) adds the v2 entry `research` to each client config and disables the v1 entry. Rollback re-enables the v1 entry; after `scrub-client-configs`, it also restores the scrubbed values from the scrub backups, because v1 does not read the Keychain (MIG-FR-25). Rollback is available only before retirement: retiring v1 deletes the scrub backups, after which it cannot be done (PRD-migration-v5 1.5; MIG-FR-26). The steps are in the [cutover runbook](../runbooks/migration-cutover-v1.md). |
| **Halt conditions** | The rollout halts on any deletion without a recorded owner decision (INV-1), any secret in an output (INV-2), a fallback to v1 during the 14-day window, or any other invariant breach (INV-3 to INV-10, or a component invariant `<PREFIX>-INV-n`), and on a blocking issue during parallel use (runbook step 7). The owner is the only responder (PRD-v7 2.6; PRD-migration-v5 2.9). |
| **Retirement** | v1 is retired only after 14 days of daily use on v2 with no fallback and the owner's explicit go-ahead; a fallback restarts the 14-day count (PRD-migration-v5 2.8). Retiring v1 removes the v1 entries, archives the v1 repository and deletes the scrub backups (MIG-FR-24, MIG-FR-26). |

**Detail:** in [LLD-platform-v1](../lld/LLD-platform-v1.md): the CLI in §2.4 and packaging and CI in §5.8 (from SPEC-v2 section 12.1); launchd templates in §2.5 and install and upgrade in §5.9 (SPEC-v2 12.2); logging in §4.3 and §8; backups in §3.3 and [LLD-cache-v1](../lld/LLD-cache-v1.md) §5 (SPEC-v2 9.8). In [LLD-migration-v1](../lld/LLD-migration-v1.md): the legacy import in §5.1 (SPEC-v2 9.6); the credential and settings import in §5.2; scrub, the client config printer and cutover in §5.3 (MIGRATION-v2, via the [cutover runbook](../runbooks/migration-cutover-v1.md)). Requirements: PLAT-FR-40 to PLAT-FR-42, PLAT-FR-50 to PLAT-FR-59, MIG-FR-1 to MIG-FR-6, MIG-FR-10 to MIG-FR-15, MIG-FR-20 to MIG-FR-22, MIG-FR-24 to MIG-FR-26 ([PRD-migration-v5](../prd/components/PRD-migration-v5.md)), HLTH-FR-41; OUT-4; NFR-12; rollout conditions in PRD-v7 2.6 and PRD-migration-v5 2.9.

## 13. Quality attributes

> **Owner:** C · **Persona:** `architect`

| Attribute | How it is met |
|---|---|
| Maintainability | One adapter module per source; conformance suite; generated inventory; strict typing; no module over about 400 lines. |
| Reliability | Per-source isolation in fan-out; retries with backoff; circuit-breaking through health states; worker isolation for parsing. Availability is personal and best effort: launchd restarts the daemon and the watchdog reports a dead daemon within 15 minutes (NFR-12). |
| Performance | Concurrent fan-out with deadlines; shared connection pools; response budgets; FTS5 and exact vectors at personal-corpus scale (thousands of chunks). |
| Observability | Call telemetry, probes, states, notifications, structured logs, status endpoints, UI. |
| Security | Section 9. |
| Cost | Global rate limits and budgets for metered sources; quota states; paid web-search providers are optional, off until configured, capped per day and called only when asked for (section 9; ADR 0012). |

## 14. Milestones and where they land

> **Owner:** C · **Persona:** `architect`

| Milestone | Components built |
|---|---|
| M0 | core, platform (settings, secrets, HTTP, downloader, stores, logging, jobs, scheduler), sources (contract, registry, arXiv, Crossref, OpenAlex), federation, tools `search`, `get_work`, `list_sources`, daemon, shim, install, CI |
| M1 | all other adapters, for 45 sources registered at the exit (PRD-v7 OUT-1); citations, authors, `cite` and integrity (PRD-v7 2.9; SRCH-32); health, credentials, quota tracking, notifications, doctor |
| M2 | workers, extraction, `fetch`, `read`, `search_cache`, embeddings, cache lifecycle, review, searchable archive and its rebuild job, collections (with export through `cite`), crawl jobs, disk and integrity checks |
| M3 | UI |
| M4 | secrets import, legacy import, client cutover, v1 retirement (which deletes the scrub backups) |

The M0 work units and the criteria each owns are in the [M0 plan](../build/M0-plan-v1.md), which replaces SPEC-v2 section 12.3 and the TEST-PLAN-v3 Appendix A unit map; `.orchestration/plan-m0.json` is generated from it (AGENTS.md). The `planner` writes the plans for M1 to M4 when each milestone starts, replacing the SPEC-v2 12.4 outlines.

## 15. Architecture principles and approved stack

> **Owner:** H · **Persona:** none · **Seed question:** 9

This section is an H section. Its content is carried over unchanged from owner-approved sources (SPEC-v2 section 1 conventions and the architectural rules in [AGENTS.md](../../AGENTS.md)); nothing here is new. Confirmed by the owner at Gate 2 (owner decision, 2026-10-22).

**Stack and conventions** (from SPEC-v2 section 1):

- Python 3.12 (uv-managed interpreter, which bundles a current SQLite), `uv`, `src/` layout, package `research_mcp`, version `3.0.0`.
- Typing: mypy strict on `src/`; Pydantic v2 models for everything that crosses a module boundary or the MCP boundary.
- Async: `anyio`; HTTP with `httpx.AsyncClient`; SQLite with `aiosqlite` through the store classes only.
- Time: UTC everywhere (`datetime` with `tzinfo=UTC`), stored as ISO 8601 text; the scheduler converts to local time for 09:00 and quiet hours.
- IDs: ULIDs for internal rows (`works.work_id`, `documents.doc_id`, jobs, batches).
- Tests: pytest with `--import-mode=importlib`; test folders have no `__init__.py`; shared test helpers live in the package `research_mcp.testing` so tests import them by absolute name.
- No em dashes or en dashes in code comments, docs or UI strings (NFR-11).

Further stack choices already recorded as decisions: macOS Keychain for secrets ([ADR 0003](../adr/0003-secrets-in-keychain.md)); two SQLite files with FTS5 and vectors in SQLite ([ADR 0008](../adr/0008-sqlite-stores-and-vectors.md)); Starlette, Jinja2 and htmx for the UI ([ADR 0010](../adr/0010-localhost-ui-stack.md)). Dependencies, extras and tool settings are in [LLD-platform-v1](../lld/LLD-platform-v1.md) §5.8 (from SPEC-v2 section 12.1).

**Architectural rules** (from AGENTS.md):

- Adapters (`src/research_mcp/sources/`) only translate: no HTTP library imports, no sleeping, no retries, no secrets, no file writes.
- No tool may block the event loop; CPU work goes to worker subprocesses (`platform/workers.py`).
- Tests pass with the network blocked; use `FakeProvider`, recorded fixtures and the fakes in `research_mcp.testing`.
- Never print, log, commit or put in fixtures any secret, token or password. Fixtures are recorded with credentials removed.
- Every change needs tests.

## 16. Key decisions

> **Owner:** C · **Persona:** `architect` drafts ADR options; the owner decides · **Seed question:** 10

Statuses as recorded in PRD-v7 1.6 on 2026-10-22. ADR 0007's file title still says "30-day cache"; ADR 0011 amends it to 120 days.

| ADR | Decision | Status |
| --- | --- | --- |
| [ADR 0001](../adr/0001-new-repo-v1-read-only.md) | v2 is a new repository; v1 stays read-only and running until cutover | accepted (2026-10-22, with Gate 1) |
| [ADR 0002](../adr/0002-one-daemon-with-stdio-shims.md) | One daemon per Mac; clients use a stdio shim | accepted (2026-10-22, with Gate 1) |
| [ADR 0003](../adr/0003-secrets-in-keychain.md) | Secrets live in the macOS Keychain; configuration holds references | accepted (2026-10-22, with Gate 1) |
| [ADR 0004](../adr/0004-modular-core-composition-root.md) | Modular core built by one composition root; no work at import | accepted (2026-10-22, with Gate 1) |
| [ADR 0005](../adr/0005-async-io-cpu-off-loop.md) | Async I/O end to end; CPU work in worker processes | accepted (2026-10-22, with Gate 1) |
| [ADR 0006](../adr/0006-source-adapter-contract.md) | Every source is an adapter with a declarative `SourceSpec` | accepted (2026-10-22, with Gate 1) |
| [ADR 0007](../adr/0007-cache-lifecycle-and-drive-archive.md) | Cache with owner review; archive to the Google Drive sync folder; amended by ADR 0011 (120 days, not 30) | accepted (2026-10-22, with Gate 1) |
| [ADR 0008](../adr/0008-sqlite-stores-and-vectors.md) | Two SQLite files; vectors stored in SQLite | accepted (2026-10-22, with Gate 1) |
| [ADR 0009](../adr/0009-no-sql-untrusted-content.md) | No free-form SQL; fetched content is labeled untrusted | accepted (2026-10-22, with Gate 1) |
| [ADR 0010](../adr/0010-localhost-ui-stack.md) | The UI is server-rendered inside the daemon | accepted (2026-10-22, with Gate 1) |
| [ADR 0011](../adr/0011-archive-keeps-text-searchable-120-day-retention.md) | 120-day retention; archived papers stay searchable (amends 0007) | accepted (2026-10-19) |
| [ADR 0012](../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md) | Domain-neutral scope; every v1 endpoint kept; web search as optional sources | accepted (2026-10-19) |
| [ADR 0013](../adr/0013-adopt-spec-driven-development.md) | Adopt spec-driven development fully, before the next build (option 2) | accepted (2026-10-22) |

No new decision in v4 changes the system's shape, so v4 proposes no new ADR.

## 17. Testing strategy

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 2

Aligned with [test plan v3](../test/test-plan-v3.md) sections 1 and 4; drafted by the `architect` and reviewed by the `test-architect` on 2026-10-22. How each criterion is verified is in the test plan; per-criterion coverage is generated in `docs/trace/coverage.md`.

**Test levels and environments** (test plan v3 1.1):

| Level | Runs | Network | External systems |
|---|---|---|---|
| unit | every work unit and commit (`tools/ci.sh --python-only`) | blocked | none |
| integration | every commit | blocked | fakes from `research_mcp.testing`: `httpx.MockTransport` with recorded fixtures, `FakeProvider`, `FakeClock` and fake sleeper, fake `launchctl`, fake notifier, injected resolver, temp folders for Drive |
| contract | every commit | blocked | in-memory MCP client (`mcp.shared.memory`) against `build_mcp` |
| live | opt-in (`pytest -m live`), nightly on the Mac later | allowed | real upstreams, no credentials unless the owner runs it locally |

Network blocking: `tests/conftest.py` installs a socket guard that fails any test opening a non-loopback connection unless it is marked `live`; `pyproject.toml` deselects `live` tests by default (`-m 'not live'`). Tests run with `--import-mode=importlib`; test folders have no `__init__.py`.

Secrets in tests: only `FakeProvider` with generated values; the security suite registers those values with the redactor and scans every output.

Fixtures: every adapter has seven recorded fixtures in `tests/sources/<id>/fixtures/` (SRC-FR-8; test plan v3 1.3). Other fakes and fixtures (synthetic v1 database, hostile PDF corpus, temp Drive folder, `FakeLaunchctl`, `FakeNotifier`) are in test plan v3 1.3.

**Cross-cutting criteria that every milestone keeps green** (test plan v3 1.2):

| Area | Rule | Criteria |
|---|---|---|
| No secret in any output | Logs, errors, tool results, UI pages, notifications and process argument lists never contain a registered secret | SEC-1, SEC-5, SEC-6, SEC-7, SEC-9, SEC-10, SEC-13, SEC-14, HLTH-32, HLTH-34, UI-4, MIG-22 |
| No secret at rest | No registered secret is stored in configuration, Application Support or log files, and credentials are kept as metadata only | SEC-24, SEC-27, HLTH-43, MIG-23 |
| Loopback and auth | Nothing binds beyond loopback; every request is authenticated | PLAT-10, PLAT-71, SEC-11, SEC-12, SEC-26, UI-2, UI-3, UI-20 |
| Async discipline | The event loop never blocks | PLAT-75, SRCH-1, ruff ASYNC rules |
| Bounded output | No result exceeds the budget | PLAT-31, PLAT-63 |
| Untrusted content | Fetched text is always enveloped | PLAT-33, SEC-22 |
| Adapter isolation | Adapters do no I/O of their own | SRC-7, conformance |
| No silent deletion | Nothing is deleted without an owner decision; MCP discards are announced; shared files survive | CACHE-33, CACHE-34, CACHE-36, CACHE-48, SEC-20 |
| Docs follow code | The generated inventory and plan are current and the trace check passes | SRC-13, `node tools/sdd/cli.mjs check` in CI |

The "No secret at rest" area is new in test plan v3 (owner decision, 2026-10-22).

**Milestone exit gates** (test plan v3 1.4; owner checks OC-01 to OC-14 are in test plan v3 section 3 and are not criteria):

| Milestone | Gate |
|---|---|
| M0 | Every M0 criterion in the [M0 plan](../build/M0-plan-v1.md) has a passing test that cites it; full `tools/ci.sh` green, including `node tools/sdd/cli.mjs check` (lint, strict mypy, coverage 85% on `src/`, build, `--help`); owner checks OC-01 and OC-02. SEC-24, SEC-26, SRCH-37 and SRCH-38 are M0 criteria with no unit in the M0 plan, so they do not gate M0 until the `planner` assigns them (test plan v3 section 5, item 4). |
| M1 | All M1 tests pass; 45 or more sources registered and passing conformance (PRD-v7 OUT-1); OC-03, OC-08 (once a remote exists), OC-11, OC-12, OC-14 (owner decision, 2026-10-22). |
| M2 | All M2 tests pass, including the hostile PDF corpus; OC-04, OC-10 and OC-13. |
| M3 | All M3 tests pass; OC-05 and OC-09. |
| M4 | All M4 tests pass; OC-06 then OC-07. |

**Exceptions** (test plan v3 section 4):

- INV-6 and NFR-3 are excepted for the scrub backups written by `scrub-client-configs` only, until v1 retirement, when MIG-26 deletes them. The exception is partial, so INV-6 and NFR-3 keep their tests otherwise, and MIG-25 and MIG-26 check the backups' permissions and deletion (owner decision, 2026-10-22 at Gate 1; MIG-FR-26).
- INV-4 and SEC-INV-7 are excepted for owner-run migration commands only, per command, until v1 retirement: `secrets import` (MIG-FR-1) and `scrub-client-configs` (MIG-FR-5) read only the MCP client configs; only the legacy import (MIG-FR-10) reads the v1 folder (`~/arxiv-papers`, the v1 database), read only (INV-10, MIG-INV-1). MCP tools and agent-triggered actions stay bound by INV-4 and SEC-INV-7, so their tests are unchanged (owner decision, 2026-10-22).

## 18. Risks and mitigations

> **Owner:** A · **Persona:** `architect`; the owner ranks them at Gate 2

The owner rated and ranked these risks at Gate 2 (owner decision, 2026-10-22); the rows are in rank order, highest first.

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Upstream APIs change faster than one person can follow (PRD-v7 2.10). | High | Medium | Probes check response shape, not just status; recorded fixtures make breakage visible in tests; each source can be disabled with a flag (sections 4, 7, 9). |
| Drive sync folder unavailable, blocked by macOS privacy controls, or not uploading (PRD-v7 2.10). | Medium | High | Install performs the first archive write in the foreground so the privacy prompt appears; `doctor` checks access; local fallback with a warning and reconcile; nothing leaves the cache until the archive copy is verified; upload state is checked and a stalled upload is reported (sections 6, 12). |
| Scope creep toward a library manager (PRD-v7 2.10). | Medium | Medium | Non-goals in PRD-v7 1.3; collections stay minimal. |
| Five-source search p95 depends on upstream latency the project does not control (test plan v3 section 5, item 3). | Medium | Medium | If OC-12 fails, the deadline or default source set is tuned rather than the gate removed (sections 5, 13). |
| Keychain locked or unreadable, for example right after login (PRD-v7 2.10). | Medium | Low | Reads go through `/usr/bin/security` with a timeout; a locked Keychain is one `keychain_locked` state and one notification, not a notice per key; `doctor` gives the fix (sections 7, 9). |
| Metered sources (OpenAlex budget, web-search providers) run out mid-task or cost more than expected (PRD-v7 2.10). | Medium | Low | Budget tracking with `quota_low`, `rate_limited` and `budget_exhausted` states; federation skips exhausted sources and says so; web-search sources are off until configured, capped per day, and never in the default fan-out (sections 4, 5, 9). |
| PyMuPDF crashes on hostile PDFs (PRD-v7 2.10). | Medium | Low | Parsing in a worker process with CPU, memory, page and time limits (sections 3, 9). |
| macOS or cleaning tools purge `~/Library/Caches` (HLD-v3 section 10). | Low | Low | Nothing the lifecycle depends on lives there; only the re-downloadable model cache does; both databases live in Application Support and are backed up nightly (section 10). |

## 19. Traceability

> **Owner:** A · **Persona:** `architect`

**Components.** The SPEC-v2 split below was checked against the LLD headings for v4. All PRDs are the Gate 1 versions; all LLDs are v1 drafts.

| Component | Prefix | PRD | LLD | SPEC sections | Carries SPEC-v2 sections |
| --- | --- | --- | --- | --- | --- |
| Platform | PLAT | [PRD-platform-v4](../prd/components/PRD-platform-v4.md) | [LLD-platform-v1](../lld/LLD-platform-v1.md) | 2, 3, 5, 9, 10, 12, 15 | 1, 2, 3.1 to 3.7, 7.4, 12.1, 12.2 (9.8 summarized in §3.3) |
| Sources | SRC | [PRD-sources-v5](../prd/components/PRD-sources-v5.md) | [LLD-sources-v1](../lld/LLD-sources-v1.md) | 4, 5, 9 | 4, 5.1 to 5.5 |
| Search and identity | SRCH | [PRD-search-v3](../prd/components/PRD-search-v3.md) | [LLD-search-v1](../lld/LLD-search-v1.md) | 5, 11.1, 14 | 6, 7.1 to 7.3 |
| Retrieval and cache | CACHE | [PRD-cache-v4](../prd/components/PRD-cache-v4.md) | [LLD-cache-v1](../lld/LLD-cache-v1.md) | 6, 10, 11.2, 11.3 | 8, 9.1 to 9.5, 9.7, 9.8 |
| Health and credentials | HLTH | [PRD-health-v4](../prd/components/PRD-health-v4.md) | [LLD-health-v1](../lld/LLD-health-v1.md) | 7, 10, 11.4, 12 | 10 |
| Local UI | UI | [PRD-ui-v4](../prd/components/PRD-ui-v4.md) | [LLD-ui-v1](../lld/LLD-ui-v1.md) | 8, 9 | 11 |
| Migration and cutover | MIG | [PRD-migration-v5](../prd/components/PRD-migration-v5.md) | [LLD-migration-v1](../lld/LLD-migration-v1.md) | 6, 9, 12, 14 | 9.6, and MIGRATION-v2 |
| Security | SEC | [PRD-security-v2](../prd/components/PRD-security-v2.md) | [LLD-security-v1](../lld/LLD-security-v1.md) | 2, 9, 17 | HLD-v3 2 and 9 (threat model); quotes 3.1, 3.1.1 and 3.2, whose names LLD-platform-v1 owns |

SPEC-v2 sections not carried into an LLD: 0.1 to 0.5 (conformance, precedence and change control), which AGENTS.md and the SDD standard now cover (LLDs own every name; documents are versioned; drift is decided by a person); 12.3 and 12.4 (work breakdown), which the milestone plans replace (section 14).

**Component requirements.**

| Component requirements | Area | SPEC section | LLD |
| --- | --- | --- | --- |
| PLAT-FR-1 to PLAT-FR-6 | Process and transport | 2, 3, 12 | LLD-platform-v1 §2.3, §5.2, §5.5, §5.7, §5.9 |
| PLAT-FR-8, PLAT-FR-9 | Configuration and paths | 10 | LLD-platform-v1 §3.2, §7.1 |
| PLAT-FR-10 to PLAT-FR-15, PLAT-FR-59 | Secrets and the daemon token | 8, 9, 10, 12 | LLD-platform-v1 §4.1 to §4.5, §5.9 |
| PLAT-FR-20 to PLAT-FR-22, PLAT-FR-25 to PLAT-FR-27 | Local access and untrusted content | 2, 9 | LLD-platform-v1 §2.1, §2.3, §4.6 |
| PLAT-FR-30 to PLAT-FR-33 | Results, errors and HTTP | 3, 5 | LLD-platform-v1 §2.1, §2.2, §5.3, §5.6, §6 |
| PLAT-FR-40 to PLAT-FR-42 | Logging | 10, 12 | LLD-platform-v1 §4.3, §8 |
| PLAT-FR-50 to PLAT-FR-58 | Packaging, CI, stores, backups and upgrades | 10, 12, 15 | LLD-platform-v1 §2.4, §2.5, §3.1, §3.3, §5.8, §5.9 |
| SRC-FR-1 to SRC-FR-10 | Contract, registry, states, fixtures, models, upstream MCP | 4 | LLD-sources-v1 §2, §3.1, §3.4, §5.2, §5.3, §5.6 |
| SRC-FR-12, SRC-FR-14, SRC-FR-15, SRC-FR-17, SRC-FR-18 | Live check, shutdown dates, docs sites, v1 coverage, site sets | 4 | LLD-sources-v1 §3.3, §5.4, §5.8 |
| SRC-FR-19 to SRC-FR-23 | The `web` group, caps, fallback, `site_set`, Google sign-in | 4, 5, 9 | LLD-sources-v1 §5.7 to §5.9; LLD-platform-v1 §4.2 |
| SRC-FR-24 to SRC-FR-26 | Contact address, generated inventory, new-source definition of done | 4, 13 | LLD-sources-v1 §3.2, §5.5, §5.10; LLD-platform-v1 §7.1 |
| SRCH-FR-1 to SRCH-FR-3, SRCH-FR-5 to SRCH-FR-9, SRCH-FR-27 | Federated search and source status | 5, 11.1 | LLD-search-v1 §2.1, §5.4; LLD-sources-v1 §5.9 |
| SRCH-FR-11 to SRCH-FR-14, SRCH-FR-28 | Identity and dedupe | 5 | LLD-search-v1 §5.2, §5.3 |
| SRCH-FR-15 to SRCH-FR-17 | Work lookup | 5 | LLD-search-v1 §2.1, §5.3 |
| SRCH-FR-20 to SRCH-FR-23 | Citations, authors and export | 5, 14 | LLD-search-v1 §2.1, §5.5 |
| SRCH-FR-25, SRCH-FR-26 | Integrity | 5 | LLD-search-v1 §2.1, §5.5 |
| CACHE-FR-1 to CACHE-FR-7 | Fetch | 6, 9, 11.2 | LLD-cache-v1 §2, §5; LLD-platform-v1 §5.4 |
| CACHE-FR-10 to CACHE-FR-14 | Extraction and chunking | 3, 6, 9 | LLD-cache-v1 §5; LLD-platform-v1 §5.5 |
| CACHE-FR-15 to CACHE-FR-18 | Reading and local search | 6, 11.2 | LLD-cache-v1 §2, §5 |
| CACHE-FR-20 to CACHE-FR-24 | Embeddings | 6, 10 | LLD-cache-v1 §3, §5 |
| CACHE-FR-30 to CACHE-FR-38 | Lifecycle and owner review | 6, 11.3 | LLD-cache-v1 §3, §5 |
| CACHE-FR-45 to CACHE-FR-52 | Archive to Google Drive and its rebuild | 6, 10, 12 | LLD-cache-v1 §2, §5 |
| CACHE-FR-55 to CACHE-FR-59 | Collections, crawl jobs, disk, integrity, data location | 6, 10, 14 | LLD-cache-v1 §5, §7 |
| HLTH-FR-1 to HLTH-FR-5 | Telemetry and probes | 7 | LLD-health-v1 §3, §5 |
| HLTH-FR-10 to HLTH-FR-12 | Source states | 5, 7 | LLD-health-v1 §5 |
| HLTH-FR-20 to HLTH-FR-25 | Credential states | 7, 11.4 | LLD-health-v1 §3, §5 |
| HLTH-FR-30 to HLTH-FR-35 | Notifications | 7, 11.3, 11.4 | LLD-health-v1 §2, §5 |
| HLTH-FR-40 to HLTH-FR-43 | Doctor and agent access | 7, 12 | LLD-health-v1 §2, §5 |
| UI-FR-1 to UI-FR-4, UI-FR-6, UI-FR-7, UI-FR-20 | General | 8, 9 | LLD-ui-v1 §2.1 to §2.4, §4 |
| UI-FR-10 to UI-FR-18, UI-FR-21 | Pages | 8 | LLD-ui-v1 §5.2, §5.3 |
| MIG-FR-1 to MIG-FR-6, MIG-FR-26 | Credentials and scrub backups | 9, 10, 12, 14 | LLD-migration-v1 §5.2, §5.3 |
| MIG-FR-10 to MIG-FR-15 | Optional corpus import | 6, 12, 14 | LLD-migration-v1 §5.1 |
| MIG-FR-20 to MIG-FR-22, MIG-FR-24, MIG-FR-25 | Client cutover, rollback and v1 retirement | 12, 14 | LLD-migration-v1 §5.3; cutover runbook |

The Security component has no requirements of its own (PRD-security-v2 2.4); its criteria are below.

**Acceptance criteria.** Every criterion of the approved component PRDs and test plan v3, including the ones added at Gate 1.

| Criteria | Area | SPEC section | LLD |
| --- | --- | --- | --- |
| PLAT-1, PLAT-2, PLAT-4, PLAT-13, PLAT-80, PLAT-84 | Version, CI script, extras, CLI | 6, 12, 15 | LLD-platform-v1 §2.4, §5.8, §7.2; LLD-cache-v1 §5 for the upload state |
| PLAT-3, PLAT-70, PLAT-72, PLAT-73, PLAT-75, PLAT-77 | Composition root, shim, event loop | 2, 3 | LLD-platform-v1 §2.3, §5.2, §5.7 |
| PLAT-5 | Offline test guard | 17 | LLD-platform-v1 §9 |
| PLAT-6, PLAT-30 to PLAT-34 | Models, envelope, errors, cursors | 3, 5 | LLD-platform-v1 §2.1, §2.2, §5.6 |
| PLAT-8 to PLAT-12 | Settings, paths, loopback setting, contact address, secret references | 4, 9, 10 | LLD-platform-v1 §4.1, §7.1 |
| PLAT-35 to PLAT-39 | HTTP client | 3, 9 | LLD-platform-v1 §5.3, §6.1 |
| PLAT-40 to PLAT-42 | Logging | 10, 12 | LLD-platform-v1 §4.3, §8 |
| PLAT-50 to PLAT-53 | Stores and migrations | 10 | LLD-platform-v1 §3.1 |
| PLAT-60 to PLAT-63 | MCP surface | 5, 9 | LLD-platform-v1 §2.3, §5.6 |
| PLAT-71 | Loopback bind | 2, 9 | LLD-platform-v1 §4.5 |
| PLAT-74, PLAT-76 | Jobs and the scheduler | 3 | LLD-platform-v1 §5.5 |
| PLAT-81 to PLAT-83 | Install, client config, daemon token | 12 | LLD-platform-v1 §2.5, §4.5, §5.9 |
| SEC-1 to SEC-4, SEC-13 | Secrets and Keychain access | 9 | LLD-security-v1 §4.3; LLD-platform-v1 §4.1 |
| SEC-5 to SEC-7, SEC-14 | Redaction | 9 | LLD-security-v1 §4.3; LLD-platform-v1 §4.3 |
| SEC-8 to SEC-10 | Credential scoping and errors | 9 | LLD-security-v1 §4.3; LLD-platform-v1 §4.4 |
| SEC-11, SEC-12, SEC-26 | Loopback, bearer token, shim token | 2, 9 | LLD-security-v1 §4.3; LLD-platform-v1 §4.5, §5.7 |
| SEC-20 to SEC-22, SEC-25 | MCP surface: no hard delete, no SQL, untrusted envelope, no caller paths | 9 | LLD-security-v1 §4.3; LLD-platform-v1 §4.6; LLD-search-v1 §2.1 |
| SEC-23 | Hostile PDFs | 6, 9 | LLD-security-v1 §4.3; LLD-platform-v1 §5.5; LLD-cache-v1 §5 |
| SEC-24, SEC-27 | No secret at rest | 9, 10 | LLD-security-v1 §3, §4.4; LLD-platform-v1 §4.1, §4.2 |
| SRC-1 to SRC-8 | Contract, registry, states, conformance, adapter isolation | 4 | LLD-sources-v1 §2, §5.2, §5.3 |
| SRC-10 to SRC-12 | The three M0 adapters | 4 | LLD-sources-v1 §5.3 |
| SRC-13 | Generated inventory | 4, 17 | LLD-sources-v1 §5.10 |
| SRC-20 to SRC-27 | M1 catalog, instances, upstream MCP, docs sites, shutdown dates, live check, v1 map, site sets | 4 | LLD-sources-v1 §3.3, §5.3, §5.4, §5.6 |
| SRC-28 to SRC-33 | The `web` group | 4, 5, 9 | LLD-sources-v1 §5.7 to §5.9; LLD-platform-v1 §4.2 |
| SRCH-10 to SRCH-16, SRCH-38 | Identity | 5 | LLD-search-v1 §5.2 |
| SRCH-1 to SRCH-9, SRCH-37 | Federation | 5, 11.1 | LLD-search-v1 §5.3, §5.4 |
| SRCH-17, SRCH-23, SRCH-36 | `get_work` | 5 | LLD-search-v1 §2.1, §5.5 |
| SRCH-20 to SRCH-22 | MCP contract and argument bounds | 5 | LLD-search-v1 §2.1 |
| SRCH-30 to SRCH-34 | Citations, authors, `cite`, integrity, search records | 5, 14 | LLD-search-v1 §2.1, §5.5 |
| CACHE-1, CACHE-2 | Downloader | 6, 9 | LLD-platform-v1 §5.4; LLD-cache-v1 §2 |
| CACHE-10 to CACHE-13 | Fetch | 6, 11.2 | LLD-cache-v1 §2, §5 |
| CACHE-14 to CACHE-18 | Extraction and chunking | 6 | LLD-cache-v1 §5 |
| CACHE-19 to CACHE-24 | Reading, local search, embeddings | 6 | LLD-cache-v1 §2, §5 |
| CACHE-30 to CACHE-36, CACHE-48 | Lifecycle and review | 6, 11.3 | LLD-cache-v1 §4, §5 |
| CACHE-40 to CACHE-44, CACHE-60 to CACHE-62 | Archive and rebuild | 6, 10 | LLD-cache-v1 §2, §5 |
| CACHE-45, CACHE-63 | Collections and their export | 6, 14 | LLD-cache-v1 §5; LLD-search-v1 §2.1 |
| CACHE-46, CACHE-47 | Disk and maintenance | 6, 13 | LLD-cache-v1 §5, §8 |
| CACHE-49 | Backups | 10, 12 | LLD-cache-v1 §5; LLD-platform-v1 §3.3 |
| HLTH-1 to HLTH-4, HLTH-44 | Telemetry and probes, including the embeddings target | 7 | LLD-health-v1 §5 |
| HLTH-10 to HLTH-13 | Source states and the locked Keychain | 5, 7 | LLD-health-v1 §5 |
| HLTH-20 to HLTH-25, HLTH-43 | Credential states and metadata only | 7, 11.4 | LLD-health-v1 §3, §5 |
| HLTH-30 to HLTH-35 | Notifications | 7 | LLD-health-v1 §2, §5 |
| HLTH-40 to HLTH-42 | Doctor and status | 7, 12 | LLD-health-v1 §2, §5 |
| UI-1 to UI-6, UI-20 | Loopback, login, CSRF, no secrets, refresh, style, Host and Origin | 8, 9 | LLD-ui-v1 §2.1 to §2.4, §4 |
| UI-10 to UI-19, UI-21 to UI-25 | Pages | 8 | LLD-ui-v1 §5.2, §5.3 |
| MIG-1 to MIG-6, MIG-22, MIG-23, MIG-25 | Credential import and scrub backups | 9, 12 | LLD-migration-v1 §5.2, §5.3 |
| MIG-10 to MIG-14, MIG-24 | Legacy import and an empty cache | 6, 12 | LLD-migration-v1 §5.1 |
| MIG-20, MIG-21, MIG-26 | Client configs, tool map, retirement | 12, 14 | LLD-migration-v1 §5.3 |

**Parent requirements.**

| Parent requirement | Component requirements | SPEC section | LLD |
| --- | --- | --- | --- |
| OUT-1 Breadth | SRC-FR-1 to SRC-FR-10, SRC-FR-12, SRC-FR-14, SRC-FR-15, SRC-FR-17 to SRC-FR-26 | 4, 14 | LLD-sources-v1 |
| OUT-2 One search | SRCH-FR-1 to SRCH-FR-3, SRCH-FR-5 to SRCH-FR-9, SRCH-FR-27 | 5, 11.1, 13 | LLD-search-v1 |
| OUT-3 Cheap to maintain | SRC-FR-25, SRC-FR-26; every PLAT-FR cites OUT-3 | 3, 4, 13 | LLD-sources-v1, LLD-platform-v1 |
| OUT-4 Monitored | HLTH-FR-1 to HLTH-FR-5, HLTH-FR-10 to HLTH-FR-12, HLTH-FR-40 to HLTH-FR-43 | 7, 12 | LLD-health-v1 |
| OUT-5 Credential care | HLTH-FR-20 to HLTH-FR-25, HLTH-FR-30 to HLTH-FR-35 | 7, 11.4 | LLD-health-v1 |
| OUT-6 Cache, not library | CACHE-FR-30 to CACHE-FR-38, CACHE-FR-45 to CACHE-FR-52; every CACHE-FR cites OUT-6 | 6, 11.3 | LLD-cache-v1 |
| OUT-7 Safe by default | PLAT-FR-10 to PLAT-FR-15, PLAT-FR-59, PLAT-FR-20 to PLAT-FR-22, PLAT-FR-25 to PLAT-FR-27; MIG-FR-26; SEC criteria | 9 | LLD-security-v1, LLD-platform-v1 |
| OUT-8 Visible | UI-FR-1 to UI-FR-4, UI-FR-6, UI-FR-7, UI-FR-10 to UI-FR-18, UI-FR-20, UI-FR-21 | 8 | LLD-ui-v1 |
| NFR-1 Single process | PLAT-FR-1, PLAT-FR-2 | 2, 3 | LLD-platform-v1 |
| NFR-2 Async | PLAT-FR-5 | 3 | LLD-platform-v1 |
| NFR-3 No secrets at rest outside the Keychain | PLAT-FR-10; MIG-FR-26 (approved exception) | 9, 10 | LLD-platform-v1, LLD-security-v1, LLD-migration-v1 |
| NFR-4 No secret in any output | PLAT-FR-11, PLAT-FR-13, PLAT-FR-14 | 9, 17 | LLD-platform-v1, LLD-security-v1 |
| NFR-5 Bounded output | PLAT-FR-30, SRCH-FR-6 | 5 | LLD-platform-v1, LLD-search-v1 |
| NFR-6 Untrusted content is labeled | PLAT-FR-25 | 2, 9 | LLD-platform-v1 |
| NFR-7 Loopback only | PLAT-FR-3, UI-FR-1 | 2, 9 | LLD-platform-v1, LLD-ui-v1 |
| NFR-8 Respect upstream terms | PLAT-FR-33, SRC-FR-24 | 3, 4, 13 | LLD-platform-v1, LLD-sources-v1 |
| NFR-9 Testable offline | SRC-FR-8 | 4, 17 | LLD-sources-v1, LLD-platform-v1 |
| NFR-10 Docs follow code | SRC-FR-25 | 4, 13, 17 | LLD-sources-v1 |
| NFR-11 Prose style | UI-FR-7 | 15 | LLD-ui-v1 |
| NFR-12 Availability and scale | PLAT-FR-1, HLTH-FR-41 | 12, 13 | LLD-platform-v1, LLD-health-v1 |

**Invariants.**

| Invariants | Enforced by | SPEC section | LLD |
| --- | --- | --- | --- |
| INV-1 | CACHE-FR-34, CACHE-FR-36; CACHE-INV-1 | 6, 12 | LLD-cache-v1 |
| INV-2 | PLAT-FR-11, PLAT-FR-13, PLAT-FR-14; SEC-INV-4 | 9, 12 | LLD-platform-v1, LLD-security-v1 |
| INV-3 | PLAT-FR-12, CACHE-FR-3; SEC-INV-5 | 9 | LLD-platform-v1, LLD-security-v1 |
| INV-4 | PLAT-FR-21, CACHE-FR-4; SEC-INV-7 | 6, 9 | LLD-platform-v1, LLD-security-v1 |
| INV-5 | PLAT-FR-3, UI-FR-1; SEC-INV-1 | 2, 9 | LLD-platform-v1, LLD-security-v1 |
| INV-6 | PLAT-FR-10, SRC-FR-23; SEC-INV-3, SEC-INV-11; exception MIG-FR-26 | 9, 10 | LLD-platform-v1, LLD-security-v1, LLD-migration-v1 |
| INV-7 | CACHE-FR-47; CACHE-INV-5 | 6 | LLD-cache-v1 |
| INV-8 | CACHE-FR-51; CACHE-INV-6 | 6 | LLD-cache-v1 |
| INV-9 | SRC-FR-19; SRC-INV-4 | 4, 5, 9 | LLD-sources-v1 |
| INV-10 | MIG-FR-10; MIG-INV-1 | 12 | LLD-migration-v1 |
| SEC-INV-1 to SEC-INV-11 | Security invariants (the platform defines none of its own) | 2, 9 | LLD-security-v1 §4.4 |
| SRC-INV-1 to SRC-INV-6 | Sources invariants | 4, 9 | LLD-sources-v1 |
| SRCH-INV-1 to SRCH-INV-3 | Search invariants | 5 | LLD-search-v1 |
| CACHE-INV-1 to CACHE-INV-7 | Cache invariants | 6 | LLD-cache-v1 |
| HLTH-INV-1 to HLTH-INV-5 | Health invariants | 7 | LLD-health-v1 |
| UI-INV-1 to UI-INV-5 | UI invariants | 8 | LLD-ui-v1 |
| MIG-INV-1 to MIG-INV-3 | Migration invariants | 12 | LLD-migration-v1 |

**Where the SPEC-v2 0.6 clarification rows live.** SPEC-v2 0.6 has seven rows from the first M0 attempt; AGENTS.md makes them requirements. Every component a row concerns carries it, marked "(SPEC-v2 0.6)". LLD-ui-v1 §1 and LLD-migration-v1 §1 state that no row concerns them. No row is missing from an LLD.

| Unit; SPEC-v2 section | Row | Carried in |
| --- | --- | --- |
| M0-01; 1, 12.1 | Offline network guard installed for the whole test session | LLD-platform-v1 §9 |
| M0-01; 1 | Import side effects attributed to `research_mcp` through any frame | LLD-platform-v1 §5.1 |
| M0-01; 12.1 | CI on macOS and Linux, SHA-pinned actions, secret scan, weekly audit | LLD-platform-v1 §5.8; LLD-security-v1 §5 (and E35 in §4.3) |
| M0-02; 6 | Idempotent normalizers, strict UTF-8 decoding, slashes in suffixes | LLD-search-v1 §5.2 |
| M0-03; 3.7, 4 | `Budget.fit` keeps one status per source | LLD-platform-v1 §5.6; LLD-sources-v1 §3.1; LLD-search-v1 §6 |
| M0-04; 2 | Path normalization and canonical credential names | LLD-platform-v1 §7.1; LLD-cache-v1 §7 |
| M0-05; 3.1 | `SecretRef` validation; `FakeProvider.metadata` | LLD-platform-v1 §4.1; LLD-security-v1 §5; LLD-health-v1 §5 |

**LLD updates due at Gate 3.** The v1 LLDs predate the Gate 1 PRDs. These are decided by the approved PRDs, so they are LLD work for the `component-designer`, not open questions here:

- The section 1 tables of every LLD cite the earlier PRD versions and the superseded requirement IDs listed in the provenance section; the next LLD versions use the successors.
- The criteria added at Gate 1 (PLAT-84, SEC-24 to SEC-27, SRCH-37, SRCH-38, CACHE-62, CACHE-63, HLTH-43, HLTH-44, UI-20 to UI-25, MIG-22 to MIG-26) are mapped above to the LLD that will carry them; no v1 LLD names them yet.
- `SourceStatus.state` in LLD-platform-v1 §2.1 (quoted in LLD-sources-v1 §6 and LLD-search-v1 §2.2) needs `budget_exhausted` and `not_needed` in place of the earlier budget state (SRCH-FR-27).
- LLD-sources-v1 §5.5 step 5 is superseded by SRC-FR-26, and the `sources --markdown` option in LLD-platform-v1 §2.4 is removed by SRC-FR-25.
- LLD-ui-v1 needs the read-only site sets on the Settings page (UI-FR-21), polling only (UI-FR-20) and job retry through `JobService.submit` (UI-FR-13).
- LLD-migration-v1 §5.3 needs the rollback from scrub backups (MIG-FR-25) and owner-only scrub backups deleted at retirement (MIG-FR-26), including where the backups are written.
- LLD-security-v1 needs the scrub backup row and the shim sentence in the §4.2 threat model, enforcement points for MIG-25 and MIG-26 in §4.3, SEC-24 to SEC-27 in the §4.4 coverage table in place of its gaps, and the migration-reads exception to INV-4 and SEC-INV-7 (section 9).
- Open questions in the v1 LLDs that the Gate 1 PRDs answer (UI token rotation, inventory generator, status names, placeholder contact, the new-source checklist, `cite` in M1, the embeddings probe, the SEC-INV gaps, the client transport) can be closed in those next versions.

## 20. Open questions

> **Owner:** A · **Persona:** `architect`

Resolved in v4 (details in the provenance section):

- [x] Q: How many sources and fixtures? 45 sources at the M1 exit (PRD-v7 OUT-1) and seven fixtures per adapter (SRC-FR-8).
- [x] Q: The section 13 Cost row. Rewritten as the owner's answer (owner decision, 2026-10-22).
- [x] Q: SEC-FR IDs. None: the security controls stay requirements of the platform, cache and health components, and Security owns the shared invariants (PRD-security-v2 1.7). The SEC criteria also cite SRC-FR-23 and MIG-FR-26 (PRD-security-v2 2.4, 2.5).
- [x] Q: LLD section citations. Checked against the LLD headings and corrected in sections 3 to 10, 12, 15 and 19.
- [x] Q: ADR statuses. ADRs 0001 to 0010 and 0013 accepted on 2026-10-22, 0011 and 0012 on 2026-10-19 (section 16).
- [x] Q: Which LLDs carry the SPEC-v2 0.6 rows? Section 19; none is missing.
- [x] Q: Section 15 as the approved stack. Confirmed by the owner at Gate 2 (owner decision, 2026-10-22).
- [x] Q: Section 18 ratings. Rated and ranked by the owner at Gate 2 (owner decision, 2026-10-22).
- [x] Q: Do the OUT, NFR and `<PREFIX>-FR-n` IDs match the approved PRDs? Yes after v4: superseded IDs were replaced, NFR-12 and MIG-FR-26 were added, and no ID here is absent from PRD-v7 or its component PRDs.
- [x] Q: Where do the M0 work breakdown and later milestone outlines live? In the M0 plan and the later milestone plans (section 14).

- [x] Q: Persona review of sections 9, 12 and 17. Confirmed by the `security-reviewer`, the `sre` and the `test-architect` in their own sections on 2026-10-22.

- [x] Q: A migration criterion for the INV-4 and SEC-INV-7 exception. Yes: one P1 criterion per command (`secrets import` and `scrub-client-configs` read only the client configs; only the legacy import reads the v1 folder), added in migration PRD v6 at Gate 3 (owner decision, 2026-10-22). Recording the exception in section 9 and test plan v3 section 4 is enough; the next PRD versions note it when they change (owner decision, 2026-10-22).

No question is open.

### Gate 2: Design approved

| Approver | Date | ADRs chosen | Notes |
| --- | --- | --- | --- |
| Kenny Hill (Engineering) | 2026-10-22 | 0001 to 0013, all accepted (section 16) | Approved in chat; recorded by Claude in the owner's name at his direction |
