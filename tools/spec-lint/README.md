# spec-lint

Checks that the spec documents are well formed. Node 20 or later, no dependencies.

```bash
node tools/spec-lint/spec-lint.mjs            # exit 1 on errors
node tools/spec-lint/spec-lint.mjs --advisory # report, never fail (used after sdd adopt)
node tools/spec-lint/spec-lint.mjs --json     # machine-readable output
```

## What it checks

| Check | Error or warning |
| --- | --- |
| Every versioned document (`<name>-vN.md`) has front matter with `title`, `type`, `version`, `status`, `owner` | Error |
| `version` in the front matter matches `vN` in the file name | Error |
| `status` is `draft`, `in-review`, `approved` or `superseded` (ADRs: `proposed`, `accepted`, `rejected`, `superseded`, `deprecated`) | Error |
| Approved documents have no open questions (`- [ ] Q:`) and no placeholders (`[PREFIX]`, `[Name]`, `[Link`, `TBD`) | Error |
| ADR numbers are unique | Error |
| ADRs carry front matter | Warning (older ADRs may use another format) |
| No requirement ID is defined twice in the latest PRDs | Error |
| Component PRDs declare `prefix`, and their IDs use it | Error |
| Acceptance criteria are in EARS (`... shall ...`) or Given/When/Then when the PRD says `notation: gherkin`, and carry a priority P1, P2 or P3 | Error in approved PRDs, warning in drafts |
| A criterion states one response | Warning |
| A component requirement's `Parent` exists in the parent PRD | Warning |
| Every skill, agent and command has `metadata.version` (semver); skills and agents have a `## Changelog` entry for it | Error |
| Every section of every template has a `> **Owner:** H/C/A` line | Warning |

## Where the rules live

The ID patterns, front matter parsing and table parsing are in [`tools/lib/sdd-lib.mjs`](../lib/sdd-lib.mjs), shared with trace-check and the hooks. The rules themselves are defined in [docs/standards/spec-driven-development-v1.md](../../docs/standards/spec-driven-development-v1.md).
