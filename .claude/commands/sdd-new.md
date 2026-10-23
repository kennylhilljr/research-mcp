---
description: "Start a new spec: interview the owner with the seed questions, then draft the PRDs."
argument-hint: "<one-line idea or problem>"
metadata:
  version: 1.1.0
---

Start a new spec-driven piece of work for this idea: $ARGUMENTS

1. Run the `sdd-intake` skill with the idea above. Ask the owner the twelve seed questions and write the answers into Section 1 of the parent PRD.
2. Stop and ask the owner to approve the problem framing (the intake checkpoint). Do not continue until they say so.
3. Run the `sdd-spec` skill to draft user stories, requirements and EARS acceptance criteria in the component PRDs.
4. Run `node tools/sdd/cli.mjs check` and report the result.
5. Tell the owner the next step is `sdd-clarify`, then Gate 1. Never set `status: approved` yourself.

## Changelog

| Version | Date | Change |
| --- | --- | --- |
| 1.1.0 | 2026-10-22 | Intake checkpoint replaces Gate 0 |
| 1.0.0 | 2026-10-22 | First release |
