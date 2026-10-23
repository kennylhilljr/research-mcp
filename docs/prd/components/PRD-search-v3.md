---
title: "Search and Identity"
type: prd-component
version: 3
status: draft
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
prefix: SRCH
component: search
parent: docs/prd/PRD-v7.md
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
supersedes: docs/prd/components/PRD-search-v2.md
date: 2026-10-22
---

# Component PRD: Search and Identity (v3)

This component PRD carries [PRD-search v1](../../../docs-archive/prd/components/PRD-search-v1.md) on the component PRD template, through [PRD-search v2](PRD-search-v2.md). Version 3 records the owner's Gate 1 answers of 2026-10-22. Requirements and acceptance criteria keep their IDs; changes are listed in section 2.15, and earlier IDs map to current ones in section 2.16. Parent: [PRD v7](../PRD-v7.md), outcomes OUT-1 and OUT-2. Vision: [vision-v2](../../vision/vision-v2.md). The system design is in [SPEC-v3](../../spec/SPEC-v3.md), which keeps HLD-v3 numbering; the component design is in [LLD-search v1](../../lld/LLD-search-v1.md).

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

One call should search many sources at once and return one clean list: each work once, with every source that knows it, plus an honest report of which sources answered (PRD-search-v1 1).

Evidence from the v1 review:

- v1 has 53 single-source tools. A question that spans sources takes 10 to 20 tool calls with different argument names and result shapes, and the same paper comes back several times (PRD-v4 2, problem 1).
- There is no federated search, no cross-source dedupe and no per-source status (REVIEW-v1 3, finding 5; FUNC-01, FUNC-02, ARCH-05).
- Duplicate works: 54 PDFs have two rows each (versioned and unversioned arXiv id), so about 132 unique works sit behind 186 rows, caused by inconsistent identifier handling (REVIEW-v1 3, finding 4; FUNC-20, FUNC-21, ARCH-10).

The owner's direction: the value of the server is its horizontal reach; merge tools, not sources (owner decision D1, REVIEW-v1 1).

**Why now.** This component is needed now for the v2 rebuild and because upstream breakage is current (PRD-v7 1.1; owner decision, 2026-10-22). The live probes of 2026-10-19 found OpenAlex keyless calls rejected for budget, Semantic Scholar bulk search ignoring `limit`, and Crossref throttling clients without a contact email (PRD-v7 1.1). These are sources that federated search calls by default, and v1 noticed none of it.

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| The owner, through an agent (Claude Code, Claude desktop, Codex, OpenClaw agents) | Search, look up, cite and check works across many sources through MCP tools, resources and prompts (PRD-v4 4) | One person; personal server (PRD-v6 1.2; owner decision, 2026-10-22) |
| The owner, directly | Sees search records in the local UI (PRD-search-v1 FR-SRCH-09) | One person (PRD-v6 1.2; owner decision, 2026-10-22) |

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- Federated search, `get_work`, identifier normalization, dedupe, citations and integrity checks (PRD-v4 5, component index).
- Authors search and citation export with `cite` (PRD-search-v1 2.4).

| Non-goal | Why it is excluded |
| --- | --- |
| Relevance tuning beyond reciprocal rank fusion | Excluded to keep v2 a working cache and one search, not a library or search engine (PRD-v6 2.10, scope creep risk; owner decision, 2026-10-22) |
| Full-text search across sources that do not offer it | Excluded to keep v2 a working cache and one search, not a library or search engine (PRD-v6 2.10, scope creep risk; owner decision, 2026-10-22) |
| Google Scholar | Not needed: OpenAlex, Semantic Scholar, Crossref and the other scholarly sources cover it (PRD-v6 1.3; owner decision, 2026-10-22) |
| Keeping v1 tool names or result shapes | Clients are updated at cutover (PRD-v4 3.2) |

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

The source PRD names parent goals G1 and G2 for this component, now OUT-1 and OUT-2 in the parent PRD (PRD-search-v1 header). The parent measure for OUT-2 is: a five-source search returns in under 8 s at p95 with every source's status reported, due at the M1 exit; and 1 to 3 tool calls per cross-source question, measured 30 days after cutover (PRD-v6 1.4). Owner check OC-12 measures the latency over 20 live runs ([test plan](../../test/test-plan-v2.md) 3).

The parent outcomes OUT-1 to OUT-8 and NFR-1 to NFR-12 suffice; no component outcome is added (owner decision, 2026-10-22).

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |

## 1.5 Leaps of faith

> **Owner:** H · **Persona:** none

Drafted by the product writer from the sources, each marked for the owner's approval (owner decision, 2026-10-22, to draft them).

| Leap of faith | How we will validate it | By when |
| --- | --- | --- |
| One merged call is what makes the reach usable: an agent answers a cross-source question in 1 to 3 tool calls instead of 10 to 20 (D1; PRD-v6 1.1, problem 1; OUT-2) (proposed for owner approval) | The OUT-2 tool-call measure in the parent 30-day review (PRD-v6 1.4) | M4 exit, measured 30 days after cutover (PRD-v6 1.4) (proposed for owner approval) |
| A five-source search can return within the 8 s deadline even though the project does not control upstream latency (OUT-2; test plan 5, risk 3) (proposed for owner approval) | Owner check OC-12: five-source live search p95 under 8 s over 20 runs | M1 exit (PRD-v6 1.4) (proposed for owner approval) |
| Consistent identifier normalization is enough to remove most duplicates, since the v1 duplicates came from inconsistent identifier handling; the fuzzy merge is only a fallback (REVIEW-v1 3, finding 4) (proposed for owner approval) | Criteria SRCH-4 and SRCH-10 to SRCH-15 pass | M0 exit (proposed for owner approval) |

## 1.6 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

The owner confirmed the drafted "never" rules as component invariants (owner decision, 2026-10-22). Each is checked by a P1 criterion of this component.

| ID | The system must never | Source (regulation, policy, contract) |
| --- | --- | --- |
| SRCH-INV-1 | Fail a search because one source failed; every selected source gets a status entry instead | SRCH-FR-27; owner decision, 2026-10-22. Checked by SRCH-3 (P1) |
| SRCH-INV-2 | Derive a work's identity from a file name | SRCH-FR-13; owner decision, 2026-10-22. Checked by SRCH-14 (P1) |
| SRCH-INV-3 | Silently replace an unknown citation style or format; it is rejected | SRCH-FR-22; owner decision, 2026-10-22. Checked by SRCH-32 (P1) |

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
| Source state names follow SPEC-v2 5.5 and the health component: `budget_exhausted` for a spent budget, and `not_needed` for a `web` source the fallback chain did not need | Made | Owner decision, 2026-10-22; HLTH-FR-12 |
| `cite` ships in M1 | Made | SPEC-v2 7.2; SRCH-32; [PRD-v7](../PRD-v7.md) 2.9 (owner decision, 2026-10-22) |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

---

## 2.1 Customer discovery

> **Owner:** A · **Persona:** `analyst`

No research notes exist in `docs/research/` for this component. The evidence comes from the v1 deep review ([REVIEW-v1](../../../docs-archive/review/REVIEW-v1.md)), which addressed findings FUNC-01, FUNC-02, FUNC-04, FUNC-17, FUNC-18, FUNC-20, FUNC-21, ARCH-05 and ARCH-10 through this component (PRD-search-v1 header). Its top findings 4 and 5 (duplicate works; no federated search, dedupe or per-source status) drive SRCH-FR-1 to SRCH-FR-3, SRCH-FR-5 to SRCH-FR-9, SRCH-FR-11 to SRCH-FR-14, SRCH-FR-27 and SRCH-FR-28.

## 2.2 User stories and priority

> **Owner:** C for stories (`product-writer`), H for priority · **Seed question:** 3

Drafted by the product writer for owner approval (owner decision, 2026-10-22, to draft them). The stories rest on the user needs in PRD-v6 1.2 and section 1.2 of this PRD. No requirement of this component serves the ECC orchestrator, so it has no story.

| ID | As a... I want... so that... | Priority | Why this priority |
| --- | --- | --- | --- |
| SRCH-US-1 | As the owner (through an agent), I want one `search` call to query many sources at once and return one ranked, bounded list, so that a cross-source question takes 1 to 3 tool calls instead of 10 to 20. | P1 | SRCH-FR-1, SRCH-FR-2, SRCH-FR-3, SRCH-FR-5, SRCH-FR-6 and SRCH-FR-7 are P1 |
| SRCH-US-2 | As the owner (through an agent), I want every search to report each source's status, and a failing or unhealthy source not to fail the search, so that I know which sources answered and can trust a partial result. | P1 | SRCH-FR-27 is P1 |
| SRCH-US-3 | As the owner (through an agent), I want each work to appear once, with every source that knows it and any disagreement between them, so that I do not sort through duplicates. | P1 | SRCH-FR-28, SRCH-FR-11 and SRCH-FR-13 are P1 |
| SRCH-US-4 | As the owner (through an agent), I want to look up a work by any identifier and see its open-access locations, integrity status and cache state, so that I can pick the best copy to fetch and read. | P1 | SRCH-FR-15, SRCH-FR-16 and SRCH-FR-17 are P1 |
| SRCH-US-5 | As the owner (through an agent), I want to follow citations, find authors, export citations and check works for retractions, so that I can cite and check works across sources. | P1 | SRCH-FR-20, SRCH-FR-22, SRCH-FR-23 and SRCH-FR-25 are P1 |
| SRCH-US-6 | As the owner (directly), I want to see a record of each search in the local UI, so that I can see what was searched and how each source did. | P2 | Only SRCH-FR-9, a P2 requirement, serves it |

## 2.3 User experience

> **Owner:** C · **Persona:** `product-writer` drafts the narrative; designers own the design artifacts · **Seed question:** 3

The key flow is a cross-source search (SPEC-v3 11.1):

1. The agent calls `search("policy-as-code adoption", sources="auto", filters={year_from: 2023})`.
2. The registry selects `openalex`, `crossref`, `semantic_scholar`, `arxiv`, `core`, `dblp` and `ssrn` from the default groups, and reports `ads` as `disabled`. Had OpenAlex's budget been spent, it would be reported `budget_exhausted` instead of selected.
3. Seven tasks run with 5 s source timeouts inside an 8 s deadline.
4. The returned records are normalized, grouped by shared identifiers, merged and ranked.
5. The agent gets 20 works with `found_in`, plus seven `source_status` entries; one says `timeout`.

The `cross-source-verify` prompt walks an agent through comparing one work across every source in `found_in` (prompt texts, `docs/contracts/prompts-v3.md`).

## 2.4 Functional requirements and acceptance criteria

> **Owner:** C · **Persona:** `product-writer` drafts requirements and criteria as options; the owner selects and approves · **Seed questions:** 3, 12

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| SRCH-FR-1 | The `search` tool takes a query, an optional source selection (`auto`, a list of source ids, or group names), filters (year range, work type, open access only, provider, repository), a total limit, a per-source limit and a cursor. | SRCH-US-1 | OUT-1, OUT-2 | P1 |
| SRCH-FR-2 | `auto` picks enabled, healthy sources from the groups that fit the filters (default groups: `scholarly`, `preprints`); the selection is reported in the result. | SRCH-US-1 | OUT-1, OUT-2 | P1 |
| SRCH-FR-3 | Sources are called concurrently. Each source has its own timeout; the whole search has a deadline (default 8 s). Sources still running at the deadline are cancelled and reported as `timeout`. | SRCH-US-1 | OUT-1, OUT-2 | P1 |
| SRCH-FR-27 | Every result carries `source_status[]` with one entry per selected source: state (`ok`, `empty`, `timeout`, `rate_limited`, `error`, `unconfigured`, `disabled`, `skipped_unhealthy`, `budget_exhausted`, and `not_needed` for a `web` source the fallback chain did not need), result count, latency, retry-after when known, and a classified error code. A failing source never fails the search. | SRCH-US-2 | OUT-1, OUT-2 | P1 |
| SRCH-FR-5 | Results are merged into works (SRCH-FR-28 and SRCH-FR-11 to SRCH-FR-14), ranked by reciprocal rank fusion across sources with a small boost for works found by more sources, and returned with `found_in[]`, best identifiers, open-access flag and cache state. | SRCH-US-1 | OUT-1, OUT-2 | P1 |
| SRCH-FR-6 | The result is bounded by the response budget (NFR-5). A single opaque cursor carries every source's own cursor so the next page continues each source where it stopped. | SRCH-US-1 | OUT-1, OUT-2 | P1 |
| SRCH-FR-7 | `detail="compact"` (default) returns title, authors (first three and a count), year, venue, identifiers, OA flag and a short abstract snippet; `detail="full"` adds full abstracts within the budget. | SRCH-US-1 | OUT-1, OUT-2 | P1 |
| SRCH-FR-8 | Sources in `rate_limited` or `down` state are skipped by `auto` until their cool-off ends, and reported as `skipped_unhealthy`. An explicit request for such a source tries it once. | SRCH-US-2 | OUT-1, OUT-2 | P2 |
| SRCH-FR-9 | Every search is recorded (query hash, sources, filters, statuses, timings) for telemetry and for the UI; query text is stored only when debug logging is on. | SRCH-US-6 | OUT-1, OUT-2 | P2 |
| SRCH-FR-28 | Identifiers are normalized at the boundary: DOI lowercased without prefix or resolver URL; arXiv id without version (the version is kept separately), old-style ids in `archive/NNNNNNN` form; PMID and PMCID numeric forms; OpenAlex, Semantic Scholar, CORE, NCT, RFC, handle and DSpace UUID in canonical form; GitHub identifiers (`github:` ids and GitHub URLs) detected and kept in canonical form; URLs normalized for scheme, host case and trailing slash. | SRCH-US-3 | OUT-1, OUT-2 | P1 |
| SRCH-FR-11 | A work is identified by any of its normalized identifiers; two records sharing any identifier are the same work. | SRCH-US-3 | OUT-1, OUT-2 | P1 |
| SRCH-FR-12 | Records with no shared identifier are merged when normalized title, year and first-author surname all match; merges by this rule are flagged `fuzzy` in the result. | SRCH-US-3 | OUT-1, OUT-2 | P2 |
| SRCH-FR-13 | Identity is never derived from a file name. | SRCH-US-3 | OUT-1, OUT-2 | P1 |
| SRCH-FR-14 | When merged records disagree (title, year, retraction status), the result notes the disagreement and the source of each value. | SRCH-US-3 | OUT-1, OUT-2 | P2 |
| SRCH-FR-15 | `get_work` accepts any identifier form (prefixed ids such as `doi:`, `arxiv:`, `pmid:`, bare DOIs, resolver URLs, arXiv URLs, DSpace handles) and returns one merged record from every source that can resolve it. | SRCH-US-4 | OUT-1, OUT-2 | P1 |
| SRCH-FR-16 | The record lists open-access locations from all sources (arXiv, PMC, repository bitstreams, Unpaywall, OpenAlex, CORE, OSF) with license and version where known. | SRCH-US-4 | OUT-1, OUT-2 | P1 |
| SRCH-FR-17 | The record includes integrity status (SRCH-FR-25, SRCH-FR-26) and cache state (cached, pinned, archived, discarded, none). | SRCH-US-4 | OUT-1, OUT-2 | P1 |
| SRCH-FR-20 | `citations` returns citing and cited works for a work, merged from OpenCitations, OpenAlex and Semantic Scholar, deduplicated by DOI, with titles filled in, and paged. | SRCH-US-5 | OUT-1, OUT-2 | P1 |
| SRCH-FR-21 | `authors` searches authors across OpenAlex, ORCID and DBLP and returns merged author records with identifiers. | SRCH-US-5 | OUT-1, OUT-2 | P2 |
| SRCH-FR-22 | `cite` exports one or more works (or a collection) as BibTeX, CSL-JSON, RIS or formatted text in a named style. DOIs use content negotiation; other works use a stored CSL snapshot formatted locally. Unknown styles and formats are rejected, not silently replaced. | SRCH-US-5 | OUT-1, OUT-2 | P1 |
| SRCH-FR-23 | `cite` works for archived and discarded items from their stored metadata. | SRCH-US-5 | OUT-1, OUT-2 | P1 |
| SRCH-FR-25 | `check_integrity` reports retractions, corrections and expressions of concern for given works from Crossref update relations (including Retraction Watch records) and OpenAlex. | SRCH-US-5 | OUT-1, OUT-2 | P1 |
| SRCH-FR-26 | `check_integrity("cache")` re-checks every cached and archived work; a work retracted since it was cached is flagged in the next cache review. | SRCH-US-5 | OUT-1, OUT-2 | P2 |

Acceptance criteria, in the order of the test generator (`tools/gen_test_plan.py`):

| ID | Criterion | Requirement | Priority | Level | Milestone |
| --- | --- | --- | --- | --- | --- |
| SRCH-10 | The identity module shall normalize DOIs according to the DOI normalization table, covering prefixes, resolver URLs, case and trailing punctuation, and reject invalid forms. | SRCH-FR-28 | P1 | unit | M0 |
| SRCH-11 | The identity module shall normalize arXiv identifiers so that `2410.18291v1` and `2410.18291` give the same id with the version kept separate, including old-style ids and abs and pdf URLs. | SRCH-FR-28, SRCH-FR-11 | P1 | unit | M0 |
| SRCH-12 | The identity module shall produce canonical forms for PMID, PMCID, OpenAlex, Semantic Scholar, CORE, NCT, RFC, handle and DSpace UUID identifiers. | SRCH-FR-28 | P1 | unit | M0 |
| SRCH-13 | The identity module shall normalize URLs for scheme and host case, default ports, fragments and tracking parameters. | SRCH-FR-28 | P1 | unit | M0 |
| SRCH-14 | The identity module's `parse_any` shall detect schemes from prefixes, hosts and shapes (including `github:` and GitHub URLs), raise `IdentifierError` for unknown input, and reject file-name shapes such as `doi_10.1145_3649835`, `core_123` and `*.pdf`. | SRCH-FR-28, SRCH-FR-13 | P1 | unit | M0 |
| SRCH-15 | The identity module shall keep every normalizer idempotent and stable under case and whitespace changes, as checked by a property test. | SRCH-FR-28 | P1 | unit | M0 |
| SRCH-16 | The identity module's `title_key` shall apply Unicode normalization, casefolding, and removal of punctuation and stop words. | SRCH-FR-12 | P2 | unit | M0 |
| SRCH-1 | The federation service shall run sources concurrently, so that three fake sources of 1 s each finish in about 1 s. | SRCH-FR-3, NFR-2 | P1 | integration | M0 |
| SRCH-2 | If a slow source is still running at its timeout or at the deadline, then the federation service shall cancel it and report it as `timeout` while the other sources return. | SRCH-FR-3, SRCH-FR-27 | P1 | integration | M0 |
| SRCH-3 | If a source fails, then the federation service shall complete the search without failing and give every selected source a status entry. | SRCH-FR-27 | P1 | integration | M0 |
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
| SRCH-37 | When `sources` is `auto`, the federation service shall skip `rate_limited` sources and report each one's status. | SRCH-FR-8, HLTH-FR-12 | P1 | integration | M0 |
| SRCH-38 | The identity module shall normalize the trailing slash of a URL. | SRCH-FR-28 | P1 | unit | M0 |

Verified elsewhere (owner decision, 2026-10-22): SRCH-FR-23 stays in this component and is verified by CACHE-36 of the cache component; SRCH-FR-26 stays in this component and is verified by CACHE-35 of the cache component. SRCH-FR-3 is also measured live by owner check OC-12, which stays an owner check.

## 2.5 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

The parent outcomes OUT-1 to OUT-8 and NFR-1 to NFR-12 suffice; no component NFR target is added (owner decision, 2026-10-22). The parent NFRs that bear most on this component are NFR-2 (no tool blocks the event loop) and NFR-5 (every tool result fits a byte budget, default 64 KB, and pages with a cursor beyond it) (PRD-v6 2.3; PRD-search-v1 FR-SRCH-06). Design defaults such as the 8 s search deadline (SRCH-FR-3) and the source timeouts stay in the LLD.

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |

## 2.6 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

Every item is personal and confidential (PRD-v6 2.4; owner decision, 2026-10-22). Retention uses the parent rule for the same kind of data, or the nearest parent rule where the parent does not list it (owner decision, 2026-10-22).

| Data | Classification | Source or owner | Retention | Notes |
| --- | --- | --- | --- | --- |
| Search records: query hash, sources, filters, statuses, timings | Personal, confidential (PRD-v6 2.4) | This component (SRCH-FR-9) | The life of the install: the parent rule for records and for daemon state (PRD-v6 2.4; owner decision, 2026-10-22) | For telemetry and the UI |
| Search query text | Personal, confidential (PRD-v6 2.4) | This component (SRCH-FR-9) | Kept only in debug logs, which rotate by size: 5 files of 10 MB (PLAT-FR-40; owner decision, 2026-10-22) | Stored only when debug logging is on |
| Work metadata and stored CSL snapshot | Personal, confidential (PRD-v6 2.4) | Upstream sources | The life of the install: the parent rule for records (owner decision, 2026-10-22); it outlives a discarded item's files so `cite` still works (SRCH-FR-23; CACHE-36) | Used by `cite` for archived and discarded items (SRCH-FR-23) |

## 2.7 Integrations and owners

> **Owner:** H confirms owners and SLAs · **Persona:** `architect` may draft · **Seed question:** 8

Kenny Hill owns every integration. No integration has an SLA; upstream services are best effort, tracked by probes (PRD-v6 2.5; owner decision, 2026-10-22).

| System | Owner | Relationship (depends on, feeds, replaces) | SLA |
| --- | --- | --- | --- |
| Sources component (adapter contract, registry, source groups, `web` group) | Kenny Hill | Depends on | None |
| Health component (source states that federation reads to skip sources, HLTH-FR-12) | Kenny Hill | Depends on | None |
| Platform component (tool envelope PLAT-FR-30, argument bounds PLAT-FR-31, budget, cursors) | Kenny Hill | Depends on | None |
| Cache component (cache state, stored metadata for `cite`, cache review for `check_integrity("cache")`) | Kenny Hill | Depends on and feeds | None |
| Upstream services: OpenCitations, OpenAlex, Semantic Scholar, ORCID, DBLP, Crossref update relations (including Retraction Watch records), and the OA sources in SRCH-FR-16 | Kenny Hill (third-party services) | Depends on | None; best effort, tracked by probes (PRD-v6 2.5) |
| v1 single-source tools (53 tools) | Kenny Hill | Replaces (PRD-v4 2) | None |

## 2.8 Product risks

> **Owner:** H · **Persona:** none

| Risk | Question | Assessment | Mitigation |
| --- | --- | --- | --- |
| Value | Will customers choose to use this? | Upstream APIs change faster than one person can follow (PRD-v6 2.10), and three default sources are degraded today (PRD-v6 1.1). If sources drop out silently, the merged list loses the reach that is the server's value (D1) (proposed for owner approval) | Every result reports each source's status and a failing source never fails the search (SRCH-FR-27, SRCH-INV-1); `auto` skips unhealthy sources and says so (SRCH-FR-8); probes and recorded fixtures make breakage visible (PRD-v6 2.10) (proposed for owner approval) |
| Usability | Can customers use it, including with accessibility needs? | v1 makes an agent juggle different argument names and result shapes across 53 tools, and repeats the same paper (PRD-v6 1.1, problem 1). A merged result that is too large or loosely shaped would be just as hard for an agent to use (proposed for owner approval) | One tool contract with an output schema (SRCH-20); bounded results with a combined cursor (NFR-5; SRCH-FR-6); `compact` detail by default (SRCH-FR-7); bad arguments rejected before any source is called (SRCH-21). The owner's direct surface is the local UI, whose usability is in [PRD-ui-v4](PRD-ui-v4.md) (proposed for owner approval) |
| Viability | Does it work for the business: economics, legal, compliance, operations? | Metered sources (OpenAlex budget, web-search providers) can run out mid-task or cost more than expected (PRD-v4 risks) | Federation skips exhausted sources and says so; web-search sources are off until configured, capped per day, and never in the default fan-out (PRD-v4 risks) |

## 2.9 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | As in PRD-v6 2.6: v1 stays read-only and running until cutover; cutover (M4) switches client configs, and v1 is archived after 14 days of daily use on v2 with no fallback to v1. By milestone: `search`, `get_work` and `list_sources` in M0; citations, `cite` and integrity checks in M1 (PRD-v7 2.9; owner decision, 2026-10-22) |
| Business conditions that must halt the rollout | The PRD-v7 2.6 conditions: any deletion without a recorded owner decision, any secret in an output, a fallback to v1 during the 14-day window, or a breach of any invariant, which includes SRCH-INV-1 to SRCH-INV-3 (PRD-v7 2.6; owner decision, 2026-10-22) |
| Support owner and escalation path | The owner is the only support; there is no escalation path (PRD-v6 2.6; owner decision, 2026-10-22) |
| Response targets by severity (S0 to S4) | None (PRD-v6 2.6; owner decision, 2026-10-22) |

## 2.10 Measurement and experimentation

> **Owner:** C · **Persona:** `product-writer` drafts; the owner decides

| Outcome | Measured by | Experiment (if any) |
| --- | --- | --- |
| OUT-2 (parent), latency | Owner check OC-12: five-source live search p95 under 8 s over 20 runs ([test plan](../../test/test-plan-v2.md) 3), at the M1 exit (PRD-v6 1.4) | None |
| OUT-2 (parent), tool calls | Tool calls per cross-source question in the parent 30-day review after cutover (PRD-v6 1.4) (proposed for owner approval) | None |

## 2.11 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

This component is done when every P1 criterion in 2.4 passes and the exit of the milestone that delivers it is met (PRD-v6 2.9). The owner check listed for this component in [the test plan](../../test/test-plan-v2.md) section 3, OC-12, counts. No extra demonstration is needed (owner decision, 2026-10-22). The OUT-2 tool-call measure is tracked 30 days after cutover as an outcome, not as a condition of done (PRD-v6 2.7).

## 2.12 Edge cases and error behavior

> **Owner:** A · **Persona:** `product-writer`

- A source still running at its timeout or at the deadline is cancelled and reported as `timeout` (SRCH-2).
- A failing source never fails the search; it gets a status entry (SRCH-3; SRCH-INV-1).
- A source whose cursor is exhausted reports `empty` on the next page (SRCH-7).
- Unconfigured, disabled and down sources are skipped by `auto` and reported with their status (SRCH-8), and so are `rate_limited` sources (SRCH-37). An explicit request for a `rate_limited` or `down` source tries it once (SRCH-FR-8).
- A source whose budget or daily cap is spent is reported `budget_exhausted` and skipped (SRCH-FR-27; HLTH-FR-12; SRC-29).
- Under the `web` fallback strategy, web sources the chain did not need report `not_needed` (SRCH-FR-27; SRC-30).
- Records with no shared identifier merge only when title, year and first author match, and the merge is flagged `fuzzy` (SRCH-5).
- Disagreeing fields across sources are recorded with their sources, not silently resolved (SRCH-9).
- Unknown identifier input raises `IdentifierError`; file-name shapes are rejected (SRCH-14; SRCH-INV-2).
- Invalid DOI forms are rejected (SRCH-10).
- URLs that differ only by a trailing slash normalize to the same form (SRCH-38).
- Out-of-range and unknown arguments are rejected before any source is called (SRCH-21).
- An unknown citation style or format is rejected, not replaced (SRCH-32; SRCH-INV-3).
- `full` detail still fits the response budget (SRCH-22).

## 2.13 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves before Gate 1

**Assumptions**

- The parent outcomes for every requirement are taken from the source PRD header (G1 and G2). Assumption: no requirement serves a different parent outcome.

**Resolved on 2026-10-22.** The owner answered every open question in PRD-search-v2: why now (1.1); user group sizes (1.2); the reasons for the non-goals (1.3); no component outcomes or NFRs (1.4, 2.5); leaps of faith and product risks, drafted for approval (1.5, 2.8); the invariants SRCH-INV-1 to SRCH-INV-3 (1.6); user stories SRCH-US-1 to SRCH-US-6, drafted for approval (2.2, 2.4); state names `budget_exhausted` and `not_needed` (1.7, SRCH-FR-27); the `rate_limited` skip (SRCH-37) and the trailing slash (SRCH-38), added as new criteria so SRCH-8 and SRCH-13 keep their wording (2.4); GitHub identifiers in SRCH-FR-28 (2.4); `cite` in M1 (1.7, 2.9); SRCH-FR-23 and SRCH-FR-26 verified by CACHE-36 and CACHE-35 (2.4); data handling (2.6); integration owners (2.7); rollout and support (2.9); and done (2.11). SPEC-v3 11.1 and the `SourceStatus` literal in LLD-search v1 still say `skipped_budget`; they follow this answer in their next versions.

**Gate 1 follow-up (owner decision, 2026-10-22).** Collection export through `cite` is verified by CACHE-63 in the cache component, an M2 criterion, so SRCH-32 stays as written. A breach of any invariant halts the rollout (PRD-v7 2.6).

## 2.14 Glossary

> **Owner:** A · **Persona:** `product-writer`

| Term | Definition |
| --- | --- |
| Federated search | One `search` call that runs many sources concurrently and returns one merged, ranked list with per-source status (PRD-search-v1 1, 2.1) |
| `auto` selection | The default source selection: enabled, healthy sources from the groups that fit the filters (default groups `scholarly` and `preprints`) (SRCH-FR-2) |
| `source_status` | The per-source entry in every result: state, result count, latency, retry-after and classified error code (SRCH-FR-27) |
| `budget_exhausted` | The state of a source whose budget or daily cap is spent; it is skipped until the reset time (SRCH-FR-27; HLTH-FR-12) |
| `not_needed` | The state of a `web` source that the `fallback` chain did not call because an earlier source answered (SRCH-FR-27; SPEC-v2 5.5) |
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

Two requirements left this PRD in this version: each was superseded by a new ID because its behavior changed (owner decision, 2026-10-22).

| ID | Status | Replaced by | Reason |
| --- | --- | --- | --- |
| SRCH-FR-4 | superseded | SRCH-FR-27 | The response changed: state `skipped_budget` becomes `budget_exhausted`, and `not_needed` is added for the `web` fallback (owner decision, 2026-10-22) |
| SRCH-FR-10 | superseded | SRCH-FR-28 | The response changed: GitHub identifiers (`github:` ids and GitHub URLs) are normalized (owner decision, 2026-10-22) |

Changes in version 3 that keep their ID, and IDs added in version 3. The first column is not headed `ID` so that spec-lint does not read these rows as definitions.

| Changed or new ID | Change | Date | Reason |
| --- | --- | --- | --- |
| SRCH-FR-27 | New: replaces SRCH-FR-4; the response changed: state `skipped_budget` becomes `budget_exhausted`, and `not_needed` is added for the `web` fallback | 2026-10-22 | owner decision, 2026-10-22 |
| SRCH-FR-28 | New: replaces SRCH-FR-10; the response changed: GitHub identifiers (`github:` ids and GitHub URLs) are normalized | 2026-10-22 | owner decision, 2026-10-22 |
| SRCH-37 | New criterion: When `sources` is `auto`, the federation service shall skip `rate_limited` sources and report each one's status. | 2026-10-22 | owner decision, 2026-10-22 |
| SRCH-38 | New criterion: The identity module shall normalize the trailing slash of a URL. | 2026-10-22 | owner decision, 2026-10-22 |
| SRCH-INV-1 | Added: a failing source never fails the search (from SRCH-FR-27) | 2026-10-22 | Owner decision, 2026-10-22 |
| SRCH-INV-2 | Added: identity is never derived from a file name (from SRCH-FR-13) | 2026-10-22 | Owner decision, 2026-10-22 |
| SRCH-INV-3 | Added: unknown citation styles and formats are never silently replaced (from SRCH-FR-22) | 2026-10-22 | Owner decision, 2026-10-22 |
| SRCH-US-1 to SRCH-US-6 | Added: user stories drafted for owner approval | 2026-10-22 | Owner decision, 2026-10-22 |

### Gate 1: Requirements approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

## 2.16 Earlier IDs

> **Owner:** A · **Persona:** `product-writer`

| Earlier ID | New ID |
| --- | --- |
| FR-SRCH-01 | SRCH-FR-1 |
| FR-SRCH-02 | SRCH-FR-2 |
| FR-SRCH-03 | SRCH-FR-3 |
| FR-SRCH-04 | SRCH-FR-4 (superseded by SRCH-FR-27) |
| FR-SRCH-05 | SRCH-FR-5 |
| FR-SRCH-06 | SRCH-FR-6 |
| FR-SRCH-07 | SRCH-FR-7 |
| FR-SRCH-08 | SRCH-FR-8 |
| FR-SRCH-09 | SRCH-FR-9 |
| FR-SRCH-10 | SRCH-FR-10 (superseded by SRCH-FR-28) |
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
