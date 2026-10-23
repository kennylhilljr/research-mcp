# Research MCP v2

A local research server for MCP clients: federated scholarly and web search, identifier resolution, a document cache with review and archive, and a localhost UI. It replaces `my-research-mcp-server` (v1), which stays read-only until cutover.

## Documents

The documents follow the owner's spec-driven development framework ([ADR 0013](docs/adr/0013-adopt-spec-driven-development.md)); the [doc map](docs/README.md) lists every one with its status.

| Document | Role |
|---|---|
| [Vision](docs/vision/vision-v2.md) | Why, for whom, the outcomes |
| [PRD v8](docs/prd/PRD-v8.md) and [component PRDs](docs/prd/components/) | Requirements and acceptance criteria: what and why |
| [SPEC v5](docs/spec/SPEC-v5.md) | The system high level design |
| [LLDs](docs/lld/) | The build contract per component: names, interfaces, formats, behavior |
| [Test plan](docs/test/test-plan-v4.md) | How each criterion is verified, owner checks, exit gates |
| [M0 plan](docs/build/M0-plan-v3.md) | Work units of the first milestone |
| [ADRs](docs/adr/) | Decisions |
| [Migration cutover runbook](docs/runbooks/migration-cutover-v1.md) | v1 to v2 cutover |
| [docs-archive/](docs-archive/) | Superseded originals: PRD v4, HLD v3, SPEC v1 and v2, TEST-PLAN v3, MIGRATION v2 and the design review |

## How it is built

By an agent team of Claude roles under the ECC orchestrator, one milestone at a time, from `.orchestration/plan-m0.json` (generated from the M0 plan). Each role plays an SDD persona from `.claude/agents/`. Agents follow [AGENTS.md](AGENTS.md); the run is described in [.orchestration/PILOT-M0.md](.orchestration/PILOT-M0.md). Before a run, the owner approves the documents at the SDD gates.

## History

This repository started on 2026-10-20 with documents carried over from `my-research-mcp` at `23b3d72`. On 2026-10-22 they moved onto the SDD templates; the originals are in `docs-archive/`.
