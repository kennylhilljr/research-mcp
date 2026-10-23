---
title: "Migration and Cutover"
type: prd-component
version: 6
status: draft
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
prefix: MIG
component: migration
parent: docs/prd/PRD-v7.md
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
supersedes: docs/prd/components/PRD-migration-v5.md
date: 2026-10-22
---

# Component PRD: Migration and Cutover (v6)

Version 4 moved [PRD-migration v3](../../../docs-archive/prd/components/PRD-migration-v3.md) onto the SDD component template; its earlier IDs map to new ones in section 2.16. This version supersedes [PRD-migration v5](PRD-migration-v5.md). Version 6 reopens Gate 1 to add the file-read boundary of each migration command (MIG-FR-27, MIG-27 to MIG-34), which closes the SPEC-v4 section 20 item (owner decision, 2026-10-22). It also adds the `retire-v1` command (MIG-FR-26, MIG-35), the client config paths and the symbolic-link rule for them (owner decision, 2026-10-23). Parent: [PRD v7](../PRD-v7.md) (PRD v8 is the draft successor: [PRD v8](../PRD-v8.md)). Vision: [vision v2](../../vision/vision-v2.md). Design: [SPEC v5](../../spec/SPEC-v5.md) and [LLD-migration v2](../../lld/LLD-migration-v2.md). Cutover steps: [migration cutover runbook](../../runbooks/migration-cutover-v2.md).

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

The owner must move from v1 to v2 without re-entering any credential, without touching v1's data, and with an easy way back until v2 has proven itself (PRD-migration-v3 1).

v1 is in daily use by three MCP clients, so v2 is built in a new repository and v1 keeps running under its existing client entries until cutover at milestone M4 (ADR 0001; PRD-v6 2.9). The parent problem, v1's 53 single-source tools and its silent breakage, is in the parent PRD (PRD-v6 1.1).

**Why now.** v2 is a rebuild, and the upstream breakage it fixes is current: the live probes of 2026-10-19 found OpenAlex, Semantic Scholar and Crossref degraded and Google Programmable Search closed to new customers (PRD-v7 1.1; owner decision, 2026-10-22). Cutover at M4 is the step that moves daily use from v1 to v2 (PRD-v6 2.9).

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| The owner | Move to v2 without re-entering credentials, keep v1's data untouched, and keep a one-step way back (PRD-migration-v3 1; MIGRATION-v2 1) | One person (PRD-v6 1.2; owner decision, 2026-10-22) |
| The MCP clients on the Mac: Claude desktop, Claude Code, OpenClaw | A v2 server entry beside the v1 entry during the parallel period (PRD-migration-v3 FR-MIG-01, FR-MIG-21) | Three clients used by one person (PRD-v6 1.2; owner decision, 2026-10-22) |
| Agents whose instructions mention v1 tool names | A map from each v1 tool to the v2 tool and arguments that replace it (PRD-migration-v3 FR-MIG-22; MIGRATION-v2 4) | The agents of one person (PRD-v6 1.2; owner decision, 2026-10-22) |

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- Credential import from the v1 client configs into the Keychain, including the v1 web-search credentials and settings (PRD-v4 5; ADR 0012).
- Optional import of the v1 corpus (PRD-v4 5; MIGRATION-v2 1).
- Client cutover, rollback and v1 retirement (PRD-v4 5).
- The v1 to v2 tool map (PRD-migration-v3 FR-MIG-22).
- The file-read boundary of each owner-run migration command (MIG-FR-27; owner decision, 2026-10-22).

| Non-goal | Why it is excluded |
| --- | --- |
| Keeping v1 tool names or result shapes | Clients are updated at cutover (PRD-v4 3.2; PRD-v6 1.3). |
| Migrating or changing the owner's separate K-12 teacher server | It is not migrated or changed (PRD-v4, changes from v3; PRD-v6 1.6). |
| Importing the v1 datasets (`~/research-datasets`) or keeping the v1 dataset tools | Not inspected; no SQL or dataset tool in the first release (MIGRATION-v2 2 and 4; ADR 0009; PRD-v6 1.6, O4 closed). |

Every non-goal above states its reason. This component adds no non-goal beyond these and the parent's (PRD-v6 1.3; owner decision, 2026-10-22).

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

MIG-OUT-1 is carried over from the PRD-v4 M4 exit (owner decision, 2026-10-22). The parent outcomes OUT-1 to OUT-8 suffice otherwise, and no other component outcome is added (owner decision, 2026-10-22).

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |
| MIG-OUT-1 | Days of daily use on v2 with no fallback to v1 | Every client uses v1 (owner decision, 2026-10-22) | 14 days, then v1 archived (PRD-v6 2.9, M4 exit) | M4 |

## 1.5 Leaps of faith

> **Owner:** H · **Persona:** none

Each bet restates a premise the sources already make.

| Leap of faith | How we will validate it | By when |
| --- | --- | --- |
| No credential is re-entered: the `env` blocks of the v1 client entries hold every credential v2 needs, so the import can move them into the Keychain (MIGRATION-v2 1, principle 2; PRD-migration-v3 1) | MIG-1 and MIG-3 on fake configs; then owner check OC-06, where cutover step 3 shows each credential `ok` or `unknown_expiry` on the Credentials page (MIGRATION-v2 3) | M4 exit |
| Rollback is one config change until v1 is retired, so the owner can switch with little risk (MIGRATION-v2 1, principle 4; ADR 0001 consequence "Rollback is re-enabling the v1 client entry") | Owner check OC-06 (test-plan-v2 3) | M4 exit |
| v2 replaces v1 for daily work, and agents can move to it from the tool map without a fallback to v1 (MIG-OUT-1; MIGRATION-v2 4; PRD-v6 2.6 halt condition "a fallback to v1 during the 14-day window") | MIG-21 (the tool map covers all 53 v1 tools); owner check OC-07 (14 days on v2 with no fallback) | M4 exit |

## 1.6 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

The owner confirmed MIG-INV-1 to MIG-INV-3 as component invariants (owner decision, 2026-10-22). Each names the P1 criterion that verifies it.

| ID | The system must never | Source (regulation, policy, contract) | Verified by (P1 criterion) |
| --- | --- | --- | --- |
| MIG-INV-1 | Modify v1's data or folder (its database is opened immutable; its folder is only read) | MIGRATION-v2 1, principle 1; ADR 0001; parent INV-10 | MIG-10 |
| MIG-INV-2 | Print a credential value during the credential import | PRD-migration-v3 FR-MIG-01; parent NFR-4 | MIG-1 (normal output) and MIG-22 (dry run, conflict prompt, not-imported list and errors) |
| MIG-INV-3 | Write an imported credential anywhere but the Keychain | ADR 0001; parent NFR-3 | MIG-23 |

**Approved exception.** The scrub backups that `scrub-client-configs` writes are not an import, but they do hold plaintext v1 keys outside the Keychain. The owner approved them as an exception to NFR-3 and INV-6 that lasts until v1 is retired; they are written owner-only and deleted at retirement (PRD-v7 1.5; MIG-FR-26; MIG-25, MIG-26; owner decision, 2026-10-22). MIG-INV-3 itself is unchanged.

**Approved exception for owner-run commands.** INV-4 and SEC-INV-7 are excepted per command, until v1 retirement, for the owner-run migration commands only: each reads only the paths in its read set (2.4, MIG-FR-27). MCP tools and agent-triggered actions stay bound by INV-4 and SEC-INV-7 (SPEC-v4 9; owner decision, 2026-10-22).

## 1.7 Known constraints and decisions

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

| Decision or constraint | Status (made or open) | Rationale or link |
| --- | --- | --- |
| v2 is a new repository; v1 stays read-only and running until cutover; at cutover v1's entries are disabled, not deleted | made; ADR 0001 is Proposed and is accepted when the owner approves this PRD at Gate 1 (owner decision, 2026-10-22; PRD-v6 1.6) | ADR 0001 |
| The v1 web-search credentials are imported, and the Vertex project, location and engine id and the Programmable Search engine id carry over as settings | made | ADR 0012; it supersedes review decision D7 |
| Imported cache items get a 120-day expiry | made | ADR 0011; it supersedes the 30 days of review decision D3 |
| Tools that took caller-chosen local paths or ran SQL are removed, not mapped | made | ADR 0009 |
| No SQL or dataset tool in the first release | made: O4 closed (PRD-v6 1.6) | PRD-v4 11, O4 |
| New free OpenAlex and Semantic Scholar keys are added at cutover | made: O2 closed (PRD-v6 1.6) | PRD-v4 11, O2; MIGRATION-v2 3, step 4 |
| Each owner-run migration command reads only its own read set; a read of any other path is refused and reported | made (owner decision, 2026-10-22) | SPEC-v4 9 and 20; MIG-FR-27 |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| Kenny Hill (Product) | 2026-10-22 | Approved in chat; recorded by Claude in the owner's name at his direction |

---

## 2.1 Customer discovery

> **Owner:** A · **Persona:** `analyst`

The deep review of v1 ([REVIEW v1](../../../docs-archive/review/REVIEW-v1.md) and [findings-functional v1](../../../docs-archive/review/findings-functional-v1.md)) inventoried what the cutover must carry:

- v1 exposes 53 tools (findings-functional 2).
- v1's data in `~/arxiv-papers` is `arxiv_index.db` (34 MB, 186 rows, 11,403 chunks), 123 PDFs and `embeddings.duckdb`, with 54 duplicate pairs and 10 web pages stored by URL (MIGRATION-v2 2).
- v1 credentials live in the `env` blocks of the v1 server entries in the Claude desktop, Claude Code and OpenClaw configs; their values were never read during design (MIGRATION-v2 2).

## 2.2 User stories and priority

> **Owner:** C for stories (`product-writer`), H for priority · **Seed question:** 3

Drafted by the product writer and approved by the owner at Gate 1, 2026-10-22 (owner decision, 2026-10-22, to draft them). The stories rest on the owner's need in 1.2 (PRD-migration-v3 1; MIGRATION-v2 1) and on the parent user needs (PRD-v6 1.2). No requirement serves the ECC orchestrator, so it has no story.

| ID | As a... I want... so that... | Priority | Why this priority |
| --- | --- | --- | --- |
| MIG-US-1 | As the owner (directly), I want my v1 credentials and web-search settings moved into the Keychain and `config.toml` without re-entering or seeing them, so that v2 works from the first day and no key leaks. | P1 | MIG-FR-1 is Must (P1) |
| MIG-US-2 | As the owner (directly), I want to run v2 beside v1, keep a one-step way back, and retire v1 only when I say so, so that I can switch with little risk. | P1 | MIG-FR-21, MIG-FR-25 and MIG-FR-24 are Must (P1) |
| MIG-US-3 | As the owner (through an agent), I want a map from each v1 tool to the v2 tool and arguments that replace it, so that agent instructions that name v1 tools can be updated. | P1 | MIG-FR-22 is Must (P1) |
| MIG-US-4 | As the owner (directly), I want to import my v1 corpus into the v2 cache with a report, without touching v1's data, so that papers I already have stay reachable and go through the normal review. | P2 | MIG-FR-10 to MIG-FR-14 are P2 |
| MIG-US-5 | As the owner (through an agent), I want v2 to work fully with an empty cache, so that the corpus import stays optional. | P1 | MIG-FR-15 is Must (P1) |
| MIG-US-6 | As the owner (directly), I want the plaintext keys removed from the old v1 client entries after cutover, so that no credential stays in a client config. | P2 | MIG-FR-5 is P2 |

## 2.3 User experience

> **Owner:** C · **Persona:** `product-writer` drafts the narrative; designers own the design artifacts · **Seed question:** 3

The owner runs the cutover from the command line, following the [cutover runbook](../../runbooks/migration-cutover-v2.md). The owner first runs `research-mcp secrets import --dry-run` to see the names, fingerprints and settings that would be written, then runs it for real. The owner may then run `research-mcp import-legacy ~/arxiv-papers --dry-run`, review the report, and run it without `--dry-run`. The owner pastes the entries from `research-mcp install --print-client-config` into each client under the server name `research`, uses v2 beside v1 for a parallel period, then disables the v1 entries and scrubs the plaintext keys with `research-mcp secrets scrub-client-configs`. Rollback until retirement is re-enabling the v1 entries; after scrubbing, it also restores the scrubbed values from the backups (MIG-FR-25). Each command reads only its own read set (MIG-FR-27); a command that is asked to read anything else stops with an error that names the path. (MIGRATION-v2 3.)

## 2.4 Functional requirements and acceptance criteria

> **Owner:** C · **Persona:** `product-writer` drafts requirements and criteria as options; the owner selects and approves · **Seed questions:** 3, 12

**Credentials**

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| MIG-FR-1 | `research-mcp secrets import` finds the v1 server entries in the MCP client configs on the Mac (Claude desktop, Claude Code, OpenClaw), reads the credential values from their `env` blocks, and writes each to the Keychain as `research-mcp/<NAME>`. It prints names, fingerprints and the config file each came from; never values. | MIG-US-1 | | P1 |
| MIG-FR-2 | When the same name has different values in different configs, the import stops for that name and asks the owner which config wins (by fingerprint), instead of guessing. | MIG-US-1 | | P1 |
| MIG-FR-3 | Every v1 credential a v2 source uses is imported, including the Brave and SerpAPI keys and the Google key shared by the Developer Knowledge and Programmable Search sources. A credential no v2 source uses is listed as "not imported" with a note and is not copied. | MIG-US-1 | | P1 |
| MIG-FR-4 | The import is idempotent and has a `--dry-run` that shows what would be written. | MIG-US-1 | | P1 |
| MIG-FR-5 | After cutover, `research-mcp secrets scrub-client-configs` removes the plaintext `env` values from the old v1 entries (with a backup of each file first), on explicit confirmation. | MIG-US-6 | | P2 |
| MIG-FR-6 | The import carries v1's non-secret web-search settings into `config.toml`: the Vertex project, location and engine id become the instance `vertex_v1`; the Programmable Search engine id becomes `sources.google_pse.engine_id`; v1's provider choice becomes `web.order` (when v1 named one provider, it goes first). It prints each setting it wrote. | MIG-US-1 | | P1 |

