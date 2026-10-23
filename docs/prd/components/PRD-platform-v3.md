---
title: "Platform and Security"
type: prd-component
version: 3
status: draft
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
prefix: PLAT
component: platform
parent: docs/prd/PRD-v5.md
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
supersedes: docs-archive/prd/components/PRD-platform-v2.md
date: 2026-10-22
---

# Component PRD: Platform and Security (v3)

This version moves [PRD-platform v2](../../../docs-archive/prd/components/PRD-platform-v2.md) onto the SDD templates. Requirements and acceptance criteria keep their meaning; only their IDs change (section 2.16). Parent: [PRD v5](../PRD-v5.md). Low level design: [LLD-platform v1](../../lld/LLD-platform-v1.md). Test plan: [test plan v1](../../test/test-plan-v1.md).

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

The platform is everything the sources, search, cache, health and UI components stand on: the process model, configuration and secrets, the HTTP client, the error and result shape, logging, packaging, CI and upgrades (PRD-platform-v2 1).

The problems it answers, as the owner's sources state them:

- Credentials are invisible and leak. Keys sit in plaintext in three MCP client configs and can leak into chat through error messages (PRD-v4 2). The CORE key is sent to third-party PDF hosts, and Google and SerpAPI keys travel in URLs and can be echoed into chat (REVIEW-v1 2; OPS-03, OPS-04, ARCH-08).
- v1 is unsafe on a personal Mac. SQL tools can read arbitrary local files, including the MCP client configs that hold every API key (REVIEW-v1 2 and 3, finding 1; OPS-01, OPS-02).
- v1 is hard to change. It is one 4,613-line module, and a better foundation (typed settings, a safe downloader, origin-scoped credentials, an error taxonomy) was written and never wired in, so every safety flag does nothing (REVIEW-v1 2; ARCH-01, ARCH-02, OPS-06).
- Every tool blocks the event loop, so a fan-out is impossible as built (REVIEW-v1 2 and 3, finding 3; ARCH-03, OPS-13).
- Each MCP client starts its own process, so rate limits break across clients, DuckDB file locks collide, and there is no shared health (REVIEW-v1 3, finding 13; OPS-12).
- Outputs are unbounded: whole papers, 1,000-record Semantic Scholar pages, 10,000-row SQL results (REVIEW-v1 3, finding 12; ARCH-09).

Why now: the review recommends rebuilding as v2 in a new repository (REVIEW-v1 2), and the platform is the first milestone, M0 Foundation (PRD-v4 10).

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| The owner, through an agent (Claude Code, Claude desktop, Codex, OpenClaw agents) | MCP tools over stdio through the shim, or loopback streamable HTTP (PRD-v4 4) | not stated (2.13) |
| The owner, directly | The local web UI at `http://127.0.0.1:<port>`, for example to reload a key after rotating it in the Keychain (PRD-v4 4) | not stated (2.13) |
| The ECC orchestrator and coding agents | The repository and its docs, to build v2 one work unit at a time (PRD-v4 4) | not stated (2.13) |
| The sources, search, cache, health and UI components | A platform to stand on (PRD-platform-v2 1) | not stated (2.13) |

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- The daemon, the stdio shim, Keychain secrets, the HTTP client, logging, output bounds, packaging and CI (PRD-v4 5).
- The process model, configuration and secrets, the error and result shape, and upgrades (PRD-platform-v2 1).

| Non-goal | Why it is excluded |
| --- | --- |
| Remote or multi-user access | The server binds to loopback on the owner's Mac (PRD-v4 3.2). |
| Free-form SQL over local files | v1's SQL tools allowed arbitrary local file reads (PRD-v4 3.2; REVIEW-v1 3, finding 1; open decision O4). |

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

This component serves parent outcomes OUT-3 and OUT-7 (PRD-platform-v2 header, goals G3 and G7). Their measures, as the parent states them (PRD-v4 3.1):

- OUT-3, cheap to maintain: a new source needs one adapter file and one fixtures folder; no other hand-written file changes.
- OUT-7, safe by default: the security test suite is green, and secret-leak tests cover every error path.

The parent's success metrics also set test coverage on `src/` at 85% or more (PRD-v4 7).

- [ ] Q: Does the platform need outcomes of its own (`PLAT-OUT-n`) with a baseline, a target and a date, or do the parent outcomes suffice?

## 1.5 Leaps of faith

> **Owner:** H · **Persona:** none

- [ ] Q: Which two or three bets must hold for the platform to succeed, and how and by when will each be validated?

## 1.6 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

The sources state these as parent goals and requirements. They are listed here without component IDs; see the question below.

| The system must never | Parent requirement | Source |
| --- | --- | --- |
| Read a local file beyond the cache | OUT-7 | PRD-v4 3.1 (G7); PRD-platform-v2 FR-PLAT-21 |
| Send a credential outside its origin | OUT-7 | PRD-v4 3.1 (G7); PRD-platform-v2 FR-PLAT-12 |
| Put a secret in any output or log (tool results, errors, logs, UI pages, notifications, test snapshots) | OUT-7, NFR-4 | PRD-v4 3.1 and 6 |
| Keep a secret at rest outside the Keychain, except the owner's Google sign-in, which `gcloud` stores and v2 never copies | NFR-3 | PRD-v4 6; ADR 0012 |
| Listen on a non-loopback address | NFR-7 | PRD-v4 6 |
| Hard-delete through any tool | none | PRD-platform-v2 FR-PLAT-27 |

- [ ] Q: Should these invariants get component IDs (`PLAT-INV-n`), or stay as parent requirements only?

