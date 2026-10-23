---
name: sdd-tasks
description: "Break an approved LLD into a milestone plan of small, dependency-ordered tasks, each traced to criterion IDs. Use after Gate 3, or to plan a fix on the short path."
argument-hint: "<component> <milestone, for example tech M2>"
metadata:
  version: 1.1.0
---

# sdd-tasks

## Purpose

Turn approved designs into work an implementer can finish in one session per task. Order work by priority, then by dependency, so the first slice is the MVP and each slice ends at a checkpoint where it works and is testable on its own.

## When to use

- The component's LLD is approved (Gate 3). The gate hook blocks this skill otherwise; name the component, for example `/sdd-tasks tech M2`.
- A bug or small change on the short path needs a task list.
- The queue changes (a new S0 or S1 item, a re-ranked story).

## Inputs

1. `AGENTS.md`.
2. `docs/README.md`.
3. The approved LLDs and their component PRDs (story priorities).
4. `docs/test/test-plan-vN.md` (planned tests, deferred criteria).
5. `docs/templates/kickoff-template.md` and `docs/templates/plan-template.md`.
6. `docs/trace/index.yaml` and open support items for the queue.

## Steps

1. Create the milestone kickoff and plan: `node tools/sdd/cli.mjs new kickoff --milestone M<n>` and `node tools/sdd/cli.mjs new plan --milestone M<n>`. Set `components:` in the plan's front matter to the components it builds; the gate hook checks each one.
2. Dispatch the `planner` persona with the LLD paths and criterion IDs in scope. It:
   - orders slices by story priority (P1 first, the MVP), then by dependency; foundational work that blocks a P1 story is itself P1;
   - splits each slice into tasks small enough for one session, each with the criterion IDs it satisfies, the files it touches and its done check;
   - marks tasks that can run in parallel;
   - places support work in the queue; this reference profile uses the combined ordering S0 > S1 > P1 > S2 = P2 > S3 = P3 > S4 (a local choice, Section 15 of the standard);
   - ends each slice with a checkpoint where the slice is working and testable.
3. Check that every criterion that is not deferred appears in at least one task, and every task cites at least one ID.
4. Flag any task that crosses components; it needs the owner before it starts.
5. Run `node tools/sdd/cli.mjs check` and `node tools/sdd/cli.mjs docmap`.

## Outputs

- `docs/build/M<n>-kickoff-v1.md` and `docs/build/M<n>-plan-v1.md`.

## Stop and gate

The owner skims the plan at Gate 3 or right after it and confirms the MVP slice. No separate approval is needed unless the plan changes scope. Agents never set `status: approved` on design documents.

## Rules

- Never re-rank stories: priority belongs to the owner. Re-ranking is a PRD change.
- Never invent a task without a criterion ID; untraced work is how drift starts.
- A task that needs a design change goes back to `sdd-lld` (within a component) or `sdd-hld` (across components).
- Ambiguity goes to the owner as `- [ ] Q:` in the plan.

## Changelog

| Version | Date | Change |
| --- | --- | --- |
| 1.1.0 | 2026-10-22 | Gate bound to the named component; plans record components; the combined queue is a local choice |
| 1.0.0 | 2026-10-22 | First release |
