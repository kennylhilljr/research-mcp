---
name: sdd-intake
description: "Interview the owner with the twelve seed questions and turn the answers into Section 1 of the parent PRD. Use when starting a new product, feature or initiative, or when someone asks for a new spec, a new PRD or to capture requirements."
argument-hint: "<one-line idea or problem>"
metadata:
  version: 1.1.0
---

# sdd-intake

## Purpose

Capture what only people can supply: the problem, the outcomes, the scope and what must never happen. Every human-owned (H) section of the PRD maps to one of twelve seed questions. This skill asks them, records the answers in the owner's words, and stops for the owner to approve the problem framing (the intake checkpoint) before any requirements are written.

## When to use

- A new product, feature or initiative starts.
- `/sdd-new <idea>` was run (it calls this skill first).
- An existing PRD has Section 1 gaps marked `- [ ] Q:`.

Do not use it for bugs or small changes; those take the short path through `sdd-spec` or `sdd-triage`.

## Inputs

1. `AGENTS.md` (repository instructions: standing rules, approved stack, owners).
2. `docs/README.md` (doc map) to see whether a parent PRD already exists.
3. `docs/standards/spec-driven-development-v2.md` (artifact chain, scope, decision owners, ID scheme).
4. `docs/scope/scope-map.yaml`: the organizational scope (L0 to L3) the work serves. Ask the owner which scope it is if the map does not say.
5. `docs/templates/PRD-template.md`.
6. The idea passed as the argument, if any.

## Steps

1. Read the inputs. If a parent PRD exists, work on its next draft version instead of a new one (`node tools/sdd/cli.mjs new --next docs/prd/PRD-vN.md` only if the current one is approved; otherwise edit the draft).
2. Dispatch the `analyst` persona with the Agent tool to prepare the interview: prior art in `docs/research/`, existing systems, and any answers already settled in `AGENTS.md`. The analyst never writes H content; it only prepares questions and context.
3. Ask the owner the twelve seed questions, one or two at a time, skipping any `AGENTS.md` already answers (usually 9 and 10):
   1. What problem are we solving, for whom, and why now?
   2. What does success look like in numbers, and by when?
   3. What are the top three things users must be able to do, in priority order?
   4. What is explicitly out of scope?
   5. What must never happen?
   6. What are the latency, availability, scale and residency targets?
   7. What data does it touch, and how is it classified?
   8. What systems must it integrate with or replace, and who owns them?
   9. What is already fixed (stack, vendors, platforms, budget)?
   10. Which decisions are already made, and which are open?
   11. What is the rollout risk tolerance, and who responds when it fails?
   12. How will we know it is done?
4. Ask follow-ups only when an answer is missing or two answers conflict. Never fill a gap with a guess.
5. Create the parent PRD if none exists: `node tools/sdd/cli.mjs new prd --title "<product name>"`.
6. Write the answers into Section 1 in the owner's words: problem and why now, users, scope and non-goals, outcomes (`OUT-n` with baseline, target, date), value, leaps of faith, invariants (`INV-n`), constraints, decisions made and open. Record answers to questions 6, 7, 8, 11 and 12 in the Section 2 places they feed, marked as owner input.
7. Every unanswered item becomes an open question in place: `- [ ] Q: <question>`.
8. Run `node tools/sdd/cli.mjs docmap` and `node tools/sdd/cli.mjs check`.

## Outputs

- `docs/prd/PRD-vN.md` (status `draft`) with Section 1 filled from the owner's answers.
- Open questions listed as `- [ ] Q:` where answers are missing.
- An updated doc map in `docs/README.md`.

## Stop and gate

Stop after Section 1. The owner approves the problem framing at the intake checkpoint before `sdd-spec` writes requirements. Present a short summary: the problem, the outcomes, the invariants and the open questions. Agents never set `status: approved`; the owner does.

## Rules

- H sections are the owner's words. You may ask, reformat and tidy; you never invent content.
- Numbers and dates come from people. If the owner gives no target, leave the question open.
- Assign IDs once and never renumber: `OUT-1`, `INV-1`, `FR-1`, `NFR-1` in the parent PRD.
- An answer that admits two readings goes back to the owner as `- [ ] Q:`.
- Project knowledge goes into the PRD, not into agent memory.

## Changelog

| Version | Date | Change |
| --- | --- | --- |
| 1.1.0 | 2026-10-22 | Intake checkpoint replaces Gate 0; reads the v2 standard and the scope map; records the scope; AGENTS.md is called repository instructions |
| 1.0.0 | 2026-10-22 | First release |
