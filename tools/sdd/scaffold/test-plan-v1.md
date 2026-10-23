---
title: "Test plan"
type: test-plan
artifact_type: test-strategy
version: 1
status: draft
owner: "[Name]"
deferred: []
excepted: []
---

# Test plan (v1)

> The approved test strategy: how each acceptance criterion will be verified, before the tests exist. Evidence is derived status, so it is not kept here: `node tools/trace-check/trace-check.mjs --write` regenerates [coverage](../trace/coverage.md) from the `@spec` annotations. Deferring a criterion (P2 and P3 only) or excepting one needs the owner's approval: list it in `deferred:` or `excepted:` in the front matter, with the reason below.

## Strategy

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves

Which test layers exist (unit, integration, end to end), the tools, and what each layer covers.

## Planned evidence

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves

| Criterion | Planned tests | Level |
| --- | --- | --- |

## Deferrals and exceptions

> **Owner:** H decides; `test-architect` records

| ID | Priority | Deferred or excepted | Reason | Approved by | Revisit by |
| --- | --- | --- | --- | --- | --- |
