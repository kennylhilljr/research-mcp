---
title: "{{TITLE}}"
type: prd
version: {{VERSION}}
status: draft
owner: "[Name]"
decision_makers: "[Name]"
artifact_type: product-specification
scope_level: L3
scope_name: "[scope key from docs/scope/scope-map.yaml]"
date: {{DATE}}
---

# {{TITLE}}: parent PRD (v{{VERSION}})

## How to use this template

*The parent PRD states the what and why for the whole product. It holds the outcomes, the functional requirement index, the NFRs and the invariants. Each component then gets a component PRD (`node tools/sdd/cli.mjs new prd-component --component <name> --prefix <PREFIX>`) with its stories and acceptance criteria. Section 1 is approved at the intake checkpoint (problem approved); the whole document at Gate 1. `scope_level` and `scope_name` record the organizational scope (L0 to L3) the product serves. Delete italic guidance before approval.*

*Parent IDs: outcomes `OUT-n`, functional requirements `FR-n`, NFRs `NFR-n`, invariants `INV-n`. They never change and are never reused.*

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

*The problem or opportunity in terms of user, customer or business need, with the data that proves it is real. One paragraph on why now. Link the vision instead of restating it.*

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| | | |

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- 

| Non-goal | Why it is excluded |
| --- | --- |
| | |

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |
| OUT-1 | | | | |

## 1.5 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

*Each invariant becomes a P1 acceptance criterion in the component that enforces it, and an S0 or S1 incident if it is ever breached.*

| ID | The system must never | Source (regulation, policy, contract) |
| --- | --- | --- |
| INV-1 | | |

## 1.6 Known constraints and decisions already made

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

*Constraints specific to this effort, and decisions already settled (link ADRs). Open decisions become ADR options at the HLD; do not argue them here.*

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

---

## 2.1 Components

> **Owner:** C · **Persona:** `architect` drafts; the owner confirms

| Component | Prefix | Component PRD |
| --- | --- | --- |
| | | |

## 2.2 Functional requirement index

> **Owner:** C · **Persona:** `product-writer` drafts wording; the owner selects and approves · **Seed question:** 3

| ID | Requirement | Component | Priority |
| --- | --- | --- | --- |
| FR-1 | | | P1 |

## 2.3 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |
| NFR-1 | Latency | | |
| NFR-2 | Availability | | |
| NFR-3 | Scale | | |
| NFR-4 | Data residency | | |

## 2.4 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

| Data | Classification | Source or owner | Retention |
| --- | --- | --- | --- |
| | | | |

## 2.5 Integrations and owners

> **Owner:** H confirms owners · **Persona:** `architect` may draft · **Seed question:** 8

| System | Owner | Relationship | SLA |
| --- | --- | --- | --- |
| | | | |

## 2.6 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | |
| Conditions that halt the rollout | |
| Support owner and escalation path | |
| Response targets by severity (S0 to S4) | |

## 2.7 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

*What must be true to call the release done.*

## 2.8 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves

- [ ] Q:

### Gate 1: Requirements approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |
