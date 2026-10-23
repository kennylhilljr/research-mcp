# sdd command line

```bash
node tools/sdd/cli.mjs <command> [options]
node tools/sdd/cli.mjs --help
```

Boolean flags (`--apply`, `--force`, `--dry-run` and the like) never consume the next word, so `adopt --apply ../repo` works.

| Command | What it does |
| --- | --- |
| `init [DIR]` | Set up the framework in a new repository. Options: `--name`, `--components tech:TECH,billing:BILL`, `--owner`, `--git`, `--dry-run`, `--force` (existing files that differ are proposed under `.sdd-proposed/<path>`) |
| `adopt [DIR]` | Analyze an existing repository and plan the framework files. Dry run by default; `--apply` writes. Never modifies or deletes existing files; a framework file that would replace an existing one is written to `.sdd-proposed/<path>`. Refuses a repository that already has `sdd.config.json` (use `upgrade`). `--json` prints the analysis; `--allow-dirty` skips the clean working tree check |
| `upgrade [DIR]` | Bring a repository's framework-owned files (skills, personas, commands, tools, templates, standards, guides, framework diagrams) to this release. Dry run by default; `--apply` writes new files and puts changed ones in `.sdd-proposed/<path>`; `--apply --overwrite` replaces them; `--allow-dirty` skips the clean working tree check. Never touches project documents, code, `AGENTS.md`, `CLAUDE.md`, settings or config |
| `doctor [DIR]` | Check the local environment: Node, git, Claude Code, hooks, skills, personas, spec-lint, trace-check |
| `check` | Run spec-lint and trace-check (advisory when `adoption.mode` is `advisory`). `--base REF` adds reach for changed files |
| `new TYPE` | Create a document from its template. Types: `vision`, `research --name`, `prd`, `prd-component --component --prefix`, `adr --name`, `spec`, `lld --component`, `test-plan`, `kickoff/plan/handoff --milestone M1`, `runbook --name`, `postmortem --name` |
| `new --help` | List the document types and their options |
| `new --next PATH` | Copy a frozen document into its next version as a draft |
| `docmap` | Regenerate the organizational scope map and the delivery artifact index in the doc map at `paths.docMap` (`docs/README.md`, or `docs/DOCMAP.md` when adopt found an existing `docs/README.md`; `--check` for CI) |
| `catalog` | Regenerate the skill, agent and command catalog in `docs/guide/catalog.md` (`--check` for CI) |
| `version` | Print the framework version |

## Files

| File | Role |
| --- | --- |
| [`cli.mjs`](cli.mjs) | Entry point and argument handling |
| [`init.mjs`](init.mjs) | New repositories |
| [`adopt.mjs`](adopt.mjs) | Existing repositories: analysis, missing-information list, draft documents |
| [`machinery.mjs`](machinery.mjs) | What gets installed, and the write plan that never overwrites |
| [`upgrade.mjs`](upgrade.mjs) | Upgrades of framework-owned files |
| [`doctor.mjs`](doctor.mjs) | Environment checks |
| [`docs.mjs`](docs.mjs) | `new`, `docmap`, `catalog` |
| [`scaffold/`](scaffold) | Starting files for a target repository (repository instructions, settings, CI, doc map, scope map, ADR index, CODEOWNERS). Their links resolve where they are installed |
| [`sdd.config.schema.json`](sdd.config.schema.json) | Schema for `sdd.config.json` |
