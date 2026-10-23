---
title: "Migration and Cutover"
type: prd-component
version: 4
status: draft
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
prefix: MIG
component: migration
parent: docs/prd/PRD-v5.md
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
supersedes: docs-archive/prd/components/PRD-migration-v3.md
date: 2026-10-22
---

# Component PRD: Migration and Cutover (v4)

This version moves [PRD-migration v3](../../../docs-archive/prd/components/PRD-migration-v3.md) onto the SDD component template. Requirements and acceptance criteria keep their meaning; their IDs are renamed (section 2.16). Parent: [PRD v5](../PRD-v5.md). Design: [LLD-migration v1](../../lld/LLD-migration-v1.md). Cutover steps: [migration cutover runbook](../../runbooks/migration-cutover-v1.md).

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

The owner must move from v1 to v2 without re-entering any credential, without touching v1's data, and with an easy way back until v2 has proven itself (PRD-migration-v3 1).

v1 is in daily use by three MCP clients, so v2 is built in a new repository and v1 keeps running under its existing client entries until cutover at milestone M4 (ADR 0001; PRD-v4 10). The parent problem, v1's 53 single-source tools and its silent breakage, is in the parent PRD (PRD-v4 2).

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| The owner | Move to v2 without re-entering credentials, keep v1's data untouched, and keep a one-step way back (PRD-migration-v3 1; MIGRATION-v2 1) | |
| The MCP clients on the Mac: Claude desktop, Claude Code, OpenClaw | A v2 server entry beside the v1 entry during the parallel period (PRD-migration-v3 FR-MIG-01, FR-MIG-21) | |
| Agents whose instructions mention v1 tool names | A map from each v1 tool to the v2 tool and arguments that replace it (PRD-migration-v3 FR-MIG-22; MIGRATION-v2 4) | |

- [ ] Q: What is the relative size of each user or stakeholder above?

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- Credential import from the v1 client configs into the Keychain, including the v1 web-search credentials and settings (PRD-v4 5; ADR 0012).
- Optional import of the v1 corpus (PRD-v4 5; MIGRATION-v2 1).
- Client cutover, rollback and v1 retirement (PRD-v4 5).
- The v1 to v2 tool map (PRD-migration-v3 FR-MIG-22).

| Non-goal | Why it is excluded |
| --- | --- |
| Keeping v1 tool names or result shapes | Clients are updated at cutover (PRD-v4 3.2). |
| Migrating or changing the owner's separate K-12 teacher server | It is not migrated or changed (PRD-v4, changes from v3). |
| Importing the v1 datasets (`~/research-datasets`) or keeping the v1 dataset tools | Not inspected; no SQL or dataset tool in the first release (MIGRATION-v2 2 and 4; ADR 0009; PRD-v4 11, O4). |

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |
| MIG-OUT-1 | Days of daily use on v2 with no fallback to v1 | | 14 days, then v1 archived (PRD-v4 10, M4 exit) | M4 |

- [ ] Q: Confirm MIG-OUT-1 as carried over from the PRD-v4 M4 exit, and state its baseline.

## 1.5 Leaps of faith

> **Owner:** H · **Persona:** none

| Leap of faith | How we will validate it | By when |
| --- | --- | --- |
| | | |

- [ ] Q: Which two or three bets must hold for the cutover to succeed?

## 1.6 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

| ID | The system must never | Source (regulation, policy, contract) |
| --- | --- | --- |
| MIG-INV-1 | Modify v1's data or folder (its database is opened immutable; its folder is only read) | MIGRATION-v2 1, principle 1; ADR 0001 |
| MIG-INV-2 | Print a credential value during the credential import | PRD-migration-v3 FR-MIG-01; parent NFR-4 |
| MIG-INV-3 | Write an imported credential anywhere but the Keychain | ADR 0001; parent NFR-3 |

- [ ] Q: Confirm MIG-INV-1 to MIG-INV-3 as invariants (each would become a P1 criterion), and add any others.

## 1.7 Known constraints and decisions

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

| Decision or constraint | Status (made or open) | Rationale or link |
| --- | --- | --- |
| v2 is a new repository; v1 stays read-only and running until cutover; at cutover v1's entries are disabled, not deleted | made (the ADR's status reads Proposed) | ADR 0001 |
| The v1 web-search credentials are imported, and the Vertex project, location and engine id and the Programmable Search engine id carry over as settings | made | ADR 0012; it supersedes review decision D7 |
| Imported cache items get a 120-day expiry | made | ADR 0011; it supersedes the 30 days of review decision D3 |
| Tools that took caller-chosen local paths or ran SQL are removed, not mapped | made | ADR 0009 |
| No SQL or dataset tool in the first release | open (recommendation: none) | PRD-v4 11, O4 |
| New free OpenAlex and Semantic Scholar keys are added at cutover | open (recommendation: yes) | PRD-v4 11, O2; MIGRATION-v2 3, step 4 |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

---

## 2.1 Customer discovery

> **Owner:** A · **Persona:** `analyst`

The deep review of v1 ([REVIEW v1](../../../docs-archive/review/REVIEW-v1.md) and [findings-functional v1](../../../docs-archive/review/findings-functional-v1.md)) inventoried what the cutover must carry:

- v1 exposes 53 tools (findings-functional 2).
- v1's data in `~/arxiv-papers` is `arxiv_index.db` (34 MB, 186 rows, 11,403 chunks), 123 PDFs and `embeddings.duckdb`, with 54 duplicate pairs and 10 web pages stored by URL (MIGRATION-v2 2).
- v1 credentials live in the `env` blocks of the v1 server entries in the Claude desktop, Claude Code and OpenClaw configs; their values were never read during design (MIGRATION-v2 2).

## 2.2 User stories and priority

> **Owner:** C for stories (`product-writer`), H for priority · **Seed question:** 3

No user stories exist yet (see 2.13).

| ID | As a... I want... so that... | Priority | Why this priority |
| --- | --- | --- | --- |

## 2.3 User experience

> **Owner:** C · **Persona:** `product-writer` drafts the narrative; designers own the design artifacts · **Seed question:** 3

The owner runs the cutover from the command line, following the [cutover runbook](../../runbooks/migration-cutover-v1.md). The owner first runs `research-mcp secrets import --dry-run` to see the names, fingerprints and settings that would be written, then runs it for real. The owner may then run `research-mcp import-legacy ~/arxiv-papers --dry-run`, review the report, and run it without `--dry-run`. The owner pastes the entries from `research-mcp install --print-client-config` into each client under the server name `research`, uses v2 beside v1 for a parallel period, then disables the v1 entries and scrubs the plaintext keys with `research-mcp secrets scrub-client-configs`. Rollback until retirement is re-enabling the v1 entries. (MIGRATION-v2 3.)

## 2.4 Functional requirements and acceptance criteria

> **Owner:** C · **Persona:** `product-writer` drafts requirements and criteria as options; the owner selects and approves · **Seed questions:** 3, 12

**Credentials**

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| MIG-FR-1 | `research-mcp secrets import` finds the v1 server entries in the MCP client configs on the Mac (Claude desktop, Claude Code, OpenClaw), reads the credential values from their `env` blocks, and writes each to the Keychain as `research-mcp/<NAME>`. It prints names, fingerprints and the config file each came from; never values. | | | P1 |
| MIG-FR-2 | When the same name has different values in different configs, the import stops for that name and asks the owner which config wins (by fingerprint), instead of guessing. | | | P1 |
| MIG-FR-3 | Every v1 credential a v2 source uses is imported, including the Brave and SerpAPI keys and the Google key shared by the Developer Knowledge and Programmable Search sources. A credential no v2 source uses is listed as "not imported" with a note and is not copied. | | | P1 |
| MIG-FR-4 | The import is idempotent and has a `--dry-run` that shows what would be written. | | | P1 |
| MIG-FR-5 | After cutover, `research-mcp secrets scrub-client-configs` removes the plaintext `env` values from the old v1 entries (with a backup of each file first), on explicit confirmation. | | | P2 |
| MIG-FR-6 | The import carries v1's non-secret web-search settings into `config.toml`: the Vertex project, location and engine id become the instance `vertex_v1`; the Programmable Search engine id becomes `sources.google_pse.engine_id`; v1's provider choice becomes `web.order` (when v1 named one provider, it goes first). It prints each setting it wrote. | | | P1 |

