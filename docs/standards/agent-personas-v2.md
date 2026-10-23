---
title: "Persona standard"
type: standard
artifact_type: standard
version: 2
status: draft
owner: "Framework owner"
date: 2026-10-22
supersedes: docs/standards/agent-personas-v1.md
---

# Persona standard (v2)

SDD has two kinds of persona. **Human personas** decide and approve: they are accountable for every outcome. **Agent personas** prepare material from approved inputs: they can be responsible for work, but never accountable for it. This standard names both, defines what an agent persona file must contain, and maps every activity to its personas in a RASCI matrix (section 4).

## 1. Human personas

A human persona is a role, not a named person. The adopting organization assigns the people: in `CODEOWNERS` and branch protection for approvals, and in the `owner` field of the scope map for organizational scopes. Agents never take a human persona.

| Code | Human persona | Owns and decides | Approves |
| --- | --- | --- | --- |
| PO | Product | The problem, outcomes, scope, priorities, constraints and acceptance; story priority; deferral of P2 and P3 criteria | The intake checkpoint and Gate 1; acceptance of the outcome |
| EN | Engineering | Architecture and implementation choices; feasibility, dependency and risk input while intent is formed; the severity of support work | Gate 2 and code review; confirms S0 and S1 and approves postmortems |
| BA | Business Application owner | The L3 Business Application that the high level design describes: its integrations, constraints and operational fit | Reviews at Gate 2; approves at Gate 3 for decisions in the application's scope |
| CO | Component owner | A software component's public contracts, persisted schema, test strategy and evidence | The component's low level design at Gate 3 |
| CT | Control owner | Security and compliance controls: trust boundaries, the threat model and authorization enforcement | Those sections at Gates 2 and 3 |
| EX | Exception authority | Whether to accept the risk when a criterion cannot be met | Exceptions, recorded in the approved test strategy |

When verification reports drift, the owner of the disputed artifact decides which artifact first lost intent: Product for requirements, Engineering for the design, the component owner for the low level design and code.

Who holds each human persona, the exception authority and the fast path criteria are local choices; see the open decisions in the [SDD standard](spec-driven-development-v3.md#18-open-decisions).

## 2. Agent personas

### 2.1 Minimum requirements

Every agent persona definition must have:

1. **Identity:** `name` (kebab case, matching the file name) and a one-sentence `description` of when to use it.
2. **Purpose:** one paragraph.
3. **Owned sections,** each tagged A or C. Never an H section.
4. **Inputs,** in reading order: the repository instructions (`AGENTS.md`) first, then the approved artifact above its output.
5. **Outputs:** exact files and format; always the next numbered version, never an edit to an approved one.
6. **Tools:** least privilege. Reviewers are read-only apart from the check commands.
7. **Boundaries:** never invent H content, never approve or verify its own work, never edit another persona's section, cite requirement IDs, mark assumptions.
8. **Gate and handoff:** which human checkpoint reviews its output and who receives it next.
9. **Definition of done:** the checks it runs before handing off.
10. **Escalation:** when it stops and asks: a missing or conflicting H answer, a spec that admits two readings, or anything hard to undo.

A persona file also carries a version and a changelog (section 6).

### 2.2 Roster

| Code | Agent persona | Prepares (A) | Drafts for a decision (C) | Checkpoint |
| --- | --- | --- | --- | --- |
| AN | `analyst` | Research, prior art, the adoption inventory, interview notes that capture the owner's H answers | None; may interview for H sections | Before the intake checkpoint and Gate 1 |
| PW | `product-writer` | Edge cases, assumptions and open questions, glossary, the ID history table | User stories, functional requirements and acceptance criteria | Gate 1 |
| AR | `architect` | Component breakdown, data flow and sequence diagrams, capacity, risks, PRD to SPEC traceability | ADR options, system context, integrations | Gate 2 |
| SEC | `security-reviewer` | None | Trust boundaries and threat model; authentication and authorization enforcement points | Gates 2 and 3 |
| CD | `component-designer` | Module structure, algorithms, error handling, configuration and feature flags | Public contracts, persisted schema, authorization enforcement | Gate 3 |
| TA | `test-architect` | Gaps, the recorded deferrals and exceptions, the derived coverage report | Testing strategy; the test plan with planned evidence per criterion | Gates 2 and 3 |
| SRE | `sre` | Observability, runbooks, failure triage, postmortem drafts | Rollout and migration | Gates 2 and 3; S0 and S1 confirmation |
| PL | `planner` | Milestone kickoffs and plans, slices, tasks, blocker triage, the queue | None | After Gate 3 |
| IM | `implementer` | Code and tests that cite criteria with `@spec`, the handoff with test results | None | Code review |
| VE | `verifier` | Traceability, drift and reach findings, the audit index and records, bug and drift triage, optional probes | None | Every checkpoint, independently |
| DS | `doc-steward` | Doc map, glossary hygiene, version and link hygiene, the catalog | None | None (mechanical) |

The `verifier` never checks work it produced, and runs with read-only tools plus the check commands.

## 3. Where personas live

| What | Where | Why |
| --- | --- | --- |
| Human persona assignments | `CODEOWNERS`, branch protection and the scope map `owner` fields | Repository controls, not front matter, prove approver authority |
| Agent persona definitions | `.claude/agents/<name>.md` | Claude Code discovers subagents there; other agents read the same files |
| This standard | `docs/standards/agent-personas-v2.md` | Reviewed and approved like any other standard |
| Catalog of agent personas, skills and commands with versions | `docs/guide/catalog.md` | Generated by `node tools/sdd/cli.mjs catalog` |
| Which persona writes which section | The owner line of each section in `docs/templates/` | Assignments travel with every new document |

Personas are not a layer of the document stack, and they do not belong in `tools/`, which holds executable checks.

## 4. RASCI

Each activity has exactly one accountable human persona, except drift (marked A†). Agents are never accountable: where an agent persona is responsible, the accountable person reviews its output at the named gate or in code review.

| Letter | Meaning |
| --- | --- |
| R | Responsible: does the work |
| A | Accountable: approves the result; always a person, and one per row except where marked † |
| S | Support: helps the responsible party, for example by drafting options or checking the trace |
| C | Consulted: gives input before the decision |
| I | Informed: told of the result |
| A/R | The accountable person also does the work (a human decision section) |
| A† | The owner of the disputed artifact is accountable: Product for requirements, Engineering for the design, the component owner for the low level design and code |

| Activity | PO | EN | BA | CO | CT | EX | AN | PW | AR | SEC | CD | TA | SRE | PL | IM | VE | DS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ## Product specification | | | | | | | | | | | | | | | | | |
| Answer the seed questions and frame the problem (intake checkpoint) | A/R | C | C | | C | | S | | | | | | | | | | |
| Record the organizational scope | A/R | C | C | | | | S | | | | | | | | | | |
| Research and prior art | A | C | | | | | R | | | | | | | | | | |
| Outcomes, scope, invariants and quality targets | A/R | C | C | | C | | S | S | | | | | | | | | |
| User stories and story priority | A | C | C | | | | | R | | | | | | | | | |
| Requirements and acceptance criteria (Gate 1) | A | C | | | C | | | R | | | | | | | | S | |
| Edge cases, assumptions, glossary and ID history | A | | | | | | | R | | | | | | | | | S |
| ## High level design | | | | | | | | | | | | | | | | | |
| Architecture decisions, system context and integrations (Gate 2) | C | A | C | | | | | | R | S | | | S | | | | |
| Trust boundaries and threat model | | C | C | | A | | | | S | R | | | | | | | |
| Rollout and migration strategy | C | A | C | | | | | | | | | | R | | | | |
| Testing strategy | C | A | | | | | | | | | | R | | | | | |
| Component breakdown, data flow, capacity and risks | | A | I | | | | | | R | | | | S | | | | |
| ## Low level design | | | | | | | | | | | | | | | | | |
| Public contracts and persisted schema (Gate 3) | | C | C | A | | | | | | S | R | | | | | | |
| Authorization enforcement points | | | C | C | A | | | | | R | S | | | | | | |
| Test strategy with planned evidence per criterion | C | | | A | | | | | | | | R | | | | S | |
| Modules, error handling, configuration and observability | | I | | A | | | | | | | R | | R | | | | |
| ## Build and verify | | | | | | | | | | | | | | | | | |
| Milestone plan and task order | C | A | | C | | | | | | | | | | R | | | |
| Code and tests that cite criteria, and the handoff | | A | | C | | | | | | | | | | | R | S | |
| Code review | | A/R | | C | | | | | | | | | | | | S | |
| Trace check, evidence states and audit record | | I | | A | | | | | | | | S | | | | R | |
| Acceptance of the outcome | A/R | C | C | | | | | | | | | | | | | S | |
| ## Change and support | | | | | | | | | | | | | | | | | |
| Decide which artifact first lost intent (drift) | A† | A† | | A† | | | | | | | | | | | | S | |
| Triage support work and set severity; confirm S0 and S1 | C | A | | C | | | | | | | | | R | R | | R | |
| Defer a P2 or P3 criterion | A | C | | | | | | | | | | R | | S | | | |
| Except a criterion and accept the risk | C | | | | C | A | | | | | | R | | | | | |
| Postmortem for an S0 or S1 incident | I | A | | C | | | | | | | | | R | | | | |
| Doc map, glossary, version and link hygiene | | A | | | | | | | | | | | | | | | R |

## 5. Changing the RASCI

The matrix is part of this standard. Changing who is accountable for an activity, or adding or removing a persona, produces the next version of this standard. An adopting organization can rename the human personas to match its own roles, but it keeps one accountable person per activity and keeps agents out of the A column.

## 6. Versioning personas and skills

- Every agent persona, skill and command carries a semantic version in its front matter under `metadata.version` (for example `1.0.0`). Keeping it under `metadata` keeps the files valid for Claude Code, claude.ai uploads and the Skills API.
- **Major** changes alter what a persona owns, its boundaries or its outputs. **Minor** changes add a capability or a check. **Patch** changes fix wording.
- Every persona and skill ends with a `## Changelog` table (`| Version | Date | Change |`) whose first row is the current version. spec-lint fails when the version is not semver or has no changelog row.
- After a change, regenerate the catalog with `node tools/sdd/cli.mjs catalog`. CI fails when the catalog is out of date.
- A change to either roster (adding, removing or merging a persona) is a change to this standard and produces its next version.

## 7. Agents without subagents

Agents that cannot run subagents, such as Codex today, use the same files by hand. Before writing a section, the agent reads the persona named in the section's owner line, follows its inputs, boundaries and definition of done, and does not take on a second persona in the same step. `AGENTS.md` points every agent to this standard.

## Changes from v1

| Change | Why |
| --- | --- |
| Added the human personas (section 1): Product, Engineering, Business Application owner, Component owner, Control owner and Exception authority | v1 named only agent personas; the gates and the RASCI need the people who decide |
| Updated the agent roster to the 1.1.0 persona files | v1 listed contracts, schema, the test plan and authorization as agent-written; 1.1.0 makes them drafts for a human decision (C) |
| Added the RASCI matrix (section 4) and the rule for changing it (section 5) | One accountable person per activity, and agents never accountable |
| Added two-letter codes for every persona | The RASCI columns need short labels |
| "Constitution" is now "repository instructions" | Matches `AGENTS.md` in 1.1.0 |
