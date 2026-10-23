---
title: "Sources"
type: prd-component
version: 5
status: approved
approved_by: "Kenny Hill (Product)"
approved: 2026-10-22
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
prefix: SRC
component: sources
parent: docs/prd/PRD-v7.md
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
supersedes: docs/prd/components/PRD-sources-v4.md
date: 2026-10-22
---

# Component PRD: Sources (v5)

This version supersedes [PRD-sources v4](PRD-sources-v4.md), which moved [PRD-sources v3](../../../docs-archive/prd/components/PRD-sources-v3.md) onto the component PRD template. Version 5 records the owner's Gate 1 answers of 2026-10-22. Requirements and criteria keep their meaning and IDs except where section 2.15 records a change; earlier IDs map to current ones in section 2.16. Parent: [PRD v7](../PRD-v7.md), outcomes OUT-1 and OUT-3. Vision: [vision-v2](../../vision/vision-v2.md). Design: [SPEC-v3](../../spec/SPEC-v3.md) and [LLD-sources v1](../../lld/LLD-sources-v1.md); ADRs [0006](../../adr/0006-source-adapter-contract.md) and [0012](../../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md).

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

- Horizontal reach is the product, across any subject area. This component defines how a source is added, described, called, tested and switched off, and which sources v2 ships with (PRD-sources-v3 1).
- The value of the server is its horizontal reach: many sources, one server. Merge tools, not sources. Add sources where they are cheap to keep healthy (owner decision D1, REVIEW-v1 1).
- v1 has no source abstraction: DSpace is 8 copy-paste tools, adding a source touches 5 places, and there is no way to disable one (REVIEW-v1 3, finding 6). Rate limits exist for 3 of about 25 sources (ADR 0006).
- Breakage is silent: three sources are degraded by upstream changes today (OpenAlex, Semantic Scholar, Crossref) and one has an announced shutdown (Google Programmable Search, 2027-01-01). Nothing in v1 noticed (PRD-v4 2, item 2).
- **Why now.** v2 is a rebuild, and the upstream breakage is current: the live probes of 2026-10-19 found OpenAlex keyless calls rejected for budget, Semantic Scholar bulk search ignoring `limit`, Crossref throttling clients without a contact email, and Google Programmable Search closed to new customers ahead of its shutdown on 2027-01-01. The review found v1 is not a sound base for the next year of use (PRD-v7 1.1; owner decision, 2026-10-22).
- Parent context: goals G1 "Breadth" and G3 "Cheap to maintain" (PRD-v4 3.1), now OUT-1 and OUT-3 in [PRD v7](../PRD-v7.md).

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| The owner, through an agent (Claude Code, Claude desktop, Codex, OpenClaw agents) | Search, fetch, read and cite research from many sources through one MCP server (PRD-v4 1, 4) | One person; the only end user; remote and multi-user access are non-goals (PRD-v6 1.2; PRD-v4 3.2) |
| The owner, directly, through the local web UI | Check the source board; see site sets, read-only, on the settings page, and edit them in the config file or with `research-mcp config set` (PRD-v4 4; SRC-FR-18; UI-FR-21) | One person (PRD-v6 1.2) |
| The ECC orchestrator and coding agents | Build v2 one work unit at a time, including adding a source in one unit (PRD-v4 4; PRD-v4 7) | Not a product measure (owner decision, 2026-10-22) |

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- How a source is added, described, called, tested and switched off (PRD-sources-v3 1).
- The source catalog below: which sources v2 ships with (PRD-sources-v3 1, 3).
- Named site sets and the optional `web` group of web-search sources (PRD-sources-v3 changes from v2; ADR 0012).
- Upstream MCP servers as a source kind, and owner-configured docs-site instances (SRC-FR-10, SRC-FR-15, SRC-FR-17).

Every non-goal below already states its reason; this component adds no non-goal beyond them and the parent's (PRD-v6 1.3; owner decision, 2026-10-22).

| Non-goal | Why it is excluded |
| --- | --- |
| Limiting coverage to one subject area | Requirements are domain-neutral; topic coverage is configuration (PRD-v4 3.2; ADR 0012) |
| Scraping Google Scholar | Parent non-goal: not needed, because OpenAlex, Semantic Scholar, Crossref and the other scholarly sources cover it; paid web-search providers are allowed only as optional sources with a daily cap (PRD-v6 1.3; PRD-v4 3.2) |
| Migrating or changing the owner's separate K-12 teacher server | Only three of its free reference sources join the catalog; its other sources stay there (PRD-sources-v3 changes from v2) |
| Keeping v1 tool names or result shapes | Parent non-goal; clients are updated at cutover (PRD-v4 3.2) |

**Source catalog.** Groups help federated search pick defaults (for example `scholarly` and `preprints` for a literature question). "Auth" names Keychain items (`research-mcp/<NAME>`). "M" is the milestone that delivers the adapter (PRD-sources-v3 3).

| # | Source id | Group | Capabilities | Auth | Notes | M |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `arxiv` | preprints | search, get, fulltext | none | https only; 1 request per 3 s across all clients | M0 |
| 2 | `crossref` | scholarly | search, get, updates | contact email | polite pool needs `mailto` | M0 |
| 3 | `openalex` | scholarly | search, get, fulltext, citations, authors | `OPENALEX_API_KEY` | usage budget; use `topics`, `last_known_institutions`; page size 100 | M0 |
| 4 | `semantic_scholar` | scholarly | search, get, citations | `SEMANTIC_SCHOLAR_API_KEY` (optional) | `/paper/search` for interactive; bulk only in jobs | M1 |
| 5 | `datacite` | scholarly | search, get | none | port the existing adapter | M1 |
| 6 | `core` | scholarly | search, get, fulltext | `CORE_API_KEY` | key never sent to non-CORE hosts | M1 |
| 7 | `unpaywall` | scholarly | fulltext (OA locator) | contact email | no placeholder email | M1 |
| 8 | `openaire` | scholarly | search, get | none | EU aggregator | M1 |
| 9 | `doaj` | scholarly | search | none | OA journals | M1 |
| 10 | `zenodo` | scholarly | search, get, fulltext | `ZENODO_TOKEN` (optional) | datasets, software, reports | M1 |
| 11 | `hal` | scholarly | search, get, fulltext | none | French OA archive | M1 |
| 12 | `dblp` | scholarly | search | none | bot protection from datacenter IPs; fine from the Mac | M1 |
| 13 | `orcid` | scholarly | authors | none | author identity | M1 |
| 14 | `ads` | scholarly | search, get, citations | `ADS_API_TOKEN` | disabled by default | M1 |
| 15 | `lens` | scholarly | search | `LENS_API_TOKEN` | patents; disabled by default | M1 |
| 16 | `osf` | preprints | search, get, fulltext | none | providers as a filter (PsyArXiv, SocArXiv) | M1 |
| 17 | `biorxiv` | preprints | get, fulltext | none | discovery through Europe PMC and Crossref | M1 |
| 18 | `medrxiv` | preprints | get, fulltext | none | as above | M1 |
| 19 | `ssrn` | preprints | search, get | none | through Crossref prefix 10.2139; PDFs often need login | M1 |
| 20 | `hf_papers` | preprints | search | none | ML papers with code; cap response size | M1 |
| 21 | `europe_pmc` | biomed | search, get, fulltext | none | port the existing adapter; add PMC OA full text | M1 |
| 22 | `pubmed` | biomed | search, get | `NCBI_API_KEY` (optional) | E-utilities | M1 |
| 23 | `clinical_trials` | biomed | search, get | none | port the existing adapter | M1 |
| 24 | `dspace_mit` | repositories | search, get, fulltext | none | DSpace adapter instance; version recorded | M1 |
| 25 | `dspace_harvard` | repositories | search, get, fulltext | none | instance | M1 |
| 26 | `dspace_cornell` | repositories | search, get, fulltext | none | instance | M1 |
| 27 | `dspace_penn` | repositories | search, get, fulltext | none | UPenn ScholarlyCommons; DSpace 7.6 | M1 |
| 28 | `ietf` | standards | search, get, fulltext | none | Datatracker and RFC Editor; status and obsoletes | M1 |
| 29 | `nist` | standards | search, get, fulltext | none | Crossref prefix 10.6028 plus CSRC pages | M1 |
| 30 | `nvd` | standards | search, get | `NVD_API_KEY` (optional) | CVE API 2.0 | M1 |
| 31 | `aws_knowledge` | vendor_docs | search, get | none | official AWS Knowledge MCP server (upstream MCP) | M1 |
| 32 | `ms_learn` | vendor_docs | search, get | none | official Microsoft Learn MCP server (upstream MCP) | M1 |
| 33 | `google_devknowledge` | vendor_docs | search, get | `GOOGLE_DEVKNOWLEDGE_API_KEY` | v1 API; key in `x-goog-api-key` header | M1 |
| 34 | `docs_site` | vendor_docs | search (local), get, crawl | none | owner-configured instances (`docs_site_<name>`), each with an allowlist; v1's six crawl projects ship as defaults | M1 |
| 35 | `github` | code | search, get | `GITHUB_TOKEN` | repos, code (needs token), README | M1 |
| 36 | `opencitations` | integrity | citations | `OPENCITATIONS_TOKEN` (optional) | port the existing adapter | M1 |
| 37 | `crossref_updates` | integrity | updates | contact email | retractions and corrections, including Retraction Watch records | M1 |
| 38 | `eric` | education | search, get | none | education research | M1 |
| 39 | `vertex_search` | web | search | Google sign-in (Application Default Credentials); `gcp` extra | instances `vertex_<name>` with project, location, engine id; metered, capped; first in the fallback order | M1 |
| 40 | `brave_search` | web | search | `BRAVE_SEARCH_API_KEY` | key in the `X-Subscription-Token` header; metered, capped; long site sets split into batches | M1 |
| 41 | `serpapi` | web | search | `SERPAPI_API_KEY` | key accepted only as a query parameter (URL never logged); metered, capped | M1 |
| 42 | `google_pse` | web | search | `GOOGLE_DEVKNOWLEDGE_API_KEY` (shared with source 33, as in v1) | engine id in settings; key in the `x-goog-api-key` header; shutdown announced for 2027-01-01, shown as `deprecated(days)` | M1 |
| 43 | `loc` | reference | search, get, fulltext | none | Library of Congress JSON API (`fo=json`): photos, manuscripts, maps, books, newspapers; rate from LoC's published per-endpoint limits | M1 |
| 44 | `open_library` | reference | search, get | none | books and editions by title, author, subject or ISBN; metadata and cover links only, no lending | M1 |
| 45 | `wikipedia` | reference | search, get, fulltext | none | English Wikipedia search and summaries; full article text through `fetch` and `read`; descriptive user agent with the owner contact, as Wikimedia asks | M1 |

**Changed from v1.** v1's single web-search tool and its four providers become the four `web` sources above (SRC-FR-19 to SRC-FR-22). Nothing it called is removed (PRD-sources-v3 3.1).

**Removed from v1** (PRD-sources-v3 3.2):

| v1 tool or source | Reason |
| --- | --- |
| Undocumented AWS docs and Microsoft Learn site-search endpoints | Replaced by the vendors' official MCP servers (sources 31 and 32), which cover the same documentation. This is the only substitution under SRC-FR-17. |
| Separate PsyArXiv tool | Becomes an OSF provider filter. |

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |
| SRC-OUT-1 | Sources registered, each listed on the source board, and v1 endpoints mapped to a v2 source (parent OUT-1, PRD-v4 G1 measure) | v1 reaches about 25 upstream services (REVIEW-v1 2) | At least 45 sources registered; every v1 endpoint mapped to a v2 source (PRD-v6 OUT-1, approved; PRD-v4 G1; PRD-v4 7) | End of M1 (PRD-v6 OUT-1); 45 or more still registered 30 days after cutover (PRD-v6 OUT-1; PRD-v4 7) |
| SRC-OUT-2 | Work needed to add a new source (parent OUT-3, PRD-v4 G3 measure) | Adding a source touches five places (PRD-v4 2, item 4) | One adapter file and one fixtures folder; no other hand-written file changes (PRD-v4 G3); one work unit for a new free source, agent-built (PRD-v4 7) | Measured 30 days after cutover (PRD-v4 7) |

SRC-OUT-2 holds as written: a new source's Keychain name lives in its `SourceSpec` and the generated inventory, so adding a source needs no SPEC edit (owner decision, 2026-10-22; see 1.7). No other component outcome is added; the parent outcomes OUT-1 to OUT-8 suffice (owner decision, 2026-10-22).

## 1.5 Leaps of faith

> **Owner:** H · **Persona:** none

Drafted by the product writer from the sources; each bet was approved by the owner at Gate 1, 2026-10-22 (owner decision, 2026-10-22, to draft them).

| Leap of faith | How we will validate it | By when |
| --- | --- | --- |
| Every catalog source fits one adapter contract with a declarative `SourceSpec`; only unusual upstreams (upstream MCP servers, crawled docs sites) need small base classes of their own (ADR 0006 decision and consequences) | SRC-20 (conformance passes for every M1 adapter), with SRC-21, SRC-22 and SRC-23 for the instance, upstream MCP and docs-site kinds | M1 exit |
| Adding a source is one module and one fixtures folder, and an agent can add a new free source in one work unit (ADR 0006 consequence; PRD-v6 OUT-3) | Owner check OC-11 (test plan section 3); the OUT-3 30-day measure confirms it afterward | M1 exit |
| The metered web-search sources stay affordable when they are off until configured, capped per day, outside the default fan-out and called in fallback order (ADR 0012 decision 4; PRD-v6 2.10, metered spend risk) | SRC-28 (never in auto selection), SRC-29 (daily cap) and SRC-30 (one paid query per page under `fallback`) | M1 exit |

## 1.6 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

The owner confirmed SRC-INV-1 to SRC-INV-6 as the invariants of this component (owner decision, 2026-10-22). Each names the P1 criterion that verifies it.

| ID | The system must never | Source (regulation, policy, contract) | Verified by (P1) |
| --- | --- | --- | --- |
| SRC-INV-1 | Call a disabled source | SRC-FR-5; PRD-sources-v3 | SRC-3 |
| SRC-INV-2 | Let an adapter sleep, retry, read secrets, write files, log request URLs with credentials, or import an HTTP library | SRC-FR-3; PRD-sources-v3; ADR 0006 | SRC-7; SRC-6 (injected sleeper) |
| SRC-INV-3 | Fetch or crawl a docs-site host or path outside its allowlist, or match its filters on a substring of the URL | SRC-FR-15; PRD-sources-v3 | SRC-23 |
| SRC-INV-4 | Put a web-search source in the default fan-out | SRC-FR-19; PRD-sources-v3; ADR 0012; PRD-v6 INV-9 | SRC-28 |
| SRC-INV-5 | Open or copy the Google sign-in credential file, keep its access token anywhere but memory, or send the token to any host other than `discoveryengine.googleapis.com` (includes the rule of SEC-INV-11) | SRC-FR-23; PRD-sources-v3; ADR 0012; NFR-3 | SRC-32 |
| SRC-INV-6 | Send a source's key to a host outside that source (for example the CORE key to a non-CORE host) (same rule as SEC-INV-5) | PRD-sources-v3 3 (source 6); PLAT-FR-12; PRD-v6 INV-3 | SEC-8 ([PRD-security-v2](PRD-security-v2.md)) |

## 1.7 Known constraints and decisions

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

| Decision or constraint | Status (made or open) | Rationale or link |
| --- | --- | --- |
| Every source is an adapter with a declarative `SourceSpec`; one registry discovers adapters and builds configured instances | Made (ADR status: proposed; accepted when the owner approves the PRD at Gate 1, PRD-v6 1.6) | [ADR 0006](../../adr/0006-source-adapter-contract.md) |
| Requirements are domain-neutral; every v1 endpoint stays reachable; web search is an optional, capped `web` group | Made, accepted 2026-10-19 | [ADR 0012](../../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md); supersedes D7 and O1 |
| Library of Congress, Open Library and Wikipedia join as the `reference` group (sources 43 to 45) | Made, owner decision of 2026-10-19 | PRD-sources-v3 changes from v2; PRD-v4 |
| Horizontal reach is the value: merge tools, not sources; add sources where they are cheap to keep healthy | Made | Owner decision D1 (REVIEW-v1 1) |
| "Penn" means UPenn ScholarlyCommons | Made | Owner decision D8 (REVIEW-v1 1) |
| Decommission the Google-based general web search (Programmable Search) | Superseded | D7 (REVIEW-v1 1), superseded by ADR 0012 |
| Secrets live in the macOS Keychain; config holds references. The one exception is the owner's Google sign-in for Vertex AI Search, which `gcloud` stores and v2 never copies | Made | [ADR 0003](../../adr/0003-secrets-in-keychain.md); ADR 0012; NFR-3 |
| Register free OpenAlex and Semantic Scholar keys; OpenAlex is unusable without one | Made (O2 closed) | PRD-v6 1.6; owner decision, 2026-10-22 |
| The AWS and Microsoft Learn MCP servers run through v2 as sources, so they appear on the source board and in federated search (SRC-FR-10) | Made (O6 closed) | PRD-v6 1.6; ADR 0012 decision 2; owner decision, 2026-10-22 |
| Every adapter ships seven recorded fixtures; the definition of done uses seven | Made | SRC-FR-8; ADR 0006; SPEC-v2 5.2; owner decision, 2026-10-22 |
| The M1 exit is 45 or more sources registered, not 38 | Made | PRD-v6 OUT-1 (approved); owner decision, 2026-10-22 |
| `tools/gen_inventory.py` generates the source inventory and its `--check` flag gates it; there is no `research-mcp sources --markdown` command | Made | SPEC-v2 12.1, 12.3; SRC-13; owner decision, 2026-10-22 |
| A placeholder contact address (example.com, example.org, .test, .invalid) is rejected by settings validation with a clear message, so the daemon does not start until it is fixed; with no address set, only the sources with `needs_contact` become `unconfigured` and the daemon starts | Made | SPEC-v2 2; PLAT-11; owner decision, 2026-10-22 |
| A new source's Keychain name lives in its `SourceSpec` and the generated inventory, so no SPEC edit is needed. The SPEC-v2 5.4 step 5 instruction (carried into the new-source checklist of LLD-sources-v1 5.5) is superseded; the LLD changes at Gate 3 | Made | SRC-OUT-2; SRC-FR-26; owner decision, 2026-10-22 |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| Kenny Hill (Product) | 2026-10-22 | Approved in chat; recorded by Claude in the owner's name at his direction |

---

## 2.1 Customer discovery

> **Owner:** A · **Persona:** `analyst`

The v1 review (REVIEW-v1, 2026-10-19) is the research behind this component. Findings that drive it:

- No source abstraction: DSpace is 8 copy-paste tools; adding a source touches 5 places; no way to disable one (REVIEW-v1 3, finding 6; ARCH-04, FUNC-12).
- Live probes of every upstream API on 2026-10-19 found these changes (REVIEW-v1 4): OpenAlex moved to a usage-priced budget per API key; Semantic Scholar `/paper/search/bulk` ignores `limit`; Crossref has new rate tiers and needs `mailto` to leave the public pool; Google Programmable Search is closed to new customers and shuts down 2027-01-01; Brave's free tier was removed; AWS docs and Microsoft Learn now ship official, unauthenticated MCP servers; the Google Developer Knowledge API `v1` is GA; UPenn ScholarlyCommons runs DSpace 7.6, not 8.
- The review's first response for Programmable Search, Brave and Vertex AI Search was removal (D7, O1); ADR 0012 reversed it and keeps all four web providers as optional, capped sources.

No documents in `docs/research/` cover this component yet.

## 2.2 User stories and priority

> **Owner:** C for stories (`product-writer`), H for priority · **Seed question:** 3

Drafted by the product writer and approved by the owner at Gate 1, 2026-10-22 (owner decision, 2026-10-22, to draft them). A story is P1 when a Must (P1) requirement serves it, otherwise P2.

| ID | As a... I want... so that... | Priority | Why this priority |
| --- | --- | --- | --- |
| SRC-US-1 | As the owner (through an agent), I want one MCP server to reach every source v1 called and the new catalog sources, in any subject area, with results in one normalized shape, so that one question can span many sources without my knowing each upstream API (PRD-v6 1.2; D1). | P1 | SRC-FR-17 (every v1 endpoint stays reachable) is P1, as are SRC-FR-1, SRC-FR-4, SRC-FR-9 and SRC-FR-15 |
| SRC-US-2 | As the owner (through an agent), I want each source's state and, for an unconfigured or deprecated source, the exact fix or the shutdown date, so that a missing key, extra or contact address never fails silently (PRD-v6 1.1, items 2 and 3; PRD-v6 1.2). | P1 | SRC-FR-6 and SRC-FR-24 are P1 |
| SRC-US-3 | As the owner (through an agent), I want the metered web-search sources to run only when I name them, under a daily cap, in a fallback order and optionally limited to a site set, so that web search stays available without uncontrolled spend (ADR 0012 decision 4; PRD-v6 2.10). | P1 | SRC-FR-19 to SRC-FR-23 are P1 |
| SRC-US-4 | As the owner (directly), I want to disable a source in configuration or from the UI, and to add, edit or remove site sets in the config file or with `research-mcp config set` (the UI Settings page shows them read-only, UI-FR-21), without a code change, so that I can react to upstream breakage and set coverage myself (PRD-v6 1.2; 1.2 above). | P1 | SRC-FR-5 and SRC-FR-18 are P1 |
| SRC-US-5 | As the ECC orchestrator, I want every source built to one adapter contract with seven recorded fixtures, one conformance suite and a generated inventory, so that a new source is one work unit that touches only one adapter module and one fixtures folder (PRD-v6 1.2; OUT-3; 1.2 above). | P1 | SRC-FR-26 is P1, as are SRC-FR-2, SRC-FR-3, SRC-FR-8 and SRC-FR-25 |
| SRC-US-6 | As the owner (directly), I want an opt-in live check that calls each enabled source once and writes refreshed fixtures for my review, so that an upstream change shows up before an agent hits it (PRD-v6 1.1, item 2; PRD-v6 2.10, upstream change risk). | P2 | Only SRC-FR-12 serves it, and it is P2 |

## 2.3 User experience

> **Owner:** C · **Persona:** `product-writer` drafts the narrative; designers own the design artifacts · **Seed question:** 3

- An agent calls `search` without naming sources; federation picks the default groups and skips sources that are `disabled` or `unconfigured`, reporting that status (SRC-FR-5, SRC-FR-6; SRC-US-1, SRC-US-2). Web-search sources run only when the caller names the `web` group or a web source, optionally with a `site_set` (SRC-FR-19, SRC-FR-22; SRC-US-3).
- An agent or the owner lists sources with `list_sources` or the `research://sources` resource and sees each source's state and, for an unconfigured one, the exact fix: the Keychain item name and signup URL, or the install command for a missing extra (SRC-FR-6, SRC-FR-7; SRC-8; SRC-US-2).
- The owner disables a source in configuration or from the UI without a code change (SRC-FR-5), and adds, edits or removes site sets in the config file or with `research-mcp config set`; the UI settings page shows them (SRC-FR-18; SRC-US-4).
- The owner runs the opt-in live check, `research-mcp sources check --live`, to call each enabled source once and refresh fixtures for review (SRC-FR-12; SRC-US-6).
- A coding agent adds a source as one adapter module, one fixtures folder and its tests, then the closing unit regenerates the inventory with `tools/gen_inventory.py` (SRC-FR-25, SRC-FR-26; SRC-US-5).

## 2.4 Functional requirements and acceptance criteria

> **Owner:** C · **Persona:** `product-writer` drafts requirements and criteria as options; the owner selects and approves · **Seed questions:** 3, 12

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| SRC-FR-1 | Every source is described by a declarative `SourceSpec`: id, title, group, capabilities, identifier schemes it understands, auth (credential names, header or query placement, required or optional, signup URL), rate policy (requests per second, burst, concurrency, daily quota), timeout, maximum page size, contact-email requirement, optional dependency extras, health probe, default enabled flag, and status note (for example a shutdown date). | SRC-US-1 | OUT-1, OUT-3 | P1 |
| SRC-FR-2 | Every source is implemented by one adapter module that satisfies the `SourceAdapter` contract: `search`, `get`, `fulltext_candidates`, `citations` (where supported) and `probe`. Unsupported capabilities are declared in the spec, not stubbed. | SRC-US-5 | OUT-1, OUT-3 | P1 |
| SRC-FR-3 | Adapters only translate between the upstream API and the normalized models. They never sleep, retry, read secrets, write files, log request URLs with credentials, or import an HTTP library; all I/O goes through the shared `HttpPort`. | SRC-US-5 | OUT-1, OUT-3 | P1 |
| SRC-FR-4 | A registry discovers adapters at startup, builds configured instances, and exposes them by id and by group. Two or more instances of one adapter (for example four DSpace repositories, several docs sites) are created from configuration alone. | SRC-US-1 | OUT-1, OUT-3 | P1 |
| SRC-FR-5 | Any source can be disabled in configuration or from the UI without a code change. Disabled sources are never called, are listed with state `disabled`, and are skipped by federated search with that status. | SRC-US-4 | OUT-1, OUT-3 | P1 |
| SRC-FR-6 | A source whose required credential is missing is listed as `unconfigured` with the exact fix (Keychain item name and signup URL) and is skipped by federated search. | SRC-US-2 | OUT-1, OUT-3 | P1 |
| SRC-FR-7 | A source whose optional dependency extra is not installed is listed as `unconfigured` with the install command. | SRC-US-2 | OUT-1, OUT-3 | P2 |
| SRC-FR-8 | Every adapter ships seven recorded fixtures: a normal search result, an empty result, a normal get result, HTTP 429 with `Retry-After`, HTTP 5xx, a malformed body, and an oversize marker. A conformance suite parametrized over the registry runs the same checks against every adapter. | SRC-US-5 | OUT-1, OUT-3 | P1 |
| SRC-FR-9 | Every adapter maps upstream records to the normalized `WorkRecord` with provenance (source id, upstream id, adapter version, retrieval time) and normalized identifiers. | SRC-US-1 | OUT-1, OUT-3 | P1 |
| SRC-FR-10 | Upstream MCP servers (AWS Knowledge, Microsoft Learn) are supported as a source kind: the adapter calls the upstream server through a platform MCP client port built on the shared HTTP client, so rate limits, host policy, telemetry and redaction still apply, and maps its results. | SRC-US-1 | OUT-1, OUT-3 | P2 |
| SRC-FR-24 | Sources that ask for a contact email or a descriptive user agent (Crossref, Unpaywall, arXiv, OpenAlex) receive the configured owner contact. Settings validation rejects a placeholder `contact.email` (example.com, example.org, .test, .invalid) with a clear message, so the daemon does not start until it is fixed; with no address set, only the sources with `needs_contact` become `unconfigured` and the daemon starts (SPEC-v2 2; PLAT-11). | SRC-US-2 | OUT-1, OUT-3 | P1 |
| SRC-FR-12 | An opt-in live check (`research-mcp sources check --live`) calls each enabled source once and can refresh its fixtures for review. | SRC-US-6 | OUT-1, OUT-3 | P2 |
| SRC-FR-25 | The source inventory (`docs/generated/sources.md`, linked from the README and agent instructions) is generated from the registry by `tools/gen_inventory.py`; its `--check` flag fails CI if the committed inventory is stale. | SRC-US-5 | OUT-1, OUT-3 | P1 |
| SRC-FR-14 | Sources with an announced shutdown carry the date in their spec and show `deprecated(days)` until removed. | SRC-US-2 | OUT-1, OUT-3 | P2 |
| SRC-FR-15 | Docs-site sources fetch and crawl only hosts and path prefixes on their allowlist, honor `robots.txt`, and match filters on the parsed host and path, never on a substring of the URL. | SRC-US-1 | OUT-1, OUT-3 | P1 |
| SRC-FR-26 | Adding a new source requires only one adapter module (discovered automatically), one fixtures folder, and its acceptance tests; the generated inventory is refreshed. The new-source checklist (SPEC-v2 5.4) without its step 5 is the definition of done: the Keychain name lives in the `SourceSpec` and the generated inventory, so no SPEC edit is needed. | SRC-US-5 | OUT-1, OUT-3 | P1 |
| SRC-FR-17 | Every upstream service v1 calls stays reachable through a v2 source (the mapping is in the migration tool map). The one substitution: v1's undocumented AWS and Microsoft Learn site-search endpoints are replaced by those vendors' official MCP servers, which cover the same documentation. v1's docs-domain list and crawl projects ship in the default configuration as editable data, not code. | SRC-US-1 | OUT-1, OUT-3 | P1 |
| SRC-FR-18 | Named site sets (a name and a list of domains) are configuration. The default configuration holds v1's docs-domain list as the site set `v1_docs`. The owner can add, edit or remove site sets in the config file (or with `research-mcp config set`) without a code change; the UI settings page shows them. | SRC-US-4 | OUT-1, OUT-3 | P1 |
| SRC-FR-19 | The `web` group holds the optional web-search sources: `vertex_search` (one instance per Vertex AI Search engine, `vertex_<name>`), `brave_search`, `serpapi` and `google_pse`. Each is disabled until its settings and credential are present, is never in the default fan-out, and runs only when a caller names the group or the source. | SRC-US-3 | OUT-1, OUT-3 | P1 |
| SRC-FR-20 | Each web-search source has a daily call cap (default 100, owner-set). At the cap the source reports `budget_exhausted` until the next local midnight, and federated search skips it with that status. | SRC-US-3 | OUT-1, OUT-3 | P1 |
| SRC-FR-21 | Within the `web` group, the strategy is `fallback` by default: call the configured sources in order (default order: Vertex, Brave, SerpAPI, Programmable Search) and stop at the first that returns results without error. `all` calls every configured web source and merges the results. The order and strategy are settings. | SRC-US-3 | OUT-1, OUT-3 | P1 |
| SRC-FR-22 | `search` accepts an optional `site_set`. Brave, SerpAPI and Programmable Search restrict results to that set's domains (splitting the domain list into several queries when a provider limits query length, as v1 does for Brave); a Vertex engine's scope is set in Google Cloud, so `site_set` filters its results after the call. An unknown set name is `invalid_argument`. | SRC-US-3 | OUT-1, OUT-3 | P1 |
| SRC-FR-23 | `vertex_search` authenticates with the owner's Google sign-in (Application Default Credentials) through the optional `gcp` extra; its own code never opens or copies the credential file (the `google-auth` library reads it), keeps the access token in memory only, and sends it only to `discoveryengine.googleapis.com`. Project, location and engine id are settings, not secrets. | SRC-US-3 | OUT-1, OUT-3 | P1 |

| ID | Criterion | Requirement | Priority | Level | Milestone |
| --- | --- | --- | --- | --- | --- |
| SRC-1 | The `SourceSpec` validation shall reject a spec that lacks a required field, has a rate or timeout outside its bounds, or sets auth with empty auth origins. | SRC-FR-1 | P1 | unit | M0 |
| SRC-2 | The source registry shall discover the built-in adapters and build two instances of one adapter from configuration alone. | SRC-FR-4 | P1 | unit | M0 |
| SRC-3 | If a source is disabled, then the system shall never call it and report its state as `disabled`. | SRC-FR-5 | P1 | unit | M0 |
| SRC-4 | If a source is missing a required credential, or a source with `needs_contact` has `contact.email` unset, then the system shall report it as `unconfigured` with the exact fix. | SRC-FR-6, SRC-FR-24 | P1 | unit | M0 |
| SRC-5 | If a source is missing an optional extra, then the system shall report it as `unconfigured` with the install command. | SRC-FR-7 | P2 | unit | M0 |
| SRC-6 | The conformance suite shall run the eight checks of SPEC 5.2, with an injected sleeper and `FakeClock`, against every registered adapter, which in this unit is the fake adapter from `research_mcp.testing.adapters`. | SRC-FR-2, SRC-FR-8, SRC-FR-9 | P1 | unit | M0 |
| SRC-7 | The static check shall fail when any module under `sources/` imports `httpx`, `requests`, `urllib.request`, `http.client`, `socket` or `research_mcp.platform.secrets`, or calls `time.sleep` or `asyncio.sleep` (`urllib.parse` is allowed). | SRC-FR-3 | P1 | unit | M0 |
| SRC-10 | The arXiv adapter shall pass conformance (run with `-k`), use https, map versions, and declare a spec rate of 1 request per 3 s with concurrency 1. | SRC-FR-8, SRC-FR-9, NFR-8 | P1 | integration | M0 |
| SRC-11 | The Crossref adapter shall pass conformance (run with `-k`), send `mailto`, map DOIs and issued dates, and declare the updates capability. | SRC-FR-8, SRC-FR-9, SRC-FR-24 | P1 | integration | M0 |
| SRC-12 | The OpenAlex adapter shall pass conformance (run with `-k`), send the API key per spec, use a page size of at most 100, use `topics` and `last_known_institutions`, and have an error classifier that maps an insufficient-budget 429 to `budget_exhausted` with detail. | SRC-FR-8, SRC-FR-9 | P1 | integration | M0 |
| SRC-8 | The `list_sources` tool and the `research://sources` resource shall list every source with its state and fix hint. | SRC-FR-5, SRC-FR-6, HLTH-FR-42 | P1 | contract | M0 |
| SRC-13 | If the committed source inventory differs from the registry, then `gen_inventory --check` shall fail. | SRC-FR-25, NFR-10 | P1 | unit | M0 |
| SRC-20 | The conformance suite shall pass for every M1 adapter in the PRD-sources catalog (section 3 of v3, section 1.3 of this version), each with its own fixtures. | SRC-FR-8, SRC-FR-9, SRC-FR-26 | P1 | integration | M1 |
| SRC-21 | The source registry shall create four DSpace instances from configuration with one adapter module, each recording its DSpace version. | SRC-FR-4 | P1 | integration | M1 |
| SRC-22 | The upstream MCP adapters (AWS Knowledge, Microsoft Learn) shall go through `McpUpstreamPort`, so that rate limits, host policy, telemetry and redaction apply, as tested against an MCP server fake. | SRC-FR-10 | P2 | integration | M1 |
| SRC-23 | The docs-site adapter shall refuse hosts and paths outside its allowlist, including substring tricks, and honor `robots.txt`. | SRC-FR-15 | P1 | integration | M1 |
| SRC-24 | Where a source has a shutdown date, the system shall report it as `deprecated(days)`. | SRC-FR-14 | P2 | unit | M1 |
| SRC-25 | When run as the opt-in live test, `sources check --live` shall write refreshed fixtures to a review folder only. | SRC-FR-12 | P2 | live | M1 |
| SRC-26 | The system shall map every upstream endpoint v1 calls to a registered v2 source (table-driven from the MIGRATION tool map, with the AWS and Microsoft Learn substitution listed) and ship `defaults.toml` holding the site set `v1_docs` with v1's 26 domains and the six `docs_site` instances with v1's seeds and filters. | SRC-FR-17, SRC-FR-18 | P1 | unit | M1 |
| SRC-27 | The system shall load site sets from config and defaults, with config overriding defaults and an invalid set name failing validation. | SRC-FR-18 | P1 | unit | M1 |
| SRC-28 | The system shall keep web sources disabled until their settings and credential are present, never include the `web` group in auto selection, and select web sources when a caller names the group or a source id. | SRC-FR-19 | P1 | integration | M1 |
| SRC-29 | When a web source reaches its daily cap of `budget_cap` calls, the system shall report it as `budget_exhausted` until the next local midnight (tested with `FakeClock`) and skip it in federation with that status. | SRC-FR-20, HLTH-FR-12 | P1 | integration | M1 |
| SRC-30 | The web federation shall, under the `fallback` strategy with Vertex exhausted and Brave failing, answer from SerpAPI, report Programmable Search as `not_needed` and spend only one paid query per page; under strategy `all`, fan out to every configured web source; and still run non-web sources in parallel within the deadline. | SRC-FR-21 | P1 | integration | M1 |
| SRC-31 | When a `site_set` is given, the system shall split Brave queries into at most 3 batches of at most 380 characters with query-named domains first, use one query for SerpAPI and Programmable Search and set `truncated` when domains are dropped, filter Vertex results by host, and return `invalid_argument` for an unknown set before any call. | SRC-FR-22 | P1 | unit | M1 |
| SRC-32 | The Vertex adapter shall pass conformance, with `GoogleAdcProvider` (fake loader) refreshing off the event loop, the token going only to `discoveryengine.googleapis.com` with `X-Goog-User-Project`, a static check that v2 code never opens the credential file, and the refresh call recorded as a call record. | SRC-FR-23, PLAT-FR-10 | P1 | integration | M1 |
| SRC-33 | The Brave, SerpAPI and Programmable Search adapters shall pass conformance, with Brave sending `X-Subscription-Token`, Programmable Search sending `x-goog-api-key` and reporting `deprecated(days)`, and the SerpAPI `api_key` never appearing in logs, errors, call records or tool results. | SRC-FR-19, PLAT-FR-12, PLAT-FR-13 | P1 | integration | M1 |

Verified elsewhere (owner decision, 2026-10-22):

- SRC-FR-1: also PLAT-6 (`SourcePolicy` and `AuthSpec` origin validation).
- SRC-FR-5, the UI disable control: UI-10 (source board enable and disable actions).
- SRC-FR-7: also PLAT-13 (the `gcp` extra and the `vertex_search` install hint).
- SRC-FR-24, the rejection of a placeholder by settings validation: PLAT-11 (the unset case is SRC-4).
- SRC-FR-26, one work unit touching only the allowed files: owner check OC-11.
- SRC-FR-19 and SRC-FR-23, a live web-group search with site set `v1_docs` through the Vertex engine with the owner's Google sign-in: owner check OC-14.
- SRC-INV-6 (same rule as SEC-INV-5), the CORE key never sent to a non-CORE host: SEC-8.

## 2.5 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |

The parent outcomes OUT-1 to OUT-8 and NFR-1 to NFR-12 suffice; no component target is added (owner decision, 2026-10-22). Design defaults such as a per-source timeout or the probe cadence stay in the LLD.

Parent NFRs that bind this component (PRD-v6 2.3): NFR-1 (one daemon owns all HTTP clients and rate limiters, so per-source limits are global), NFR-2 (async; no tool blocks the event loop), NFR-3 (no secrets at rest outside the Keychain, except the Google sign-in), NFR-4 (no secret in any output), NFR-6 (untrusted content is labeled), NFR-8 (respect upstream terms, including arXiv's 1 request per 3 seconds; verified by SRC-10), NFR-9 (testable offline; live checks are opt-in) and NFR-10 (source inventories are generated from the registry; verified by SRC-13).

## 2.6 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

Every item is personal and confidential (PRD-v6 2.4). Retention follows the parent rule for the same kind of data; an item the parent does not list follows the nearest parent rule (owner decision, 2026-10-22).

| Data | Classification | Source or owner | Retention | Notes |
| --- | --- | --- | --- | --- |
| Upstream API keys and tokens (the "Auth" column in 1.3) | Personal, confidential; secret (NFR-3, NFR-4) | Owner; Keychain items `research-mcp/<NAME>` (ADR 0003) | Until revoked or replaced (PRD-v6 2.4) | Adapters never read secrets (SRC-FR-3) |
| Google sign-in access token for `vertex_search` | Personal, confidential; secret (ADR 0012 decision 5) | `gcloud` owns the Application Default Credentials file (ADR 0012) | In memory only; not stored by v2 (SRC-FR-23; PRD-v6 2.4) | Sent only to `discoveryengine.googleapis.com` (SRC-FR-23) |
| Owner contact email | Personal, confidential | Owner configuration (SRC-FR-24) | Life of the install, until the owner changes it (nearest parent rule: daemon state, PRD-v6 2.4) | Sent to sources that ask for it; placeholder addresses rejected by settings validation (SRC-FR-24) |
| Normalized work records with provenance | Personal, confidential; untrusted content (NFR-6) | Upstream sources (SRC-FR-9) | When cached, the cache rules: 120 days from fetch, with pinned and archived items never expiring (PRD-v6 2.4; ADR 0011) | Web-search snippets are untrusted (NFR-6) |
| Recorded fixtures | Personal, confidential; recorded with credentials removed (repository instructions) | This repository (SRC-FR-8) | Life of the install, until replaced by refreshed fixtures the owner accepts (nearest parent rule: records, PRD-v6 2.4; SRC-FR-12) | Refreshed fixtures go to a review folder first (SRC-FR-12) |
| Site sets, docs-site instances, web-search engine settings | Personal, confidential; settings, not secrets (SRC-FR-23) | Owner configuration (SRC-FR-18, SRC-FR-23) | Life of the install (nearest parent rule: daemon state, PRD-v6 2.4) | Project, location and engine id are settings, not secrets (SRC-FR-23) |

## 2.7 Integrations and owners

> **Owner:** H confirms owners and SLAs · **Persona:** `architect` may draft · **Seed question:** 8

Kenny Hill owns every integration. No integration has an SLA: upstream services are best effort, tracked by probes (PRD-v6 2.5; owner decision, 2026-10-22).

| System | Owner | Relationship (depends on, feeds, replaces) | SLA |
| --- | --- | --- | --- |
| The upstream services in the 1.3 catalog (HTTP APIs) | Kenny Hill | Depends on; each is run by its upstream provider | None; best effort, tracked by probes |
| AWS Knowledge and Microsoft Learn MCP servers | Kenny Hill | Depends on (run by AWS and Microsoft); replaces v1's undocumented site-search endpoints (SRC-FR-10, SRC-FR-17) | None; best effort, tracked by probes |
| Vertex AI Search and the owner's Google sign-in (`gcloud`, `google-auth`) | Kenny Hill | Depends on (run by Google; the owner's Google account) (SRC-FR-23; ADR 0012) | None; best effort, tracked by probes |
| Platform HTTP client, MCP client port and Keychain secrets | Kenny Hill | Depends on: all adapter I/O goes through the shared `HttpPort` (SRC-FR-3, SRC-FR-10) | None |
| Federated search | Kenny Hill | Feeds: the registry selects sources and skip statuses (SRC-FR-5, SRC-FR-6, SRC-FR-20, SRC-FR-21) | None |
| Health and credentials | Kenny Hill | Feeds probes and quotas; reads source states (SRC-FR-1, SRC-FR-14; HLTH-FR-12) | None |
| Local UI | Kenny Hill | Feeds: source board, disable control, site sets on the settings page (SRC-FR-5, SRC-FR-18) | None |
| Migration tool map | Kenny Hill | Feeds the v1-to-v2 endpoint mapping (SRC-FR-17; SRC-26) | None |

## 2.8 Product risks

> **Owner:** H · **Persona:** none

| Risk | Question | Assessment | Mitigation |
| --- | --- | --- | --- |
| Value | Will customers choose to use this? | The owner is the only user and asked for horizontal reach (D1); the risk is sources that are added but not cheap to keep healthy, so breadth decays (D1; PRD-v6 2.10, upstream change) | Every source ships fixtures and a probe (2.11); any source can be disabled without a code change (SRC-FR-5); OUT-1 is measured again 30 days after cutover (PRD-v6 1.4) |
| Usability | Can customers use it, including with accessibility needs? | The risk is that a missing key, extra or contact address fails silently, as breakage and credentials did in v1 (PRD-v6 1.1, items 2 and 3) | `unconfigured` with the exact fix (SRC-FR-6, SRC-FR-7, SRC-FR-24; SRC-8); skipped sources report their status (SRC-FR-5). UI accessibility belongs to the UI component (PRD-ui-v4) |
| Viability | Does it work for the business: economics, legal, compliance, operations? | Economics is the metered spend risk and operations the upstream change risk below; upstream terms are respected (NFR-8) | As in the two rows below; NFR-8 and SRC-10 for upstream terms |
| Upstream change (PRD-v4 12) | Upstream APIs change faster than one person can follow. | As in the parent risk table (PRD-v6 2.10); no component assessment added | Probes check response shape, not just status; recorded fixtures make breakage visible in tests; each source can be disabled with a flag (PRD-v4 12) |
| Metered spend (PRD-v4 12) | Metered sources (OpenAlex budget, web-search providers) run out mid-task or cost more than expected. | As in the parent risk table (PRD-v6 2.10); no component assessment added | Budget tracking with `quota_low`, `rate_limited` and `budget_exhausted` states; federation skips exhausted sources and says so; web-search sources are off until configured, capped per day, and never in the default fan-out (PRD-v4 12) |

## 2.9 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | As in PRD-v6 2.6: v1 stays read-only and running until cutover; cutover (M4) switches client configs; v1 is archived after 14 days of daily use on v2 with no fallback to v1. For this component, M0 delivers the contract, registry and three reference adapters, and M1 delivers the remaining sources (PRD-v4 10) |
| Business conditions that must halt the rollout | The PRD-v7 2.6 conditions: any deletion without a recorded owner decision, any secret in an output, a fallback to v1 during the 14-day window, or a breach of any invariant, which includes SRC-INV-1 to SRC-INV-6 (PRD-v7 2.6; owner decision, 2026-10-22) |
| Support owner and escalation path | The owner is the only support; there is no escalation path (PRD-v6 2.6; owner decision, 2026-10-22) |
| Response targets by severity (S0 to S4) | None (PRD-v6 2.6; owner decision, 2026-10-22) |

## 2.10 Measurement and experimentation

> **Owner:** C · **Persona:** `product-writer` drafts; the owner decides

| Outcome | Measured by | Experiment (if any) |
| --- | --- | --- |
| SRC-OUT-1 | Sources registered (45 or more, PRD-v6 OUT-1) as listed by the registry; every v1 endpoint mapped (SRC-26) | None |
| SRC-OUT-2 | Owner estimate of time to add a new free source, agent-built (one work unit, PRD-v4 7); owner check OC-11 (test plan section 3) | None |

## 2.11 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

- Every P1 criterion of this component passes, and the exit of the milestone that delivers it is met (PRD-v6 2.9; owner decision, 2026-10-22).
- The owner checks listed for this component in [the test plan](../../test/test-plan-v2.md) section 3 count: OC-11 and OC-14. No extra demonstration is required (owner decision, 2026-10-22).
- Each source in the catalog has the seven recorded fixtures (SRC-FR-8) and one probe test (PRD-sources-v3 4; owner decision, 2026-10-22).
- For each new source, the new-source checklist (SPEC-v2 5.4) is the definition of done (SRC-FR-26), without its step 5: the Keychain name lives in the `SourceSpec` and the generated inventory (owner decision, 2026-10-22).
- M0 exit: all M0 tests green; a client can search three sources through the shim on the owner's Mac. M1 exit: 45 or more sources registered, every v1 endpoint mapped; source board data available through `research://sources` (PRD-v6 2.9; PRD-v6 OUT-1).

## 2.12 Edge cases and error behavior

> **Owner:** A · **Persona:** `product-writer`

| Edge case | Behavior | Criterion |
| --- | --- | --- |
| A required credential is missing | Listed `unconfigured` with the Keychain item name and signup URL; skipped by federation (SRC-FR-6) | SRC-4, SRC-8 |
| `contact.email` is unset for a source with `needs_contact` | `unconfigured` with the exact fix (SRC-FR-24) | SRC-4 |
| `contact.email` holds a placeholder address (example.com, example.org, .test, .invalid) | Rejected by settings validation with a clear message; the daemon does not start until it is fixed (SRC-FR-24; SPEC-v2 2) | PLAT-11 |
| An optional extra (for example `gcp`) is not installed | `unconfigured` with the install command (SRC-FR-7; ADR 0012) | SRC-5 |
| Upstream returns 429 with `Retry-After`, 5xx, a malformed body, or an oversize body | Covered by the conformance checks (SRC-FR-8) | SRC-6, SRC-20 |
| OpenAlex returns an insufficient-budget 429 | Mapped to `budget_exhausted` with detail | SRC-12 |
| A source has an announced shutdown date | `deprecated(days)` until removed (SRC-FR-14) | SRC-24, SRC-33 |
| A docs-site URL tries a substring trick to pass the allowlist | Refused (SRC-FR-15) | SRC-23 |
| A web source reaches its daily cap | `budget_exhausted` until the next local midnight; skipped with that status (SRC-FR-20) | SRC-29 |
| In `fallback`, the first web sources are exhausted or failing | The next configured source answers; later ones report `not_needed` (SRC-FR-21) | SRC-30 |
| A site set is long for a provider's query length | Split into batches (Brave) or truncated with `truncated` set (SerpAPI, Programmable Search) (SRC-FR-22) | SRC-31 |
| An unknown site set name is given | `invalid_argument` before any call (SRC-FR-22) | SRC-31 |
| The live check refreshes fixtures | Written to a review folder only, never over the committed fixtures (SRC-FR-12) | SRC-25 |

## 2.13 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves before Gate 1

**Resolved on 2026-10-22.** The owner answered every open question in v4: the user group sizes (1.2); the leaps of faith, drafted for approval (1.5); the invariants SRC-INV-1 to SRC-INV-6 (1.6); the user stories and their priority, drafted for approval (2.2, and the Story column in 2.4); seven fixtures per adapter (1.7, 2.11); the M1 exit of 45 sources (1.4, 1.7, 2.11); `tools/gen_inventory.py` as the only inventory generator (SRC-FR-25); the placeholder contact address (SRC-FR-24, PLAT-11, 2.12); the Keychain name of a new source and the superseded SPEC-v2 5.4 step 5 (SRC-FR-26; 1.4, 1.7, 2.11); no component NFR targets (2.5); data classification and retention (2.6); integration owners and SLAs (2.7); product risks (2.8); rollout and support (2.9). The v4 assumption that OUT-1 and OUT-3 keep the meaning of PRD-v4 G1 and G3 is settled by PRD-v6 1.4, which carries those targets over as approved.

**Gate 1 follow-up (owner decision, 2026-10-22).** The UI Settings page shows the named site sets read-only, as SRC-FR-18 says (UI-FR-21, UI-25 in the UI component); site sets are edited in the config file or with `research-mcp config set`. A placeholder `contact.email` stops the daemon from starting until it is fixed, as SPEC-v2 2, PLAT-11 and the settings code already do; only an unset address leaves the `needs_contact` sources `unconfigured` (SRC-FR-24; SRC-4). The new-source requirement is now SRC-FR-26, the checklist without step 5 (2.15). SRC-INV-6 is the same rule as SEC-INV-5, and SRC-INV-5 includes the rule of SEC-INV-11; the Security component owns both. A breach of any invariant halts the rollout (PRD-v7 2.6).

## 2.14 Glossary

> **Owner:** A · **Persona:** `product-writer`

