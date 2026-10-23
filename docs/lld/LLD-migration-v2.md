---
title: "Migration and Cutover low level design"
type: lld
version: 2
status: draft
owner: "Kenny Hill"
prefix: MIG
component: migration
supersedes: docs/lld/LLD-migration-v1.md
parent: docs/spec/SPEC-v5.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs/lld/LLD-migration-v1.md
date: 2026-10-22
---

# LLD: Migration and Cutover (v2)

Requirements: [PRD-migration v6](../prd/components/PRD-migration-v6.md) (draft; it supersedes v5 and adds MIG-FR-27 and MIG-27 to MIG-35). Security context: [PRD-security v3](../prd/components/PRD-security-v3.md), [LLD-security v2](LLD-security-v2.md) (E37, scrub backups) and [LLD-platform v2](LLD-platform-v2.md) (settings, secrets, redaction, jobs). System design: [SPEC v5](../spec/SPEC-v5.md) sections 6, 9, 10, 12 and 14. Design sources kept from v1: SPEC-v2 section 9.6 (legacy import) and [MIGRATION v2](../../docs-archive/migration/MIGRATION-v2.md) sections 1, 2 and 4. The cutover steps are the [migration cutover runbook](../runbooks/migration-cutover-v1.md); another agent writes its next version, and section 11 lists what it must carry.

Changes from v1: the file-read boundary of every owner-run migration command (a path guard, section 5.4); the scrub backup location, modes and deletion (5.5); the `restore-client-configs` command (5.6); the halt rule (5.7); the install printer reads nothing (5.3); new contracts, schema files and tests; all ten v1 questions resolved; the five v2 questions are answered by owner decisions of 2026-10-23 (section 11); the retire command `retire-v1 --confirm` and MIG-35 are added.

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

This component covers the credential and settings import from the v1 client configs, the optional legacy corpus import, the client config printer, the scrub and restore of client configs, the v1 to v2 tool map, rollback and v1 retirement, and the file-read boundary of each owner-run command. It is governed by SPEC-v5 section 6 (retrieval and cache: the legacy import writes into the cache), section 9 (security: the INV-4 and SEC-INV-7 exception and the INV-6 and NFR-3 exception) and section 12 (deployment and operations: install, client configs, parallel run, retirement).

| Requirement | Criteria | SPEC section |
| --- | --- | --- |
| MIG-FR-1 | MIG-1, MIG-22, MIG-23, MIG-27 | SPEC-v5 9, 12 |
| MIG-FR-2 | MIG-2, MIG-22 | SPEC-v5 12 |
| MIG-FR-3 | MIG-3, MIG-22 | SPEC-v5 12 |
| MIG-FR-4 | MIG-4, MIG-22, MIG-34 | SPEC-v5 12 |
| MIG-FR-5 | MIG-5, MIG-28 | SPEC-v5 9, 12 |
| MIG-FR-6 | MIG-6, MIG-23 | SPEC-v5 12 |
| MIG-FR-10 | MIG-10, MIG-29, MIG-32 | SPEC-v5 6, 9 |
| MIG-FR-11 | MIG-11 | SPEC-v5 6 |
| MIG-FR-12 | MIG-12 | SPEC-v5 6 |
| MIG-FR-13 | MIG-13 | SPEC-v5 6 |
| MIG-FR-14 | MIG-14 | SPEC-v5 6 |
| MIG-FR-15 | MIG-24 (MIG-10 also covers the read-only part) | SPEC-v5 6 |
| MIG-FR-20 | MIG-20, MIG-33 (also PLAT-82, OC-06) | SPEC-v5 12 |
| MIG-FR-21 | MIG-20 (also OC-06) | SPEC-v5 12 |
| MIG-FR-22 | MIG-21 | SPEC-v5 12 |
| MIG-FR-24 | OC-07 | SPEC-v5 12, 14 |
| MIG-FR-25 | MIG-31 (also OC-06) | SPEC-v5 12 |
| MIG-FR-26 | MIG-25, MIG-26, MIG-35 | SPEC-v5 9, 10 |
| MIG-FR-27 | MIG-27 to MIG-34 | SPEC-v5 9 |

MIG-FR-23 was superseded by MIG-FR-25 in PRD-migration v5 and has no row (history only). The invariants MIG-INV-1 (verified by MIG-10), MIG-INV-2 (MIG-1, MIG-22) and MIG-INV-3 (MIG-23) are enforced as described in 4 and 5.7.

Principles (MIGRATION-v2 1):

1. v1 is never modified. Its database is opened immutable; its folder is only read.
2. No credential is re-entered. They move from the v1 client configs into the Keychain.
3. The corpus import is optional. v2 works with an empty cache.
4. Rollback is one config change until v1 is retired; after scrubbing, it also restores the scrubbed values from the scrub backups (MIG-FR-25).
5. Every owner-run migration command reads only its read set (MIG-FR-27). Nothing an agent can trigger is excepted from INV-4 and SEC-INV-7.

Inventory (MIGRATION-v2 2, as of 2026-10-19):

| Item | Where | Notes |
|---|---|---|
| v1 code | `~/Documents/GitHub/my-research-mcp-server` at `568d440` | read-only; never read by v2 |
| v1 data | `~/arxiv-papers`: `arxiv_index.db` (34 MB, 186 rows, 11,403 chunks), 123 PDFs, `embeddings.duckdb` | 54 duplicate pairs; 10 web pages stored by URL |
| v1 datasets | `~/research-datasets` | not inspected; not imported (O4 closed); a read of it is refused (MIG-30) |
| v1 credentials | `env` blocks of the v1 server entries in the Claude desktop, Claude Code and OpenClaw configs | names in the review's credential table; values never read during design |

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

No file in `docs/contracts/` is warranted for this component (v1 question resolved): its public surface is five owner-run CLI commands, a report folder and two small JSON files on disk (3), none consumed by another component or team. The tables below are the contract and go to Gate 3 review.

**Commands** (SPEC-v5 12; PRD-migration v6 2.4):

| Command | Purpose | Read set (5.4) | Criteria |
|---|---|---|---|
| `install [--print-client-config]` | Install the launchd jobs and print client config. | `--print-client-config` reads nothing beyond the v2 install | MIG-20, MIG-33 |
| `secrets list\|import [--dry-run]\|scrub-client-configs\|rotate-token` | Manage Keychain items. `import` and `scrub-client-configs` are the migration commands. | `import`: client configs and `config.toml`. `scrub-client-configs`: client configs only | MIG-1 to MIG-6, MIG-22, MIG-23, MIG-27, MIG-28, MIG-34 |
| `import-legacy <path> [--dry-run] [--mode]` | Import the v1 corpus (SPEC-v2 9.6). | The tree at `<path>`, and `cache.db` | MIG-10 to MIG-14, MIG-29, MIG-32, MIG-34 |
| `restore-client-configs` | Restore the scrubbed `env` values by writing each client config back from its scrub backup (MIG-FR-25). | The scrub backups only | MIG-31 |
| `retire-v1 --confirm` | Delete the scrub backups at retirement by calling `ClientConfigService.retire_v1()` (MIG-FR-26; owner decision, 2026-10-23). | The scrub backups only (the same set as restore) | MIG-26, MIG-35 |

`secrets list` prints names, fingerprints and states only (SPEC-v5 12.1; PLAT-FR-59 for `rotate-token`); it is not a migration command and is outside this component's boundary. `--mode` takes `cache`, `archive` or `metadata_only`; the default is `cache` (MIG-FR-10, MIG-FR-13). The command that deletes the scrub backups at retirement is `research-mcp retire-v1 --confirm` (owner decision, 2026-10-23); it reads and deletes only the scrub-backup set, and the service operation is `ClientConfigService.retire_v1()` (5.5). PRD-migration v6 is being edited in place to add its read-set row and the P1 criterion MIG-35 (traces to MIG-FR-26).

Every command that writes (everything except `install --print-client-config`) asks for explicit confirmation or `--dry-run` first where the table in 5 says so; with no terminal it refuses and writes nothing [assumption: PRD-migration v6 MIG-FR-5 requires "explicit confirmation" for scrub only; restore and retire follow the same rule for symmetry].

**Exit codes** (proposed; the CLI has no code table yet):

| Code | Meaning |
|---|---|
| 0 | Done, or a dry run finished |
| 2 | Usage error, no confirmation, or a rejected argument |
| 3 | A read was refused (5.4); no write happened after the refusal |
| 4 | Owner input needed: conflicting credential values (MIG-2) |
| 5 | Halted: an invariant breach was detected (5.7) |
| 6 | Refused to start: the halt marker exists (5.7) |

**Errors** (use the platform `ErrorCode`, `core/errors.py`; no code is added to the enum, LLD-platform v2 2.1):

| Condition | `ErrorCode` | `detail` | Message rule |
|---|---|---|---|
| A read outside the read set | `blocked_by_policy` | `read_refused` | Names the command and the refused path; never any file content (MIG-30) |
| A symbolic link leaving the v1 tree | `blocked_by_policy` | `link_leaves_tree` | Names the link path (MIG-32) |
| `<path>` is not a v1 data tree, or contains the home folder or a v2 folder | `blocked_by_policy` | `not_v1_tree` | Names the path |
| Conflicting values for one name | `invalid_argument` | `credential_conflict` | Names the credential and the config files, by fingerprint; no value (MIG-2, MIG-22) |
| A client config cannot be parsed as JSON | `invalid_argument` | `unsupported_format` | Names the file; nothing is written |
| v1 database missing at `<path>/arxiv_index.db` | `not_found` | `v1_db_missing` | Names the path |
| Migration commands refused because the halt marker exists | `blocked_by_policy` | `migration_halted` | Names the marker path (5.7) |
| An invariant breach was detected | `internal` | `invariant_breach` | Names the invariant ID and the command; no content, no value (5.7) |

**Service interfaces** (module names in 5):

```python
class ReadGuard:   # services/migration_guard.py
    def open_bytes(self, path: Path) -> bytes: ...
    def open_text(self, path: Path) -> str: ...
    def sqlite_immutable(self, db: Path) -> sqlite3.Connection: ...     # file:...?immutable=1
    def tree_index(self, root: Path) -> TreeIndex: ...                   # lstat walk; refuses an escaping link
    def reads(self) -> tuple[ReadRecord, ...]: ...                       # path, size; no content

class SecretsImportService:       # services/client_configs.py
    def run(self, *, dry_run: bool, choose: Callable[[str, list[ConfigChoice]], str]) -> ImportSummary: ...
class ClientConfigService:        # services/client_configs.py
    def print_config(self) -> list[ClientEntry]: ...                     # reads nothing
    def scrub(self, *, confirm: bool) -> ScrubSummary: ...
    def restore(self, *, confirm: bool) -> RestoreSummary: ...
    def retire_v1(self, *, confirm: bool) -> RetireSummary: ...         # deletes the scrub backups (MIG-26, MIG-35); CLI: retire-v1 --confirm
class LegacyImportService:        # services/legacy_import.py
    def run(self, path: Path, mode: Mode, dry_run: bool) -> ImportReport: ...   # job kind legacy_import
```

`LegacyImportService.run` runs as the job kind `legacy_import`, submitted through `JobService.submit(kind, params) -> job_id` (SPEC-v5 3.6 in the platform LLD v2).

**Keychain items written** by `secrets import`: `research-mcp/<NAME>`, one per imported credential (MIG-FR-1). The Keychain name of each credential comes from the `SourceSpec` that uses it (owner decision, 2026-10-22).

**Settings written** by `secrets import` into `config.toml` (MIG-FR-6; key rows from LLD-platform v2 7.1, verbatim):

| Key | Default | Notes |
|---|---|---|
| `sources.vertex_<name>` | none | `{ instance_of = "vertex_search", project = "...", location = "global", engine_id = "...", title = "..." }`; one per Vertex AI Search engine |
| `sources.google_pse.engine_id` | none | Programmable Search engine id (v1 `GOOGLE_PSE_CX`); not a secret |
| `web.order` | `["vertex_*", "brave_search", "serpapi", "google_pse"]` | `vertex_*` expands to the configured Vertex instances in name order |

The import writes the Vertex settings as the instance `vertex_v1`; when v1 named one provider, it goes first in `web.order` (MIG-FR-6, MIG-6).

**Client config entry** printed by `install --print-client-config`: for each client (Claude desktop, Claude Code, OpenClaw), a server entry that launches `research-mcp stdio`, with no secrets, under the server name `research` (MIG-FR-20, MIG-FR-21; SEC-INV-10).

**Import report files** (SPEC-v2 9.6 step 7): `state_dir/imports/<timestamp>/report.json` and `report.md`, with rows read, works created, merged pairs, unresolved ids, re-extraction failures, chunk counts before and after, and the legacy-id to work-id map (MIG-FR-14). The report also carries `dry_run` and the read ledger of the run (path and size of each file opened, no content; 8).

**v1 to v2 tool map** (MIGRATION-v2 4, verbatim). It covers all 53 v1 tools (MIG-FR-22, MIG-21). The map ships as the data module `src/research_mcp/services/tool_map.py`, a `dict[str, str]` from v1 tool name to the replacement text below, so MIG-21 has a place to test; the 53 v1 names are listed in `tests/migration/fixtures/v1_tool_names.txt` (one per line).

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
| `analytics_sql`, `dataset_query`, `list_datasets` | removed (ADR 0009, O4 closed) |
| `embedding_stats` | `library(action="stats")` (reports coverage) |
| `embed_chunks` | removed: embedding happens at fetch |
| `semantic_search` | `search_cache(query, mode="semantic")` |

The generated v2 inventory (`docs/generated/sources.md`, from `tools/gen_inventory.py --check`) and this table are the inputs for updating agent instructions that mention v1 tool names (MIGRATION-v2 4).

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

This component owns no database table and adds no schema migration. The legacy import writes rows into the `cache.db` tables of the cache LLD (`works`, `identifiers`, `documents`, `files`, `extractions`, `chunks`) through the cache service, never by opening `cache.db` itself (5.4). The columns it sets by name (SPEC-v2 9.6) are:

- `documents.origin_url = pdf_path` and `documents.source = docs_site_<project>` for v1 `iam:<project>:<hash>` rows, which become HTML documents;
- `documents.expires_at = now + 120 d` in mode `cache` (MIG-FR-13);
- `extractions.parser = "v1-import"` for v1 chunks imported where re-extraction fails;
- `identifiers` rows with scheme `legacy` for each raw v1 id of a merged group and for ids with an unknown prefix.

Files are copied into the cache by SHA-256 (`files.sha256`).

**New files on disk (persisted formats; the owner approves them at Gate 3).** All live under one fixed folder `~/.research-mcp-migration/` (mode `0700`), which is not configurable (5.5):

| Path | Mode | Content | Written by | Removed by |
|---|---|---|---|---|
| `~/.research-mcp-migration/` | `0700` | Folder | first scrub | `retire_v1()` when empty |
| `~/.research-mcp-migration/scrub-backups/` | `0700` | Folder | `scrub-client-configs` | `retire_v1()` |
| `scrub-backups/<client>-<utc>.bak` | `0600` | Byte-for-byte copy of one client config file before scrubbing (holds plaintext v1 keys; the approved exception, MIG-FR-26) | `scrub-client-configs` | `retire_v1()` |
| `scrub-backups/manifest.json` | `0600` | See below; no secret value | `scrub-client-configs` | `retire_v1()` |
| `~/.research-mcp-migration/HALTED.json` | `0600` | The halt marker (5.7); no secret value, no file content | a command that detects a breach | the owner, by hand after reading it; no command (owner decision, 2026-10-23) |

`manifest.json` (version 1):

```json
{
  "version": 1,
  "entries": [
    {"client": "claude_code", "original": "<absolute path>", "backup": "claude_code-20261104T120000Z.bak",
     "sha256": "<hex of the backup bytes>", "size": 1234, "mode": "0600", "value_count": 3, "utc": "2026-11-04T12:00:00Z"}
  ]
}
```

`client` is one of `claude_desktop`, `claude_code`, `openclaw`; `original` must equal the candidate path for that client or restore refuses the entry (5.6). `value_count` is the number of `env` values removed; it is not a secret.

`HALTED.json`: `{"version": 1, "utc": "...", "command": "scrub-client-configs", "invariant": "MIG-INV-2", "path": "<refused or offending path or null>"}`.

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

**Settings persisted** by `secrets import`: the `config.toml` keys in section 2. No new settings key is added (7). The code's `src/store/schema.ts` named in the persona file does not exist in this repository (the stores are Python and SQLite); the schema check here is against LLD-platform v2 7.1 and the cache LLD, with no difference found.

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

Reviewed by `security-reviewer` at Gate 3 (2026-10-23). The component-designer proposes the points below; no policy is invented beyond the approved PRDs and SPEC v5 section 9.

| # | Point | Where | Rule | Invariant | Criteria |
|---|---|---|---|---|---|
| M1 | Read set per command | `services/migration_guard.py` `ReadGuard`, built from `ReadSet.for_command(...)` | Every file open by migration code goes through the guard; a path outside the command's read set is refused (5.4) | INV-4 and SEC-INV-7 exception (PRD-migration v6 1.6) | MIG-27 to MIG-31, MIG-33, MIG-34 |
| M2 | Refusal text | `ReadRefused` to `ToolError(blocked_by_policy)` | Names the path, shows no content (2) | INV-4 exception | MIG-30 |
| M3 | Tree containment and links | `ReadGuard.tree_index` | A link whose real path leaves the tree is refused; rows' stored paths are data and are never opened as given (5.1) | MIG-INV-1; exception | MIG-32 |
| M4 | v1 immutable | `ReadGuard.sqlite_immutable`; the tree snapshot taken before and after | `file:...?immutable=1`; the tree is byte-for-byte unchanged | MIG-INV-1, INV-10 | MIG-10 |
| M5 | Credential values in memory only | `Secret` (`platform/secrets.py`); `OutputGate` | Values are wrapped in `Secret` when read from the `env` block; every printed or logged line passes the platform `Redactor` with the imported values registered; a hit blocks the line and halts (5.7) | MIG-INV-2, SEC-INV-4 | MIG-1, MIG-22 |
| M6 | Write only to the Keychain | `SecretProvider.set` (`KeychainProvider`, `security -i` on stdin) | After a run, the files the command wrote are scanned for the imported values (the same scan as SEC-24); a hit halts | MIG-INV-3, SEC-INV-3 | MIG-23 |
| M7 | Scrub backup controls | `BackupStore` in `services/client_configs.py` | Fixed folder, mode `0700`, files `0600`, created with `O_EXCL` and `O_NOFOLLOW`, never inside a synced folder or the folders SEC-24 scans; checked at every use (5.5) | INV-6 and NFR-3 exception (E37) | MIG-25, MIG-26 |
| M8 | Restore manifest check | `ClientConfigService.restore` | A manifest entry whose `original` is not one of the three client config paths, or whose `backup` leaves the backup folder, is refused | exception; SEC-INV-7 | MIG-31 |
| M9 | Halt marker | `HaltGuard` | A detected breach writes the marker (0600, no value); while it exists only `secrets import`, `scrub-client-configs`, `import-legacy` and `retire-v1 --confirm` refuse; `restore-client-configs` and the printer still run (5.7). `retire-v1 --confirm` (owner decision, 2026-10-23; MIG-35) reads only the backup folder through a `ReadGuard` and refuses a symbolic link as the folder or any manifest entry (G2, G3) | PRD-v7 2.6 | design tests (9) |
| M10 | No client holds the daemon token | `ClientConfigService.print_config` | The printed entries contain no secret and launch `research-mcp stdio` | SEC-INV-10 | MIG-20, PLAT-82 |

The exception covers owner-run commands only. The guard is not imported by `mcp_app/`, and a static test fails if any `mcp_app/` or tool module imports `migration_guard` (9, MIG-30 companion), so no MCP tool can reach a migration read (SPEC-v5 9).

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

| Module | Contents |
|---|---|
| `src/research_mcp/cli.py` | The `install`, `secrets` (`import`, `scrub-client-configs`), `import-legacy`, `restore-client-configs` and `retire-v1` commands. Each migration command starts with `migration_bootstrap()` (below), not the generic settings load |
| `src/research_mcp/services/migration_guard.py` | `ReadSet`, `ReadGuard`, `ReadRefused`, `TreeIndex`, `HaltGuard`, `OutputGate`, `TreeSnapshot` (5.4, 5.7) |
| `src/research_mcp/services/client_configs.py` | `ClientPaths`, `SecretsImportService`, `ClientConfigService`, `BackupStore` (5.2, 5.3, 5.5, 5.6) |
| `src/research_mcp/services/legacy_import.py` | `LegacyImportService` (5.1); the path in `sdd.config.json` for this component |
| `src/research_mcp/services/tool_map.py` | `V1_TOOL_MAP` (2) |
| `src/research_mcp/platform/secrets.py` | `SecretRef`, `SecretProvider`, `KeychainProvider`, `FakeProvider`, `Secret` (fingerprint is `sha256(value)[:8]`, LLD-platform v2 4.1) |
| `src/research_mcp/platform/jobs.py` | `JobService`, `Job`, `JobKind` (job kind `legacy_import`) |
| `src/research_mcp/platform/workers.py` | `WorkerRunner`, which runs the re-extraction tasks |

**`migration_bootstrap()`.** The generic CLI start loads `Settings`, which opens `config.toml`. That would put `config.toml` in the read set of `scrub-client-configs`, `restore-client-configs`, `retire-v1`, `install --print-client-config` and `import-legacy`, where the PRD does not list it. So each migration command bootstraps without `Settings`: fixed paths (the backup folder, the default state folder), the daemon port from `RESEARCH_MCP_SERVER__PORT` or its default 7319, and the daemon token from the Keychain. `secrets import` alone reads `config.toml`, and only through its guard. A daemon on a non-default port makes `import-legacy` fail to connect (a visible error, not a wrong read). The generic CLI `config.toml` read and the daemon's own `state.db` and log opens stay outside the per-command read sets [assumption; owner decision, 2026-10-23, handled here and in 5.4]. The daemon reads its own `config.toml` at its own start; that is not a read by the command.

**Client config locations.** `ClientPaths(home)` builds the three candidates from an injected home folder, so tests use a fake home:

| Client | Candidate file | Basis |
|---|---|---|
| Claude desktop | `<home>/Library/Application Support/Claude/claude_desktop_config.json` | assumption: the usual macOS location |
| Claude Code | `<home>/.claude.json` | assumption: the usual user-scope file |
| OpenClaw | `<home>/.openclaw/openclaw.json` | assumption: not stated in the sources |

The three paths are confirmed (owner decision, 2026-10-23). A symbolic link as the final component is refused (G2): the owner replaces the link with the file, or pastes by hand (owner decision, 2026-10-23). The v1 server entry is the entry whose `command` or `args` name `my-research-mcp-server` [assumption]. Build step: the implementer reads, read-only from the v1 repository, how the v1 server entry is recognized and which `env` variable names the preferred web provider, replaces the assumption with those facts, and lists both for the owner to confirm at review (owner decision, 2026-10-23).

### 5.1 Legacy import (SPEC-v2 9.6 and MIG-FR-10 to MIG-FR-15)

`LegacyImportService.run(path, mode, dry_run)` runs as the job kind `legacy_import`, inside the daemon:

0. **Guard.** Build `ReadGuard(ReadSet.legacy_import(path, cache_db))`. Validate `<path>` (5.4 rule G6): `<path>/arxiv_index.db` exists, and `<path>` is neither the home folder nor an ancestor of it nor of a v2 folder. Take `TreeSnapshot` of `<path>` (relative path, size, mtime_ns, inode of every entry; `lstat` only). Run `tree_index(path)`, which refuses any link whose real path leaves the tree (MIG-32).
1. Open `<path>/arxiv_index.db` through `ReadGuard.sqlite_immutable`, as `file:...?immutable=1`, so no WAL or SHM files are created (MIG-10).
2. Run the inventory and the pre-import queries (3).
3. Map each row:
   - arXiv ids go through `normalize_arxiv`;
   - `doi:` and `doi/` go through `normalize_doi`;
   - `core:` and `core/` map to the `core` scheme;
   - `iam:<project>:<hash>` becomes an HTML document with `origin_url = pdf_path` and `source = docs_site_<project>` (the name form is confirmed by MIG-FR-11);
   - anything else maps to the `legacy` scheme, followed by a title lookup through `get_work`; a failed lookup leaves the `legacy` id and is listed under unresolved ids (MIG-FR-11, MIG-FR-14).
