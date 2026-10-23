---
title: "Research MCP v2: one tool, many sources"
type: prd
version: 7
status: approved
approved_by: "Kenny Hill (Product)"
approved: 2026-10-22
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
supersedes: docs/prd/PRD-v6.md
derives_from: docs-archive/prd/PRD-v4.md
date: 2026-10-22
---

# Research MCP v2: one tool, many sources: parent PRD (v7)

Vision: [vision-v2](../vision/vision-v2.md). Supersedes [PRD-v6](PRD-v6.md). [PRD-v5](PRD-v5.md) carried [PRD-v4](../../docs-archive/prd/PRD-v4.md) onto the SDD templates; version 6 recorded the owner's intake answers of 2026-10-22, and version 7 records his Gate 1 answers of the same day (the NFR targets, `cite` in M1, clients through the shim only, backup and log retention, the scrub backup exception, a breach of any invariant as a halt condition, and the component PRD versions). Owner answers are cited as "owner decision, 2026-10-22"; owner decisions come from [REVIEW-v1](../../docs-archive/review/REVIEW-v1.md) section 1 and the [ADRs](../adr/). Every statement cites its source in parentheses. Earlier IDs map to new ones in section 2.11.

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

Research MCP is a personal MCP server that lets Claude, Codex and OpenClaw agents search, fetch, read and cite research from many sources through one MCP server; v2 is a rebuild (PRD-v4 1). The reasons for the rebuild are in the [vision](../vision/vision-v2.md); the problems it must solve are these (PRD-v4 2):

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
| The owner, through an agent (Claude Code, Claude desktop, Codex, OpenClaw agents), using MCP tools, resources and prompts over stdio through the shim, which relays to the daemon over loopback streamable HTTP; clients never hold the daemon token (PLAT-FR-2; ADR 0003; owner decision, 2026-10-22) | Ask one cross-source question and get merged results, then fetch, read and summarize the best open-access papers (PRD-v4 4) | One person; personal server (PRD-v4 1) |
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
| Scraping Google Scholar | Not needed: OpenAlex, Semantic Scholar, Crossref and the other scholarly sources cover it (owner decision, 2026-10-22). Paid web-search providers are allowed only as optional sources with a daily cap (PRD-v4 3.2; ADR 0012) |
| Limiting coverage to one subject area | Requirements are domain-neutral; coverage comes from configuration (PRD-v4 3.2; ADR 0012) |
| Free-form SQL over local files | v1's SQL tools allowed arbitrary local file reads (PRD-v4 2.5, 3.2; REVIEW-v1 3, finding 1) |
| Keeping v1 tool names or result shapes | Clients are updated at cutover (PRD-v4 3.2) |

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

Each outcome traces to the outcome of the same ID in the [vision](../vision/vision-v2.md). The metrics and targets below are carried over from PRD-v4 sections 3.1 and 7 and were approved by the owner as written (owner decision, 2026-10-22). There are no calendar dates: a target with no 30-day measure is due at the exit of the milestone in 2.9 that delivers it (owner decision, 2026-10-22). PRD-v4 7 metrics are measured 30 days after cutover.

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |
| OUT-1 | **Breadth.** Sources registered, each listed on the source board; every v1 endpoint mapped to a v2 source (G1; PRD-v4 7) | About 25 sources in v1 (PRD-v4 1) | 45 or more sources registered; every v1 endpoint mapped (G1; PRD-v4 7; ADR 0012) | End of M1 (G1); 45 or more still registered 30 days after cutover (PRD-v4 7) |
| OUT-2 | **One search.** Latency of a five-source search with every source's status reported; tool calls per cross-source question (G2; PRD-v4 7) | No federated search; 10 to 20 tool calls per cross-source question (PRD-v4 2.1, 7) | Under 8 s at p95 with every source's status reported; 1 to 3 tool calls (G2; PRD-v4 7) | Tool calls: 30 days after cutover (PRD-v4 7). Latency: M1 exit, the first milestone with five or more sources (owner decision, 2026-10-22) |
| OUT-3 | **Cheap to maintain.** Files changed to add a source; time to add a new free source; test coverage on `src/` (G3; PRD-v4 7) | Adding a source touches five places in one 4,613-line file (PRD-v4 2.4); coverage 62% (REVIEW-v1 3, finding 15) | One adapter file and one fixtures folder, with no other hand-written file changed (G3); one work unit, owner estimate, agent-built (PRD-v4 7); 85% or more coverage and contract tests for every adapter (PRD-v4 7) | 30 days after cutover (PRD-v4 7) |
| OUT-4 | **Monitored.** Probe per source; time for a detected state change to reach the owner; time to report a dead daemon; share of source state changes the owner noticed before an agent hit them (G4; PRD-v4 7) | Nothing monitored; three sources degraded unnoticed (PRD-v4 2.2) | Every source has a probe; a state change reaches the owner within 15 minutes outside quiet hours; the watchdog reports a dead daemon within 15 minutes (G4); 90% or more noticed first (PRD-v4 7) | Share noticed: 30 days after cutover (PRD-v4 7). Others: M1 exit, which delivers probes, health states and notifications (owner decision, 2026-10-22) |
| OUT-5 | **Credential care.** Expiry notice schedule; time to an invalid-credential notice; credentials that expired without a prior notice (G5; PRD-v4 7) | Nobody is told when a credential expires or stops working (PRD-v4 2.3) | Expiring notices at 14, 7, 3 and 1 days; invalid notice within one probe cycle (G5); 0 expired without a prior notice (PRD-v4 7) | 30 days after cutover (PRD-v4 7) |
| OUT-6 | **Cache, not library.** Items deleted without a recorded owner decision (G6; PRD-v4 7) | Papers kept forever, duplicated, never cleaned up (PRD-v4 2.6) | 0 (G6; PRD-v4 7) | 30 days after cutover (PRD-v4 7) |
| OUT-7 | **Safe by default.** Security test suite result; secret-leak test coverage of error paths (G7) | Arbitrary local file reads through SQL, keys sent to third-party hosts, downloads that go anywhere (PRD-v4 2.5) | Security test suite green; secret-leak tests cover every error path (G7) | M2 exit, after fetch and the cache add their paths; green at every milestone exit (owner decision, 2026-10-22) |
| OUT-8 | **Visible.** UI pages rendering from live state (G8) | No UI in v1 (owner decision, 2026-10-22) | Every UI page in [PRD-ui-v4](components/PRD-ui-v4.md) renders from live state (G8) | M3 exit, which delivers the UI pages (PRD-v4 10; owner decision, 2026-10-22) |

## 1.5 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

INV-1 to INV-9 restate a "never" or "nothing" statement the sources already make. The owner confirmed them and added INV-10 (owner decision, 2026-10-22).

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
| INV-10 | Modify v1 (`my-research-mcp-server`) or `~/arxiv-papers` before cutover; v1 data is read only through the legacy import job | Owner decision, 2026-10-22; ADR 0001; AGENTS.md |

**Approved exception.** The scrub backups that `scrub-client-configs` writes hold plaintext v1 keys, outside the Keychain. The owner approved them as an exception to INV-6 and NFR-3 that lasts until v1 is retired; they are written owner-only and deleted at retirement (MIG-FR-26; test plan section 4; owner decision, 2026-10-22 at Gate 1). INV-6 itself is unchanged.

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
- **O2 closed:** register free OpenAlex and Semantic Scholar keys; OpenAlex is unusable without one (PRD-v4 11; owner decision, 2026-10-22).
- **O3 closed:** PDFs are parsed with PyMuPDF in a worker process; its AGPL license is acceptable for personal, non-distributed use (PRD-v4 11; owner decision, 2026-10-22).
- **O4 closed:** no SQL or dataset tool in the first release; revisit if `~/research-datasets` is still used (PRD-v4 11; owner decision, 2026-10-22).
- **O5 closed:** the second notification channel is the OpenClaw inbox, through a configurable webhook (PRD-v4 11; owner decision, 2026-10-22).
- **O6 closed:** the AWS and Microsoft Learn MCP servers run through v2 as sources, so they appear on the source board and in federated search (ADR 0012 decision 2; owner decision, 2026-10-22).
- **O7 closed:** retention is 120 days counted from fetch; keep, unpin, undo and collection changes grant a fresh 120 days (ADR 0011; owner decision, 2026-10-22).
- **O8 closed:** the review asks 3 days before expiry and re-asks unanswered items after 7 days (ADR 0011); discarded items go to a trash for 7 days before deletion (owner decision, 2026-10-22).
- **Domain-neutral requirements; every v1 endpoint kept;** the undocumented AWS and Microsoft Learn site-search endpoints give way to the vendors' official MCP servers; the v1 docs-domain list and crawl projects ship as default configuration (ADR 0012; PRD-v4 "Earlier changes (v3)").
- **Reference group:** Library of Congress, Open Library and Wikipedia join as a free, keyless `reference` group, taking the catalog to 45 sources; they come from the owner's separate K-12 teacher server, which is not migrated or changed (owner decision of 2026-10-19; PRD-v4 "Changes from v3").

**ADRs**

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](../adr/0001-new-repo-v1-read-only.md) | v2 is a new repository; v1 stays read-only and running until cutover | Accepted (2026-10-22, with Gate 1 approval of this PRD) |
| [0002](../adr/0002-one-daemon-with-stdio-shims.md) | One daemon per Mac; clients use a stdio shim | Accepted (2026-10-22, with Gate 1 approval of this PRD) |
| [0003](../adr/0003-secrets-in-keychain.md) | Secrets live in the macOS Keychain; configuration holds references | Accepted (2026-10-22, with Gate 1 approval of this PRD) |
| [0004](../adr/0004-modular-core-composition-root.md) | Modular core built by one composition root; no work at import | Accepted (2026-10-22, with Gate 1 approval of this PRD) |
| [0005](../adr/0005-async-io-cpu-off-loop.md) | Async I/O end to end; CPU work in worker processes | Accepted (2026-10-22, with Gate 1 approval of this PRD) |
| [0006](../adr/0006-source-adapter-contract.md) | Every source is an adapter with a declarative `SourceSpec` | Accepted (2026-10-22, with Gate 1 approval of this PRD) |
| [0007](../adr/0007-cache-lifecycle-and-drive-archive.md) | Cache with owner review; archive to the Google Drive sync folder (amended by 0011: 120 days, not 30) | Accepted (2026-10-22, with Gate 1 approval of this PRD) |
| [0008](../adr/0008-sqlite-stores-and-vectors.md) | Two SQLite files; vectors stored in SQLite | Accepted (2026-10-22, with Gate 1 approval of this PRD) |
| [0009](../adr/0009-no-sql-untrusted-content.md) | No free-form SQL; fetched content is labeled untrusted | Accepted (2026-10-22, with Gate 1 approval of this PRD) |
| [0010](../adr/0010-localhost-ui-stack.md) | The UI is server-rendered inside the daemon | Accepted (2026-10-22, with Gate 1 approval of this PRD) |
| [0011](../adr/0011-archive-keeps-text-searchable-120-day-retention.md) | 120-day retention; archived papers keep their text and embeddings and stay searchable | Accepted (2026-10-19) |
| [0012](../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md) | Domain-neutral scope; every v1 endpoint kept; web search as optional, capped sources | Accepted (2026-10-19) |
| [0013](../adr/0013-adopt-spec-driven-development.md) | Adopt spec-driven development fully, before the next build (option 2) | Accepted (2026-10-22) |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| Kenny Hill (Product) | 2026-10-22 | Approved in chat on PRD-v6; recorded by Claude in the owner's name at his direction. The v7 changes to 1.2 and 1.5 are the owner's Gate 1 decisions of the same day |

---

## 2.1 Components

> **Owner:** C · **Persona:** `architect` drafts; the owner confirms

PRD-v4 section 5 had seven components, with platform and security in one. This version lists Security as its own component. Each component has one LLD.

