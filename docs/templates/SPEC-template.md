---
title: "{{TITLE}}"
type: spec
version: {{VERSION}}
status: draft
owner: "[Name]"
parent: docs/prd/PRD-v1.md
artifact_type: high-level-design
scope_level: L3
scope_name: "[scope key from docs/scope/scope-map.yaml]"
date: {{DATE}}
---

# SPEC: system high-level design (v{{VERSION}})

## How to use this template

*The SPEC is the system HLD. It shows the shape of the solution: humans choose among options, agents draft. Number every section so LLDs and handoffs can cite `SPEC 4.2`. Approved at Gate 2. If a section restates the PRD in different words, cut it.*

## 1. Architecture principles and approved stack

> **Owner:** H · **Persona:** none · **Seed question:** 9

*Link `AGENTS.md` and the standard. List only what is specific to this system.*

## 2. System context and boundaries

> **Owner:** C · **Persona:** `architect`

*What is inside the system and what is outside. A context diagram helps.*

## 3. Key decisions

> **Owner:** C · **Persona:** `architect` drafts ADR options; the owner decides · **Seed question:** 10

| ADR | Decision | Status |
| --- | --- | --- |
| ADR NNNN | | proposed |

## 4. Component breakdown and responsibilities

> **Owner:** A · **Persona:** `architect`

| Component | Prefix | Responsibility | Requirements | LLD |
| --- | --- | --- | --- | --- |
| | | | | |

## 5. Data flow and sequences

> **Owner:** A · **Persona:** `architect`

*Sequence diagrams for the main flows (Mermaid sources in `docs/assets/diagrams/`).*

## 6. Data model

> **Owner:** A · **Persona:** `architect`

*Entities, ownership and classification (from the PRD's data table).*

## 7. Trust boundaries and authorization model

> **Owner:** C · **Persona:** `security-reviewer` drafts the threat model; the owner decides

## 8. Integrations and external dependencies

> **Owner:** C · **Persona:** `architect` · **Seed question:** 8

| System | Owner | Interface | SLA | Failure behavior |
| --- | --- | --- | --- | --- |
| | | | | |

## 9. Capacity and scaling

> **Owner:** A · **Persona:** `architect` · **Seed question:** 6

*Estimates derived from the NFR targets.*

## 10. Rollout and migration

> **Owner:** C · **Persona:** `sre` · **Seed question:** 11

*Phases, flags, kill-switch triggers and rollback, within the owner's risk tolerance.*

## 11. Testing strategy

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 2

*Test layers and tooling. The test plan says how each criterion is verified; per-criterion coverage is generated in `docs/trace/coverage.md`.*

## 12. Risks and mitigations

> **Owner:** A · **Persona:** `architect`; the owner ranks them at Gate 2

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| | | | |

## 13. Traceability

> **Owner:** A · **Persona:** `architect`

| Parent requirement | Component requirements | SPEC section |
| --- | --- | --- |
| FR-1 | | |

## 14. Open questions

> **Owner:** A · **Persona:** `architect`

- [ ] Q:

### Gate 2: Design approved

| Approver | Date | ADRs chosen | Notes |
| --- | --- | --- | --- |
| | | | |
