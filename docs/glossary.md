# Glossary

Domain terms used across this project's documents, defined once. Terms used only inside one PRD can stay in that PRD's glossary section.

> **Owner:** A · **Persona:** `product-writer` (definitions), `doc-steward` (hygiene)

## Framework terms

| Term | Definition |
| --- | --- |
| Acceptance criterion | A testable statement of behavior in EARS notation, with an ID such as `TECH-2`. Tests and code cite it with `@spec`. |
| ADR | Architecture decision record: one decision with its options and tradeoffs. Superseded by a new ADR, never edited after acceptance. |
| Agent role (persona) | A named, scoped role an agent plays when it drafts or reviews part of a document, such as `product-writer` or `verifier`. It prepares material; it never makes an accountable decision. |
| Annotation reach | The share of changed source files that carry at least one `@spec` annotation. |
| Business Application | An L3 scope: one application that delivers a capability to the business. Not the same as a software component. |
| Decision owner (H, C, A) | The tag on every template section. H: a person supplies and approves it. C: an agent drafts options; a person selects and approves. A: an agent prepares it from approved inputs. |
| Declaration, imperative | Parts of L0 direction: a declaration states a position the organization takes; an imperative states something every domain must do. Both are imported, not written in SDD. |
| Delivery artifact chain | The unnumbered sequence of artifact types from Product specification through high level design, low level design, plans, code, tests, handoff and evidence. Each derives from the one above. |
| Drift | A disagreement between artifacts in the trace, such as code that does more than its criterion. The named owner decides which artifact lost intent. |
| EARS | Easy Approach to Requirements Syntax: fixed sentence shapes such as "When *trigger*, the *system* shall *response*." |
| Evidence state | The state trace-check gives each criterion: planned, test linked, passing, failing, deferred, excepted, drifted or gap. |
| Gate | A human approval checkpoint: Gate 1 approves the Product specification, Gate 2 the high level design, Gate 3 the low level design for one component. Gates are not scope levels. |
| HLD | High level design: the SPEC, the system design with its ADRs. An artifact type, not an organizational level. |
| Intake checkpoint | The human approval of the problem framing (PRD Section 1) before requirements are written. A local control, not one of the three gates. |
| LLD | Low level design: one per software component, with contracts, schema, authorization and the test strategy. An artifact type, not an organizational level. |
| Organizational scope (L0 to L3) | Where an artifact sits in the organization: L0 Enterprise strategy, declarations and imperatives; L1 domain; L2 solution or capability; L3 Business Application. Recorded in the scope map. |
| Portable core | The parts every adopting organization keeps: templates with decision owners, human gates, stable IDs and their lifecycle, structural trace checks and change control. |
| Reverse orphan | An `@spec` annotation that cites an ID no document defines. |
| Scope map | `docs/scope/scope-map.yaml`: each organizational scope, its level, its parent one level up, its owner and status. |
| Severity (S0 to S4) | The urgency and impact of support work, from S0 (critical, immediate) to S4 (negligible, backlog). A separate lens from Product priority (P1 to P3). |
| Software component | A part of one application's code with its own ID prefix, PRD and LLD, such as `tech` in the worked example. Not an organizational scope. |
| Strategy | L0 direction for the whole organization, such as the enterprise strategy that domains translate. |
| Tech domain | The example L1 domain of this toolkit's reference profile, used to show how organizational scope works. |
| Traceability | Plain-text links from a criterion to the tests and code that cite it, checked by trace-check. Structural: a link does not prove that a test checks what the criterion means. |

## Domain terms

| Term | Definition |
| --- | --- |
