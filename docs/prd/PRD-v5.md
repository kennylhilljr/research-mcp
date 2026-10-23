---
title: "Research MCP v2: one tool, many sources"
type: prd
version: 5
status: draft
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
supersedes: docs-archive/prd/PRD-v4.md
date: 2026-10-22
---

# Research MCP v2: one tool, many sources: parent PRD (v5)

Vision: [vision-v1](../vision/vision-v1.md). Supersedes [PRD-v4](../../docs-archive/prd/PRD-v4.md), whose content is carried over here on the SDD templates; owner decisions come from [REVIEW-v1](../../docs-archive/review/REVIEW-v1.md) section 1 and the [ADRs](../adr/). Every statement cites its source in parentheses. Earlier IDs map to new ones in section 2.11.

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

Research MCP is a personal MCP server that lets Claude, Codex and OpenClaw agents search, fetch, read and cite research from many sources through one MCP server; v2 is a rebuild (PRD-v4 1). The reasons for the rebuild are in the [vision](../vision/vision-v1.md); the problems it must solve are these (PRD-v4 2):

1. **Reach is there but hard to use.** v1 has 53 single-source tools. A question that spans sources takes 10 to 20 tool calls with different argument names and result shapes, and the same paper comes back several times.
2. **Breakage is silent.** Three sources are degraded by upstream changes today (OpenAlex, Semantic Scholar, Crossref) and one has an announced shutdown (Google Programmable Search, 2027-01-01). Nothing in v1 noticed.
3. **Credentials are invisible.** Keys sit in plaintext in three MCP client configs, can leak into chat through error messages, and nobody is told when one expires or stops working.
4. **It is hard to change.** Everything is in one 4,613-line file; adding a source touches five places.
5. **It is unsafe in ways that matter on a personal Mac:** arbitrary local file reads through SQL, keys sent to third-party hosts, downloads that go anywhere.
6. **The local corpus grows without purpose.** Papers are fetched for one-off needs but kept forever, duplicated, and never cleaned up.

**Why now.** The upstream breakage is current: the live probes of 2026-10-19 found OpenAlex keyless calls rejected for budget, Semantic Scholar bulk search ignoring `limit`, Crossref throttling clients without a contact email, and Google Programmable Search closed to new customers ahead of its shutdown on 2027-01-01 (REVIEW-v1 4; PRD-v4 2.2). The review found v1 is not a sound base for the next year of use (REVIEW-v1 2).

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| The owner, through an agent (Claude Code, Claude desktop, Codex, OpenClaw agents), using MCP tools, resources and prompts over stdio (through a shim) or loopback streamable HTTP | Ask one cross-source question and get merged results, then fetch, read and summarize the best open-access papers (PRD-v4 4) | One person; personal server (PRD-v4 1) |
| The owner, directly, on the local web UI at `http://127.0.0.1:<port>` | Check the source board, reload a key after rotating it in the Keychain, answer the "archive or discard" review (PRD-v4 4) | One person (PRD-v4 1) |
| The owner, passively, through macOS notifications and an optional OpenClaw inbox message | Be told that a token expires soon, that a source is rate limited, or that cached papers are due for review (PRD-v4 4) | One person (PRD-v4 1) |
| The ECC orchestrator and coding agents, through the repository and its docs | Build v2 one work unit at a time (PRD-v4 4) | Not stated |

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- One MCP server, reached through one daemon per Mac, with every source behind one adapter contract and searched together (PRD-v4 1; NFR-1).
- Breadth: every source and endpoint v1 calls, grown to 45 sources, including the optional, capped `web` group and the `reference` group (Library of Congress, Open Library, Wikipedia) (PRD-v4 1 and "Changes from v3"; ADR 0012).
- Federated search, work lookup, identifier normalization, dedupe, citations and integrity checks (PRD-v4 5).
- Fetch, read, cite and local search over a 120-day cache with an owner review and a searchable Google Drive archive (PRD-v4 1, 5; ADR 0011).
- Source and credential health, quotas, notifications and `doctor` (PRD-v4 5).
- A read-mostly local web UI (PRD-v4 5).
- Platform, security, packaging and CI; migration and cutover from v1 (PRD-v4 5).

