---
name: sdd-lld
description: "Write one low-level design per component from the approved SPEC: contracts, schema, algorithms, errors, configuration, observability and the test plan. Use after Gate 2, when a component is ready for detailed design."
argument-hint: "<component name>"
metadata:
  version: 1.1.0
---

# sdd-lld

## Purpose

Produce the build detail for one component. Agents prepare most of the LLD from the approved SPEC. Decisions that are expensive to reverse are drafted as options for people to decide (C): public contracts, persisted schema, authorization enforcement and the test strategy.

## When to use

- The SPEC is approved (Gate 2) and the component's PRD is approved (Gate 1). The gate hook blocks this skill otherwise; name the component, for example `/sdd-lld tech`.
- A component's design must change within the component (changes that cross components go back to `sdd-hld`).

## Inputs

1. `AGENTS.md`.
2. `docs/README.md`.
3. The approved SPEC and accepted ADRs.
4. The component's approved PRD in `docs/prd/components/`.
5. `docs/templates/LLD-template.md` and `docs/templates/test-plan-template.md`.
6. Existing contracts in `docs/contracts/` and existing code for the component.

## Steps

1. Create the LLD: `node tools/sdd/cli.mjs new lld --component <name>` (or `new --next` if the current one is approved).
2. Dispatch the `component-designer` persona with the component's criterion IDs and SPEC sections in scope. It writes: API contracts (OpenAPI, JSON Schema or tool schemas in `docs/contracts/`), data model, schema and migrations, module structure and interfaces, algorithms, error handling with retries and idempotency, configuration and feature flags, and a Decisions and alternatives table.
3. After the draft, the component designer runs an edge-case probe on its own gaps: missing state transitions, unstated invariants, unspecified error shapes, ordering assumptions. Gaps go to the owner as `- [ ] Q:` or into the LLD.
4. Dispatch the `security-reviewer` persona for the authentication and authorization enforcement section. It is always human-reviewed.
5. Dispatch the `sre` persona for observability: metrics, logs and alerts with thresholds traced to NFR IDs.
6. Dispatch the `test-architect` persona to draft the test strategy for the owner to approve: map every criterion of the component to planned tests in the LLD's test strategy section and the test plan's planned evidence table (each mapped criterion becomes `planned`), list deferred P2 or P3 criteria in the test plan front matter `deferred:` only with the owner's approval, then run `node tools/trace-check/trace-check.mjs --write` to regenerate `docs/trace/coverage.md`.
7. Run `node tools/sdd/cli.mjs check` and `node tools/sdd/cli.mjs docmap`. Before build, a criterion without planned evidence is a warning; resolve each one.

## Outputs

- `docs/lld/LLD-<component>-vN.md`, status `draft`.
- New or changed files in `docs/contracts/`.
- An updated draft `docs/test/test-plan-vN.md` (a new version if the current one is approved) and a regenerated `docs/trace/coverage.md`.

## Stop and gate

Stop for **Gate 3**. The Business Application, component and control owners review public or cross-team contracts, persisted schema, authorization enforcement and the test strategy, then set `status: approved` and record `approved_by` and `approved` on the LLD. Agents never set it. The rest of the LLD is reviewed through the code.

## Rules

- Each LLD links back to its SPEC sections and the criterion IDs it satisfies.
- Rationale inferred from existing code is tagged `[inferred]` until the owner confirms it.
- Every optional behavior gets a feature flag that is safe to switch off.
- Anything the LLD cannot settle without the owner becomes `- [ ] Q:`.

## Changelog

| Version | Date | Change |
| --- | --- | --- |
| 1.1.0 | 2026-10-22 | Gate bound to the named component; contracts, schema, authorization and test strategy drafted as C; planned evidence |
| 1.0.0 | 2026-10-22 | First release |
