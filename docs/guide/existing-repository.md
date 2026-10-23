# Adopting the framework in an existing repository

`sdd adopt` analyzes a running application, drafts the framework's documents from what it finds, and lists what people still need to supply. It is built to be safe on a repository that is in production.

## Safety guarantees

- **Dry run by default.** Without `--apply`, nothing is written.
- **Existing files are never modified or deleted.** If a file the framework wants to add already exists (for example `AGENTS.md`, `CLAUDE.md` or `.claude/settings.json`), the framework's version is written to the same path under a `.sdd-proposed/` folder at the repository root (for example `.sdd-proposed/AGENTS.md`), for you to merge by hand. The folder sits outside `.claude/` and your source tree, so nothing loads a proposal by mistake.
- **The application's own commands are never run.** No install, build or test command is executed; the analysis only reads files.
- **CI is added, not changed.** On GitHub, a separate `.github/workflows/sdd.yml` runs the checks in advisory mode with `continue-on-error`, so it cannot fail existing pipelines. Other CI systems are listed as a missing item instead.
- **Clean tree required.** `--apply` refuses to run with uncommitted changes, so the adoption lands as one reviewable diff. Use `--allow-dirty` to override.
- **No dependencies are added.** `package.json` is not touched; the tools run with `node tools/...`.
- **Your docs index is kept.** If `docs/README.md` already exists, the doc map goes to `docs/DOCMAP.md` instead and `paths.docMap` points there.
- **One adoption per repository.** If `sdd.config.json` already exists, adopt stops and points to `sdd upgrade`.

## Steps

1. **Preview:**

   ```bash
   node <path-to-framework>/tools/sdd/cli.mjs adopt ../legacy-app
   ```

   The dry run prints the languages, components and tests it found, every file it would create, every proposal, and how many items need human input.

2. **Inspect the analysis as JSON** if you want to script around it:

   ```bash
   node <path-to-framework>/tools/sdd/cli.mjs adopt ../legacy-app --json
   ```

3. **Apply:**

   ```bash
   node <path-to-framework>/tools/sdd/cli.mjs adopt ../legacy-app --apply
   ```

4. **Review the diff** with `git status` and `git diff`, then commit it on a branch.

## What it writes

| File | Content |
| --- | --- |
| `docs/adoption/inventory-v1.md` | What was found: languages, frameworks, test frameworks, integrations, components, API specs, schemas, CI, docs, existing agent files |
| `docs/adoption/missing-information-v1.md` | The twelve seed questions and the framework prerequisites, each marked missing or partly inferred, with where the answer goes |
| `docs/prd/PRD-v1.md`, `docs/prd/components/PRD-<component>-v1.md` | Draft PRDs with inferred content tagged `[inferred]` and open questions |
| `docs/spec/SPEC-v1.md`, `docs/lld/LLD-<component>-v1.md` | Draft designs describing the system as it is today |
| `docs/test/test-plan-v1.md`, `docs/trace/index.yaml`, `docs/trace/coverage.md` | Existing tests, components marked `MAPPED`, and an empty coverage report that `trace-check --write` fills |
| `docs/adr/0001-adopt-spec-driven-development.md` | A proposed decision on how to adopt |
| `sdd.config.json` | Detected code roots, test roots, components and prefixes, `adoption.mode: advisory` |
| Machinery | Skills, personas, commands, hooks, tools, templates, standards, guides |
| `.sdd-proposed/` | The framework's version of any file that already existed, for you to merge |

## What adopt asks for

`docs/adoption/missing-information-v1.md` is the checklist of what people must supply before the framework can run fully. Typical items:

- answers to seed questions that code cannot reveal: outcomes and targets, non-goals, invariants, NFR targets, data classification, rollout tolerance;
- the approvers for the intake checkpoint and each gate, the exception authority and the fast path criteria;
- the organizational scope the repository serves (the L1 domain, L2 capability and L3 Business Application in `docs/scope/scope-map.yaml`);
- who owns `docs/` for review in `CODEOWNERS` (adopt never adds or edits one, because it can change how existing pull requests are reviewed);
- confirmation of component names and ID prefixes;
- the real test, typecheck and build commands for `AGENTS.md`;
- where CI should run the checks;
- how to merge existing agent instructions with the new `AGENTS.md`;
- which lint, format or type check configs (tsconfig, ESLint, Prettier, Biome) should exclude `tools/` and `.sdd-proposed/`.

In Claude Code, `/sdd-adopt` walks through the list with the owner and fills in the answers.

## Lint, format and type check configs

The framework's tools are plain JavaScript modules under `tools/`. Each one starts with `// @ts-nocheck`, so a TypeScript project that checks JavaScript does not type check them. Linters and formatters that scan the whole repository may still pick them up. adopt detects tsconfig, ESLint, Prettier and Biome configs and lists the exclusions to add (`tools/` and `.sdd-proposed/`) in the missing-information file. It never edits those configs.

## From advisory to enforced

Start in advisory mode. As each component gets acceptance criteria and annotated tests, the `verifier` audits it and its status in `docs/trace/index.yaml` moves from `MAPPED` to `AUDITED`. When the owner is ready:

1. set `adoption.mode` to `enforced` in `sdd.config.json`;
2. remove `--advisory` and `continue-on-error` from `.github/workflows/sdd.yml`;
3. make the workflow a required check in branch protection.

Criteria in draft PRDs are never enforced, so components can be adopted one at a time.
