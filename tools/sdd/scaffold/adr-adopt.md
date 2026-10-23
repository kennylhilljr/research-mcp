---
title: "Adopt spec-driven development"
status: proposed
owner: "{{OWNER}}"
date: {{DATE}}
---

# ADR {{NUMBER}}: Adopt spec-driven development

> **Owner:** C · **Persona:** `architect` drafts; the owner decides.

## Context

This application is already running. Its intent lives in code, tests and people's heads, so agents that change it have to guess what it is meant to do. The SDD framework {{FRAMEWORK_VERSION}} was added by `sdd adopt` without changing any existing file.

## Options

| Option | Benefits | Costs |
| --- | --- | --- |
| 1. Adopt incrementally: write specs for components as they change; checks stay advisory until components reach AUDITED | No big-bang effort; value appears where work happens | Coverage grows slowly; two styles coexist for a while |
| 2. Adopt fully: specify every component before new work | Complete trace quickly | Large upfront cost; delays delivery |
| 3. Do not adopt | No cost | Agents keep guessing intent |

## Decision

- [ ] Q: Which option does the owner choose?

## Consequences

To be written once the decision is made.
