---
title: "{{TITLE}}"
type: prd-component
version: {{VERSION}}
status: draft
owner: "[Name]"
decision_makers: "[Name]"
prefix: {{PREFIX}}
parent: docs/prd/PRD-v1.md
artifact_type: product-specification
scope_level: L3
scope_name: "[scope key from docs/scope/scope-map.yaml]"
date: {{DATE}}
---

# Component PRD: {{TITLE}} (v{{VERSION}})

## How to use this template

*Every section has a decision owner tag. **H** human decision: a person supplies and approves it; an agent may interview, organize and edit but never invents it. **C** human decision with agent draft: the named persona drafts options and exposes assumptions and tradeoffs; a person selects and approves. **A** agent prepared from approved inputs: the named persona prepares it; it cannot change approved intent and must pass the checks.*

*This PRD states the what and why, never the how. Solution options, architecture, rollout plans, system monitoring and test plans belong in the SPEC, ADRs, LLDs and the milestone plan.*

*Section 1 is approved at the intake checkpoint (problem approved) before Section 2 begins. Section 2 is approved at Gate 1 (requirements approved). Each approval produces a new version; an approved version is never edited.*

*Scope: `scope_level` and `scope_name` record the organizational scope (L0 to L3) this PRD serves; they are not document stages. IDs never change and are never reused: acceptance criteria `[PREFIX]-1` (what tests and code cite with `@spec`), stories `[PREFIX]-US-1`, functional requirements `[PREFIX]-FR-1`, NFRs `[PREFIX]-NFR-1`, invariants `[PREFIX]-INV-1`, outcomes `[PREFIX]-OUT-1`.*

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

*The problem this component solves, for whom, and the evidence that it is real. Link the parent PRD instead of repeating it.*

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
| [PREFIX]-OUT-1 | | | | |

## 1.5 Leaps of faith

> **Owner:** H · **Persona:** none

*Two or three bets that must hold for this to succeed. If one turned out false, would we still build this? If not, it belongs here.*

| Leap of faith | How we will validate it | By when |
| --- | --- | --- |
| | | |

## 1.6 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

*Each invariant becomes a P1 acceptance criterion and an S0 or S1 incident if breached.*

| ID | The system must never | Source (regulation, policy, contract) |
| --- | --- | --- |
| [PREFIX]-INV-1 | | |

## 1.7 Known constraints and decisions

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

| Decision or constraint | Status (made or open) | Rationale or link |
| --- | --- | --- |
| | | |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

---

## 2.1 Customer discovery

> **Owner:** A · **Persona:** `analyst`

*What research found, with links to `docs/research/`.*

## 2.2 User stories and priority

> **Owner:** C for stories (`product-writer`), H for priority · **Seed question:** 3

*P1 must ship for the release to have value (the MVP). P2 should ship. P3 could ship. Each P1 story is an independently testable slice.*

| ID | As a... I want... so that... | Priority | Why this priority |
| --- | --- | --- | --- |
| [PREFIX]-US-1 | | P1 | |

## 2.3 User experience

> **Owner:** C · **Persona:** `product-writer` drafts the narrative; designers own the design artifacts · **Seed question:** 3

*The key flows as a short narrative. Link the full design. Reference story IDs.*

## 2.4 Functional requirements and acceptance criteria

> **Owner:** C · **Persona:** `product-writer` drafts requirements and criteria as options; the owner selects and approves · **Seed questions:** 3, 12

| ID | Requirement | Story | Parent |
| --- | --- | --- | --- |
| [PREFIX]-FR-1 | | [PREFIX]-US-1 | FR-1 |

*Acceptance criteria in EARS, one response each, with the system named as the subject. Criteria inherit their story's priority.*

| ID | Criterion | Requirement | Priority |
| --- | --- | --- | --- |
| [PREFIX]-1 | When *trigger*, the *system* shall *response*. | [PREFIX]-FR-1 | P1 |

*EARS patterns: ubiquitous (The system shall...), event-driven (When...), state-driven (While...), unwanted behavior (If... then...), optional feature (Where...). To use Given/When/Then instead, set `notation: gherkin` in the front matter.*

## 2.5 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |
| [PREFIX]-NFR-1 | Latency | | |

## 2.6 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

| Data | Classification | Source or owner | Retention | Notes |
| --- | --- | --- | --- | --- |
| | | | | |

## 2.7 Integrations and owners

> **Owner:** H confirms owners and SLAs · **Persona:** `architect` may draft · **Seed question:** 8

| System | Owner | Relationship (depends on, feeds, replaces) | SLA |
| --- | --- | --- | --- |
| | | | |

## 2.8 Product risks

> **Owner:** H · **Persona:** none

| Risk | Question | Assessment | Mitigation |
| --- | --- | --- | --- |
| Value | Will customers choose to use this? | | |
| Usability | Can customers use it, including with accessibility needs? | | |
| Viability | Does it work for the business: economics, legal, compliance, operations? | | |

## 2.9 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | |
| Business conditions that must halt the rollout | |
| Support owner and escalation path | |
| Response targets by severity (S0 to S4) | |

## 2.10 Measurement and experimentation

> **Owner:** C · **Persona:** `product-writer` drafts; the owner decides

| Outcome | Measured by | Experiment (if any) |
| --- | --- | --- |
| [PREFIX]-OUT-1 | | |

## 2.11 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

*Which criteria pass, what is demonstrated, and which outcome metrics are measurable at launch.*

## 2.12 Edge cases and error behavior

> **Owner:** A · **Persona:** `product-writer`

*Boundary conditions and failure modes. Each one that changes behavior becomes an acceptance criterion in 2.4.*

## 2.13 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves before Gate 1

- [ ] Q:

## 2.14 Glossary

> **Owner:** A · **Persona:** `product-writer`

| Term | Definition |
| --- | --- |
| | |

## 2.15 ID history

> **Owner:** C · **Persona:** `product-writer` records; the owner confirms

*IDs that left this PRD. A change to the actor, trigger, response, target, control obligation or test obligation gets a new ID, and the old one is recorded here as superseded. An editorial change keeps the ID. Rows in this table are not definitions.*

| ID | Status | Replaced by | Reason |
| --- | --- | --- | --- |

### Gate 1: Requirements approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |
