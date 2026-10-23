# Scaffold

Starting files that `sdd init` and `sdd adopt` install into a target repository. `machinery.mjs` maps each file to its installed path (for example `docs-README.md` becomes `docs/README.md`), and `{{PROJECT}}`, `{{OWNER}}`, `{{DATE}}` and `{{FRAMEWORK_VERSION}}` are filled in on install.

**Links resolve where a file is installed, not where it sits here.** `AGENTS.md` links to `docs/README.md` because it is installed at the repository root. Link checkers should skip this folder; `test/tools/setup.test.ts` checks every link in a freshly installed repository instead.
