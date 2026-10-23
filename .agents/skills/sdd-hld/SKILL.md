---
name: sdd-hld
description: "Draft the system high-level design (the SPEC) and ADR options with tradeoffs from approved PRDs. Use after Gate 1, when the requirements are approved and the system shape needs designing or changing."
metadata:
  version: 1.1.0
---

# sdd-hld

## Purpose

Design the shape of the solution. The architect drafts options for every decision with real tradeoffs; the owner chooses. Then the SPEC records the component breakdown, data flow, capacity, risks, trust boundaries, integrations, rollout strategy and the traceability from PRD requirements to SPEC sections.

## When to use

- At least one PRD is approved (Gate 1). The gate hook blocks this skill otherwise.
- A change crosses components or changes the system's shape (the cascade rule sends it here).

## Inputs

1. `AGENTS.md` (approved stack and architecture principles).
2. `docs/README.md`.
3. The approved parent PRD and component PRDs.
4. Existing ADRs in `docs/adr/` and the current SPEC, if any.
5. `docs/templates/SPEC-template.md` and `docs/templates/ADR-template.md`.
6. Research in `docs/research/`.

## Steps

1. Create the SPEC: `node tools/sdd/cli.mjs new spec` (or `new --next docs/spec/SPEC-vN.md` if the current one is approved).
2. Dispatch the `architect` persona with the approved PRD IDs in scope. It lists the open decisions (from PRD Section 1.9 and from the design itself) and, for each, drafts 2 or 3 options with consequences.
3. For each decision with a real tradeoff, create an ADR: `node tools/sdd/cli.mjs new adr --name <slug>` with status `proposed`. Present the options to the owner and record the choice. A choice that one option clearly dominates needs only a line in the SPEC, not an ADR.
4. Dispatch the `security-reviewer` persona to draft trust boundaries and the threat model (C sections; the owner decides).
5. Dispatch the `sre` persona to draft the rollout and migration strategy from the owner's risk tolerance (PRD 2.9).
6. The architect then writes the A sections: component breakdown, data flow and sequence diagrams (Mermaid), capacity estimates from NFR targets, risks and mitigations, and the PRD-to-SPEC traceability table (every FR and criterion ID mapped to a SPEC section).
7. Dispatch the `test-architect` persona to draft the testing strategy section (C: the owner approves it at Gate 2).
8. Cut anything that restates the PRD in different words.
9. Run `node tools/sdd/cli.mjs check` and `node tools/sdd/cli.mjs docmap`. Approved criteria without tests are not errors yet: tests are required once a milestone plan exists for the component.

## Outputs

- `docs/spec/SPEC-vN.md`, status `draft`.
- `docs/adr/NNNN-<slug>.md`, status `proposed` until the owner decides.
- Diagrams as Mermaid in the SPEC, optionally rendered under `docs/assets/diagrams/`.

## Stop and gate

Stop for **Gate 2**. The owner chooses among ADR options (ADR status `accepted` or `rejected`), ranks the risks, and sets `status: approved` on the SPEC. Agents never set either.

## Rules

- Never write H content: architecture principles and the approved stack live in `AGENTS.md`.
- Present choices as options with consequences, not as the agent's best guess.
- A decision lives in the lowest artifact (SPEC, ADR or LLD) that covers everything it affects.
- An ADR is never edited after acceptance; a new ADR supersedes it.
- Ambiguity in a PRD goes back to the owner as `- [ ] Q:`; do not design around it silently.

## Changelog

| Version | Date | Change |
| --- | --- | --- |
| 1.1.0 | 2026-10-22 | Testing strategy drafted as C; check no longer blocks design on missing tests; AGENTS.md is called repository instructions; decisions live in the lowest artifact that covers them |
| 1.0.0 | 2026-10-22 | First release |
