---
title: "Search and Identity"
type: prd-component
version: 2
status: draft
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
prefix: SRCH
component: search
parent: docs/prd/PRD-v5.md
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
supersedes: docs-archive/prd/components/PRD-search-v1.md
date: 2026-10-22
---

# Component PRD: Search and Identity (v2)

This version moves [PRD-search v1](../../../docs-archive/prd/components/PRD-search-v1.md) onto the component PRD template. Requirements and acceptance criteria keep their meaning; their IDs follow the new scheme (section 2.16). The design is in [LLD-search v1](../../lld/LLD-search-v1.md). Parent: [PRD v5](../PRD-v5.md), outcomes OUT-1 and OUT-2.

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

One call should search many sources at once and return one clean list: each work once, with every source that knows it, plus an honest report of which sources answered (PRD-search-v1 1).

Evidence from the v1 review:

- v1 has 53 single-source tools. A question that spans sources takes 10 to 20 tool calls with different argument names and result shapes, and the same paper comes back several times (PRD-v4 2, problem 1).
- There is no federated search, no cross-source dedupe and no per-source status (REVIEW-v1 3, finding 5; FUNC-01, FUNC-02, ARCH-05).
- Duplicate works: 54 PDFs have two rows each (versioned and unversioned arXiv id), so about 132 unique works sit behind 186 rows, caused by inconsistent identifier handling (REVIEW-v1 3, finding 4; FUNC-20, FUNC-21, ARCH-10).

The owner's direction: the value of the server is its horizontal reach; merge tools, not sources (owner decision D1, REVIEW-v1 1).

- [ ] Q: Is there a reason this component is needed now beyond the v2 rebuild itself (PRD-v4 1)?

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| The owner, through an agent (Claude Code, Claude desktop, Codex, OpenClaw agents) | Search, look up, cite and check works across many sources through MCP tools, resources and prompts (PRD-v4 4) | Not stated |
| The owner, directly | Sees search records in the local UI (PRD-search-v1 FR-SRCH-09) | Not stated |

- [ ] Q: What is the relative size or importance of each user group for this component?

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- Federated search, `get_work`, identifier normalization, dedupe, citations and integrity checks (PRD-v4 5, component index).
- Authors search and citation export with `cite` (PRD-search-v1 2.4).

| Non-goal | Why it is excluded |
| --- | --- |
| Relevance tuning beyond reciprocal rank fusion | Not stated (PRD-search-v1 3) |
| Full-text search across sources that do not offer it | Not stated (PRD-search-v1 3) |
| Google Scholar | Scraping Google Scholar is a parent non-goal (PRD-search-v1 3; PRD-v4 3.2) |
| Keeping v1 tool names or result shapes | Clients are updated at cutover (PRD-v4 3.2) |

- [ ] Q: Why are relevance tuning beyond reciprocal rank fusion and cross-source full-text search excluded?

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

The source PRD names parent goals G1 and G2 for this component, now OUT-1 and OUT-2 in the parent PRD (PRD-search-v1 header). The parent measure for OUT-2 is: a five-source search returns in under 8 s at p95 with every source's status reported (PRD-v4 3.1, G2). Owner check OC-12 measures it over 20 live runs (TEST-PLAN-v3).

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |

- [ ] Q: Does this component need its own outcomes (`SRCH-OUT-n`), or do the parent outcomes OUT-1 and OUT-2 suffice?

## 1.5 Leaps of faith

> **Owner:** H · **Persona:** none

| Leap of faith | How we will validate it | By when |
| --- | --- | --- |

- [ ] Q: Which two or three bets must hold for federated search to succeed?

## 1.6 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

| ID | The system must never | Source (regulation, policy, contract) |
| --- | --- | --- |

- [ ] Q: The source PRD states several "never" rules as requirements: a failing source never fails the search (SRCH-FR-4); identity is never derived from a file name (SRCH-FR-13); unknown citation styles and formats are rejected, not silently replaced (SRCH-FR-22). Should any of these become invariants (`SRCH-INV-n`)?

## 1.7 Known constraints and decisions

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

| Decision or constraint | Status (made or open) | Rationale or link |
| --- | --- | --- |
| Merge tools, not sources: the value is horizontal reach | Made | Owner decision D1 ([REVIEW-v1](../../../docs-archive/review/REVIEW-v1.md) 1) |
| Requirements are domain-neutral; web search is an optional source group `web`, off until configured, capped per day and not in the default fan-out; within the group the default strategy is `fallback` | Made | [ADR 0012](../../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md) |
| `search` gains an optional `site_set` argument in M1, added with a default so the M0 tool contract stays valid | Made | ADR 0012, Consequences |
| No tool blocks the event loop; network I/O is async | Made | NFR-2; [ADR 0005](../../adr/0005-async-io-cpu-off-loop.md) |
| Every tool result fits a byte budget (default 64 KB) and pages with a cursor beyond it | Made | NFR-5 |
| Archived items keep their stored metadata, so `cite` works from it | Made | [ADR 0011](../../adr/0011-archive-keeps-text-searchable-120-day-retention.md); PRD-cache-v2 FR-CACHE-49 |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

---

## 2.1 Customer discovery

> **Owner:** A · **Persona:** `analyst`

No research notes exist in `docs/research/` for this component. The evidence comes from the v1 deep review ([REVIEW-v1](../../../docs-archive/review/REVIEW-v1.md)), which addressed findings FUNC-01, FUNC-02, FUNC-04, FUNC-17, FUNC-18, FUNC-20, FUNC-21, ARCH-05 and ARCH-10 through this component (PRD-search-v1 header). Its top findings 4 and 5 (duplicate works; no federated search, dedupe or per-source status) drive SRCH-FR-1 to SRCH-FR-14.

## 2.2 User stories and priority

> **Owner:** C for stories (`product-writer`), H for priority · **Seed question:** 3

No user stories exist yet (see 2.13).

| ID | As a... I want... so that... | Priority | Why this priority |
| --- | --- | --- | --- |

## 2.3 User experience

> **Owner:** C · **Persona:** `product-writer` drafts the narrative; designers own the design artifacts · **Seed question:** 3

The key flow is a cross-source search (HLD-v3 11.1):

1. The agent calls `search("policy-as-code adoption", sources="auto", filters={year_from: 2023})`.
2. The registry selects `openalex`, `crossref`, `semantic_scholar`, `arxiv`, `core`, `dblp` and `ssrn` from the default groups, and reports `ads` as `disabled`. Had OpenAlex's budget been spent, it would be reported `skipped_budget` instead of selected.
3. Seven tasks run with 5 s source timeouts inside an 8 s deadline.
4. The returned records are normalized, grouped by shared identifiers, merged and ranked.
5. The agent gets 20 works with `found_in`, plus seven `source_status` entries; one says `timeout`.

The `cross-source-verify` prompt walks an agent through comparing one work across every source in `found_in` (prompt texts, `docs/contracts/prompts-v3.md`).

## 2.4 Functional requirements and acceptance criteria

> **Owner:** C · **Persona:** `product-writer` drafts requirements and criteria as options; the owner selects and approves · **Seed questions:** 3, 12

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| SRCH-FR-1 | The `search` tool takes a query, an optional source selection (`auto`, a list of source ids, or group names), filters (year range, work type, open access only, provider, repository), a total limit, a per-source limit and a cursor. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-2 | `auto` picks enabled, healthy sources from the groups that fit the filters (default groups: `scholarly`, `preprints`); the selection is reported in the result. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-3 | Sources are called concurrently. Each source has its own timeout; the whole search has a deadline (default 8 s). Sources still running at the deadline are cancelled and reported as `timeout`. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-4 | Every result carries `source_status[]` with one entry per selected source: state (`ok`, `empty`, `timeout`, `rate_limited`, `error`, `unconfigured`, `disabled`, `skipped_unhealthy`, `skipped_budget`), result count, latency, retry-after when known, and a classified error code. A failing source never fails the search. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-5 | Results are merged into works (SRCH-FR-10 to SRCH-FR-14), ranked by reciprocal rank fusion across sources with a small boost for works found by more sources, and returned with `found_in[]`, best identifiers, open-access flag and cache state. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-6 | The result is bounded by the response budget (NFR-5). A single opaque cursor carries every source's own cursor so the next page continues each source where it stopped. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-7 | `detail="compact"` (default) returns title, authors (first three and a count), year, venue, identifiers, OA flag and a short abstract snippet; `detail="full"` adds full abstracts within the budget. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-8 | Sources in `rate_limited` or `down` state are skipped by `auto` until their cool-off ends, and reported as `skipped_unhealthy`. An explicit request for such a source tries it once. | | OUT-1, OUT-2 | P2 |
| SRCH-FR-9 | Every search is recorded (query hash, sources, filters, statuses, timings) for telemetry and for the UI; query text is stored only when debug logging is on. | | OUT-1, OUT-2 | P2 |
| SRCH-FR-10 | Identifiers are normalized at the boundary: DOI lowercased without prefix or resolver URL; arXiv id without version (the version is kept separately), old-style ids in `archive/NNNNNNN` form; PMID and PMCID numeric forms; OpenAlex, Semantic Scholar, CORE, NCT, RFC, handle and DSpace UUID in canonical form; URLs normalized for scheme, host case and trailing slash. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-11 | A work is identified by any of its normalized identifiers; two records sharing any identifier are the same work. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-12 | Records with no shared identifier are merged when normalized title, year and first-author surname all match; merges by this rule are flagged `fuzzy` in the result. | | OUT-1, OUT-2 | P2 |
| SRCH-FR-13 | Identity is never derived from a file name. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-14 | When merged records disagree (title, year, retraction status), the result notes the disagreement and the source of each value. | | OUT-1, OUT-2 | P2 |
| SRCH-FR-15 | `get_work` accepts any identifier form (prefixed ids such as `doi:`, `arxiv:`, `pmid:`, bare DOIs, resolver URLs, arXiv URLs, DSpace handles) and returns one merged record from every source that can resolve it. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-16 | The record lists open-access locations from all sources (arXiv, PMC, repository bitstreams, Unpaywall, OpenAlex, CORE, OSF) with license and version where known. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-17 | The record includes integrity status (SRCH-FR-25, SRCH-FR-26) and cache state (cached, pinned, archived, discarded, none). | | OUT-1, OUT-2 | P1 |
| SRCH-FR-20 | `citations` returns citing and cited works for a work, merged from OpenCitations, OpenAlex and Semantic Scholar, deduplicated by DOI, with titles filled in, and paged. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-21 | `authors` searches authors across OpenAlex, ORCID and DBLP and returns merged author records with identifiers. | | OUT-1, OUT-2 | P2 |
| SRCH-FR-22 | `cite` exports one or more works (or a collection) as BibTeX, CSL-JSON, RIS or formatted text in a named style. DOIs use content negotiation; other works use a stored CSL snapshot formatted locally. Unknown styles and formats are rejected, not silently replaced. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-23 | `cite` works for archived and discarded items from their stored metadata. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-25 | `check_integrity` reports retractions, corrections and expressions of concern for given works from Crossref update relations (including Retraction Watch records) and OpenAlex. | | OUT-1, OUT-2 | P1 |
| SRCH-FR-26 | `check_integrity("cache")` re-checks every cached and archived work; a work retracted since it was cached is flagged in the next cache review. | | OUT-1, OUT-2 | P2 |

Acceptance criteria, in the order of the test generator (`tools/gen_test_plan.py`):

| ID | Criterion | Requirement | Priority | Level | Milestone |
| --- | --- | --- | --- | --- | --- |
| SRCH-10 | The identity module shall normalize DOIs according to the DOI normalization table, covering prefixes, resolver URLs, case and trailing punctuation, and reject invalid forms. | SRCH-FR-10 | P1 | unit | M0 |
| SRCH-11 | The identity module shall normalize arXiv identifiers so that `2410.18291v1` and `2410.18291` give the same id with the version kept separate, including old-style ids and abs and pdf URLs. | SRCH-FR-10, SRCH-FR-11 | P1 | unit | M0 |
| SRCH-12 | The identity module shall produce canonical forms for PMID, PMCID, OpenAlex, Semantic Scholar, CORE, NCT, RFC, handle and DSpace UUID identifiers. | SRCH-FR-10 | P1 | unit | M0 |
| SRCH-13 | The identity module shall normalize URLs for scheme and host case, default ports, fragments and tracking parameters. | SRCH-FR-10 | P1 | unit | M0 |
| SRCH-14 | The identity module's `parse_any` shall detect schemes from prefixes, hosts and shapes (including `github:` and GitHub URLs), raise `IdentifierError` for unknown input, and reject file-name shapes such as `doi_10.1145_3649835`, `core_123` and `*.pdf`. | SRCH-FR-10, SRCH-FR-13 | P1 | unit | M0 |
| SRCH-15 | The identity module shall keep every normalizer idempotent and stable under case and whitespace changes, as checked by a property test. | SRCH-FR-10 | P1 | unit | M0 |
| SRCH-16 | The identity module's `title_key` shall apply Unicode normalization, casefolding, and removal of punctuation and stop words. | SRCH-FR-12 | P2 | unit | M0 |
| SRCH-1 | The federation service shall run sources concurrently, so that three fake sources of 1 s each finish in about 1 s. | SRCH-FR-3, NFR-2 | P1 | integration | M0 |
| SRCH-2 | If a slow source is still running at its timeout or at the deadline, then the federation service shall cancel it and report it as `timeout` while the other sources return. | SRCH-FR-3, SRCH-FR-4 | P1 | integration | M0 |
| SRCH-3 | If a source fails, then the federation service shall complete the search without failing and give every selected source a status entry. | SRCH-FR-4 | P1 | integration | M0 |
| SRCH-4 | When records share any identifier, the federation service shall merge them into one work whose `found_in` lists every source. | SRCH-FR-5, SRCH-FR-11 | P1 | integration | M0 |
| SRCH-5 | When records match on title, year and first author, the federation service shall merge them and flag the merge `fuzzy`. | SRCH-FR-12 | P2 | integration | M0 |
| SRCH-6 | The federation service shall rank works by reciprocal rank fusion with the multi-source boost, matching the golden ordering. | SRCH-FR-5 | P1 | integration | M0 |
| SRCH-7 | When a search continues from the combined cursor, the federation service shall continue each source from its own cursor and report exhausted sources as `empty`. | SRCH-FR-6 | P1 | integration | M0 |
| SRCH-8 | When `sources` is `auto`, the federation service shall select enabled sources from the default groups and skip unconfigured, disabled and down sources with their status. | SRCH-FR-2, SRCH-FR-8, HLTH-FR-12 | P1 | integration | M0 |
| SRCH-9 | When fields disagree across sources, the federation service shall record the disagreeing values with their sources. | SRCH-FR-14 | P2 | integration | M0 |
| SRCH-17 | When `get_work` resolves an identifier, the works service shall merge records from every source that understands the identifier and list the OA locations. | SRCH-FR-15, SRCH-FR-16 | P1 | integration | M0 |
| SRCH-20 | When the `search` tool is called through an in-memory MCP client, the MCP server shall return structured content matching the tool's output schema. | SRCH-FR-1, PLAT-FR-30 | P1 | contract | M0 |
| SRCH-21 | If a tool call has out-of-range or unknown arguments, then the MCP server shall reject it before any source is called. | PLAT-FR-31 | P1 | contract | M0 |
| SRCH-22 | The `search` tool shall trim authors and abstracts in `compact` detail and fit `full` detail within the budget. | SRCH-FR-7 | P1 | contract | M0 |
| SRCH-23 | The `get_work` tool shall accept prefixed ids, bare DOIs, resolver URLs and arXiv URLs. | SRCH-FR-15 | P1 | contract | M0 |
| SRCH-30 | The `citations` tool shall merge OpenCitations, OpenAlex and Semantic Scholar results, dedupe them by DOI, fill in titles and return them in pages. | SRCH-FR-20 | P1 | integration | M1 |
| SRCH-31 | The `authors` tool shall merge OpenAlex, ORCID and DBLP author records. | SRCH-FR-21 | P2 | integration | M1 |
| SRCH-32 | The `cite` tool shall export BibTeX, CSL-JSON, RIS and text, format non-DOI works from the CSL snapshot, and reject an unknown style or format. | SRCH-FR-22 | P1 | integration | M1 |
| SRCH-33 | The `check_integrity` tool shall report retractions and corrections, including Retraction Watch records, as checked against golden fixtures. | SRCH-FR-25 | P1 | integration | M1 |
| SRCH-34 | When a search runs, the federation service shall record the query hash, sources, statuses and timings, keeping the query text only in debug. | SRCH-FR-9 | P2 | integration | M1 |
| SRCH-36 | The `get_work` tool shall report integrity status and cache state (cached, pinned, archived, discarded, none). | SRCH-FR-17 | P1 | integration | M2 |

SRCH-FR-23 and SRCH-FR-26 have no criterion in this component; the test plan verifies them with CACHE-36 and CACHE-35 (see 2.13).

## 2.5 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

No component NFRs are defined. Parent NFRs that apply: NFR-2 (no tool blocks the event loop), NFR-5 (every tool result fits a byte budget, default 64 KB, and pages with a cursor beyond it) (PRD-v4 NFR table; PRD-search-v1 FR-SRCH-06). The search deadline defaults to 8 s (SRCH-FR-3).

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |

- [ ] Q: Does this component need its own NFRs (`SRCH-NFR-n`), for example a latency target for `get_work`, or do the parent NFRs suffice?

## 2.6 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

| Data | Classification | Source or owner | Retention | Notes |
| --- | --- | --- | --- | --- |
| Search records: query hash, sources, filters, statuses, timings | Not stated | This component (SRCH-FR-9) | Not stated | For telemetry and the UI |
| Search query text | Not stated | This component (SRCH-FR-9) | Not stated | Stored only when debug logging is on |
| Work metadata and stored CSL snapshot | Not stated | Upstream sources | Not stated | Used by `cite` for archived and discarded items (SRCH-FR-23) |

- [ ] Q: What is the classification and retention of search records, query text and work metadata?

## 2.7 Integrations and owners

> **Owner:** H confirms owners and SLAs · **Persona:** `architect` may draft · **Seed question:** 8

| System | Owner | Relationship (depends on, feeds, replaces) | SLA |
| --- | --- | --- | --- |
| Sources component (adapter contract, registry, source groups, `web` group) | Not stated | Depends on | Not stated |
| Health component (source states that federation reads to skip sources, HLTH-FR-12) | Not stated | Depends on | Not stated |
| Platform component (tool envelope PLAT-FR-30, argument bounds PLAT-FR-31, budget, cursors) | Not stated | Depends on | Not stated |
| Cache component (cache state, stored metadata for `cite`, cache review for `check_integrity("cache")`) | Not stated | Depends on and feeds | Not stated |
| Upstream services: OpenCitations, OpenAlex, Semantic Scholar, ORCID, DBLP, Crossref update relations (including Retraction Watch records), and the OA sources in SRCH-FR-16 | Third parties | Depends on | Not stated |
| v1 single-source tools (53 tools) | Owner | Replaces (PRD-v4 2) | Not stated |

- [ ] Q: Who owns each integration, and are there SLAs?

## 2.8 Product risks

> **Owner:** H · **Persona:** none

| Risk | Question | Assessment | Mitigation |
| --- | --- | --- | --- |
| Value | Will customers choose to use this? | Not stated | Not stated |
| Usability | Can customers use it, including with accessibility needs? | Not stated | Not stated |
| Viability | Does it work for the business: economics, legal, compliance, operations? | Metered sources (OpenAlex budget, web-search providers) can run out mid-task or cost more than expected (PRD-v4 risks) | Federation skips exhausted sources and says so; web-search sources are off until configured, capped per day, and never in the default fan-out (PRD-v4 risks) |

- [ ] Q: What are the value and usability risks for federated search, and how are they mitigated?

## 2.9 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | By milestone: `search`, `get_work` and `list_sources` in M0; citations and integrity checks in M1 (PRD-v4 milestones) |
| Business conditions that must halt the rollout | Not stated |
| Support owner and escalation path | Not stated |
| Response targets by severity (S0 to S4) | Not stated |

- [ ] Q: What business conditions must halt the rollout, who is the support owner and escalation path, and what are the response targets by severity?

## 2.10 Measurement and experimentation

> **Owner:** C · **Persona:** `product-writer` drafts; the owner decides

| Outcome | Measured by | Experiment (if any) |
| --- | --- | --- |
| OUT-2 (parent) | Owner check OC-12: five-source live search p95 under 8 s over 20 runs (TEST-PLAN-v3) | None |

## 2.11 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

The criteria in 2.4 pass (PRD-search-v1 4). For M0, a client can search three sources through the shim on the owner's Mac (PRD-v4 milestones, M0 exit).

- [ ] Q: Which outcome metrics must be measurable at launch for this component?

## 2.12 Edge cases and error behavior

> **Owner:** A · **Persona:** `product-writer`

- A source still running at its timeout or at the deadline is cancelled and reported as `timeout` (SRCH-2).
- A failing source never fails the search; it gets a status entry (SRCH-3).
- A source whose cursor is exhausted reports `empty` on the next page (SRCH-7).
- Unconfigured, disabled and down sources are skipped by `auto` and reported with their status (SRCH-8). An explicit request for a `rate_limited` or `down` source tries it once (SRCH-FR-8).
- Records with no shared identifier merge only when title, year and first author match, and the merge is flagged `fuzzy` (SRCH-5).
- Disagreeing fields across sources are recorded with their sources, not silently resolved (SRCH-9).
- Unknown identifier input raises `IdentifierError`; file-name shapes are rejected (SRCH-14).
- Invalid DOI forms are rejected (SRCH-10).
- Out-of-range and unknown arguments are rejected before any source is called (SRCH-21).
- An unknown citation style or format is rejected, not replaced (SRCH-32).
- `full` detail still fits the response budget (SRCH-22).

## 2.13 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves before Gate 1

- [ ] Q: Which user stories (`SRCH-US-n`) should this component have, and what priority does each carry? No stories exist yet, so the Story column in 2.4 is empty.
- [ ] Q: SRCH-FR-23 and SRCH-FR-26 have no criterion here; TEST-PLAN-v3 traces them to AT-CACHE-36 and AT-CACHE-35 (now CACHE-36 and CACHE-35). Should they move to the cache component, or should this component get its own criteria for them?
- [ ] Q: SRCH-FR-4 lists the state `skipped_budget`, while HLTH-FR-12 and SPEC-v2 5.5 use `budget_exhausted` and SPEC-v2 5.5 adds `not_needed` for the `web` fallback. Which state names are the contract?
- [ ] Q: SRCH-FR-8 says `auto` skips `rate_limited` and `down` sources; SRCH-8 checks unconfigured, disabled and down. Is the `rate_limited` skip meant to have its own criterion?
- [ ] Q: SRCH-FR-10 lists URL trailing-slash normalization, but SRCH-13 does not check it. Is the trailing slash part of URL normalization?
- [ ] Q: SRCH-FR-10 does not list GitHub identifiers, but SRCH-14 checks `github:` and GitHub URLs. Should SRCH-FR-10 name them?
- [ ] Q: The parent milestone table puts `cite` in M2 (PRD-v4 milestones), while SRCH-32 and SPEC-v2 7.2 put it in M1. Which milestone holds?
- The parent outcomes for every requirement are taken from the source PRD header (G1 and G2). Assumption: no requirement serves a different parent outcome.

## 2.14 Glossary

> **Owner:** A · **Persona:** `product-writer`

| Term | Definition |
| --- | --- |
| Federated search | One `search` call that runs many sources concurrently and returns one merged, ranked list with per-source status (PRD-search-v1 1, 2.1) |
| `auto` selection | The default source selection: enabled, healthy sources from the groups that fit the filters (default groups `scholarly` and `preprints`) (SRCH-FR-2) |
| `source_status` | The per-source entry in every result: state, result count, latency, retry-after and classified error code (SRCH-FR-4) |
| `found_in` | The list of sources that returned a merged work (SRCH-FR-5) |
| Reciprocal rank fusion | The ranking that combines each source's rank order, with a small boost for works found by more sources (SRCH-FR-5) |
| Combined cursor | One opaque cursor that carries every source's own cursor (SRCH-FR-6) |
| Fuzzy merge | A merge of records with no shared identifier, made because normalized title, year and first-author surname match; flagged `fuzzy` (SRCH-FR-12) |
| OA location | An open-access copy of a work, with license and version where known (SRCH-FR-16) |
| CSL snapshot | Stored citation metadata used to format non-DOI works locally (SRCH-FR-22) |
| Integrity status | Retractions, corrections and expressions of concern reported for a work (SRCH-FR-25) |
| `web` group | The optional, metered web-search source group, not in the default fan-out (ADR 0012) |

## 2.15 ID history

> **Owner:** C · **Persona:** `product-writer` records; the owner confirms

| ID | Status | Replaced by | Reason |
| --- | --- | --- | --- |

## 2.16 Earlier IDs

> **Owner:** A · **Persona:** `product-writer`

| Earlier ID | New ID |
| --- | --- |
| FR-SRCH-01 | SRCH-FR-1 |
| FR-SRCH-02 | SRCH-FR-2 |
| FR-SRCH-03 | SRCH-FR-3 |
| FR-SRCH-04 | SRCH-FR-4 |
| FR-SRCH-05 | SRCH-FR-5 |
| FR-SRCH-06 | SRCH-FR-6 |
| FR-SRCH-07 | SRCH-FR-7 |
| FR-SRCH-08 | SRCH-FR-8 |
| FR-SRCH-09 | SRCH-FR-9 |
| FR-SRCH-10 | SRCH-FR-10 |
| FR-SRCH-11 | SRCH-FR-11 |
| FR-SRCH-12 | SRCH-FR-12 |
| FR-SRCH-13 | SRCH-FR-13 |
| FR-SRCH-14 | SRCH-FR-14 |
| FR-SRCH-15 | SRCH-FR-15 |
| FR-SRCH-16 | SRCH-FR-16 |
| FR-SRCH-17 | SRCH-FR-17 |
| FR-SRCH-20 | SRCH-FR-20 |
| FR-SRCH-21 | SRCH-FR-21 |
| FR-SRCH-22 | SRCH-FR-22 |
| FR-SRCH-23 | SRCH-FR-23 |
| FR-SRCH-25 | SRCH-FR-25 |
| FR-SRCH-26 | SRCH-FR-26 |
| AT-SRCH-10 | SRCH-10 |
| AT-SRCH-11 | SRCH-11 |
| AT-SRCH-12 | SRCH-12 |
| AT-SRCH-13 | SRCH-13 |
| AT-SRCH-14 | SRCH-14 |
| AT-SRCH-15 | SRCH-15 |
| AT-SRCH-16 | SRCH-16 |
| AT-SRCH-01 | SRCH-1 |
| AT-SRCH-02 | SRCH-2 |
| AT-SRCH-03 | SRCH-3 |
| AT-SRCH-04 | SRCH-4 |
| AT-SRCH-05 | SRCH-5 |
| AT-SRCH-06 | SRCH-6 |
| AT-SRCH-07 | SRCH-7 |
| AT-SRCH-08 | SRCH-8 |
| AT-SRCH-09 | SRCH-9 |
| AT-SRCH-17 | SRCH-17 |
| AT-SRCH-20 | SRCH-20 |
| AT-SRCH-21 | SRCH-21 |
| AT-SRCH-22 | SRCH-22 |
| AT-SRCH-23 | SRCH-23 |
| AT-SRCH-30 | SRCH-30 |
| AT-SRCH-31 | SRCH-31 |
| AT-SRCH-32 | SRCH-32 |
| AT-SRCH-33 | SRCH-33 |
| AT-SRCH-34 | SRCH-34 |
| AT-SRCH-36 | SRCH-36 |

### Gate 1: Requirements approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |
