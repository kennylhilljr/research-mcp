---
title: "M1 plan: the full catalog, citations, health and credentials"
type: plan
version: 6
status: draft
owner: "Kenny Hill"
milestone: M1
artifact_type: plan
components: [health, platform, search, security, sources]
scope_level: L3
scope_name: "research-mcp"
derives_from: docs/spec/SPEC-v5.md
date: 2026-10-26
supersedes: docs/build/M1-plan-v5.md
---

# M1 plan (v6)

Changes from v5 (the architect's plan check in run `rm-m1e`, 2026-10-27, returned `changes_requested`):

- M1-25 depends on M1-26, whose `CredentialService` the health service calls; 2.2 states what M1-25 changes in `platform/scheduler.py`.
- M1-20 adds `to_csl` (LLD-search-v3 5.3), and M1-21 depends on it.
- M1-31 adds the `CacheStore` methods for the `works` columns that cite and integrity read and write; M1-21 and M1-22 depend on it.
- From a pre-review of this version: M1-31 adds the `calls` reads health needs; M1-11 plugs `McpUpstreamPort` into the conformance harness; M1-28 may update the tool-list contract test for `ops_status`; M1-24 defines `HealthEvent` and `EventKind`; `CredentialService` takes a `run_probes` callable; M1-27 depends on M1-25; HLTH-25 is shared by M1-25 and M1-26; M1-23 registers the prompts and the `integrity_recheck` handler; M1-25 adds the hourly schedule and M1-28 registers the local-target probes.

Changes from v4 (the architect's plan check in run `rm-m1d`, 2026-10-27, returned `changes_requested`):

- M1-25 exposes the `health_evaluate` job and M1-28 registers it with the other M1 jobs (2.2).
- M1-24 owns `CredentialStateView` in `services/health_eval.py`; M1-26 imports it (2.2).

Changes from v3 (the architect's plan check in run `rm-m1c`, 2026-10-27, returned `changes_requested`):

- New unit M1-31 adds the `StateStore` methods for searches, call rollups and daily counts, credentials and notifications; M1-18, M1-25, M1-26, M1-27 and M1-28 depend on it, and M1-18 no longer edits `platform/stores.py`.
- M1-28 depends on M1-11, whose MCP client it wires.
- The note on shared files names `app.py` once, with all four units.

Changes from v2 (the architect's plan check in run `rm-m1b`, 2026-10-27, returned `changes_requested`):

- The inventory check moves to the full CI run (owner decision, 2026-10-27), so adapter units no longer touch `docs/generated/sources.md`, as LLD-sources-v3 5.5 and OC-11 require; M1-29 regenerates it once.
- M1-02 owns the conformance suite and its harness: capability-keyed checks and an MCP-fake context.
- M1-01 adds the `gcloud_adc` secret backend and the Vertex header; M1-11 adds streamable-HTTP reading to `platform/http.py` and the MCP fake to `testing/adapters.py`, after M1-01.
- `app.py` composition is assigned: M1-23 wires the four search services, M1-28 every other M1 wire (2.1).
- M1-25 depends on M1-02 (`ProbeResult.api_version`); M1-23 depends on M1-18 (both edit `app.py`).
- 2.2 adds rows for M1-01, M1-02, M1-03 and M1-11.

Changes from v1 (the architect's plan check in run `rm-m1a`, 2026-10-27, returned `changes_requested`):

- Every unit that adds a source owns `docs/generated/sources.md` too, because CI checks the inventory in every mode (2.1).
- M1-29 depends on M1-14 and M1-15, so the catalog of 45 includes the four web sources.
- M1-02 adds the registry's helper-spec mechanism for `doi_resolver`; M1-21 only declares the spec (2.2).
- The M1-28 row in 2.2 follows LLD-health-v3 5.9: `daemon_alive` keeps its own `httpx.AsyncClient`; and M1-28 registers the M1 scheduler jobs in `app.py`.

Milestone M1 builds what SPEC-v5 section 14 assigns to it: every other adapter, for at least 45 sources registered at the exit (PRD-v8 OUT-1); `docs_site` with `get`, the allowlist and `robots.txt` only; the `citations`, `authors`, `cite` and `check_integrity` tools (PRD-v8 2.9); and health, credentials, quota tracking, notifications and the M1 doctor checks. M1's scope is the set of criteria that the component PRDs mark M1: 44 criteria in sources v5 (14), search v3 (5), health v4 (23), platform v4 (1) and security v3 (1). Cache, UI and migration have no M1 criteria. The plan also carries the code follow-ups the owner decided at the end of M0 ([M0 handoff](M0-handoff-v1.md)). `tools/gen_m0_plan.py` builds `.orchestration/plan-m1.json` from the task table below, with the same columns as the M0 plan.

## 1. Slices

> **Owner:** A · **Persona:** `planner`

Each wave is a slice; units in one wave have no overlapping files and can run in parallel. The waves follow from `depends_on`.

| Slice | Units | Checkpoint |
| --- | --- | --- |
| 1 | M1-01, M1-02, M1-24, M1-30, M1-31 | every unit merged with its criteria passing |
| 2 | M1-03, M1-04, M1-05, M1-06, M1-07, M1-08, M1-09, M1-10, M1-11, M1-12, M1-13, M1-16 | every unit merged with its criteria passing |
| 3 | M1-14, M1-15, M1-19, M1-20, M1-22 | every unit merged with its criteria passing |
| 4 | M1-17, M1-21, M1-26, M1-29 | every unit merged with its criteria passing |
| 5 | M1-18, M1-25 | every unit merged with its criteria passing |
| 6 | M1-23, M1-27 | every unit merged with its criteria passing |
| 7 | M1-28 | every unit merged with its criteria passing |

## 2. Tasks

> **Owner:** A · **Persona:** `planner`

Columns after Persona are read by `tools/gen_m0_plan.py`: the LLDs the unit implements, its file scope (paths under `src/research_mcp/` unless they start with `src/`, `tests/`, `tools/`, `docs/` or `.github/`; a path ending in `/` covers its whole folder, so an adapter unit owns `tests/sources/<id>/` with its seven fixtures and its test file), the risk that sets its routing tier, and its status. trace-check reads the Status column: only the criteria in the cells of a `done` task are due.

| # | Task | Criteria | Depends on | Persona | Implements | Files (scope) | Risk | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1-01 | Optional extras `gcp` and `cite`, the Google ADC provider and its `gcloud_adc` secret backend | PLAT-13, SEC-27 | none | `implementer` | `docs/lld/LLD-platform-v3.md` (§4.2, §5.8); `docs/lld/LLD-security-v2.md` (§4.4); `docs/lld/LLD-sources-v3.md` (§5.1); `docs/lld/LLD-search-v3.md` (§5.9); SPEC-v5 9, 12 | `pyproject.toml`, `uv.lock`, `platform/google_adc.py`, `tests/unit/test_version.py`, `tests/unit/platform/test_google_adc.py`, `tests/security/test_no_secret_at_rest.py`, `platform/secrets.py`, `platform/http.py`, `tests/unit/platform/test_secrets.py`, `tests/unit/platform/test_http.py` | high | planned |
| M1-02 | Source contract follow-ups: models, adapter protocol, helper specs, capability-keyed conformance, `defaults.toml`, site sets and shutdown dates | SRC-24, SRC-27 | none | `implementer` | `docs/lld/LLD-sources-v3.md` (§2.1, §3.1, §3.2, §3.3, §5.2, §5.13); SPEC-v5 4 | `core/models.py`, `sources/base.py`, `sources/registry.py`, `settings.py`, `packaging/defaults.toml`, `testing/adapters.py`, `tests/unit/sources/test_registry.py`, `tests/unit/test_settings.py`, `tests/sources/test_conformance.py`, `tests/sources/conftest.py`, `tools/ci.sh` | high | planned |
| M1-03 | The `web` group: gating, daily caps and site-set queries | SRC-28, SRC-29, SRC-31 | M1-02 | `implementer` | `docs/lld/LLD-sources-v3.md` (§5.7, §5.8, §5.9); SPEC-v5 4, 5 | `sources/registry.py`, `sources/sitequery.py`, `tests/services/test_web_group.py`, `tests/unit/sources/test_sitequery.py` | medium | planned |
| M1-04 | Adapters: Semantic Scholar, DataCite, CORE, Unpaywall | SRC-20 | M1-02 | `implementer` | `docs/lld/LLD-sources-v3.md` (§3.4, §5.1, §5.3, §5.5; SPEC-v5 4) | `sources/semantic_scholar.py`, `sources/datacite.py`, `sources/core_ac.py`, `sources/unpaywall.py`, `tests/sources/semantic_scholar/`, `tests/sources/datacite/`, `tests/sources/core/`, `tests/sources/unpaywall/` | medium | planned |
| M1-05 | Adapters: OpenAIRE, DOAJ, Zenodo, HAL | SRC-20 | M1-02 | `implementer` | `docs/lld/LLD-sources-v3.md` (§3.4, §5.1, §5.3, §5.5; SPEC-v5 4) | `sources/openaire.py`, `sources/doaj.py`, `sources/zenodo.py`, `sources/hal.py`, `tests/sources/openaire/`, `tests/sources/doaj/`, `tests/sources/zenodo/`, `tests/sources/hal/` | medium | planned |
| M1-06 | Adapters: DBLP, ORCID, ADS, Lens | SRC-20 | M1-02 | `implementer` | `docs/lld/LLD-sources-v3.md` (§3.4, §5.1, §5.3, §5.5; SPEC-v5 4) | `sources/dblp.py`, `sources/orcid.py`, `sources/ads.py`, `sources/lens.py`, `tests/sources/dblp/`, `tests/sources/orcid/`, `tests/sources/ads/`, `tests/sources/lens/` | medium | planned |
| M1-07 | Adapters: OSF, bioRxiv, medRxiv, SSRN, Hugging Face papers | SRC-20 | M1-02 | `implementer` | `docs/lld/LLD-sources-v3.md` (§3.4, §5.1, §5.3, §5.5; SPEC-v5 4) | `sources/osf.py`, `sources/biorxiv.py`, `sources/medrxiv.py`, `sources/ssrn.py`, `sources/hf_papers.py`, `tests/sources/osf/`, `tests/sources/biorxiv/`, `tests/sources/medrxiv/`, `tests/sources/ssrn/`, `tests/sources/hf_papers/` | medium | planned |
| M1-08 | Adapters: Europe PMC, PubMed, ClinicalTrials.gov | SRC-20 | M1-02 | `implementer` | `docs/lld/LLD-sources-v3.md` (§3.4, §5.1, §5.3, §5.5; SPEC-v5 4) | `sources/europe_pmc.py`, `sources/pubmed.py`, `sources/clinical_trials.py`, `tests/sources/europe_pmc/`, `tests/sources/pubmed/`, `tests/sources/clinical_trials/` | medium | planned |
| M1-09 | DSpace adapter with four instances from configuration | SRC-20, SRC-21 | M1-02 | `implementer` | `docs/lld/LLD-sources-v3.md` (§2.3, §3.3, §5.12; SPEC-v5 4) | `sources/dspace.py`, `tests/sources/dspace/` | medium | planned |
| M1-10 | Adapters: IETF, NIST, NVD, Google Developer Knowledge | SRC-20 | M1-02 | `implementer` | `docs/lld/LLD-sources-v3.md` (§3.4, §5.1, §5.3, §5.5; SPEC-v5 4) | `sources/ietf.py`, `sources/nist.py`, `sources/nvd.py`, `sources/google_devknowledge.py`, `tests/sources/ietf/`, `tests/sources/nist/`, `tests/sources/nvd/`, `tests/sources/google_devknowledge/` | medium | planned |
| M1-11 | Upstream MCP port and the AWS Knowledge and Microsoft Learn adapters | SRC-20, SRC-22 | M1-01, M1-02 | `implementer` | `docs/lld/LLD-sources-v3.md` (§5.6); `docs/lld/LLD-platform-v3.md` (§4.4); SPEC-v5 4, 9 | `platform/mcp_client.py`, `sources/mcp_upstream.py`, `sources/aws_knowledge.py`, `sources/ms_learn.py`, `tests/unit/platform/test_mcp_client.py`, `tests/sources/aws_knowledge/`, `tests/sources/ms_learn/`, `platform/http.py`, `testing/adapters.py`, `tests/unit/platform/test_http.py`, `tests/sources/conftest.py` | high | planned |
| M1-12 | Docs-site adapter (`get` only), allowlist and `robots.txt` | SRC-20, SRC-23 | M1-02 | `implementer` | `docs/lld/LLD-sources-v3.md` (§3.3, §5.11); SPEC-v5 4, 9 | `sources/docs_site.py`, `sources/docs_allowlist.py`, `sources/robots.py`, `tests/sources/docs_site/`, `tests/unit/sources/test_docs_allowlist.py`, `tests/unit/sources/test_robots.py` | high | planned |
| M1-13 | Adapters: GitHub, OpenCitations, Crossref updates, ERIC | SRC-20 | M1-02 | `implementer` | `docs/lld/LLD-sources-v3.md` (§3.4, §5.1, §5.3, §5.5; SPEC-v5 4) | `sources/github.py`, `sources/opencitations.py`, `sources/crossref_updates.py`, `sources/eric.py`, `tests/sources/github/`, `tests/sources/opencitations/`, `tests/sources/crossref_updates/`, `tests/sources/eric/` | medium | planned |
| M1-14 | Vertex AI Search adapter | SRC-20, SRC-32 | M1-01, M1-03 | `implementer` | `docs/lld/LLD-sources-v3.md` (§5.7); `docs/lld/LLD-platform-v3.md` (§4.2); SPEC-v5 4, 9 | `sources/vertex_search.py`, `tests/sources/vertex_search/`, `tests/unit/sources/test_vertex_static.py` | high | planned |
| M1-15 | Adapters: Brave Search, SerpAPI, Programmable Search | SRC-20, SRC-33 | M1-03 | `implementer` | `docs/lld/LLD-sources-v3.md` (§5.7, §5.8); SPEC-v5 4, 9 | `sources/brave_search.py`, `sources/serpapi.py`, `sources/google_pse.py`, `tests/sources/brave_search/`, `tests/sources/serpapi/`, `tests/sources/google_pse/` | medium | planned |
| M1-16 | Adapters: Library of Congress, Open Library, Wikipedia | SRC-20 | M1-02 | `implementer` | `docs/lld/LLD-sources-v3.md` (§3.4, §5.1, §5.3, §5.5; SPEC-v5 4) | `sources/loc.py`, `sources/open_library.py`, `sources/wikipedia.py`, `tests/sources/loc/`, `tests/sources/open_library/`, `tests/sources/wikipedia/` | medium | planned |
| M1-17 | Federation of the `web` group (`fallback` strategy) and `site_set` on `search` | SRC-30 | M1-03, M1-14, M1-15 | `implementer` | `docs/lld/LLD-sources-v3.md` (§5.9); `docs/lld/LLD-search-v3.md` (§2.1, §5.4); SPEC-v5 5 | `services/federation.py`, `mcp_app/tools_discovery.py`, `tests/services/test_federation_web.py` | medium | planned |
| M1-18 | Search records: wire the recording port to `StateStore.search_put` (added by M1-31) | SRCH-34 | M1-17, M1-30, M1-31 | `implementer` | `docs/lld/LLD-search-v3.md` (§3, §5.4, §5.11); `docs/lld/LLD-platform-v3.md` (§3.1); SPEC-v5 5, 10 | `services/federation.py`, `app.py`, `tests/services/test_federation.py` | medium | planned |
| M1-19 | Citations service | SRCH-30 | M1-04, M1-13 | `implementer` | `docs/lld/LLD-search-v3.md` (§5.7); SPEC-v5 5 | `services/citations.py`, `tests/services/test_citations.py` | medium | planned |
| M1-20 | Authors (merge OpenAlex, ORCID and DBLP author records) and `to_csl` | SRCH-31 | M1-06 | `implementer` | `docs/lld/LLD-search-v3.md` (§5.3, §5.8); SPEC-v5 5 | `services/works.py`, `tests/services/test_works.py` | medium | planned |
| M1-21 | `cite` service and the `doi_resolver` helper spec | SRCH-32 | M1-01, M1-02, M1-20, M1-31 | `implementer` | `docs/lld/LLD-search-v3.md` (§5.9); `docs/lld/LLD-sources-v3.md` (§5.13); SPEC-v5 5, 12 | `services/cite.py`, `sources/doi_resolver.py`, `tests/services/test_cite.py` | medium | planned |
| M1-22 | Integrity service: retractions and corrections | SRCH-33 | M1-13, M1-31 | `implementer` | `docs/lld/LLD-search-v3.md` (§5.10); SPEC-v5 5, 14 | `services/integrity.py`, `tests/services/test_integrity.py` | medium | planned |
| M1-23 | MCP tools `citations`, `authors`, `cite` and `check_integrity` | SRCH-20, SRCH-21 | M1-17, M1-18, M1-19, M1-20, M1-21, M1-22 | `implementer` | `docs/lld/LLD-search-v3.md` (§2.1); SPEC-v5 5 | `mcp_app/tools_discovery.py`, `mcp_app/server.py`, `tests/contract/test_tools_discovery.py`, `tests/contract/test_tool_contract.py`, `app.py`, `mcp_app/prompts.py` | high | planned |
| M1-24 | Health evaluation: the source state table and rate-limit states | HLTH-10, HLTH-12 | none | `implementer` | `docs/lld/LLD-health-v3.md` (§5.5); SPEC-v5 7 | `services/health_eval.py`, `tests/unit/services/test_health_eval.py` | medium | planned |
| M1-25 | Health service: telemetry, rollups, probes and local targets | HLTH-1, HLTH-2, HLTH-3, HLTH-4, HLTH-11, HLTH-44, HLTH-25 | M1-02, M1-24, M1-26, M1-30, M1-31 | `implementer` | `docs/lld/LLD-health-v3.md` (§3, §5.3, §5.4, §5.6); `docs/lld/LLD-platform-v3.md` (§5.10); SPEC-v5 7 | `services/health.py`, `platform/scheduler.py`, `tests/services/test_health.py`, `tests/services/test_credentials.py` | high | planned |
| M1-26 | Credential service: states, expiry, quotas and fix text | HLTH-13, HLTH-20, HLTH-21, HLTH-22, HLTH-23, HLTH-24, HLTH-25, HLTH-43 | M1-01, M1-13, M1-14, M1-15, M1-24, M1-31 | `implementer` | `docs/lld/LLD-health-v3.md` (§3, §5.7); `docs/lld/LLD-security-v2.md` (§4.3); SPEC-v5 7, 9 | `services/credentials.py`, `tests/unit/services/test_credentials.py`, `tests/services/test_credentials.py` | high | planned |
| M1-27 | Notify service: once-only notices, digest, quiet hours, macOS notifier | HLTH-30, HLTH-31, HLTH-32, HLTH-33, HLTH-34, HLTH-35 | M1-25, M1-26, M1-31 | `implementer` | `docs/lld/LLD-health-v3.md` (§2, §5.8); SPEC-v5 7 | `services/notify.py`, `testing/notifier.py`, `tests/services/test_notify.py`, `tests/unit/services/test_notify.py` | high | planned |
| M1-28 | M1 composition in `app.py`, status surfaces and the M1 doctor checks | HLTH-42, HLTH-40 | M1-11, M1-18, M1-23, M1-25, M1-26, M1-27, M1-31 | `implementer` | `docs/lld/LLD-health-v3.md` (§2.1, §5.9, §5.10); `docs/lld/LLD-platform-v3.md` (§4.5); SPEC-v5 7, 12 | `mcp_app/tools_ops.py`, `mcp_app/resources.py`, `mcp_app/server.py`, `app.py`, `services/doctor.py`, `tests/contract/test_status_contract.py`, `tests/unit/test_cli.py`, `tests/integration/test_app.py`, `tests/contract/test_tool_contract.py` | high | planned |
| M1-29 | Catalog of 45 sources, live check, v1 endpoint map and inventory | SRC-20, SRC-25, SRC-26 | M1-04, M1-05, M1-06, M1-07, M1-08, M1-09, M1-10, M1-11, M1-12, M1-13, M1-14, M1-15, M1-16 | `implementer` | `docs/lld/LLD-sources-v3.md` (§5.3, §5.4, §5.10); SPEC-v5 4, 17 | `cli.py`, `testing/livecheck.py`, `tools/gen_inventory.py`, `docs/generated/sources.md`, `tests/unit/sources/test_catalog.py`, `tests/unit/sources/test_live_check.py`, `tests/unit/sources/test_v1_map.py`, `tests/live/test_sources_live.py` | medium | planned |
| M1-30 | M0 follow-ups: `LaunchctlPort` in `build_app`, the `log_rotate` schedule, README | PLAT-70, PLAT-76 | none | `implementer` | `docs/lld/LLD-platform-v3.md` (§2.3, §5.10); `docs/build/M0-handoff-v1.md` (owner decisions) | `app.py`, `platform/scheduler.py`, `README.md`, `tests/integration/test_app.py`, `tests/integration/test_scheduler.py` | medium | planned |
| M1-31 | `StateStore` and `CacheStore` methods for the M1 tables: searches, call rollups and daily counts, credentials, notifications, and the `works` columns of cite and integrity | PLAT-52 | none | `implementer` | `docs/lld/LLD-platform-v3.md` (§3.1); `docs/lld/LLD-health-v3.md` (§3); `docs/lld/LLD-search-v3.md` (§3, §5.9, §5.10, §5.11); SPEC-v5 10 | `platform/stores.py`, `tests/unit/platform/test_stores.py` | high | planned |

### 2.1 Notes

- **Package files.** M1-01 is the only unit that edits `pyproject.toml` and `uv.lock`: it adds the `gcp` extra (google-auth, PLAT-13) and the `cite` extra (the `text` citation format, SPEC-v5 12). No unit adds a package `__init__.py`; `sources/` and `services/` already exist.
- **Adapters.** The registry discovers adapters, so an adapter unit touches only its modules and its `tests/sources/<id>/` folders, never `test_conformance.py`, which is parametrized over what the registry finds (LLD-sources-v3 5.3). Each adapter has the seven fixtures of LLD-sources-v3 3.4. SRC-20 is named by every adapter unit and by M1-29, which checks the whole catalog of 45.
- **Ordering by `depends_on`.** Every unit that uses another unit's contract names it: the adapters depend on M1-02 (models and the adapter protocol with `search_authors` and `updates`); citations on Semantic Scholar (M1-04) and OpenCitations (M1-13); authors on ORCID and DBLP (M1-06); integrity on Crossref updates (M1-13); credentials on the Google ADC provider (M1-01), GitHub (M1-13) and the web adapters (M1-14, M1-15, for HLTH-25); M1-18, M1-25 and M1-28 on M1-30, which edits `app.py` and `platform/scheduler.py` first; M1-18, M1-25, M1-26, M1-27 and M1-28 on M1-31, which adds the `StateStore` methods they read and write; M1-28 on M1-11, whose `platform/mcp_client.py` it wires; the catalog check (M1-29) on every adapter unit, the web adapters (M1-14, M1-15) included.
- **The generated inventory.** `tools/gen_inventory.py --check` stays a CI gate in the full `tools/ci.sh` run (the milestone gate and GitHub's CI) and leaves the `--python-only` run that each unit's acceptance uses; M1-02 makes that change to `tools/ci.sh`. An adapter unit therefore touches only its module, its fixtures and its tests (LLD-sources-v3 5.5; OC-11), and M1-29 regenerates `docs/generated/sources.md` once, after every adapter is merged (owner decision, 2026-10-27).
- **Composition in `app.py`.** `app.py` builds the registry, the services and the scheduler. M1-18 wires search recording, M1-23 the citations, authors, cite and integrity services behind the four tools, and M1-28 every other M1 wire: the registry's `health=` and `calls_today=` (so the SRC-29 daily cap applies in the daemon), the call sink to `HealthService.on_calls`, `credentials_changed` to `CredentialService.on_reload`, `NotifyService` and the `notify_webhook` policy, the `McpUpstreamPort` and `SourceContext.mcp`, provider routing in `_secret_refs` for `gcloud_adc`, and the M1 scheduler jobs. M1-30, M1-18, M1-23 and M1-28 edit `app.py` in that order.
- **Shared files across waves.** `sources/registry.py` (M1-02, then M1-03), `services/federation.py` (M1-17, then M1-18), `mcp_app/tools_discovery.py` (M1-17, then M1-23), `mcp_app/server.py` (M1-23, then M1-28) and `platform/scheduler.py` (M1-30, then M1-25), `platform/http.py` (M1-01, then M1-11), `testing/adapters.py` (M1-02, then M1-11) and `app.py` (M1-30, M1-18, M1-23, M1-28) are each edited by units that `depends_on` orders.
- **Criteria shared by two units.** SRC-20 as above. HLTH-40 (doctor) was done in M0; M1-28 names it again because it adds the M1 checks of LLD-health-v3 5.9 (`credential:<NAME>`, `probe:<source>`, `terminal_notifier`, `launchd_jobs`) and switches `daemon_alive`'s probe to the `HttpClient` the owner deferred to M1. SRCH-20 and SRCH-21 (MCP contract and argument bounds) were done in M0; M1-23 names them because it adds four tools to the same contract. PLAT-70 and PLAT-76 were done in M0; M1-30 names them because it changes `build_app` and the scheduler.
- **Gaps, listed explicitly.** (1) `docs_site` `search` and `crawl` are M2 (SPEC-v5 14). (2) HLTH-41 (`doctor --notify`) is M2 by PRD-health v4. (3) The M1 owner checks are not tasks; see section 3.

### 2.2 Clarifications

Lessons from M0 and requirements for the unit named; the LLDs repeat them where they belong.

| Unit | Source | Requirement |
| --- | --- | --- |
| every unit | M0 runs `rm-m0b` and `rm-m0f` | Only change files in your scope. A file another unit owns that is not merged yet is a reason to report status blocked, not to create it. Tests pass with the network blocked; live calls go only through the opt-in live check (SRC-25). |
| every adapter unit | LLD-sources-v3 5.5 | Follow the new-source checklist: `SourceSpec` with hosts, auth and `RateSpec` from the provider's published limits (record any `[assumption]` in the handoff), seven fixtures, conformance passing, no credential in fixtures (`tests/security` scans them). |
| M1-11 | SRC-22 | Upstream MCP calls go through `McpUpstreamPort` over the shared `HttpClient`, so host policy, rate limits, telemetry and redaction apply; no adapter opens its own client. |
| M1-12 | SRC-23 | Host and path matching rejects substring tricks (`docs.example.com.evil`, `evil.com/docs.example.com`) and honours `robots.txt` before any `get`. |
| M1-18 | M0 plan v4 2.2 (M0-13) | M0 records searches through a no-op port; this unit wires the port to `StateStore.search_put`, which M1-31 adds, in the composition root. The `searches` table already exists (state migration 0001); add no migration unless the LLD's columns differ. |
| M1-26 | HLTH-43 | Credential rows hold metadata only (state, fingerprint, expiry, quota); no column, log line or notification carries a value. |
| M1-28 | M0 handoff, owner decision (2026-10-25); LLD-health-v3 5.9 | `daemon_alive` keeps its own `httpx.AsyncClient` for the loopback `/healthz` call, within the 3 s liveness budget. The `HttpClient` and the registry serve only the new `probe:<source>` checks. |
| M1-28 | plan check `rm-m1a`; LLD-platform-v3 5.5 | Scheduler jobs are registered in `app.py`, so this unit wires the M1 jobs: the probes, `health_evaluate` (every 60 s), `health_rollup` (hourly) and the local-target probes (every 15 minutes) (M1-25), `credential_sync` (M1-26) and `digest` (M1-27). Those units expose the job functions and test them directly; they do not edit `app.py`. |
| M1-25 | plan check `rm-m1e`; LLD-health-v3 5.3, 5.4 | `HealthService.on_calls` and probe handling call `CredentialService.on_expiry_header` and `on_auth_result`, so this unit runs after M1-26; `CredentialService` does not take a `HealthService`. In `platform/scheduler.py` add what the health jobs need and nothing else: one due time per enabled, configured source in `schedule_runs` (`job = "probe:<source>"`) with the cadence and jitter of LLD-health-v3 5.4, and an hourly schedule (minute 5) for `health_rollup` (5.3). Registering the jobs stays M1-28's. HLTH-25 is shared with M1-26: this unit tests the parts it builds (Brave and Programmable Search probes at most once per 24 h, Brave's rate-limit headers updating the quota through `on_calls`) in `tests/services/test_credentials.py`, and that `on_calls` forwards GitHub's expiry header to `CredentialService.on_expiry_header` (HLTH-21). |
| M1-20 | plan check `rm-m1e`; LLD-search-v3 5.3 | Add `to_csl(work) -> dict` to `services/works.py`, the CSL-JSON item that cite formats from and the cache component stores in M2. |
| M1-25 | plan check `rm-m1d`; LLD-health-v3 5.5, 7 | Expose and test the `health_evaluate` job function: it re-runs `evaluate_source` for every source, writes state changes and emits their events. |
| M1-24 | pre-review of v6; LLD-health-v3 2.6, 5.7 | Define `HealthEvent` and `EventKind` in `services/health_eval.py`; M1-25, M1-26 and M1-27 import them from there. |
| M1-26 | pre-review of v6; LLD-health-v3 5.7 | `CredentialService` takes a `run_probes` callable for `on_reload` (LLD-health-v3 5.7 says it runs `HealthService.run_probe`); M1-28 wires it to the health service. Test HLTH-25's free validation (the SerpAPI account endpoint, Vertex engine metadata) here; M1-25 tests the probe and quota parts. |
| M1-27 | pre-review of v6; LLD-health-v3 5.8 | `NotifyService.banners()` reads `HealthService.active_keys()`; this unit runs after M1-25 for that. |
| M1-23 | pre-review of v6; LLD-search-v3 2.3, 5.10 | Register the M1 prompts in `mcp_app/prompts.py`, and in `app.py` register the `integrity_recheck` job handler with `JobService` besides wiring the four search services. |
| M1-24 | plan check `rm-m1d`; LLD-health-v3 5.5, 5.7 | Define `CredentialStateView` (name, state, `days_left`) in `services/health_eval.py`; `EvalInputs.required_credentials` uses it, and M1-26's `CredentialService.evaluate` imports it from there. |
| M1-02 | plan check `rm-m1a`; LLD-sources-v3 5.13; LLD-search-v3 5.9 | Add the helper-spec mechanism to the registry: a module that declares a `SourceSpec` as a helper (no `ADAPTER`, no search capability) gives `registry.policy(id)` its hosts and rate limit for the `HttpClient`, and stays out of `list_sources`, the inventory and conformance. Test it in `tests/unit/sources/test_registry.py` with a helper declared in the test. |
| M1-31 | plan check `rm-m1c`; LLD-health-v3 3; LLD-search-v3 3 | The state tables exist since migration 0001; add only `StateStore` methods: `search_put`, the call rollups and their pruning, a per-source count of today's calls (for `calls_today=`, SRC-29), credential metadata rows (no value column, HLTH-43) notifications with their acknowledged and snoozed state, and the per-source reads of `calls` that health needs (the last N non-probe calls, a time window, the last 2xx non-probe call, 24-hour figures; LLD-health-v3 5.4, 5.5). On `CacheStore` (`cache.db`): read a work's `csl_json` by work id or identifier (cite), write `integrity_status` and `integrity_checked_at`, and list the cached works (`check_integrity` with `ids="cache"`). M1 creates no `works` rows; the cache component does in M2, so with an empty cache these methods return nothing. Add no migration unless an LLD column is missing. |
| M1-02 | plan check `rm-m1b`; LLD-sources-v3 5.3 | Key the conformance checks by capability: a source without `search` (for example `docs_site`, `opencitations`, `crossref_updates`) runs the checks of the capabilities it declares, never `search`. Let the harness take an `mcp` factory (default `None`) for the `SourceContext`, so M1-11 can plug in `McpUpstreamPort` over the harness's `HttpClient` (LLD-sources-v3 5.6). Move `tools/gen_inventory.py --check` from the `--python-only` run to the full run of `tools/ci.sh`. List in the handoff every `defaults.toml` value read from v1 (DSpace base URLs, Syncope seeds) for the owner to confirm before M1-29 runs. |
| M1-01 | plan check `rm-m1b`; LLD-platform-v3 4.2; LLD-health-v3 5.2 | Add the `gcloud_adc` `SecretRef` backend and `SecretMeta.account` and `expires_at` in `platform/secrets.py`, and the `X-Goog-User-Project` header for the Vertex origin in `platform/http.py`. Routing `gcloud_adc` references in `app.py` is M1-28's. |
| M1-11 | plan check `rm-m1b`; LLD-sources-v3 5.6; LLD-platform-v3 4.4 | `McpUpstreamPort` speaks streamable HTTP over the shared `HttpClient`: add what `platform/http.py` needs to read `text/event-stream` replies and the `Mcp-Session-Id` header, without a second client. Put the in-memory MCP server fake in `research_mcp.testing.adapters`, and set the harness's `mcp` factory in `tests/sources/conftest.py` to an `McpUpstreamPort` over the harness's `HttpClient`, so conformance sees real HTTP traffic for `aws_knowledge` and `ms_learn`. Building the port in `app.py` is M1-28's. |
| M1-03 | plan check `rm-m1b` | Declare the fake web adapters that `tests/services/test_web_group.py` needs inside that test; `testing/adapters.py` is not in this unit's scope. |
| M1-21 | plan check `rm-m1a` | `sources/doi_resolver.py` only declares the `doi_resolver` helper spec through the M1-02 mechanism (host `doi.org`, its own rate limit); it does not edit `registry.py`. |
| M1-30 | M0 handoff, owner decisions (2026-10-25) | Type `launchctl` as `LaunchctlPort` in `build_app` and keep the redactor seam; run `log_rotate` every 15 minutes and once at start; update the README (clients reach the daemon only through the shim, no `token_keychain` setting, the daemon and `install` are built). |

## 3. Verification

> **Owner:** A · **Persona:** `planner`

At the end of each slice the `verifier` checks that every merged unit's criteria have passing tests that cite them, that the behavior entry points carry `@spec`, and that `node tools/sdd/cli.mjs check` and `tools/ci.sh --python-only` pass. The milestone exit gate is in [test plan v5](../test/test-plan-v5.md) 1.4 and SPEC-v5 section 17: all M1 tests pass; 45 or more sources registered and passing conformance (PRD-v8 OUT-1); the owner checks OC-03 (a real macOS notification opens the right UI page), OC-08 (CI on GitHub Actions, macOS and Linux, Python 3.12 and 3.13, with the secret scan and weekly audit), OC-11 (an agent adds a new free source in one work unit touching only the allowed files), OC-12 (a five-source live search under 8 s at p95 over 20 runs) and OC-14.

## 4. Open questions

> **Owner:** A · **Persona:** `planner`

- [x] Q: The M0 owner decisions call for LLD and SPEC corrections (LLD-health-v3 5.9, LLD-platform-v3 2.3, 4.1, 5.2, 5.10, LLD-search-v3 5.2, LLD-sources-v3 5.2 row 8, SPEC-v5 3, 14, 17). Agents read the LLDs as the source of truth, so a stale rule (for example `normalize_url` removing one trailing slash) can cost attempts. Options: (a) draft and approve the next LLD versions before the M1 run; (b) run M1 now and rely on the M0 handoff's decision table, which section 2.2 points to. Recommendation: (a) for the LLDs that M1 units implement (sources, search, health, platform). The owner decides. **Resolved (owner decision, 2026-10-26):** option (a): LLD-platform, LLD-health, LLD-search and LLD-sources v3 carry the corrections, the task table cites v3, and they are approved with this plan. The SPEC-v5 corrections (sections 3, 14, 17) wait for the next SPEC version; no M1 unit depends on them.
- [x] Q: OC-08 needs CI on GitHub Actions. `main` is on GitHub now; the workflow from M0-01 exists in `.github/workflows/ci.yml`. Options: (a) confirm the workflow runs green on GitHub before the M1 exit; (b) defer OC-08. Recommendation: (a). The owner decides. **Resolved (owner decision, 2026-10-26):** option (a). On 2026-10-26 the `ci` workflow passed on `main` for macOS and Ubuntu with Python 3.12 and 3.13, and the secret scan passed; the weekly dependency audit is scheduled and has not run yet, so OC-08 is recorded once it does (or after a manual `gh workflow run ci`).
- [x] Q: Many adapters and OC-12 need provider keys (CORE, Lens, ADS, NVD, GitHub, Semantic Scholar if used with a key, Brave, SerpAPI, Programmable Search, Vertex). Units use fixtures only, so keys are needed only for the opt-in live check and the owner checks. Options: (a) the owner adds the keys to the Keychain before the live check; (b) run the live check only for free sources. Recommendation: (a) before OC-12. The owner decides. **Resolved (owner decision, 2026-10-26):** option (a): the owner adds the provider keys to the Keychain before the live check and OC-12.
- [x] Q: Slice 2 has 14 units that can run at once. Options: (a) let ECC run them in parallel within its concurrency limit; (b) cap the wave at 4 to limit cost and review load. Recommendation: (b) for the first wave, then raise it if reviews keep up. The owner decides. **Resolved (owner decision, 2026-10-26):** option (b). `ecc drive` dispatches one unit at a time (run `rm-m0f` never had two units running), so the cap holds with no setting; the slices give the order, not parallel runs.
