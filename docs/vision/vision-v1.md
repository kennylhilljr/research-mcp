---
title: "Research MCP v2 vision"
type: vision
version: 1
status: draft
owner: "Kenny Hill"
artifact_type: vision
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/prd/PRD-v4.md
date: 2026-10-22
---

# Vision and strategy (v1)

Every outcome in the [parent PRD](../prd/PRD-v5.md) traces to an outcome here. Content is carried over from [PRD-v4](../../docs-archive/prd/PRD-v4.md) and the owner decisions in [REVIEW-v1](../../docs-archive/review/REVIEW-v1.md) section 1, as amended by [ADR 0011](../adr/0011-archive-keeps-text-searchable-120-day-retention.md) and [ADR 0012](../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md).

## Why

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

Research MCP is a personal MCP server that lets Claude, Codex and OpenClaw agents search, fetch, read and cite research from many sources through one server (PRD-v4 1). Its value is horizontal reach: many sources, one server (D1). v1 has that reach but makes it hard to use (53 single-source tools, 10 to 20 calls for one cross-source question), breaks silently (three sources degraded by upstream changes, one with an announced shutdown on 2027-01-01), hides credentials and their expiry, is hard to change (one 4,613-line file), is unsafe in ways that matter on a personal Mac, and keeps one-off downloads forever (PRD-v4 2).

## For whom

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

- **The owner, through an agent** (Claude Code, Claude desktop, Codex, OpenClaw agents): one call searches many sources together and returns merged, deduplicated results instead of 10 to 20 calls with different shapes (PRD-v4 2.1, 4, G2).
- **The owner, directly**, on a lightweight local web page: sees sources, health, credentials, quotas, jobs and the cache, and answers the "archive or discard" review (PRD-v4 4, G8; D6).
- **The owner, passively**, through macOS notifications (and optionally an OpenClaw inbox message): is told when a source degrades, when a credential is expiring or invalid, and when cached papers are due for review (PRD-v4 4; D5).
- **The ECC orchestrator and coding agents**, who build v2 one work unit at a time from the repository and its docs (PRD-v4 4).

## Multi-year outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

The release metrics and targets for each outcome are in [PRD-v5](../prd/PRD-v5.md) section 1.4 (proposed in PRD-v4, not yet approved). The parent PRD uses the same IDs.

| ID | Outcome | Measure | Target | By when |
| --- | --- | --- | --- | --- |
| OUT-1 | **Breadth.** Every source and endpoint v1 calls is kept, high-value new sources are added, and coverage of any subject area grows by configuration (G1; D1; ADR 0012) | Sources registered; v1 endpoints mapped | PRD-v5 1.4 | PRD-v5 1.4 |
| OUT-2 | **One search.** A single call searches many sources and returns merged, deduplicated results with per-source status (G2; D1) | Search latency; tool calls per cross-source question | PRD-v5 1.4 | PRD-v5 1.4 |
| OUT-3 | **Cheap to maintain.** Adding, fixing or disabling a source is isolated to one module plus fixtures (G3; D5) | Files changed to add a source | PRD-v5 1.4 | PRD-v5 1.4 |
| OUT-4 | **Monitored.** The owner sees at a glance which sources work, which are degraded or down, and why (G4; D5) | Time for a state change to reach the owner | PRD-v5 1.4 | PRD-v5 1.4 |
| OUT-5 | **Credential care.** The owner is told before a credential expires and when one stops working, with the fix (G5; D5) | Notices before expiry; expired credentials without notice | PRD-v5 1.4 | PRD-v5 1.4 |
| OUT-6 | **Cache, not library.** Fetched items live 120 days, then the owner chooses archive or discard; nothing is deleted without an answer; archived items stay searchable (G6; D2; D3 as amended by ADR 0011) | Items deleted without an owner decision | PRD-v5 1.4 | PRD-v5 1.4 |
| OUT-7 | **Safe by default.** No local file read beyond the cache, no credential sent outside its origin, no secret in any output or log (G7) | Security and secret-leak tests | PRD-v5 1.4 | PRD-v5 1.4 |
| OUT-8 | **Visible.** A local web page shows sources, credentials, quotas, jobs and the cache (G8; D6) | UI pages rendering from live state | PRD-v5 1.4 | PRD-v5 1.4 |

## Strategic bets and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**Bets**

- **Merge tools, not sources.** Reach is the value; add sources where they are cheap to keep healthy (D1). Every source sits behind one adapter contract and is searched together with the others (PRD-v4 1).
- **Domain-neutral coverage.** No goal, requirement or tool is tied to one subject area; coverage comes from configuration (docs-site instances, site sets, web-search engines) (ADR 0012).
- **Maintainability and monitoring count as much as features.** Source health, credential-expiry notice and a lightweight UI are part of the product, not extras (D5; D6).
- **A working cache, not a library.** Papers are usually fetched for a one-time need (D2); they are kept 120 days, reviewed with the owner before expiry, and archived to Google Drive where they stay searchable (D3, D4; ADR 0011).
- **Rebuild, not patch.** v2 is a rebuild in a new repository; v1 stays read-only and running until cutover (PRD-v4 1; REVIEW-v1 2; ADR 0001, proposed).

**Non-goals** (PRD-v4 3.2; detail in [PRD-v5](../prd/PRD-v5.md) 1.3)

- A curated paper library, reference manager or note-taking tool.
- Remote or multi-user access.
- Scraping Google Scholar.
- Limiting coverage to one subject area.
- Free-form SQL over local files.
- Keeping v1 tool names or result shapes.

## Open questions

> **Owner:** A · **Persona:** `analyst`

- [ ] Q: The sources state release targets only (PRD-v4 3.1 and 7). Are there outcomes or targets for a horizon beyond the v2 release, and by when?
- [ ] Q: `scope_name` is `research-mcp`, but `docs/scope/scope-map.yaml` names the L3 scope `rmcp` under the key `application` and its owner is a placeholder. Which name is the scope key, and should the map be updated?
