---
title: "M0 plan: foundations and three sources"
type: plan
version: 1
status: draft
owner: "Kenny Hill"
milestone: M0
artifact_type: plan
components: [cache, health, platform, search, security, sources]
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# M0 plan (v1)

Milestone M0 is the ECC pilot: the platform, identifiers, three sources and the first MCP tools, as SPEC-v2 section 12.3 broke it down. `tools/gen_m0_plan.py` builds `.orchestration/plan-m0.json` from the task table below; keep its columns. M0-01 to M0-05 were built and merged in the first run (`rm-m0b`); their tests now cite the SDD criteria.

## 1. Slices

> **Owner:** A · **Persona:** `planner`

Each wave is a slice; units in one wave have no overlapping files and can run in parallel.

| Slice | Units | Checkpoint |
| --- | --- | --- |
| 1 | M0-01 | every unit merged with its criteria passing |
| 2 | M0-02, M0-04 | every unit merged with its criteria passing |
| 3 | M0-03, M0-05 | every unit merged with its criteria passing |
| 4 | M0-06, M0-08 | every unit merged with its criteria passing |
| 5 | M0-07 | every unit merged with its criteria passing |
| 6 | M0-09 | every unit merged with its criteria passing |
| 7 | M0-10, M0-11, M0-12, M0-13 | every unit merged with its criteria passing |
| 8 | M0-14 | every unit merged with its criteria passing |
| 9 | M0-15 | every unit merged with its criteria passing |
| 10 | M0-16 | every unit merged with its criteria passing |

## 2. Tasks

> **Owner:** A · **Persona:** `planner`

Columns after Persona are read by `tools/gen_m0_plan.py`: the LLDs the unit implements, its file scope (paths under `src/research_mcp/` unless they start with `src/`, `tests/`, `tools/`, `docs/` or `.github/`; `fixtures/*` stands for the seven fixtures of the sources LLD), the risk that sets its routing tier, and its status.

| # | Task | Criteria | Depends on | Persona | Implements | Files (scope) | Risk | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0-01 | Repository scaffold, packages and CI script | PLAT-1, PLAT-2, PLAT-3, PLAT-5, PLAT-4 | none | `implementer` | `docs/lld/LLD-platform-v1.md` (SPEC-v2 1, 12.1) | `pyproject.toml`, `uv.lock`, `.python-version`, `src/research_mcp/__init__.py`, `src/research_mcp/version.py`, `src/research_mcp/core/__init__.py`, `src/research_mcp/platform/__init__.py`, `src/research_mcp/sources/__init__.py`, `src/research_mcp/services/__init__.py`, `src/research_mcp/mcp_app/__init__.py`, `src/research_mcp/ui/__init__.py`, `src/research_mcp/testing/__init__.py`, `tools/ci.sh`, `.github/workflows/ci.yml`, `tests/conftest.py`, `tests/unit/test_version.py`, `tests/unit/test_import_side_effects.py`, `tests/unit/test_network_guard.py`, `src/research_mcp/packaging/__init__.py` | high | done |
| M0-02 | Identifier normalization | SRCH-10, SRCH-11, SRCH-12, SRCH-13, SRCH-14, SRCH-15, SRCH-16 | M0-01 | `implementer` | `docs/lld/LLD-search-v1.md` (SPEC-v2 6 (`core/ids.py`)) | `core/ids.py`, `tests/unit/core/test_ids.py` | medium | done |
| M0-03 | Specs, models, errors, envelope, budget and test clock | PLAT-30, PLAT-31, PLAT-32, PLAT-33, PLAT-6, PLAT-34 | M0-02 | `implementer` | `docs/lld/LLD-platform-v1.md`; `docs/lld/LLD-sources-v1.md` (SPEC-v2 3.7 (types, `HttpError`, context), 4 (`core/specs.py`, `core/models.py`)) | `core/specs.py`, `core/models.py`, `core/errors.py`, `core/context.py`, `core/envelope.py`, `core/budget.py`, `core/timeutil.py`, `testing/clock.py`, `tests/unit/core/test_envelope.py`, `tests/unit/core/test_budget.py`, `tests/unit/core/test_models.py` | medium | done |
| M0-04 | Settings and paths | PLAT-8, PLAT-9, PLAT-10, PLAT-11 | M0-01 | `implementer` | `docs/lld/LLD-platform-v1.md` (SPEC-v2 2) | `settings.py`, `tests/unit/test_settings.py` | medium | done |
| M0-05 | Secrets and Keychain provider | PLAT-12, SEC-1, SEC-2, SEC-13, SEC-3, SEC-4 | M0-04 | `implementer` | `docs/lld/LLD-platform-v1.md` (SPEC-v2 3.1) | `platform/secrets.py`, `tests/unit/platform/test_secrets.py` | high | done |
| M0-06 | Redaction and structured logging | SEC-5, SEC-6, SEC-14, SEC-7, PLAT-40, PLAT-41, PLAT-42 | M0-03, M0-05 | `implementer` | `docs/lld/LLD-platform-v1.md` (SPEC-v2 3.2) | `platform/redact.py`, `platform/logging.py`, `tests/unit/platform/test_redact.py`, `tests/unit/platform/test_logging.py`, `tests/security/test_no_secret_in_logs.py` | high | planned |
| M0-07 | Async HTTP client, rate limits and downloader | PLAT-35, PLAT-36, PLAT-37, PLAT-38, PLAT-39, SEC-8, SEC-9, SEC-10, CACHE-1, CACHE-2 | M0-03, M0-06 | `implementer` | `docs/lld/LLD-platform-v1.md` (SPEC-v2 3.3, 3.4) | `platform/http.py`, `platform/download.py`, `platform/ratelimit.py`, `tests/unit/platform/test_http.py`, `tests/unit/platform/test_ratelimit.py`, `tests/unit/platform/test_downloader.py`, `tests/security/test_scoped_credentials.py` | high | planned |
| M0-08 | Stores and migrations | PLAT-50, PLAT-51, PLAT-52, PLAT-53 | M0-03 | `implementer` | `docs/lld/LLD-platform-v1.md`; `docs/lld/LLD-cache-v1.md`; `docs/lld/LLD-health-v1.md` (SPEC-v2 3.5, 8.1, 10.1) | `platform/stores.py`, `platform/migrations/state/0001_init.sql`, `platform/migrations/cache/0001_init.sql`, `tests/unit/platform/test_stores.py` | high | planned |
| M0-09 | Source contract, registry and conformance suite | SRC-1, SRC-2, SRC-3, SRC-4, SRC-5, SRC-6, SRC-7 | M0-02, M0-07 | `implementer` | `docs/lld/LLD-sources-v1.md` (SPEC-v2 4 (`sources/base.py`), 5.1, 5.2) | `sources/base.py`, `sources/registry.py`, `testing/adapters.py`, `tests/sources/conftest.py`, `tests/sources/test_conformance.py`, `tests/unit/sources/test_registry.py`, `tests/unit/sources/test_adapter_imports.py` | high | planned |
| M0-10 | arXiv adapter | SRC-10 | M0-09 | `implementer` | `docs/lld/LLD-sources-v1.md` (SPEC-v2 4, 5.2) | `sources/arxiv.py`, `tests/sources/arxiv/fixtures/*`, `tests/sources/arxiv/test_arxiv.py` | medium | planned |
| M0-11 | Crossref adapter | SRC-11 | M0-09 | `implementer` | `docs/lld/LLD-sources-v1.md` (SPEC-v2 4, 5.2) | `sources/crossref.py`, `tests/sources/crossref/fixtures/*`, `tests/sources/crossref/test_crossref.py` | medium | planned |
| M0-12 | OpenAlex adapter | SRC-12 | M0-09 | `implementer` | `docs/lld/LLD-sources-v1.md` (SPEC-v2 4, 5.2) | `sources/openalex.py`, `tests/sources/openalex/fixtures/*`, `tests/sources/openalex/test_openalex.py` | medium | planned |
| M0-13 | Grouping, merge and federation service | SRCH-1, SRCH-2, SRCH-3, SRCH-4, SRCH-5, SRCH-6, SRCH-7, SRCH-8, SRCH-9, SRCH-17 | M0-09 | `implementer` | `docs/lld/LLD-search-v1.md` (SPEC-v2 6 (`services/works.py`), 7.1) | `services/federation.py`, `services/works.py`, `tests/services/test_federation.py`, `tests/services/test_works.py` | high | planned |
| M0-14 | MCP app: M0 tools, the sources resource and `@tool_boundary` | SRCH-20, SRCH-21, SRCH-22, SRCH-23, SRC-8, PLAT-60, PLAT-61, PLAT-62, PLAT-63 | M0-08, M0-13 | `implementer` | `docs/lld/LLD-platform-v1.md`; `docs/lld/LLD-search-v1.md` (SPEC-v2 3.7 (`tool_boundary`), 7.2 (M0 rows), 7.3 (M0 row), 7.4 (`build_mcp`)) | `mcp_app/server.py`, `mcp_app/tools_discovery.py`, `mcp_app/resources.py`, `tests/contract/conftest.py`, `tests/contract/test_tools_discovery.py`, `tests/contract/test_tool_contract.py` | high | planned |
| M0-15 | Daemon, composition root, scheduler and stdio shim | PLAT-70, SEC-11, SEC-12, PLAT-71, PLAT-72, PLAT-73, PLAT-74, PLAT-75, PLAT-76, PLAT-77 | M0-05, M0-14 | `implementer` | `docs/lld/LLD-platform-v1.md`; `docs/lld/LLD-health-v1.md` (SPEC-v2 3.6 (jobs, scheduler), 7.4 (mount), 10.5 (healthz, readyz)) | `app.py`, `daemon.py`, `shim.py`, `platform/auth.py`, `platform/jobs.py`, `platform/scheduler.py`, `testing/launchctl.py`, `tests/unit/test_app.py`, `tests/unit/test_shim.py`, `tests/unit/test_jobs.py`, `tests/unit/test_scheduler.py`, `tests/security/test_loopback_auth.py` | high | planned |
| M0-16 | CLI, install, doctor skeleton and launchd templates | PLAT-80, PLAT-81, PLAT-82, PLAT-83, SRC-13, HLTH-40 | M0-10, M0-11, M0-12, M0-15 | `implementer` | `docs/lld/LLD-health-v1.md`; `docs/lld/LLD-platform-v1.md` (SPEC-v2 10.5 (doctor skeleton), 12.1 (CLI), 12.2) | `cli.py`, `packaging/launchd/local.research-mcpd.plist.template`, `packaging/launchd/local.research-mcp-doctor.plist.template`, `packaging/launchd/local.research-mcp-watchdog.plist.template` (all under src/research_mcp), `tools/gen_inventory.py`, `docs/generated/sources.md`, `tests/unit/test_cli.py`, `tests/unit/test_install.py` | medium | planned |

### 2.1 Notes

- **Package scaffolding.** M0-01 declares every dependency, extra and pytest setting in the platform LLD (SPEC-v2 12.1), and creates every package `__init__.py`. No later unit edits `pyproject.toml`, `uv.lock` or an `__init__.py`.
- **No test packages.** Test folders have no `__init__.py`; pytest runs in importlib mode.
- **Parallel units.** Scopes do not overlap, so units in the same wave can run in parallel.
- **Source discovery.** The registry finds adapters, so adapter units touch no shared file.
- **Fixtures.** In the scope column, `fixtures/*` stands for the seven fixtures in the sources LLD (SPEC-v2 5.2). The generated plan lists them by name.

### 2.2 Clarifications from the first M0 attempt

Carried from SPEC-v2 section 0.6. They are requirements for the unit named; the LLDs repeat them where they belong.

| Unit | SPEC-v2 section | Requirement |
| --- | --- | --- |
| M0-01 | 1, 12.1; PLAT-5, NFR-9 | The offline network guard MUST be installed for the whole test session (a session-scoped autouse fixture or a plugin active before collection), not per test. It MUST refuse, before any I/O, `socket.socket.connect`, `connect_ex`, `sendto`, `sendmsg` and `socket.create_connection` to non-loopback addresses, and `getaddrinfo`, `gethostbyname`, `gethostbyname_ex` and `gethostbyaddr` for non-loopback names. Loopback MUST keep working. Negative tests MUST prove each refusal happens before I/O. |
| M0-01 | 1; PLAT-3 | Import side effects MUST be attributed to `research_mcp` when any frame of the stack belongs to it, not only the innermost frame; a dependency doing I/O on behalf of a `research_mcp` import (for example settings construction reading the environment at import time) counts. Include that case as a regression test. |
| M0-01 | 12.1; PLAT-FR-53 | The CI workflow MUST run on macOS and Linux with Python 3.12 and 3.13, pin every action by commit SHA, scan for secrets, and run a weekly dependency audit. |
| M0-02 | 6; SRCH-10, SRCH-15 | Every normalizer MUST be idempotent (for example a repository name ending `.git.git` normalizes once to its final form). Percent-decoding MUST be strict UTF-8; invalid sequences raise `IdentifierError` instead of becoming replacement characters. DOI suffixes keep their slashes; handle suffixes MAY contain slashes, and a trailing slash is significant where 6 says so. |
| M0-03 | 3.7, 4; PLAT-31, SRCH-FR-4 | `Budget.fit` MUST keep `FederatedResult.statuses` (one status per source) and MUST fail explicitly when mandatory metadata cannot fit. Its prefix search MUST distinguish "does not validate" from "too large". |
| M0-04 | 2; PLAT-8, PLAT-9 | Paths MUST be normalized (resolving `..`) before the durable-location check. Credential names MUST keep their canonical case across TOML and `RESEARCH_MCP_` environment overrides, so an environment override updates the same credential the TOML defines. |
| M0-05 | 3.1; PLAT-12, SEC-13 | `SecretRef` MUST validate on construction: the name matches the allowed pattern, and a Keychain reference's service is exactly `research-mcp/<NAME>`. No control character (in particular a newline) may reach the `security -i` script. `FakeProvider.metadata` MUST behave like `KeychainProvider.metadata` (no metadata for `env:` references). |

## 3. Verification

> **Owner:** A · **Persona:** `planner`

At the end of each slice the `verifier` checks that every merged unit's criteria have passing tests that cite them, that the behavior entry points carry `@spec`, and that `node tools/sdd/cli.mjs check` and `tools/ci.sh --python-only` pass. The milestone exit gate is in [the test plan](../test/test-plan-v1.md) (section 1.4, milestone exit gates).

## 4. Open questions

> **Owner:** A · **Persona:** `planner`

- [ ] Q: Should the next ECC run start from M0-06, treating M0-01 to M0-05 as merged, or rebuild every unit from this plan? The generator still emits all 16 units, as before.
- [ ] Q: M0-06 and M0-08 have unmerged branches from the first run that cite the old test ids. Discard them, or let the next run start from them?

