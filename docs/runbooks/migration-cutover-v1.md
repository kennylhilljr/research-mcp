---
title: "Cutover from v1 to v2"
type: runbook
version: 1
status: draft
owner: "Kenny Hill"
component: migration
artifact_type: operations
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/migration/MIGRATION-v2.md
date: 2026-10-22
---

# Runbook: Cutover from v1 to v2 (v1)

The cutover steps of [MIGRATION v2](../../docs-archive/migration/MIGRATION-v2.md) section 3, unchanged except for the requirement IDs. The design behind them (principles, inventory, the v1 to v2 tool map and the legacy import) is in [LLD-migration](../lld/LLD-migration-v1.md); the requirements are in [PRD-migration](../prd/components/PRD-migration-v4.md).

## When to use it

> **Owner:** H · **Persona:** none (`sre` drafts)

At milestone M4, when every M4 criterion passes. Owner checks OC-06 (steps completed) and OC-07 (14 days on v2) in the [test plan](../test/test-plan-v1.md) section 3 close it.

## Before you start

> **Owner:** A · **Persona:** `sre`

1. v1 is never modified. Its database is opened immutable; its folder is only read.
2. No credential is re-entered. They move from the v1 client configs into the Keychain.
3. The corpus import is optional. v2 works with an empty cache.
4. Rollback is one config change until v1 is retired.

## Steps

> **Owner:** A · **Persona:** `sre`

| # | Step | Command or action | Check |
|---|---|---|---|
| 1 | Install v2 and the daemon | `uv tool install <path to my-research-mcp>[pdf,embeddings,macos]`, then `research-mcp install` | `research-mcp doctor` shows the daemon alive |
| 2 | Set the contact email | `research-mcp config set contact.email <address>` | doctor `contact_email` ok |
| 3 | Import credentials and web-search settings (dry run, then real) | `research-mcp secrets import --dry-run`, then `research-mcp secrets import` | Names and fingerprints listed; the Vertex instance `vertex_v1`, the Programmable Search engine id and `web.order` printed; Credentials page shows each `ok` or `unknown_expiry` |
| 4 | Add new free keys (open decision O2) | Create OpenAlex and Semantic Scholar keys; `security add-generic-password -U -s research-mcp/OPENALEX_API_KEY -a "$USER" -w` | Source board: `openalex` ok |
| 4b | Web search caps and sign-in | `research-mcp config set sources.<id>.budget_cap <n>` for each web source; for Vertex, `gcloud auth application-default login` if doctor reports the Google sign-in `missing` or `invalid` | Source board: each configured web source `ok`; a `search` with `groups=["web"]` and `site_set="v1_docs"` returns results |
| 5 | Optional corpus import | `research-mcp import-legacy ~/arxiv-papers --dry-run`, review the report, then without `--dry-run` | Report shows about 132 works, 54 merges, 10 HTML documents |
| 6 | Add v2 to clients beside v1 | Paste the entries from `research-mcp install --print-client-config` (server name `research`) | Each client lists the v2 tools |
| 7 | Parallel use, 3 to 7 days | Use v2 for real work; v1 still available | No blocking issue; source board mostly ok |
| 8 | Disable v1 entries | Set the v1 entries to disabled in each client | Agents use only v2 |
| 9 | Scrub plaintext keys | `research-mcp secrets scrub-client-configs` (backs up each file first) | No secret values remain in client configs |
| 10 | Retire v1 | After 14 days with no fallback and the owner's go-ahead: remove the v1 entries; archive the v1 repository; keep `~/arxiv-papers` until the owner removes it | Owner sign-off |

Rollback before step 10: re-enable the v1 entries (step 8 reversed). The Keychain items stay; v1 does not read them, so the scrubbed values must be restored from the step 9 backups if rollback is needed after scrubbing.

## Verify

> **Owner:** A · **Persona:** `sre`

- [ ] Q: The source document has no separate verification list beyond the checks inside the steps. Which checks confirm the cutover (for example `research-mcp doctor` green and a three-source search through the shim, as in owner check OC-01)?

## Roll back

> **Owner:** H · **Persona:** none (`sre` drafts)

Rollback before step 10: re-enable the v1 entries (step 8 reversed). The Keychain items stay; v1 does not read them, so the scrubbed values must be restored from the step 9 backups if rollback is needed after scrubbing (MIGRATION-v2 section 1 principle 4 and section 3; MIG-FR-23).

- [ ] Q: Who decides a rollback, and what triggers it?

## Related

> **Owner:** A · **Persona:** `doc-steward`

- [LLD-migration](../lld/LLD-migration-v1.md), [PRD-migration](../prd/components/PRD-migration-v4.md), [ADR 0001](../adr/0001-new-repo-v1-read-only.md)
