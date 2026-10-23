# Starting a new repository

`sdd init` sets up the framework in an empty folder. It copies the machinery (skills, personas, commands, hooks, tools, templates, standards and guides) and creates a clean skeleton. It never copies this repository's worked example.

## Create the repository

From anywhere, point the CLI of a clone of this framework at a new folder:

```bash
node <path-to-framework>/tools/sdd/cli.mjs init ../my-service --components tech:TECH,billing:BILL --git
```

| Option | Meaning |
| --- | --- |
| `--name <name>` | Project name (defaults to the folder name) |
| `--components name:PREFIX,...` | Components and their ID prefixes, written to `sdd.config.json` |
| `--owner <name>` | Owner named in `AGENTS.md` |
| `--git` | Run `git init` if the folder is not a repository yet |
| `--dry-run` | Print what would be created, write nothing |
| `--force` | Add the framework to a folder that already has files (existing files are never overwritten; the framework's version of a file that exists goes to `.sdd-proposed/`; use `adopt` for running applications) |

## What it creates

```text
my-service/
├── AGENTS.md                 # Repository instructions to fill in (H)
├── CLAUDE.md                 # One line: @AGENTS.md
├── sdd.config.json           # Paths, components, feature flags
├── package.json              # Only if none exists: sdd scripts, no dependencies
├── .claude/                  # Skills, personas, commands, hook settings
├── .github/workflows/ci.yml  # Tests, spec-lint, trace-check
├── .github/CODEOWNERS        # Who reviews docs/, all lines commented out until you fill it in
├── docs/
│   ├── README.md             # Doc map: scope map, artifact index, approval workflow
│   ├── scope/scope-map.yaml  # L0 to L3 organizational scopes, placeholders to fill in
│   ├── adr/README.md         # ADR index and statuses
│   ├── glossary.md
│   ├── templates/  standards/  guide/
│   ├── test/test-plan-v1.md  # Test strategy, planned evidence, deferrals and exceptions
│   ├── trace/index.yaml      # Audit state, empty
│   ├── trace/coverage.md     # Generated evidence report, empty
│   └── vision/ research/ prd/components/ adr/ spec/ lld/ contracts/ build/ runbooks/ postmortems/
├── tools/                    # spec-lint, trace-check, hooks, sdd CLI
├── src/
└── test/
```

## First session

1. **Fill in `AGENTS.md`.** Replace the commands with your project's real ones and add organization rules.
2. **Fill in the scope map and the reviewers.** Name your L0 to L3 scopes in `docs/scope/scope-map.yaml`, set `project.scope` in `sdd.config.json`, and fill in `.github/CODEOWNERS` with the people who approve each gate.
3. **Check the environment:** `node tools/sdd/cli.mjs doctor`.
4. **Open Claude Code** in the folder and run `/sdd-new <one line about what you want to build>`. The `sdd-intake` skill interviews you with the twelve seed questions and writes Section 1 of the parent PRD. You approve that problem framing (the intake checkpoint); `sdd-spec` then drafts the requirements as options for you to select.
5. **Answer open questions.** Run `/sdd-clarify`. Every `- [ ] Q:` in the PRD needs an answer before Gate 1.
6. **Approve the PRD.** Read it, fill in the approvals table and set `status: approved`, `approved_by` and `approved` in its front matter. That passes Gate 1 and unlocks `/sdd-hld`.
7. Continue with `/sdd-hld` (Gate 2), `/sdd-lld <component>` (Gate 3), `/sdd-tasks <component>`, `/sdd-implement <milestone>` and `/sdd-verify`. See [usage](usage.md).

## Adding a component later

```bash
node tools/sdd/cli.mjs new prd-component --component payments --prefix PAY
```

Then add the component to `sdd.config.json` under `components` with its paths.
