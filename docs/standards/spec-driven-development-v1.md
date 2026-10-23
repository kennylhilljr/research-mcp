---
title: "Spec-driven development standard"
type: standard
version: 1
status: approved
owner: "Framework owner"
date: 2026-10-22
---

# Spec-driven development standard (v1)

This standard defines how a repository using the SDD framework divides work between people and agents. It is normative: "must" is a rule the tools or the gates enforce, "should" is a strong default. The [framework overview](../guide/framework-overview.md) explains the reasoning in plain terms.

## 1. Principles

1. People write what cannot be derived: intent, boundaries, invariants and decisions that are expensive to reverse. An agent may interview the owner to capture them, but must never invent them.
2. Agents derive everything else, and regenerate it when something upstream changes.
3. Human approval stays where mistakes are costly to undo: public contracts, persisted schema and security paths are reviewed even when an agent wrote them.
4. Every section has one owner, and every artifact stays short.
5. Links between layers are plain text that a script can check.
6. Approved versions are frozen. A change produces the next numbered version.

## 2. The constitution

`AGENTS.md` at the repository root is the constitution. It holds the organization's rules, the approved stack, commands and the definition of done. Every person and agent reads it first. `CLAUDE.md` contains one line, `@AGENTS.md`, so Claude Code loads the same file. The constitution is human-owned; agents may propose changes but must not apply them without the owner's approval.

## 3. Layers

| Layer | Document | Folder | Mostly | Approved at |
| --- | --- | --- | --- | --- |
| L0 | Vision and strategy | `docs/vision/` | H | |
| L1 | Parent PRD: outcomes, FR index, NFRs, invariants | `docs/prd/` | H | Gate 1 |
| L2 | Component PRDs: stories, requirements, acceptance criteria | `docs/prd/components/` | H and C | Gate 1 |
| L3 | SPEC, the system HLD | `docs/spec/` | C | Gate 2 |
| L4 | LLD per component, contracts, test plan | `docs/lld/`, `docs/contracts/`, `docs/test/` | A | Gate 3 |
| L5 | Milestone kickoff and plan | `docs/build/` | A | |
| L6 | Code, tests and handoff | `src/`, `test/`, `docs/build/` | A | Code review |

Beside the stack:

- **Research** (`docs/research/`, A) informs L0 to L3. It records findings and never decides.
- **ADRs** (`docs/adr/`, C) record decisions at whatever layer makes them, most often L3.
- **Audit state** (`docs/trace/`, A) is derived and never versioned.
- **Operations** (`docs/runbooks/`, `docs/postmortems/`) are written by the `sre` persona.
- **Templates** (`docs/templates/`) and **standards** (`docs/standards/`) define the documents themselves.

Each layer derives from the one above, and each requirement ID cites its parent, so a check can walk from a vision outcome down to a passing test.

## 4. Ownership tags

Every section of every template carries one tag and, for C and A, the persona that writes it.

| Tag | Who writes | Who decides | An agent may |
| --- | --- | --- | --- |
| **H** Human-authored | The owner | The owner | Ask questions and reformat; never invent content |
| **C** Co-authored | A persona drafts two or three options, or a first pass | The owner picks, edits and signs off | Propose options with tradeoffs |
| **A** Agent-generated | A persona, derived from the H and C sections | The owner reviews at the gate, or only on exception | Regenerate freely when upstream changes |

The tag is written as a line under the section heading, for example `> **Owner:** A · **Persona:** product-writer`. spec-lint warns when a template section has no owner line.

## 5. Gates

| Gate | What is approved | Who | What it unlocks |
| --- | --- | --- | --- |
| Gate 0 | The problem framing (PRD Section 1) | Decision makers | Requirements work |
| Gate 1 | The PRD (parent and component) | Owner | `sdd-hld` |
| Gate 2 | The SPEC and the chosen ADRs | Owner | `sdd-lld` |
| Gate 3 | The LLD, with contracts, schema and authorization reviewed | Owner, with security review | `sdd-tasks`, `sdd-implement` |

A gate is passed by a person setting `status: approved` in the document's front matter and filling in the approvals table. Agents must never set `status: approved`. The gate hook blocks `sdd-hld`, `sdd-lld`, `sdd-tasks` and `sdd-implement` until their input is approved. Gate 0 is human only: no hook enforces it, and `sdd-spec` stops when the problem framing is not approved.

## 6. The twelve seed questions

Every H section maps to one of these questions. The `sdd-intake` skill asks them; an agent follows up only when an answer is missing or two answers conflict.

| # | Question | Feeds |
| --- | --- | --- |
| 1 | What problem are we solving, for whom, and why now? | PRD problem, users |
| 2 | What does success look like in numbers, and by when? | Outcomes, deadline |
| 3 | What are the top three things users must be able to do, in priority order? | Stories and priorities, then criteria |
| 4 | What is explicitly out of scope? | Non-goals |
| 5 | What must never happen? | Invariants, threat model, security tests |
| 6 | What are the latency, availability, scale and residency targets? | NFRs, capacity, alerts |
| 7 | What data does it touch, and how is it classified? | Data table, controls |
| 8 | What systems must it integrate with or replace, and who owns them? | Integrations |
| 9 | What is already fixed (stack, vendors, platforms, budget)? | Constitution, ADR limits |
| 10 | Which decisions are already made, and which are open? | ADR options |
| 11 | What is the rollout risk tolerance, and who responds when it fails? | Rollout plan, support owners |
| 12 | How will we know it is done? | Definition of done, test plan |

Questions 9 and 10 are usually answered once in the constitution.

## 7. Requirement IDs

| ID | Pattern | Example | Defined in |
| --- | --- | --- | --- |
| Parent requirement | `FR-<n>`, `NFR-<n>`, `OUT-<n>`, `INV-<n>` | `FR-3` | Parent PRD |
| Acceptance criterion | `<PREFIX>-<n>` | `TECH-2` | Component PRD |
| Story | `<PREFIX>-US-<n>` | `TECH-US-1` | Component PRD |
| Component requirement | `<PREFIX>-FR-<n>` | `TECH-FR-1` | Component PRD |
| Component NFR, invariant, outcome | `<PREFIX>-NFR-<n>`, `<PREFIX>-INV-<n>`, `<PREFIX>-OUT-<n>` | `TECH-INV-1` | Component PRD |
| Decision | four-digit number | ADR 0002 | `docs/adr/` |

Rules:

- `<PREFIX>` is two to ten uppercase letters or digits, starts with a letter, is unique in the repository, and is declared in the component PRD's `prefix` front matter and in `sdd.config.json`. `FR`, `NFR`, `OUT`, `INV`, `US`, `AC`, `ADR`, `SPEC`, `LLD` and `PRD` are reserved.
- IDs are defined in the first column of a table whose first header is `ID`.
- An ID is never renumbered and never reused, even after the requirement is deleted.
- Only acceptance criteria are tracked for test coverage. Tests and code cite criteria, not stories or requirements.

## 8. Acceptance criteria

- Criteria are written in EARS by default: ubiquitous ("The system shall..."), event-driven ("When..."), state-driven ("While..."), unwanted behavior ("If... then..."), optional feature ("Where..."), or a combination.
- A document may use Given/When/Then instead by setting `notation: gherkin` in its front matter. One notation per document.
- Each criterion states one response, names the system as its subject, is testable as written, and carries a priority of P1, P2 or P3.
- spec-lint enforces the form and the priority on approved documents and warns on drafts.

## 9. Document conventions

**Front matter.** Every versioned document starts with YAML front matter:

| Key | Required | Values |
| --- | --- | --- |
| `title` | yes | Free text |
| `type` | yes | `vision`, `research`, `prd`, `prd-component`, `spec`, `lld`, `test-plan`, `kickoff`, `plan`, `handoff`, `runbook`, `standard` |
| `version` | yes | Must match the `-vN` in the file name |
| `status` | yes | `draft`, `in-review`, `approved`, `superseded` |
| `owner` | yes | The accountable person |
| `prefix` | component PRDs and LLDs | The component's ID prefix |
| `parent` | when there is one | Path of the document this derives from |
| `supersedes` | on a next version | Path of the previous version |
| `deferred` | test plan only | Criteria deferred with the owner's approval |
| `notation` | optional | `ears` (default) or `gherkin` |

**Versions.** File names end in `-vN.md`. A document whose status is `approved` must not be edited. A change produces the next version with `node tools/sdd/cli.mjs new --next <path>`, which copies the file, raises the version, sets `status: draft` and records `supersedes`. The protect-approved hook blocks edits to frozen documents. The doc map (`docs/README.md`, or the file named by `paths.docMap`) lists the latest version of each document.

**ADRs** are numbered once (`0001-<slug>.md`), carry a status of `proposed`, `accepted`, `rejected`, `superseded` or `deprecated`, and are never versioned. A changed decision gets a new ADR that supersedes the old one.

**Open questions** are written as a checkbox line starting with `- [ ] Q:` and resolved as `- [x] Q:` with the answer. An approved document must have no open questions and no template placeholders.

**Brownfield rationale.** Rationale inferred from existing code is tagged `[inferred]` until the owner confirms it.

## 10. Linking and tracking intent

**Annotations.** A test cites the criterion it verifies in a comment of the form `@spec TECH-2` (several IDs are separated by commas). The entry point of the behavior in code carries the same annotation: the topmost function or handler that owns the behavior, not every helper. A behavior that spans subsystems gets one annotation per subsystem entry point. References to SPEC or LLD sections go in the handoff, not in code.

**Checks.** `tools/trace-check` runs in CI on every pull request. It fails the build when:

1. an annotation cites an ID that no PRD defines (reverse orphan);
2. a criterion in an approved PRD has no test citing it and is not deferred (uncovered);
3. the test plan marks a criterion covered but no test cites it (hollow status);
4. a P1 criterion is listed as deferred.

It warns when a criterion has a test but no code entry point, when a component changed since its last audit or has not been audited within `trace.staleAfterDays`, and when annotation reach falls below `trace.reachWarnBelow`. Criteria in draft PRDs are reported but not enforced.

**Status lives only in derived files.** Coverage lives in `docs/trace/coverage.md`, regenerated by `trace-check --write`, and drift in `docs/trace/index.yaml`. Approved document versions, the test plan included, never carry status. Deferral is the one human decision recorded in the test plan, in its `deferred:` front matter list; the test plan read is the latest `docs/test/test-plan-vN.md` (approved first) unless `paths.testPlan` names another.

**Which version is enforced.** trace-check enforces the latest approved version of each PRD. While a newer version is a draft, the approved version's criteria stay enforced, and the IDs the draft adds are defined but not enforced until it is approved.

**Annotation reach.** The checks see only annotated code, and the agent that writes the code also places the annotations, so under-annotating is the cheapest way to pass. Reach (the share of changed source files that carry at least one annotation) is reported on every pull request, and code review treats a falling number as a finding.

**Semantic checks.** Two optional modes run behind feature flags: a divergence probe in `sdd-clarify`, where blind readers give two or three readings of each new criterion and every fork goes back to the owner; and a bidirectional differential in `sdd-verify`, which compares code written from a criterion with a criterion reconstructed from the code. Both support the gates and code review; neither replaces them.

## 11. Priorities

**Product delivery** ranks new capability before it is built.

| Priority | Meaning | Rule |
| --- | --- | --- |
| P1 | Must ship for the release to have value (the MVP) | First milestone; cannot be deferred |
| P2 | Should ship; the release has value without it | After P1; may be deferred with approval |
| P3 | Could ship | Backlog; re-ranked each milestone |

The owner sets a priority and a one-line reason on every story. Criteria inherit their story's priority. NFRs and invariants are always P1. Re-ranking is a change to the PRD, not to the task list.

**Support** ranks what goes wrong once something is built.

| Severity | Urgency | Impact | Example | Response | Path |
| --- | --- | --- | --- | --- | --- |
| S0 | Critical | Extensive | System outage, or a breach of an invariant | Immediate | Runbook now; fast path fix; postmortem |
| S1 | High | Large | Major feature malfunctioning | Urgent, within the normal schedule | Fast path: spec fix plus tasks; postmortem |
| S2 | Moderate | Moderate | Minor feature malfunctioning | Ranked against other work | Normal change |
| S3 | Low | Minor | A feature blocks a few users | Routine work | Normal change from the backlog |
| S4 | Negligible | Negligible | Cosmetic issue | Backlog | Backlog |

| Support type | What it is | Triaged by | Fix starts at |
| --- | --- | --- | --- |
| Failure | Outage, degradation or failed deploy | `sre` | Runbook, then the layer that caused it |
| Bug | Behavior violates an existing criterion | `verifier` | Code, with a reproducing test that cites the criterion |
| Spec gap | No criterion covers the behavior, or a criterion is wrong | `verifier` | The PRD or LLD |
| Blocker | Something stops delivery | `planner` | Whoever owns the blocking item |
| Drift | Code and spec disagree | `verifier` | The layer that is wrong, decided by the owner |

Rules: the triage agent assigns type and severity and cites the affected IDs; a person confirms every S0 and S1; a breach of an invariant is always S0 or S1; a blocker takes the severity of the work it blocks; every fix starts at the layer where behavior left intent.

**One queue.** Both lenses feed one ordered queue, kept by the `planner`: S0, then S1, then P1, then S2 and P2, then S3 and P3, then S4. S0 interrupts work in flight; everything else waits for the next task boundary.

## 12. Cascade and the size router

- A change inside one component cascades freely to its LLD, tests and code in the same change.
- A change that crosses components stops for a person and goes into the next SPEC version, with an ADR when the system's shape changes.
- Bugs and small changes take the short path: update the spec, then tasks, then code. S0 and S1 support work always takes the short path, with the gates combined into one human review.
- Every fix walks the same path upward first: find the layer where behavior left intent, and fix that layer before the code.

## 13. Feature flags

Every optional behavior has a flag in `sdd.config.json` under `features`. Switching a flag off must not lose data.

| Flag | Default | Effect |
| --- | --- | --- |
| `gateHook` | on | Blocks a skill until its input document is approved |
| `protectApprovedDocs` | on | Blocks edits to approved documents |
| `reachReport` | on | Reports annotation reach in trace-check |
| `divergenceProbe` | off | Enables the blind divergence probe in `sdd-clarify` |
| `differentialAudit` | off | Enables the bidirectional differential in `sdd-verify` |

Repositories adopted with `sdd adopt` also carry `adoption.mode: advisory`, which makes the checks report without failing until the owner switches to `enforced`.
