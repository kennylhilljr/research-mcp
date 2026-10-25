---
title: "Research MCP v2 test plan"
type: test-plan
version: 5
status: draft
supersedes: docs/test/test-plan-v4.md
owner: "Kenny Hill"
artifact_type: test-strategy
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/test-plan/TEST-PLAN-v3.md
deferred: []
excepted: []
date: 2026-10-22
---

# Test plan (v5)

The approved test strategy for Research MCP v2: how every acceptance criterion in the component PRDs is verified. It carries over [TEST-PLAN v3](../../docs-archive/test-plan/TEST-PLAN-v3.md) with SDD IDs (acceptance test `AT-PLAT-31` is now criterion `PLAT-31`; requirement `FR-PLAT-30` is now `PLAT-FR-30`). The criteria themselves live in each component PRD, section 2.4. Version 2 added the criteria from the owner's Gate 1 answers of 2026-10-22 ([PRD v7](../prd/PRD-v7.md) and its component PRDs). Version 3 recorded the owner's decisions of 2026-10-22: OC-14 joins the M1 exit gate (1.4), a "No secret at rest" area joins 1.2, and a second exception covers owner-run migration commands (section 4). Version 4 supersedes [test plan v3](test-plan-v3.md) and adds rows for the criteria of [PRD-security v3](../prd/components/PRD-security-v3.md) (SEC-28 to SEC-32) and [PRD-migration v6](../prd/components/PRD-migration-v6.md) (MIG-27 to MIG-35), and aligns the planned test names with the v2 LLDs (platform, security, sources, search, cache, health, UI, migration); it does not change the owner decisions above. Version 5 points the M0 gate (1.4) at [M0 plan v4](../build/M0-plan-v4.md), which assigns every M0 criterion to a task. Tests cite their criterion first in the docstring (`"""@spec PLAT-31: ..."""`), and `docs/trace/coverage.md` is derived from those citations.

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
| No secret in any output | Logs, errors, tool results, UI pages, notifications and process argument lists never contain a registered secret | SEC-1, SEC-5, SEC-6, SEC-7, SEC-9, SEC-10, SEC-13, SEC-14, SEC-28, HLTH-32, HLTH-34, UI-4, MIG-22 |
| No secret at rest | No registered secret is stored in configuration, Application Support or log files, and credentials are kept as metadata only (owner decision, 2026-10-22) | SEC-24, SEC-27, HLTH-43, MIG-23 |
| Loopback and auth | Nothing binds beyond loopback; every request is authenticated | PLAT-10, PLAT-71, SEC-11, SEC-12, SEC-26, SEC-29, SEC-32, UI-2, UI-3, UI-20 |
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
| M0 | Every M0 criterion in docs/build/M0-plan-v4.md has a passing test that cites it; full `tools/ci.sh` green (including `node tools/sdd/cli.mjs check`) (lint, strict mypy, coverage 85% on `src/`, build, `--help`); owner checks OC-01 and OC-02. |
| M1 | All M1 tests pass; 45 or more sources registered and passing conformance (PRD-v7 OUT-1); OC-03, OC-08 (once a remote exists), OC-11, OC-12, OC-14 (owner decision, 2026-10-22). |
| M2 | All M2 tests pass, including the hostile PDF corpus; OC-04, OC-10 and OC-13. |
| M3 | All M3 tests pass; OC-05 and OC-09. |
| M4 | All M4 tests pass; OC-06 then OC-07. |

## 2. Planned evidence

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves

Every criterion, in the order of the earlier catalog. The work unit is the M0 task that owns the criterion (later milestones assign units when their plan is written).


### 2.1 Platform (PLAT, [PRD](../prd/components/PRD-platform-v4.md) and [LLD](../lld/LLD-platform-v2.md))

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
| PLAT-40 | `tests/unit/platform/test_logging.py::test_rotating_file_is_5_files_of_10mb`, `tests/unit/platform/test_logging.py::test_stderr_warnings_only`, `tests/unit/platform/test_logging.py::test_rotate_stderr_log` | unit | M0 | M0-06 |
| PLAT-41 | `tests/unit/platform/test_logging.py::test_records_carry_fields_and_correlation_id` | unit | M0 | M0-06 |
| PLAT-42 | `tests/unit/platform/test_logging.py::test_query_text_is_hash_and_length`, `tests/unit/platform/test_logging.py::test_debug_logs_query_text_through_redactor`, `tests/unit/platform/test_logging.py::test_query_hash_is_nfc_casefold_stable` | unit | M0 | M0-06 |
| PLAT-35 | `tests/unit/platform/test_http.py::test_retry_after_and_rate_limited` | unit | M0 | M0-07 |
| PLAT-36 | `tests/unit/platform/test_http.py::test_retries_5xx_and_policy_block` | unit | M0 | M0-07 |
| PLAT-37 | `tests/unit/platform/test_ratelimit.py::test_shared_bucket_spaces_arxiv_calls` | unit | M0 | M0-07 |
| PLAT-38 | `tests/unit/platform/test_http.py::test_byte_cap_aborts_before_full_body` | unit | M0 | M0-07 |
| PLAT-39 | `tests/unit/platform/test_http.py::test_user_agent_and_call_record_per_attempt` | unit | M0 | M0-07 |
| PLAT-50 | `tests/unit/platform/test_stores.py::test_migrator_transaction_and_user_version` | unit | M0 | M0-08 |
| PLAT-51 | `tests/unit/platform/test_stores.py::test_newer_database_is_refused` | unit | M0 | M0-08 |
| PLAT-52 | `tests/unit/platform/test_stores.py::test_pragmas_and_serialized_writes` | unit | M0 | M0-08 |
| PLAT-53 | `tests/unit/platform/test_stores.py::test_schemas_match_spec` | unit | M0 | M0-08 |
| PLAT-60 | `tests/contract/test_tool_contract.py::test_every_tool_declares_annotations` | contract | M0 | M0-14 |
| PLAT-61 | `tests/contract/test_tool_contract.py::test_instructions_state_untrusted_and_owner_decision_rules` | contract | M0 | M0-14 |
| PLAT-62 | `tests/contract/test_tool_contract.py::test_internal_error_has_no_exception_text` | contract | M0 | M0-14 |
| PLAT-63 | `tests/contract/test_tool_contract.py::test_result_never_exceeds_response_bytes` | contract | M0 | M0-14 |
| PLAT-70 | `tests/integration/test_app.py::test_lifespan_opens_and_closes_everything`, `tests/integration/test_app.py::test_healthz_and_readyz` | integration | M0 | M0-15 |
| PLAT-71 | `tests/integration/test_app.py::test_daemon_refuses_non_loopback_bind` | integration | M0 | M0-15 |
| PLAT-72 | `tests/integration/test_shim.py::test_full_mcp_session_through_shim` | integration | M0 | M0-15 |
| PLAT-73 | `tests/integration/test_shim.py::test_down_daemon_starts_via_launchctl_then_one_error` | integration | M0 | M0-15 |
| PLAT-74 | `tests/integration/test_jobs.py::test_submit_status_progress_cancel_persist` | integration | M0 | M0-15 |
| PLAT-75 | `tests/integration/test_app.py::test_event_loop_heartbeat_under_slow_source` | integration | M0 | M0-15 |
| PLAT-76 | `tests/integration/test_scheduler.py::test_missed_daily_job_runs_once` | integration | M0 | M0-15 |
| PLAT-77 | `tests/integration/test_shim.py::test_stateless_restart_and_initialize_replay` | integration | M0 | M0-15 |
| PLAT-80 | `tests/unit/test_cli.py::test_help_lists_platform_commands` | unit | M0 | M0-16 |
| PLAT-81 | `tests/unit/test_install.py::test_plists_parse_and_hold_nothing_secret` | unit | M0 | M0-16 |
| PLAT-82 | `tests/unit/test_install.py::test_client_config_launches_stdio_without_secret_or_url` | unit | M0 | M0-16 |
| PLAT-83 | `tests/unit/test_install.py::test_install_generates_token_if_absent`, `tests/unit/test_install.py::test_rotate_token_replaces_and_old_token_fails` | unit | M0 | M0-16 |
| PLAT-13 | `tests/unit/test_version.py::test_gcp_extra_is_optional_and_vertex_unconfigured_when_missing` | unit | M1 |  |
| PLAT-84 | `tests/unit/test_version.py::test_macos_extra_is_optional_and_reported_when_missing` | unit | M2 |  |

### 2.2 Security (SEC, [PRD](../prd/components/PRD-security-v3.md) and [LLD](../lld/LLD-security-v2.md))

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
| SEC-28 | `tests/security/test_no_secret_in_tool_results.py::test_successful_tool_results_hold_no_registered_secret` (name from LLD-security v2 9) | contract | M2 |  |
| SEC-29 | `tests/ui/test_login.py::test_next_accepts_only_ui_paths` (LLD-ui v2 9) | integration | M3 |  |
| SEC-30 | `tests/unit/test_install.py::test_daemon_token_is_43_char_urlsafe_base64` (name in LLD-security v2) | unit | M0 |  |
| SEC-31 | `tests/unit/test_settings.py::test_webhook_scheme_https_or_loopback_http_only` (name in LLD-security v2 section 9) | unit | M3 |  |
| SEC-32 | `tests/ui/test_static.py::test_static_needs_a_session` (LLD-ui v2 9) | integration | M3 |  |

### 2.3 Sources (SRC, [PRD](../prd/components/PRD-sources-v5.md) and [LLD](../lld/LLD-sources-v2.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| SRC-1 | `tests/unit/sources/test_registry.py::test_spec_rejects_missing_field_out_of_bounds_rate_and_auth_without_origins` (one parametrized case per bound in the 2.1 table; file `[inferred]`; M0-09) | unit | M0 | M0-09 |
| SRC-2 | `tests/unit/sources/test_registry.py::test_discovers_builtin_and_builds_two_instances_from_settings` (M0-09) | unit | M0 | M0-09 |
| SRC-3 | `tests/unit/sources/test_registry.py::test_disabled_source_is_skipped_and_records_no_request` (M0-09) | unit | M0 | M0-09 |
| SRC-4 | `tests/unit/sources/test_registry.py::test_missing_credential_or_contact_is_unconfigured_with_exact_fix` (M0-09) | unit | M0 | M0-09 |
| SRC-5 | `tests/unit/sources/test_registry.py::test_missing_extra_is_unconfigured_with_install_command` (M0-09) | unit | M0 | M0-09 |
| SRC-6 | `tests/sources/test_conformance.py::test_conformance_passes_for_fake_adapter` over the fake adapter from `research_mcp.testing.adapters` (M0-09) | unit | M0 | M0-09 |
| SRC-7 | `tests/unit/sources/test_adapter_imports.py::test_forbidden_import_or_call_in_adapter_module_fails` (positive case on a temp module per forbidden import and call; M0-09) | unit | M0 | M0-09 |
| SRC-10 | `tests/sources/arxiv/test_arxiv.py::test_arxiv_https_version_mapping_rate_and_concurrency` and `tests/sources/test_conformance.py::test_conformance_passes[arxiv]` (M0-10) | integration | M0 | M0-10 |
| SRC-11 | `tests/sources/crossref/test_crossref.py::test_crossref_mailto_doi_date_mapping_and_updates_capability` and `tests/sources/test_conformance.py::test_conformance_passes[crossref]` (M0-11) | integration | M0 | M0-11 |
| SRC-12 | `tests/sources/openalex/test_openalex.py::test_openalex_key_placement_page_size_and_budget_429_classified` and `tests/sources/test_conformance.py::test_conformance_passes[openalex]` (M0-12) | integration | M0 | M0-12 |
| SRC-8 | `tests/contract/test_tools_discovery.py::test_list_sources_and_resource_list_every_source_with_state_and_fix` (M0-14; file `[inferred]`) | contract | M0 | M0-14 |
| SRC-13 | `tests/unit/test_cli.py::test_gen_inventory_check_fails_on_stale_inventory` (M0-16; file `[inferred]`) | unit | M0 | M0-16 |
| SRC-20 | `tests/sources/test_conformance.py::test_conformance_passes[<id>]` (one case per adapter, with `tests/sources/<id>/fixtures/`) and `tests/unit/sources/test_catalog.py::test_45_catalog_ids_registered_each_with_seven_fixtures` (M1) | integration | M1 |  |
| SRC-21 | `tests/sources/dspace/test_dspace.py::test_four_instances_record_api_version_and_dspace_version` (M1) | integration | M1 |  |
| SRC-22 | `tests/sources/aws_knowledge/test_aws_knowledge.py::test_calls_go_through_upstream_port_with_policy_and_telemetry` and `tests/sources/ms_learn/test_ms_learn.py::test_calls_go_through_upstream_port_with_policy_and_telemetry` against the MCP server fake (M1) | integration | M1 |  |
| SRC-23 | `tests/sources/docs_site/test_docs_site.py::test_allowlist_substring_traversal_and_robots_disallow_refused` (M1) | integration | M1 |  |
| SRC-24 | `tests/unit/sources/test_registry.py::test_deprecated_days_counts_down_to_shutdown_on` (`FakeClock`; M1) | unit | M1 |  |
| SRC-25 | `tests/live/test_sources_live.py::test_live_check_writes_only_under_review` (opt-in `live` mark) and non-live `tests/unit/sources/test_live_check.py::test_path_outside_review_is_refused` (M1) | live | M1 |  |
| SRC-26 | `tests/unit/sources/test_v1_map.py::test_v1_endpoint_map_with_aws_and_learn_substitution` and `tests/unit/sources/test_v1_map.py::test_defaults_hold_26_domains_and_six_docs_site_instances` (M1) | unit | M1 |  |
| SRC-27 | `tests/unit/test_settings.py::test_site_sets_override_by_name_empty_list_removes_and_invalid_name_fails` (M1; file `[inferred]`) | unit | M1 |  |
| SRC-28 | `tests/services/test_web_group.py::test_web_sources_disabled_until_enabled_and_configured`, `tests/services/test_web_group.py::test_web_removed_from_auto_even_when_in_default_groups` and `tests/services/test_web_group.py::test_web_selected_by_group_name_or_source_id` (M1) | integration | M1 |  |
| SRC-29 | `tests/services/test_web_group.py::test_daily_cap_gives_budget_exhausted_until_local_midnight_and_federation_skips` (`FakeClock`; M1) | integration | M1 |  |
| SRC-30 | `tests/services/test_federation_web.py::test_fallback_chain_one_paid_query_per_page`, `tests/services/test_federation_web.py::test_all_strategy_fans_out_to_every_web_source` and `tests/services/test_federation_web.py::test_non_web_sources_run_in_parallel_inside_deadline` (M1; file `[inferred]`) | integration | M1 |  |
| SRC-31 | `tests/unit/sources/test_sitequery.py::test_brave_batches_at_most_3_of_380_chars_query_domains_first`, `tests/unit/sources/test_sitequery.py::test_serpapi_and_pse_single_query_with_truncated`, `tests/unit/sources/test_sitequery.py::test_vertex_filters_results_by_host` and `tests/unit/sources/test_sitequery.py::test_unknown_site_set_is_invalid_argument_with_no_call` (M1) | unit | M1 |  |
| SRC-32 | `tests/sources/vertex_search/test_vertex_search.py::test_refresh_off_loop_token_only_to_discoveryengine_with_project_header_and_call_record` and `tests/unit/sources/test_vertex_static.py::test_no_src_module_opens_the_credential_file` (M1) | integration | M1 |  |
| SRC-33 | `tests/sources/brave_search/test_brave_search.py::test_brave_headers`, `tests/sources/google_pse/test_google_pse.py::test_pse_reports_deprecated_days`, `tests/sources/serpapi/test_serpapi.py::test_serpapi_key_never_in_logs_errors_call_records_or_tool_results` (M1) | integration | M1 |  |

### 2.4 Search (SRCH, [PRD](../prd/components/PRD-search-v3.md) and [LLD](../lld/LLD-search-v2.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| SRCH-10 | `tests/unit/core/test_ids.py::test_doi`, `tests/unit/core/test_ids.py::test_bad_doi`, `tests/unit/core/test_ids.py::test_unicode_whitespace_in_suffix` | unit | M0 | M0-02 |
| SRCH-11 | `tests/unit/core/test_ids.py::test_arxiv` | unit | M0 | M0-02 |
| SRCH-12 | `tests/unit/core/test_ids.py::test_canonical_forms`, `tests/unit/core/test_ids.py::test_invalid_scheme_forms` | unit | M0 | M0-02 |
| SRCH-13 | `tests/unit/core/test_ids.py::test_url`, `tests/unit/core/test_ids.py::test_invalid_url` | unit | M0 | M0-02 |
| SRCH-14 | `tests/unit/core/test_ids.py::test_detect`, `tests/unit/core/test_ids.py::test_reject_unknown`, `tests/unit/core/test_ids.py::test_identifier_frozen` | unit | M0 | M0-02 |
| SRCH-15 | `tests/unit/core/test_ids.py::test_normalizer_properties`, `tests/unit/core/test_ids.py::test_strict_utf8_decoding`, `tests/unit/core/test_ids.py::test_url_unencoded_whitespace` | unit | M0 | M0-02 |
| SRCH-16 | `tests/unit/core/test_ids.py::test_title` | unit | M0 | M0-02 |
| SRCH-1 | `tests/services/test_federation.py::test_sources_run_concurrently` | integration | M0 | M0-13 |
| SRCH-2 | `tests/services/test_federation.py::test_slow_source_times_out` | integration | M0 | M0-13 |
| SRCH-3 | `tests/services/test_federation.py::test_failing_source_gets_status` | integration | M0 | M0-13 |
| SRCH-4 | `tests/services/test_works.py::test_shared_identifier_merges` | integration | M0 | M0-13 |
| SRCH-5 | `tests/services/test_works.py::test_fuzzy_merge_flagged` | integration | M0 | M0-13 |
| SRCH-6 | `tests/services/test_federation.py::test_rrf_golden_order` | integration | M0 | M0-13 |
| SRCH-7 | `tests/services/test_federation.py::test_combined_cursor_continues_and_reports_empty` | integration | M0 | M0-13 |
| SRCH-8 | `tests/services/test_federation.py::test_auto_skips_unconfigured_disabled_down` | integration | M0 | M0-13 |
| SRCH-9 | `tests/services/test_works.py::test_conflicts_recorded_with_sources` | integration | M0 | M0-13 |
| SRCH-17 | `tests/services/test_works.py::test_get_work_merges_and_lists_oa` | integration | M0 | M0-13 |
| SRCH-20 | `tests/contract/test_tool_contract.py::test_search_structured_content` | contract | M0 | M0-14 |
| SRCH-21 | `tests/contract/test_tool_contract.py::test_bad_arguments_rejected_before_source_call` | contract | M0 | M0-14 |
| SRCH-22 | `tests/contract/test_tools_discovery.py::test_compact_and_full_fit_budget` | contract | M0 | M0-14 |
| SRCH-23 | `tests/contract/test_tools_discovery.py::test_get_work_id_forms` | contract | M0 | M0-14 |
| SRCH-30 | `tests/services/test_citations.py::test_merge_dedupe_titles_paging` | integration | M1 |  |
| SRCH-31 | `tests/services/test_works.py::test_authors_merge` | integration | M1 |  |
| SRCH-32 | `tests/services/test_cite.py::test_formats_snapshot_and_unknown_rejected`, `tests/services/test_cite.py::test_text_style_csl_processor`, `tests/services/test_cite.py::test_doi_negotiation_uses_doi_resolver` | integration | M1 |  |
| SRCH-33 | `tests/services/test_integrity.py::test_retractions_golden_fixtures` | integration | M1 |  |
| SRCH-34 | `tests/services/test_federation.py::test_search_record_hash_not_text`, `tests/services/test_federation.py::test_search_record_filters_json` | integration | M1 |  |
| SRCH-36 | `tests/services/test_works.py::test_get_work_cache_state_and_integrity` | integration | M2 |  |
| SRCH-37 | `tests/services/test_federation.py::test_auto_skips_rate_limited_sources_and_reports_status` | integration | M0 |  |
| SRCH-38 | `tests/unit/core/test_ids.py::test_url_trailing_slash` | unit | M0 |  |

### 2.5 Cache (CACHE, [PRD](../prd/components/PRD-cache-v4.md) and [LLD](../lld/LLD-cache-v2.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| CACHE-1 | `tests/unit/platform/test_downloader.py::test_rejects_http_private_loopback_linklocal_also_after_redirect`, `tests/unit/platform/test_downloader.py::test_dns_rebinding_uses_checked_ip`, `tests/unit/platform/test_downloader.py::test_rejects_media_type_magic_bytes_and_oversize` | unit | M0 | M0-07 |
| CACHE-2 | `tests/unit/platform/test_downloader.py::test_atomic_write_by_sha256_and_full_provenance`, `tests/unit/platform/test_downloader.py::test_existing_file_reused` | unit | M0 | M0-07 |
| CACHE-10 | `tests/services/test_cache_fetch.py::test_fetch_picks_best_oa_location_by_preference`, `tests/services/test_cache_fetch.py::test_pdf_without_extra_is_unconfigured_before_download` | integration | M2 |  |
| CACHE-11 | `tests/contract/test_tools_cache.py::test_no_cache_tool_accepts_a_local_path` | contract | M2 |  |
| CACHE-12 | `tests/services/test_cache_fetch.py::test_cached_work_returns_existing_and_discarded_work_refetches_from_recipe` | integration | M2 |  |
| CACHE-13 | `tests/services/test_cache_jobs.py::test_multi_fetch_and_crawl_run_as_jobs_with_progress_and_cancel`, `tests/services/test_cache_jobs.py::test_fetch_list_returns_job_handle_and_bad_item_rejects_all` | integration | M2 |  |
| CACHE-14 | `tests/services/test_extract_worker.py::test_crashing_or_hanging_parser_marks_extract_failed_and_daemon_serves` | integration | M2 |  |
| CACHE-15 | `tests/unit/services/test_chunking.py::test_golden_target_overlap_boundaries_no_split_words_offsets_pages` | unit | M2 |  |
| CACHE-16 | `tests/unit/services/test_extract_html.py::test_headings_kept_and_36kb_single_line_page_is_bounded` | unit | M2 |  |
| CACHE-17 | `tests/unit/services/test_extract_pdf.py::test_image_only_pdf_flags_needs_ocr` | unit | M2 |  |
| CACHE-18 | `tests/unit/services/test_extract_pdf.py::test_extraction_records_parser_and_versions` | unit | M2 |  |
| CACHE-19 | `tests/contract/test_tools_cache.py::test_read_windows_by_page_section_chunk_with_cursor_and_bounds` | contract | M2 |  |
| CACHE-20 | `tests/services/test_cache_search.py::test_keyword_semantic_hybrid_literal_fallback_and_coverage` | integration | M2 |  |
| CACHE-21 | `tests/contract/test_tools_cache.py::test_library_list_and_stats_report_state_size_age_expiry` | contract | M2 |  |
| CACHE-22 | `tests/services/test_embeddings.py::test_every_chunk_embedded_keyed_by_hash_and_model_removed_with_chunks` | integration | M2 |  |
| CACHE-23 | `tests/unit/services/test_embeddings.py::test_query_encoding_for_queries_passage_encoding_for_chunks` | unit | M2 |  |
| CACHE-24 | `tests/services/test_cache_search.py::test_without_embeddings_extra_runs_keyword_only_and_says_so` | integration | M2 |  |
| CACHE-30 | `tests/unit/services/test_lifecycle_transitions.py::test_lifecycle_transition_row`, `tests/integration/test_outbox.py::test_drain_is_idempotent` | unit | M2 |  |
| CACHE-31 | `tests/services/test_review.py::test_daily_review_builds_one_batch_one_notification_one_webhook` | integration | M2 |  |
| CACHE-32 | `tests/services/test_review.py::test_per_item_and_bulk_decisions_apply_archive_discard_keep_pin` | integration | M2 |  |
| CACHE-33 | `tests/services/test_review.py::test_ninety_simulated_days_without_answers_delete_nothing` | integration | M2 |  |
| CACHE-34 | `tests/contract/test_tools_cache.py::test_review_decide_rejects_closed_foreign_and_records_agent_mcp_and_notifies_discards` | contract | M2 |  |
| CACHE-35 | `tests/services/test_review.py::test_review_items_show_citation_size_age_asks_access_and_integrity_change` | integration | M2 |  |
| CACHE-36 | `tests/services/test_trash.py::test_discard_keeps_metadata_undo_restores_notice_before_purge_shared_file_survives` | integration | M2 |  |
| CACHE-40 | `tests/services/test_archive.py::test_auto_detects_drive_folder_and_writes_file_and_sidecar_fields` | integration | M2 |  |
| CACHE-41 | `tests/services/test_archive.py::test_readback_verifies_before_cached_copy_removed_and_mismatch_keeps_it` | integration | M2 |  |
| CACHE-42 | `tests/services/test_archive.py::test_unavailable_target_uses_fallback_warns_and_reconcile_moves` | integration | M2 |  |
| CACHE-43 | `tests/services/test_archive.py::test_archived_document_stays_searchable_readable_and_citable` | integration | M2 |  |
| CACHE-44 | `tests/services/test_archive.py::test_target_health_fields_upload_state_moves_to_uploaded_and_24h_stall_notifies` | integration | M2 |  |
| CACHE-45 | `tests/services/test_collections.py::test_create_add_remove_list_show_and_pinning_collections` | integration | M2 |  |
| CACHE-46 | `tests/services/test_disk.py::test_samples_thresholds_and_notices` | integration | M2 |  |
| CACHE-47 | `tests/services/test_maintenance.py::test_detects_corrupt_fts_missing_orphans_and_fixes_only_as_confirmed_jobs` | integration | M2 |  |
| CACHE-60 | `tests/services/test_archive.py::test_reindex_rebuilds_works_documents_reextracts_verifies_and_reports` | integration | M2 |  |
| CACHE-61 | `tests/contract/test_tools_cache.py::test_search_cache_marks_state_filters_states_and_points_archived_hit_to_drive_path` | contract | M2 |  |
| CACHE-48 | `tests/contract/test_tools_cache.py::test_library_offers_no_discard_action` | contract | M2 |  |
| CACHE-49 | `tests/services/test_backup.py::test_nightly_online_backup_of_state_cache_and_config_keeps_seven` | integration | M2 |  |
| CACHE-62 | `tests/services/test_archive.py::test_reindex_leaves_drive_files_unchanged` | integration | M2 |  |
| CACHE-63 | `tests/services/test_cite.py::test_cite_collection_exports_every_item` | integration | M2 |  |

### 2.6 Health (HLTH, [PRD](../prd/components/PRD-health-v4.md) and [LLD](../lld/LLD-health-v2.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| HLTH-40 | `tests/unit/test_cli.py::test_doctor_skeleton_runs_four_checks`, `tests/unit/test_cli.py::test_liveness_runs_two_checks`, `tests/unit/test_cli.py::test_json_output`, `tests/unit/test_cli.py::test_exit_code_reflects_install_critical`, `tests/unit/test_cli.py::test_only_installation_integrity_is_install_critical`, `tests/unit/test_cli.py::test_install_critical_fails_upgrade_check` | unit | M0 | M0-16 |
| HLTH-1 | `tests/services/test_health.py::test_calls_rollups_and_pruning` | integration | M1 |  |
| HLTH-2 | `tests/services/test_health.py::test_probe_cadence_jitter_and_passive_skip` | integration | M1 |  |
| HLTH-3 | `tests/services/test_health.py::test_probe_shape_change_marks_down` | integration | M1 |  |
| HLTH-4 | `tests/services/test_health.py::test_probes_local_targets` | integration | M1 |  |
| HLTH-10 | `tests/unit/services/test_health_eval.py::test_each_rule_produces_its_state`, `tests/unit/services/test_health_eval.py::test_worst_state_wins` | unit | M1 |  |
| HLTH-12 | `tests/unit/services/test_health_eval.py::test_rate_limited_and_budget_clear_at_their_time` | unit | M1 |  |
| HLTH-13 | `tests/unit/services/test_credentials.py::test_locked_keychain_gives_one_notification` | unit | M1 |  |
| HLTH-11 | `tests/services/test_health.py::test_source_detail_has_every_field` | integration | M1 |  |
| HLTH-20 | `tests/unit/services/test_credentials.py::test_credential_states_from_fixtures` | unit | M1 |  |
| HLTH-21 | `tests/services/test_credentials.py::test_github_expiry_header_and_rate_limit_update` | integration | M1 |  |
| HLTH-22 | `tests/unit/services/test_credentials.py::test_rotate_by_default_and_override` | unit | M1 |  |
| HLTH-23 | `tests/unit/services/test_credentials.py::test_fix_text_names_item_page_and_value_free_command` | unit | M1 |  |
| HLTH-24 | `tests/unit/services/test_credentials.py::test_google_signin_states_and_metadata_only`, `tests/unit/services/test_credentials.py::test_google_signin_account_stored_in_credentials_account` | unit | M1 |  |
| HLTH-25 | `tests/services/test_credentials.py::test_metered_validation_uses_free_methods` | integration | M1 |  |
| HLTH-30 | `tests/services/test_notify.py::test_state_change_and_expiry_milestones_fire_once` | integration | M1 |  |
| HLTH-31 | `tests/services/test_notify.py::test_unresolved_items_roll_into_one_digest` | integration | M1 |  |
| HLTH-32 | `tests/unit/services/test_notify.py::test_macos_argv_has_no_token`, `tests/unit/services/test_notify.py::test_osascript_fallback`, `tests/unit/services/test_notify.py::test_webhook_payload_and_header` | unit | M1 |  |
| HLTH-33 | `tests/unit/services/test_notify.py::test_quiet_hours_hold_all_but_install_critical_urgent_and_recent_invalid`, `tests/unit/services/test_notify.py::test_expiry_critical_row_is_held_in_quiet_hours_and_in_digest` | unit | M1 |  |
| HLTH-34 | `tests/unit/services/test_notify.py::test_text_has_no_secret_or_url_query` | unit | M1 |  |
| HLTH-35 | `tests/unit/services/test_notify.py::test_ack_and_snooze_persist` | unit | M1 |  |
| HLTH-41 | `tests/integration/test_doctor.py::test_every_check_runs_with_simulated_tcc_denial`, `tests/integration/test_doctor.py::test_notify_only_when_result_changes`, `tests/integration/test_doctor.py::test_daemon_down_install_critical_bypasses_quiet_hours` | integration | M2 |  |
| HLTH-42 | `tests/contract/test_status_contract.py::test_ops_status_resource_and_api_status_hold_no_secret` | contract | M1 |  |
| HLTH-43 | `tests/unit/services/test_credentials.py::test_credentials_store_metadata_only` | unit | M1 |  |
| HLTH-44 | `tests/services/test_health.py::test_probes_embeddings_local_target` | integration | M1 |  |

### 2.7 UI (UI, [PRD](../prd/components/PRD-ui-v4.md) and [LLD](../lld/LLD-ui-v2.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| UI-1 | `tests/ui/test_serving.py::test_ui_is_loopback_only_and_pages_load_no_external_assets` | integration | M3 |  |
| UI-2 | `tests/ui/test_login.py::test_one_time_token_expires_is_single_use_and_sets_strict_httponly_cookie` | integration | M3 |  |
| UI-3 | `tests/ui/test_csrf.py::test_post_without_valid_csrf_is_refused_and_maintenance_needs_confirmation` | integration | M3 |  |
| UI-4 | `tests/ui/test_no_secrets.py::test_no_page_contains_a_registered_secret` | integration | M3 |  |
| UI-5 | `tests/ui/test_refresh.py::test_fragments_poll_every_10s_and_nothing_else` | integration | M3 |  |
| UI-6 | `tests/ui/test_strings.py::test_templates_and_strings_have_no_em_or_en_dashes` | unit | M3 |  |
| UI-10 | `tests/ui/test_board.py::test_board_counts_groups_chips_and_probe_and_enable_actions` | integration | M3 |  |
| UI-11 | `tests/ui/test_credentials.py::test_credentials_show_metadata_and_value_free_command_and_no_value_field` | integration | M3 |  |
| UI-12 | `tests/ui/test_quota.py::test_quota_shows_allowance_used_remaining_reset_and_projection` | integration | M3 |  |
| UI-13 | `tests/ui/test_jobs.py::test_jobs_list_and_cancel_needs_confirmation` | integration | M3 |  |
| UI-14 | `tests/ui/test_cache.py::test_cache_lists_items_with_totals_and_search_finds_cached` | integration | M3 |  |
| UI-15 | `tests/ui/test_review.py::test_per_item_and_bulk_decisions_with_summary_confirmation` | integration | M3 |  |
| UI-16 | `tests/ui/test_archive.py::test_archive_shows_target_catalog_discards_and_undo` | integration | M3 |  |
| UI-17 | `tests/ui/test_maintenance.py::test_each_action_requires_confirmation_and_starts_its_job` | integration | M3 |  |
| UI-18 | `tests/ui/test_events.py::test_events_list_notifications_and_redacted_logs_searchable_by_correlation_id` | integration | M3 |  |
| UI-19 | `tests/ui/test_settings.py::test_settings_show_effective_config_names_only_and_test_notification_works` | integration | M3 |  |
| UI-20 | `tests/ui/test_host_origin.py::test_foreign_host_or_origin_is_refused` | integration | M3 |  |
| UI-21 | `tests/ui/test_review.py::test_unanswered_item_stays_listed_with_times_asked` | integration | M3 |  |
| UI-22 | `tests/ui/test_banner.py::test_fallback_notification_shows_in_banner_until_resolved` | integration | M3 |  |
| UI-23 | `tests/ui/test_keychain_locked.py::test_credentials_and_settings_show_one_keychain_locked_state` | integration | M3 |  |
| UI-24 | `tests/ui/test_jobs.py::test_retry_resubmits_same_kind_and_parameters` | integration | M3 |  |
| UI-25 | `tests/ui/test_settings.py::test_lists_site_sets_read_only` | integration | M3 |  |

### 2.8 Migration (MIG, [PRD](../prd/components/PRD-migration-v6.md) and [LLD](../lld/LLD-migration-v2.md))

| Criterion | Planned tests | Level | Milestone | Unit |
| --- | --- | --- | --- | --- |
| MIG-1 | `tests/migration/test_secrets_import.py::test_writes_keychain_items_prints_names_and_fingerprints_only` | integration | M4 |  |
| MIG-2 | `tests/migration/test_secrets_import.py::test_conflicting_values_stop_and_ask_by_fingerprint` | integration | M4 |  |
| MIG-3 | `tests/unit/services/test_secrets_import.py::test_imports_used_names_and_reports_unused_as_not_imported` | unit | M4 |  |
| MIG-4 | `tests/migration/test_secrets_import.py::test_idempotent_and_dry_run_writes_nothing` | integration | M4 |  |
| MIG-5 | `tests/migration/test_scrub.py::test_scrub_backs_up_then_removes_only_v1_env_values` | integration | M4 |  |
| MIG-6 | `tests/unit/services/test_secrets_import.py::test_web_search_settings_to_config` | unit | M4 |  |
| MIG-10 | `tests/migration/test_legacy_import.py::test_v1_folder_byte_for_byte_unchanged` | integration | M4 |  |
| MIG-11 | `tests/migration/test_legacy_import.py::test_maps_ids_merges_pairs_and_html_documents` | integration | M4 |  |
| MIG-12 | `tests/migration/test_legacy_import.py::test_reextracts_and_falls_back_to_v1_chunks` | integration | M4 |  |
| MIG-13 | `tests/migration/test_legacy_import.py::test_cache_mode_gives_120_day_expiry` | integration | M4 |  |
| MIG-14 | `tests/migration/test_legacy_import.py::test_report_has_every_field` | integration | M4 |  |
| MIG-20 | `tests/unit/services/test_client_configs.py::test_print_config_for_three_clients_without_secrets` | unit | M4 |  |
| MIG-21 | `tests/unit/services/test_tool_map.py::test_covers_all_53_v1_tools` | unit | M4 |  |
| MIG-22 | `tests/migration/test_secrets_import.py::test_prints_no_credential_value` | integration | M4 |  |
| MIG-23 | `tests/migration/test_secrets_import.py::test_leaves_no_credential_value_at_rest` | integration | M4 |  |
| MIG-24 | `tests/migration/test_empty_cache.py::test_search_get_work_and_fetch_without_legacy_import` | integration | M4 |  |
| MIG-25 | `tests/unit/services/test_client_configs.py::test_scrub_backup_is_owner_only` | unit | M4 |  |
| MIG-26 | `tests/migration/test_retirement.py::test_retire_deletes_scrub_backups` | integration | M4 |  |
| MIG-27 | `tests/migration/test_read_boundary.py::test_secrets_import_opens_only_client_configs` | integration | M4 |  |
| MIG-28 | `tests/migration/test_read_boundary.py::test_scrub_opens_only_client_configs` | integration | M4 |  |
| MIG-29 | `tests/migration/test_read_boundary.py::test_import_legacy_opens_only_files_under_the_tree` | integration | M4 |  |
| MIG-30 | `tests/migration/test_read_boundary.py::test_read_outside_set_is_refused_naming_path_without_content` | integration | M4 |  |
| MIG-31 | `tests/migration/test_read_boundary.py::test_restore_opens_only_scrub_backups` | integration | M4 |  |
| MIG-32 | `tests/migration/test_read_boundary.py::test_import_legacy_refuses_link_leaving_tree` | integration | M4 |  |
| MIG-33 | `tests/migration/test_read_boundary.py::test_print_client_config_opens_no_file` | integration | M4 |  |
| MIG-34 | `tests/migration/test_read_boundary.py::test_v2_tree_reads_stay_at_listed_paths` | integration | M4 |  |
| MIG-35 | `tests/migration/test_read_boundary.py::test_retire_v1_opens_only_scrub_backups` (also asserts `retire-v1` without `--confirm` deletes nothing) | integration | M4 |  |

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
4. Resolved in v5: M0 plan v4 assigns the five M0 criteria that v1 left without a task (SEC-24 to M0-23, SEC-26 to M0-22, SEC-30 to M0-16, SRCH-37 to M0-21, SRCH-38 to M0-17), and the M0 gate (1.4) now names plan v4. History: five M0 criteria had no owning task in docs/build/M0-plan-v1.md, so their Unit was empty: SEC-24, SEC-26, SEC-30, SRCH-37 and SRCH-38. The M0 gate (1.4) counts only the criteria in that plan, so these would not gate M0 until the `planner` assigns them in the next M0 plan version; SRCH-38 fits M0-02, which is done, so it needs a new or reopened unit. Still open in v4; handed to the `planner`. SEC-24 now also sits in the 1.2 "No secret at rest" area, which every milestone keeps green once its test exists.
5. SEC-24 is the one criterion for no registered secret at rest after install, start and reload; the duplicate platform criterion was removed because the Security component owns the shared invariants (owner decision, 2026-10-22). Resolved in v3: 1.2 has a "No secret at rest" area listing SEC-24, SEC-27, HLTH-43 and MIG-23 (owner decision, 2026-10-22).
6. The owner-run migration commands have criteria for the INV-4 and SEC-INV-7 exception: MIG-27 to MIG-34 (PRD-migration v6, owner decision, 2026-10-22) and MIG-35 for `retire-v1 --confirm` (MIG-FR-26, owner decision, 2026-10-23). LLD-migration v2 9 now names every test, one file `tests/migration/test_read_boundary.py` with a file-open recorder. Resolved for naming. MIG-10 still covers only that the legacy import leaves v1 unmodified.
7. SEC-28 to SEC-32 are new in PRD-security v3 (approved 2026-10-23). SEC-28 to SEC-32 all have names in LLD-security v2 (and LLD-ui v2 for SEC-29 and SEC-32). Open: the levels of SEC-29 to SEC-32. The PRD sets integration (SEC-29, SEC-32) and unit (SEC-30, SEC-31); the owner asked for contract. Recommendation: keep the PRD levels. The contract level here is the in-memory MCP client against `build_mcp`, which does not serve `/ui` routes, so SEC-29 and SEC-32 need the ASGI app and a session (integration), and SEC-30 and SEC-31 need no app at all (unit). Needs the owner's confirmation. SEC-30 (M0) is owned by M0-16 in docs/build/M0-plan-v4.md.

## 6. Evidence

> **Owner:** A · **Persona:** `test-architect` (generated)

Evidence is derived status and lives in [docs/trace/coverage.md](../trace/coverage.md), regenerated by `node tools/trace-check/trace-check.mjs --write`. Do not copy it here.