**Optional corpus import**

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| MIG-FR-10 | `research-mcp import-legacy <path> [--dry-run] [--mode M]` (M is `cache`, `archive` or `metadata_only`) runs as a job. It opens the v1 database read-only (immutable) and never modifies the v1 folder. | MIG-US-4 | | P2 |
| MIG-FR-11 | The import normalizes identifiers (arXiv without version, DOI and CORE prefixes, v1's crawled-site rows become HTML documents with their URL under the matching `docs_site_<project>` source), merges the 54 duplicate pairs keeping the titled row's metadata, and maps unknown prefixes (`harv...`, `penn...`) to a `legacy` scheme followed by a best-effort lookup. | MIG-US-4 | | P2 |
| MIG-FR-12 | The import re-extracts the PDFs with the v2 parser and chunker rather than copying v1 chunks, and falls back to v1 chunks only where re-extraction fails. | MIG-US-4 | | P2 |
| MIG-FR-13 | The default mode is `cache`: every imported item gets a fresh 120-day expiry and goes through the normal review. | MIG-US-4 | | P2 |
| MIG-FR-14 | The import writes a report (JSON and Markdown) with rows read, works created, merged pairs, unresolved ids, re-extraction failures, chunk counts before and after, and the legacy-id to work-id map. | MIG-US-4 | | P2 |
| MIG-FR-15 | Running the import is optional; v2 works fully with an empty cache. | MIG-US-5 | | P1 |

**Client cutover and v1 retirement**

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| MIG-FR-20 | `research-mcp install --print-client-config` prints, for each client, the server entry that launches `research-mcp stdio` (no secrets). | MIG-US-2 | | P1 |
| MIG-FR-21 | Cutover adds the v2 entry beside the v1 entry under a new name (`research`), so both can run during a parallel period; the v1 entry is disabled, not deleted, at cutover. | MIG-US-2 | | P1 |
| MIG-FR-22 | A tool map documents, for each of the 53 v1 tools, the v2 tool and arguments that replace it (or "removed" with the reason), so agent instructions can be updated. | MIG-US-3 | | P1 |
| MIG-FR-25 | Rollback is re-enabling the v1 entry in the client configs; it needs no data conversion because v1's data is never modified. After `scrub-client-configs`, rollback also restores the scrubbed values from the scrub backups with `research-mcp restore-client-configs`, which reads only the scrub backups, because v1 does not read the Keychain (MIGRATION-v2 3; owner decision, 2026-10-22). | MIG-US-2 | | P1 |
| MIG-FR-26 | `scrub-client-configs` writes each backup with owner-only permissions (mode 0600). The backups hold plaintext v1 keys and are an approved exception to NFR-3 and INV-6 that lasts until v1 is retired; retiring v1 deletes them. The deletion is the command `research-mcp retire-v1 --confirm`: without `--confirm` it refuses and deletes nothing; with `--confirm` it deletes the scrub backups and reports each path; it touches only the scrub-backup set (owner decision, 2026-10-23). | MIG-US-6 | OUT-7 | P2 |
| MIG-FR-24 | v1 is retired (entry removed, repository archived) only after 14 days of daily use on v2 with no fallback, and only on the owner's explicit go-ahead. | MIG-US-2 | | P1 |

**File-read boundary**

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| MIG-FR-27 | Each owner-run migration command reads only the paths in its read set below. A read of any other path is refused and reported. MCP tools and agent-triggered actions are not covered: they stay bound by INV-4 and SEC-INV-7 (SPEC-v4 9; owner decision, 2026-10-22). | MIG-US-1 | INV-4 | P1 |

Read set of each command (paths from MIG-FR-1, MIG-FR-5, MIG-FR-10 and SPEC-v4 9; owner decision, 2026-10-22). A command's write targets (the Keychain, `config.toml`, the report folder, the scrub backups) are not reads and are governed by their own requirements.

| Command | May read | Source |
| --- | --- | --- |
| `research-mcp secrets import` | The client config files that hold the v1 server entry, at exactly `~/Library/Application Support/Claude/claude_desktop_config.json` (Claude desktop), `~/.claude.json` (Claude Code) and `~/.openclaw/openclaw.json` (OpenClaw); a path whose final component is a symbolic link is refused (MIG-32); the v2 config file `~/.config/research-mcp/config.toml`, to keep the import idempotent (MIG-FR-4) | MIG-FR-1; MIG-FR-4; SPEC-v4 9 and 10 |
| `research-mcp secrets scrub-client-configs` | The same three client config files, with the same symbolic-link refusal (MIG-32); no other path | MIG-FR-5; SPEC-v4 9; owner decision, 2026-10-23 |
| `research-mcp import-legacy <path>` | The v1 data tree at `<path>` (`~/arxiv-papers`: `arxiv_index.db`, opened immutable, the PDFs and `embeddings.duckdb`), read only; a symbolic link that leaves that tree is refused (MIG-32); the v2 cache `~/Library/Application Support/research-mcp/cache/cache.db`, to merge with works already there (confirmed, owner decision, 2026-10-22) | MIG-FR-10; SPEC-v4 9 and 10; MIG-INV-1 |
| `research-mcp install --print-client-config` | Nothing beyond the v2 install (owner decision, 2026-10-22) | MIG-FR-20 |
| `research-mcp restore-client-configs` | The scrub backups only | MIG-FR-25 |
| `research-mcp retire-v1 --confirm` | The scrub-backup set only, the same set as `restore-client-configs`; it deletes that set and touches nothing else (owner decision, 2026-10-23) | MIG-FR-26 |

The CLI's own `config.toml` read and the daemon's opens of its own `state.db` stay outside these per-command read sets (assumption, see 2.13).

**Acceptance criteria**

| ID | Criterion | Requirement | Priority | Level | Milestone |
| --- | --- | --- | --- | --- | --- |
| MIG-1 | When `secrets import` reads fake client configs, the secrets import shall write Keychain items through a fake provider and print names and fingerprints only. | MIG-FR-1 | P1 | integration | M4 |
| MIG-2 | If one name has conflicting values, then the secrets import shall stop the import for that name and ask. | MIG-FR-2 | P1 | integration | M4 |
| MIG-3 | The secrets import shall import the Brave, SerpAPI and shared Google keys and report a v1 credential that no v2 source uses as not imported, without copying it. | MIG-FR-3 | P1 | unit | M4 |
| MIG-4 | The secrets import shall be idempotent and write nothing under `--dry-run`. | MIG-FR-4 | P1 | integration | M4 |
| MIG-5 | When the owner confirms, `scrub-client-configs` shall back up each file and remove only the v1 `env` values. | MIG-FR-5 | P2 | integration | M4 |
| MIG-6 | The secrets import shall turn the v1 web-search settings into config, with `VERTEX_AI_*` giving the instance `vertex_v1`, `GOOGLE_PSE_CX` giving `sources.google_pse.engine_id` and a named v1 provider going first in `web.order`, and with every written setting printed. | MIG-FR-6 | P1 | unit | M4 |
| MIG-10 | When `import-legacy` runs, the legacy import shall open the v1 database immutable and leave the v1 folder byte-for-byte unchanged. | MIG-FR-10, MIG-FR-15 | P1 | integration | M4 |
| MIG-11 | When the legacy import runs on a synthetic v1 database with the 54-pair pattern, 10 URL rows and harv and penn ids, the legacy import shall produce the expected works, HTML documents and legacy ids. | MIG-FR-11 | P2 | integration | M4 |
| MIG-12 | The legacy import shall use re-extraction and import v1 chunks only where re-extraction fails. | MIG-FR-12 | P2 | integration | M4 |
| MIG-13 | When the legacy import runs in mode `cache`, the legacy import shall give every item a fresh 120-day expiry. | MIG-FR-13 | P2 | integration | M4 |
| MIG-14 | The legacy import report shall contain every field in MIG-FR-14. | MIG-FR-14 | P2 | integration | M4 |
| MIG-20 | The client config printer shall produce its output for Claude desktop, Claude Code and OpenClaw. | MIG-FR-20, MIG-FR-21 | P1 | unit | M4 |
| MIG-21 | The tool map shall cover all 53 v1 tools. | MIG-FR-22 | P1 | unit | M4 |
| MIG-22 | The secrets import shall print no credential value in any of its output, including the `--dry-run` output, the conflict prompt, the not-imported list and every error message. | MIG-FR-1, MIG-FR-2, MIG-FR-3, MIG-FR-4 | P1 | integration | M4 |
| MIG-23 | When the secrets import runs on fake client configs, the secrets import shall leave no imported credential value in any file it writes outside the fake Keychain provider, including `config.toml`, the state directory and the logs. | MIG-FR-1, MIG-FR-6 | P1 | integration | M4 |
| MIG-24 | While no legacy import has run and the cache is empty, the system shall complete `search`, `get_work` and `fetch` calls against fake sources without an error. | MIG-FR-15 | P1 | integration | M4 |
| MIG-25 | When `scrub-client-configs` writes a backup of a client config file, the migration service shall create it with owner-only permissions (mode 0600). | MIG-FR-26, NFR-3 | P1 | unit | M4 |
| MIG-26 | When v1 is retired, the migration service shall delete every backup that `scrub-client-configs` wrote. | MIG-FR-26, NFR-3 | P1 | integration | M4 |
| MIG-27 | When `secrets import` runs in a fake home that holds the client config files and decoy files elsewhere, the secrets import shall open only the client config files that hold the v1 server entry. | MIG-FR-27, MIG-FR-1 | P1 | integration | M4 |
| MIG-28 | When `scrub-client-configs` runs in a fake home that holds the client config files and decoy files elsewhere, the scrub command shall open only the client config files that hold the v1 server entry. | MIG-FR-27, MIG-FR-5 | P1 | integration | M4 |
| MIG-29 | When `import-legacy` runs on a fake v1 tree beside decoy files outside it, the legacy import shall open only files under the v1 tree it was given. | MIG-FR-27, MIG-FR-10 | P1 | integration | M4 |
| MIG-30 | If an owner-run migration command is asked to read a path outside its read set, then the migration service shall refuse the read with an error that names the path and shows no file content. | MIG-FR-27 | P1 | integration | M4 |
| MIG-31 | When `restore-client-configs` runs in a fake home that holds scrub backups and decoy files elsewhere, the restore command shall open only the scrub backups. | MIG-FR-27, MIG-FR-25 | P1 | integration | M4 |
| MIG-32 | If the v1 tree holds a symbolic link that leaves the tree, then `import-legacy` shall refuse the link with an error that names the path and shows no file content. | MIG-FR-27, MIG-FR-10 | P1 | integration | M4 |
| MIG-33 | When `install --print-client-config` runs, the install command shall open no file beyond the v2 install. | MIG-FR-27, MIG-FR-20 | P1 | integration | M4 |
| MIG-34 | When `secrets import` or `import-legacy` reads the v2 tree, the command shall open only the v2 paths listed for it in the read set. | MIG-FR-27, MIG-FR-4 | P1 | integration | M4 |
| MIG-35 | If `retire-v1` is run without `--confirm`, then the retire command shall refuse and delete nothing; when it is run with `--confirm`, it deletes the scrub backups and reports each path, and nothing else. | MIG-FR-26 | P1 | integration | M4 |

MIG-FR-26 stays P2 while MIG-25, MIG-26 and MIG-35 are P1: scrubbing is optional, but if it ships, its backup controls must pass, the same pattern as CACHE-62 for CACHE-FR-51 (owner decision, 2026-10-22).

MIG-27 to MIG-30 are one P1 criterion per command plus the refusal, as the owner decided in SPEC-v4 20; MIG-31 to MIG-34 add the restore command, the symbolic-link refusal, the print command and the v2 paths (owner decision, 2026-10-22). `restore-client-configs` is stated under MIG-FR-25, which already covers restoring on rollback, so no new requirement is added. MIG-FR-27 is new because the boundary is a requirement that the criteria verify; MIG-FR-5 stays P2 while MIG-28 is P1 for the same reason as MIG-25. MIG-35 verifies the `retire-v1 --confirm` command stated under MIG-FR-26 (owner decision, 2026-10-23). The symbolic-link refusal of MIG-32 also applies to a client config file whose final component is a symbolic link, for `secrets import` and `scrub-client-configs`; this is a note on the read sets, and the meaning of MIG-32 is unchanged (owner decision, 2026-10-23).

Verified elsewhere (owner decision, 2026-10-22):

- MIG-FR-20: also by PLAT-82 in the platform component, and by owner check OC-06.
- MIG-FR-21: by owner check OC-06, beside MIG-20.
- MIG-FR-25: by owner check OC-06 (cutover runbook steps 1 to 9 completed).
- MIG-FR-24: by owner check OC-07 (14 days on v2 with no fallback; the owner approves retiring v1).

Owner checks stay owner checks; they are listed in [test-plan-v2](../../test/test-plan-v2.md) section 3.

## 2.5 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

The parent's cross-cutting requirements apply, in particular NFR-3 (no secrets at rest outside the Keychain), NFR-4 (no secret in any output) and NFR-9 (testable offline) (PRD-v6 2.3). The parent outcomes OUT-1 to OUT-8 and NFR-1 to NFR-12 suffice, and no component target is added, including no time limit for the credential import or the legacy import (owner decision, 2026-10-22). Design defaults stay in the LLD.

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |

## 2.6 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

Every item is personal and confidential (PRD-v6 2.4). Each retention uses the parent rule for the same kind of data, or the nearest parent rule (owner decision, 2026-10-22).

| Data | Classification | Source or owner | Retention | Notes |
| --- | --- | --- | --- | --- |
| v1 credential values in client config `env` blocks | Personal, confidential; secret (PRD-v6 2.4; NFR-3, NFR-4) | MCP client configs on the Mac (MIGRATION-v2 2) | In the client configs until `scrub-client-configs` removes them after cutover (MIG-FR-5); in the Keychain until revoked or replaced (PRD-v6 2.4) | Written only to the Keychain as `research-mcp/<NAME>` (MIG-FR-1; ADR 0001) |
| Scrub backups of the client config files | Personal, confidential; hold the plaintext v1 credential values (MIGRATION-v2 3, step 9) | Written by `scrub-client-configs` (MIG-FR-5) | Until v1 is retired, then deleted (MIG-FR-26; owner decision, 2026-10-22) | Used by rollback after scrubbing (MIG-FR-25); owner-only permissions; an approved exception to NFR-3 and INV-6 (MIG-FR-26) |
| v1 web-search settings (Vertex project, location, engine id; Programmable Search engine id) | Personal, confidential; not secrets (PRD-v6 2.4; ADR 0012) | v1 client configs | Life of the install (nearest parent rule: daemon state, PRD-v6 2.4; owner decision, 2026-10-22) | Written to `config.toml` (MIG-FR-6) |
| v1 corpus (`arxiv_index.db`, PDFs, `embeddings.duckdb`) | Personal, confidential (PRD-v6 2.4) | `~/arxiv-papers` (MIGRATION-v2 2) | Kept until the owner removes it (MIGRATION-v2 3, step 10) | Read only (MIG-INV-1; parent INV-10); read only by `import-legacy` (MIG-FR-27) |
| Imported works and documents | Personal, confidential; untrusted content (PRD-v6 2.4; NFR-6) | v2 `cache.db` | The parent cache rules: 120 days from fetch in mode `cache` (MIG-FR-13; ADR 0011); archived items never expire (PRD-v6 2.4) | |
| Import report | Personal, confidential (PRD-v6 2.4) | `state_dir/imports/<timestamp>/` (SPEC-v2 9.6) | Life of the install (nearest parent rule for reports and records; owner decision, 2026-10-22) | |

## 2.7 Integrations and owners

> **Owner:** H confirms owners and SLAs · **Persona:** `architect` may draft · **Seed question:** 8

Kenny Hill owns every integration. No integration has an SLA; upstream services are best effort, tracked by probes (PRD-v6 2.5; owner decision, 2026-10-22).

| System | Owner | Relationship (depends on, feeds, replaces) | SLA |
| --- | --- | --- | --- |
| Claude desktop, Claude Code and OpenClaw client configs | Kenny Hill | Depends on (read for credentials; v2 entry added; v1 entry disabled and scrubbed) | None |
| macOS Keychain | Kenny Hill | Feeds (credentials written as `research-mcp/<NAME>`) | None |
| v1 server (`my-research-mcp-server`) and its data | Kenny Hill | Replaces (after retirement, MIG-FR-24) | None |
| v2 cache, extraction worker and `get_work` lookup | Kenny Hill | Feeds (legacy import writes works, documents and chunks) | None; the best-effort `get_work` lookup depends on upstream services, tracked by probes (PRD-v6 2.5) |

## 2.8 Product risks

> **Owner:** H · **Persona:** none

| Risk | Question | Assessment | Mitigation |
| --- | --- | --- | --- |
| Value | Will customers choose to use this? | The owner may fall back to v1 during the 14-day window, which halts the rollout (PRD-v6 2.6) and resets MIG-OUT-1. | A parallel period of 3 to 7 days with v1 still available (MIGRATION-v2 3, step 7); rollback by re-enabling v1 (MIG-FR-25); retirement only on the owner's go-ahead (MIG-FR-24). |
| Usability | Can customers use it, including with accessibility needs? | The cutover is ten command-line steps (MIGRATION-v2 3), and agent instructions that name v1 tools stop working after cutover because v1 names are not kept (PRD-v6 1.3; MIGRATION-v2 4). The sources state no accessibility need. | Dry runs for both imports (MIG-FR-4, MIG-FR-10); a runbook with a check per step (MIGRATION-v2 3); a tool map that covers all 53 v1 tools (MIG-21). |
| Viability | Does it work for the business: economics, legal, compliance, operations? | Two server processes may run side by side during the parallel period, and v2's global rate limits do not cover v1's calls (ADR 0001). | The parallel period should be short (ADR 0001). |

## 2.9 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | v2 runs beside v1 for a parallel period of 3 to 7 days; v1 entries are then disabled, not deleted; v1 is retired only after 14 days with no fallback and the owner's go-ahead (MIGRATION-v2 3; MIG-FR-21; MIG-FR-24; PRD-v6 2.6). |
| Business conditions that must halt the rollout | A blocking issue during parallel use (MIGRATION-v2 3, step 7); and the PRD-v7 2.6 conditions: any deletion without a recorded owner decision, any secret in an output, a fallback to v1 during the 14-day window, or a breach of any invariant, which includes MIG-INV-1 to MIG-INV-3 (PRD-v7 2.6; owner decision, 2026-10-22). Rollback is re-enabling the v1 entries (MIG-FR-25). |
| Support owner and escalation path | The owner is the only support; there is no escalation path (PRD-v6 2.6; owner decision, 2026-10-22). |
| Response targets by severity (S0 to S4) | None (PRD-v6 2.6; owner decision, 2026-10-22). |

## 2.10 Measurement and experimentation

> **Owner:** C · **Persona:** `product-writer` drafts; the owner decides

| Outcome | Measured by | Experiment (if any) |
| --- | --- | --- |
| MIG-OUT-1 | Owner check OC-07: 14 days on v2 with no fallback; the owner approves retiring v1 (test-plan-v2 3) | none |

## 2.11 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

The component is done when every P1 criterion passes (MIG-1, MIG-2, MIG-3, MIG-4, MIG-6, MIG-10, MIG-20, MIG-21, MIG-22, MIG-23, MIG-24, MIG-25, MIG-26, MIG-27, MIG-28, MIG-29, MIG-30, MIG-31, MIG-32, MIG-33, MIG-34 and MIG-35) and the M4 exit is met: 14 days of daily use on v2 with no fallback to v1, then v1 archived (PRD-v6 2.9). The owner checks listed for this component in test-plan-v2 section 3, OC-06 and OC-07, count toward done. No extra demonstration is required (owner decision, 2026-10-22).

## 2.12 Edge cases and error behavior

> **Owner:** A · **Persona:** `product-writer`

- The same credential name has different values in different client configs: the import stops for that name and asks (MIG-2).
- A v1 credential is not used by any v2 source: it is reported as not imported and not copied (MIG-3).
- The import is run twice, or with `--dry-run`: the result is the same, and a dry run writes nothing (MIG-4).
- The secrets import hits an error, a conflict or a dry run: no credential value appears in its output (MIG-22).
- A v1 row has an unknown prefix (`harv...`, `penn...`): it maps to the `legacy` scheme, followed by a best-effort lookup (MIG-FR-11, MIG-11).
- A v1 row stores a web page by URL: it becomes an HTML document under the matching `docs_site_<project>` source (MIG-FR-11, MIG-11).
- Re-extraction of a file fails: the v1 chunks are imported for that document (MIG-12).
- The owner never runs the legacy import: v2 works with an empty cache (MIG-FR-15, MIG-24).
- Rollback after the plaintext keys were scrubbed: v1 does not read the Keychain, so rollback restores the scrubbed values from the scrub backups (MIG-FR-25; MIGRATION-v2 3). Owner check OC-06 verifies it (owner decision, 2026-10-22).
- A migration command is pointed at a path outside its read set (for example `import-legacy` at `~/research-datasets`, or `secrets import` at a file that is not a client config): the read is refused with an error that names the path, and no content is shown (MIG-FR-27, MIG-30).
- The v1 tree holds a symbolic link to a file outside it: `import-legacy` refuses it (MIG-32; owner decision, 2026-10-22).
- `install --print-client-config` runs: it reads nothing beyond the v2 install (MIG-33; owner decision, 2026-10-22).
- Rollback after scrubbing: `restore-client-configs` reads only the scrub backups (MIG-31; owner decision, 2026-10-22).
- `retire-v1` is run without `--confirm`: it refuses and deletes nothing (MIG-35; owner decision, 2026-10-23).
- A client config file is a symbolic link in its final component: the command refuses it (MIG-32 note; owner decision, 2026-10-23).

## 2.13 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves before Gate 1

**Resolved on 2026-10-22 (version 5).** The owner answered every open question in PRD-migration-v4: the user stories, drafted for approval (2.2, with a story on every requirement in 2.4); the relative sizes (1.2); MIG-OUT-1 and its baseline (1.4); the leaps of faith, drafted for approval (1.5); MIG-INV-1 to MIG-INV-3, each with a P1 criterion, including the new MIG-22 and MIG-23 (1.6, 2.4); no component NFRs (2.5); classification and retention (2.6); owners and SLAs (2.7); the value and usability risks, drafted for approval (2.8); support and response targets (2.9); MIG-FR-25 and MIG-FR-24 verified by owner checks OC-06 and OC-07 (2.4, "Verified elsewhere"); a criterion of its own for MIG-FR-15 (MIG-24); rollback after scrubbing, now in MIG-FR-25 (2.4); and ADR 0001, accepted when the owner approves this PRD at Gate 1 (1.7).

**Gate 1 follow-up (version 5, owner decision, 2026-10-22).** The scrub backups keep plaintext v1 keys on disk. The owner approved them as an exception to NFR-3 and INV-6 that lasts until v1 is retired: they are written owner-only and deleted at retirement (MIG-FR-26, MIG-25, MIG-26; PRD-v7 1.5; test plan section 4). MIG-INV-3 names that exception. MIG-FR-26 stays P2 with P1 criteria (2.4). A breach of any invariant halts the rollout (PRD-v7 2.6).

**Reopened Gate 1 answer (version 6, owner decision, 2026-10-22).** One P1 criterion per command for the INV-4 and SEC-INV-7 exception: `secrets import` and `scrub-client-configs` read only the client configs, and only the legacy import reads the v1 folder (SPEC-v4 20). Added as MIG-FR-27 and MIG-27 to MIG-30.

**Assumptions**

- Assumption: the Parent column of 2.4 is left empty because the source PRD header names milestone M4 but no parent goal. MIG-FR-27 is the exception: it cites INV-4 (PRD-v7 1.5), which the exception in SPEC-v4 9 names.
- Assumption: the reopening note listed the commands `import-v1`, `scrub-client-configs`, `verify` and `cutover`. This PRD defines `secrets import`, `import-legacy` and `scrub-client-configs`; cutover is a milestone and a runbook, and there is no `verify` command. The read set therefore covers the commands this PRD names.
- Assumption: the owner allowed v2 reads at the exact paths in the read set. The listed paths come from SPEC-v4 10: `~/.config/research-mcp/config.toml` for `secrets import`, and `~/Library/Application Support/research-mcp/cache/cache.db` for `import-legacy`. The `cache.db` read (merging with works already present) is confirmed (owner decision, 2026-10-22).
- Assumption: the CLI's read of its own `config.toml` and the daemon's opens of its own `state.db` stay outside the per-command read sets (owner decision, 2026-10-23).
- Assumption: the implementer reads two v1 facts from the v1 repository, read-only: how to recognise the v1 server entry in a client config, and which env variable names the preferred web provider. The owner confirms both at review (owner decision, 2026-10-23).
- Assumption: the owner named the new command `restore-client-configs`. MIG-FR-25 already covers restoring on rollback, so no MIG-FR-28 is added.

**Answered on 2026-10-22 (owner decision, 2026-10-22).** `install --print-client-config` reads nothing beyond the v2 install (MIG-33). A new command, `restore-client-configs`, restores scrubbed values on rollback and reads only the scrub backups (MIG-FR-25, MIG-31). `import-legacy` refuses a symbolic link that leaves the v1 tree (MIG-32). Commands may read the v2 tree at the exact paths in the read set (MIG-34).

**Answered on 2026-10-23 (owner decision, 2026-10-23).** A new command, `research-mcp retire-v1 --confirm`, deletes the scrub backups at v1 retirement (MIG-FR-26, MIG-35). `secrets import` and `scrub-client-configs` read the three named client config files, and a symbolic final component is refused (MIG-32 note).

**Open questions**

None.

## 2.14 Glossary

> **Owner:** A · **Persona:** `product-writer`

| Term | Definition |
| --- | --- |
| v1 | The current server, `my-research-mcp-server`, read-only until cutover (PRD-v4; ADR 0001). |
| v2 | The rebuilt server in the new repository (ADR 0001). |
| Cutover | Milestone M4: credential import, optional corpus import, client configs switched, v1 stopped (PRD-v6 2.9). |
| Parallel period | The time when the v2 entry (`research`) and the v1 entry both run in the clients (MIG-FR-21). |
| Retirement | Removing the v1 entries and archiving the v1 repository, after 14 days with no fallback and the owner's go-ahead (MIG-FR-24). |
| Fingerprint | What the import prints in place of a credential value, so the owner can tell values apart (MIG-FR-1, MIG-FR-2). |
| Legacy import | The optional, one-time import of the v1 corpus by `research-mcp import-legacy` (MIG-FR-10). |
| `legacy` scheme | The identifier scheme for v1 ids with an unknown prefix and for the raw v1 ids of merged rows (MIG-FR-11; SPEC-v2 9.6). |
| Tool map | The table that maps each of the 53 v1 tools to its v2 replacement, or to "removed" with the reason (MIG-FR-22). |
| Scrub backup | The copy of each client config file that `scrub-client-configs` writes before it removes the v1 `env` values; rollback after scrubbing restores values from it (MIG-FR-5, MIG-FR-25; MIGRATION-v2 3). |
| Read set | The paths one owner-run migration command may read; a read of any other path is refused and reported (MIG-FR-27). |

## 2.15 ID history

> **Owner:** C · **Persona:** `product-writer` records; the owner confirms

No ID left this PRD in version 6. MIG-FR-23 (superseded in version 5) keeps its row here so the history stays complete.

| ID | Status | Replaced by | Reason |
| --- | --- | --- | --- |
| MIG-FR-23 | superseded | MIG-FR-25 | The response changed: after `scrub-client-configs`, rollback restores the scrubbed values from the scrub backups (owner decision, 2026-10-22) |

New IDs and editorial changes in this version; these rows are not definitions.

| Changed or new ID | Change | Date | Reason |
| --- | --- | --- | --- |
| MIG-FR-27 | New requirement: each owner-run migration command reads only its read set; any other read is refused and reported | 2026-10-22 | owner decision, 2026-10-22 |
| MIG-27 | New criterion: `secrets import` opens only the client config files | 2026-10-22 | owner decision, 2026-10-22 |
| MIG-28 | New criterion: `scrub-client-configs` opens only the client config files | 2026-10-22 | owner decision, 2026-10-22 |
| MIG-29 | New criterion: `import-legacy` opens only files under the v1 tree it was given | 2026-10-22 | owner decision, 2026-10-22 |
| MIG-30 | New criterion: a read outside a command's read set is refused with an error that names the path | 2026-10-22 | owner decision, 2026-10-22 |
| MIG-31 | New criterion: `restore-client-configs` opens only the scrub backups | 2026-10-22 | owner decision, 2026-10-22 |
| MIG-32 | New criterion: `import-legacy` refuses a symbolic link that leaves the v1 tree | 2026-10-22 | owner decision, 2026-10-22 |
| MIG-33 | New criterion: `install --print-client-config` reads nothing beyond the v2 install | 2026-10-22 | owner decision, 2026-10-22 |
| MIG-34 | New criterion: reads of the v2 tree stay at the listed paths | 2026-10-22 | owner decision, 2026-10-22 |
| MIG-FR-25 | Editorial: names the command `restore-client-configs`; the ID is kept | 2026-10-22 | owner decision, 2026-10-22 |
| MIG-35 | New criterion: `retire-v1` without `--confirm` refuses and deletes nothing; with `--confirm` it deletes the scrub backups, reports each path, and touches nothing else | 2026-10-23 | owner decision, 2026-10-23 |
| MIG-FR-26 | Editorial: names the command `retire-v1 --confirm` that deletes the scrub backups; the ID is kept | 2026-10-23 | owner decision, 2026-10-23 |

### Gate 1: Requirements approved

| Approver | Date | Notes |
| --- | --- | --- |
| Pending | Pending | Version 6 is a draft; the owner approves it at the reopened Gate 1 |

## 2.16 Earlier IDs

> **Owner:** A · **Persona:** `product-writer`

| Earlier ID | New ID |
| --- | --- |
| FR-MIG-01 | MIG-FR-1 |
| FR-MIG-02 | MIG-FR-2 |
| FR-MIG-03 | MIG-FR-3 |
| FR-MIG-04 | MIG-FR-4 |
| FR-MIG-05 | MIG-FR-5 |
| FR-MIG-06 | MIG-FR-6 |
| FR-MIG-10 | MIG-FR-10 |
| FR-MIG-11 | MIG-FR-11 |
| FR-MIG-12 | MIG-FR-12 |
| FR-MIG-13 | MIG-FR-13 |
| FR-MIG-14 | MIG-FR-14 |
| FR-MIG-15 | MIG-FR-15 |
| FR-MIG-20 | MIG-FR-20 |
| FR-MIG-21 | MIG-FR-21 |
| FR-MIG-22 | MIG-FR-22 |
| FR-MIG-23 | MIG-FR-23 (superseded by MIG-FR-25) |
| FR-MIG-24 | MIG-FR-24 |
| AT-MIG-01 | MIG-1 |
| AT-MIG-02 | MIG-2 |
| AT-MIG-03 | MIG-3 |
| AT-MIG-04 | MIG-4 |
| AT-MIG-05 | MIG-5 |
| AT-MIG-06 | MIG-6 |
| AT-MIG-10 | MIG-10 |
| AT-MIG-11 | MIG-11 |
| AT-MIG-12 | MIG-12 |
| AT-MIG-13 | MIG-13 |
| AT-MIG-14 | MIG-14 |
| AT-MIG-20 | MIG-20 |
| AT-MIG-21 | MIG-21 |