| Component | Prefix | Component PRD | LLD | Owner |
| --- | --- | --- | --- | --- |
| Platform | PLAT | [PRD-platform-v4](components/PRD-platform-v4.md) | [LLD-platform-v1](../lld/LLD-platform-v1.md) | Kenny Hill |
| Sources | SRC | [PRD-sources-v5](components/PRD-sources-v5.md) | [LLD-sources-v1](../lld/LLD-sources-v1.md) | Kenny Hill |
| Search and identity | SRCH | [PRD-search-v3](components/PRD-search-v3.md) | [LLD-search-v1](../lld/LLD-search-v1.md) | Kenny Hill |
| Retrieval and cache | CACHE | [PRD-cache-v4](components/PRD-cache-v4.md) | [LLD-cache-v1](../lld/LLD-cache-v1.md) | Kenny Hill |
| Health and credentials | HLTH | [PRD-health-v4](components/PRD-health-v4.md) | [LLD-health-v1](../lld/LLD-health-v1.md) | Kenny Hill |
| Local UI | UI | [PRD-ui-v4](components/PRD-ui-v4.md) | [LLD-ui-v1](../lld/LLD-ui-v1.md) | Kenny Hill |
| Migration and cutover | MIG | [PRD-migration-v5](components/PRD-migration-v5.md) | [LLD-migration-v1](../lld/LLD-migration-v1.md) | Kenny Hill |
| Security | SEC | [PRD-security-v2](components/PRD-security-v2.md) | [LLD-security-v1](../lld/LLD-security-v1.md) | Kenny Hill |

## 2.2 Functional requirement index

> **Owner:** C · **Persona:** `product-writer` drafts wording; the owner selects and approves · **Seed question:** 3

No parent `FR-n` IDs exist: the functional requirements live in each component PRD's section 2.4, with that component's prefix. Each component requirement traces to the outcome (`OUT-n`) and NFR (`NFR-n`) IDs in this document. Priorities are set by the owner in the component PRDs.

| Component | Requirements | Where | Traces to |
| --- | --- | --- | --- |
| Platform | `PLAT-FR-n` | [PRD-platform-v4](components/PRD-platform-v4.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Sources | `SRC-FR-n` | [PRD-sources-v5](components/PRD-sources-v5.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Search and identity | `SRCH-FR-n` | [PRD-search-v3](components/PRD-search-v3.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Retrieval and cache | `CACHE-FR-n` | [PRD-cache-v4](components/PRD-cache-v4.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Health and credentials | `HLTH-FR-n` | [PRD-health-v4](components/PRD-health-v4.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Local UI | `UI-FR-n` | [PRD-ui-v4](components/PRD-ui-v4.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Migration and cutover | `MIG-FR-n` | [PRD-migration-v5](components/PRD-migration-v5.md) 2.4 | OUT and NFR IDs, cited per requirement |
| Security | none yet; its criteria `SEC-n` cite other components' requirements and parent NFRs | [PRD-security-v2](components/PRD-security-v2.md) 2.4 | NFR IDs, cited per criterion |

## 2.3 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

Quality and target text for NFR-1 to NFR-11 are carried over from PRD-v4 section 6; NFR-12 records the owner's availability and scale answer. The owner approved every target as written (owner decision, 2026-10-22). The "How it is measured" column is the product writer's proposal, marked "Proposed", for the owner and the test plan to confirm.

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |
| NFR-1 | Single process | One daemon per Mac owns all HTTP clients, rate limiters, stores and the scheduler. MCP clients connect through a thin stdio shim, which relays to the daemon over loopback HTTP ([ADR 0002](../adr/0002-one-daemon-with-stdio-shims.md)). | Proposed: a test connects two clients and confirms they share one daemon and one set of rate limiters |
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
| NFR-12 | Availability and scale | Personal and best effort: one user on one Mac. The daemon runs while the Mac is awake and launchd restarts it when it exits; the watchdog reports a dead daemon within 15 minutes (OUT-4). There is no uptime percentage (owner decision, 2026-10-22). | Proposed: a test confirms the launchd job restarts the daemon, and the OUT-4 watchdog test covers the report |

## 2.4 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

All data is personal and confidential; the classification column adds handling rules the sources state. Retention values marked as the owner's are from 2026-10-22 (owner decision, 2026-10-22).

| Data | Classification | Source or owner | Retention |
| --- | --- | --- | --- |
| API keys, the daemon token and any webhook token | Personal, confidential; secret (NFR-3, NFR-4) | macOS Keychain; config holds references (NFR-3; ADR 0003) | Until revoked or replaced (owner decision, 2026-10-22) |
| The owner's Google sign-in for Vertex AI Search | Personal, confidential; secret (ADR 0012 decision 5) | `gcloud` owns the Application Default Credentials file; v2 keeps a short-lived access token in memory only (ADR 0012 decision 5) | Not stored by v2 |
| Fetched papers and documents: files, extracted text, chunks, full-text entries, embeddings | Personal, confidential; untrusted content (NFR-6) | Upstream sources; `cache.db` (PRD-v4 8; ADR 0011) | 120 days from fetch; keep, unpin, undo and collection changes grant a fresh 120 days; pinned and archived items never expire (ADR 0011) |
| Archived papers | Personal, confidential | File and sidecar in `My Drive/Research Archive/<year>/`; text and embeddings stay in `cache.db` (D4; ADR 0011) | Never expire (ADR 0011 decision 4) |
| Discarded items | Personal, confidential | Cache trash | 7 days, then deleted (O8; owner decision, 2026-10-22) |
| Daemon state (`state.db`) | Personal, confidential | Application Support (PRD-v4 8) | Life of the install (owner decision, 2026-10-22) |
| Nightly backups of `state.db` and `cache.db` | Personal, confidential | Application Support (PRD-v4 8) | The last 7 kept (PLAT-FR-57; CACHE-49; owner decision, 2026-10-22) |
| Logs | Personal, confidential; must contain no secret (NFR-4) | `~/Library/Logs/research-mcp/` | Rotated by size: 5 files of 10 MB (PLAT-FR-40; owner decision, 2026-10-22) |
| v1 corpus (`~/arxiv-papers`, 307 MB) | Personal, confidential | Owner's Mac; read-only (INV-10); optional import with a merge report (REVIEW-v1 5) | Once imported, the imported items follow the cache rules above (owner decision, 2026-10-22) |
| Scrub backups of the v1 client config files | Personal, confidential; hold plaintext v1 keys | Written by `scrub-client-configs` with owner-only permissions (MIG-FR-5, MIG-FR-26) | Until v1 is retired, then deleted; an approved exception to NFR-3 and INV-6 (MIG-FR-26; owner decision, 2026-10-22) |

## 2.5 Integrations and owners

> **Owner:** H confirms owners · **Persona:** `architect` may draft · **Seed question:** 8

The owner, Kenny Hill, owns every integration on the v2 side. No integration has an SLA: upstream services are best effort, and probes track their state (OUT-4) (owner decision, 2026-10-22).

| System | Owner | Relationship | SLA |
| --- | --- | --- | --- |
| Upstream research sources (45, including the `web` and `reference` groups) | Kenny Hill | v2 calls them through one adapter contract, within their terms and rate limits (PRD-v4 1; NFR-8; ADR 0012) | None; best effort, tracked by probes |
| AWS and Microsoft Learn official MCP servers | Kenny Hill | Upstream sources replacing v1's undocumented site-search endpoints (ADR 0012 decision 2; REVIEW-v1 4) | None; best effort, tracked by probes |
| MCP clients: Claude Code, Claude desktop, Codex, OpenClaw agents | Kenny Hill | Connect only through the stdio shim; client configs switched at cutover (PRD-v4 4, 10; owner decision, 2026-10-22) | None |
| macOS Keychain | Kenny Hill | Holds every secret; read through `/usr/bin/security` with a timeout (NFR-3; PRD-v4 12) | None |
| launchd | Kenny Hill | Runs the daemon (PRD-v4 8) | None |
| macOS notifications and the optional OpenClaw inbox webhook | Kenny Hill | Notification channels (PRD-v4 4; O5) | None |
| Google Drive sync folder | Kenny Hill | Archive target (D4; ADR 0011) | None |
| `gcloud` and Vertex AI Search | Kenny Hill | Short-lived token for `discoveryengine.googleapis.com`; token refresh only to `oauth2.googleapis.com` (ADR 0012) | None |
| v1 server (`my-research-mcp-server`) | Kenny Hill | Read-only and running until cutover; source of the credential import and optional corpus import (PRD-v4 header, 10; ADR 0001) | None |
| ECC orchestrator | Kenny Hill | Builds v2 one work unit at a time (PRD-v4 4) | None |

## 2.6 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | v1 stays read-only and running until cutover (PRD-v4 header; ADR 0001; INV-10). Cutover (M4) switches client configs; v1 is archived after 14 days of daily use on v2 with no fallback to v1 (PRD-v4 10). |
| Conditions that halt the rollout | Any deletion without a recorded owner decision (INV-1), any secret in an output (INV-2), a fallback to v1 during the 14-day window, or a breach of any other invariant (INV-3 to INV-10, or a component invariant `<PREFIX>-INV-n`) (owner decision, 2026-10-22) |
| Support owner and escalation path | The owner is the only support; there is no escalation path (owner decision, 2026-10-22) |
| Response targets by severity (S0 to S4) | None (owner decision, 2026-10-22). Detection targets are in OUT-4 and OUT-5. |

## 2.7 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

From PRD-v4 sections 7 and 10:

- Every milestone's exit in 2.9 is met, ending with M4: 14 days of daily use on v2 with no fallback to v1, then v1 archived (PRD-v4 10).
- The release is done at the M4 exit. The 30-day metrics in 1.4 are tracked afterward as outcomes, not as a condition of done (owner decision, 2026-10-22; PRD-v4 7).

## 2.8 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves

**Assumptions**

- PRD-v4 7 metrics are attached to the closest outcome in 1.4: tool calls to OUT-2, coverage and time to add a source to OUT-3, share noticed to OUT-4. The owner approved 1.4 with this placement (owner decision, 2026-10-22).
- The "How it is measured" column in 2.3 is a proposal for the test plan, not a target.

**Resolved on 2026-10-22.** Every open question in PRD-v5 is answered above: O2 to O8 (1.6), the 1.4 targets and their milestones (1.4), the Google Scholar reason (1.3), INV-10 (1.5), availability and scale (NFR-12), data handling (2.4), integration owners (2.5), rollout and support (2.6), done (2.7), ADRs 0001 to 0010 and 0013 (1.6), and the scope key `research-mcp`.

Gate 1 answers of the same day: the NFR targets in 2.3 are approved as written; `cite` ships in M1 (2.9); MCP clients connect only through the shim, so 1.2, NFR-1 and 2.5 now say so (an editorial clarification of NFR-1: its single-process target is unchanged); the last 7 nightly backups are kept and logs rotate by size, correcting two retention values of PRD-v6 2.4 that contradicted PLAT-FR-57 and PLAT-FR-40; the scrub backups are an approved exception to INV-6 and NFR-3 until v1 retirement (1.5, 2.4); and a breach of any invariant, parent or component, halts the rollout (2.6). No question is open.

## 2.9 Milestones

> **Owner:** H · **Persona:** none (`planner` drafts the milestone plans)

Carried over from PRD-v4 section 10, except that `cite` moves from M2 to M1, where SPEC-v2 7.2 and SRCH-32 already put it (owner decision, 2026-10-22). There are no calendar dates; each 1.4 target is due at the exit of the milestone that delivers it (owner decision, 2026-10-22).

| Milestone | Outcome | Exit |
| --- | --- | --- |
| **M0 Foundation** (ECC pilot) | Repo, settings, Keychain secrets, safe HTTP client with redaction, state store, adapter contract and registry, three reference adapters (arXiv, Crossref, OpenAlex), federated `search`, `get_work`, `list_sources`, daemon, stdio shim, launchd install, CI. | All M0 tests green; a client can search three sources through the shim on the owner's Mac. |
| **M1 Reach and health** | Every remaining v1 source ported and the new sources added, each with fixtures and a probe; citations, `cite`, integrity checks; health states, credential states, quota tracking, notifications, `doctor`. | 45 or more sources registered, every v1 endpoint mapped; source board data available through `research://sources`; notifications verified on the Mac. |
| **M2 Retrieval and cache** | `fetch`, `read`, `search_cache`, collections, extraction and chunking, embeddings, the 120-day lifecycle, the review, the searchable Drive archive and its rebuild job, disk monitoring. | Lifecycle tests green; one real archive written to Drive and verified. |
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
| Kenny Hill (Product) | 2026-10-22 | Approved in chat; recorded by Claude in the owner's name at his direction |
