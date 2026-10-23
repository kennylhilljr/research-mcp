# {{PROJECT}}: instructions for people and coding agents

This file is the repository instruction adapter. Every person and every agent (Claude Code, Codex or any tool that reads `AGENTS.md`) reads it first. It points to the controlled standard, the scope map and the artifact index; it is not organizational authority by itself. It is human-owned: agents may propose changes but never edit it without the owner's approval.

Framework: spec-driven development (SDD) {{FRAMEWORK_VERSION}}. Owner: {{OWNER}}.

## Read first

- [docs/README.md](docs/README.md) is the doc map: the organizational scope map, the delivery artifact index and the approval workflow. The latest approved documents are the source of truth. If code and docs disagree, raise it; do not silently diverge.
- [docs/standards/spec-driven-development-v2.md](docs/standards/spec-driven-development-v2.md) defines organizational scope, the delivery artifact chain, decision owners, gates, IDs and evidence. Once its owner approves it, it applies to this repository only; the organization's controlled standard is an open decision recorded there.
- [docs/standards/agent-personas-v1.md](docs/standards/agent-personas-v1.md) defines the agent personas and their limits.
- [docs/scope/scope-map.yaml](docs/scope/scope-map.yaml) names the L0 to L3 organizational scopes this repository serves.

## Three separate concepts

- **Organizational scope** is L0 to L3 (L0 strategy and imperatives, L1 domain, L2 capability, L3 Business Application). It is recorded in the scope map and in `scope_level` and `scope_name`.
- **The delivery artifact chain** is unnumbered: Product specification, high level design, low level design, plans, code, tests, handoff and evidence.
- **Gates 1 to 3** are approval checkpoints. They do not correspond to scope levels L1 to L3.

## Decision owners

Every section of every template is tagged:

- **H** Human decision: a person supplies and approves it. Interview, organize and edit; never invent. Ask, or list it as an open question (`- [ ] Q: ...`).
- **C** Human decision with agent draft: draft options, expose assumptions, sources and tradeoffs; a person selects and approves.
- **A** Agent prepared from approved inputs: prepare it as the persona named in the template; never change approved intent; it must pass the checks.

Product owns the problem, outcomes, scope, priorities, constraints and acceptance. Engineering gives feasibility and risk input, then owns architecture and implementation. A choice found during implementation that changes approved behavior goes back to Product.

## Rules

- **Approved versions are frozen.** Never edit a document whose status is `approved`; create the next version with `node tools/sdd/cli.mjs new --next <path>`. ADRs are superseded by a new ADR.
- **Approvals are human.** The intake checkpoint approves the problem framing (PRD Section 1); Gate 1 the Product specification; Gate 2 the SPEC (HLD); Gate 3 the LLD for one component. Agents never set `status: approved`, `approved_by` or `approved`. Name the component when you run a gated skill (`/sdd-lld tech`).
- **Every requirement has a stable ID**, never renumbered and never reused. Acceptance criteria use `<PREFIX>-<n>` (for example `TECH-2`) unless `ids.criterionPattern` allows a richer form. A change of actor, trigger, response, target or test obligation gets a new ID; the old one goes in the PRD's ID history table.
- **Tests and code cite the criteria they satisfy** with a comment such as `// @spec TECH-2`: on the test that exercises the behavior and on the entry point of the behavior in code, not on every helper. A link is structural evidence; it does not prove meaning.
- **Drift is decided by a person.** Verification reports a disagreement. The named owner determines the first artifact in the delivery trace that no longer reflects approved intent; correct that artifact, then update or regenerate what depends on it.
- **A change that crosses components stops for a person** and goes into the next SPEC version, with an ADR when the system's shape changes.
- **Never verify your own work.** The `verifier` persona checks work it did not produce.
- **Project knowledge goes into the docs**, not into an agent's private memory.
- **Rationale inferred from existing code** is tagged `[inferred]` until the owner confirms it.
- **Writing style for docs:** short sentences, plain words, no em dashes.

<!-- Add organization rules here: security, data handling, approved stack, vendors. -->

## Commands

```bash
npm test                              # tests                      (replace with this project's command)
npm run typecheck                     # type check or lint         (replace with this project's command)
node tools/sdd/cli.mjs check          # spec-lint and trace-check
node tools/sdd/cli.mjs doctor         # check the local environment
node tools/sdd/cli.mjs new --help     # create a document from a template
```

## Workflow

| Step | Skill (Claude Code) | Persona | Human checkpoint |
| --- | --- | --- | --- |
| Capture intent | `/sdd-intake` | `analyst` | Product answers the twelve seed questions; intake checkpoint: approve the problem framing |
| Write the PRD | `/sdd-spec` | `product-writer` | |
| Close gaps | `/sdd-clarify` | `product-writer`, `verifier` | Gate 1: approve the Product specification |
| High-level design | `/sdd-hld` | `architect`, `security-reviewer`, `sre` | Gate 2: choose ADRs, approve the SPEC |
| Low-level design | `/sdd-lld <component>` | `component-designer`, `test-architect` | Gate 3: approve contracts, schema, authorization, test strategy |
| Plan | `/sdd-tasks <component>` | `planner` | |
| Build | `/sdd-implement <milestone>` | `implementer` | Code review |
| Verify | `/sdd-verify` | `verifier` | The owner decides each disagreement |
| Adopt an existing codebase | `/sdd-adopt` | `analyst`, `architect` | |
| Triage support work | `/sdd-triage` | `sre`, `verifier`, `planner` | Owner confirms S0 and S1 |

Bugs and small changes take the short path: correct the first artifact that lost intent, then tasks, then code.

## Agents without skills, subagents or hooks (Codex and others)

Follow the same workflow by hand. For each step, read the matching `.claude/skills/<skill>/SKILL.md` and follow it; when it names a persona, read `.claude/agents/<persona>.md` and stay inside that persona's limits. The gate and approved-file hooks are Claude Code adapters: without them, check the approval yourself before each gated step, and never edit an approved document. Run `node tools/sdd/cli.mjs check` before you finish; CI and code review apply to every agent.

## Definition of done

A change is done when tests pass, `node tools/sdd/cli.mjs check` passes, every new or changed behavior cites its criterion with `@spec`, the docs and the doc map are current, and a handoff note records what was verified and the test results.
