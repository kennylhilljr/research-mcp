---
title: "{{TITLE}}"
type: lld
version: {{VERSION}}
status: draft
owner: "[Name]"
prefix: {{PREFIX}}
component: {{COMPONENT}}
parent: docs/spec/SPEC-v1.md
artifact_type: low-level-design
scope_level: L3
scope_name: "[scope key from docs/scope/scope-map.yaml]"
date: {{DATE}}
---

# LLD: {{TITLE}} (v{{VERSION}})

## How to use this template

*One LLD per component. Agents prepare most of it from the approved SPEC. Decisions that are costly to reverse are C: public contracts, persisted schema, authorization enforcement and the test strategy are drafted as options and approved by the owners at Gate 3. Link back to the SPEC section and the requirement IDs this component satisfies. Rationale inferred from existing code is tagged `[inferred]` until the owner confirms it.*

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

| Requirement | Criteria | SPEC section |
| --- | --- | --- |
| [PREFIX]-FR-1 | [PREFIX]-1 | SPEC 4 |

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

*Link the machine-readable contract in `docs/contracts/`.*

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

| Flag | Default | Safe to switch off? |
| --- | --- | --- |
| | off | |

## 8. Observability

> **Owner:** A · **Persona:** `sre`

*Metrics, logs and alerts. Thresholds trace to NFR IDs.*

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

*Planned evidence: map every criterion of the component to the tests that will verify it. A criterion named here is `planned` until a test cites it. The evidence report itself is generated in `docs/trace/coverage.md` by trace-check.*

| Criterion | Planned tests | Level |
| --- | --- | --- |
| [PREFIX]-1 | | Unit |

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| | | |

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

- [ ] Q:

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
