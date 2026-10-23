# Versioning

Three things carry versions: the framework, each skill, persona and command, and each document.

## The framework

The framework version (now 1.0.0) is recorded in:

- `sdd.config.json` (`frameworkVersion`), so every repository shows which release it was set up with;
- `tools/lib/sdd-lib.mjs` (`FRAMEWORK_VERSION`);
- `package.json`, `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`;
- `CHANGELOG.md` in the framework repository.

A release bumps all of them together and adds a changelog entry. The framework follows semantic versioning: a major release changes a rule in a standard or a document format; a minor release adds a skill, persona, check or command; a patch fixes wording or a bug.

## Skills, personas and commands

Each file carries its version in front matter under `metadata`, which keeps it valid for Claude Code, claude.ai uploads and the Skills API:

```yaml
---
name: sdd-spec
description: Turn the intake brief into the parent and component PRDs.
metadata:
  version: 1.1.0
---
```

Skills and personas end with a changelog table whose first row is the current version:

```markdown
## Changelog

| Version | Date | Change |
| --- | --- | --- |
| 1.1.0 | 2026-11-02 | Adds the divergence probe hand-off |
| 1.0.0 | 2026-10-22 | First release |
```

| Change | Bump |
| --- | --- |
| Changes what the skill or persona owns, its boundaries, inputs or outputs | major |
| Adds a step, a check or a capability | minor |
| Fixes wording | patch |

After a change:

1. bump `metadata.version` and add the changelog row;
2. run `node tools/sdd/cli.mjs catalog` to update [the catalog](catalog.md);
3. run `node tools/spec-lint/spec-lint.mjs`, which fails on a missing or invalid version or a missing changelog row.

CI fails when the catalog is out of date.

## Documents

Documents are versioned by file name (`PRD-tech-v2.md`). An approved version is frozen; `node tools/sdd/cli.mjs new --next <path>` creates the next one. ADRs are numbered once and superseded, never versioned. See the [standard](../standards/spec-driven-development-v2.md).

## Upgrading a repository to a new framework release

Run `upgrade` from the new framework release against the repository. adopt refuses a repository that already has `sdd.config.json`.

```bash
node <path-to-new-framework>/tools/sdd/cli.mjs upgrade .                      # dry run: lists what would change
node <path-to-new-framework>/tools/sdd/cli.mjs upgrade . --apply              # create missing files; propose the rest
node <path-to-new-framework>/tools/sdd/cli.mjs upgrade . --apply --overwrite  # replace framework files in place
```

`upgrade` only touches framework-owned files: skills, personas, commands, tools, templates, standards, guides and the framework diagrams. It never touches your documents, `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json` or `sdd.config.json`.

- With `--apply`, missing framework files are created, and every framework file that differs from the new release is written to `.sdd-proposed/<same path>` for you to review and merge. Use this when you have customized skills or personas.
- With `--apply --overwrite`, differing framework files are replaced in place. Use this when you have not customized them.
- `--apply` refuses to run with uncommitted changes; `--allow-dirty` overrides that.

Afterwards, set `frameworkVersion` in `sdd.config.json` to the new release, delete `.sdd-proposed/`, then run `node tools/sdd/cli.mjs catalog` and `node tools/sdd/cli.mjs check`. The release notes are in the framework repository's `CHANGELOG.md`.

### From 1.0.0 to 1.1.0

`upgrade` brings the new tools, skills, personas, templates, standard v2, guides and diagrams. These steps are yours, because `upgrade` never touches project files:

1. Copy `tools/sdd/scaffold/scope-map.yaml` to `docs/scope/scope-map.yaml` and name your L0 to L3 scopes. Add `paths.scopeMap`, `project.scope` and, if you want them, `approvals.requireApprover`, `ids.criterionPattern` and `paths.testResults` to `sdd.config.json` (the defaults work without them).
2. Compare your `AGENTS.md` with `tools/sdd/scaffold/AGENTS.md` and merge what you want: the intake checkpoint replaces Gate 0, the three separate concepts, the new decision owner definitions and the drift rule. The same goes for `docs/README.md` against `scaffold/docs-README.md`.
3. Add `excepted: []` to the test plan's front matter and a planned evidence table, in the next version of the test plan. Add `components:` to new milestone plans.
4. Optionally copy `scaffold/adr-README.md` to `docs/adr/README.md` and `scaffold/CODEOWNERS` to `.github/CODEOWNERS`, then fill it in.
5. Run `node tools/trace-check/trace-check.mjs --write`. It renames `covered` to `test linked` in the evidence report and moves the trace index counts to the new fields.
6. Review gated skill calls: with more than one component, `/sdd-lld`, `/sdd-tasks` and `/sdd-implement` now need the component or milestone named.

Behavior changes to expect: an approved criterion without a test is an error only once a milestone plan exists for its component (before that, a warning when nothing is planned), and the gate hook checks the specific component instead of any approved document of the right type.
