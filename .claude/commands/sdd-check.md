---
description: "Run spec-lint and trace-check, summarize the findings by type and propose fixes."
metadata:
  version: 1.1.0
---

Run the framework's checks and explain the results.

1. Run `node tools/sdd/cli.mjs check` from the repository root.
2. Group the output by type:
   - front matter and versioning errors (spec-lint);
   - criteria that are not in EARS form or have no priority (spec-lint);
   - reverse orphans: `@spec` annotations citing undefined IDs (trace-check);
   - criteria without tests in a component that has a milestone plan, failing tests, and hollow status (trace-check);
   - criteria with no planned evidence before build, and governing artifacts changed after the last audit (trace-check warnings);
   - warnings: staleness, reach, skills, agents or commands without a version or changelog.
3. For each group, propose a fix and ask the owner which artifact is the first one that no longer reflects approved intent (spec, design, test or code); the fix starts there. Do not edit approved documents; propose `node tools/sdd/cli.mjs new --next <path>` instead (for an accepted ADR, a new ADR that supersedes it).
4. If `docs/trace/coverage.md` is stale (hollow status), offer to run `node tools/trace-check/trace-check.mjs --write`.
5. Ask before changing anything.

## Changelog

| Version | Date | Change |
| --- | --- | --- |
| 1.1.0 | 2026-10-22 | Evidence states and the drift rule |
| 1.0.0 | 2026-10-22 | First release |
