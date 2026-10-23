---
title: "Research MCP v2 system design"
type: spec
version: 5
status: approved
approved_by: "Kenny Hill (Engineering)"
approved: 2026-10-23
owner: "Kenny Hill"
parent: docs/prd/PRD-v8.md
artifact_type: high-level-design
scope_level: L3
scope_name: "research-mcp"
supersedes: docs/spec/SPEC-v4.md
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# SPEC: Research MCP v2 system design (v5)

- **Requirements:** [PRD-v8](../prd/PRD-v8.md) (approved 2026-10-23, the successor of [PRD-v7](../prd/PRD-v7.md)) and its component PRDs: [platform v4](../prd/components/PRD-platform-v4.md), [sources v5](../prd/components/PRD-sources-v5.md), [search v3](../prd/components/PRD-search-v3.md), [cache v4](../prd/components/PRD-cache-v4.md), [health v4](../prd/components/PRD-health-v4.md), [ui v4](../prd/components/PRD-ui-v4.md), [migration v6](../prd/components/PRD-migration-v6.md) and [security v3](../prd/components/PRD-security-v3.md). Migration v6 and security v3 reopened Gate 1 and were approved on 2026-10-23; the others are the versions approved on 2026-10-22.
- **Detail:** the component LLDs in [docs/lld/](../lld/): `LLD-platform-v2`, `LLD-sources-v2`, `LLD-search-v2`, `LLD-cache-v2`, `LLD-health-v2` and `LLD-security-v2`, `LLD-ui-v2` and `LLD-migration-v2` (approved at Gate 3, 2026-10-23; section 19). Section 19 says which LLD carries which part of SPEC-v2.
- **Contracts:** [envelope and errors v1](../contracts/envelope-and-errors-v1.md), [source adapter v1](../contracts/source-adapter-v1.md), [cache tools, archive sidecar and rebuild report v1](../contracts/cache-tools-and-sidecar-v1.md), [health status, doctor output and webhook payload v1](../contracts/health-status-and-webhook-v1.md), [prompts v3](../contracts/prompts-v3.md) (approved at Gate 3, 2026-10-23, except prompts v3, which keeps its own status).
- **Tests:** [test plan v4](../test/test-plan-v4.md).
- **Decisions:** [ADRs 0001 to 0013](../adr/) (section 16).

## Provenance and changes

**Changes in v5** (draft, 2026-10-22). This version follows the Gate 3 design work and the two reopened component PRDs, and keeps only what belongs at system level; component detail stays in the LLDs. Each item is an owner decision of 2026-10-22 unless it says otherwise.

- Section 2: the unauthenticated surfaces are `/healthz`, `/readyz` and `/ui/login`; `/ui/static/*` needs a UI session; one deny-by-default `AuthGate` in `app.py` stands in front of every mount (SEC-INV-2; SEC-29, SEC-32).
- Section 3: the `AuthGate` and in-tree-only adapters are architecture rules.
- Section 4: adapters are in-tree only (no entry-point discovery); `docs_site` delivers `get`, the allowlist and `robots.txt` in M1, and `search` and `crawl` in M2; a web source also needs `enabled = true`.
- Section 5: `cite` needs the optional `cite` extra.
- Section 6: a PDF fetch without the `pdf` extra reports `unconfigured`.
- Section 7: critical has two meanings, row severity and `install_critical`.
- Section 9: tool results are redacted at the tool boundary (SEC-28); the webhook accepts https, or http on loopback (SEC-31); the exception to INV-4 and SEC-INV-7 now has a read set per command (MIG-FR-27).
- Section 10: the Drive copy of backups is built behind `backup.drive_copy`, default off; schema additions are recorded by pointer.
- Section 12: optional extras, the upgrade rollback rule, the Drive copy and `restore-client-configs`.
- Section 14: milestone placement of the new criteria and of `docs_site`.
- Sections 17 and 19: new IDs SEC-28 to SEC-32, MIG-FR-27 and MIG-27 to MIG-35, pointers to the new PRD and LLD versions, and the LLD work still due.
- Section 9 (owner decisions, 2026-10-22 and 2026-10-23): the scrub backup folder is fixed; the `import-legacy` read of the v2 `cache.db` is confirmed; client config files read by scrub are named; `retire-v1 --confirm` joins the read-set table (MIG-FR-26; MIG-35).
- Sections 16 and 20: no ADRs for `AuthGate`, in-tree adapters or the Drive backup copy (owner decision, 2026-10-23); section 20 has no open question left.
- Sections 17 and 19: pointers move to test plan v4; PRD-v8 IDs verified.

Sections 9, 12 and 17 are owned by the `security-reviewer`, the `sre` and the `test-architect`; the v5 edits there are the architect's draft of the owner's answers and need those personas' review.

**Changes in v4** (Gate 2 draft, 2026-10-22). This version follows the approved [PRD-v7](../prd/PRD-v7.md), its component PRDs and [test plan v3](../test/test-plan-v3.md); where SPEC-v3 disagreed with an approved PRD, the PRD wins. It records the owner's Gate 2 answers: the section 13 Cost row, section 15 confirmed as written, and the section 18 risks rated and ranked (owner decision, 2026-10-22). It applies the Gate 1 decisions: 45 sources and seven fixtures per adapter (sections 2, 4, 17); MCP clients only through the stdio shim (section 2); `cite` in M1 (section 14); ADRs 0001 to 0013 accepted (section 16); the source states `budget_exhausted` and `not_needed` (sections 5, 11.1); token rotation from the CLI only, UI polling, job retry and read-only site sets (sections 8, 12); the placeholder contact address and the generated inventory (section 4); backup and log retention (sections 10, 12); the scrub backup exception (sections 9, 10, 17); and the rollout halt conditions (section 12). It also records the decisions of that round (owner decision, 2026-10-22): an exception to INV-4 and SEC-INV-7 for owner-run migration commands, scoped per command; the scrub backups live outside v2's config, Application Support and log folders and never in a synced folder (section 9); the accepted residual risk that same-user processes sit inside trust boundary 2 (section 9); OC-14 in the M1 gate and the "No secret at rest" cross-cutting row (section 17); and test plan v3. History note: superseded requirement IDs were replaced by their successors (PLAT-FR-16 by PLAT-FR-59; SRC-FR-11, SRC-FR-13 and SRC-FR-16 by SRC-FR-24, SRC-FR-25 and SRC-FR-26; SRCH-FR-4 and SRCH-FR-10 by SRCH-FR-27 and SRCH-FR-28; UI-FR-5 and UI-FR-19 by UI-FR-20 and UI-FR-21; MIG-FR-23 by MIG-FR-25), MIG-FR-26 is new, and the source state `skipped_budget` of SPEC-v3 11.1 is now `budget_exhausted` (SRCH-FR-27).

**Changes in v3.** Version 3 moved the high level design onto the spec-driven development framework ([ADR 0013](../adr/0013-adopt-spec-driven-development.md); the current standard is [v3](../standards/spec-driven-development-v3.md)). Sections 1 to 14 carry over [HLD-v3](../../docs-archive/design/HLD-v3.md) with the same numbers and titles, so documents that cite "HLD section N" still match; only references were updated (SPEC v1 and v2 sections now point to the LLD that holds them, requirement and criterion IDs use the SDD scheme). The architecture parts of [SPEC-v2](../../docs-archive/spec/SPEC-v2.md) (conventions in its section 1) moved to section 15; its detailed contracts moved to the LLDs. Sections 15 to 20 follow the [SPEC template](../templates/SPEC-template.md).

ID scheme used here: `FR-<AREA>-nn` became `<PREFIX>-FR-n`, `NFR-nn` became `NFR-n`, goals `Gn` became `OUT-n`, and acceptance tests `AT-<AREA>-nn` became criteria `<PREFIX>-n` (`AT-SEC-nn` became `SEC-n`). Leading zeros are dropped.

Carried from HLD-v3, changes from its v2: owner decisions of 2026-10-19, second round ([ADR 0012](../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md)): the design is domain-neutral (topic coverage is configuration); every endpoint v1 calls is kept; web search returns as an optional, capped source group (`web`: Vertex AI Search, Brave, SerpAPI, Programmable Search) that runs only on request, in fallback order by default (sections 4, 5 and 9). M0 is unchanged.

Carried from HLD-v3, earlier changes (v2): owner decisions of 2026-10-19: cache retention is **120 days** instead of 30, and **archiving keeps a paper searchable**: only the PDF moves to Google Drive; extracted text, chunks, full-text entries and embeddings stay in `cache.db`, and a rebuild job can re-import the archive from Drive. See [ADR 0011](../adr/0011-archive-keeps-text-searchable-120-day-retention.md).

## 1. Scope

> **Owner:** C · **Persona:** `architect`

This document describes the shape of v2: the processes, the main components and how they talk, the data each owns, the security boundaries, and the key flows. Module names, schemas, signatures and interfaces are in the component LLDs (`docs/lld/LLD-<component>-vN.md`) and the contracts in `docs/contracts/`; section 19 maps each component to its LLD. The M0 work breakdown is in the [M0 plan](../build/M0-plan-v1.md) (section 14).

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
 |  AuthGate (app.py, deny by default) in front of every mount          |
 |  MCP endpoint /mcp  |  UI /ui  |  /healthz /readyz /api/status       |
 |  services: federation, works, cache, health, notify, jobs, scheduler |
 |  source registry (45 sources)  |  shared async HTTP client           |
 |  stores: state.db, cache.db  |  workers (one subprocess per task)    |
 +---+--------------+-----------------+-----------------+--------------+
     |              |                 |                 |
     v              v                 v                 v
 Upstream APIs   macOS Keychain   Google Drive sync   macOS notifications,
 (arXiv, OpenAlex (secrets,       folder (archive;   OpenClaw inbox webhook
 Crossref, ...,   read only)      backup copy off
 upstream MCPs)                   by default)
           ^
           | doctor (launchd: liveness every 15 min, full check daily; independent of the daemon)
```

MCP clients connect only through the stdio shim. Loopback streamable HTTP is the transport between the shim and the daemon, and the UI's transport: the owner's browser reaches `/ui` on `127.0.0.1` with a UI session, and the CLI reaches `/api` with the bearer token (for example to mint a UI login token). No MCP client is offered direct loopback HTTP, and no client holds the daemon token (PRD-v8 1.2, NFR-1; PLAT-FR-2; SEC-INV-10).

**Authorization point.** One deny-by-default gate, `AuthGate`, in `app.py` stands in front of every mount. It checks Host and Origin on every path (SEC-12), classifies each path, and accepts only the credential its class allows; a route with no explicit class is refused with 401 (owner decision, 2026-10-22; PLAT-FR-3; SEC-11). The classes are:

| Surface | Credential | Source |
|---|---|---|
| `/healthz`, `/readyz` | None (the only fixed unauthenticated shapes) | SEC-INV-2; HLTH-FR-43 |
| `/ui/login` | A valid one-time login token; on success it sets a UI session. A `next` value is followed only if it is a path under `/ui/` | SEC-INV-2; UI-FR-2; SEC-29 |
| `/ui/static/*` and every other `/ui` page | A UI session (CSRF token on writes) | SEC-INV-2; UI-FR-3; SEC-32 |
| `/mcp`, `/api` | The bearer token | PLAT-FR-3; SEC-11 |
| `/api/status` | The bearer token or a UI session | HLTH-FR-43 |

The UI session check and the CSRF check stay in `ui/`; the gate owns the bearer check and the Host and Origin check (owner decision, 2026-10-22). PRD-v7 NFR-7 named only `/healthz` and `/readyz`; PRD-v8 NFR-7 carries the wording of [PRD-security-v3](../prd/components/PRD-security-v3.md) 2.5 (verified).

Trust boundaries:

1. **Upstream content is untrusted.** Everything that comes from an API or a downloaded file is data; it is labeled untrusted when returned to a model.
2. **Local callers are authenticated.** Only the shim (with the bearer token it reads from the Keychain) and the UI (with a session) can call the daemon; the CLI uses the same bearer token. The only unauthenticated requests are the ones in the table above.
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
- Adapters translate only; they never retry, sleep, read secrets or write files ([ADR 0006](../adr/0006-source-adapter-contract.md)). Adapters are in-tree only: the registry discovers modules under `sources/`, and installed packages cannot add adapters to the daemon that holds the secrets cache (owner decision, 2026-10-22; section 4).
- Tools are thin: validate arguments, call one service, wrap the result in the envelope. The tool boundary redacts every string in a successful result (SEC-28).
- One composition root, `build_app(settings)`, creates everything inside a lifespan. Nothing happens at import. It mounts `AuthGate` in front of every route (section 2).
- Network I/O is async; CPU-heavy work (PDF parsing, chunking, embedding) runs in one short-lived subprocess per task, killed on timeout or memory limit; SQLite access runs in a thread with one writer per database.

**Detail:** the MCP transport and composition root in [LLD-platform-v2](../lld/LLD-platform-v2.md) §2.3 (from SPEC-v2 section 7.4); the gate in §4.5 and [LLD-security-v2](../lld/LLD-security-v2.md) §5.2; conventions and package layout in §5.1 (from SPEC-v2 section 1); layers in §5.2 (from HLD-v3 section 3); workers, jobs and the scheduler in §5.5 (from SPEC-v2 section 3.6); the stdio shim in §5.7. Requirements: PLAT-FR-1 to PLAT-FR-6; NFR-1, NFR-2.

## 4. Sources

> **Owner:** C · **Persona:** `architect`

- A **`SourceSpec`** declares each source: capabilities, identifier schemes, auth (including its Keychain names and signup URL), rate policy, timeouts, page size, extras, probe, shutdown date, default enabled.
- An **adapter** implements `search`, `get`, `fulltext_candidates`, `citations` and `probe` for the capabilities it declares, returning normalized `WorkRecord`s with provenance.
- The **registry** discovers adapters, creates configured instances (four DSpace repositories, docs sites, Vertex AI Search engines), applies enable and disable settings, and answers "which sources can do X for group Y right now", combining configuration with live health. v2 registers 45 sources at the M1 exit (PRD-v8 OUT-1; PRD-sources-v5 1.3). Discovery is in-tree only (`pkgutil` over the `sources/` package); there is no entry-point discovery and no `sources.entry_points` setting (owner decision, 2026-10-22).
- **Upstream MCP servers** (AWS Knowledge, Microsoft Learn) are adapters that use an MCP client instead of HTTP JSON.
- **Site sets** are named domain lists in configuration (v1's docs-domain list ships as `v1_docs`). Topic coverage, in any subject area, is added by configuring docs sites, site sets and search engines, not by code. Site sets are edited in the config file or with `research-mcp config set`; the UI shows them read-only (SRC-FR-18; UI-FR-21).
- **Docs sites** (`docs_site` instances) are delivered in two steps. M1 delivers `get`, the domain allowlist and `robots.txt` handling; `search` and `crawl` arrive in M2 with the crawl jobs (owner decision, 2026-10-22; SRC-FR-15; CACHE-FR-56).
- **Web search** is the `web` group: four optional, metered sources, each off until configured and capped per day. A configured web source also needs `enabled = true`; presence of a key never enables a call. It is never in the default fan-out.
- **Contact address.** Sources that ask for a contact email get the configured owner contact. A placeholder `contact.email` (example.com, example.org, .test, .invalid) is a settings validation error with a clear message, so the daemon does not start until it is fixed; with no address set, only the `needs_contact` sources are `unconfigured` and the daemon starts (SRC-FR-24; PLAT-11).
- **Inventory and new sources.** The source inventory is generated from the registry by `tools/gen_inventory.py`, and its `--check` flag gates CI (SRC-FR-25). The `doi_resolver` helper that `cite` uses is declared by the sources component and excluded from the 45-source inventory ([LLD-search-v2](../lld/LLD-search-v2.md) §12). A new source is one adapter module, one fixtures folder and its tests; its Keychain name lives in its `SourceSpec` and the generated inventory, so the new-source checklist has no "edit the SPEC" step (SRC-FR-26).
- **Testing:** every adapter has seven recorded fixtures and runs through one conformance suite (SRC-FR-8); an opt-in live check refreshes fixtures.

**Detail:** in [LLD-sources-v2](../lld/LLD-sources-v2.md) and the [source adapter contract](../contracts/source-adapter-v1.md): the source contract and policy types in §2.1 and §2.2; discovery in §2.3; shared models in §3.1; settings keys in §3.2; default data and site sets in §3.3; fixtures on disk in §3.4; the registry in §5.2; conformance in §5.3; the live check in §5.4; the new-source checklist in §5.5 (SRC-FR-26 supersedes its step 5); upstream MCP adapters in §5.6; web sources, site sets in queries and the `web` group federation in §5.7 to §5.9; the inventory in §5.10; the docs-site allowlist and `robots.txt` in §5.11; DSpace instances in §5.12. The contact-address validation is in [LLD-platform-v2](../lld/LLD-platform-v2.md) §7.1. Requirements: SRC-FR-1 to SRC-FR-10, SRC-FR-12, SRC-FR-14, SRC-FR-15, SRC-FR-17 to SRC-FR-26 ([PRD-sources-v5](../prd/components/PRD-sources-v5.md)); OUT-1, OUT-3.

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
- **Citations, authors, cite and integrity** are services over the same registry and identity layer; they ship in M1 (PRD-v8 2.9). The `text` citation format needs the optional `cite` extra (section 12).

**Detail:** in [LLD-search-v2](../lld/LLD-search-v2.md): the tool catalog in §2.1 (from SPEC-v2 section 7.2); resources and prompts in §2.3 (SPEC-v2 7.3); identity in §5.2 and grouping in §5.3 (SPEC-v2 6); federation in §5.4 (SPEC-v2 7.1); citations, authors, `cite` and integrity in §5.7 to §5.10; search records in §5.11. The `web` group federation rules are in [LLD-sources-v2](../lld/LLD-sources-v2.md) §5.9; the envelope and budget in [LLD-platform-v2](../lld/LLD-platform-v2.md) §2.1 and §5.6 and the [envelope and errors contract](../contracts/envelope-and-errors-v1.md). Requirements: SRCH-FR-1 to SRCH-FR-3, SRCH-FR-5 to SRCH-FR-9, SRCH-FR-11 to SRCH-FR-17, SRCH-FR-20 to SRCH-FR-23, SRCH-FR-25 to SRCH-FR-28 ([PRD-search-v3](../prd/components/PRD-search-v3.md)), SRC-FR-21, SRC-FR-22, HLTH-FR-12; OUT-2; NFR-5.

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
- **Optional PDF support.** PDF extraction needs the `pdf` extra (section 12). Without it, a PDF fetch returns `unconfigured` before anything is recorded; HTML needs no extra (owner decision, 2026-10-22).
- **Collections** export through `cite` (CACHE-63).

**Detail:** in [LLD-cache-v2](../lld/LLD-cache-v2.md) and the [cache tools, sidecar and rebuild report contract](../contracts/cache-tools-and-sidecar-v1.md): tools, CLI, UI routes, notifications and the sidecar in §2; the `cache.db` schema in §3 (from SPEC-v2 section 8.1); the fetch pipeline in §5.2; extraction, chunking and embeddings in §5.3; local search in §5.4; state transitions in §5.5; the review batch in §5.6; archive in §5.7; disk and integrity in §5.8; collections in §5.9; the archive rebuild in §5.10; backups in §5.11; jobs and schedules in §5.12 (SPEC-v2 sections 8.2, 8.3, 9.1 to 9.5, 9.7 and 9.8). The downloader is in [LLD-platform-v2](../lld/LLD-platform-v2.md) §5.4 (SPEC-v2 3.4) and the workers in §5.5 (SPEC-v2 3.6); the legacy import into the cache is in [LLD-migration-v2](../lld/LLD-migration-v2.md) §5.1 (SPEC-v2 9.6). Requirements: CACHE-FR-1 to CACHE-FR-7, CACHE-FR-10 to CACHE-FR-18, CACHE-FR-20 to CACHE-FR-24, CACHE-FR-30 to CACHE-FR-38, CACHE-FR-45 to CACHE-FR-52, CACHE-FR-55 to CACHE-FR-59 ([PRD-cache-v4](../prd/components/PRD-cache-v4.md)); OUT-6.

## 7. Health, credentials and notifications

> **Owner:** C · **Persona:** `architect`

```
 HTTP client --telemetry--> state.db.calls --rollup--> source_health
 scheduler --probes--> adapters.probe() ----------------^
 secrets --metadata--> state.db.credentials <-- passive headers (GitHub expiry, rate limits)
 health.evaluate() -> source and credential states -> diff -> notify (macOS, OpenClaw webhook, UI banner)
 doctor (launchd: liveness every 15 min, full daily) -> same checks without the daemon -> notify on change
```

- **States** follow [PRD-health-v4](../prd/components/PRD-health-v4.md) section 2.4: source states HLTH-FR-10 to HLTH-FR-12 and credential states HLTH-FR-20 to HLTH-FR-25. Credential rows hold metadata only, never values (HLTH-INV-1). The Google sign-in's account address is metadata, not a secret, and sits in the credential row.
- **Notifications** fire on state changes and roll unresolved items into a daily digest, with quiet hours. The OpenClaw webhook is an `HttpClient` request with its policy limited to the configured origin, and its URL scheme is https, or http on a loopback host (SEC-31).
- **Federation** consults health before selecting sources and skips `down`, `rate_limited` and `budget_exhausted` sources (HLTH-FR-12).
- **Two meanings of critical** (owner decision, 2026-10-22). They must not be confused:
  1. *Row severity.* A status or credential row has a severity (`info`, `warning`, `critical`) that orders the board and the digest; for example a credential expiring in 3 days or fewer is a `critical` row.
  2. *`install_critical`.* A `doctor` check carries `install_critical` only when installation integrity is broken. Only `install_critical` bypasses quiet hours, makes `doctor` exit non-zero, and rolls back an upgrade (section 12). An invalid credential, a failed probe, low disk or a missing TCC permission is at most a warning there, so an expired key or a source outage never wakes the owner in quiet hours or rolls back a good upgrade.

**Detail:** in [LLD-health-v2](../lld/LLD-health-v2.md) and the [health status, doctor output and webhook contract](../contracts/health-status-and-webhook-v1.md): the HTTP endpoints, MCP surface, CLI and webhook in §2; the `state.db` schema in §3; telemetry in §5.3; probes in §5.4; state evaluation in §5.5; local targets in §5.6; credentials in §5.7; notifications in §5.8; `doctor` in §5.9; readiness and status in §5.10. Requirements: HLTH-FR-1 to HLTH-FR-5, HLTH-FR-10 to HLTH-FR-12, HLTH-FR-20 to HLTH-FR-25, HLTH-FR-30 to HLTH-FR-35, HLTH-FR-40 to HLTH-FR-43; OUT-4, OUT-5.

## 8. Local UI

> **Owner:** C · **Persona:** `architect`

- **Stack:** Starlette routes and Jinja2 templates in the daemon, with a vendored htmx file for partial refresh and confirmation dialogs ([ADR 0010](../adr/0010-localhost-ui-stack.md)).
- **Data access:** pages read the same services the MCP tools use, so there is no second API.
- **Sessions:** a session starts from a one-time token URL at `/ui/login`, which is unauthenticated except for that token; `next` is followed only under `/ui/`. Every other `/ui` path, including `/ui/static/*`, needs the session. All writes need CSRF tokens and confirmation (section 2).
- **Refresh:** pages refresh live data with `hx-get` polling every 10 seconds only (UI-FR-20).
- **Pages:** source board, credentials, quota, jobs, cache, review, archive, maintenance, events, settings. A job retry resubmits the job through `JobService.submit` with the same parameters (UI-FR-13). The Settings page shows the named site sets read-only (UI-FR-21).
- **No token rotation in the UI:** the daemon token rotates only from the CLI with `research-mcp secrets rotate-token` (PLAT-FR-59).

**Detail:** in [LLD-ui-v2](../lld/LLD-ui-v2.md) (from SPEC-v2 section 11): routes, login and session, request checks and partial refresh in §2.1 to §2.4; enforcement points in §4; files, services and pages in §5.1 to §5.3. The login, session and CSRF rule it implements is in [LLD-security-v2](../lld/LLD-security-v2.md) §5.3; the gate and the daemon token in [LLD-platform-v2](../lld/LLD-platform-v2.md) §4.5. Requirements: UI-FR-1 to UI-FR-4, UI-FR-6, UI-FR-7, UI-FR-10 to UI-FR-18, UI-FR-20, UI-FR-21 ([PRD-ui-v4](../prd/components/PRD-ui-v4.md)); OUT-8.

## 9. Security architecture

> **Owner:** C · **Persona:** `security-reviewer`

| Threat | Control |
|---|---|
| Prompt-injected model tries to read local files | No SQL tool; no caller-chosen paths; files only under the cache root; DuckDB (if used internally) locked down ([ADR 0009](../adr/0009-no-sql-untrusted-content.md)). Approved exception, scoped per owner-run migration command, with a fixed read set for each (MIG-FR-27; PRD-migration-v6 2.4): `secrets import` reads the MCP client configs and the v2 `config.toml` (for idempotence); `scrub-client-configs` reads only the client configs; `restore-client-configs` and `retire-v1 --confirm` (which deletes the scrub backups, MIG-FR-26; MIG-35) touch only the scrub-backup set; `install --print-client-config` reads nothing beyond the v2 install; only the legacy import (MIG-FR-10) reads the v1 folder (`~/arxiv-papers`, the v1 database, read only; a symbolic link that leaves the tree is refused) and the v2 `cache.db`, to merge with works already there (INV-10; MIG-INV-1; the `cache.db` read is confirmed, owner decision, 2026-10-22). The client config files scrub reads are the Claude Desktop config, `~/.claude.json` and `~/.openclaw/openclaw.json`; a symbolic link as the final path component is refused. A read of any other path is refused with an error that names the path (MIG-30). The CLI's own read of `config.toml` and the daemon's own opens of `state.db` are not migration reads and stay outside the per-command sets. MCP tools and anything an agent can trigger stay bound by INV-4 and SEC-INV-7. It is recorded in [test plan v4](../test/test-plan-v4.md) section 4, not a PRD change (owner decision, 2026-10-22). |
| Prompt-injected model tries to delete data | No hard delete in MCP; the only MCP discard is a review decision inside an open batch, recorded as an agent decision, sent to a 7-day trash and announced to the owner at once with an undo link; the owner is notified again 24 hours before any purge; annotations mark state-changing tools. |
| Secret leaks into chat or logs | Keychain (the Google sign-in and the scrub backups excepted, see below); `Secret` type; origin-scoped attachment; header placement; one redaction filter on logs, errors, UI and notifications; every string in a successful tool result is redacted at the tool boundary (SEC-28); errors carry codes, not exception text. |
| Paid web-search spend runs away | Web sources off until configured, never in the default fan-out, fallback order (one paid query per page), daily caps that switch a source to `budget_exhausted`. |
| Google sign-in token misuse | `gcloud` owns the sign-in; v2 holds only a short-lived access token in memory and attaches it only to `discoveryengine.googleapis.com`. |
| Plaintext v1 keys in scrub backups | An approved exception to INV-6, NFR-3 and SEC-INV-3 (not SEC-INV-6) until v1 is retired: `scrub-client-configs` writes each backup owner-only (mode 0600); the backups serve only to restore the v1 entries on rollback with `restore-client-configs`; retiring v1 deletes them (PRD-v8 1.5; MIG-FR-25, MIG-FR-26; MIG-25, MIG-26). The backups live outside v2's config, Application Support and log folders, so SEC-24 and the NFR-3 scan apply without exception, and never inside a synced folder (Google Drive, iCloud), so the keys never leave the Mac; the folder is `~/.research-mcp-migration/scrub-backups/` (mode 0700, files 0600), set in LLD-migration-v2 section 3 (owner decision, 2026-10-22). |
| SSRF and hostile downloads | One downloader: https, per-hop host policy, public IPs only with the connection pinned to the checked IP (no second DNS lookup), byte cap, magic bytes, atomic write. |
| Hostile PDFs | Parsing in a separate subprocess per document with a CPU limit, an RSS watchdog, a wall-clock timeout and a page cap; a crash affects only that document. |
| Other local processes call the daemon | Loopback only; one deny-by-default `AuthGate` in `app.py` in front of every mount, with the bearer token, Host and Origin checks on all paths; UI session cookie plus CSRF. The only requests answered without a credential are `/healthz`, `/readyz` and `/ui/login` (which needs its one-time token); `/ui/static/*` needs a UI session (SEC-INV-2; SEC-11, SEC-12, SEC-29, SEC-32). MCP clients reach the daemon only through the stdio shim, which reads the token from the Keychain; no client holds it (SEC-INV-10; SEC-26). Accepted residual risk: any process running as the owner can launch `research-mcp stdio` or read the Keychain item without a prompt, so same-user code sits inside trust boundary 2; SEC-INV-10 keeps the token out of client configs, not away from same-user processes. This is accepted on one personal Mac (owner decision, 2026-10-22). |
| Daemon token exposed | The token is 32 random bytes in URL-safe base64, 43 characters (SEC-30), and rotates only from the CLI with `research-mcp secrets rotate-token`, never from the UI; the new value is written through `security -i` on stdin (PLAT-FR-59; SEC-13). |
| Webhook sends a token to a bad URL | The webhook URL must be https, or http on a loopback host; the request goes through the origin-scoped HTTP client (SEC-31; SEC-INV-5). |
| Third-party code runs in the daemon | Adapters are in-tree only; there is no entry-point discovery (section 4). |
| Backup data leaves the Mac | The Drive copy of backups is behind `backup.drive_copy`, default off; with it off, no personal data leaves the Mac by that path (owner decision, 2026-10-22; section 10). |
| Upstream drift returns wrong data | Probes check response shape; fixtures pinned in tests; per-source disable. |
| Supply chain | Lock file, weekly dependency audit, SHA-pinned CI actions, secret scan. |

Two exceptions keep secrets outside the Keychain. The owner's Google sign-in is a standing exception written into INV-6 and SEC-INV-3: `gcloud` stores it and v2 never copies it (ADR 0012; SEC-INV-11). The scrub backups hold many v1 keys and are a time-boxed exception outside that text, lasting until v1 is retired (PRD-v8 1.5; MIG-FR-26). INV-6 and SEC-INV-3 themselves are unchanged.

The Security component owns the shared invariants SEC-INV-1 to SEC-INV-11 and defines no `SEC-FR` IDs: the controls stay requirements of the platform, cache, health, sources (SRC-FR-23) and migration (MIG-FR-26, MIG-FR-27) components, and the SEC criteria cite them (PRD-security-v3 1.7, 2.4).

**Detail:** trust boundaries, the threat model, enforcement points and invariant coverage in [LLD-security-v2](../lld/LLD-security-v2.md) §4.1 to §4.4; the daemon token and gate in §5.2, the UI login, session and CSRF rule in §5.3, redaction call sites in §5.4, and scrub backups and migration reads in §5.5. Secrets, the Google sign-in and redaction are owned by [LLD-platform-v2](../lld/LLD-platform-v2.md) §4.1 to §4.3; credential scoping and the HTTP client in §4.4 and §5.3; loopback, the gate, the daemon token and endpoints in §4.5; local files and destructive actions in §4.6; the downloader in §5.4; the tool boundary in §5.6; the scrub backups in [LLD-migration-v2](../lld/LLD-migration-v2.md) §5.3. Requirements: [PRD-security-v3](../prd/components/PRD-security-v3.md), criteria SEC-1 to SEC-14 and SEC-20 to SEC-32, invariants SEC-INV-1 to SEC-INV-11; MIG-FR-26, MIG-FR-27; OUT-7; NFR-3, NFR-4, NFR-6, NFR-7.

## 10. Data stores

> **Owner:** C · **Persona:** `architect`

| Store | Location | Owns | Backed up |
|---|---|---|---|
| `state.db` (SQLite, WAL) | `~/Library/Application Support/research-mcp/` | Credential metadata, source health, call telemetry and rollups, searches, jobs, schedule runs, notifications, review batches and a copy of review events | Nightly, the last 7 kept |
| `cache.db` (SQLite, WAL, FTS5, vector BLOBs) | `~/Library/Application Support/research-mcp/cache/` | Works, identifiers, source records, documents and lifecycle (including pins, decisions and archive paths), files, extractions, chunks, FTS, embeddings, collections, outbox | Nightly, the last 7 kept |
| Files | `~/Library/Application Support/research-mcp/cache/files/` (by SHA-256) and `trash/` | Cached PDFs and HTML | No (re-fetchable; archived copies live in Drive) |
| Model cache | `~/Library/Caches/research-mcp/models/` | Embedding model files | No (re-downloadable) |
| Archive | Drive sync folder `My Drive/Research Archive/<year>/` | Archived files and sidecars (their text stays in `cache.db`) | By Google Drive; also the source for the archive rebuild job |
| Backup copy (optional) | Drive sync folder `My Drive/Research Archive/_state/<date>/` | A copy of the day's local backup, written only when `backup.drive_copy` is on (default off) | By Google Drive; pruned to the same count as the local backups |
| Config | `~/.config/research-mcp/config.toml` | Settings and secret references | Nightly with `state.db` |
| Logs | `~/Library/Logs/research-mcp/` | JSON lines, redacted | No; `research-mcp.jsonl` rotated by size, 5 files of 10 MB; `daemon.err.log` rotated by the platform design (PLAT-FR-40) |
| Secrets | macOS login Keychain, `research-mcp/<NAME>` | Credential values and the daemon token | By Keychain |
| Scrub backups (temporary) | Outside the config, Application Support and log folders and outside any synced folder: `~/.research-mcp-migration/scrub-backups/` (0700) | Plaintext copies of the v1 client configs, mode 0600 | No; deleted at v1 retirement |

Nothing the lifecycle depends on lives in `~/Library/Caches`, which macOS and cleaning tools may purge. Both databases are backed up nightly and the last 7 backups are kept (PLAT-FR-57); only re-fetchable files are not. The Drive copy of the backups is built behind the flag `backup.drive_copy`, default off; it runs only after the local backup is verified, writes only to `_state/`, never uses the local archive fallback, and is skipped with a warning when the archive target is unavailable (owner decision, 2026-10-22; PLAT-FR-57; OC-10). The scrub backups of the v1 client configs are the one temporary store of plaintext keys outside the Keychain; they are owner-only and deleted when v1 is retired (section 9; MIG-FR-26).

This SPEC does not carry column definitions. The schema additions of the Gate 3 designs are all part of migration `0001_init`, which no code has created yet: `searches.filters_json` ([LLD-search-v2](../lld/LLD-search-v2.md) §3), `chunks.title` (indexed by the chunk full-text table), `documents.pin_direct` and `documents.integrity_at_fetch` ([LLD-cache-v2](../lld/LLD-cache-v2.md) §3.2), `disk_samples.model_cache_bytes` (cache §3.2 and [LLD-health-v2](../lld/LLD-health-v2.md) §3), and `credentials.account` (health §3). Owner decisions, 2026-10-22.

**Detail:** settings and paths in [LLD-platform-v2](../lld/LLD-platform-v2.md) §7.1 (from SPEC-v2 section 2) and §3.2; stores and migrations in §3.1 (SPEC-v2 3.5); backups in §3.3 (the contract and the `backup.drive_copy` key) and [LLD-cache-v2](../lld/LLD-cache-v2.md) §5.11 (SPEC-v2 9.8); logging in LLD-platform-v2 §4.3, §5.10 and §8; `cache.db` in LLD-cache-v2 §3 (SPEC-v2 8.1); `state.db` in LLD-health-v2 §3 (SPEC-v2 10.1). Requirements: PLAT-FR-8, PLAT-FR-9, PLAT-FR-40, PLAT-FR-56, PLAT-FR-57, CACHE-FR-59.

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

1. At 09:00 the scheduler finds 6 documents expiring within 3 days and creates a review batch.
2. The owner gets one macOS notification.
3. Clicking it opens the batch page under `/ui/review/`. The owner archives 2, discards 3 and leaves 1 unanswered.
4. The archive job copies 2 files plus sidecars to Drive, verifies them, and removes the cached PDFs; both papers stay searchable through their text in `cache.db`.
5. The 3 discards go to the trash for 7 days.
6. When the batch closes 24 hours later, the unanswered item becomes `kept` and is asked about again 7 days later.

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
| **Optional extras** | Heavy or optional dependencies are extras, kept out of the base install (PLAT-FR-51; PLAT-4): `pdf` (PDF extraction; without it a PDF fetch reports `unconfigured`, section 6) and `cite` (`citeproc-py`, for the `text` citation format; the package choice is an assumption to confirm at build). The full extras list is in [LLD-platform-v2](../lld/LLD-platform-v2.md) §5.8 (owner decision, 2026-10-22). |
| **Upgrade** | `research-mcp upgrade` writes a pre-upgrade backup, replaces the environment and rolls back, restoring both databases, only when a `doctor` check is `install_critical` or the daemon is not ready (PLAT-FR-55; section 7). A warning-level `doctor` result does not roll back (owner decision, 2026-10-22). |
| **Daemon token** | Generated at install; rotated only from the CLI with `research-mcp secrets rotate-token`, never from the UI (PLAT-FR-59; PLAT-83; SEC-30). |
| **Logs** | JSON lines in `~/Library/Logs/research-mcp/research-mcp.jsonl`, rotated by size: 5 files of 10 MB; stderr receives warnings and errors only (PLAT-FR-40). The UI's Events page shows recent warning and error lines, redacted (UI-FR-18; HLD-v3 12). launchd also writes the daemon's stderr to `daemon.err.log` in the same folder; `RotatingFileHandler` does not rotate that file, and the platform LLD designs its rotation ([LLD-platform-v2](../lld/LLD-platform-v2.md) §2.5, §5.10). |
| **Availability** | Best effort on one Mac: launchd KeepAlive restarts the daemon when it exits, and the watchdog (`doctor --liveness --notify`, every 15 minutes) reports a dead daemon within 15 minutes. There is no uptime percentage and no response target (NFR-12; OUT-4; HLTH-FR-41; PRD-v8 2.6). |
| **Backups** | Nightly copy of `state.db`, `cache.db` and the config; the last 7 are kept (PLAT-FR-57; CACHE-49). The optional copy to `Research Archive/_state/` in Drive is built behind `backup.drive_copy`, default off (owner decision, 2026-10-22; section 10; OC-10). |
| **Parallel run with v1** | v1 stays installed and read-only under its old client entry, disabled (not deleted) at cutover, until retirement ([ADR 0001](../adr/0001-new-repo-v1-read-only.md); MIG-FR-21; INV-10). |
| **Cutover and rollback** | Cutover (M4) adds the v2 entry `research` to each client config and disables the v1 entry. Rollback re-enables the v1 entry; after `scrub-client-configs`, it also runs `research-mcp restore-client-configs`, which restores the scrubbed values from the scrub backups and reads only them, because v1 does not read the Keychain (MIG-FR-25; MIG-31). Rollback is available only before retirement: retiring v1 deletes the scrub backups, after which it cannot be done (PRD-migration-v6 1.5; MIG-FR-26). The steps are in the [cutover runbook](../runbooks/migration-cutover-v2.md). |
| **Halt conditions** | The rollout halts on any deletion without a recorded owner decision (INV-1), any secret in an output (INV-2), a fallback to v1 during the 14-day window, or any other invariant breach (INV-3 to INV-10, or a component invariant `<PREFIX>-INV-n`), and on a blocking issue during parallel use (runbook step 7). The owner is the only responder (PRD-v8 2.6; PRD-migration-v6 2.9). |
| **Retirement** | v1 is retired only after 14 days of daily use on v2 with no fallback and the owner's explicit go-ahead; a fallback restarts the 14-day count (PRD-migration-v6 2.8). Retiring v1 removes the v1 entries, archives the v1 repository and deletes the scrub backups with `research-mcp retire-v1 --confirm` (MIG-FR-24, MIG-FR-26; MIG-35). |

**Detail:** in [LLD-platform-v2](../lld/LLD-platform-v2.md): the CLI in §2.4 and packaging and CI in §5.8 (from SPEC-v2 section 12.1); launchd templates in §2.5 and install and upgrade in §5.9 (SPEC-v2 12.2); the daemon start, credential reload and log rotation in §5.10; logging in §4.3 and §8; backups in §3.3 and [LLD-cache-v2](../lld/LLD-cache-v2.md) §5.11 (SPEC-v2 9.8). In [LLD-migration-v2](../lld/LLD-migration-v2.md): the legacy import in §5.1 (SPEC-v2 9.6); the credential and settings import in §5.2; scrub, restore, the client config printer and cutover in §5.3 (MIGRATION-v2, via the [cutover runbook](../runbooks/migration-cutover-v2.md)). Requirements: PLAT-FR-40 to PLAT-FR-42, PLAT-FR-50 to PLAT-FR-59, MIG-FR-1 to MIG-FR-6, MIG-FR-10 to MIG-FR-15, MIG-FR-20 to MIG-FR-22, MIG-FR-24 to MIG-FR-27 ([PRD-migration-v6](../prd/components/PRD-migration-v6.md)), HLTH-FR-41; OUT-4; NFR-12; rollout conditions in PRD-v8 2.6 and PRD-migration-v6 2.9.

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
| M0 | core, platform (settings, secrets, HTTP, downloader, stores, logging, jobs, scheduler), the `AuthGate`, the daemon token format (SEC-30), sources (contract, registry, arXiv, Crossref, OpenAlex), federation, tools `search`, `get_work`, `list_sources`, daemon, shim, install, CI |
| M1 | all other adapters, for 45 sources registered at the exit (PRD-v8 OUT-1); `docs_site` with `get`, the allowlist and `robots.txt` only; citations, authors, `cite` and integrity (PRD-v8 2.9; SRCH-32); health, credentials, quota tracking, notifications, doctor |
| M2 | workers, extraction, `fetch`, `read`, `search_cache`, embeddings, cache lifecycle, review, searchable archive and its rebuild job, collections (with export through `cite`), `docs_site` `search` and crawl jobs, disk and integrity checks, redaction of tool results at the tool boundary (SEC-28) |
| M3 | UI, with the `/ui/login` `next` rule, the `/ui/static/*` session rule and the webhook scheme rule (SEC-29, SEC-32, SEC-31) |
| M4 | secrets import, legacy import, client cutover, `restore-client-configs`, the migration read sets (MIG-FR-27), v1 retirement (which deletes the scrub backups) |

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

Further stack choices already recorded as decisions: macOS Keychain for secrets ([ADR 0003](../adr/0003-secrets-in-keychain.md)); two SQLite files with FTS5 and vectors in SQLite ([ADR 0008](../adr/0008-sqlite-stores-and-vectors.md)); Starlette, Jinja2 and htmx for the UI ([ADR 0010](../adr/0010-localhost-ui-stack.md)). Dependencies, extras and tool settings are in [LLD-platform-v2](../lld/LLD-platform-v2.md) §5.8 (from SPEC-v2 section 12.1).

**Architectural rules** (from AGENTS.md):

- Adapters (`src/research_mcp/sources/`) only translate: no HTTP library imports, no sleeping, no retries, no secrets, no file writes.
- No tool may block the event loop; CPU work goes to worker subprocesses (`platform/workers.py`).
- Tests pass with the network blocked; use `FakeProvider`, recorded fixtures and the fakes in `research_mcp.testing`.
- Never print, log, commit or put in fixtures any secret, token or password. Fixtures are recorded with credentials removed.
- Every change needs tests.

## 16. Key decisions

> **Owner:** C · **Persona:** `architect` drafts ADR options; the owner decides · **Seed question:** 10

Statuses as recorded in PRD-v7 1.6 on 2026-10-22 (PRD-v8 1.6 is to carry them forward). ADR 0007's file title still says "30-day cache"; ADR 0011 amends it to 120 days.

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

v5 adds no listener, store, trust boundary or external dependency beyond the optional Drive backup copy, which is off by default. The owner's answers on the `AuthGate`, in-tree-only adapters and the Drive backup copy are recorded in sections 2, 4 and 10; no ADR is written for them (owner decision, 2026-10-23).

## 17. Testing strategy

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 2

Aligned with [test plan v4](../test/test-plan-v4.md); drafted by the `architect` for review by the `test-architect`. How each criterion is verified is in the test plan; per-criterion coverage is generated in `docs/trace/coverage.md`.

**Test levels and environments** (test plan v4 1.1):

| Level | Runs | Network | External systems |
|---|---|---|---|
| unit | every work unit and commit (`tools/ci.sh --python-only`) | blocked | none |
| integration | every commit | blocked | fakes from `research_mcp.testing`: `httpx.MockTransport` with recorded fixtures, `FakeProvider`, `FakeClock` and fake sleeper, fake `launchctl`, fake notifier, injected resolver, temp folders for Drive |
| contract | every commit | blocked | in-memory MCP client (`mcp.shared.memory`) against `build_mcp` |
| live | opt-in (`pytest -m live`), nightly on the Mac later | allowed | real upstreams, no credentials unless the owner runs it locally |

Network blocking: `tests/conftest.py` installs a socket guard that fails any test opening a non-loopback connection unless it is marked `live`; `pyproject.toml` deselects `live` tests by default (`-m 'not live'`). Tests run with `--import-mode=importlib`; test folders have no `__init__.py`.

Secrets in tests: only `FakeProvider` with generated values; the security suite registers those values with the redactor and scans every output.

Fixtures: every adapter has seven recorded fixtures in `tests/sources/<id>/fixtures/` (SRC-FR-8; test plan v4 1.3). Other fakes and fixtures (synthetic v1 database, hostile PDF corpus, temp Drive folder, `FakeLaunchctl`, `FakeNotifier`) are in test plan v4 1.3. The migration read-set criteria (MIG-27 to MIG-35) run in a fake home with decoy files outside each command's read set.

**Cross-cutting criteria that every milestone keeps green** (test plan v4 1.2, with the v5 additions):

| Area | Rule | Criteria |
|---|---|---|
| No secret in any output | Logs, errors, tool results, UI pages, notifications and process argument lists never contain a registered secret | SEC-1, SEC-5, SEC-6, SEC-7, SEC-9, SEC-10, SEC-13, SEC-14, SEC-28, HLTH-32, HLTH-34, UI-4, MIG-22 |
| No secret at rest | No registered secret is stored in configuration, Application Support or log files, and credentials are kept as metadata only | SEC-24, SEC-27, SEC-30, HLTH-43, MIG-23 |
| Loopback and auth | Nothing binds beyond loopback; every request is authenticated except `/healthz`, `/readyz` and `/ui/login`; `/ui/static/*` needs a session | PLAT-10, PLAT-71, SEC-11, SEC-12, SEC-26, SEC-29, SEC-31, SEC-32, UI-2, UI-3, UI-20 |
| Async discipline | The event loop never blocks | PLAT-75, SRCH-1, ruff ASYNC rules |
| Bounded output | No result exceeds the budget | PLAT-31, PLAT-63 |
| Untrusted content | Fetched text is always enveloped | PLAT-33, SEC-22 |
| Adapter isolation | Adapters do no I/O of their own | SRC-7, conformance |
| No silent deletion | Nothing is deleted without an owner decision; MCP discards are announced; shared files survive | CACHE-33, CACHE-34, CACHE-36, CACHE-48, SEC-20 |
| Migration read boundary | Each owner-run migration command opens only its read set | MIG-27 to MIG-35 |
| Docs follow code | The generated inventory and plan are current and the trace check passes | SRC-13, `node tools/sdd/cli.mjs check` in CI |

The "No secret at rest" area is new in test plan v3 (owner decision, 2026-10-22); the "Migration read boundary" area and the SEC-28 to SEC-32 entries are new in v5 and are in test plan v4.

**Milestone exit gates** (test plan v4 1.4; owner checks OC-01 to OC-14 are in test plan v4 section 3 and are not criteria):

| Milestone | Gate |
|---|---|
| M0 | Every M0 criterion in the [M0 plan](../build/M0-plan-v1.md) has a passing test that cites it; full `tools/ci.sh` green, including `node tools/sdd/cli.mjs check` (lint, strict mypy, coverage 85% on `src/`, build, `--help`); owner checks OC-01 and OC-02. SEC-24, SEC-26, SEC-30, SRCH-37 and SRCH-38 are M0 criteria with no unit in the M0 plan, so they do not gate M0 until the `planner` assigns them (test plan v4 section 5, item 4). |
| M1 | All M1 tests pass; 45 or more sources registered and passing conformance (PRD-v8 OUT-1); OC-03, OC-08 (once a remote exists), OC-11, OC-12, OC-14 (owner decision, 2026-10-22). |
| M2 | All M2 tests pass, including the hostile PDF corpus and SEC-28; OC-04, OC-10 and OC-13. |
| M3 | All M3 tests pass, including SEC-29, SEC-31 and SEC-32; OC-05 and OC-09. |
| M4 | All M4 tests pass, including MIG-27 to MIG-35; OC-06 then OC-07. |

**Exceptions** (test plan v4 section 4):

- INV-6 and NFR-3 are excepted for the scrub backups written by `scrub-client-configs` only, until v1 retirement, when MIG-26 deletes them. The exception is partial, so INV-6 and NFR-3 keep their tests otherwise, and MIG-25 and MIG-26 check the backups' permissions and deletion (owner decision, 2026-10-22 at Gate 1; MIG-FR-26).
- INV-4 and SEC-INV-7 are excepted for owner-run migration commands only, per command, until v1 retirement, each with the read set in section 9 (MIG-FR-27). MCP tools and agent-triggered actions stay bound by INV-4 and SEC-INV-7, so their tests (SEC-25, CACHE-11) are unchanged. MIG-27 to MIG-35 check each read set and the refusals (owner decision, 2026-10-22).

## 18. Risks and mitigations

> **Owner:** A · **Persona:** `architect`; the owner ranks them at Gate 2

The owner rated and ranked these risks at Gate 2 (owner decision, 2026-10-22); the rows are in rank order, highest first. v5 adds no risk row; the exposure of the optional Drive backup copy is controlled by its default of off (section 10).

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Upstream APIs change faster than one person can follow (PRD-v8 2.10). | High | Medium | Probes check response shape, not just status; recorded fixtures make breakage visible in tests; each source can be disabled with a flag (sections 4, 7, 9). |
| Drive sync folder unavailable, blocked by macOS privacy controls, or not uploading (PRD-v8 2.10). | Medium | High | Install performs the first archive write in the foreground so the privacy prompt appears; `doctor` checks access; local fallback with a warning and reconcile; nothing leaves the cache until the archive copy is verified; upload state is checked and a stalled upload is reported (sections 6, 12). |
| Scope creep toward a library manager (PRD-v8 2.10). | Medium | Medium | Non-goals in PRD-v8 1.3; collections stay minimal. |
| Five-source search p95 depends on upstream latency the project does not control (test plan v4 section 5, item 3). | Medium | Medium | If OC-12 fails, the deadline or default source set is tuned rather than the gate removed (sections 5, 13). |
| Keychain locked or unreadable, for example right after login (PRD-v8 2.10). | Medium | Low | Reads go through `/usr/bin/security` with a timeout; a locked Keychain is one `keychain_locked` state and one notification, not a notice per key; `doctor` gives the fix (sections 7, 9). |
| Metered sources (OpenAlex budget, web-search providers) run out mid-task or cost more than expected (PRD-v8 2.10). | Medium | Low | Budget tracking with `quota_low`, `rate_limited` and `budget_exhausted` states; federation skips exhausted sources and says so; web-search sources are off until configured, capped per day, and never in the default fan-out (sections 4, 5, 9). |
| PyMuPDF crashes on hostile PDFs (PRD-v8 2.10). | Medium | Low | Parsing in a worker process with CPU, memory, page and time limits (sections 3, 9). |
| macOS or cleaning tools purge `~/Library/Caches` (HLD-v3 section 10). | Low | Low | Nothing the lifecycle depends on lives there; only the re-downloadable model cache does; both databases live in Application Support and are backed up nightly (section 10). |

## 19. Traceability

> **Owner:** A · **Persona:** `architect`

**Components.** The SPEC-v2 split below was checked against the LLD headings for v5. Platform, sources, search, cache, health and security point at their Gate 3 draft LLDs (v2); UI and migration have no LLD v2 yet. PRD-migration-v6 and PRD-security-v3 are reopened-Gate 1 drafts; the other PRDs are the approved versions.

| Component | Prefix | PRD | LLD | SPEC sections | Carries SPEC-v2 sections |
| --- | --- | --- | --- | --- | --- |
| Platform | PLAT | [PRD-platform-v4](../prd/components/PRD-platform-v4.md) | [LLD-platform-v2](../lld/LLD-platform-v2.md) | 2, 3, 5, 9, 10, 12, 15 | 1, 2, 3.1 to 3.7, 7.4, 12.1, 12.2 (9.8 summarized in §3.3) |
| Sources | SRC | [PRD-sources-v5](../prd/components/PRD-sources-v5.md) | [LLD-sources-v2](../lld/LLD-sources-v2.md) | 4, 5, 9 | 4, 5.1 to 5.5 |
| Search and identity | SRCH | [PRD-search-v3](../prd/components/PRD-search-v3.md) | [LLD-search-v2](../lld/LLD-search-v2.md) | 5, 11.1, 14 | 6, 7.1 to 7.3 |
| Retrieval and cache | CACHE | [PRD-cache-v4](../prd/components/PRD-cache-v4.md) | [LLD-cache-v2](../lld/LLD-cache-v2.md) | 6, 10, 11.2, 11.3 | 8, 9.1 to 9.5, 9.7, 9.8 |
| Health and credentials | HLTH | [PRD-health-v4](../prd/components/PRD-health-v4.md) | [LLD-health-v2](../lld/LLD-health-v2.md) | 7, 10, 11.4, 12 | 10 |
| Local UI | UI | [PRD-ui-v4](../prd/components/PRD-ui-v4.md) | [LLD-ui-v2](../lld/LLD-ui-v2.md) | 2, 8, 9 | 11 |
| Migration and cutover | MIG | [PRD-migration-v6](../prd/components/PRD-migration-v6.md) | [LLD-migration-v2](../lld/LLD-migration-v2.md) | 6, 9, 10, 12, 14 | 9.6, and MIGRATION-v2 |
| Security | SEC | [PRD-security-v3](../prd/components/PRD-security-v3.md) | [LLD-security-v2](../lld/LLD-security-v2.md) | 2, 9, 17 | HLD-v3 2 and 9 (threat model); quotes 3.1, 3.1.1 and 3.2, whose names LLD-platform-v2 owns |

SPEC-v2 sections not carried into an LLD: 0.1 to 0.5 (conformance, precedence and change control), which AGENTS.md and the SDD standard now cover (LLDs own every name; documents are versioned; drift is decided by a person); 12.3 and 12.4 (work breakdown), which the milestone plans replace (section 14).

**Contracts.** [Envelope and errors v1](../contracts/envelope-and-errors-v1.md) (platform; sections 5, 9), [source adapter v1](../contracts/source-adapter-v1.md) (sources; section 4), [cache tools, archive sidecar and rebuild report v1](../contracts/cache-tools-and-sidecar-v1.md) (cache; section 6), [health status, doctor output and webhook payload v1](../contracts/health-status-and-webhook-v1.md) (health; section 7) and [prompts v3](../contracts/prompts-v3.md) (search; section 5). All are drafts for the owner to approve at Gate 3.

**Component requirements.**

| Component requirements | Area | SPEC section | LLD |
| --- | --- | --- | --- |
| PLAT-FR-1 to PLAT-FR-6 | Process and transport | 2, 3, 12 | LLD-platform-v2 §2.3, §5.2, §5.5, §5.7, §5.9 |
| PLAT-FR-8, PLAT-FR-9 | Configuration and paths | 10 | LLD-platform-v2 §3.2, §7.1 |
| PLAT-FR-10 to PLAT-FR-15, PLAT-FR-59 | Secrets and the daemon token | 8, 9, 10, 12 | LLD-platform-v2 §4.1 to §4.5, §5.9, §5.10 |
| PLAT-FR-20 to PLAT-FR-22, PLAT-FR-25 to PLAT-FR-27 | Local access and untrusted content | 2, 9 | LLD-platform-v2 §2.1, §2.3, §4.5, §4.6, §5.6 |
| PLAT-FR-30 to PLAT-FR-33 | Results, errors and HTTP | 3, 5 | LLD-platform-v2 §2.1, §2.2, §5.3, §5.6, §6 |
| PLAT-FR-40 to PLAT-FR-42 | Logging | 10, 12 | LLD-platform-v2 §4.3, §5.10, §8 |
| PLAT-FR-50 to PLAT-FR-58 | Packaging, CI, stores, backups and upgrades | 10, 12, 15 | LLD-platform-v2 §2.4, §2.5, §3.1, §3.3, §5.8, §5.9 |
| SRC-FR-1 to SRC-FR-10 | Contract, registry, states, fixtures, models, upstream MCP | 4 | LLD-sources-v2 §2, §3.1, §3.4, §5.2, §5.3, §5.6 |
| SRC-FR-12, SRC-FR-14, SRC-FR-15, SRC-FR-17, SRC-FR-18 | Live check, shutdown dates, docs sites, v1 coverage, site sets | 4, 14 | LLD-sources-v2 §3.3, §5.4, §5.8, §5.11 |
| SRC-FR-19 to SRC-FR-23 | The `web` group, caps, fallback, `site_set`, Google sign-in | 4, 5, 9 | LLD-sources-v2 §5.7 to §5.9; LLD-platform-v2 §4.2 |
| SRC-FR-24 to SRC-FR-26 | Contact address, generated inventory, new-source definition of done | 4, 13 | LLD-sources-v2 §3.2, §5.5, §5.10; LLD-platform-v2 §7.1 |
| SRCH-FR-1 to SRCH-FR-3, SRCH-FR-5 to SRCH-FR-9, SRCH-FR-27 | Federated search and source status | 5, 11.1 | LLD-search-v2 §2.1, §5.4, §5.11; LLD-sources-v2 §5.9 |
| SRCH-FR-11 to SRCH-FR-14, SRCH-FR-28 | Identity and dedupe | 5 | LLD-search-v2 §5.2, §5.3 |
| SRCH-FR-15 to SRCH-FR-17 | Work lookup | 5 | LLD-search-v2 §2.1, §5.3 |
| SRCH-FR-20 to SRCH-FR-23 | Citations, authors and export | 5, 12, 14 | LLD-search-v2 §2.1, §5.7 to §5.9 |
| SRCH-FR-25, SRCH-FR-26 | Integrity | 5 | LLD-search-v2 §2.1, §5.10 |
| CACHE-FR-1 to CACHE-FR-7 | Fetch | 6, 9, 11.2 | LLD-cache-v2 §2, §5.2, §5.12; LLD-platform-v2 §5.4 |
| CACHE-FR-10 to CACHE-FR-14 | Extraction and chunking | 3, 6, 9 | LLD-cache-v2 §5.3; LLD-platform-v2 §5.5 |
| CACHE-FR-15 to CACHE-FR-18 | Reading and local search | 6, 11.2 | LLD-cache-v2 §2, §3.1, §5.4 |
| CACHE-FR-20 to CACHE-FR-24 | Embeddings | 6, 10 | LLD-cache-v2 §3, §5.3 |
| CACHE-FR-30 to CACHE-FR-38 | Lifecycle and owner review | 6, 11.3 | LLD-cache-v2 §3, §5.5, §5.6 |
| CACHE-FR-45 to CACHE-FR-52 | Archive to Google Drive and its rebuild | 6, 10, 12 | LLD-cache-v2 §2, §5.7, §5.10 |
| CACHE-FR-55 to CACHE-FR-59 | Collections, crawl jobs, disk, integrity, data location | 6, 10, 14 | LLD-cache-v2 §5.8, §5.9, §5.11, §5.12 |
| HLTH-FR-1 to HLTH-FR-5 | Telemetry and probes | 7 | LLD-health-v2 §3, §5.3, §5.4, §5.6 |
| HLTH-FR-10 to HLTH-FR-12 | Source states | 5, 7 | LLD-health-v2 §5.5 |
| HLTH-FR-20 to HLTH-FR-25 | Credential states | 7, 11.4 | LLD-health-v2 §3, §5.7 |
| HLTH-FR-30 to HLTH-FR-35 | Notifications | 7, 11.3, 11.4 | LLD-health-v2 §2, §5.8 |
| HLTH-FR-40 to HLTH-FR-43 | Doctor and agent access | 7, 12 | LLD-health-v2 §2, §5.9, §5.10 |
| UI-FR-1 to UI-FR-4, UI-FR-6, UI-FR-7, UI-FR-20 | General | 2, 8, 9 | LLD-ui-v2 §2.1 to §2.4, §4; LLD-security-v2 §5.3 |
| UI-FR-10 to UI-FR-18, UI-FR-21 | Pages | 8 | LLD-ui-v2 §5.2, §5.3 |
| MIG-FR-1 to MIG-FR-6, MIG-FR-26 | Credentials and scrub backups | 9, 10, 12, 14 | LLD-migration-v2 §5.2, §5.3 |
| MIG-FR-10 to MIG-FR-15 | Optional corpus import | 6, 12, 14 | LLD-migration-v2 §5.1 |
| MIG-FR-20 to MIG-FR-22, MIG-FR-24, MIG-FR-25 | Client cutover, rollback (`restore-client-configs`) and v1 retirement | 12, 14 | LLD-migration-v2 §5.3; cutover runbook |
| MIG-FR-27 | File-read boundary and the read set of each owner-run command (new in PRD-migration-v6) | 9, 10, 12, 14, 17 | LLD-security-v2 §4.3 (E36), §5.5; LLD-migration-v2 §5.1 to §5.3 |

The Security component has no requirements of its own (PRD-security-v3 2.4); its criteria are below.

**Acceptance criteria.** Every criterion of the approved component PRDs, PRD-security-v3, PRD-migration-v6 and test plan v4. New in v5: SEC-28 to SEC-32 and MIG-27 to MIG-35.

| Criteria | Area | SPEC section | LLD |
| --- | --- | --- | --- |
| PLAT-1, PLAT-2, PLAT-4, PLAT-13, PLAT-80, PLAT-84 | Version, CI script, extras, CLI | 6, 12, 15 | LLD-platform-v2 §2.4, §5.8, §7.2; LLD-cache-v2 §5.7 for the upload state |
| PLAT-3, PLAT-70, PLAT-72, PLAT-73, PLAT-75, PLAT-77 | Composition root, shim, event loop | 2, 3 | LLD-platform-v2 §2.3, §5.2, §5.7 |
| PLAT-5 | Offline test guard | 17 | LLD-platform-v2 §9 |
| PLAT-6, PLAT-30 to PLAT-34 | Models, envelope, errors, cursors | 3, 5 | LLD-platform-v2 §2.1, §2.2, §5.6 |
| PLAT-8 to PLAT-12 | Settings, paths, loopback setting, contact address, secret references | 4, 9, 10 | LLD-platform-v2 §4.1, §7.1 |
| PLAT-35 to PLAT-39 | HTTP client | 3, 9 | LLD-platform-v2 §5.3, §6.1 |
| PLAT-40 to PLAT-42 | Logging | 10, 12 | LLD-platform-v2 §4.3, §5.10, §8 |
| PLAT-50 to PLAT-53 | Stores and migrations | 10 | LLD-platform-v2 §3.1 |
| PLAT-60 to PLAT-63 | MCP surface | 5, 9 | LLD-platform-v2 §2.3, §5.6 |
| PLAT-71 | Loopback bind | 2, 9 | LLD-platform-v2 §4.5 |
| PLAT-74, PLAT-76 | Jobs and the scheduler | 3 | LLD-platform-v2 §5.5 |
| PLAT-81 to PLAT-83 | Install, client config, daemon token | 12 | LLD-platform-v2 §2.5, §4.5, §5.9 |
| SEC-1 to SEC-4, SEC-13 | Secrets and Keychain access | 9 | LLD-security-v2 §4.3; LLD-platform-v2 §4.1 |
| SEC-5 to SEC-7, SEC-14 | Redaction | 9 | LLD-security-v2 §4.3, §5.4; LLD-platform-v2 §4.3 |
| SEC-8 to SEC-10 | Credential scoping and errors | 9 | LLD-security-v2 §4.3; LLD-platform-v2 §4.4 |
| SEC-11, SEC-12, SEC-26 | Loopback, bearer token, Host and Origin, shim token | 2, 9 | LLD-security-v2 §4.3, §5.2; LLD-platform-v2 §4.5, §5.7 |
| SEC-20 to SEC-22, SEC-25 | MCP surface: no hard delete, no SQL, untrusted envelope, no caller paths | 9 | LLD-security-v2 §4.3; LLD-platform-v2 §4.6; LLD-search-v2 §2.1 |
| SEC-23 | Hostile PDFs | 6, 9 | LLD-security-v2 §4.3; LLD-platform-v2 §5.5; LLD-cache-v2 §5.3 |
| SEC-24, SEC-27 | No secret at rest | 9, 10 | LLD-security-v2 §3, §4.4; LLD-platform-v2 §4.1, §4.2 |
| SEC-28 | Tool results redacted at the tool boundary (new) | 3, 9, 14 | LLD-security-v2 §5.4; LLD-platform-v2 §4.5, §5.6 |
| SEC-29, SEC-32 | `/ui/login` `next` rule and `/ui/static/*` session (new) | 2, 8, 9 | LLD-security-v2 §5.2, §5.3; LLD-ui-v2 §2.1 to §2.4 |
| SEC-30 | `DAEMON_TOKEN` format (new) | 9, 12 | LLD-security-v2 §5.2; LLD-platform-v2 §4.5 |
| SEC-31 | Webhook scheme (new) | 7, 9 | LLD-health-v2 §2.4, §5.8; LLD-security-v2 §4.3 |
| SRC-1 to SRC-8 | Contract, registry, states, conformance, adapter isolation | 4 | LLD-sources-v2 §2, §5.2, §5.3 |
| SRC-10 to SRC-12 | The three M0 adapters | 4 | LLD-sources-v2 §5.3 |
| SRC-13 | Generated inventory | 4, 17 | LLD-sources-v2 §5.10 |
| SRC-20 to SRC-27 | M1 catalog, instances, upstream MCP, docs sites, shutdown dates, live check, v1 map, site sets | 4 | LLD-sources-v2 §3.3, §5.3, §5.4, §5.6, §5.11 |
| SRC-28 to SRC-33 | The `web` group | 4, 5, 9 | LLD-sources-v2 §5.7 to §5.9; LLD-platform-v2 §4.2 |
| SRCH-10 to SRCH-16, SRCH-38 | Identity | 5 | LLD-search-v2 §5.2 |
| SRCH-1 to SRCH-9, SRCH-37 | Federation | 5, 11.1 | LLD-search-v2 §5.3, §5.4 |
| SRCH-17, SRCH-23, SRCH-36 | `get_work` | 5 | LLD-search-v2 §2.1, §5.10 |
| SRCH-20 to SRCH-22 | MCP contract and argument bounds | 5 | LLD-search-v2 §2.1 |
| SRCH-30 to SRCH-34 | Citations, authors, `cite`, integrity, search records | 5, 12, 14 | LLD-search-v2 §2.1, §5.7 to §5.11 |
| CACHE-1, CACHE-2 | Downloader | 6, 9 | LLD-platform-v2 §5.4; LLD-cache-v2 §2 |
| CACHE-10 to CACHE-13 | Fetch | 6, 11.2 | LLD-cache-v2 §2, §5.2, §5.12 |
| CACHE-14 to CACHE-18 | Extraction and chunking | 6 | LLD-cache-v2 §5.3 |
| CACHE-19 to CACHE-24 | Reading, local search, embeddings | 6 | LLD-cache-v2 §2, §5.3, §5.4 |
| CACHE-30 to CACHE-36, CACHE-48 | Lifecycle and review | 6, 11.3 | LLD-cache-v2 §4, §5.5, §5.6 |
| CACHE-40 to CACHE-44, CACHE-60 to CACHE-62 | Archive and rebuild | 6, 10 | LLD-cache-v2 §2, §5.7, §5.10 |
| CACHE-45, CACHE-63 | Collections and their export | 6, 14 | LLD-cache-v2 §5.9; LLD-search-v2 §2.1 |
| CACHE-46, CACHE-47 | Disk and maintenance | 6, 13 | LLD-cache-v2 §5.8, §8 |
| CACHE-49 | Backups | 10, 12 | LLD-cache-v2 §5.11; LLD-platform-v2 §3.3 |
| HLTH-1 to HLTH-4, HLTH-44 | Telemetry and probes, including the embeddings target | 7 | LLD-health-v2 §5.3, §5.4, §5.6 |
| HLTH-10 to HLTH-13 | Source states and the locked Keychain | 5, 7 | LLD-health-v2 §5.5, §5.7 |
| HLTH-20 to HLTH-25, HLTH-43 | Credential states and metadata only | 7, 11.4 | LLD-health-v2 §3, §5.7 |
| HLTH-30 to HLTH-35 | Notifications | 7 | LLD-health-v2 §2, §5.8 |
| HLTH-40 to HLTH-42 | Doctor and status | 7, 12 | LLD-health-v2 §2, §5.9, §5.10 |
| UI-1 to UI-6, UI-20 | Loopback, login, CSRF, no secrets, refresh, style, Host and Origin | 2, 8, 9 | LLD-ui-v2 §2.1 to §2.4, §4; LLD-security-v2 §5.3 |
| UI-10 to UI-19, UI-21 to UI-25 | Pages | 8 | LLD-ui-v2 §5.2, §5.3 |
| MIG-1 to MIG-6, MIG-22, MIG-23, MIG-25 | Credential import and scrub backups | 9, 12 | LLD-migration-v2 §5.2, §5.3 |
| MIG-10 to MIG-14, MIG-24 | Legacy import and an empty cache | 6, 12 | LLD-migration-v2 §5.1 |
| MIG-20, MIG-21, MIG-26 | Client configs, tool map, retirement | 12, 14 | LLD-migration-v2 §5.3 |
| MIG-27 to MIG-35 | Read sets: per command, refusal, symbolic link, restore, print, v2 paths, `retire-v1 --confirm` (new) | 9, 10, 12, 17 | LLD-security-v2 §4.3 (E36), §5.5; LLD-migration-v2 §5.1 to §5.3 |

**Parent requirements.** The parent requirement IDs below were checked against [PRD-v8](../prd/PRD-v8.md) (approved): OUT-1 to OUT-8 and NFR-1 to NFR-12 exist there with these names, and its NFR-7 carries the new wording.

| Parent requirement | Component requirements | SPEC section | LLD |
| --- | --- | --- | --- |
| OUT-1 Breadth | SRC-FR-1 to SRC-FR-10, SRC-FR-12, SRC-FR-14, SRC-FR-15, SRC-FR-17 to SRC-FR-26 | 4, 14 | LLD-sources-v2 |
| OUT-2 One search | SRCH-FR-1 to SRCH-FR-3, SRCH-FR-5 to SRCH-FR-9, SRCH-FR-27 | 5, 11.1, 13 | LLD-search-v2 |
| OUT-3 Cheap to maintain | SRC-FR-25, SRC-FR-26; every PLAT-FR cites OUT-3 | 3, 4, 13 | LLD-sources-v2, LLD-platform-v2 |
| OUT-4 Monitored | HLTH-FR-1 to HLTH-FR-5, HLTH-FR-10 to HLTH-FR-12, HLTH-FR-40 to HLTH-FR-43 | 7, 12 | LLD-health-v2 |
| OUT-5 Credential care | HLTH-FR-20 to HLTH-FR-25, HLTH-FR-30 to HLTH-FR-35 | 7, 11.4 | LLD-health-v2 |
| OUT-6 Cache, not library | CACHE-FR-30 to CACHE-FR-38, CACHE-FR-45 to CACHE-FR-52; every CACHE-FR cites OUT-6 | 6, 11.3 | LLD-cache-v2 |
| OUT-7 Safe by default | PLAT-FR-10 to PLAT-FR-15, PLAT-FR-59, PLAT-FR-20 to PLAT-FR-22, PLAT-FR-25 to PLAT-FR-27; MIG-FR-26, MIG-FR-27; SEC criteria | 9 | LLD-security-v2, LLD-platform-v2 |
| OUT-8 Visible | UI-FR-1 to UI-FR-4, UI-FR-6, UI-FR-7, UI-FR-10 to UI-FR-18, UI-FR-20, UI-FR-21 | 8 | LLD-ui-v2 |
| NFR-1 Single process | PLAT-FR-1, PLAT-FR-2 | 2, 3 | LLD-platform-v2 |
| NFR-2 Async | PLAT-FR-5 | 3 | LLD-platform-v2 |
| NFR-3 No secrets at rest outside the Keychain | PLAT-FR-10; MIG-FR-26 (approved exception) | 9, 10 | LLD-platform-v2, LLD-security-v2, LLD-migration-v2 |
| NFR-4 No secret in any output | PLAT-FR-11, PLAT-FR-13, PLAT-FR-14; SEC-28 | 9, 17 | LLD-platform-v2, LLD-security-v2 |
| NFR-5 Bounded output | PLAT-FR-30, SRCH-FR-6 | 5 | LLD-platform-v2, LLD-search-v2 |
| NFR-6 Untrusted content is labeled | PLAT-FR-25 | 2, 9 | LLD-platform-v2 |
| NFR-7 Loopback only | PLAT-FR-3, UI-FR-1; SEC-INV-2 (`/healthz`, `/readyz`, `/ui/login`; `/ui/static/*` needs a session) | 2, 9 | LLD-platform-v2, LLD-security-v2, LLD-ui-v2 |
| NFR-8 Respect upstream terms | PLAT-FR-33, SRC-FR-24 | 3, 4, 13 | LLD-platform-v2, LLD-sources-v2 |
| NFR-9 Testable offline | SRC-FR-8 | 4, 17 | LLD-sources-v2, LLD-platform-v2 |
| NFR-10 Docs follow code | SRC-FR-25 | 4, 13, 17 | LLD-sources-v2 |
| NFR-11 Prose style | UI-FR-7 | 15 | LLD-ui-v2 |
| NFR-12 Availability and scale | PLAT-FR-1, HLTH-FR-41 | 12, 13 | LLD-platform-v2, LLD-health-v2 |

**Invariants.**

| Invariants | Enforced by | SPEC section | LLD |
| --- | --- | --- | --- |
| INV-1 | CACHE-FR-34, CACHE-FR-36; CACHE-INV-1 | 6, 12 | LLD-cache-v2 |
| INV-2 | PLAT-FR-11, PLAT-FR-13, PLAT-FR-14; SEC-INV-4 | 9, 12 | LLD-platform-v2, LLD-security-v2 |
| INV-3 | PLAT-FR-12, CACHE-FR-3; SEC-INV-5 | 9 | LLD-platform-v2, LLD-security-v2 |
| INV-4 | PLAT-FR-21, CACHE-FR-4; SEC-INV-7; exception per command MIG-FR-27 | 6, 9 | LLD-platform-v2, LLD-security-v2 |
| INV-5 | PLAT-FR-3, UI-FR-1; SEC-INV-1 | 2, 9 | LLD-platform-v2, LLD-security-v2 |
| INV-6 | PLAT-FR-10, SRC-FR-23; SEC-INV-3, SEC-INV-11; exception MIG-FR-26 | 9, 10 | LLD-platform-v2, LLD-security-v2, LLD-migration-v2 |
| INV-7 | CACHE-FR-47; CACHE-INV-5 | 6 | LLD-cache-v2 |
| INV-8 | CACHE-FR-51; CACHE-INV-6 | 6 | LLD-cache-v2 |
| INV-9 | SRC-FR-19; SRC-INV-4 | 4, 5, 9 | LLD-sources-v2 |
| INV-10 | MIG-FR-10; MIG-INV-1 | 12 | LLD-migration-v2 |
| SEC-INV-1 to SEC-INV-11 | Security invariants (the platform defines none of its own); SEC-INV-2 covers `AuthGate` | 2, 9 | LLD-security-v2 §4.4 |
| SRC-INV-1 to SRC-INV-6 | Sources invariants | 4, 9 | LLD-sources-v2 |
| SRCH-INV-1 to SRCH-INV-3 | Search invariants | 5 | LLD-search-v2 |
| CACHE-INV-1 to CACHE-INV-7 | Cache invariants | 6 | LLD-cache-v2 |
| HLTH-INV-1 to HLTH-INV-5 | Health invariants | 7 | LLD-health-v2 |
| UI-INV-1 to UI-INV-5 | UI invariants | 8 | LLD-ui-v2 |
| MIG-INV-1 to MIG-INV-3 | Migration invariants | 12 | LLD-migration-v2 |

**Where the SPEC-v2 0.6 clarification rows live.** SPEC-v2 0.6 has seven rows from the first M0 attempt; AGENTS.md makes them requirements. Every component a row concerns carries it, marked "(SPEC-v2 0.6)". LLD-ui-v2 §1 and LLD-migration-v2 §1 state that no row concerns them.

| Unit; SPEC-v2 section | Row | Carried in |
| --- | --- | --- |
| M0-01; 1, 12.1 | Offline network guard installed for the whole test session | LLD-platform-v2 §9 |
| M0-01; 1 | Import side effects attributed to `research_mcp` through any frame | LLD-platform-v2 §5.1 |
| M0-01; 12.1 | CI on macOS and Linux, SHA-pinned actions, secret scan, weekly audit | LLD-platform-v2 §5.8; LLD-security-v2 (E35 in §4.3) |
| M0-02; 6 | Idempotent normalizers, strict UTF-8 decoding, slashes in suffixes | LLD-search-v2 §5.2 |
| M0-03; 3.7, 4 | `Budget.fit` keeps one status per source | LLD-platform-v2 §5.6; LLD-sources-v2 §3.1; LLD-search-v2 §6 |
| M0-04; 2 | Path normalization and canonical credential names | LLD-platform-v2 §7.1; LLD-cache-v2 §3.6 |
| M0-05; 3.1 | `SecretRef` validation; `FakeProvider.metadata` | LLD-platform-v2 §4.1; LLD-security-v2 §5.1; LLD-health-v2 §5.2 |

**LLD work still due before Gate 3 closes.** These follow from the approved or draft PRDs and owner answers of 2026-10-22, so they are LLD work for the `component-designer`, not open questions here:

- `LLD-ui-v2`: the `/ui/login` `next` rule, the `/ui/static/*` session rule, the CSRF rule from LLD-security-v2 §5.3, polling only (UI-FR-20), job retry through `JobService.submit` (UI-FR-13) and read-only site sets (UI-FR-21); and the section 1 table citing PRD-ui-v4, PRD-security-v3 and SPEC-v5.
- `LLD-migration-v2`: the read set of each command and the refusal (MIG-FR-27, MIG-27 to MIG-35), `restore-client-configs` (MIG-FR-25), `retire-v1 --confirm` (MIG-FR-26), the symbolic-link refusal and the v2 `cache.db` read for `import-legacy`; the scrub backup path and modes are already set in LLD-migration-v2 section 3.
- `LLD-platform-v2` still has to take what the sibling LLDs ask of it: the scheduler jobs `review_close`, `archive_reconcile`, `health_evaluate`, `health_rollup`, `credential_sync` and `probe:<source>`; the flags `cache.crawl_enabled`, `cache.collections_enabled` and `archive.reindex_enabled`; the webhook validator (https, or http on loopback only); the settings keys `federation.fuzzy_merge`, `federation.record_searches`, `cite.doi_negotiation` and `integrity.recheck_before_review`; the `cite` extra; the `0001_init` additions named in section 10; `sdd.config.json` paths for `services/doctor.py`, the cache tool wrappers and `services/disk.py`; and the `fetch` tool taking one item or a list of 1 to 20, which changes the tool-result union and the footprint test.
- Sibling LLDs must use `calls_today` (not `quota_used`) for the web count, and the `SourceStatus.state` values `budget_exhausted` and `not_needed`.
- The next PRD, test plan and LLD versions cite SPEC-v5 and the new IDs (SEC-28 to SEC-32, MIG-FR-27, MIG-27 to MIG-34).

## 20. Open questions

> **Owner:** A · **Persona:** `architect`

Resolved in v5, with the owner answers recorded in the sections named: `AuthGate` and the unauthenticated surfaces (section 2); in-tree-only adapters and `docs_site` milestones (sections 4, 14); the Drive backup copy (section 10); the two meanings of critical (section 7); the migration read sets and the `restore-client-configs` rollback (sections 9, 12); the schema additions (section 10); the `cite` and `pdf` extras (section 12). The v4 questions were all resolved and are in SPEC-v4 section 20.

There are no open questions. The four that stood at the start of this round are closed: PRD-v8 exists and its OUT and NFR IDs and NFR-7 wording match section 19 and cite the same component versions (section 19); the scrub backup folder is `~/.research-mcp-migration/scrub-backups/` (section 9); the `import-legacy` read of the v2 `cache.db` is confirmed (owner decision, 2026-10-22; section 9); and there are no ADRs for `AuthGate`, in-tree adapters or the Drive backup copy (owner decision, 2026-10-23; section 16).

### Gate 2: Design approved

| Approver | Date | ADRs chosen | Notes |
| --- | --- | --- | --- |
| Kenny Hill (Engineering) | 2026-10-23 | 0001 to 0013, all accepted (section 16); no new ADRs (owner decision, 2026-10-23) | Approved in chat; recorded by Claude in the owner's name at his direction |