## 1.7 Known constraints and decisions

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

| Decision or constraint | Status (made or open) | Rationale or link |
| --- | --- | --- |
| One daemon per Mac; clients use a stdio shim | open (ADR Proposed, accepted when the owner approves PRD v1) | [ADR 0002](../../adr/0002-one-daemon-with-stdio-shims.md); NFR-1 |
| Secrets live in the macOS Keychain; configuration holds references | open (ADR Proposed) | [ADR 0003](../../adr/0003-secrets-in-keychain.md); NFR-3 |
| Modular core built by one composition root; no work at import | open (ADR Proposed) | [ADR 0004](../../adr/0004-modular-core-composition-root.md) |
| Async I/O end to end; CPU work in worker processes | open (ADR Proposed) | [ADR 0005](../../adr/0005-async-io-cpu-off-loop.md); NFR-2 |
| Two SQLite files; vectors stored in SQLite | open (ADR Proposed) | [ADR 0008](../../adr/0008-sqlite-stores-and-vectors.md) |
| No free-form SQL; fetched content is labeled untrusted | open (ADR Proposed; open decision O4 recommends no SQL or dataset tool in the first release) | [ADR 0009](../../adr/0009-no-sql-untrusted-content.md); PRD-v4 11 |
| SQLite remains the only store; DuckDB is not used for storage | made (ADR Accepted, 2026-10-19) | [ADR 0011](../../adr/0011-archive-keeps-text-searchable-120-day-retention.md) |
| The owner's Google sign-in for Vertex AI Search is the one credential not in the Keychain; a `gcp` extra holds `google-auth`; SerpAPI may carry its key as a query parameter under PLAT-FR-12 | made (ADR Accepted, 2026-10-19) | [ADR 0012](../../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md) |
| v2 must be maintainable and monitored, and must notify the owner when a credential is expiring or invalid | made (owner decision D5) | REVIEW-v1 1 |
| PDF parser: PyMuPDF in a worker process | open (open decision O3, recommendation) | PRD-v4 11 |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

---

## 2.1 Customer discovery

> **Owner:** A · **Persona:** `analyst`

The discovery for this component is the deep review of v1 ([REVIEW-v1](../../../docs-archive/review/REVIEW-v1.md)) and its findings files. PRD-platform-v2 lists the findings it addresses: ARCH-01 to ARCH-03, ARCH-06 to ARCH-09, ARCH-13 to ARCH-15, ARCH-17 to ARCH-21, OPS-01 to OPS-14 and OPS-19 to OPS-22. The review's top findings that drive this component:

| Review finding | Severity | Requirements it drives |
| --- | --- | --- |
| 1. Arbitrary local file read through `analytics_sql` and a bypassable `dataset_query` sandbox | Critical | PLAT-FR-20 to PLAT-FR-22 |
| 2. Monolith plus an unwired foundation; two config systems; import-time side effects | Critical | ADR 0004; PLAT-FR-4, PLAT-FR-8 |
| 3. Every tool blocks the event loop | Critical | ADR 0005; PLAT-FR-5 |
| 7. Credential leaks: CORE bearer to third-party hosts; keys in URL query strings echoed through `str(e)` | High | PLAT-FR-10 to PLAT-FR-16 |
| 12. Unbounded outputs | High | PLAT-FR-30 |
| 13. Each MCP client starts its own process | High | ADR 0002; PLAT-FR-1, PLAT-FR-2 |

No separate research note exists in `docs/research/`.

## 2.2 User stories and priority

> **Owner:** C for stories (`product-writer`), H for priority · **Seed question:** 3

No user stories exist yet (2.13).

| ID | As a... I want... so that... | Priority | Why this priority |
| --- | --- | --- | --- |

## 2.3 User experience

> **Owner:** C · **Persona:** `product-writer` drafts the narrative; designers own the design artifacts · **Seed question:** 3

The owner installs the package, then runs `research-mcp install`. Install writes the launchd jobs, creates the folders, generates the daemon token in the Keychain, and prints a client configuration snippet with no secrets in it (PLAT-FR-54, PLAT-FR-16). Each MCP client is configured to launch `research-mcp stdio`; the shim relays to the one daemon and starts it through launchd when it is down (PLAT-FR-1, PLAT-FR-2).

When the owner rotates a key, they update the Keychain item and press "Reload credentials" in the UI (or send `SIGHUP`); no restart is needed (PLAT-FR-15; HLD-v3 11.4). When a new version ships, `research-mcp upgrade` stops the daemon, upgrades, migrates, checks itself with `doctor`, and restarts, rolling back when the check fails (PLAT-FR-55).

Agents see every tool result in one envelope, bounded in size, with fetched text marked untrusted and errors given as codes rather than exception text (PLAT-FR-14, PLAT-FR-25, PLAT-FR-30).

## 2.4 Functional requirements and acceptance criteria

> **Owner:** C · **Persona:** `product-writer` drafts requirements and criteria as options; the owner selects and approves · **Seed questions:** 3, 12

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |
| PLAT-FR-1 | One daemon, `research-mcpd`, runs under a launchd LaunchAgent (`RunAtLoad`, `KeepAlive`) and owns all HTTP clients, rate limiters, stores, the scheduler, the MCP endpoint and the UI. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-2 | `research-mcp stdio` is the command every MCP client launches (clients never hold the daemon token). It relays stdio to the daemon's loopback endpoint with the bearer token; if the daemon is down it asks launchd to start it and retries; if that fails it returns one clear MCP error. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-3 | The daemon serves MCP over streamable HTTP on `127.0.0.1` only, requires a bearer token (from the Keychain, compared in constant time), checks Host and Origin, and refuses to start on a non-loopback address. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-4 | The app is built by one composition root (`build_app(settings)`) with a lifespan that opens and closes every port. Importing any module does no I/O, reads no environment and configures no logging. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-5 | No tool blocks the event loop: network I/O is async; PDF parsing, extraction and embedding run in one subprocess per task; SQLite work runs off-loop. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-6 | Long operations run as jobs (persisted, with progress, cancellation and resume) and return a job id. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-8 | One settings model, loaded from `~/.config/research-mcp/config.toml` plus `RESEARCH_MCP_*` environment overrides, validated at startup with clear errors; per-source sections come from each `SourceSpec`. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-9 | Paths follow macOS conventions: config in `~/.config/research-mcp/`; state and cache data in `~/Library/Application Support/research-mcp/` (cache data must not live in `~/Library/Caches`, which can be purged); only re-downloadable model files in `~/Library/Caches/research-mcp/`; logs in `~/Library/Logs/research-mcp/`. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-10 | Secrets are Keychain generic passwords with service `research-mcp/<NAME>` and account set to the macOS user. Configuration holds only references (`keychain:research-mcp/<NAME>`). No secret is written to any file, and no secret value is ever passed in a process argument list (Keychain writes go through stdin). The one exception is the owner's Google sign-in for Vertex AI Search: `gcloud` owns its file; v2's own code never opens or copies that file (the `google-auth` library reads it) and holds only a short-lived access token in memory. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-11 | Secret values are wrapped in a `Secret` type whose text form is `Secret(name=..., fp=...)`; only the platform HTTP, MCP-client and auth modules reveal the value. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-12 | Credentials are attached only to requests whose origin matches the credential's source, in a header where the API allows it (for example `x-goog-api-key`). Where the API accepts only a query parameter (SerpAPI), the URL is never logged and the redactor masks the parameter. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-13 | One redaction filter, attached to every log handler so third-party and child-logger records are covered, masks known secret values and credential-like patterns (`key=`, `api_key=`, `token=`, `Authorization`, `X-Subscription-Token`, `x-goog-api-key`, `AIza`, `ghp_`, `github_pat_` prefixes) in every log record, error message, tool result, UI page and notification. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-14 | Tool errors never include raw exception text or upstream error bodies; they return `{code, message, retryable, correlation_id}`, and the details go to the redacted log. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-15 | Secrets are read once at start and kept in memory; "Reload credentials" and `SIGHUP` re-read them. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-16 | The HTTP bearer token for the daemon is generated at install, stored in the Keychain, and can be rotated from the UI. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-20 | There is no free-form SQL tool (open decision O4). | | OUT-3, OUT-7 | P1 |
| PLAT-FR-21 | No tool reads a local file outside the cache root, and no tool accepts a caller-chosen local path. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-22 | If DuckDB is used internally, its connection has external access off, allowed directories limited to the cache, extension auto-install and auto-load off, and configuration locked. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-25 | Text fetched from the internet (PDF text, web pages, READMEs, abstracts, snippets) is returned inside an envelope marked `untrusted` with its source; the server instructions tell clients to treat it as data. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-26 | Every tool declares MCP annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`). | | OUT-3, OUT-7 | P1 |
| PLAT-FR-27 | State-changing tools (`fetch`, `library` actions, collection changes, review decisions) are clearly described as such; no tool hard-deletes. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-30 | Every tool returns one envelope, `{data, source_status, warnings, next_cursor, truncated}`, as a typed model so the MCP SDK emits an output schema and structured content. Outputs fit the response budget (default 64 KB) and page with cursors beyond it. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-31 | Every numeric argument has bounds in its signature; every enumerated argument is a closed set. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-32 | One error taxonomy (`ErrorCode`) distinguishes at least: `invalid_argument`, `not_found`, `unconfigured`, `auth_failed`, `rate_limited`, `upstream_error`, `upstream_timeout`, `budget_exhausted`, `too_large`, `blocked_by_policy`, `internal`. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-33 | One shared async HTTP client sets timeouts, restricts each source to its declared hosts, retries 429, 500, 502, 503, 504 and connection errors with jitter and honors `Retry-After`, applies per-source token buckets and concurrency limits that are global across all clients, caps bytes while streaming, sends one user agent with the owner contact, and records telemetry for every call. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-40 | Logs are JSON lines in `~/Library/Logs/research-mcp/research-mcp.jsonl`, rotated at 10 MB with 5 files kept. stderr receives warnings and errors only. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-41 | Log fields: time, level, event, correlation id, tool, source, operation, status, error code, latency, bytes, job id, attempt. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-42 | Query text is logged as a hash and length unless debug logging is on. | | OUT-3, OUT-7 | P2 |
| PLAT-FR-50 | `src/` layout, package `research_mcp`, Python 3.12, managed with `uv` and a committed lock file. Console scripts: `research-mcp` (CLI: `serve`, `stdio`, `doctor`, `ui`, `sources`, `config`, `install`, `upgrade`, `secrets`, `import-legacy`) and `research-mcpd`. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-51 | Heavy dependencies are extras: `pdf` (PyMuPDF), `embeddings` (fastembed, NumPy), `macos` (pyobjc, for Drive upload checks), `gcp` (google-auth, for Vertex AI Search). A search-only install needs none of them. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-52 | `tools/ci.sh --python-only` (run on every work unit) runs ruff (rules E, F, I, W, B, UP, SIM, ASYNC, BLE, S, C90), the ruff format check, mypy in strict mode on `src/`, pytest with coverage reported, and the generator checks; the full `tools/ci.sh` (milestone exit and CI) adds the 85% coverage gate, a wheel build and the `--help` smoke test. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-53 | GitHub Actions runs `tools/ci.sh` on macOS and Linux, Python 3.12 and 3.13, with SHA-pinned actions, `permissions: contents: read`, a secret scan, and a weekly dependency audit. | | OUT-3, OUT-7 | P2 |
| PLAT-FR-54 | `research-mcp install` writes the launchd plists from templates, creates the folders, generates the daemon token, and prints the client configuration snippets (no secrets in them). | | OUT-3, OUT-7 | P1 |
| PLAT-FR-55 | `research-mcp upgrade` stops the daemon, syncs dependencies, runs migrations, runs `doctor`, and restarts; on a failed `doctor` it rolls back to the previous environment. | | OUT-3, OUT-7 | P2 |
| PLAT-FR-56 | Database schemas are versioned with `PRAGMA user_version`, and numbered migrations run in a transaction at start; the daemon refuses to start on a database newer than the code. | | OUT-3, OUT-7 | P1 |
| PLAT-FR-57 | `state.db`, `cache.db` and `config.toml` are backed up nightly (7 kept), optionally copied to `Research Archive/_state/` in Drive. Stored files and the trash are not backed up (archived items live in Drive). | | OUT-3, OUT-7 | P2 |
| PLAT-FR-58 | The project version starts at 3.0.0 so it never collides with v1's 2.0.0 package metadata. | | OUT-3, OUT-7 | P1 |

Acceptance criteria, in the order of the test list (`tools/gen_test_plan.py`). Level and milestone come from that list.

| ID | Criterion | Requirement | Priority | Level | Milestone |
| --- | --- | --- | --- | --- | --- |
| PLAT-1 | The `research_mcp` package shall report a version of 3.x that matches the pyproject metadata. | PLAT-FR-58 | P1 | unit | M0 |
| PLAT-2 | The repository shall contain `tools/ci.sh` as an executable file that starts with `#!/usr/bin/env bash`. | PLAT-FR-52 | P1 | unit | M0 |
| PLAT-3 | When, in a fresh subprocess, every third-party dependency has been imported first, pydantic has been primed by defining a throwaway model, and recording has started with `os.environ` replaced by a recording mapping and an audit hook, the `research_mcp` package and every submodule shall, on import and attributing only events whose frames are in `research_mcp`, read no environment variable, open no non-module file, create no socket, start no subprocess, make no directory and add no logging handler. | PLAT-FR-4 | P1 | unit | M0 |
| PLAT-5 | The test configuration in `tests/conftest.py` shall block non-loopback sockets for every test not marked live and deselect live tests by default. | NFR-9 | P1 | unit | M0 |
| PLAT-4 | The pyproject shall declare the extras `pdf` and `embeddings`, with base dependencies that exclude pymupdf, fastembed and duckdb. | PLAT-FR-51 | P1 | unit | M0 |
| PLAT-30 | The `ToolResult` model shall serialize to the envelope shape and expose a JSON schema. | PLAT-FR-30 | P1 | unit | M0 |
| PLAT-31 | The budget shall trim items and long text to the byte limit, set `truncated` and keep the cursor. | PLAT-FR-30, NFR-5 | P1 | unit | M0 |
| PLAT-32 | The core error types shall provide every code in PLAT-FR-32 in `ErrorCode` and carry code, message, retryable and correlation_id in `ToolError`. | PLAT-FR-32 | P1 | unit | M0 |
| PLAT-33 | The untrusted envelope shall mark fetched text with `untrusted=true` and its source. | PLAT-FR-25, NFR-6 | P1 | unit | M0 |
| PLAT-6 | The `core.specs` and `core.models` types (`SourcePolicy`, `AuthSpec` origins, `SearchFilters` bounds, `Work`, `CallRecord`) and `research_mcp.testing.clock.FakeClock` shall respectively validate and advance time deterministically. | SRC-FR-1, PLAT-FR-30 | P1 | unit | M0 |
| PLAT-34 | The system shall HMAC-sign cursors with a key passed in and reject a tampered or foreign cursor with `invalid_argument`. | SRCH-FR-6 | P1 | unit | M0 |
| PLAT-8 | The settings model shall load from `config.toml` with `RESEARCH_MCP_` environment overrides, fail on invalid values with a clear message, and apply defaults that match SPEC section 2 (including `cache.retention_days = 120`). | PLAT-FR-8, CACHE-FR-30 | P1 | unit | M0 |
| PLAT-9 | The settings model shall default state and cache data to `~/Library/Application Support/research-mcp` (never `~/Library/Caches`), models to `~/Library/Caches` and logs to `~/Library/Logs`, and create directories with mode 0700. | PLAT-FR-9, CACHE-FR-59 | P1 | unit | M0 |
| PLAT-10 | If `server.host` is a non-loopback address, then the settings validation shall reject it. | PLAT-FR-3, NFR-7 | P1 | unit | M0 |
| PLAT-11 | The settings validation shall reject `contact.email` placeholder values (example.com, example.org, .test, .invalid) and allow an unset email. | SRC-FR-11, NFR-8 | P1 | unit | M0 |
| PLAT-12 | The secrets module shall parse secret references of the forms `keychain:research-mcp/NAME` and `env:NAME` and fail on malformed references. | PLAT-FR-10 | P1 | unit | M0 |
| PLAT-40 | The logging configuration shall write JSON lines to the rotating file (10 MB x 5) and only warnings and errors to stderr. | PLAT-FR-40 | P1 | unit | M0 |
| PLAT-41 | The logging configuration shall give every log record `correlation_id` and the fields in PLAT-FR-41. | PLAT-FR-41 | P1 | unit | M0 |
| PLAT-42 | While debug logging is off, the logging configuration shall record query text only as a hash and length. | PLAT-FR-42 | P2 | unit | M0 |
| PLAT-35 | When a response is a 429 with `Retry-After`, the HTTP client shall retry after the stated delay through the injected sleeper, fail at once as `rate_limited` with `retry_after_ms` for delays over 60 s, and end as `rate_limited` with the last `retry_after_ms` after three 429s. | PLAT-FR-33 | P1 | unit | M0 |
| PLAT-36 | The HTTP client shall retry 500, 502, 503, 504 and connection errors up to 3 attempts with jittered backoff and then fail with `upstream_error`, not retry other 4xx, and fail a request to a host outside the policy with `blocked_by_policy`. | PLAT-FR-33 | P1 | unit | M0 |
| PLAT-37 | The HTTP client shall share each per-source token bucket among all callers, so that two concurrent arXiv calls are spaced 3 s apart (fake clock). | PLAT-FR-33, NFR-8 | P1 | unit | M0 |
| PLAT-38 | If a streamed response exceeds the byte cap, then the HTTP client shall abort with `too_large` before the whole body is read. | PLAT-FR-33 | P1 | unit | M0 |
| PLAT-39 | The HTTP client shall send the user agent with the owner contact on every request and emit a call record for every attempt. | PLAT-FR-33, HLTH-FR-1, NFR-8 | P1 | unit | M0 |
| PLAT-50 | The `Migrator` shall run migrations inside explicit `BEGIN IMMEDIATE` and `COMMIT` (so a failing script leaves no partial schema), set `user_version` for `state.db` and `cache.db`, and refuse SQLite older than 3.37. | PLAT-FR-56 | P1 | unit | M0 |
| PLAT-51 | If a database is newer than the code, then the store shall fail to open it with a clear error. | PLAT-FR-56 | P1 | unit | M0 |
| PLAT-52 | The database connections shall use WAL, `foreign_keys=ON` and `busy_timeout`, and serialize writes. | PLAT-FR-5 | P1 | unit | M0 |
| PLAT-53 | The stores shall create schemas that match SPEC 8.1 and 10.1, keep the external-content FTS table in sync through triggers with `snippet()` returning text, hold the CHECK constraints for archived and discarded documents, and not pin collections by default. | CACHE-FR-30, CACHE-FR-36, CACHE-FR-55 | P1 | unit | M0 |
| PLAT-60 | The MCP server shall declare `readOnlyHint`, `destructiveHint`, `idempotentHint` and `openWorldHint` on every registered tool. | PLAT-FR-26 | P1 | contract | M0 |
| PLAT-61 | The server instructions shall state the untrusted-content rule and the owner-decision rule for reviews. | PLAT-FR-25, CACHE-FR-35 | P1 | contract | M0 |
| PLAT-62 | If a tool hits an internal error, then the MCP server shall return code, message, retryable and correlation_id with no exception text. | PLAT-FR-14, PLAT-FR-32 | P1 | contract | M0 |
| PLAT-63 | The MCP server shall never return a tool result that exceeds `limits.response_bytes`. | PLAT-FR-30, NFR-5 | P1 | contract | M0 |
| PLAT-70 | The `build_app` composition root shall open and close every component in its lifespan and answer `/healthz` and `/readyz`. | PLAT-FR-4, HLTH-FR-43 | P1 | integration | M0 |
| PLAT-71 | The daemon shall refuse to bind a non-loopback address. | PLAT-FR-3, NFR-7 | P1 | integration | M0 |
| PLAT-72 | The stdio shim shall relay a full MCP session (initialize, list tools, call search) to an in-process daemon. | PLAT-FR-2, NFR-1 | P1 | integration | M0 |
| PLAT-73 | While the daemon is down, the stdio shim shall ask launchd to start it (fake launchctl), retry, and then return one clear MCP error. | PLAT-FR-2 | P1 | integration | M0 |
| PLAT-74 | The job service shall persist job submit, status, progress and cancel in `state.db`. | PLAT-FR-6 | P1 | integration | M0 |
| PLAT-75 | While a slow fake source runs, the daemon shall keep the event loop responsive (heartbeat gap under 200 ms). | PLAT-FR-5, NFR-2 | P1 | integration | M0 |
| PLAT-76 | The scheduler shall compare wall-clock due times every 60 s and run a missed daily job exactly once after a simulated sleep or restart (FakeClock). | PLAT-FR-6 | P1 | integration | M0 |
| PLAT-77 | The daemon shall mount MCP stateless at `/mcp`, so that the shim keeps working across a daemon restart and replays initialize once on a session error. | PLAT-FR-2, NFR-1 | P1 | integration | M0 |
| PLAT-80 | The `research-mcp --help` output shall list serve, stdio, doctor, ui, sources, config, install, upgrade, secrets and import-legacy. | PLAT-FR-50 | P1 | unit | M0 |
| PLAT-81 | The install command shall render the daemon, watchdog and doctor launchd plists with every placeholder filled, such that plistlib parses them, and write nothing secret. | PLAT-FR-54, HLTH-FR-41 | P1 | unit | M0 |
| PLAT-82 | The `install --print-client-config` command shall print entries that launch `research-mcp stdio` and contain no secret. | PLAT-FR-54, MIG-FR-20 | P1 | unit | M0 |
| PLAT-83 | The CLI shall generate `DAEMON_TOKEN` through the secret provider during install if it is absent, and replace it on `secrets rotate-token` so that the old token stops working. | PLAT-FR-16 | P1 | unit | M0 |
| PLAT-13 | The system shall declare the `gcp` extra (google-auth) in pyproject, exclude google-auth from base dependencies, and report `vertex_search` as unconfigured with the install command when the extra is not installed. | PLAT-FR-51, SRC-FR-7 | P1 | unit | M1 |