**Optional corpus import**

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| MIG-FR-10 | `research-mcp import-legacy <path> [--dry-run] [--mode M]` (M is `cache`, `archive` or `metadata_only`) runs as a job. It opens the v1 database read-only (immutable) and never modifies the v1 folder. | | | P2 |
| MIG-FR-11 | The import normalizes identifiers (arXiv without version, DOI and CORE prefixes, v1's crawled-site rows become HTML documents with their URL under the matching `docs_site_<project>` source), merges the 54 duplicate pairs keeping the titled row's metadata, and maps unknown prefixes (`harv...`, `penn...`) to a `legacy` scheme followed by a best-effort lookup. | | | P2 |
| MIG-FR-12 | The import re-extracts the PDFs with the v2 parser and chunker rather than copying v1 chunks, and falls back to v1 chunks only where re-extraction fails. | | | P2 |
| MIG-FR-13 | The default mode is `cache`: every imported item gets a fresh 120-day expiry and goes through the normal review. | | | P2 |
| MIG-FR-14 | The import writes a report (JSON and Markdown) with rows read, works created, merged pairs, unresolved ids, re-extraction failures, chunk counts before and after, and the legacy-id to work-id map. | | | P2 |
| MIG-FR-15 | Running the import is optional; v2 works fully with an empty cache. | | | P1 |

**Client cutover and v1 retirement**

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| MIG-FR-20 | `research-mcp install --print-client-config` prints, for each client, the server entry that launches `research-mcp stdio` (no secrets). | | | P1 |
| MIG-FR-21 | Cutover adds the v2 entry beside the v1 entry under a new name (`research`), so both can run during a parallel period; the v1 entry is disabled, not deleted, at cutover. | | | P1 |
| MIG-FR-22 | A tool map documents, for each of the 53 v1 tools, the v2 tool and arguments that replace it (or "removed" with the reason), so agent instructions can be updated. | | | P1 |
| MIG-FR-23 | Rollback is re-enabling the v1 entry in the client configs; it needs no data conversion because v1's data is never modified. | | | P1 |
| MIG-FR-24 | v1 is retired (entry removed, repository archived) only after 14 days of daily use on v2 with no fallback, and only on the owner's explicit go-ahead. | | | P1 |

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

MIG-FR-20 is also verified by PLAT-82 in the platform component. MIG-FR-23 and MIG-FR-24 have no acceptance criterion; they are checked by the owner checks OC-06 and OC-07 (TEST-PLAN-v3 5).

## 2.5 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

The parent's cross-cutting requirements apply, in particular NFR-3 (no secrets at rest outside the Keychain), NFR-4 (no secret in any output) and NFR-9 (testable offline) (PRD-v4 6).

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |

- [ ] Q: Does this component need its own NFRs (for example a time limit for the legacy import or the credential import)? If so, what are the targets?

## 2.6 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

| Data | Classification | Source or owner | Retention | Notes |
| --- | --- | --- | --- | --- |
| v1 credential values in client config `env` blocks | | MCP client configs on the Mac (MIGRATION-v2 2) | Removed from the configs by `scrub-client-configs` after cutover (MIG-FR-5) | Written only to the Keychain as `research-mcp/<NAME>` (MIG-FR-1; ADR 0001) |
| v1 web-search settings (Vertex project, location, engine id; Programmable Search engine id) | Not secrets (ADR 0012) | v1 client configs | | Written to `config.toml` (MIG-FR-6) |
| v1 corpus (`arxiv_index.db`, PDFs, `embeddings.duckdb`) | | `~/arxiv-papers` (MIGRATION-v2 2) | Kept until the owner removes it (MIGRATION-v2 3, step 10) | Read only (MIG-INV-1) |
| Imported works and documents | | v2 `cache.db` | 120 days in mode `cache` (MIG-FR-13; ADR 0011) | |
| Import report | | `state_dir/imports/<timestamp>/` (SPEC-v2 9.6) | | |

- [ ] Q: What is the classification of each data item above, and the retention of the web-search settings and the import report?

## 2.7 Integrations and owners

> **Owner:** H confirms owners and SLAs · **Persona:** `architect` may draft · **Seed question:** 8

| System | Owner | Relationship (depends on, feeds, replaces) | SLA |
| --- | --- | --- | --- |
| Claude desktop, Claude Code and OpenClaw client configs | | Depends on (read for credentials; v2 entry added; v1 entry disabled and scrubbed) | |
| macOS Keychain | | Feeds (credentials written as `research-mcp/<NAME>`) | |
| v1 server (`my-research-mcp-server`) and its data | | Replaces (after retirement, MIG-FR-24) | |
| v2 cache, extraction worker and `get_work` lookup | | Feeds (legacy import writes works, documents and chunks) | |

- [ ] Q: Who owns each integration above, and what SLA applies, if any?

## 2.8 Product risks

> **Owner:** H · **Persona:** none

| Risk | Question | Assessment | Mitigation |
| --- | --- | --- | --- |
| Value | Will customers choose to use this? | | |
| Usability | Can customers use it, including with accessibility needs? | | |
| Viability | Does it work for the business: economics, legal, compliance, operations? | Two server processes may run side by side during the parallel period, and v2's global rate limits do not cover v1's calls (ADR 0001). | The parallel period should be short (ADR 0001). |

- [ ] Q: What is the assessment and mitigation for the value and usability risks?

## 2.9 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | v2 runs beside v1 for a parallel period of 3 to 7 days; v1 entries are then disabled, not deleted; v1 is retired only after 14 days with no fallback and the owner's go-ahead (MIGRATION-v2 3; MIG-FR-21; MIG-FR-24). |
| Business conditions that must halt the rollout | A blocking issue during parallel use (MIGRATION-v2 3, step 7). Rollback is re-enabling the v1 entries (MIG-FR-23). |
| Support owner and escalation path | |
| Response targets by severity (S0 to S4) | |

- [ ] Q: Who is the support owner and escalation path, and what are the response targets by severity?

## 2.10 Measurement and experimentation

> **Owner:** C · **Persona:** `product-writer` drafts; the owner decides

| Outcome | Measured by | Experiment (if any) |
| --- | --- | --- |
| MIG-OUT-1 | Owner check OC-07: 14 days on v2 with no fallback; the owner approves retiring v1 (TEST-PLAN-v3 6) | none |

## 2.11 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

All M4 tests pass; owner check OC-06 (cutover steps 1 to 9 completed), then OC-07 (14 days on v2 with no fallback; the owner approves retiring v1) (TEST-PLAN-v3 8). Exit: 14 days of daily use on v2 with no fallback to v1; then v1 archived (PRD-v4 10).

## 2.12 Edge cases and error behavior

> **Owner:** A · **Persona:** `product-writer`

- The same credential name has different values in different client configs: the import stops for that name and asks (MIG-2).
- A v1 credential is not used by any v2 source: it is reported as not imported and not copied (MIG-3).
- The import is run twice, or with `--dry-run`: the result is the same, and a dry run writes nothing (MIG-4).
- A v1 row has an unknown prefix (`harv...`, `penn...`): it maps to the `legacy` scheme, followed by a best-effort lookup (MIG-FR-11, MIG-11).
- A v1 row stores a web page by URL: it becomes an HTML document under the matching `docs_site_<project>` source (MIG-FR-11, MIG-11).
- Re-extraction of a file fails: the v1 chunks are imported for that document (MIG-12).
- Rollback after the plaintext keys were scrubbed: v1 does not read the Keychain, so the scrubbed values must be restored from the scrub backups (MIGRATION-v2 3). No criterion covers this (see 2.13).

## 2.13 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves before Gate 1

- [ ] Q: Name the user stories for this component, with their priorities, so each requirement can cite one.
- [ ] Q: What is the relative size of each user or stakeholder in 1.2?
- [ ] Q: Confirm MIG-OUT-1 and state its baseline (1.4).
- [ ] Q: Which leaps of faith must hold (1.5)?
- [ ] Q: Confirm MIG-INV-1 to MIG-INV-3 (1.6). If confirmed, each needs a P1 criterion; today MIG-10 covers MIG-INV-1, MIG-1 covers part of MIG-INV-2, and no criterion covers MIG-INV-3.
- [ ] Q: Does the component need its own NFRs (2.5)?
- [ ] Q: Classify the data in 2.6 and set the missing retentions.
- [ ] Q: Name the owners and SLAs in 2.7, the risk assessments in 2.8 and the support owner and response targets in 2.9.
- [ ] Q: MIG-FR-23 (rollback) and MIG-FR-24 (retirement) are checked only by owner checks OC-06 and OC-07. Should they get acceptance criteria?
- [ ] Q: MIG-FR-15 says v2 works fully with an empty cache, but its only criterion, MIG-10, checks that the v1 database is opened immutable and the v1 folder is unchanged. Should MIG-FR-15 get its own criterion?
- [ ] Q: MIG-FR-23 says rollback needs no data conversion, but after `scrub-client-configs` rollback needs the scrubbed values restored from the backups (MIGRATION-v2 3). Should MIG-FR-23 or MIG-FR-5 say so?
- [ ] Q: ADR 0001 still reads "Proposed (accepted when the owner approves PRD v1)". Is it accepted?
- Assumption: the parent column is left empty because the source PRD header names milestone M4 but no parent goal.

## 2.14 Glossary

> **Owner:** A · **Persona:** `product-writer`

| Term | Definition |
| --- | --- |
| v1 | The current server, `my-research-mcp-server`, read-only until cutover (PRD-v4; ADR 0001). |
| v2 | The rebuilt server in the new repository (ADR 0001). |
| Cutover | Milestone M4: credential import, optional corpus import, client configs switched, v1 stopped (PRD-v4 10). |
| Parallel period | The time when the v2 entry (`research`) and the v1 entry both run in the clients (MIG-FR-21). |
| Retirement | Removing the v1 entries and archiving the v1 repository, after 14 days with no fallback and the owner's go-ahead (MIG-FR-24). |
| Fingerprint | What the import prints in place of a credential value, so the owner can tell values apart (MIG-FR-1, MIG-FR-2). |
| Legacy import | The optional, one-time import of the v1 corpus by `research-mcp import-legacy` (MIG-FR-10). |
| `legacy` scheme | The identifier scheme for v1 ids with an unknown prefix and for the raw v1 ids of merged rows (MIG-FR-11; SPEC-v2 9.6). |
| Tool map | The table that maps each of the 53 v1 tools to its v2 replacement, or to "removed" with the reason (MIG-FR-22). |

## 2.15 ID history

> **Owner:** C · **Persona:** `product-writer` records; the owner confirms

| ID | Status | Replaced by | Reason |
| --- | --- | --- | --- |

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
| FR-MIG-23 | MIG-FR-23 |
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

### Gate 1: Requirements approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |
