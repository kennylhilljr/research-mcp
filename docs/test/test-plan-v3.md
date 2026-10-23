---
title: "Research MCP v2 test plan"
type: test-plan
version: 3
status: draft
supersedes: docs/test/test-plan-v2.md
owner: "Kenny Hill"
artifact_type: test-strategy
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/test-plan/TEST-PLAN-v3.md
deferred: []
excepted: []
date: 2026-10-22
---

# Test plan (v3)

The approved test strategy for Research MCP v2: how every acceptance criterion in the component PRDs is verified. It carries over [TEST-PLAN v3](../../docs-archive/test-plan/TEST-PLAN-v3.md) with SDD IDs (acceptance test `AT-PLAT-31` is now criterion `PLAT-31`; requirement `FR-PLAT-30` is now `PLAT-FR-30`). The criteria themselves live in each component PRD, section 2.4. Version 2 added the criteria from the owner's Gate 1 answers of 2026-10-22 ([PRD v7](../prd/PRD-v7.md) and its component PRDs). Version 3 supersedes [test plan v2](test-plan-v2.md) and records the owner's decisions of 2026-10-22: OC-14 joins the M1 exit gate (1.4), a "No secret at rest" area joins 1.2, and a second exception covers owner-run migration commands (section 4). Tests cite their criterion first in the docstring (`"""@spec PLAT-31: ..."""`), and `docs/trace/coverage.md` is derived from those citations.

## 1. Strategy

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves

### 1.1 Levels and environments

| Level | Runs | Network | External systems |
|---|---|---|---|
| unit | every work unit and commit (`tools/ci.sh --python-only`) | blocked | none |
| integration | every commit | blocked | fakes from `research_mcp.testing`: `httpx.MockTransport` with recorded fixtures, `FakeProvider`, `FakeClock` and fake sleeper, fake `launchctl`, fake notifier, injected resolver, temp folders for Drive |
| contract | every commit | blocked | in-memory MCP client (`mcp.shared.memory`) against `build_mcp` |
| live | opt-in (`pytest -m live`), nightly on the Mac later | allowed | real upstreams, no credentials unless the owner runs it locally |

Network blocking: `tests/conftest.py` installs a socket guard that fails any test opening a non-loopback connection unless it is marked `live`; `pyproject.toml` deselects `live` tests by default (`-m 'not live'`). Tests run with `--import-mode=importlib`; test folders have no `__init__.py`.

Secrets in tests: only `FakeProvider` with generated values; the security suite registers those values with the redactor and scans every output.

### 1.2 Cross-cutting tests that every milestone keeps green

| Area | Rule | Tests |
|---|---|---|
| No secret in any output | Logs, errors, tool results, UI pages, notifications and process argument lists never contain a registered secret | SEC-1, SEC-5, SEC-6, SEC-7, SEC-9, SEC-10, SEC-13, SEC-14, HLTH-32, HLTH-34, UI-4, MIG-22 |
| No secret at rest | No registered secret is stored in configuration, Application Support or log files, and credentials are kept as metadata only (owner decision, 2026-10-22) | SEC-24, SEC-27, HLTH-43, MIG-23 |
| Loopback and auth | Nothing binds beyond loopback; every request is authenticated | PLAT-10, PLAT-71, SEC-11, SEC-12, SEC-26, UI-2, UI-3, UI-20 |
| Async discipline | The event loop never blocks | PLAT-75, SRCH-1, ruff ASYNC rules |
| Bounded output | No result exceeds the budget | PLAT-31, PLAT-63 |
| Untrusted content | Fetched text is always enveloped | PLAT-33, SEC-22 |
| Adapter isolation | Adapters do no I/O of their own | SRC-7, conformance |
| No silent deletion | Nothing is deleted without an owner decision; MCP discards are announced; shared files survive | CACHE-33, CACHE-34, CACHE-36, CACHE-48, SEC-20 |
| Docs follow code | The generated inventory and plan are current and the trace check passes | SRC-13, `node tools/sdd/cli.mjs check` in CI |

### 1.3 Fixtures and fakes

| Fake or fixture | Location | Used by |
|---|---|---|
| Recorded source fixtures (seven per adapter) | `tests/sources/<id>/fixtures/` | conformance, adapter tests, federation |
| `FakeProvider` (secrets; records argv) | `src/research_mcp/platform/secrets.py` | all tests that need credentials |
| `FakeClock`, fake `Sleeper` | `src/research_mcp/testing/clock.py` | rate limits, retries, scheduler, lifecycle, notifications |
| Fake adapters (configurable latency, failures) | `src/research_mcp/testing/adapters.py` | registry, conformance, federation |
| `FakeLaunchctl` | `src/research_mcp/testing/launchctl.py` | shim, install, doctor |
| `FakeNotifier`, fake resolver | `src/research_mcp/testing/notifier.py`, test-local | notifications (M1), downloader |
| In-memory MCP client | `tests/contract/conftest.py` | contract tests |
| Synthetic v1 database | `tests/migration/fixtures/make_v1_db.py` | legacy import (reproduces 54 pairs, 10 URL rows, harv and penn ids) |
| Hostile PDF corpus | `tests/fixtures/pdf/hostile/` | SEC-23 |
| Temp "Drive" folder | pytest `tmp_path` laid out as `CloudStorage/GoogleDrive-test/My Drive` | archive tests |

### 1.4 Milestone exit gates

| Milestone | Gate |
|---|---|
| M0 | Every M0 criterion in docs/build/M0-plan-v1.md has a passing test that cites it; full `tools/ci.sh` green (including `node tools/sdd/cli.mjs check`) (lint, strict mypy, coverage 85% on `src/`, build, `--help`); owner checks OC-01 and OC-02. |
| M1 | All M1 tests pass; 45 or more sources registered and passing conformance (PRD-v7 OUT-1); OC-03, OC-08 (once a remote exists), OC-11, OC-12, OC-14 (owner decision, 2026-10-22). |
| M2 | All M2 tests pass, including the hostile PDF corpus; OC-04, OC-10 and OC-13. |
| M3 | All M3 tests pass; OC-05 and OC-09. |
| M4 | All M4 tests pass; OC-06 then OC-07. |

## 2. Planned evidence

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves

Every criterion, in the order of the earlier catalog. The work unit is the M0 task that owns the criterion (later milestones assign units when their plan is written).


### 2.1 Platform (PLAT, [PRD](../prd/components/PRD-platform-v4.md) and [LLD](../lld/LLD-platform-v1.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| PLAT-1 | `tests/unit/test_version.py::test_version_is_3x_and_matches_metadata` | unit | M0 | M0-01 |
| PLAT-2 | `tests/unit/test_version.py::test_ci_script_is_executable_bash` | unit | M0 | M0-01 |
| PLAT-3 | `tests/unit/test_import_side_effects.py::test_third_party_modules_cover_base_dependencies`, `tests/unit/test_import_side_effects.py::test_probe_detects_import_side_effects`, `tests/unit/test_import_side_effects.py::test_probe_detects_work_done_through_a_dependency`, `tests/unit/test_import_side_effects.py::test_importing_research_mcp_does_no_work` | unit | M0 | M0-01 |
| PLAT-5 | `tests/unit/test_network_guard.py::test_blocks_connect_before_io`, `tests/unit/test_network_guard.py::test_blocks_create_connection_before_io`, `tests/unit/test_network_guard.py::test_blocks_datagrams_before_io`, `tests/unit/test_network_guard.py::test_blocks_name_lookup_before_io`, `tests/unit/test_network_guard.py::test_blocks_reverse_lookup_before_io`, `tests/unit/test_network_guard.py::test_blocks_loopback_lookalikes_before_io`, `tests/unit/test_network_guard.py::test_blocks_async_http_client`, `tests/unit/test_network_guard.py::test_passes_loopback_through`, `tests/unit/test_network_guard.py::test_allows_loopback_server`, `tests/unit/test_network_guard.py::test_live_tests_deselected_by_default`, `tests/unit/test_network_guard.py::test_live_tests_run_unguarded_when_selected`, `tests/unit/test_network_guard.py::test_guard_covers_session_fixtures`, `tests/unit/test_network_guard.py::test_guard_covers_collection` | unit | M0 | M0-01 |
| PLAT-4 | `tests/unit/test_version.py::test_heavy_dependencies_are_extras` | unit | M0 | M0-01 |
| PLAT-30 | `tests/unit/core/test_envelope.py::test_envelope` | unit | M0 | M0-03 |
| PLAT-31 | `tests/unit/core/test_budget.py::test_budget`, `tests/unit/core/test_budget.py::test_statuses_are_mandatory`, `tests/unit/core/test_budget.py::test_invalid_prefix_is_not_a_size_result` | unit | M0 | M0-03 |
| PLAT-32 | `tests/unit/core/test_envelope.py::test_errors` | unit | M0 | M0-03 |
| PLAT-33 | `tests/unit/core/test_envelope.py::test_untrusted` | unit | M0 | M0-03 |
| PLAT-6 | `tests/unit/core/test_models.py::test_models_and_clock` | unit | M0 | M0-03 |
| PLAT-34 | `tests/unit/core/test_budget.py::test_cursors` | unit | M0 | M0-03 |
| PLAT-8 | `tests/unit/test_settings.py::test_defaults`, `tests/unit/test_settings.py::test_toml_and_environment`, `tests/unit/test_settings.py::test_typed_web_source_defaults`, `tests/unit/test_settings.py::test_invalid_values`, `tests/unit/test_settings.py::test_webhook_rejects_tokens`, `tests/unit/test_settings.py::test_webhook_accepts_plain_url`, `tests/unit/test_settings.py::test_rotate_by_is_utc` | unit | M0 | M0-04 |
| PLAT-9 | `tests/unit/test_settings.py::test_paths_and_creation`, `tests/unit/test_settings.py::test_reject_purgeable_paths`, `tests/unit/test_settings.py::test_normalization_and_symlinks` | unit | M0 | M0-04 |
| PLAT-10 | `tests/unit/test_settings.py::test_non_loopback`, `tests/unit/test_settings.py::test_loopback` | unit | M0 | M0-04 |
| PLAT-11 | `tests/unit/test_settings.py::test_placeholder_email`, `tests/unit/test_settings.py::test_optional_email` | unit | M0 | M0-04 |
| PLAT-12 | `tests/unit/platform/test_secrets.py::test_parse_valid_references`, `tests/unit/platform/test_secrets.py::test_parse_rejects_malformed_references`, `tests/unit/platform/test_secrets.py::test_direct_construction_validates`, `tests/unit/platform/test_secrets.py::test_parse_error_does_not_echo_input` | unit | M0 | M0-05 |
| PLAT-40 | planned | unit | M0 | M0-06 |
| PLAT-41 | planned | unit | M0 | M0-06 |
| PLAT-42 | planned | unit | M0 | M0-06 |
| PLAT-35 | planned | unit | M0 | M0-07 |
| PLAT-36 | planned | unit | M0 | M0-07 |
| PLAT-37 | planned | unit | M0 | M0-07 |
| PLAT-38 | planned | unit | M0 | M0-07 |
| PLAT-39 | planned | unit | M0 | M0-07 |
| PLAT-50 | planned | unit | M0 | M0-08 |
| PLAT-51 | planned | unit | M0 | M0-08 |
| PLAT-52 | planned | unit | M0 | M0-08 |
| PLAT-53 | planned | unit | M0 | M0-08 |
| PLAT-60 | planned | contract | M0 | M0-14 |
| PLAT-61 | planned | contract | M0 | M0-14 |
| PLAT-62 | planned | contract | M0 | M0-14 |
| PLAT-63 | planned | contract | M0 | M0-14 |
| PLAT-70 | planned | integration | M0 | M0-15 |
| PLAT-71 | planned | integration | M0 | M0-15 |
| PLAT-72 | planned | integration | M0 | M0-15 |
| PLAT-73 | planned | integration | M0 | M0-15 |
| PLAT-74 | planned | integration | M0 | M0-15 |
| PLAT-75 | planned | integration | M0 | M0-15 |
| PLAT-76 | planned | integration | M0 | M0-15 |
| PLAT-77 | planned | integration | M0 | M0-15 |
| PLAT-80 | planned | unit | M0 | M0-16 |
| PLAT-81 | planned | unit | M0 | M0-16 |
| PLAT-82 | planned | unit | M0 | M0-16 |
| PLAT-83 | planned | unit | M0 | M0-16 |
| PLAT-13 | planned | unit | M1 |  |
| PLAT-84 | `tests/unit/test_version.py::test_macos_extra_is_optional_and_reported_when_missing` | unit | M2 |  |

### 2.2 Security (SEC, [PRD](../prd/components/PRD-security-v2.md) and [LLD](../lld/LLD-security-v1.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| SEC-1 | `tests/unit/platform/test_secrets.py::test_secret_text_forms_hide_value`, `tests/unit/platform/test_secrets.py::test_secret_has_no_dict_and_refuses_pickle` | unit | M0 | M0-05 |
| SEC-2 | `tests/unit/platform/test_secrets.py::test_keychain_read_argv_and_timeout`, `tests/unit/platform/test_secrets.py::test_keychain_read_exit_codes`, `tests/unit/platform/test_secrets.py::test_keychain_read_failures_are_error`, `tests/unit/platform/test_secrets.py::test_keychain_empty_output_is_error`, `tests/unit/platform/test_secrets.py::test_env_reference_reads_environment`, `tests/unit/platform/test_secrets.py::test_keychain_rejects_unsafe_account` | unit | M0 | M0-05 |
| SEC-13 | `tests/unit/platform/test_secrets.py::test_keychain_set_writes_through_stdin`, `tests/unit/platform/test_secrets.py::test_keychain_set_quotes_value`, `tests/unit/platform/test_secrets.py::test_keychain_set_rejects_unprintable_values`, `tests/unit/platform/test_secrets.py::test_keychain_set_failure_hides_stderr`, `tests/unit/platform/test_secrets.py::test_keychain_set_timeout_does_not_chain_stderr`, `tests/unit/platform/test_secrets.py::test_set_refuses_env_reference`, `tests/unit/platform/test_secrets.py::test_fake_provider_set_records_argv_without_value` | unit | M0 | M0-05 |
| SEC-3 | `tests/unit/platform/test_secrets.py::test_keychain_metadata_never_passes_w`, `tests/unit/platform/test_secrets.py::test_keychain_metadata_without_mdat_and_failures`, `tests/unit/platform/test_secrets.py::test_env_reference_has_no_metadata_in_both_providers`, `tests/unit/platform/test_secrets.py::test_fake_provider_metadata_matches_keychain` | unit | M0 | M0-05 |
| SEC-4 | `tests/unit/platform/test_secrets.py::test_secret_cache_reload_returns_changed_names` | unit | M0 | M0-05 |
| SEC-5 | planned | unit | M0 | M0-06 |
| SEC-6 | planned | unit | M0 | M0-06 |
| SEC-14 | planned | unit | M0 | M0-06 |
| SEC-7 | planned | unit | M0 | M0-06 |
| SEC-8 | planned | unit | M0 | M0-07 |
| SEC-9 | planned | unit | M0 | M0-07 |
| SEC-10 | planned | unit | M0 | M0-07 |
| SEC-11 | planned | integration | M0 | M0-15 |
| SEC-12 | planned | integration | M0 | M0-15 |
| SEC-20 | planned | contract | M2 |  |
| SEC-21 | planned | contract | M2 |  |
| SEC-22 | planned | contract | M2 |  |
| SEC-23 | planned | integration | M2 |  |
| SEC-24 | `tests/security/test_no_secret_at_rest.py::test_config_and_state_db_hold_no_secret` | integration | M0 |  |
| SEC-25 | `tests/security/test_path_arguments.py::test_tools_open_no_file_outside_cache_root` | contract | M2 |  |
| SEC-26 | `tests/unit/test_shim.py::test_shim_reads_daemon_token_only_from_keychain` | unit | M0 |  |
| SEC-27 | `tests/security/test_no_secret_at_rest.py::test_google_adc_refresh_writes_no_credential` | integration | M1 |  |

### 2.3 Sources (SRC, [PRD](../prd/components/PRD-sources-v5.md) and [LLD](../lld/LLD-sources-v1.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| SRC-1 | planned | unit | M0 | M0-09 |
| SRC-2 | planned | unit | M0 | M0-09 |
| SRC-3 | planned | unit | M0 | M0-09 |
| SRC-4 | planned | unit | M0 | M0-09 |
| SRC-5 | planned | unit | M0 | M0-09 |
| SRC-6 | planned | unit | M0 | M0-09 |
| SRC-7 | planned | unit | M0 | M0-09 |
| SRC-10 | planned | integration | M0 | M0-10 |
| SRC-11 | planned | integration | M0 | M0-11 |
| SRC-12 | planned | integration | M0 | M0-12 |
| SRC-8 | planned | contract | M0 | M0-14 |
| SRC-13 | planned | unit | M0 | M0-16 |
| SRC-20 | planned | integration | M1 |  |
| SRC-21 | planned | integration | M1 |  |
| SRC-22 | planned | integration | M1 |  |
| SRC-23 | planned | integration | M1 |  |
| SRC-24 | planned | unit | M1 |  |
| SRC-25 | planned | live | M1 |  |
| SRC-26 | planned | unit | M1 |  |
| SRC-27 | planned | unit | M1 |  |
| SRC-28 | planned | integration | M1 |  |
| SRC-29 | planned | integration | M1 |  |
| SRC-30 | planned | integration | M1 |  |
| SRC-31 | planned | unit | M1 |  |
| SRC-32 | planned | integration | M1 |  |
| SRC-33 | planned | integration | M1 |  |

### 2.4 Search (SRCH, [PRD](../prd/components/PRD-search-v3.md) and [LLD](../lld/LLD-search-v1.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| SRCH-10 | `tests/unit/core/test_ids.py::test_doi`, `tests/unit/core/test_ids.py::test_bad_doi`, `tests/unit/core/test_ids.py::test_unicode_whitespace_in_suffix` | unit | M0 | M0-02 |
| SRCH-11 | `tests/unit/core/test_ids.py::test_arxiv` | unit | M0 | M0-02 |
| SRCH-12 | `tests/unit/core/test_ids.py::test_canonical_forms`, `tests/unit/core/test_ids.py::test_invalid_scheme_forms` | unit | M0 | M0-02 |
| SRCH-13 | `tests/unit/core/test_ids.py::test_url`, `tests/unit/core/test_ids.py::test_invalid_url` | unit | M0 | M0-02 |
| SRCH-14 | `tests/unit/core/test_ids.py::test_detect`, `tests/unit/core/test_ids.py::test_reject_unknown`, `tests/unit/core/test_ids.py::test_identifier_frozen` | unit | M0 | M0-02 |
| SRCH-15 | `tests/unit/core/test_ids.py::test_normalizer_properties`, `tests/unit/core/test_ids.py::test_strict_utf8_decoding`, `tests/unit/core/test_ids.py::test_url_unencoded_whitespace` | unit | M0 | M0-02 |
| SRCH-16 | `tests/unit/core/test_ids.py::test_title` | unit | M0 | M0-02 |
| SRCH-1 | planned | integration | M0 | M0-13 |
| SRCH-2 | planned | integration | M0 | M0-13 |
| SRCH-3 | planned | integration | M0 | M0-13 |
| SRCH-4 | planned | integration | M0 | M0-13 |
| SRCH-5 | planned | integration | M0 | M0-13 |
| SRCH-6 | planned | integration | M0 | M0-13 |
| SRCH-7 | planned | integration | M0 | M0-13 |
| SRCH-8 | planned | integration | M0 | M0-13 |
| SRCH-9 | planned | integration | M0 | M0-13 |
| SRCH-17 | planned | integration | M0 | M0-13 |
| SRCH-20 | planned | contract | M0 | M0-14 |
| SRCH-21 | planned | contract | M0 | M0-14 |
| SRCH-22 | planned | contract | M0 | M0-14 |
| SRCH-23 | planned | contract | M0 | M0-14 |
| SRCH-30 | planned | integration | M1 |  |
| SRCH-31 | planned | integration | M1 |  |
| SRCH-32 | planned | integration | M1 |  |
| SRCH-33 | planned | integration | M1 |  |
| SRCH-34 | planned | integration | M1 |  |
| SRCH-36 | planned | integration | M2 |  |
| SRCH-37 | `tests/services/test_federation.py::test_auto_skips_rate_limited_sources_and_reports_status` | integration | M0 |  |
| SRCH-38 | `tests/unit/core/test_ids.py::test_url_trailing_slash` | unit | M0 |  |

### 2.5 Cache (CACHE, [PRD](../prd/components/PRD-cache-v4.md) and [LLD](../lld/LLD-cache-v1.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| CACHE-1 | planned | unit | M0 | M0-07 |
| CACHE-2 | planned | unit | M0 | M0-07 |
| CACHE-10 | planned | integration | M2 |  |
| CACHE-11 | planned | contract | M2 |  |
| CACHE-12 | planned | integration | M2 |  |
| CACHE-13 | planned | integration | M2 |  |
| CACHE-14 | planned | integration | M2 |  |
| CACHE-15 | planned | unit | M2 |  |
| CACHE-16 | planned | unit | M2 |  |
| CACHE-17 | planned | unit | M2 |  |
| CACHE-18 | planned | unit | M2 |  |
| CACHE-19 | planned | contract | M2 |  |
| CACHE-20 | planned | integration | M2 |  |
| CACHE-21 | planned | contract | M2 |  |
| CACHE-22 | planned | integration | M2 |  |
| CACHE-23 | planned | unit | M2 |  |
| CACHE-24 | planned | integration | M2 |  |
| CACHE-30 | planned | unit | M2 |  |
| CACHE-31 | planned | integration | M2 |  |
| CACHE-32 | planned | integration | M2 |  |
| CACHE-33 | planned | integration | M2 |  |
| CACHE-34 | planned | contract | M2 |  |
| CACHE-35 | planned | integration | M2 |  |
| CACHE-36 | planned | integration | M2 |  |
| CACHE-40 | planned | integration | M2 |  |
| CACHE-41 | planned | integration | M2 |  |
| CACHE-42 | planned | integration | M2 |  |
| CACHE-43 | planned | integration | M2 |  |
| CACHE-44 | planned | integration | M2 |  |
| CACHE-45 | planned | integration | M2 |  |
| CACHE-46 | planned | integration | M2 |  |
| CACHE-47 | planned | integration | M2 |  |
| CACHE-60 | planned | integration | M2 |  |
| CACHE-61 | planned | contract | M2 |  |
| CACHE-48 | planned | contract | M2 |  |
| CACHE-49 | planned | integration | M2 |  |
| CACHE-62 | `tests/services/test_archive.py::test_reindex_leaves_drive_files_unchanged` | integration | M2 |  |
| CACHE-63 | `tests/services/test_cite.py::test_cite_collection_exports_every_item` | integration | M2 |  |

### 2.6 Health (HLTH, [PRD](../prd/components/PRD-health-v4.md) and [LLD](../lld/LLD-health-v1.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| HLTH-40 | planned | unit | M0 | M0-16 |
| HLTH-1 | planned | integration | M1 |  |
| HLTH-2 | planned | integration | M1 |  |
| HLTH-3 | planned | integration | M1 |  |
| HLTH-4 | planned | integration | M1 |  |
| HLTH-10 | planned | unit | M1 |  |
| HLTH-12 | planned | unit | M1 |  |
| HLTH-13 | planned | unit | M1 |  |
| HLTH-11 | planned | integration | M1 |  |
| HLTH-20 | planned | unit | M1 |  |
| HLTH-21 | planned | integration | M1 |  |
| HLTH-22 | planned | unit | M1 |  |
| HLTH-23 | planned | unit | M1 |  |
| HLTH-24 | planned | unit | M1 |  |
| HLTH-25 | planned | integration | M1 |  |
| HLTH-30 | planned | integration | M1 |  |
| HLTH-31 | planned | integration | M1 |  |
| HLTH-32 | planned | unit | M1 |  |
| HLTH-33 | planned | unit | M1 |  |
| HLTH-34 | planned | unit | M1 |  |
| HLTH-35 | planned | unit | M1 |  |
| HLTH-41 | planned | integration | M2 |  |
| HLTH-42 | planned | contract | M1 |  |
| HLTH-43 | `tests/unit/services/test_credentials.py::test_credentials_store_metadata_only` | unit | M1 |  |
| HLTH-44 | `tests/services/test_health.py::test_probes_embeddings_local_target` | integration | M1 |  |

### 2.7 UI (UI, [PRD](../prd/components/PRD-ui-v4.md) and [LLD](../lld/LLD-ui-v1.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| UI-1 | planned | integration | M3 |  |
| UI-2 | planned | integration | M3 |  |
| UI-3 | planned | integration | M3 |  |
| UI-4 | planned | integration | M3 |  |
| UI-5 | planned | integration | M3 |  |
| UI-6 | planned | unit | M3 |  |
| UI-10 | planned | integration | M3 |  |
| UI-11 | planned | integration | M3 |  |
| UI-12 | planned | integration | M3 |  |
| UI-13 | planned | integration | M3 |  |
| UI-14 | planned | integration | M3 |  |
| UI-15 | planned | integration | M3 |  |
| UI-16 | planned | integration | M3 |  |
| UI-17 | planned | integration | M3 |  |
| UI-18 | planned | integration | M3 |  |
| UI-19 | planned | integration | M3 |  |
| UI-20 | `tests/ui/test_host_origin.py::test_foreign_host_or_origin_is_refused` | integration | M3 |  |
| UI-21 | `tests/ui/test_review.py::test_unanswered_item_stays_listed_with_times_asked` | integration | M3 |  |
| UI-22 | `tests/ui/test_banner.py::test_fallback_notification_shows_in_banner_until_resolved` | integration | M3 |  |
| UI-23 | `tests/ui/test_keychain_locked.py::test_credentials_and_settings_show_one_keychain_locked_state` | integration | M3 |  |
| UI-24 | `tests/ui/test_jobs.py::test_retry_resubmits_same_kind_and_parameters` | integration | M3 |  |
| UI-25 | `tests/ui/test_settings.py::test_lists_site_sets_read_only` | integration | M3 |  |

### 2.8 Migration (MIG, [PRD](../prd/components/PRD-migration-v5.md) and [LLD](../lld/LLD-migration-v1.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| MIG-1 | planned | integration | M4 |  |
| MIG-2 | planned | integration | M4 |  |
| MIG-3 | planned | unit | M4 |  |
| MIG-4 | planned | integration | M4 |  |
| MIG-5 | planned | integration | M4 |  |
| MIG-6 | planned | unit | M4 |  |
| MIG-10 | planned | integration | M4 |  |
| MIG-11 | planned | integration | M4 |  |
| MIG-12 | planned | integration | M4 |  |
| MIG-13 | planned | integration | M4 |  |
| MIG-14 | planned | integration | M4 |  |
| MIG-20 | planned | unit | M4 |  |
| MIG-21 | planned | unit | M4 |  |
| MIG-22 | `tests/migration/test_secrets_import.py::test_prints_no_credential_value` | integration | M4 |  |
| MIG-23 | `tests/migration/test_secrets_import.py::test_leaves_no_credential_value_at_rest` | integration | M4 |  |
| MIG-24 | `tests/migration/test_empty_cache.py::test_search_get_work_and_fetch_without_legacy_import` | integration | M4 |  |
| MIG-25 | `tests/unit/services/test_legacy_import.py::test_scrub_backup_is_owner_only` | unit | M4 |  |
| MIG-26 | `tests/migration/test_retirement.py::test_retire_deletes_scrub_backups` | integration | M4 |  |

## 3. Owner and live checks

> **Owner:** H · **Persona:** none (`test-architect` records)

Checks only the owner can run on the Mac or against real upstreams. They are not criteria and no test cites them.

| ID | Check | Verifies | Milestone |
| --- | --- | --- | --- |
| OC-01 | On the Mac: install, doctor green, a client searches three sources through the shim | PLAT-FR-1, PLAT-FR-54 | M0 |
| OC-02 | On the Mac: the daemon reads every Keychain item with no prompt; doctor shows each credential state | PLAT-FR-10 | M0 |
| OC-13 | On the Mac: install triggers the Google Drive privacy prompt in the foreground; doctor archive_access passes afterward | CACHE-FR-45 | M2 |
| OC-03 | On the Mac: a real macOS notification for a forced credential state opens the right UI page | HLTH-FR-32 | M1 |
| OC-04 | On the Mac: one real archive written to the Drive folder, visible in Drive on the web | CACHE-FR-45, CACHE-FR-47 | M2 |
| OC-05 | Owner walkthrough of every UI page | UI-FR-10, UI-FR-21 | M3 |
| OC-06 | Cutover steps 1 to 9 of the cutover runbook (docs/runbooks/migration-cutover-v1.md) completed | MIG-FR-20, MIG-FR-21, MIG-FR-25 | M4 |
| OC-07 | 14 days on v2 with no fallback; owner approves retiring v1 | MIG-FR-24 | M4 |
| OC-08 | CI on GitHub Actions (macOS and Linux, 3.12 and 3.13) with secret scan and weekly audit, once a remote exists | PLAT-FR-53 | M1 |
| OC-09 | Upgrade with a forced doctor failure rolls back | PLAT-FR-55 | M3 |
| OC-10 | Nightly state backup present for 3 days; optional Drive copy | PLAT-FR-57 | M2 |
| OC-11 | A new free source added by an agent in one work unit, touching only the allowed files | SRC-FR-26, OUT-3 | M1 |
| OC-12 | Five-source live search p95 under 8 s over 20 runs | OUT-2, SRCH-FR-3 | M1 |
| OC-14 | On the Mac: a web-group search with site_set v1_docs returns results through the Vertex engine with the owner's Google sign-in; doctor shows the sign-in ok | SRC-FR-19, SRC-FR-23, HLTH-FR-25 | M1 |

## 4. Deferrals and exceptions

> **Owner:** H decides; `test-architect` records

The owner approved two exceptions on 2026-10-22. Both are partial, so INV-6, NFR-3, INV-4 and SEC-INV-7 keep their tests and stay out of the `excepted:` front matter, which excepts whole criteria from coverage. MCP tools and agent-triggered actions stay bound by INV-4 and SEC-INV-7 (SEC-25, SEC-21, CACHE-11, CACHE-1).

| ID | Priority | Deferred or excepted | Reason | Approved by | Revisit |
| --- | --- | --- | --- | --- | --- |
| INV-6, NFR-3 | P1 | excepted for the scrub backups written by `scrub-client-configs` only | they hold plaintext v1 keys so rollback after scrubbing works (MIG-FR-25, MIG-FR-26) | Kenny Hill (Product), 2026-10-22 | at v1 retirement, when MIG-26 deletes them |
| INV-4, SEC-INV-7 | P1 | excepted for owner-run migration commands only, per command: `secrets import` (MIG-FR-1) and `scrub-client-configs` (MIG-FR-5) read only the MCP client configs; only the legacy import (MIG-FR-10) reads the v1 folder (`~/arxiv-papers`, the v1 database), read only (INV-10, MIG-INV-1) | the owner runs these commands to move v1 credentials and data into v2; MCP tools and agent-triggered actions stay bound by INV-4 and SEC-INV-7 | Kenny Hill (Product), 2026-10-22 | at v1 retirement |

## 5. Gaps and risks

> **Owner:** A · **Persona:** `test-architect`

1. The in-memory MCP client in `mcp<2` exposes structured content differently across minor versions; SRCH-20 pins the SDK version in the lock file and checks the field the pinned version uses.
2. PLAT-3 (no work at import) cannot rely on audit hooks for environment reads, so the subprocess replaces `os.environ` with a recording mapping and filters `open` events to non-module files.
3. OC-12 depends on upstream latency the project does not control; if it fails, the deadline or default source set is tuned rather than the gate removed.
4. Four new M0 criteria have no owning task in docs/build/M0-plan-v1.md, so their Unit is empty: SEC-24, SEC-26, SRCH-37 and SRCH-38. The M0 gate (1.4) counts only the criteria in that plan, so these would not gate M0 until the `planner` assigns them in the next M0 plan version; SRCH-38 fits M0-02, which is done, so it needs a new or reopened unit. Still open in v3; handed to the `planner`. SEC-24 now also sits in the 1.2 "No secret at rest" area, which every milestone keeps green once its test exists.
5. SEC-24 is the one criterion for no registered secret at rest after install, start and reload; the duplicate platform criterion was removed because the Security component owns the shared invariants (owner decision, 2026-10-22). Resolved in v3: 1.2 has a "No secret at rest" area listing SEC-24, SEC-27, HLTH-43 and MIG-23 (owner decision, 2026-10-22).
6. No criterion yet tests that the owner-run migration commands stay within the section 4 INV-4 and SEC-INV-7 exception (for example, that `secrets import` and `scrub-client-configs` read only the MCP client configs and never the v1 folder, and that the legacy import reads the v1 folder without modifying it; MIG-10 covers only the last part); open question for the owner: is a new MIG criterion wanted?


## 6. Evidence

> **Owner:** A · **Persona:** `test-architect` (generated)

Evidence is derived status and lives in [docs/trace/coverage.md](../trace/coverage.md), regenerated by `node tools/trace-check/trace-check.mjs --write`. Do not copy it here.