## 2.5 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

This component defines no NFR of its own. The parent's NFR-1 to NFR-10 apply (PRD-platform-v2 header). Their targets, as the parent states them (PRD-v4 6):

| Parent NFR | Quality | Target |
| --- | --- | --- |
| NFR-1 | Single process | One daemon per Mac owns all HTTP clients, rate limiters, stores and the scheduler; clients connect through a thin stdio shim or loopback HTTP. |
| NFR-2 | Async | No tool blocks the event loop. |
| NFR-3 | No secrets at rest outside the Keychain | Config files hold references only, including the daemon token and any webhook token; the Google sign-in is the one exception. |
| NFR-4 | No secret in any output | Tool results, errors, logs, UI pages, notifications and test snapshots never contain a secret value. |
| NFR-5 | Bounded output | Every tool result fits a byte budget (default 64 KB) and pages with a cursor beyond it. |
| NFR-6 | Untrusted content is labeled | Text fetched from the internet is returned inside an envelope marked untrusted. |
| NFR-7 | Loopback only | Nothing listens on a non-loopback address; every HTTP request except `/healthz` and `/readyz` needs a bearer token or a UI session. |
| NFR-8 | Respect upstream terms | Per-source rate limits are global across clients; contact email and user agent are sent where asked; arXiv's 1 request per 3 seconds is honored. |
| NFR-9 | Testable offline | The default test run makes no network calls; live checks are opt-in. |
| NFR-10 | Docs follow code | Tool and source inventories are generated from the registry. |