4. Group rows by normalized id and by file path. Keep the row with a non-empty title for metadata, and record both raw ids as `legacy` identifiers.
5. **Files.** A row's `pdf_path` is data, never a path to open (it could name any file if the database were altered). The importer resolves it to the tree by its final name component with `TreeIndex.by_name(name)`; no match, or more than one, is an unresolved id. The resolved file is read through the guard, its first bytes must be `%PDF`, and it is copied into the cache by SHA-256 and re-extracted with the v2 worker (MIG-FR-12). If extraction fails, import the v1 chunks for that document with `parser="v1-import"`. `embeddings.duckdb` is in the read set but is never opened: v2 re-extracts and re-embeds, and uses no DuckDB (ADR 0008) [inferred; a test asserts it is not opened].
6. Set each document's state by mode: `cache` (default) `expires_at = now + 120 d`; `archive` archives each document; `metadata_only` creates works and identifiers only.
7. **Cache access.** The service reaches `cache.db` only through the injected cache service (a port); it opens no v2 file itself. The v2 files this touches are `cache.db` and its SQLite sidecars (`-wal`, `-shm`), which the read set treats as part of `cache.db` (MIG-34).
8. **Post-check.** Take `TreeSnapshot` again; any difference (including a new `-wal` or `-shm`) is a MIG-INV-1 breach and halts (5.7).
9. Write `state_dir/imports/<timestamp>/report.json` and `report.md`.

**Dry run** (v1 question resolved; basis: PRD-migration v6 2.3 "run with `--dry-run`, review the report", MIG-FR-10): steps 0 to 4 and the file resolution of step 5 run; nothing is copied, extracted or written to the cache; the report is written with `dry_run: true`, "would create" counts, and the unresolved ids.

In mode `cache`, imported items go through the normal review (MIG-FR-13). Running the import is optional; v2 works fully with an empty cache (MIG-FR-15, MIG-24).

### 5.2 Credential and settings import

`SecretsImportService.run(dry_run, choose)` (MIG-FR-1 to MIG-FR-4, MIG-FR-6). Build `ReadGuard(ReadSet.secrets_import(paths))` with the three candidate files and `config.toml`:

1. For each candidate in the order desktop, Code, OpenClaw: if `lstat` finds no file, report "not found" and go on. Otherwise open it through the guard, parse JSON and find the v1 server entry (MIG-27).
2. Wrap each `env` value in `Secret` at once and register it with the `OutputGate` redactor. From here no code path holds a value in a plain `str` beyond the call to `SecretProvider.set`.
3. For each name that a v2 source's `SourceSpec` declares as a credential (this includes the Brave and SerpAPI keys and the Google key shared by the Developer Knowledge and Programmable Search sources), write it to the Keychain as `research-mcp/<NAME>`. A name no `SourceSpec` uses is listed as "not imported" with a note and is not copied (MIG-3). This resolves where the names are defined: the v1 `env` names equal the v2 names by design, and the set of used names is the union over the `SourceSpec` registry.
4. If one name has different values in different configs, call `choose(name, choices)` with fingerprints only; no value is ever offered. Without an answer, stop for that name with `credential_conflict` (MIG-2).
5. Read `config.toml` through the guard (this keeps the run idempotent, MIG-FR-4). Write the v1 web-search settings as in section 2 with the platform `config set` writer, and print each setting written (MIG-6). The v1 variable that names the preferred provider is a build step: read from the v1 repository, listed for owner confirmation (5, client config locations) [assumption until then].
6. Print names, fingerprints and the config file each came from, through `OutputGate`.
7. With `--dry-run`, run steps 1 to 6 up to the writes, print what would be written, and write nothing: no Keychain call, no `config.toml` write (MIG-4).
8. Post-check: scan the files the run wrote for any registered value (M6, MIG-23).

A repeated run reads the same inputs and writes the same Keychain values and settings (MIG-4). The Keychain write for an unchanged value is skipped by comparing fingerprints from `SecretProvider.get` [assumption: `get` is allowed in a CLI import; it reveals nothing to output].

### 5.3 Client config printer, cutover and rollback

- `install --print-client-config`: `ClientConfigService.print_config()` builds the three entries from constants and the path of the running executable (`sys.argv[0]` resolved without opening any file). It builds a `ReadSet` with no file and no tree, so any open by this command is refused. It prints entries that launch `research-mcp stdio` under the name `research`, with no secret (MIG-FR-20, MIG-33; SEC-INV-10). The install step that follows writes the launchd plists (write targets, not reads) and generates the daemon token (PLAT-FR-59).
- The v2 entry is added beside the v1 entry under the name `research`; the v1 entry is disabled, not deleted, at cutover (MIG-FR-21; ADR 0001). The owner pastes entries by hand; no command edits a client config except `scrub-client-configs` and `restore-client-configs`.
- `secrets scrub-client-configs`: 5.5.
- Rollback until retirement is re-enabling the v1 entry (MIG-FR-25), which needs no data conversion. After scrubbing, `restore-client-configs` writes back the scrubbed values (5.6). v1 is retired only after 14 days of daily use on v2 with no fallback and the owner's explicit go-ahead (MIG-FR-24); retirement runs `research-mcp retire-v1 --confirm`, which deletes the scrub backups (5.5). The step-by-step procedure is the [cutover runbook](../runbooks/migration-cutover-v1.md).

### 5.4 File-read boundary (MIG-FR-27, MIG-27 to MIG-34)

**Read sets** (from PRD-migration v6 2.4; `ReadSet` is a frozen value built per command):

| Command | `files` (exact) | `trees` | Criteria |
|---|---|---|---|
| `secrets import` | the three client config candidates; `~/.config/research-mcp/config.toml` | none | MIG-27, MIG-34 |
| `secrets scrub-client-configs` | the three client config candidates | none | MIG-28 |
| `import-legacy <path>` | `~/Library/Application Support/research-mcp/cache/cache.db` and its `-wal`, `-shm` sidecars (confirmed by the owner, owner decision, 2026-10-22; PRD-migration v6 2.13) | `<path>` | MIG-29, MIG-32, MIG-34 |
| `install --print-client-config` | none | none | MIG-33 |
| `restore-client-configs` | `scrub-backups/manifest.json` | `~/.research-mcp-migration/scrub-backups/` (flat; regular files only) | MIG-31 |
| `retire-v1 --confirm` | `scrub-backups/manifest.json` | `~/.research-mcp-migration/scrub-backups/` (flat; regular files only; the same set as restore; PRD-migration v6 row added 2026-10-23) | MIG-35 |

The scrub and restore write targets (client configs, the backup folder) and the Keychain, `config.toml`, report folder writes are not reads (PRD-migration v6 2.4) and are governed by 5.2 to 5.6.

**Guard rules.** `ReadGuard` is the only door; no other function in the migration modules opens a file, lists a folder or connects to SQLite.

- **G1 Normalize.** `p = os.path.abspath(os.path.expanduser(path))`, which resolves `..` first (the M0-04 rule of LLD-platform v2 7.1). No later check uses the raw argument.
- **G2 Exact files.** `p` must equal a listed file by its normalized path. The final component must not be a symbolic link (checked with `lstat`) and must be a regular file; it is opened with `O_RDONLY | O_NOFOLLOW`. A linked dotfile is refused; the owner replaces the link with the file or pastes by hand (owner decision, 2026-10-23).
- **G3 Trees.** `p` must lie lexically under a listed root. Then `real = os.path.realpath(p)` must lie under `realpath(root)`, or the guard raises `ReadRefused(reason="link_leaves_tree")` naming `p`. The file is opened by `real` with `O_NOFOLLOW`, then `fstat` must show a regular file.
- **G4 Folders.** `tree_index` and `iterdir` walk with `lstat` and `os.scandir`, never follow a linked folder, and apply G3 to every link they meet. A listing of a path that is not a listed root is refused.
- **G5 SQLite.** `sqlite_immutable(db)` applies G2 or G3 to `db`, then connects with `file:<real>?immutable=1` and `mode=ro`. The guard refuses sidecars of a v1 database it did not list.
- **G6 Tree root.** For `import-legacy`, `<path>` must contain `arxiv_index.db`, and must not be the home folder, an ancestor of it, or an ancestor of `~/Library/Application Support/research-mcp`, `~/.config/research-mcp` or `~/.research-mcp-migration`. This is how `~/research-datasets` (no `arxiv_index.db`) is refused with an error that names it (PRD-migration v6 2.12), and how a pointer at `~` is refused. The check uses `lstat` only.
- **G7 Refusal.** A violation raises `ReadRefused(command, path, reason)` before any open. The CLI maps it to `blocked_by_policy`, exit 3, with the message "`<command>` may not read `<path>`" and no content (MIG-30). Reading the offending file in order to report it is never done.
- **G8 Ledger.** The guard records each successful open (path, size) for the report and for 8; it never records content.

**Enforcement in depth.** The guard is the design, and three checks keep code from bypassing it:

1. A static test (`tests/migration/test_no_direct_io.py`) parses `services/client_configs.py`, `services/legacy_import.py` and `services/migration_guard.py`, and fails on any call to `open`, `io.open`, `os.open`, `os.scandir`, `os.listdir`, `Path.open`, `Path.read_text`, `Path.read_bytes`, `Path.iterdir`, `Path.glob`, `Path.rglob`, `sqlite3.connect` or `duckdb.connect` outside `migration_guard.py` (and outside the write helpers of `BackupStore`, which are listed by name).
2. Each criterion's test (9) runs the command in a fake home beside decoy files and records every `open`, `sqlite3.connect`, `os.scandir` and `os.listdir` event with a Python audit hook (`sys.addaudithook`, installed once in `tests/migration/conftest.py` as `OpenRecorder`). It asserts that the set of paths opened under the fake home is a subset of the read set plus the declared write targets, and that no decoy path appears. The decoys are `~/research-datasets/data.db`, `~/.ssh/decoy_key`, `~/Documents/decoy.txt`, `~/Library/Application Support/Other/decoy.json`, and a second client-looking file `~/.claude/settings.json`; each holds the sentinel text `DECOY-SENTINEL`, which the test searches for in the command's output and logs.
3. In the CLI process (not the daemon), `migration_bootstrap()` installs a runtime audit hook that raises on an `open` event for a path under the home folder that is outside the read set, the declared write targets, `sys.prefix`, `sys.base_prefix` and the Python bytecode folders. It is defence in depth; the hook cannot be removed once installed and lives only as long as the command. In the daemon the job runs under the guard and the post-checks only, because the daemon has many unrelated opens.

**Declared write targets** (not reads, allowed by the recorder): the Keychain subprocess, `config.toml` (secrets import only, after its guarded read), `state_dir/imports/<timestamp>/`, the cache files folder, the scrub backup folder and the three client configs (scrub and restore), and the log files. In the integration tests the job store is a fake in memory, so `state.db` is not opened by migration code; in production the daemon opens `state.db` and its log files for its own job record and logs, which is daemon infrastructure and not a read by the command (assumption; owner decision, 2026-10-23: both stay outside the read sets).

### 5.5 Scrub and the scrub backups (MIG-FR-5, MIG-FR-26)

Location (resolves the SPEC-v5 9 item "the migration LLD sets the exact path at Gate 3"; owner decision, 2026-10-22, delegated the path to this LLD): a fixed folder `~/.research-mcp-migration/scrub-backups/` in the home folder, mode `0700`. It is outside `~/.config/research-mcp`, `~/Library/Application Support/research-mcp` and `~/Library/Logs/research-mcp`, so SEC-24 and the NFR-3 scan apply to those without exception. It is not configurable, because a setting could move it into a synced folder. `BackupStore` checks the folder before every scrub, restore and retire, and after writing; any failure is a breach (5.7, T4):

- the folder and `scrub-backups/` exist as real directories (not links), owned by the current user, mode exactly `0700`;
- `realpath` of the folder is not under `~/Library/CloudStorage`, `~/Library/Mobile Documents`, `~/Documents`, or `~/Desktop` (the fixed list holds the usual sync roots only, because the confirmed `archive.target` would need `config.toml`, which scrub may not read [assumption]);
- every file in it is a regular file of mode `0600` owned by the current user.

`ClientConfigService.scrub(confirm)`, with `ReadSet.scrub(paths)`:

1. For each candidate file that exists, read it through the guard and parse JSON. If it is not valid JSON (for example JSON with comments), stop for that file with `unsupported_format` and write nothing for it.
2. Find the v1 server entries. Count the `env` values to remove. A file with none is skipped ("nothing to scrub"), so a second run writes no backup (idempotent).
3. Show, per file, the path, the entry names, the count and the fingerprints of the values, never the values. Proceed only on explicit confirmation (`confirm`); with no terminal or no confirmation, exit 2 and write nothing (MIG-FR-5).
4. For each file: create the folder if missing (`os.mkdir` with mode `0700`, then `chmod`), run the folder checks, then write the backup: `os.open(name, O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW, 0o600)`, `fchmod(fd, 0o600)`, write the bytes already read, `fsync`; check `fstat` for mode and size. The backup is not read back (the scrub read set does not include it); integrity comes from the in-memory SHA-256 of the buffer that was written, recorded in the manifest. Write `manifest.json` atomically (temp in the same folder, mode `0600`, `os.replace`).
5. Write the scrubbed config atomically beside the original (temp file `.<name>.rmcp-tmp`, original mode copied, `fsync`, `os.replace`). Only the `env` values of the v1 entries are replaced by the empty string; keys, other entries and key order are kept. The file is re-serialized with `json.dumps(indent=2)` (formatting may change; accepted, owner decision, 2026-10-23). Non-secret values such as `GOOGLE_PSE_CX` are also blanked, because MIG-5 says "remove only the v1 env values" and the settings already live in `config.toml` [inferred].
6. Post-check: the scrubbed bytes contain none of the registered values (MIG-INV-2 scan); the backup folder checks pass again.

`ClientConfigService.retire_v1(confirm)` (MIG-FR-26, MIG-26, MIG-35), called by `research-mcp retire-v1 --confirm` (owner decision, 2026-10-23), which reads and deletes only the scrub-backup set: requires explicit confirmation as the recorded owner go-ahead (the PRD-v7 2.6 halt condition forbids deletion without a recorded owner decision). It reads `manifest.json` through a `ReadGuard` whose read set is the backup folder (the same set as restore), deletes each file the manifest names, then `manifest.json`, then `scrub-backups/`, then `~/.research-mcp-migration/` if empty. A file in the folder that the manifest does not name is listed and left in place, not deleted, because it was not recorded as a backup. The result is logged by name and count. APFS gives no guarantee that unlinked data is erased [assumption; not addressed by the sources].

### 5.6 Restore (MIG-FR-25, MIG-31)

`ClientConfigService.restore(confirm)` with `ReadSet.restore(backup_dir)`:

1. Run the backup folder checks (5.5). Read `manifest.json` through the guard; for each client take the oldest entry with `value_count > 0`.
2. Refuse (`read_refused`) an entry whose `original` is not the candidate path for its `client`, or whose `backup` name is not a plain file name inside the folder (M8). A manifest is data, not a trusted path list.
3. Read the backup through the guard and check its SHA-256 against the manifest; a mismatch is a breach (T4) and halts.
4. Show what will be restored and confirm. Without confirmation, exit 2 and write nothing.
5. The command cannot read the current client config (not in its read set). To avoid losing later edits, it writes the backup bytes to a temp file beside the original, creates a hard link of the current file as `<name>.pre-restore-<utc>` (a link is not a read; if the link fails, stop before replacing), then `os.replace` the temp over the original. This restores the whole file as it was at scrub time. Because step 8 of the runbook (disable v1) came before the scrub, the restored v1 entry is still disabled: re-enabling it is the owner's step (MIG-FR-25: rollback is re-enabling v1).
6. Restore leaves the backups in place for a later rollback; only retirement deletes them (MIG-26).
7. Restore is allowed while the halt marker exists (5.7), because rollback is the safe direction.

