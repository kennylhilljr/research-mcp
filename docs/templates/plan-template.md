---
title: "{{MILESTONE}} plan"
type: plan
version: {{VERSION}}
status: draft
owner: "[Name]"
milestone: {{MILESTONE}}
artifact_type: plan
components: [] # the components this plan builds; the gate hook checks each one has an approved LLD
date: {{DATE}}
---

# {{MILESTONE}} plan (v{{VERSION}})

## How to use this template

*The plan breaks an approved LLD into slices and dependency-ordered tasks. Each task fits in one agent session and cites the requirement IDs it serves. Set `components:` in the front matter to the components the plan builds; the gate hook checks that each one has an approved LLD. Order tasks by priority and severity; this reference profile uses the combined ordering S0, S1, P1, then S2 and P2, then S3 and P3 (a local choice).*

## Slices

> **Owner:** A · **Persona:** `planner`

| Slice | Stories | Criteria | Checkpoint |
| --- | --- | --- | --- |
| 1 | | | |

## Tasks

> **Owner:** A · **Persona:** `planner`

| # | Task | Criteria | Depends on | Persona | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | | | | `implementer` | planned |

*Status is `planned`, `in progress` or `done`. trace-check requires a test for a criterion once a task that names it is `done`.*

## Verification

> **Owner:** A · **Persona:** `planner`

*What the verifier checks at the end of each slice.*

## Open questions

> **Owner:** A · **Persona:** `planner`

- [ ] Q:
