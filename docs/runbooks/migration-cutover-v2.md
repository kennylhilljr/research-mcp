---
title: "Cutover from v1 to v2"
type: runbook
version: 2
status: draft
owner: "Kenny Hill"
component: migration
artifact_type: operations
scope_level: L3
scope_name: "research-mcp"
derives_from: docs/runbooks/migration-cutover-v1.md
date: 2026-10-22
---

# Runbook: Cutover from v1 to v2 (v2)

The cutover steps of [MIGRATION v2](../../docs-archive/migration/MIGRATION-v2.md) section 3. Version 2 follows [PRD-migration v6](../prd/components/PRD-migration-v6.md), [PRD v8](../prd/PRD-v8.md) (draft successor of [PRD v7](../prd/PRD-v7.md)), [SPEC v5](../spec/SPEC-v5.md) (draft), [LLD-platform v2](../lld/LLD-platform-v2.md) and [test plan v4](../test/test-plan-v4.md) (draft). The design behind the steps is in [LLD-migration](../lld/LLD-migration-v1.md).

## When to use it

> **Owner:** H · **Persona:** none (`sre` drafts)

At milestone M4, when every M4 criterion passes. Owner checks OC-06 (steps 1 to 9 completed, including rollback after scrubbing) and OC-07 (14 days on v2) in the test plan section 3 close it (MIG-FR-25, MIG-FR-24).

## Before you start

> **Owner:** A · **Persona:** `sre`

1. v1 is never modified. Its database is opened immutable; its folder is only read. `import-legacy` refuses a symbolic link that leaves the v1 tree (MIG-32).
2. No credential is re-entered. They move from the v1 client configs into the Keychain.
3. The corpus import is optional. v2 works with an empty cache.
4. Rollback is one config change until step 9; after step 9 it also needs `restore-client-configs` (MIG-FR-25).
5. Upgrading v2 during the cutover: `research-mcp upgrade` unloads the KeepAlive daemon job with `launchctl bootout gui/$UID/local.research-mcpd` before any file is replaced, and does the same for the watchdog and doctor jobs (LLD-platform v2 5.9; PLAT-FR-55). Do not replace files by hand while the job is loaded.
6. Backups: nightly backups keep the last 7 (`backup.keep`, a count of folders, not days; PLAT-FR-57). The upgrade writes a `pre-upgrade-*` folder first; only the newest is kept (LLD-platform v2 3.3).
7. Watchdog quiet hours: `notify.quiet_hours` defaults to `21:00-08:00` local time. The 15-minute watchdog's dead-daemon notice may not show as a macOS notification in that window, so run `research-mcp doctor` by hand after any step done in it (LLD-platform v2, configuration table).
8. Scrub backups hold plaintext v1 keys, written owner-only (mode 0600). This is an approved exception to NFR-3 and INV-6 until v1 is retired; they are deleted at retirement (MIG-FR-26; MIG-25; MIG-26).

## Steps

> **Owner:** A · **Persona:** `sre`

| # | Step | Command or action | Check |
|---|---|---|---|
| 1 | Install v2 and the daemon | `uv tool install <path to sample-app>[pdf,embeddings,macos]`, then `research-mcp install` | `research-mcp doctor` shows the daemon alive |
| 2 | Set the contact email | `research-mcp config set contact.email <address>` | doctor `contact_email` ok |
| 3 | Import credentials and web-search settings (dry run, then real) | `research-mcp secrets import --dry-run`, then `research-mcp secrets import` | Names and fingerprints listed, no value shown; the Vertex instance, the Programmable Search engine id and `web.order` printed; Credentials page shows each `ok` or `unknown_expiry` |
| 4 | Add new free keys (open decision O2) | Create OpenAlex and Semantic Scholar keys; `security add-generic-password -U -s research-mcp/OPENALEX_API_KEY -a "$USER" -w` | Source board: `openalex` ok |
| 4b | Web search caps and sign-in | `research-mcp config set sources.<id>.budget_cap <n>` for each web source; for Vertex, `gcloud auth application-default login` if doctor reports the Google sign-in `missing` or `invalid` | Source board: each configured web source `ok`; a `search` with `groups=["web"]` and `site_set="v1_docs"` returns results |
| 5 | Optional corpus import | `research-mcp import-legacy <v1 corpus folder> --dry-run`, review the report, then without `--dry-run` | Report matches the dry run; any symbolic link leaving the v1 tree is refused and listed (MIG-32) |
| 6 | Add v2 to clients beside v1 | Paste the entries from `research-mcp install --print-client-config` (server name `research`) | Each client lists the v2 tools |
| 7 | Parallel use, 3 to 7 days | Use v2 for real work; v1 still available | No blocking issue; source board mostly ok |
| 8 | Disable v1 entries | Set the v1 entries to disabled in each client | Agents use only v2 |
| 9 | Scrub plaintext keys | `research-mcp secrets scrub-client-configs` (writes a backup of each file first) | (a) A grep of each client config for the old key values finds none; (b) one backup exists per scrubbed file, mode 0600 (`stat -f %Lp <backup>` prints `600`); (c) the command output shows no secret value; (d) every Keychain item still reads `ok` in doctor |
| 10 | Retire v1 | Only after 14 days of daily use with no fallback and the owner's explicit go-ahead (MIG-FR-24): remove the v1 entries; archive the v1 repository; delete the scrub backups (MIG-26); keep the v1 corpus folder until the owner removes it | (a) The owner's go-ahead is recorded before any removal; (b) no v1 entry remains in any client; (c) no scrub backup remains (list of the backup folder is empty); (d) v1 repository archived, corpus folder untouched; (e) `research-mcp doctor` green |

Each deletion in step 10 needs a recorded owner decision; without one, halt (see Halt).

## Halt

> **Owner:** A · **Persona:** `sre`

The rollout halts, with no further steps, on any of these (PRD-v7 2.6; PRD-migration v6 section on halting conditions):

- a deletion without a recorded owner decision;
- a secret in any output (command output, log, UI or notification);
- a fallback to v1 during the 14-day window (this also resets MIG-OUT-1);
- any other invariant breach, including MIG-INV-1 to MIG-INV-3.

On a halt: stop, change nothing further, and report to the owner. Do not retry a step that caused the halt.

## Verify

> **Owner:** A · **Persona:** `sre`

- [ ] `research-mcp doctor` is green and a three-source search through the shim returns results (OC-01).
- [ ] Step 9 checks (a) to (d) pass.
- [ ] Rollback after scrubbing was exercised (see Roll back) and the v1 entries worked, then v2 was restored as the active setup (OC-06; MIG-FR-25).
- [ ] After 14 days with no fallback, step 10 checks (a) to (e) pass (OC-07).

## Roll back

> **Owner:** H · **Persona:** none (`sre` drafts)

Before step 9: re-enable the v1 entries (step 8 reversed). The Keychain items stay; v1 does not use them.

After step 9 (rollback-after-scrub restore, MIG-FR-25): v1 does not read the Keychain, so first restore the scrubbed values, then re-enable the v1 entries.

1. Run `research-mcp restore-client-configs`. It reads only the scrub backups (MIG-31).
2. Check: each client config again holds its v1 `env` values (compare against the backup by file, not by printing values); the command output shows no secret value.
3. Re-enable the v1 entries in each client.
4. Check: each client lists the v1 tools.
5. The scrub backups stay until v1 is retired (MIG-FR-26). Treat the rollback as a fallback to v1 for the halt rules.

After step 10: the scrub backups are deleted, so restore is not possible; v1 is archived and the Keychain items are the only copy of the keys. Stop and ask the owner; this cannot be undone by this runbook.

Who decides (owner decision, 2026-10-23): the rollout halts on any halt trigger (PRD-v7 2.6; see Halt). Rollback to v1 happens only on the owner's explicit decision. Then the MIG-FR-25 steps above run (with `restore-client-configs` if the configs were scrubbed) and the 14-day clock restarts.

Reference for rollback and halt:

- Client configs touched by scrub and restore: the Claude Desktop config, `~/.claude.json` and `~/.openclaw/openclaw.json`. A symlinked file is refused; the owner pastes the entries by hand.
- Scrub backup folder: `~/.research-mcp-migration/scrub-backups/` (folder mode 0700, files mode 0600).
- `research-mcp retire-v1 --confirm` deletes the scrub backups at retirement (MIG-35). After it runs, restore is not possible.
- Halt marker: `~/.research-mcp-migration/HALTED.json`. The owner clears it by deleting it by hand after reading it. Nothing else clears it.
- Before the scrub step (step 9), the implementer confirms with the owner how v1 client entries are recognized.

## Related

> **Owner:** A · **Persona:** `doc-steward`

- [LLD-migration v2](../lld/LLD-migration-v2.md), [PRD-migration v6](../prd/components/PRD-migration-v6.md), [PRD v8](../prd/PRD-v8.md) (draft), [SPEC v5](../spec/SPEC-v5.md) (draft), [test plan v4](../test/test-plan-v4.md) (draft), [LLD-platform v2](../lld/LLD-platform-v2.md), [ADR 0001](../adr/0001-new-repo-v1-read-only.md)