### 5.7 Halt rule on an invariant breach (PRD-v7 2.6; PRD-migration v6 2.9)

PRD-v7 2.6 halts the rollout on any invariant breach, including MIG-INV-1 to MIG-INV-3. In code, a refusal is the guard working; a breach is an invariant failing, or a sign that migration code or an input tried to leave its boundary. The service halts on:

| ID | Trigger | Detected by |
|---|---|---|
| T1 | MIG-INV-1: the v1 tree differs after a run (a size, mtime, inode, an added or removed entry such as `-wal` or `-shm`) | `TreeSnapshot` before and after (5.1 steps 0 and 8) |
| T2 | MIG-INV-2: a registered credential value is in a line about to be printed or logged | `OutputGate` (the platform `Redactor` with the imported values registered); the line is blocked, never emitted |
| T3 | MIG-INV-3: a registered value is found in a file the run wrote, other than through the Keychain provider | post-run scan of the declared write targets (M6) |
| T4 | The INV-6 and NFR-3 exception limits fail: a backup folder or file with a wider mode, another owner, a link, a synced location, or a hash mismatch | `BackupStore` checks (5.5, 5.6) |
| T5 | The INV-4 and SEC-INV-7 exception fails: a read outside the read set that did not come from an operator-typed argument (a manifest entry, a database path, a link in the tree, or the CLI audit hook seeing an open outside the set) | `ReadRefused(origin="internal")`, or the CLI audit hook |

An operator-typed argument that fails G6 (for example `import-legacy ~/research-datasets`) is a plain refusal (exit 3, no marker), because nothing was read and the owner can retry with the right path.

On a breach, `HaltGuard.halt(invariant, command, path)`:

1. Stops the command at once: no further read, write or Keychain call, and no cleanup that touches more files (a half-scrubbed set is safe: every scrubbed file already has its backup).
2. Writes `~/.research-mcp-migration/HALTED.json` (3) with mode `0600`, creating the folder with `0700` if needed. The marker has no content from any file and no value.
3. Prints one line through `OutputGate`: the invariant ID, the command, the path if any, and the marker path; exits 5. It logs `migration.halt` through the redactor with the same fields.
4. While the marker exists, only the commands that read or write credentials or the v1 tree refuse (`secrets import`, `scrub-client-configs`, `import-legacy` and `retire-v1 --confirm`), with exit 6, `migration_halted`, naming the marker path. `restore-client-configs` and `install --print-client-config` still run. The check uses `lstat` on the marker; no command reads the marker, since it is outside every read set.
5. The rollout is halted by the owner's acts, not by the code: the cutover runbook step list stops at the failed step and the owner decides (PRD-migration v6 2.9; support is the owner alone). Clearing the marker is the owner's act: the owner deletes `~/.research-mcp-migration/HALTED.json` by hand after reading it; no command clears it (owner decision, 2026-10-23).

The platform health or `doctor` display of the marker is for the `sre` and the health LLD to decide; this LLD adds no health check.

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

| Condition | Behavior | Source |
| --- | --- | --- |
| One credential name has different values in different configs | Stop the import for that name and ask which config wins, by fingerprint; do not guess; exit 4 | MIG-FR-2, MIG-2 |
| A v1 credential no v2 source uses | Report it as "not imported" with a note; do not copy it | MIG-FR-3, MIG-3 |
| `secrets import` run again | Idempotent: same inputs, same writes, an unchanged value is not rewritten | MIG-FR-4, MIG-4 |
| `--dry-run` on `secrets import` | Show what would be written; no Keychain call, no `config.toml` write | MIG-FR-4, MIG-4 |
| `--dry-run` on `import-legacy` | Steps 0 to 4 and file resolution; report written with `dry_run: true`; nothing else | 5.1; MIG-FR-10 |
| A read outside a command's read set | Refuse with the path named and no content; exit 3; nothing more is read | MIG-FR-27, MIG-30 |
| A symbolic link leaving the v1 tree | Refuse the import before any write; name the link; this is a T5 breach if found while indexing and halts | MIG-32; 5.7 |
| `<path>` is not a v1 tree (no `arxiv_index.db`, or contains home) | Plain refusal; no marker | 5.4 G6 |
| A v1 row's `pdf_path` is absolute or names another folder | The path is not opened; the file is looked up by name in the tree; no match is an unresolved id | 5.1 step 5 |
| Unknown v1 id prefix (`harv...`, `penn...`) | Map to the `legacy` scheme, then a title lookup through `get_work`; a failed lookup is listed as unresolved | MIG-FR-11, MIG-11 |
| Two v1 rows share a normalized id or a file path | Merge; keep the titled row's metadata; record both raw ids as `legacy` identifiers | MIG-11 |
| Re-extraction fails | Import the v1 chunks for that document with `parser="v1-import"` | MIG-FR-12, MIG-12 |
| A worker task crashes or is killed | The task ends with code `extract_failed`; only that task is affected | LLD-platform v2 5 |
| Legacy import job interrupted (daemon stop) | The job ends `failed`; re-running is safe: files are keyed by SHA-256, works by normalized id, so no duplicate is created [inferred from the keys; the cache LLD owns the upsert rules] | MIG-FR-10 |
| A client config is not plain JSON | `unsupported_format`; nothing written for that file | 5.5 |
| `scrub-client-configs` run again | Files with nothing left to scrub are skipped; no new backup | 5.5 |
| Backup folder or file fails a mode, owner, link, location or hash check | Halt (T4) | MIG-25 |
| The v1 tree changed during an import | Halt (T1) | MIG-10 |
| A credential value reaches an output line or a written file | Halt (T2, T3) | MIG-22, MIG-23 |
| Rollback after `scrub-client-configs` | `restore-client-configs` writes the backed-up files; the owner re-enables the v1 entries | MIG-FR-25, MIG-31 |
| `restore` link of the current file fails | Stop before replacing; nothing changed | 5.6 |
| A halt marker exists | `secrets import`, `scrub-client-configs`, `import-legacy` and retire refuse (exit 6); restore and the printer run | 5.7 |

There are no automatic retries: every migration command is owner-run and short, and a failure ends the command with a code the owner reads.

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

This component adds no `config.toml` key and no feature flag. Its behaviors are owner-run commands, so the opt-in is running the command: the legacy import runs only when the owner starts it (MIG-FR-15), `scrub-client-configs` and `restore-client-configs` only on explicit confirmation (MIG-FR-5, MIG-FR-25), and retirement only on the owner's go-ahead (MIG-FR-24). The platform flag table (LLD-platform v2 7.2) lists none for migration, and none is added (follows the platform LLD v2; no feature-flag PRD exists). The read boundary has no off switch: a switch would defeat the exception it limits.

| Flag | Default | Safe to switch off? |
| --- | --- | --- |
| none | not applicable | Not applicable: each behavior is an explicit command; not running it loses no data, changes no tool list, and leaves hooks and the daemon unaffected |

Command options: `--dry-run` (both imports) and `--mode` for `import-legacy` (`cache`, the default; `archive`; `metadata_only`). The import reads `paths.state_dir` (through the daemon) for the report location and writes the settings listed in section 2. The 120-day expiry matches `cache.retention_days = 120` (LLD-platform v2 7.1; ADR 0011). Fixed constants, not settings: the folder `~/.research-mcp-migration/` and its modes, the three client config candidates, and the exit codes.

## 8. Observability

> **Owner:** A · **Persona:** `sre`

Reviewed by `sre` at Gate 3 (2026-10-23) against SPEC-v5 12, PRD-v8 2.6 and PRD-migration v6; not approved. Log event names use the `migration.` prefix, which no other LLD uses (platform and security define none; UI uses `ui.`).

- `secrets import` prints names, fingerprints, the source config file and each setting written; never values (MIG-FR-1, MIG-FR-6, MIG-22). Every line goes through `OutputGate`.
- Each migration command prints, at the end, a read ledger: the number of files opened and their paths (no content), so the owner sees what was read (G8). The legacy import report carries the same ledger.
- Log events (redacted, JSON lines): `migration.read_refused` (command, path), `migration.halt` (invariant, command, path), `migration.backup_written` (client, size, no content), `migration.backups_deleted` (count and paths, from `retire-v1 --confirm`; MIG-35). None carries a value or file content.
- The legacy import runs as a job; its state lives in `state.db.jobs`, and progress is pushed to MCP `Context.report_progress` while the caller waits (LLD-platform v2 5).
- The legacy import report (section 2) records rows read, works created, merged pairs, unresolved ids, re-extraction failures, chunk counts before and after, and the legacy-id to work-id map (MIG-FR-14).
- Cutover checks use `research-mcp doctor`, the Credentials page and the source board (runbook; MIGRATION-v2 3). Showing a halt marker in `doctor` is not designed here (5.7).
- **Halt detection and clearing.** A breach is detected by the command itself, which writes `~/.research-mcp-migration/HALTED.json`, prints one line, exits 5 and logs `migration.halt`; later migration commands exit 6 with `migration_halted` (5.7). No runtime alert exists beyond that. The owner clears the marker by deleting the file by hand after reading it (owner decision, 2026-10-23; the runbook says the same).

No component NFR is defined (PRD-migration v6 2.5), so no numeric threshold applies here. The halt rules trace to PRD-v8 2.6, and the no-secret rule to NFR-4.

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

Reviewed by `test-architect` at Gate 3 (2026-10-23). Test plan v4 carries a row for every criterion, MIG-1 to MIG-35, with the names below.

Shared fixtures in `tests/migration/conftest.py`: `fake_home` (a temp folder used as `HOME`, with the three client configs holding fake v1 entries with fake keys, a fake `config.toml`, and the decoys listed in 5.4), `fake_provider` (`FakeProvider`), `OpenRecorder` (the audit hook of 5.4, active only while a test uses it), and `make_v1_db` (`tests/migration/fixtures/make_v1_db.py`, the synthetic v1 database with 54 pairs, 10 URL rows and harv and penn ids). Tests never read the Keychain or real client configs (MIG-1; test plan v4 section 7). Offline only (NFR-9).

| Criterion | Planned test | Level | Design element |
| --- | --- | --- | --- |
| MIG-1 | `tests/migration/test_secrets_import.py::test_writes_keychain_items_prints_names_and_fingerprints_only` | integration | 5.2 |
| MIG-2 | `tests/migration/test_secrets_import.py::test_conflicting_values_stop_and_ask_by_fingerprint` | integration | 5.2 step 4 |
| MIG-3 | `tests/unit/services/test_secrets_import.py::test_imports_used_names_and_reports_unused_as_not_imported` | unit | 5.2 step 3 |
| MIG-4 | `tests/migration/test_secrets_import.py::test_idempotent_and_dry_run_writes_nothing` | integration | 5.2 steps 5, 7 |
| MIG-5 | `tests/migration/test_scrub.py::test_scrub_backs_up_then_removes_only_v1_env_values` | integration | 5.5 |
| MIG-6 | `tests/unit/services/test_secrets_import.py::test_web_search_settings_to_config` | unit | 5.2 step 5 |
| MIG-10 | `tests/migration/test_legacy_import.py::test_v1_folder_byte_for_byte_unchanged` (fixture `make_v1_db.py`) | integration | 5.1 steps 1, 8 |
| MIG-11 | `tests/migration/test_legacy_import.py::test_maps_ids_merges_pairs_and_html_documents` | integration | 5.1 steps 3, 4 |
| MIG-12 | `tests/migration/test_legacy_import.py::test_reextracts_and_falls_back_to_v1_chunks` | integration | 5.1 step 5 |
| MIG-13 | `tests/migration/test_legacy_import.py::test_cache_mode_gives_120_day_expiry` | integration | 5.1 step 6 |
| MIG-14 | `tests/migration/test_legacy_import.py::test_report_has_every_field` | integration | 5.1 step 9 |
| MIG-20 | `tests/unit/services/test_client_configs.py::test_print_config_for_three_clients_without_secrets` | unit | 5.3 |
| MIG-21 | `tests/unit/services/test_tool_map.py::test_covers_all_53_v1_tools` | unit | 2 (`V1_TOOL_MAP`) |
| MIG-22 | `tests/migration/test_secrets_import.py::test_prints_no_credential_value` (normal, dry run, conflict, not-imported, error paths) | integration | M5, `OutputGate` |
| MIG-23 | `tests/migration/test_secrets_import.py::test_leaves_no_credential_value_at_rest` | integration | M6 |
| MIG-24 | `tests/migration/test_empty_cache.py::test_search_get_work_and_fetch_without_legacy_import` | integration | 5.1 (optional) |
| MIG-25 | `tests/unit/services/test_client_configs.py::test_scrub_backup_is_owner_only` (the test plan names `test_legacy_import.py`; the scrub code is in `client_configs.py`, 11) | unit | 5.5 |
| MIG-26 | `tests/migration/test_retirement.py::test_retire_deletes_scrub_backups` | integration | 5.5 `retire_v1` |
| MIG-27 | `tests/migration/test_read_boundary.py::test_secrets_import_opens_only_client_configs` | integration | 5.4 read set row 1 |
| MIG-28 | `tests/migration/test_read_boundary.py::test_scrub_opens_only_client_configs` | integration | 5.4 row 2 |
| MIG-29 | `tests/migration/test_read_boundary.py::test_import_legacy_opens_only_files_under_the_tree` | integration | 5.4 row 3 |
| MIG-30 | `tests/migration/test_read_boundary.py::test_read_outside_set_is_refused_naming_path_without_content` (parametrized over the five commands and the sentinel) | integration | G7, M2 |
| MIG-31 | `tests/migration/test_read_boundary.py::test_restore_opens_only_scrub_backups` | integration | 5.6 |
| MIG-32 | `tests/migration/test_read_boundary.py::test_import_legacy_refuses_link_leaving_tree` | integration | G3, G4 |
| MIG-33 | `tests/migration/test_read_boundary.py::test_print_client_config_opens_no_file` | integration | 5.3, empty read set |
| MIG-34 | `tests/migration/test_read_boundary.py::test_v2_tree_reads_stay_at_listed_paths` (`config.toml` for `secrets import`; `cache.db` and sidecars for `import-legacy`) | integration | 5.4 |
| MIG-35 | `tests/migration/test_read_boundary.py::test_retire_v1_opens_only_scrub_backups` (also asserts `retire-v1` without `--confirm` deletes nothing and reads no decoy) | integration | 5.4 row 6, 5.5 `retire_v1` |

How the boundary tests work (MIG-27 to MIG-34): each runs the command through its service entry in `fake_home`, with `OpenRecorder` active, then asserts (a) every recorded open under the fake home is in the read set or the declared write targets, (b) no decoy path was recorded, (c) the sentinel text appears in no output or log. MIG-27 and MIG-28 put all three client configs and a fourth look-alike (`~/.claude/settings.json`) in the fake home; the candidate list is fixed, so the look-alike is never opened. A candidate that exists but holds no v1 entry is opened once to find that out; the tests use configs that all hold the entry, which is how MIG-27 and MIG-28 read ("files that hold the v1 server entry") [inferred: a file cannot be known to hold the entry without opening it].

MIG-30's parametrized inputs: `import-legacy` pointed at `fake_home/research-datasets` and at `fake_home`; for the other three commands, a candidate client config or manifest entry that is a link or a path to a decoy (a manifest `original` outside the three candidates, a `backup` of `../decoy.json`). The printer takes no path, so MIG-33 covers it.

Extra design tests with no PRD criterion (raised to the test-architect, because the halt rule has no criterion of its own; the sources give a halt condition at PRD-v7 2.6 but no acceptance criterion):

