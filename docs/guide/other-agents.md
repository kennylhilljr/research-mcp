# Using the framework with Codex and other agents

The rules live in plain files that any agent can read. Claude Code gets the most help today: skills, personas and two hooks that enforce the gates and protect approved documents. Other agents follow the same controls procedurally, unless an equivalent adapter is installed for them.

## What every agent reads

| File | Role |
| --- | --- |
| `AGENTS.md` | The repository instruction adapter. Canonical for every agent; Claude Code reaches it through `CLAUDE.md` (`@AGENTS.md`). It points to the standard; it is not organizational authority by itself. |
| `.claude/skills/<skill>/SKILL.md` | Step-by-step instructions for each stage of the chain |
| `.claude/agents/<persona>.md` | Persona definitions: what each role owns, its inputs, limits and definition of done |
| `docs/standards/` | The rules for this repository |
| `docs/templates/` | The documents, with an owner and persona on every section |

## Working without skills or subagents

An agent that cannot load skills or spawn subagents follows the same chain by hand:

1. Read `AGENTS.md` and `docs/README.md`.
2. Pick the step from the workflow table in `AGENTS.md` and open its `SKILL.md`.
3. For each section the skill writes, read the persona named in the template's owner line and stay inside its limits.
4. Never write an H section; add a `- [ ] Q:` line instead.
5. Never approve a document or verify your own work.
6. Before each gated step, check the approval yourself: the component's PRD, the SPEC, the component's LLD or the plan, as the [standard](../standards/spec-driven-development-v3.md#8-the-intake-checkpoint-and-the-gates) describes. Never edit a document whose status is `approved`.
7. Run `node tools/sdd/cli.mjs check` before finishing.

| Control | Claude Code | Other agents |
| --- | --- | --- |
| Gates | Enforced by the gate hook | Procedural (step 6), unless an adapter is installed |
| Approved documents frozen | Enforced by the protect-approved hook | Procedural, unless an adapter is installed |
| spec-lint and trace-check | CI | CI |
| Code review and CODEOWNERS | Repository settings | Repository settings |

CI and code review apply to every agent: spec-lint fails on malformed or incomplete documents, and trace-check fails on broken links.

## Adding support for a new agent

When another agent gains skills or subagents:

1. Point its skill or agent discovery at `.claude/skills/` and `.claude/agents/` (or copy them to the folder it expects, keeping the same files).
2. Register equivalents of the two hooks if it supports hooks; both scripts read JSON on stdin and exit 2 to block.
3. Record the change in `CHANGELOG.md` and add a section to this guide.

Keep `AGENTS.md` canonical. Tool-specific files should only point to it.