## 2.6 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

| Data | Classification | Source or owner | Retention | Notes |
| --- | --- | --- | --- | --- |
| Credential values and the daemon token | not stated (2.13) | macOS login Keychain, `research-mcp/<NAME>` (HLD-v3 10) | By Keychain | Never in files or argument lists (PLAT-FR-10) |
| Google sign-in access token | not stated (2.13) | `gcloud` owns the sign-in (ADR 0012) | In memory only, short-lived | v2 never copies the credential file |
| `config.toml` | not stated (2.13) | The owner, `~/.config/research-mcp/` | Backed up nightly, 7 kept (PLAT-FR-57) | Settings and secret references only |
| `state.db` | not stated (2.13) | Application Support (HLD-v3 10) | Backed up nightly, 7 kept (PLAT-FR-57) | Credential metadata, source health, telemetry, jobs, schedule runs, notifications, review batches |
| `cache.db` | not stated (2.13) | Application Support (HLD-v3 10) | Backed up nightly, 7 kept (PLAT-FR-57) | Works, documents, extractions, embeddings and the lifecycle (cache component) |
| Logs | not stated (2.13) | `~/Library/Logs/research-mcp/` | 10 MB with 5 files kept (PLAT-FR-40) | Redacted; query text as hash and length (PLAT-FR-42) |

## 2.7 Integrations and owners

> **Owner:** H confirms owners and SLAs · **Persona:** `architect` may draft · **Seed question:** 8

| System | Owner | Relationship (depends on, feeds, replaces) | SLA |
| --- | --- | --- | --- |
| macOS Keychain (`/usr/bin/security`) | not stated (2.13) | Depends on: holds every secret (ADR 0003) | not stated |
| launchd | not stated (2.13) | Depends on: runs the daemon, the watchdog and the daily doctor (PLAT-FR-1, PLAT-FR-54) | not stated |
| `gcloud` and `google-auth` | not stated (2.13) | Depends on: the Google sign-in for Vertex AI Search (ADR 0012) | not stated |
| MCP clients (Claude Code, Claude desktop, Codex, OpenClaw agents) | not stated (2.13) | Feeds: they launch the stdio shim (PRD-v4 4) | not stated |
| Upstream APIs | not stated (2.13) | Depends on: reached only through the shared HTTP client (PLAT-FR-33) | not stated |
| GitHub Actions | not stated (2.13) | Depends on: runs CI once a remote exists (PLAT-FR-53) | not stated |
| v1 (`my-research-mcp-server`) | not stated (2.13) | Replaces (PRD-v4 1) | not stated |

## 2.8 Product risks

> **Owner:** H · **Persona:** none

| Risk | Question | Assessment | Mitigation |
| --- | --- | --- | --- |
| Value | Will customers choose to use this? | not stated (2.13) | not stated |
| Usability | Can customers use it, including with accessibility needs? | not stated (2.13) | not stated |
| Viability | Does it work for the business: economics, legal, compliance, operations? | Operations: the Keychain may be locked or unreadable, for example right after login (PRD-v4 12). | Reads go through `/usr/bin/security` with a timeout; a locked Keychain is one `keychain_locked` state and one notification, not a notice per key; `doctor` gives the fix (PRD-v4 12). |

## 2.9 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | not stated (2.13) |
| Business conditions that must halt the rollout | not stated (2.13) |
| Support owner and escalation path | not stated (2.13) |
| Response targets by severity (S0 to S4) | not stated (2.13) |

## 2.10 Measurement and experimentation

> **Owner:** C · **Persona:** `product-writer` drafts; the owner decides

| Outcome | Measured by | Experiment (if any) |
| --- | --- | --- |
| OUT-3 | Files changed when an agent adds a new free source in one work unit (owner check OC-11 in TEST-PLAN-v3 6) | none |
| OUT-7 | The security component's criteria passing in CI, with secret-leak tests on every error path (PRD-v4 3.1) | none |

## 2.11 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

As the sources state it:

- M0 exit: all M0 tests green, and a client can search three sources through the shim on the owner's Mac (PRD-v4 10).
- M0 gate: every M0 test in Appendix A passes; the full `tools/ci.sh` is green (lint, strict mypy, 85% coverage on `src/`, build, `--help`); owner checks OC-01 and OC-02 pass (TEST-PLAN-v3 8).
- PLAT-13 lands in M1 with the Vertex source (PRD-platform-v2, changes from v1).

## 2.12 Edge cases and error behavior

> **Owner:** A · **Persona:** `product-writer`

| Edge case | Behavior | Criterion |
| --- | --- | --- |
| The daemon is down when a client starts | The shim asks launchd to start it, retries, then returns one clear MCP error | PLAT-73 |
| The daemon restarts during a client session | The shim keeps working and replays initialize once on a session error | PLAT-77 |
| `server.host` is not loopback | Settings validation rejects it, and the daemon refuses to bind | PLAT-10, PLAT-71 |
| `contact.email` is a placeholder or unset | A placeholder is rejected; an unset email is allowed | PLAT-11 |
| A secret reference is malformed | Parsing fails | PLAT-12 |
| An upstream returns 429 with a `Retry-After` over 60 s | The call fails at once as `rate_limited` with `retry_after_ms` | PLAT-35 |
| A request names a host outside the source's policy | It fails with `blocked_by_policy` | PLAT-36 |
| A response body is larger than the cap | The call aborts with `too_large` before the whole body is read | PLAT-38 |
| A result is larger than the response budget | Items and long text are trimmed, `truncated` is set and the cursor is kept | PLAT-31, PLAT-63 |
| A cursor is tampered with or foreign | It is rejected with `invalid_argument` | PLAT-34 |
| A tool hits an internal error | The result carries a code and no exception text | PLAT-62 |
| A migration script fails | No partial schema is left | PLAT-50 |
| A database is newer than the code | Opening it fails with a clear error | PLAT-51 |
| The Mac sleeps through a daily job | The job runs exactly once afterward | PLAT-76 |
| The `gcp` extra is not installed | `vertex_search` reports `unconfigured` with the install command | PLAT-13 |

## 2.13 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves before Gate 1

- [ ] Q: Which user stories (`PLAT-US-n`) does the owner want for this component, and at what priority? The Story column in 2.4 is empty until they exist.
- [ ] Q: What is the relative size of each user group in 1.2?
- [ ] Q: How is each data item in 2.6 classified?
- [ ] Q: Who owns each integration in 2.7, and what SLA applies?
- [ ] Q: What are the Value and Usability assessments in 2.8?
- [ ] Q: What are the rollout appetite, halt conditions, support owner and response targets in 2.9?
- [ ] Q: These requirements have no criterion in this PRD; their evidence lives in other components or in owner checks (TEST-PLAN-v3 5 and 6). Is that the intended split? PLAT-FR-1 (OC-01), PLAT-FR-11 (SEC-1), PLAT-FR-12 (SEC-8, SEC-9, SRC-33), PLAT-FR-13 (SEC-5, SEC-6, SEC-7, SEC-14, SRC-33), PLAT-FR-15 (SEC-4), PLAT-FR-20 (SEC-21), PLAT-FR-21 (CACHE-11), PLAT-FR-22 (SEC-21), PLAT-FR-27 (CACHE-34, SEC-20), PLAT-FR-31 (SRCH-21), PLAT-FR-53 (OC-08), PLAT-FR-55 (OC-09), PLAT-FR-57 (CACHE-49, OC-10).
- [ ] Q: No criterion checks the `macos` extra of PLAT-FR-51; PLAT-4 covers `pdf` and `embeddings` and PLAT-13 covers `gcp`. Is that gap intended?
- [ ] Q: The PRD-platform-v2 header names its parent "PRD v3" but links PRD-v4, says it supersedes "v1" but links PRD-platform-v2 itself, and cites SPEC v1 and HLD-v3 sections 3 and 9. Which parent and design versions should this PRD cite?
- Assumption: parent outcomes OUT-3 and OUT-7 are the renamed goals G3 and G7 of PRD-v4, as the brief for this migration states.

## 2.14 Glossary

> **Owner:** A · **Persona:** `product-writer`

| Term | Definition |
| --- | --- |
| Daemon | `research-mcpd`, the one process per Mac that owns all HTTP clients, rate limiters, stores, the scheduler, the MCP endpoint and the UI (PLAT-FR-1). |
| Shim | `research-mcp stdio`, the thin relay every MCP client launches; it holds no state (PLAT-FR-2; HLD-v3 2). |
| Composition root | `build_app(settings)`, the one place that creates every component inside a lifespan (PLAT-FR-4). |
| Envelope | The one result shape every tool returns: `{data, source_status, warnings, next_cursor, truncated}` (PLAT-FR-30). |
| Response budget | The byte limit a tool result must fit, `limits.response_bytes`, default 64 KB (PLAT-FR-30; NFR-5). |
| Untrusted envelope | The wrapper that marks fetched text with `untrusted=true` and its source (PLAT-FR-25). |
| Secret reference | Configuration text that names a secret without holding it, such as `keychain:research-mcp/<NAME>` (PLAT-FR-10). |
| `Secret` | The type that wraps a secret value; its text form shows only the name and a fingerprint (PLAT-FR-11). |
| Call record | The telemetry row recorded for every outbound attempt (PLAT-FR-33; HLTH-FR-1). |
| Job | A long operation, persisted with progress, cancellation and resume, that returns a job id (PLAT-FR-6). |

## 2.15 ID history

> **Owner:** C · **Persona:** `product-writer` records; the owner confirms

| ID | Status | Replaced by | Reason |
| --- | --- | --- | --- |

### Gate 1: Requirements approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

## 2.16 Earlier IDs

> **Owner:** A · **Persona:** `product-writer`

| Earlier ID | New ID |
| --- | --- |
| FR-PLAT-01 | PLAT-FR-1 |
| FR-PLAT-02 | PLAT-FR-2 |
| FR-PLAT-03 | PLAT-FR-3 |
| FR-PLAT-04 | PLAT-FR-4 |
| FR-PLAT-05 | PLAT-FR-5 |
| FR-PLAT-06 | PLAT-FR-6 |
| FR-PLAT-08 | PLAT-FR-8 |
| FR-PLAT-09 | PLAT-FR-9 |
| FR-PLAT-10 | PLAT-FR-10 |
| FR-PLAT-11 | PLAT-FR-11 |
| FR-PLAT-12 | PLAT-FR-12 |
| FR-PLAT-13 | PLAT-FR-13 |
| FR-PLAT-14 | PLAT-FR-14 |
| FR-PLAT-15 | PLAT-FR-15 |
| FR-PLAT-16 | PLAT-FR-16 |
| FR-PLAT-20 | PLAT-FR-20 |
| FR-PLAT-21 | PLAT-FR-21 |
| FR-PLAT-22 | PLAT-FR-22 |
| FR-PLAT-25 | PLAT-FR-25 |
| FR-PLAT-26 | PLAT-FR-26 |
| FR-PLAT-27 | PLAT-FR-27 |
| FR-PLAT-30 | PLAT-FR-30 |
| FR-PLAT-31 | PLAT-FR-31 |
| FR-PLAT-32 | PLAT-FR-32 |
| FR-PLAT-33 | PLAT-FR-33 |
| FR-PLAT-40 | PLAT-FR-40 |
| FR-PLAT-41 | PLAT-FR-41 |
| FR-PLAT-42 | PLAT-FR-42 |
| FR-PLAT-50 | PLAT-FR-50 |
| FR-PLAT-51 | PLAT-FR-51 |
| FR-PLAT-52 | PLAT-FR-52 |
| FR-PLAT-53 | PLAT-FR-53 |
| FR-PLAT-54 | PLAT-FR-54 |
| FR-PLAT-55 | PLAT-FR-55 |
| FR-PLAT-56 | PLAT-FR-56 |
| FR-PLAT-57 | PLAT-FR-57 |
| FR-PLAT-58 | PLAT-FR-58 |
| AT-PLAT-01 | PLAT-1 |
| AT-PLAT-02 | PLAT-2 |
| AT-PLAT-03 | PLAT-3 |
| AT-PLAT-05 | PLAT-5 |
| AT-PLAT-04 | PLAT-4 |
| AT-PLAT-30 | PLAT-30 |
| AT-PLAT-31 | PLAT-31 |
| AT-PLAT-32 | PLAT-32 |
| AT-PLAT-33 | PLAT-33 |
| AT-PLAT-06 | PLAT-6 |
| AT-PLAT-34 | PLAT-34 |
| AT-PLAT-08 | PLAT-8 |
| AT-PLAT-09 | PLAT-9 |
| AT-PLAT-10 | PLAT-10 |
| AT-PLAT-11 | PLAT-11 |
| AT-PLAT-12 | PLAT-12 |
| AT-PLAT-40 | PLAT-40 |
| AT-PLAT-41 | PLAT-41 |
| AT-PLAT-42 | PLAT-42 |
| AT-PLAT-35 | PLAT-35 |
| AT-PLAT-36 | PLAT-36 |
| AT-PLAT-37 | PLAT-37 |
| AT-PLAT-38 | PLAT-38 |
| AT-PLAT-39 | PLAT-39 |
| AT-PLAT-50 | PLAT-50 |
| AT-PLAT-51 | PLAT-51 |
| AT-PLAT-52 | PLAT-52 |
| AT-PLAT-53 | PLAT-53 |
| AT-PLAT-60 | PLAT-60 |
| AT-PLAT-61 | PLAT-61 |
| AT-PLAT-62 | PLAT-62 |
| AT-PLAT-63 | PLAT-63 |
| AT-PLAT-70 | PLAT-70 |
| AT-PLAT-71 | PLAT-71 |
| AT-PLAT-72 | PLAT-72 |
| AT-PLAT-73 | PLAT-73 |
| AT-PLAT-74 | PLAT-74 |
| AT-PLAT-75 | PLAT-75 |
| AT-PLAT-76 | PLAT-76 |
| AT-PLAT-77 | PLAT-77 |
| AT-PLAT-80 | PLAT-80 |
| AT-PLAT-81 | PLAT-81 |
| AT-PLAT-82 | PLAT-82 |
| AT-PLAT-83 | PLAT-83 |
| AT-PLAT-13 | PLAT-13 |