| Test | Checks |
|---|---|
| `tests/migration/test_halt.py::test_each_breach_writes_marker_and_exits_5` | T1 to T5 each write `HALTED.json` (0600, no value), exit 5 |
| `tests/migration/test_halt.py::test_marker_blocks_import_scrub_legacy_and_retire_but_not_restore` | exit 6; restore and printer still run |
| `tests/migration/test_halt.py::test_output_gate_blocks_a_line_with_a_registered_value` | T2 |
| `tests/migration/test_no_direct_io.py::test_only_the_guard_opens_files` | 5.4 check 1 |
| `tests/migration/test_no_direct_io.py::test_no_mcp_module_imports_the_guard` | 4 (M1 scope) |
| `tests/migration/test_scrub.py::test_backup_folder_checks_refuse_wide_modes_links_and_synced_locations` | T4 |
| `tests/migration/test_restore.py::test_restores_oldest_valued_backup_and_keeps_pre_restore_link` | 5.6 |
| `tests/migration/test_legacy_import.py::test_pdf_path_in_db_is_never_opened_as_given` | 5.1 step 5 |
| `tests/migration/test_legacy_import.py::test_embeddings_duckdb_is_not_opened` | 5.1 step 5 |

Owner checks OC-06 (cutover runbook steps 1 to 9 completed, including a rollback after scrubbing that uses `restore-client-configs`) and OC-07 (14 days on v2 with no fallback) cover MIG-FR-20, MIG-FR-21, MIG-FR-24 and MIG-FR-25 at M4 (test plan v4 section 3).

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| v2 reads v1 only through the legacy import and the credential import; v1 entries are disabled, not deleted, at cutover | Clean history; the owner keeps a working tool; rollback needs no data conversion (ADR 0001) | Rebuilding in place in the v1 tree (ADR 0001) |
| One `ReadGuard` is the only door for every migration read, with a read set per command | The exception in SPEC-v5 9 is per command; one choke point makes "reads only its read set" checkable by a static test and by a recorder (MIG-27 to MIG-34) | A path check at each call site (easy to miss); an OS sandbox profile per command (not available to a Python CLI without new tooling) |
| Test with an audit hook recording `open`, `sqlite3.connect`, `os.scandir` and `os.listdir` | Python's audit events cover the C-level SQLite open that a monkeypatch of `open` would miss | Patching `builtins.open` (misses `sqlite3`); `strace` (not portable to macOS CI) |
| Rows' `pdf_path` values are looked up by name in the tree and never opened as given | A v1 database altered to name `~/.ssh/...` must not become a read | Open the stored path if it lies under the tree (path rebasing is guessy) |
| Open the v1 database `immutable=1` | No WAL or SHM files are created, so the v1 folder is unchanged (SPEC-v2 9.6) | `?mode=ro` (findings-functional 6.3) |
| `embeddings.duckdb` is listed but never opened | v2 re-extracts and re-embeds and uses no DuckDB (ADR 0008) [inferred] | Reading v1 embeddings (contradicts MIG-FR-12) |
| Re-extract files with the v2 parser and chunker; use v1 chunks only on failure | Chunk ids, offsets, sections and embeddings stay consistent with new fetches (findings-functional 6.3) | Copying v1 chunks (MIG-FR-12) |
| Default mode `cache` with a 120-day expiry | Cached items live 120 days and go through the owner review (ADR 0011; OUT-6) | Modes `archive` and `metadata_only` |
| Import the v1 web-search credentials and settings | Every v1 endpoint is kept; web search is an optional source group (ADR 0012) | Dropping the providers (review decision D7, superseded) |
| Map removed v1 tools to "removed" with a reason | No caller-chosen local paths and no free-form SQL (ADR 0009) | none recorded |
| Scrub backups in a fixed `~/.research-mcp-migration/scrub-backups/` (0700), files 0600 | Outside the folders SEC-24 scans; never synced; not configurable, so it cannot be moved into a synced folder (SPEC-v5 9; owner decision, 2026-10-22) | Under `~/.config/research-mcp` (would put plaintext keys in the scanned config folder); under Application Support (same); a setting for the path (could land in Drive) |
| Restore overwrites the whole client config from the backup and links the current file aside | Restore may read only the backups (MIG-31), so it cannot merge; the link keeps later edits | Merge by reading the current file (outside the read set); overwrite without a trace (loses edits) |
| `migration_bootstrap()` skips `Settings` for four of the five commands | The generic settings load would read `config.toml` outside those read sets | Add `config.toml` to every read set (a PRD change; declined, owner decision, 2026-10-23) |
| A halt marker on a detected breach, refusing the credential and legacy commands | PRD-v7 2.6: a breach of any invariant halts the rollout; a file marker survives the process and needs no new command | Exit code only (the next run would continue); a `migration clear-halt` command (new surface; declined, owner decision, 2026-10-23) |
| Refusing an operator-typed bad path is not a breach | Nothing was read; halting would punish a typo | Halt on every refusal (fail closed but noisy) |
| `restore-client-configs` is allowed while halted | Rollback is the safe direction | Block everything (traps the owner on v2 during a halt) |

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

Resolved from the approved sources in this version (answers recorded where used):

- The v1 file count (123 PDFs in MIGRATION-v2 2; 122 distinct files in findings-functional 6.3): both can be true, since two rows share a file. The design hard-codes neither; the report records the counts found (5.1; runbook "about 132 works").
- Unknown-prefix lookup: a title lookup through `get_work`, best effort (SPEC-v2 9.6 and MIG-FR-11); a failure is an unresolved id (5.1 step 3).
- Crawled-site source name: `docs_site_<project>` (MIG-FR-11).
- The findings-functional enrichment step and the `needs_ocr` report fields: not in MIG-FR-14 or any criterion, so out of scope (PRD-migration v6 frozen).
- Dry run of the legacy import: report only, `dry_run: true` (5.1).
- Module, class and function names, and the tool map location: section 5 and 2.
- Fingerprint: `sha256(value)[:8]` (LLD-platform v2 4.1). The names to import: the union of `SourceSpec` credential names; the Keychain name lives in the `SourceSpec` (owner decision, 2026-10-22; 5.2).
- A machine-readable contract: not warranted (2).
- MIG-FR-23 against MIGRATION-v2 3: superseded by MIG-FR-25, which states both (PRD-migration v6 2.15).
- The SPEC basis: SPEC-v5 is the parent; SPEC-v2 9.6 is kept as a cited design source.

Owner decisions (2026-10-23), recorded where used:

- Retirement: `research-mcp retire-v1 --confirm` calls `retire_v1()` and deletes the scrub backups; it reads and deletes only the scrub-backup set; PRD-migration v6 gains the read-set row and MIG-35 (2, 5.4, 5.5, 9).
- Client config paths confirmed; a linked final component is refused (G2); the owner replaces the link with the file or pastes by hand (5, 5.4).
- The two v1 facts (entry recognition, preferred-provider `env` name) are a build step read from the v1 repository, read-only, and listed for the owner to confirm at review; the current assumption stays marked [assumption] (5). Re-serializing with `json.dumps(indent=2)` is accepted (5.5).
- The halt marker is cleared by the owner deleting it by hand; no command (3, 5.7).
- The CLI `config.toml` read and the daemon's own `state.db` opens stay outside the per-command read sets (5, 5.4).

Build-step note: the owner confirms the two v1 facts at review of the implementation (listed as open at Gate 3).
The `cache.db` read of `import-legacy` is confirmed (owner decision, 2026-10-22; PRD-migration v6 2.13).

For other personas and agents (not owner decisions):

- The cutover runbook v2 should add: `restore-client-configs` in the rollback; the retire command `retire-v1 --confirm`; the halt marker and the exit codes; and the backup folder path. It must not carry MIG-FR-23.
- The `sdd.config.json` `migration.paths` lists only `services/legacy_import.py`; the new modules (`migration_guard.py`, `client_configs.py`, `tool_map.py`) and `tests/migration` are not covered.
- The test plan names `test_legacy_import.py::test_scrub_backup_is_owner_only` for MIG-25, but the scrub code is in `client_configs.py`; the test-architect should rename it.

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
