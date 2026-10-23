---
title: "Migration and Cutover low level design"
type: lld
version: 1
status: draft
owner: "Kenny Hill"
prefix: MIG
component: migration
parent: docs/spec/SPEC-v3.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# LLD: Migration and Cutover (v1)

Requirements: [PRD-migration v4](../prd/components/PRD-migration-v4.md). Design sources: [SPEC v2](../../docs-archive/spec/SPEC-v2.md) section 9.6 (legacy import) and [MIGRATION v2](../../docs-archive/migration/MIGRATION-v2.md) sections 1, 2 and 4. The cutover steps (MIGRATION-v2 section 3) are the [migration cutover runbook](../runbooks/migration-cutover-v1.md).

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

This component covers the credential and settings import from the v1 client configs, the optional legacy corpus import, the client config printer, the v1 to v2 tool map, rollback and v1 retirement. It is governed by SPEC-v3 section 6 (retrieval and cache: the legacy import writes into the cache) and SPEC-v3 section 12 (deployment and operations: install, client configs and the parallel run with v1).

| Requirement | Criteria | SPEC section |
| --- | --- | --- |
| MIG-FR-1 | MIG-1 | SPEC-v3 section 12 |
| MIG-FR-2 | MIG-2 | SPEC-v3 section 12 |
| MIG-FR-3 | MIG-3 | SPEC-v3 section 12 |
| MIG-FR-4 | MIG-4 | SPEC-v3 section 12 |
| MIG-FR-5 | MIG-5 | SPEC-v3 section 12 |
| MIG-FR-6 | MIG-6 | SPEC-v3 section 12 |
| MIG-FR-10 | MIG-10 | SPEC-v3 section 6 |
| MIG-FR-11 | MIG-11 | SPEC-v3 section 6 |
| MIG-FR-12 | MIG-12 | SPEC-v3 section 6 |
| MIG-FR-13 | MIG-13 | SPEC-v3 section 6 |
| MIG-FR-14 | MIG-14 | SPEC-v3 section 6 |
| MIG-FR-15 | MIG-10 | SPEC-v3 section 6 |
| MIG-FR-20 | MIG-20 (also PLAT-82) | SPEC-v3 section 12 |
| MIG-FR-21 | MIG-20 | SPEC-v3 section 12 |
| MIG-FR-22 | MIG-21 | SPEC-v3 section 12 |
| MIG-FR-23 | none (owner check OC-06) | SPEC-v3 section 12 |
| MIG-FR-24 | none (owner check OC-07) | SPEC-v3 section 12 |

No row of SPEC-v2 section 0.6 concerns this component: its rows cover units M0-01 to M0-05 (test network guard, import side effects, CI, identifier normalizers, `Budget.fit`, settings paths and `SecretRef` validation).

Principles (MIGRATION-v2 1):

1. v1 is never modified. Its database is opened immutable; its folder is only read.
2. No credential is re-entered. They move from the v1 client configs into the Keychain.
3. The corpus import is optional. v2 works with an empty cache.
4. Rollback is one config change until v1 is retired.

Inventory (MIGRATION-v2 2, as of 2026-10-19):

| Item | Where | Notes |
|---|---|---|
| v1 code | `~/Documents/GitHub/my-research-mcp-server` at `568d440` | read-only |
| v1 data | `~/arxiv-papers`: `arxiv_index.db` (34 MB, 186 rows, 11,403 chunks), 123 PDFs, `embeddings.duckdb` | 54 duplicate pairs; 10 web pages stored by URL |
| v1 datasets | `~/research-datasets` | not inspected; open decision O4 |
| v1 credentials | `env` blocks of the v1 server entries in the Claude desktop, Claude Code and OpenClaw configs | names in the review's credential table; values never read during design |

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

No machine-readable contract for this component exists in `docs/contracts/` yet (see 11).

**Commands** (SPEC-v2 12.1, verbatim rows):

| Command | Purpose |
|---|---|
| `install [--print-client-config]` | Install the launchd jobs and print client config. |
| `secrets list\|import [--dry-run]\|scrub-client-configs\|rotate-token` | Manage Keychain items. |
| `import-legacy <path> [--dry-run] [--mode]` | Import the v1 corpus (9.6). |

`secrets list` prints names, fingerprints and states only (SPEC-v2 12.1). `--mode` takes `cache`, `archive` or `metadata_only`; the default is `cache` (MIG-FR-10, MIG-FR-13).

**Service interface** (SPEC-v2 9.6): `LegacyImportService.run(path, mode, dry_run)` runs as the job kind `legacy_import`, submitted through `JobService.submit(kind, params) -> job_id` (SPEC-v2 3.6).

**Keychain items written** by `secrets import`: `research-mcp/<NAME>`, one per imported credential (MIG-FR-1).

**Settings written** by `secrets import` into `config.toml` (MIG-FR-6; key rows from SPEC-v2 2, verbatim):

| Key | Default | Notes |
|---|---|---|
| `sources.vertex_<name>` | none | `{ instance_of = "vertex_search", project = "...", location = "global", engine_id = "...", title = "..." }`; one per Vertex AI Search engine (5.5) |
| `sources.google_pse.engine_id` | none | Programmable Search engine id (v1 `GOOGLE_PSE_CX`); not a secret |
| `web.order` | `["vertex_*", "brave_search", "serpapi", "google_pse"]` | `vertex_*` expands to the configured Vertex instances in name order |

The import writes the Vertex settings as the instance `vertex_v1`; when v1 named one provider, it goes first in `web.order` (MIG-FR-6).

**Client config entry** printed by `install --print-client-config`: for each client (Claude desktop, Claude Code, OpenClaw), a server entry that launches `research-mcp stdio`, with no secrets, under the server name `research` (MIG-FR-20, MIG-FR-21).

**Import report files** (SPEC-v2 9.6 step 7): `state_dir/imports/<timestamp>/report.json` and `report.md`, with rows read, works created, merged pairs, unresolved ids, re-extraction failures, chunk counts before and after, and the legacy-id to work-id map (MIG-FR-14).

**v1 to v2 tool map** (MIGRATION-v2 4, verbatim). It covers all 53 v1 tools (MIG-FR-22, MIG-21).

| v1 tool | v2 replacement |
|---|---|
| `search_arxiv` | `search(query, sources=["arxiv"])` |
| `get_paper_metadata` | `get_work("arxiv:<id>")` |
| `download_paper` | `fetch("arxiv:<id>")` |
| `index_paper` | removed: no caller-chosen local paths (ADR 0009); `fetch` indexes automatically |
| `index_all_papers` | `research-mcp import-legacy` (one time) |
| `query_papers` | `search_cache(query, mode="keyword")` |
| `get_paper_text` | `read(doc_id, pages=...)` |
| `list_indexed_papers` | `library(action="list")` |
| `remove_paper` | discard through the cache review only (UI, or `cache_review_decide` inside an open batch); the item goes to the 7-day trash |
| `index_stats` | `library(action="stats")` |
| `search_semantic_scholar` | `search(query, sources=["semantic_scholar"])` |
| `get_semantic_scholar_paper` | `get_work("s2:<id>")` |
| `resolve_doi` | `get_work("doi:<doi>")` |
| `search_crossref` | `search(query, sources=["crossref"])` |
| `get_doi_citation` | `cite(ids=["doi:<doi>"], format=..., style=...)` |
| `download_paper_by_doi` | `fetch("doi:<doi>")` |
| `search_openalex` | `search(query, sources=["openalex"])` |
| `get_openalex_work` | `get_work("openalex:<id>")` |
| `search_openalex_authors` | `authors(query)` |
| `search_osf` | `search(query, sources=["osf"])` |
| `search_psyarxiv` | `search(query, sources=["osf"], provider="psyarxiv")` |
| `search_core` | `search(query, sources=["core"])` |
| `get_core_work` | `get_work("core:<id>")` |
| `download_core_paper` | `fetch("core:<id>")` |
| `search_mit_dspace`, `search_harvard_dash`, `search_cornell_ecommons`, `search_penn_scholarly` | `search(query, sources=["dspace_mit"])` and so on, or `groups=["repositories"]` |
| `get_mit_dspace_item`, `get_harvard_dash_item`, `get_cornell_ecommons_item`, `get_penn_scholarly_item` | `get_work("<handle or uuid>")` |
| `search_europe_pmc` | `search(query, sources=["europe_pmc"])` |
| `check_retractions` | `check_integrity(ids)` |
| `get_citations` | `citations(id)` |
| `search_clinical_trials` | `search(query, sources=["clinical_trials"])` |
| `search_aws_docs` | `search(query, sources=["aws_knowledge"])` |
| `search_gcp_docs` | `search(query, sources=["google_devknowledge"])` |
| `search_microsoft_docs` | `search(query, sources=["ms_learn"])` |
| `fetch_cloud_doc_page` | `fetch(url)` then `read`, or `get_work(url)` for a summary |
| `search_iam_docs` | `search(query, groups=["web"], site_set="v1_docs")`; same providers in the same order (Vertex, Brave, SerpAPI, Programmable Search) |
| `index_iam_project` | `crawl_site("docs_site_<project>")`; v1's six projects ship as default `docs_site` instances |
| `search_iam_index` | `search_cache(query, collection=...)` or `search(query, sources=["docs_site_<name>"])` |
| `list_iam_indexed` | `library(action="list")` filtered by source in the UI; `list_sources(group="vendor_docs")` lists the configured sites |
| `search_github_repos`, `search_github_code` | `search(query, sources=["github"], work_type="repository" or "code")` |
| `fetch_github_readme` | `get_work("github:<owner>/<repo>")` |
| `analytics_sql`, `dataset_query`, `list_datasets` | removed (ADR 0009, open decision O4) |
| `embedding_stats` | `library(action="stats")` (reports coverage) |
| `embed_chunks` | removed: embedding happens at fetch |
| `semantic_search` | `search_cache(query, mode="semantic")` |

The generated v2 inventory (`docs/generated/sources.md`) and this table are the inputs for updating agent instructions that mention v1 tool names (MIGRATION-v2 4).

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

This component owns no table and adds no migration. The legacy import writes rows into the `cache.db` tables of SPEC-v2 8.1: `works`, `identifiers`, `documents`, `files`, `extractions` and `chunks`. The columns it sets by name in SPEC-v2 9.6 are:

- `documents.origin_url = pdf_path` and `documents.source = docs_site_<project>` for v1 `iam:<project>:<hash>` rows, which become HTML documents;
- `documents.expires_at = now + 120 d` in mode `cache`;
- `extractions.parser = "v1-import"` for v1 chunks imported where re-extraction fails;
- `identifiers` rows with scheme `legacy` for each raw v1 id of a merged group and for ids with an unknown prefix.

Files are copied into the cache by SHA-256 (`files.sha256`).

**v1 schema read** (read only, opened immutable). The pre-import queries from findings-functional section 6.3 name the v1 table `papers` (columns `arxiv_id`, `pdf_path`, `title`) and the table `chunks` (joined to `papers` on `arxiv_id`):

```sql
SELECT COUNT(*) AS rows, COUNT(DISTINCT pdf_path) AS paths FROM papers;
SELECT pdf_path, GROUP_CONCAT(arxiv_id) AS ids, COUNT(*) n FROM papers
  WHERE pdf_path NOT LIKE 'http%' GROUP BY pdf_path HAVING n > 1;
SELECT arxiv_id FROM papers WHERE arxiv_id GLOB '*v[0-9]*';
SELECT arxiv_id, pdf_path FROM papers WHERE pdf_path LIKE 'http%';
SELECT arxiv_id FROM papers WHERE arxiv_id NOT GLOB '[0-9][0-9][0-9][0-9].[0-9]*' AND arxiv_id NOT LIKE 'iam:%';
SELECT COUNT(*) FROM chunks c JOIN papers p USING(arxiv_id) WHERE p.title = '' OR p.title IS NULL;
```

**Settings persisted** by `secrets import`: the `config.toml` keys in section 2.

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

- **Credential import.** v2 reads the v1 client config `env` blocks once on the Mac and writes only to the Keychain (ADR 0001). It prints names, fingerprints and the source config file, never values (MIG-FR-1; parent NFR-4). Imported credentials live only in the Keychain as `research-mcp/<NAME>` (parent NFR-3).
- **Unused credentials.** A v1 credential no v2 source uses is listed as "not imported" with a note and is not copied (MIG-FR-3).
- **Scrub.** `secrets scrub-client-configs` runs only on explicit confirmation, backs up each file first, and removes only the plaintext `env` values of the old v1 entries (MIG-FR-5, MIG-5).
- **Client config printer.** The printed entries contain no secrets (MIG-FR-20; PLAT-82).
- **v1 data.** The v1 database is opened `file:...?immutable=1` and the v1 folder is never modified (SPEC-v2 9.6 step 1; MIG-FR-10).
- **Tests.** Tests never read the Keychain or real client configs; they use `FakeProvider` and fake client configs (MIG-1; TEST-PLAN-v3 7).

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

| Module | Contents (SPEC-v2 1 layout) |
|---|---|
| `src/research_mcp/cli.py` | The `install`, `secrets` and `import-legacy` commands |
| `src/research_mcp/services/legacy_import.py` | `LegacyImportService` |
| `src/research_mcp/platform/secrets.py` | `SecretRef`, `SecretProvider`, `KeychainProvider`, `FakeProvider`, used by the credential import |
| `src/research_mcp/platform/jobs.py` | `JobService`, `Job`, `JobKind` (job kind `legacy_import`) |
| `src/research_mcp/platform/workers.py` | `WorkerRunner`, which runs the re-extraction tasks |

### 5.1 Legacy import (SPEC-v2 9.6, verbatim)

`LegacyImportService.run(path, mode, dry_run)` runs as the job kind `legacy_import`:

1. Open `<path>/arxiv_index.db` as `file:...?immutable=1`, so no WAL or SHM files are created.
2. Run the inventory and the pre-import queries from findings-functional section 6.3.
3. Map each row:
   - arXiv ids go through `normalize_arxiv`;
   - `doi:` and `doi/` go through `normalize_doi`;
   - `core:` and `core/` map to the `core` scheme;
   - `iam:<project>:<hash>` becomes an HTML document with `origin_url = pdf_path` and `source = docs_site_<project>`;
   - anything else maps to the `legacy` scheme, followed by a title lookup through `get_work`.
4. Group rows by normalized id and by file path. Keep the row with a non-empty title for metadata, and record both raw ids as `legacy` identifiers.
5. Copy each distinct file into the cache by SHA-256 and re-extract it with the v2 worker. If extraction fails, import the v1 chunks for that document with `parser="v1-import"`.
6. Set each document's state by mode:
   - `cache` (the default): `expires_at = now + 120 d`;
   - `archive`: archive each document;
   - `metadata_only`: create works and identifiers only.
7. Write `state_dir/imports/<timestamp>/report.json` and `report.md`.

In mode `cache`, imported items go through the normal review (MIG-FR-13). Running the import is optional; v2 works fully with an empty cache (MIG-FR-15).

### 5.2 Credential and settings import

SPEC-v2 names the command (`secrets import [--dry-run]`) but does not give its algorithm. From MIG-FR-1 to MIG-FR-4 and MIG-FR-6:

1. Find the v1 server entries in the Claude desktop, Claude Code and OpenClaw configs on the Mac.
2. Read the credential values from their `env` blocks.
3. For each name used by a v2 source (including the Brave and SerpAPI keys and the Google key shared by the Developer Knowledge and Programmable Search sources), write it to the Keychain as `research-mcp/<NAME>`. List a name no v2 source uses as "not imported" with a note.
4. If one name has different values in different configs, stop for that name and ask the owner which config wins, by fingerprint.
5. Write the v1 web-search settings to `config.toml` as in section 2, and print each setting written.
6. Print names, fingerprints and the config file each came from.
7. With `--dry-run`, show what would be written and write nothing. Repeated runs give the same result.

### 5.3 Scrub, client config printer and cutover

- `secrets scrub-client-configs`: after cutover and on explicit confirmation, back up each client config file, then remove the plaintext `env` values from the old v1 entries (MIG-FR-5).
- `install --print-client-config`: print, for each client, the server entry that launches `research-mcp stdio` (MIG-FR-20). The v2 entry is added beside the v1 entry under the name `research`; the v1 entry is disabled, not deleted, at cutover (MIG-FR-21; ADR 0001).
- Rollback is re-enabling the v1 entry; it needs no data conversion (MIG-FR-23). v1 is retired only after 14 days of daily use on v2 with no fallback and the owner's explicit go-ahead (MIG-FR-24). The step-by-step procedure is the [cutover runbook](../runbooks/migration-cutover-v1.md).

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

| Condition | Behavior | Source |
|---|---|---|
| One credential name has different values in different configs | Stop the import for that name and ask which config wins, by fingerprint; do not guess | MIG-FR-2 |
| A v1 credential no v2 source uses | Report it as "not imported" with a note; do not copy it | MIG-FR-3 |
| `secrets import` run again | Idempotent | MIG-FR-4 |
| `--dry-run` on `secrets import` | Show what would be written; write nothing | MIG-FR-4, MIG-4 |
| Unknown v1 id prefix (`harv...`, `penn...`) | Map to the `legacy` scheme, then a title lookup through `get_work` | SPEC-v2 9.6 step 3; MIG-FR-11 |
| Two v1 rows share a normalized id or a file path | Merge; keep the titled row's metadata; record both raw ids as `legacy` identifiers | SPEC-v2 9.6 step 4 |
| Re-extraction fails | Import the v1 chunks for that document with `parser="v1-import"` | SPEC-v2 9.6 step 5 |
| A worker task crashes or is killed | The task ends with code `extract_failed`; only that task is affected | SPEC-v2 3.6 |
| Rollback after `scrub-client-configs` | v1 does not read the Keychain, so the scrubbed values must be restored from the scrub backups | MIGRATION-v2 3 |

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

The sources define no feature flag for this component. Its behaviors are owner-run commands: the legacy import runs only when the owner starts it (MIG-FR-15), and `scrub-client-configs` runs only on explicit confirmation (MIG-FR-5).

| Flag | Default | Safe to switch off? |
| --- | --- | --- |

Command options: `--dry-run` (both imports) and `--mode` for `import-legacy` (`cache`, the default; `archive`; `metadata_only`). The import reads `paths.state_dir` for the report location and writes the settings listed in section 2. The 120-day expiry matches `cache.retention_days = 120` (SPEC-v2 2; ADR 0011).

## 8. Observability

> **Owner:** A · **Persona:** `sre`

- `secrets import` prints names, fingerprints, the source config file and each setting written; never values (MIG-FR-1, MIG-FR-6).
- The legacy import runs as a job; its state lives in `state.db.jobs`, and progress is pushed to MCP `Context.report_progress` while the caller waits (SPEC-v2 3.6).
- The legacy import report (section 2) records rows read, works created, merged pairs, unresolved ids, re-extraction failures, chunk counts before and after, and the legacy-id to work-id map (MIG-FR-14).
- Cutover checks use `research-mcp doctor`, the Credentials page and the source board (runbook; MIGRATION-v2 3).

No component NFR is defined yet (PRD-migration-v4 2.5).

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

No test in `tests/` cites an `AT-MIG` id yet. TEST-PLAN-v3 names no test files for this component; it names the fixture `tests/migration/fixtures/make_v1_db.py` (synthetic v1 database reproducing the 54 pairs, 10 URL rows and harv and penn ids) for the legacy import tests (TEST-PLAN-v3 7). Owner checks OC-06 and OC-07 cover MIG-FR-20, MIG-FR-21, MIG-FR-23 and MIG-FR-24 at M4 (TEST-PLAN-v3 6).

| Criterion | Planned tests | Level | Status |
| --- | --- | --- | --- |
| MIG-1 | planned | integration | planned |
| MIG-2 | planned | integration | planned |
| MIG-3 | planned | unit | planned |
| MIG-4 | planned | integration | planned |
| MIG-5 | planned | integration | planned |
| MIG-6 | planned | unit | planned |
| MIG-10 | planned (fixture `tests/migration/fixtures/make_v1_db.py`) | integration | planned |
| MIG-11 | planned (fixture `tests/migration/fixtures/make_v1_db.py`) | integration | planned |
| MIG-12 | planned (fixture `tests/migration/fixtures/make_v1_db.py`) | integration | planned |
| MIG-13 | planned (fixture `tests/migration/fixtures/make_v1_db.py`) | integration | planned |
| MIG-14 | planned (fixture `tests/migration/fixtures/make_v1_db.py`) | integration | planned |
| MIG-20 | planned | unit | planned |
| MIG-21 | planned | unit | planned |

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| v2 reads v1 only through the legacy import and the credential import; v1 entries are disabled, not deleted, at cutover | Clean history; the owner keeps a working tool; rollback needs no data conversion (ADR 0001) | Rebuilding in place in the v1 tree (ADR 0001) |
| Open the v1 database `immutable=1` | No WAL or SHM files are created, so the v1 folder is unchanged (SPEC-v2 9.6) | `?mode=ro` (findings-functional 6.3) |
| Re-extract files with the v2 parser and chunker; use v1 chunks only on failure | Chunk ids, offsets, sections and embeddings stay consistent with new fetches (findings-functional 6.3) | Copying v1 chunks (MIG-FR-12) |
| Default mode `cache` with a 120-day expiry | Cached items live 120 days and go through the owner review (ADR 0011; OUT-6) | Modes `archive` and `metadata_only` (SPEC-v2 9.6) |
| Import the v1 web-search credentials and settings | Every v1 endpoint is kept; web search is an optional source group (ADR 0012) | Dropping the providers (review decision D7, superseded) |
| Map removed v1 tools to "removed" with a reason | No caller-chosen local paths and no free-form SQL (ADR 0009) | none recorded |

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

- [ ] Q: The v1 file count differs between sources: MIGRATION-v2 2 lists 123 PDFs; findings-functional 6.3 says the v2 parser runs on 122 distinct files. Which is current?
- [ ] Q: The lookup for unknown prefixes differs: SPEC-v2 9.6 says a title lookup through `get_work`; findings-functional 6.3 says a DSpace search of the matching repository, then Crossref and OpenAlex; MIG-FR-11 says best-effort lookup. Which does the import do?
- [ ] Q: The crawled-site source name differs: SPEC-v2 9.6 and MIG-FR-11 use `docs_site_<project>`; findings-functional 6.3 uses `docs_site:<project>`. Confirm `docs_site_<project>`.
- [ ] Q: findings-functional 6.3 also lists an enrichment step (batch lookup to fill `csl_json`, `year`, `venue`, and `check_integrity`) and report fields for integrity flags and `needs_ocr`. SPEC-v2 9.6 and MIG-FR-14 have neither. Are they in scope?
- [ ] Q: SPEC-v2 9.6 does not say what `dry_run` does for the legacy import (for example, write only the report). What is written in a dry run?
- [ ] Q: SPEC-v2 gives no module, class or function names for `secrets import`, `scrub-client-configs`, the client config printer or the tool map, and no file location for the tool map that MIG-21 tests. SPEC-v3 should name them.
- [ ] Q: SPEC-v2 does not name the fingerprint algorithm, the v1 environment variable names to import (MIG-6 names `VERTEX_AI_*` and `GOOGLE_PSE_CX`), or how v1's provider choice is read. Where are these defined?
- [ ] Q: No machine-readable contract exists in `docs/contracts/` for the commands, the report or the tool map. Should one be written?
- [ ] Q: MIG-FR-23 says rollback needs no data conversion, while MIGRATION-v2 3 says rollback after scrubbing needs the values restored from the scrub backups. Which wording should the requirement carry?
- [ ] Q: The source PRD header cites SPEC v1 sections 9.6 and 5.5 and calls its parent "PRD v3" while linking PRD-v4; this LLD follows SPEC-v2 9.6. Confirm SPEC-v2 as the basis.

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
