# Research MCP v2

A local research server for MCP clients: federated scholarly and web search, identifier resolution, a document cache with review and archive, and a localhost UI. It replaces `my-research-mcp-server` (v1), which stays read-only until cutover.

## Documents

| Document | Role |
|---|---|
| [PRD v4](docs/prd/PRD-v4.md) and [component PRDs](docs/prd/components/) | Requirements: what and why |
| [SPEC v1](docs/spec/SPEC-v1.md) | The build contract: names, interfaces, formats, behavior, work breakdown |
| [HLD v3](docs/design/HLD-v3.md) | Shape and rationale |
| [TEST-PLAN v3](docs/test-plan/TEST-PLAN-v3.md) | Acceptance tests and owner checks, mapped to requirements and units |
| [ADRs](docs/adr/) | Decisions |
| [MIGRATION v2](docs/migration/MIGRATION-v2.md) | v1 to v2 migration and cutover |
| [Design review](docs/review/REVIEW-v1.md) | The review that shaped the documents |

## How it is built

By an agent team under the ECC orchestrator, one milestone at a time, from `.orchestration/plan-m0.json` (generated from SPEC 12.3 and TEST-PLAN Appendix A). Agents follow [AGENTS.md](AGENTS.md). The run itself is described in [.orchestration/PILOT-M0.md](.orchestration/PILOT-M0.md).

## History

This repository starts fresh on 2026-10-20. Its documents carry over from `my-research-mcp` at `23b3d72`, where their earlier versions and the first M0 attempt remain for reference. The low-level design became SPEC v1 here.
