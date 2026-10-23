---
title: "Spec-driven development standard"
type: standard
artifact_type: standard
version: 3
status: in-review
owner: "Framework owner"
date: 2026-10-22
supersedes: docs/standards/spec-driven-development-v2.md
---

# Spec-driven development standard (v3)

This standard defines how a repository using the SDD toolkit carries intent from Product to Engineering and keeps it traceable through tests, code and evidence. "Must" is a rule the tools or the gates enforce; "should" is a strong default.

**Authority.** When approved, this standard is approved for this repository and the repositories that install the toolkit from it. It is a reference implementation that is being built and iterated, not a finished enterprise standard. The organization's controlled standard, and who approves it, is an open decision (Section 18). `AGENTS.md`, a README or a tool configuration never becomes organizational authority by implication.

## 1. Purpose

SDD creates a controlled bridge from Product intent to Engineering delivery.

- **Product** owns the problem, desired outcomes, scope, priorities, constraints and acceptance.
- **Engineering** contributes feasibility, dependency and risk input while intent is formed, then owns architecture and implementation choices.
- **Product stays accountable** when implementation reveals a choice that changes approved behavior or outcomes. That choice goes back to Product before it ships.
- **Agents** prepare bounded, traceable material from approved inputs. They do not replace accountable Product, Engineering, Security or business decisions.

Shared templates, named decision ownership, approval gates and stable identifiers preserve the connection from intent to evidence.

## 2. Portable core and local choices

An adopting organization takes the portable core as is and adapts the local choices to its own governance.

| Portable core | Local choices (this reference profile's defaults) |
| --- | --- |
| Templates with a decision owner on every section (H, C, A) | Folder layout under `docs/` |
| Human approval at Gates 1 to 3 | Who approves each gate, exception authority, fast path criteria |
| Stable IDs and their lifecycle (Section 10) | ID syntax (`TECH-2` by default; a richer form is configurable) |
| Structural trace checks from criteria to tests and code | The intake checkpoint as a named control (Section 8) |
| Frozen approved versions and change control | One combined queue for priority and severity (Section 15) |
| Organizational scope recorded separately from the artifact chain | The L1 domain and its scope map (the Tech domain in this profile) |
| | Agent tooling: Claude Code skills, personas and hooks |

## 3. Three separate concepts

Organizational scope, the delivery artifact chain and the gates are independent.

| Concept | Values | What it answers |
| --- | --- | --- |
| Organizational scope | L0, L1, L2, L3 | Which part of the organization an artifact serves |
| Delivery artifact chain | Artifact types, unnumbered | Which artifact derives from which |
| Gates | Gate 1, Gate 2, Gate 3, plus the intake checkpoint | Which human approval an artifact needs |

Gate 1, Gate 2 and Gate 3 are approval checkpoints. They do not correspond to organizational scope levels L1, L2 and L3. HLD and LLD are artifact types, not organizational levels.

## 4. Organizational scope

| Level | Meaning |
| --- | --- |
| L0 | Enterprise strategy, declarations and imperatives |
| L1 | Domain. The Tech domain is the example domain in this reference profile |
| L2 | Solution or capability, such as entitlement management or access certification |
| L3 | Business Application |

The scope map (`docs/scope/scope-map.yaml`, set by `paths.scopeMap`) names each scope, its level, its parent one level up, its owner and its status. spec-lint checks that levels are L0 to L3 and that each parent is exactly one level up. The worked example's scopes are illustrative: they do not select the pilot's L2 capability or L3 Business Application.

**Scope metadata.** Documents may carry these front matter keys. They describe two different relationships: a scope parent is an organizational unit; a trace parent is an artifact.

| Key | Meaning |
| --- | --- |
| `scope_level` | L0, L1, L2 or L3 |
| `scope_name` | A key in the scope map |
| `scope_parent` | The parent scope, a key in the scope map |
| `affected_scopes` | Other scopes the artifact changes |
| `artifact_type` | Its place in the delivery artifact chain (Section 5): `strategic-direction`, `domain-translation`, `vision`, `problem-framing`, `product-specification`, `high-level-design`, `low-level-design`, `test-strategy`, `plan`, `handoff`, `evidence`, `decision`, `research`, `operations` or `standard` |
| `derives_from` | Path of the artifact it derives from (the trace parent) |
| `satisfies` | Requirement IDs it satisfies |

When `scope_name` is absent, the doc map uses the component's `scope` from `sdd.config.json`, then `project.scope`.

## 5. The delivery artifact chain

Each artifact derives from the one above it. The chain is unnumbered.

| Artifact type | Document | Folder | Decision owner | Approved at |
| --- | --- | --- | --- | --- |
| Strategic direction | Imported L0 strategy, declarations and imperatives | Outside the repository, linked | L0 owners | Outside SDD |
| Domain translation | How the L1 domain applies L0 direction | `docs/vision/` or linked | L1 owners | Outside SDD |
| Vision and direction | The product's vision | `docs/vision/` | Product (H) | |
| Problem framing | PRD Section 1, from the seed questions | `docs/prd/` | Product (H) | Intake checkpoint |
| Product specification | Parent PRD and component PRDs | `docs/prd/`, `docs/prd/components/` | Product (H and C) | Gate 1 |
| High level design | The SPEC and its ADRs | `docs/spec/`, `docs/adr/` | Engineering (C) | Gate 2 |
| Low level design | LLD per component, contracts, test strategy | `docs/lld/`, `docs/contracts/`, `docs/test/` | Engineering (C and A) | Gate 3 |
| Plan | Milestone kickoff and plan | `docs/build/` | Engineering (A) | |
| Code and tests | Implementation | `src/`, `test/` | Engineering (A) | Code review |
| Handoff | What was built and its evidence | `docs/build/` | Engineering (A) | Code review |
| Evidence | Coverage and audit state, derived | `docs/trace/` | Derived (A) | |

Beside the chain: research (`docs/research/`, A) records findings and never decides; operations (`docs/runbooks/`, `docs/postmortems/`) are written by the `sre` persona; templates and standards define the documents themselves.

## 6. Decision ownership

Every section of every template carries one tag and, for C and A, the persona that drafts it.

| Tag | Meaning | An agent may |
| --- | --- | --- |
| **H** Human decision | A person supplies and approves the content | Interview, organize and edit; never invent |
| **C** Human decision with agent draft | A person selects and approves | Draft options, expose assumptions, sources and tradeoffs |
| **A** Agent prepared from approved inputs | Prepared by an agent; reviewed at the gate or on exception | Prepare and regenerate it; never change approved intent; must pass defined checks |

Functional requirements, acceptance criteria, the approved test strategy, public contracts, persisted schema and authorization enforcement are C. Coverage and audit counts are A because they are derived evidence. The tag is written under the section heading, for example `> **Owner:** C · **Persona:** product-writer`.

## 7. Roles at the bridge

| Activity | Product | Engineering | Agents |
| --- | --- | --- | --- |
| Problem framing and outcomes | Owns | Feasibility, dependency and risk input | Interview, organize, find gaps |
| Product specification | Owns and approves (Gate 1) | Reviews feasibility and controls | Draft criteria as options |
| High level design | Confirms any effect on approved outcomes | Owns and approves (Gate 2) | Draft options with tradeoffs |
| Low level design | Confirms any change to approved behavior | Owns and approves with control owners (Gate 3) | Draft contracts, schema and test strategy for review |
| Build and evidence | Accepts the outcome | Owns code review | Implement, link tests, regenerate evidence |

The full set of human personas (Product, Engineering, the Business Application owner, component and control owners, and the exception authority), the agent personas and a RASCI matrix for every activity are in the [persona standard](agent-personas-v2.md).

## 8. The intake checkpoint and the gates

| Checkpoint | What is approved | Approver (default role) | What it unlocks |
| --- | --- | --- | --- |
| Intake checkpoint | The problem framing (PRD Section 1) | Product authority | Requirements work (`sdd-spec`) |
| Gate 1 | The Product specification, parent and component | Product authority, with feasibility and control reviewers | `sdd-hld`; `sdd-lld` for that component |
| Gate 2 | The SPEC and its chosen ADRs | Engineering authority, with Product confirming any effect on approved outcomes | `sdd-lld` |
| Gate 3 | The LLD, with contracts, schema and authorization reviewed | Business Application, component and control owners for the decisions in their scope | `sdd-tasks` and `sdd-implement` for that component |

The intake checkpoint is a local control of this reference profile. It is not one of the three formal gates, and no hook enforces it; `sdd-spec` stops when the problem framing is not approved.

**Recording an approval.** A person sets `status: approved` and records who and when: `approved_by: "<name> (<role>)"` and `approved: <date>`. With `approvals.requireApprover: true`, spec-lint requires both. Agents never set `status: approved`.

**Binding.** Each gate applies to a specific component. The gate hook checks the component the skill is working on: `sdd-lld tech` needs the SPEC and the `tech` component PRD approved; `sdd-tasks tech` needs the `tech` LLD approved; `sdd-implement M1` needs the M1 plan and the approved LLD of every component that plan covers. When a repository has more than one component and none is named, the hook asks for it.

**Limits of enforcement.** Front matter is self-asserted: a hook can read `approved_by` but cannot prove who that person is or that they hold the role. Approver authority comes from repository controls: a `CODEOWNERS` file that names the owners of `docs/`, branch protection that requires their review, and the approval record in the pull request. The gate hook is an adapter for Claude Code; other agents follow the gates procedurally unless an equivalent adapter is installed.

## 9. The twelve seed questions

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
| 12 | How will we know it is done? | Definition of done, test strategy |

## 10. Requirement IDs and their lifecycle

| ID | Pattern | Example | Defined in |
| --- | --- | --- | --- |
| Parent requirement | `FR-<n>`, `NFR-<n>`, `OUT-<n>`, `INV-<n>` | `FR-3` | Parent PRD |
| Acceptance criterion | `<PREFIX>-<n>` | `TECH-2` | Component PRD |
| Story | `<PREFIX>-US-<n>` | `TECH-US-1` | Component PRD |
| Component requirement | `<PREFIX>-FR-<n>` | `TECH-FR-1` | Component PRD |
| Component NFR, invariant, outcome | `<PREFIX>-NFR-<n>`, `<PREFIX>-INV-<n>`, `<PREFIX>-OUT-<n>` | `TECH-INV-1` | Component PRD |
| Decision | four-digit number | ADR 0002 | `docs/adr/` |

`<PREFIX>` is two to ten uppercase letters or digits, starts with a letter, is unique in the repository, and is declared in the component PRD's `prefix` and in `sdd.config.json`. `FR`, `NFR`, `OUT`, `INV`, `US`, `AC`, `ADR`, `SPEC`, `LLD` and `PRD` are reserved. IDs are defined in the first column of a table whose first header is `ID`.

**Richer criterion IDs.** A project may also accept a richer form, such as `AM-PRIV-001-AC1`, by setting `ids.criterionPattern` in `sdd.config.json` to a regular expression whose named group `prefix` gives the component prefix. The default form is always accepted. An ID should not encode organizational scope, because moving behavior between scopes must not change its ID.

**Lifecycle rules.**

- An ID is never renumbered and never reused.
- An editorial clarification keeps the ID.
- A change to the actor, trigger, response, measurable target, control obligation or test obligation creates a new ID, and the old ID is recorded as superseded by the new one.
- A split or a merge creates new IDs; the old IDs are recorded as split or merged.
- Moving unchanged behavior between organizational scopes does not by itself create a new ID.
- An ID that leaves a PRD is recorded in that PRD's **ID history** table: `| ID | Status | Replaced by | Reason |`, with a status of `withdrawn`, `superseded`, `split` or `merged`. Rows in that table are not definitions.

spec-lint checks across every version of each PRD: an ID defined in two document families is an error; an ID that disappears without an ID history row is a warning; a criterion whose wording changed between versions is reported so a person can confirm the change is editorial.

## 11. Acceptance criteria

- Criteria are written in EARS by default: ubiquitous ("The system shall..."), event-driven ("When..."), state-driven ("While..."), unwanted behavior ("If... then..."), optional feature ("Where..."), or a combination.
- A document may use Given/When/Then instead by setting `notation: gherkin` in its front matter. One notation per document.
- Each criterion states one response, names the system as its subject, is testable as written, and carries a priority of P1, P2 or P3.
- spec-lint enforces the form and the priority on approved documents and warns on drafts.

## 12. Document conventions

**Front matter.** Every versioned document starts with YAML front matter:

| Key | Required | Values |
| --- | --- | --- |
| `title` | yes | Free text |
| `type` | yes | `vision`, `research`, `prd`, `prd-component`, `spec`, `lld`, `test-plan`, `kickoff`, `plan`, `handoff`, `runbook`, `standard` |
| `version` | yes | Must match the `-vN` in the file name |
| `status` | yes | `draft`, `in-review`, `approved`, `superseded` |
| `owner` | yes | The accountable person |
| `approved_by`, `approved` | when approved | Who approved, with role, and the date |
| `prefix` | component PRDs and LLDs | The component's ID prefix |
| `parent` | when there is one | Path of the document this derives from (kept for older documents; new documents may use `derives_from`) |
| `components` | plans, optional | Components a milestone plan covers; otherwise read from the criteria it cites |
| `supersedes` | on a next version | Path of the previous version |
| `deferred`, `excepted` | test plan only | Criteria deferred, or excepted, with the owner's approval |
| `notation` | optional | `ears` (default) or `gherkin` |
| Scope metadata | optional | Section 4 |

**Versions.** File names end in `-vN.md`. A document whose status is `approved` must not be edited. A change produces the next version with `node tools/sdd/cli.mjs new --next <path>`. The protect-approved hook blocks edits to frozen documents.

**ADRs** are numbered once (`0001-<slug>.md`), carry a status of `proposed`, `accepted`, `rejected`, `superseded` or `deprecated`, and are never versioned. `docs/adr/README.md` indexes them.

**Open questions** are written as `- [ ] Q:` and resolved as `- [x] Q:` with the answer. An approved document has no open questions and no template placeholders.

**Brownfield rationale.** Rationale inferred from existing code is tagged `[inferred]` until the owner confirms it.

## 13. Traceability and evidence

**Annotations.** A test cites the criterion it verifies in a comment of the form `@spec TECH-2`, and its title names the ID. The entry point of the behavior in code carries the same annotation: the topmost function or handler that owns the behavior, not every helper.

**What the checks prove.** The checks verify that approved criteria resolve to cited tests and behavior entry points, and they flag broken or missing structural links. They do not prove semantic equivalence or coverage of every line, so accountable human review remains required. Checks across the rest of the chain (L0 direction, L1 translation, design, tasks and handoff) are planned; today the doc map shows those links and spec-lint checks that `derives_from` paths exist.

**Evidence states.** trace-check gives each criterion one state:

| State | Meaning |
| --- | --- |
| `planned` | No test yet; the test strategy or the component's LLD maps it to planned tests |
| `test linked` | A test cites it with `@spec`; no result was read |
| `passing`, `failing` | A linked test ran, read from a JUnit XML report (`--results` or `paths.testResults`) |
| `deferred` | The owner deferred it (P2 or P3 only) |
| `excepted` | The owner accepted an exception, recorded in the approved test strategy with its reason |
| `drifted` | The verifier recorded drift for it in the trace index |
| `gap` | No test and no planned evidence |

**When evidence is required.**

| Stage | Required | Enforced by |
| --- | --- | --- |
| Before build (after Gate 1, through Gate 3) | Every approved criterion is planned, deferred or excepted | trace-check warns on a gap |
| During build (a milestone plan exists for the component) | Every approved criterion the plan names is test linked, deferred or excepted once its task is done; when the plan names no criteria of the component, every approved criterion of the component is | trace-check errors |
| At handoff | Linked tests pass, and review evidence is recorded in the handoff | trace-check errors on `failing` when a report is given; the handoff records the run |

A plan names a criterion by citing its ID; a range such as `TECH-1 to TECH-4` (or `TECH-001 to TECH-004`, keeping the zero padding) names every ID in between; the two ends differ only in their last number. Each current plan (its latest version, not superseded) is read on its own. When a task table in the plan has a Status column (whatever its criteria column is called), a criterion is due once a task that names it in a delivered column (any column but #, Task, Depends on and Status) has a status starting with `done`, `merged`, `complete` or `completed`; prose mentions elsewhere in that plan do not count, and until then the criterion is not yet due. A plan without a Status column makes every criterion it names due at once. A plan that names no criteria of a component it covers makes all of that component's criteria due.

A P1 criterion cannot be deferred. It can be excepted only by the exception authority (Section 18).

**Status lives only in derived files.** Evidence lives in `docs/trace/coverage.md`, regenerated by `trace-check --write`. The trace index (`docs/trace/index.yaml`) holds each component's audit record: scope, owner, audited date and commit, findings, disposition, drift, next action, and the governing artifact versions, which `--write` records. Approved documents never carry status. Evidence goes stale when a source file changes, and also when a governing artifact (the parent PRD, the component PRD, the SPEC, the LLD or the test strategy) is approved or changed after the last audit.

**Annotation reach.** Reach (the share of changed source files that carry at least one annotation) is reported on every pull request, and code review treats a falling number as a finding.

## 14. Drift and fixes

Verification reports a disagreement. The named human owner determines the first artifact in the delivery trace that no longer reflects approved intent. The team corrects that artifact, then updates or regenerates its dependent artifacts.

This permits a code-first correction when code violates unchanged approved intent, and it sends a flawed requirement or design back to its accountable owner.

## 15. Priority and severity

Product priority and operational severity are separate decision lenses.

**Product priority** ranks new capability before it is built.

| Priority | Meaning | Rule |
| --- | --- | --- |
| P1 | Must ship for the release to have value | First milestone; cannot be deferred |
| P2 | Should ship; the release has value without it | After P1; may be deferred with approval |
| P3 | Could ship | Backlog; re-ranked each milestone |

**Operational severity** ranks what goes wrong once something is built.

| Severity | Impact | Example | Response |
| --- | --- | --- | --- |
| S0 | Extensive | Outage, or a breach of an invariant | Immediate; runbook, fast path fix, postmortem |
| S1 | Large | Major feature malfunctioning | Urgent; fast path, postmortem |
| S2 | Moderate | Minor feature malfunctioning | Ranked against other work |
| S3 | Minor | A feature blocks a few users | Routine work |
| S4 | Negligible | Cosmetic issue | Backlog |

Support types (failure, bug, spec gap, blocker, drift) and the `sdd-triage` skill are described in the [usage guide](../guide/usage.md). A person confirms every S0 and S1.

**Combined queue (local choice).** The portable core does not require one queue; adopting organizations map both lenses into their existing portfolio and incident processes. This reference profile tests a combined ordering kept by the `planner`: S0, S1, P1, then S2 and P2, then S3 and P3, then S4.

## 16. Cascade and the size router

- A change inside one component cascades to its LLD, tests and code in the same change.
- A change that crosses components stops for a person and goes into the next SPEC version, with an ADR when the system's shape changes.
- Bugs and small changes take the short path: correct the first artifact that lost intent (Section 14), then tasks, then code. S0 and S1 support work takes the fast path, with the gates combined into one human review.

## 17. Configuration and feature flags

Every optional behavior has a flag in `sdd.config.json` under `features`. Switching a flag off must not lose data.

| Setting | Default | Effect |
| --- | --- | --- |
| `features.gateHook` | on | Blocks a skill until the artifact it builds on is approved for that component |
| `features.protectApprovedDocs` | on | Blocks edits to approved documents |
| `features.reachReport` | on | Reports annotation reach in trace-check |
| `features.divergenceProbe` | off | Enables the blind divergence probe in `sdd-clarify` |
| `features.differentialAudit` | off | Enables the bidirectional differential in `sdd-verify` |
| `approvals.requireApprover` | off | Requires `approved_by` and `approved` on approved documents |
| `ids.criterionPattern` | none | Accepts a richer criterion ID form |
| `paths.testResults` | none | JUnit XML report for passing and failing states |

Repositories adopted with `sdd adopt` also carry `adoption.mode: advisory`, which makes the checks report without failing until the owner switches to `enforced`.

## 18. Open decisions

These stay open until their owners decide. The toolkit does not settle them, and approving this standard does not decide them.

| Decision | Decided by | Status |
| --- | --- | --- |
| Where the controlled standard lives, and which authority approves it | The owning authority | Open |
| The Tech domain pilot's L2 capability and L3 Business Application | Pilot owners | Open |
| Named approvers for each gate, the exception authority, the fast path criteria and audit timing | Product and Engineering authorities | Open |
| Whether the intake checkpoint and the combined queue stay after the pilot | Pilot owners | Open |
| The license for reuse outside this repository | Repository owner, with legal review | Open |

## Changes from v1

| Area | v1 | v2 |
| --- | --- | --- |
| Stages | Layers L0 to L6 | Unnumbered delivery artifact chain; L0 to L3 reserved for organizational scope |
| Gate 0 | Gate 0, problem framing | Intake checkpoint, a local control outside the three gates |
| Ownership | A for functional requirements, criteria, test strategy and contracts | C for those; A only for prepared and derived material |
| Gates | Any approved document of the right type | Bound to the component and plan being advanced |
| Evidence | `covered` meant a test annotation exists | `test linked`, plus planned, passing, failing, deferred, excepted, drifted and gap |
| Drift | Fix the layer where intent was lost, spec first | The owner names the first artifact that lost intent; code first is allowed |
| Queue | One queue was a core rule | Two lenses; the combined queue is a local choice |
| IDs | Never renumbered or reused | Full lifecycle with an ID history table; optional richer form |
| Authority | Normative standard and constitution | Approved for this repository; controlled standard open |

## Changes from v2

| Area | v2 | v3 |
| --- | --- | --- |
| Evidence during build | Every approved criterion of a component in a milestone plan needs a test | Only the criteria the plan names, once a task that names them is done; a plan that names no criteria of a component still covers all of them |