| Term | Definition |
| --- | --- |
| Source | One upstream service, or one configured instance of an adapter, exposed by id and group (SRC-FR-4) |
| `SourceSpec` | The declarative description of a source (SRC-FR-1) |
| Adapter | The module that translates between one upstream API and the normalized models (SRC-FR-2, SRC-FR-3) |
| Registry | The component that discovers adapters, builds configured instances and exposes them by id and group (SRC-FR-4) |
| Instance | A source created from configuration on top of a shared adapter, for example `dspace_mit` or `docs_site_<name>` (SRC-FR-4) |
| Group | A label such as `scholarly`, `preprints` or `web` that federated search uses to pick defaults (1.3) |
| Fixture | A recorded upstream response used by the conformance suite (SRC-FR-8) |
| Conformance suite | One set of checks run against every registered adapter (SRC-FR-8) |
| Upstream MCP server | An MCP server, such as AWS Knowledge or Microsoft Learn, used as a source (SRC-FR-10) |
| Site set | A named list of domains in configuration, for example `v1_docs` (SRC-FR-18) |
| `web` group | The optional, metered web-search sources (SRC-FR-19) |
| `fallback` strategy | Call the configured web sources in order and stop at the first that returns results without error (SRC-FR-21) |
| Application Default Credentials | The owner's Google sign-in, stored by `gcloud` and read by `google-auth` (SRC-FR-23) |
| `deprecated(days)` | The state shown for a source with an announced shutdown date (SRC-FR-14) |
| `budget_exhausted` | The state of a source that reached its daily cap or budget (SRC-FR-20) |
| `unconfigured` | The state of a source that lacks a required credential, an optional extra or a contact address it needs; it is listed with the exact fix and skipped by federated search (SRC-FR-6, SRC-FR-7, SRC-FR-24) |
| Placeholder address | A contact email on a placeholder domain (example.com, example.org, .test, .invalid) that settings validation rejects, so the daemon does not start until it is fixed (SRC-FR-24) |

## 2.15 ID history

> **Owner:** C · **Persona:** `product-writer` records; the owner confirms

Three requirements left this PRD in this version: each was superseded by a new ID because its behavior changed (owner decision, 2026-10-22).

| ID | Status | Replaced by | Reason |
| --- | --- | --- | --- |
| SRC-FR-11 | superseded | SRC-FR-24 | The response changed: a placeholder address is rejected by settings validation with a clear message, so the daemon does not start until it is fixed; with no address set, only the `needs_contact` sources become `unconfigured` (owner decision, 2026-10-22) |
| SRC-FR-13 | superseded | SRC-FR-25 | The response changed: `tools/gen_inventory.py` generates the inventory and `--check` gates it; `research-mcp sources --markdown` is removed (owner decision, 2026-10-22) |
| SRC-FR-16 | superseded | SRC-FR-26 | The definition of done changed: the SPEC-v2 5.4 checklist applies without its step 5, because the Keychain name lives in the `SourceSpec` (owner decision, 2026-10-22) |

**Changes in version 5.** These IDs are new, or changed only editorially (owner decision, 2026-10-22). The table's first column is not headed "ID" because these rows are not definitions and the IDs are still in force.

| Changed or new ID | Change | Date | Reason |
| --- | --- | --- | --- |
| SRC-FR-24 | New: replaces SRC-FR-11; the response changed: a placeholder address is rejected by settings validation with a clear message, so the daemon does not start until it is fixed; with no address set, only the `needs_contact` sources become `unconfigured` | 2026-10-22 | owner decision, 2026-10-22 |
| SRC-FR-25 | New: replaces SRC-FR-13; the response changed: `tools/gen_inventory.py` generates the inventory and `--check` gates it; `research-mcp sources --markdown` is removed | 2026-10-22 | owner decision, 2026-10-22 |
| SRC-FR-26 | New: replaces SRC-FR-16; the new-source checklist (SPEC-v2 5.4) without its step 5 is the definition of done | 2026-10-22 | owner decision, 2026-10-22 |
| SRC-20 | Requirement column cites SRC-FR-26 instead of SRC-FR-16; wording unchanged | 2026-10-22 | owner decision, 2026-10-22 |
| SRC-FR-1 to SRC-FR-23 (except the superseded SRC-FR-11, SRC-FR-13 and SRC-FR-16) | Story column filled with one story ID each | 2026-10-22 | owner decision, 2026-10-22 |
| SRC-US-1 to SRC-US-6 | New stories, drafted by the product writer and approved by the owner at Gate 1, 2026-10-22 | 2026-10-22 | owner decision, 2026-10-22 |
| SRC-INV-1 to SRC-INV-6 | Confirmed as component invariants; each names its verifying P1 criterion (SRC-INV-6 now cites SEC-8 instead of SRC-33, and is marked as the same rule as SEC-INV-5) | 2026-10-22 | owner decision, 2026-10-22 |

### Gate 1: Requirements approved

| Approver | Date | Notes |
| --- | --- | --- |
| Kenny Hill (Product) | 2026-10-22 | Approved in chat; recorded by Claude in the owner's name at his direction |

## 2.16 Earlier IDs

> **Owner:** A · **Persona:** `product-writer`

| Earlier ID | New ID |
| --- | --- |
| FR-SRC-01 | SRC-FR-1 |
| FR-SRC-02 | SRC-FR-2 |
| FR-SRC-03 | SRC-FR-3 |
| FR-SRC-04 | SRC-FR-4 |
| FR-SRC-05 | SRC-FR-5 |
| FR-SRC-06 | SRC-FR-6 |
| FR-SRC-07 | SRC-FR-7 |
| FR-SRC-08 | SRC-FR-8 |
| FR-SRC-09 | SRC-FR-9 |
| FR-SRC-10 | SRC-FR-10 |
| FR-SRC-11 | SRC-FR-11 (superseded by SRC-FR-24) |
| FR-SRC-12 | SRC-FR-12 |
| FR-SRC-13 | SRC-FR-13 (superseded by SRC-FR-25) |
| FR-SRC-14 | SRC-FR-14 |
| FR-SRC-15 | SRC-FR-15 |
| FR-SRC-16 | SRC-FR-16 (superseded by SRC-FR-26) |
| FR-SRC-17 | SRC-FR-17 |
| FR-SRC-18 | SRC-FR-18 |
| FR-SRC-19 | SRC-FR-19 |
| FR-SRC-20 | SRC-FR-20 |
| FR-SRC-21 | SRC-FR-21 |
| FR-SRC-22 | SRC-FR-22 |
| FR-SRC-23 | SRC-FR-23 |
| AT-SRC-01 | SRC-1 |
| AT-SRC-02 | SRC-2 |
| AT-SRC-03 | SRC-3 |
| AT-SRC-04 | SRC-4 |
| AT-SRC-05 | SRC-5 |
| AT-SRC-06 | SRC-6 |
| AT-SRC-07 | SRC-7 |
| AT-SRC-08 | SRC-8 |
| AT-SRC-10 | SRC-10 |
| AT-SRC-11 | SRC-11 |
| AT-SRC-12 | SRC-12 |
| AT-SRC-13 | SRC-13 |
| AT-SRC-20 | SRC-20 |
| AT-SRC-21 | SRC-21 |
| AT-SRC-22 | SRC-22 |
| AT-SRC-23 | SRC-23 |
| AT-SRC-24 | SRC-24 |
| AT-SRC-25 | SRC-25 |
| AT-SRC-26 | SRC-26 |
| AT-SRC-27 | SRC-27 |
| AT-SRC-28 | SRC-28 |
| AT-SRC-29 | SRC-29 |
| AT-SRC-30 | SRC-30 |
| AT-SRC-31 | SRC-31 |
| AT-SRC-32 | SRC-32 |
| AT-SRC-33 | SRC-33 |