| Non-goal | Why it is excluded |
| --- | --- |
| A curated paper library, reference manager or note-taking tool | Zotero does that (PRD-v4 3.2); the local index is a working cache, not a library (D2) |
| Remote or multi-user access | The server binds to loopback on the owner's Mac (PRD-v4 3.2) |
| Scraping Google Scholar | No reason stated in PRD-v4 3.2 (see 2.8). Paid web-search providers are allowed only as optional sources with a daily cap (PRD-v4 3.2; ADR 0012) |
| Limiting coverage to one subject area | Requirements are domain-neutral; coverage comes from configuration (PRD-v4 3.2; ADR 0012) |
| Free-form SQL over local files | v1's SQL tools allowed arbitrary local file reads (PRD-v4 2.5, 3.2; REVIEW-v1 3, finding 1) |
| Keeping v1 tool names or result shapes | Clients are updated at cutover (PRD-v4 3.2) |

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

Each outcome traces to the outcome of the same ID in the [vision](../vision/vision-v1.md). The metrics and targets below are carried over from PRD-v4 sections 3.1 and 7. **They were proposed for owner review and are not yet approved:** PRD-v4's status is "Draft for owner review". They are kept unchanged until the owner approves or changes them at Gate 1. PRD-v4 7 metrics are measured 30 days after cutover.

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |
| OUT-1 | **Breadth.** Sources registered, each listed on the source board; every v1 endpoint mapped to a v2 source (G1; PRD-v4 7) | About 25 sources in v1 (PRD-v4 1) | 45 or more sources registered; every v1 endpoint mapped (G1; PRD-v4 7; ADR 0012) | End of M1 (G1); 45 or more still registered 30 days after cutover (PRD-v4 7) |
| OUT-2 | **One search.** Latency of a five-source search with every source's status reported; tool calls per cross-source question (G2; PRD-v4 7) | No federated search; 10 to 20 tool calls per cross-source question (PRD-v4 2.1, 7) | Under 8 s at p95 with every source's status reported; 1 to 3 tool calls (G2; PRD-v4 7) | Tool calls: 30 days after cutover (PRD-v4 7). Latency: not stated |
| OUT-3 | **Cheap to maintain.** Files changed to add a source; time to add a new free source; test coverage on `src/` (G3; PRD-v4 7) | Adding a source touches five places in one 4,613-line file (PRD-v4 2.4); coverage 62% (REVIEW-v1 3, finding 15) | One adapter file and one fixtures folder, with no other hand-written file changed (G3); one work unit, owner estimate, agent-built (PRD-v4 7); 85% or more coverage and contract tests for every adapter (PRD-v4 7) | 30 days after cutover (PRD-v4 7) |
| OUT-4 | **Monitored.** Probe per source; time for a detected state change to reach the owner; time to report a dead daemon; share of source state changes the owner noticed before an agent hit them (G4; PRD-v4 7) | Nothing monitored; three sources degraded unnoticed (PRD-v4 2.2) | Every source has a probe; a state change reaches the owner within 15 minutes outside quiet hours; the watchdog reports a dead daemon within 15 minutes (G4); 90% or more noticed first (PRD-v4 7) | Share noticed: 30 days after cutover (PRD-v4 7). Others: not stated |
| OUT-5 | **Credential care.** Expiry notice schedule; time to an invalid-credential notice; credentials that expired without a prior notice (G5; PRD-v4 7) | Nobody is told when a credential expires or stops working (PRD-v4 2.3) | Expiring notices at 14, 7, 3 and 1 days; invalid notice within one probe cycle (G5); 0 expired without a prior notice (PRD-v4 7) | 30 days after cutover (PRD-v4 7) |
| OUT-6 | **Cache, not library.** Items deleted without a recorded owner decision (G6; PRD-v4 7) | Papers kept forever, duplicated, never cleaned up (PRD-v4 2.6) | 0 (G6; PRD-v4 7) | 30 days after cutover (PRD-v4 7) |
| OUT-7 | **Safe by default.** Security test suite result; secret-leak test coverage of error paths (G7) | Arbitrary local file reads through SQL, keys sent to third-party hosts, downloads that go anywhere (PRD-v4 2.5) | Security test suite green; secret-leak tests cover every error path (G7) | Not stated |
| OUT-8 | **Visible.** UI pages rendering from live state (G8) | Not stated | Every UI page in [PRD-ui-v3](components/PRD-ui-v3.md) renders from live state (G8) | Not stated (M3 delivers the UI pages, PRD-v4 10) |

## 1.5 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

Each invariant below restates a "never" or "nothing" statement the sources already make; none is new.

| ID | The system must never | Source (regulation, policy, contract) |
| --- | --- | --- |
| INV-1 | Delete a cached item without a recorded owner decision | D3 ("Nothing is deleted without an answer"); G6; ADR 0011 |
| INV-2 | Put a secret value in a tool result, error, log, UI page, notification or test snapshot | NFR-04 (now NFR-4); G7 |
| INV-3 | Send a credential outside its origin | G7; PRD-v4 2.5 |
| INV-4 | Read a local file beyond the cache | G7; PRD-v4 2.5, 3.2 |
| INV-5 | Listen on a non-loopback address | NFR-07 (now NFR-7); PRD-v4 3.2 |
| INV-6 | Hold a secret at rest outside the Keychain, except the owner's Google sign-in for Vertex AI Search, which `gcloud` stores and v2 never copies | NFR-03 (now NFR-3); ADR 0012 decision 5 |
| INV-7 | Remove an item from the cache before its archive copy is verified | PRD-v4 12 (Drive sync risk) |
| INV-8 | Modify the Drive archive files during an archive rebuild | ADR 0011 decision 3 |
| INV-9 | Call a web-search source unless the caller asked for it, or put one in the default fan-out | ADR 0012 decision 4; PRD-v4 12 |

## 1.6 Known constraints and decisions already made

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

**Constraints** (as stated in the sources)

- Personal server on the owner's Mac, bound to loopback (PRD-v4 1, 3.2; NFR-7).
- One launchd daemon (`research-mcpd`) running one Python process, with two SQLite files (`state.db`, `cache.db`) in Application Support, backed up nightly; clients start `research-mcp stdio`, a shim that relays to the daemon (PRD-v4 8).
- Secrets live in the macOS Keychain (NFR-3).
- New repository `my-research-mcp`; v1 (`my-research-mcp-server`) is read-only until cutover (PRD-v4 header).
- Upstream terms are respected, including arXiv's 1 request per 3 seconds (NFR-8).
- Google Programmable Search shuts down on 2027-01-01 (ADR 0012 decision 3; REVIEW-v1 4).
- v2 is built by the ECC orchestrator one work unit at a time (PRD-v4 4).

**Owner decisions** (REVIEW-v1 1, as amended)

| Decision | As it stands | Source |
| --- | --- | --- |
| D1 | The value of the server is its horizontal reach: many sources, one server. Merge tools, not sources; add sources where they are cheap to keep healthy. | REVIEW-v1 1 |
| D2 | Papers and documents are usually fetched for a one-time need; the local index is a working cache, not a library. | REVIEW-v1 1 |
| D3 | **Amended.** Cached items are kept 120 days from fetch (not 30). Before an item expires the owner is asked whether to archive or discard it; nothing is deleted without an answer. Archived items keep their text and embeddings and stay searchable. | REVIEW-v1 1; [ADR 0011](../adr/0011-archive-keeps-text-searchable-120-day-retention.md) |
| D4 | The archive is the owner's Google Drive, through the locally synced folder (`My Drive/Research Archive/<year>/`). | REVIEW-v1 1 |
| D5 | v2 must be maintainable and monitored, and must notify the owner when a credential is expiring or invalid so it can be rotated. | REVIEW-v1 1 |
| D6 | v2 has a lightweight local UI to see sources, health, credentials, jobs and the cache. | REVIEW-v1 1 |
| D7 | **Reversed.** Web search is not decommissioned: Vertex AI Search, Brave, SerpAPI and Google Programmable Search return as the optional source group `web`, each off until configured, capped per day, and used only when asked for. | REVIEW-v1 1; [ADR 0012](../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md) |
| D8 | "Penn" means UPenn ScholarlyCommons. | REVIEW-v1 1 |

**Other decisions made**

- **O1 closed:** keep all four web-search providers as optional, capped sources (PRD-v4 11; ADR 0012).
- **Domain-neutral requirements; every v1 endpoint kept;** the undocumented AWS and Microsoft Learn site-search endpoints give way to the vendors' official MCP servers; the v1 docs-domain list and crawl projects ship as default configuration (ADR 0012; PRD-v4 "Earlier changes (v3)").
- **Reference group:** Library of Congress, Open Library and Wikipedia join as a free, keyless `reference` group, taking the catalog to 45 sources; they come from the owner's separate K-12 teacher server, which is not migrated or changed (owner decision of 2026-10-19; PRD-v4 "Changes from v3").

**ADRs**

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](../adr/0001-new-repo-v1-read-only.md) | v2 is a new repository; v1 stays read-only and running until cutover | Proposed |
| [0002](../adr/0002-one-daemon-with-stdio-shims.md) | One daemon per Mac; clients use a stdio shim | Proposed |
| [0003](../adr/0003-secrets-in-keychain.md) | Secrets live in the macOS Keychain; configuration holds references | Proposed |
| [0004](../adr/0004-modular-core-composition-root.md) | Modular core built by one composition root; no work at import | Proposed |
| [0005](../adr/0005-async-io-cpu-off-loop.md) | Async I/O end to end; CPU work in worker processes | Proposed |
| [0006](../adr/0006-source-adapter-contract.md) | Every source is an adapter with a declarative `SourceSpec` | Proposed |
| [0007](../adr/0007-cache-lifecycle-and-drive-archive.md) | Cache with owner review; archive to the Google Drive sync folder (amended by 0011) | Proposed |
| [0008](../adr/0008-sqlite-stores-and-vectors.md) | Two SQLite files; vectors stored in SQLite | Proposed |
| [0009](../adr/0009-no-sql-untrusted-content.md) | No free-form SQL; fetched content is labeled untrusted | Proposed |
| [0010](../adr/0010-localhost-ui-stack.md) | The UI is server-rendered inside the daemon | Proposed |
| [0011](../adr/0011-archive-keeps-text-searchable-120-day-retention.md) | 120-day retention; archived papers keep their text and embeddings and stay searchable | Accepted (2026-10-19) |
| [0012](../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md) | Domain-neutral scope; every v1 endpoint kept; web search as optional, capped sources | Accepted (2026-10-19) |
| [0013](../adr/0013-adopt-spec-driven-development.md) | Adopt spec-driven development | Proposed |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

---

## 2.1 Components

> **Owner:** C · **Persona:** `architect` drafts; the owner confirms

PRD-v4 section 5 had seven components, with platform and security in one. This version lists Security as its own component. Each component has one LLD.

| Component | Prefix | Component PRD | LLD | Owner |
| --- | --- | --- | --- | --- |
| Platform | PLAT | [PRD-platform-v3](components/PRD-platform-v3.md) | [LLD-platform-v1](../lld/LLD-platform-v1.md) | Kenny Hill |
| Sources | SRC | [PRD-sources-v4](components/PRD-sources-v4.md) | [LLD-sources-v1](../lld/LLD-sources-v1.md) | Kenny Hill |
| Search and identity | SRCH | [PRD-search-v2](components/PRD-search-v2.md) | [LLD-search-v1](../lld/LLD-search-v1.md) | Kenny Hill |
| Retrieval and cache | CACHE | [PRD-cache-v3](components/PRD-cache-v3.md) | [LLD-cache-v1](../lld/LLD-cache-v1.md) | Kenny Hill |
| Health and credentials | HLTH | [PRD-health-v3](components/PRD-health-v3.md) | [LLD-health-v1](../lld/LLD-health-v1.md) | Kenny Hill |
| Local UI | UI | [PRD-ui-v3](components/PRD-ui-v3.md) | [LLD-ui-v1](../lld/LLD-ui-v1.md) | Kenny Hill |
| Migration and cutover | MIG | [PRD-migration-v4](components/PRD-migration-v4.md) | [LLD-migration-v1](../lld/LLD-migration-v1.md) | Kenny Hill |
| Security | SEC | [PRD-security-v1](components/PRD-security-v1.md) | [LLD-security-v1](../lld/LLD-security-v1.md) | Kenny Hill |

## 2.2 Functional requirement index

> **Owner:** C · **Persona:** `product-writer` drafts wording; the owner selects and approves · **Seed question:** 3

No parent `FR-n` IDs exist: the functional requirements live in each component PRD's section 2.4, with that component's prefix. Each component requirement traces to the outcome (`OUT-n`) and NFR (`NFR-n`) IDs in this document. Priorities are set by the owner in the component PRDs.

| Component | Requirements | Where | Traces to |
| --- | --- | --- | --- |
| Platform | `PLAT-FR-n` | [PRD-platform-v3](components/PRD-platform-v3.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Sources | `SRC-FR-n` | [PRD-sources-v4](components/PRD-sources-v4.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Search and identity | `SRCH-FR-n` | [PRD-search-v2](components/PRD-search-v2.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Retrieval and cache | `CACHE-FR-n` | [PRD-cache-v3](components/PRD-cache-v3.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Health and credentials | `HLTH-FR-n` | [PRD-health-v3](components/PRD-health-v3.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Local UI | `UI-FR-n` | [PRD-ui-v3](components/PRD-ui-v3.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Migration and cutover | `MIG-FR-n` | [PRD-migration-v4](components/PRD-migration-v4.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Security | none yet; its criteria `SEC-n` cite other components' requirements and parent NFRs | [PRD-security-v1](components/PRD-security-v1.md) 2.4 | NFR IDs, cited per criterion |

## 2.3 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

Quality and target text are carried over from PRD-v4 section 6 (proposed, not yet approved; see 1.4). The "How it is measured" column is the product writer's proposal, marked "Proposed", for the owner and the test plan to confirm.

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |
| NFR-1 | Single process | One daemon per Mac owns all HTTP clients, rate limiters, stores and the scheduler. MCP clients connect through a thin stdio shim or loopback HTTP ([ADR 0002](../adr/0002-one-daemon-with-stdio-shims.md)). | Proposed: a test connects two clients and confirms they share one daemon and one set of rate limiters |
| NFR-2 | Async | No tool blocks the event loop. Network I/O is async; PDF parsing, extraction and embedding run in worker processes ([ADR 0005](../adr/0005-async-io-cpu-off-loop.md)). | Proposed: a test confirms no tool call blocks the event loop and that CPU work runs in a worker process |
| NFR-3 | No secrets at rest outside the Keychain | Config files hold references only; this includes the daemon token and any webhook token ([ADR 0003](../adr/0003-secrets-in-keychain.md)). The one exception is the owner's Google sign-in for Vertex AI Search, which `gcloud` stores and v2 never copies ([ADR 0012](../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md)). | Proposed: a scan of config files and the data folder finds only Keychain references |
| NFR-4 | No secret in any output | Tool results, errors, logs, UI pages, notifications and test snapshots never contain a secret value. | Proposed: secret-leak tests cover every error path and every output surface (G7) |
| NFR-5 | Bounded output | Every tool result fits a byte budget (default 64 KB) and pages with a cursor beyond it. | Proposed: a test confirms every tool result is within the budget and returns a cursor when there is more |
| NFR-6 | Untrusted content is labeled | Text fetched from the internet is returned inside an envelope marked untrusted ([ADR 0009](../adr/0009-no-sql-untrusted-content.md)). | Proposed: a test confirms every tool that returns fetched text wraps it in the untrusted envelope |
| NFR-7 | Loopback only | Nothing listens on a non-loopback address; every HTTP request except the `/healthz` and `/readyz` checks needs a bearer token or a UI session. | Proposed: a test confirms every listener is on loopback and every other route rejects a request without a token or session |
| NFR-8 | Respect upstream terms | Per-source rate limits are global across clients; contact email and user agent are sent where asked; arXiv's 1 request per 3 seconds is honored. | Proposed: a test confirms limits are shared across clients and arXiv calls are at least 3 seconds apart |
| NFR-9 | Testable offline | The default test run makes no network calls. Live checks are opt-in. | Proposed: the default test run passes with the network blocked |
| NFR-10 | Docs follow code | Tool and source inventories are generated from the registry, never hand-maintained. | Proposed: a check confirms the published inventories match the registry |
| NFR-11 | Prose style | Documents and UI text use no em dashes or en dashes. | Proposed: a lint over docs and UI templates finds no em dash or en dash |

## 2.4 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

The sources do not name a classification scheme; the column records only what they state (see 2.8).

| Data | Classification | Source or owner | Retention |
| --- | --- | --- | --- |
| API keys, the daemon token and any webhook token | Secret (NFR-3, NFR-4) | macOS Keychain; config holds references (NFR-3; ADR 0003) | Not stated |
| The owner's Google sign-in for Vertex AI Search | Secret (ADR 0012 decision 5) | `gcloud` owns the Application Default Credentials file; v2 keeps a short-lived access token in memory only (ADR 0012 decision 5) | Not stored by v2 |
| Fetched papers and documents: files, extracted text, chunks, full-text entries, embeddings | Untrusted content (NFR-6); otherwise not stated | Upstream sources; `cache.db` (PRD-v4 8; ADR 0011) | 120 days from fetch; keep, unpin, undo and collection changes grant a fresh 120 days; pinned and archived items never expire (ADR 0011) |
| Archived papers | Not stated | File and sidecar in `My Drive/Research Archive/<year>/`; text and embeddings stay in `cache.db` (D4; ADR 0011) | Never expire (ADR 0011 decision 4) |
| Discarded items | Not stated | Cache | 7-day trash, proposed in open decision O8 (PRD-v4 11) |
| Daemon state (`state.db`) | Not stated | Application Support, backed up nightly (PRD-v4 8) | Not stated |
| Logs | Must contain no secret (NFR-4) | Daemon | Not stated |
| v1 corpus (`~/arxiv-papers`, 307 MB) | Not stated | Owner's Mac; read-only; optional import with a merge report (REVIEW-v1 5) | Not stated |

## 2.5 Integrations and owners

> **Owner:** H confirms owners · **Persona:** `architect` may draft · **Seed question:** 8

Owners and SLAs are not stated in the sources (see 2.8).

| System | Owner | Relationship | SLA |
| --- | --- | --- | --- |
| Upstream research sources (45, including the `web` and `reference` groups) | Each upstream provider (to confirm) | v2 calls them through one adapter contract, within their terms and rate limits (PRD-v4 1; NFR-8; ADR 0012) | Not stated |
| AWS and Microsoft Learn official MCP servers | The vendors (to confirm) | Upstream sources replacing v1's undocumented site-search endpoints (ADR 0012 decision 2; REVIEW-v1 4) | Not stated |
| MCP clients: Claude Code, Claude desktop, Codex, OpenClaw agents | Not stated | Connect through the stdio shim or loopback HTTP; client configs switched at cutover (PRD-v4 4, 10) | Not stated |
| macOS Keychain | Not stated | Holds every secret; read through `/usr/bin/security` with a timeout (NFR-3; PRD-v4 12) | Not stated |
| launchd | Not stated | Runs the daemon (PRD-v4 8) | Not stated |
| macOS notifications and the optional OpenClaw inbox webhook | Not stated | Notification channels (PRD-v4 4; O5) | Not stated |
| Google Drive sync folder | Not stated | Archive target (D4; ADR 0011) | Not stated |
| `gcloud` and Vertex AI Search | Not stated | Short-lived token for `discoveryengine.googleapis.com`; token refresh only to `oauth2.googleapis.com` (ADR 0012) | Not stated |
| v1 server (`my-research-mcp-server`) | Not stated | Read-only and running until cutover; source of the credential import and optional corpus import (PRD-v4 header, 10; ADR 0001) | Not stated |
| ECC orchestrator | Not stated | Builds v2 one work unit at a time (PRD-v4 4) | Not stated |

## 2.6 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | v1 stays read-only and running until cutover (PRD-v4 header; ADR 0001, proposed). Cutover (M4) switches client configs; v1 is archived after 14 days of daily use on v2 with no fallback to v1 (PRD-v4 10). |
| Conditions that halt the rollout | Not stated (see 2.8) |
| Support owner and escalation path | Not stated (see 2.8) |
| Response targets by severity (S0 to S4) | Not stated (see 2.8). Detection targets are in OUT-4 and OUT-5. |

## 2.7 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

From PRD-v4 sections 7 and 10:

- Every milestone's exit in 2.9 is met, ending with M4: 14 days of daily use on v2 with no fallback to v1, then v1 archived (PRD-v4 10).
- The success metrics in 1.4 are measured 30 days after cutover (PRD-v4 7).

Whether done means the M4 exit alone or also the 30-day metrics is open (see 2.8).

## 2.8 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves

**Assumptions**

- PRD-v4 7 metrics are attached to the closest outcome in 1.4 by the product writer: tool calls to OUT-2, coverage and time to add a source to OUT-3, share noticed to OUT-4. The owner should confirm the placement.
- The "How it is measured" column in 2.3 is a proposal, not a target.

**Open decisions carried from PRD-v4 section 11** (agent recommendation as context)

- [ ] Q: O2. Register free OpenAlex and Semantic Scholar keys? Recommendation: yes; OpenAlex is unusable without one (PRD-v4 11; REVIEW-v1 7).
- [ ] Q: O3. Which PDF parser? Recommendation: PyMuPDF in a worker process (best extraction; AGPL, judged acceptable for personal, non-distributed use) (PRD-v4 11; REVIEW-v1 7).
- [ ] Q: O4. Any SQL or dataset tool? Recommendation: none in the first release; revisit if `~/research-datasets` is still used (PRD-v4 11; REVIEW-v1 7).
- [ ] Q: O5. A second notification channel besides macOS notifications? Recommendation: the OpenClaw inbox through a configurable webhook (PRD-v4 11; REVIEW-v1 7).
- [ ] Q: O6. Run the AWS and Microsoft Learn MCP servers through v2 as sources, or add them to clients separately? Recommendation: through v2, so they appear on the source board and in federated search (PRD-v4 11; REVIEW-v1 7). ADR 0012 decision 2 already maps them to v2 sources; the owner may be able to close this.
- [ ] Q: O7. Retention fixed at 120 days from fetch, or 120 days from last use? Recommendation: fixed from fetch; predictable (PRD-v4 11). ADR 0011 (accepted) already says "counted from fetch", with keep, unpin, undo and collection changes granting a fresh 120 days; the owner may be able to close this.
- [ ] Q: O8. Review timing: ask 3 days before expiry, re-ask unanswered items after 7 days, and send discards to a 7-day trash? Recommendation: accept (PRD-v4 11). ADR 0011 (accepted) already states the first two; the 7-day trash is the open part.

**Questions raised while moving PRD-v4 onto the template**

- [ ] Q: Does the owner approve the numeric targets in 1.4 and 2.3 as written in PRD-v4, or change any of them?
- [ ] Q: What are the target dates for the milestones in 2.9, and by when must OUT-2 latency, OUT-4 (other than the share noticed), OUT-7 and OUT-8 be met?
- [ ] Q: What are the availability and scale targets (seed question 6)? PRD-v4 states latency only for a five-source search.
- [ ] Q: What is the baseline for OUT-8 (does v1 have any UI)?
- [ ] Q: Why is scraping Google Scholar a non-goal (1.3)? PRD-v4 states no reason.
- [ ] Q: Are the invariants in 1.5 complete and correctly worded, and are there others (for example, never modifying v1 or `~/arxiv-papers` before cutover)?
- [ ] Q: What classification scheme applies to the data in 2.4, and what is the retention of credentials, `state.db`, logs, nightly backups and the v1 corpus after import?
- [ ] Q: Who owns each integration in 2.5, and are there SLAs?
- [ ] Q: What conditions halt the rollout, who supports v2 and how is it escalated, and what are the response targets by severity (2.6)?
- [ ] Q: Is the release done at the M4 exit, or only after the 30-day metrics in 1.4 are met (2.7)?
- [ ] Q: ADRs 0001 to 0010 say they are accepted when the owner approves the PRD. Does Gate 1 approval of this PRD accept them, or does the owner decide each one?
- [ ] Q: Which option of ADR 0013 (adopt spec-driven development) does the owner choose?
- [ ] Q: `scope_name` is `research-mcp`, but `docs/scope/scope-map.yaml` names the L3 scope `rmcp` under the key `application`. Which is the scope key?

## 2.9 Milestones

> **Owner:** H · **Persona:** none (`planner` drafts the milestone plans)

Carried over from PRD-v4 section 10. No dates are stated (see 2.8).

| Milestone | Outcome | Exit |
| --- | --- | --- |
| **M0 Foundation** (ECC pilot) | Repo, settings, Keychain secrets, safe HTTP client with redaction, state store, adapter contract and registry, three reference adapters (arXiv, Crossref, OpenAlex), federated `search`, `get_work`, `list_sources`, daemon, stdio shim, launchd install, CI. | All M0 tests green; a client can search three sources through the shim on the owner's Mac. |
| **M1 Reach and health** | Every remaining v1 source ported and the new sources added, each with fixtures and a probe; citations, integrity checks; health states, credential states, quota tracking, notifications, `doctor`. | 45 or more sources registered, every v1 endpoint mapped; source board data available through `research://sources`; notifications verified on the Mac. |
| **M2 Retrieval and cache** | `fetch`, `read`, `search_cache`, `cite`, collections, extraction and chunking, embeddings, the 120-day lifecycle, the review, the searchable Drive archive and its rebuild job, disk monitoring. | Lifecycle tests green; one real archive written to Drive and verified. |
| **M3 Local UI** | All UI pages. | UI acceptance tests green; owner walkthrough. |
| **M4 Cutover** | Credential import from v1 client configs into Keychain, optional corpus import, client configs switched, v1 stopped. | 14 days of daily use on v2 with no fallback to v1; then v1 archived. |

## 2.10 Risks

> **Owner:** H · **Persona:** none

Carried over from PRD-v4 section 12.

| Risk | Mitigation |
| --- | --- |
| Upstream APIs change faster than one person can follow. | Probes check response shape, not just status; recorded fixtures make breakage visible in tests; each source can be disabled with a flag. |
| Metered sources (OpenAlex budget, web-search providers) run out mid-task or cost more than expected. | Budget tracking with `quota_low`, `rate_limited` and `budget_exhausted` states; federation skips exhausted sources and says so; web-search sources are off until configured, capped per day, and never in the default fan-out. |
| Keychain locked or unreadable (for example right after login). | Reads go through `/usr/bin/security` with a timeout; a locked Keychain is one `keychain_locked` state and one notification, not a notice per key; `doctor` gives the fix. |
| Drive sync folder unavailable, blocked by macOS privacy controls, or not uploading. | Install performs the first archive write in the foreground so the privacy prompt appears; `doctor` checks access; local fallback with a warning and reconcile; nothing leaves the cache until the archive copy is verified; upload state is checked and a stalled upload is reported. |
| PyMuPDF crashes on hostile PDFs. | Parsing in a worker process with CPU, memory, page and time limits. |
| Scope creep toward a library manager. | Non-goals in section 1.3; collections stay minimal. |

## 2.11 Earlier IDs

> **Owner:** A · **Persona:** `product-writer`

PRD-v4 IDs and the IDs that replace them. The wording and targets are unchanged.

| Earlier ID | New ID |
| --- | --- |
| G1 | OUT-1 |
| G2 | OUT-2 |
| G3 | OUT-3 |
| G4 | OUT-4 |
| G5 | OUT-5 |
| G6 | OUT-6 |
| G7 | OUT-7 |
| G8 | OUT-8 |
| NFR-01 | NFR-1 |
| NFR-02 | NFR-2 |
| NFR-03 | NFR-3 |
| NFR-04 | NFR-4 |
| NFR-05 | NFR-5 |
| NFR-06 | NFR-6 |
| NFR-07 | NFR-7 |
| NFR-08 | NFR-8 |
| NFR-09 | NFR-9 |
| NFR-10 | NFR-10 |
| NFR-11 | NFR-11 |

### Gate 1: Requirements approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |
