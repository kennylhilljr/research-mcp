---
title: "Platform and Security low level design"
type: lld
version: 2
status: approved
approved_by: "Kenny Hill (Engineering)"
approved: 2026-10-23
owner: "Kenny Hill"
prefix: PLAT
component: platform
parent: docs/spec/SPEC-v5.md
supersedes: docs/lld/LLD-platform-v1.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# LLD: Platform and Security (v2)

This LLD carries over SPEC-v2 sections 1 (conventions and layout), 2 (settings and paths), 3.1 to 3.7 (secrets, Google sign-in, redaction and logging, HTTP client, downloader, stores and migrations, workers and jobs, errors and the envelope), 7.4 (MCP transport), 12.1 (packaging and CI) and 12.2 (launchd, install and upgrade), with HLD-v3 sections 3, 10 and 12 for context. Names are unchanged from SPEC-v2 unless a decision in section 10 renames one. Requirements and criteria are in [PRD-platform v4](../prd/components/PRD-platform-v4.md); the system design is [SPEC-v5](../spec/SPEC-v5.md); the security component's requirements are in [PRD-security v3](../prd/components/PRD-security-v3.md) and the test strategy is [test plan v4](../test/test-plan-v4.md) (draft). Supersedes [LLD-platform v1](LLD-platform-v1.md). The machine-readable contract is [envelope and error codes v1](../contracts/envelope-and-errors-v1.md) (draft).

**Changes in v2.** This version follows the approved PRD-platform v4, SPEC-v4 and PRD-security v2, which win wherever v1 disagreed. History note: PLAT-FR-16 is replaced by PLAT-FR-59 (the daemon token rotates only from the CLI, owner decision, 2026-10-22); SRC-FR-11 by SRC-FR-24; SRCH-FR-4 and SRCH-FR-10 by SRCH-FR-27 and SRCH-FR-28; MIG-FR-23 by MIG-FR-25; the source state `skipped_budget` is now `budget_exhausted`, and the `web` fallback adds `not_needed`. Added: PLAT-FR-40 as 5 files of 10 MB with the `daemon.err.log` rotation that SPEC-v4 12 hands to this LLD (4.3, 5.10), PLAT-FR-57 as 7 nightly backups (3.3), PLAT-84 (1, 9), the platform side of SEC-INV-1 to SEC-INV-11 (4.7), the enforcement points of SEC-24 and SEC-26 (4.7), the stdio-shim-only client rule (5.7), the SIGHUP handler (5.10) and the user agent without a contact (5.3). The open questions of v1 are settled in section 10 from the approved sources; the two that the sources left open were answered by the owner on 2026-10-22 (3.3, 4.5, 9), and section 11 holds no open question. The owner also answered the questions of LLD-security v2 that touch this LLD: the single auth gate (4.5), the redaction of tool results with SEC-28, proposed in PRD-security v3 (4.5, 4.7, 5.6, 9), and the unauthenticated surfaces (4.5).

**Reviewer note.** The brief for this version asked the `component-designer` to update the whole file. Sections 4, 8 and 9 belong to other personas (`security-reviewer`, `sre`, `test-architect`); the changes there were drafted by the `component-designer` and have been reviewed in Gate 3 on 2026-10-23: section 4 by `security-reviewer`, section 8 by `sre` and section 9 by `test-architect`; nothing here has been verified by the owner.

Section numbers inside text copied from the SPEC (for example "(9.3)" or "section 4") refer to SPEC-v2; bare section numbers in this LLD's own text (for example "(4.4)" or "(11)") refer to this LLD. In the tables, "SPEC n" means section n of SPEC-v5. Requirement and criterion IDs in copied text use the new IDs; rows marked "(SPEC-v2 0.6)" are verbatim and keep the old IDs.

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

Governing sections: SPEC 2 (system context), SPEC 3 (component architecture), SPEC 9 (security architecture), SPEC 10 (data stores), SPEC 12 (deployment and operations) and SPEC 15 (stack).

| Requirement | Criteria | SPEC section | Detailed in |
| --- | --- | --- | --- |
| PLAT-FR-1 | none in PRD-platform (owner check OC-01) | SPEC 2, 3, 12 | 5.9, 5.10 |
| PLAT-FR-2 | PLAT-72, PLAT-73, PLAT-77, SEC-26 | SPEC 2, 3 | 2.3, 5.7 |
| PLAT-FR-3 | PLAT-10, PLAT-71, SEC-11, SEC-12 | SPEC 2, 9 | 4.5 |
| PLAT-FR-4 | PLAT-3, PLAT-70 | SPEC 3 | 2.3, 5.1, 5.2 |
| PLAT-FR-5 | PLAT-52, PLAT-75 | SPEC 3 | 3.1, 5.5 |
| PLAT-FR-6 | PLAT-74, PLAT-76 | SPEC 3 | 5.5 |
| PLAT-FR-8 | PLAT-8 | SPEC 10 | 7.1 |
| PLAT-FR-9 | PLAT-9 | SPEC 10 | 3.2, 7.1 |
| PLAT-FR-10 | PLAT-12, SEC-2, SEC-13, SEC-24, SEC-26, SEC-27 | SPEC 9, 10 | 4.1, 4.2, 4.7 |
| PLAT-FR-11 | none in PRD-platform (SEC-1) | SPEC 9 | 4.1 |
| PLAT-FR-12 | none in PRD-platform (SEC-8, SEC-9, SRC-33) | SPEC 9 | 4.4 |
| PLAT-FR-13 | none in PRD-platform (SEC-5, SEC-6, SEC-7, SEC-14, SEC-28 proposed in PRD-security v3, SRC-33) | SPEC 9 | 4.3 |
| PLAT-FR-14 | PLAT-62, SEC-10 | SPEC 9 | 5.6, 6 |
| PLAT-FR-15 | none in PRD-platform (SEC-4) | SPEC 9, 11.4 | 4.1, 5.10 |
| PLAT-FR-59 (replaces PLAT-FR-16) | PLAT-83, SEC-13 | SPEC 9, 12 | 4.5, 5.9 |
| PLAT-FR-20 | none in PRD-platform (SEC-21) | SPEC 9 | 4.6 |
| PLAT-FR-21 | none in PRD-platform (CACHE-11, SEC-25) | SPEC 9 | 4.6 |
| PLAT-FR-22 | none in PRD-platform (SEC-21) | SPEC 9 | 4.6 |
| PLAT-FR-25 | PLAT-33, PLAT-61 | SPEC 9 | 2.1 |
| PLAT-FR-26 | PLAT-60 | SPEC 9 | 2.3 |
| PLAT-FR-27 | none in PRD-platform (CACHE-34, SEC-20) | SPEC 9 | 4.6 |
| PLAT-FR-30 | PLAT-6, PLAT-30, PLAT-31, PLAT-63 | SPEC 3, 5 | 2.1, 5.6 |
| PLAT-FR-31 | none in PRD-platform (SRCH-21) | SPEC 5 | 2.3 |
| PLAT-FR-32 | PLAT-32, PLAT-62 | SPEC 3, 5 | 2.1, 6 |
| PLAT-FR-33 | PLAT-35, PLAT-36, PLAT-37, PLAT-38, PLAT-39 | SPEC 3, 9 | 2.2, 5.3, 6 |
| PLAT-FR-40 | PLAT-40 | SPEC 10, 12 | 4.3, 5.10, 8 |
| PLAT-FR-41 | PLAT-41 | SPEC 12 | 8 |
| PLAT-FR-42 | PLAT-42 | SPEC 12 | 4.3, 8 |
| PLAT-FR-50 | PLAT-80 | SPEC 12 | 2.4, 5.8 |
| PLAT-FR-51 | PLAT-4, PLAT-13, PLAT-84 | SPEC 12, 15 | 5.8, 7.2 |
| PLAT-FR-52 | PLAT-2 | SPEC 12 | 5.8 |
| PLAT-FR-53 | none in PRD-platform (owner check OC-08) | SPEC 12 | 5.8 |
| PLAT-FR-54 | PLAT-81, PLAT-82 | SPEC 12 | 2.5, 5.9 |
| PLAT-FR-55 | none in PRD-platform (owner check OC-09) | SPEC 12 | 5.9, 6 |
| PLAT-FR-56 | PLAT-50, PLAT-51 | SPEC 10 | 3.1 |
| PLAT-FR-57 | none in PRD-platform (CACHE-49, owner check OC-10) | SPEC 10, 12 | 3.3 |
| PLAT-FR-58 | PLAT-1 | SPEC 12 | 5.1 |
| SRC-FR-1 (sources) | PLAT-6 | SPEC 4 | 2.2 |
| SRC-FR-7 (sources) | PLAT-13 | SPEC 12 | 7.2 |
| SRC-FR-24 (sources; replaces SRC-FR-11) | PLAT-11 | SPEC 4 | 5.3, 7.1 |
| SRCH-FR-6 (search) | PLAT-34 | SPEC 5 | 5.6 |
| CACHE-FR-30, CACHE-FR-36, CACHE-FR-55 (cache) | PLAT-8, PLAT-53 | SPEC 10 | 3.1, 7.1 |
| CACHE-FR-50 (cache) | PLAT-84 | SPEC 6, 12 | 5.8, 7.2 |
| CACHE-FR-59 (cache) | PLAT-9 | SPEC 10 | 3.2, 7.1 |
| HLTH-FR-1 (health) | PLAT-39 | SPEC 7 | 5.3 |
| HLTH-FR-41 (health) | PLAT-81 | SPEC 12 | 2.5 |
| HLTH-FR-43 (health) | PLAT-70 | SPEC 7 | 4.5 |
| MIG-FR-20 (migration) | PLAT-82 | SPEC 12 | 5.9 |
| NFR-9 (parent) | PLAT-5 | SPEC 17 | 9 |

All 46 criteria of PRD-platform v4 appear above: PLAT-1 to PLAT-6, PLAT-8 to PLAT-13, PLAT-30 to PLAT-42, PLAT-50 to PLAT-53, PLAT-60 to PLAT-63, PLAT-70 to PLAT-77, PLAT-80 to PLAT-84.

**Security criteria enforced in platform code** (PRD-security v3 2.4; the security component owns the criteria, this component owns the code): SEC-1 (4.1), SEC-2 and SEC-3 (4.1), SEC-4 (4.1, 5.10), SEC-5, SEC-6, SEC-7 and SEC-14 (4.3), SEC-8, SEC-9 and SEC-10 (4.4, 6.1), SEC-11 and SEC-12 (4.5), SEC-13 (4.1), SEC-20 (4.6), SEC-21 (4.6), SEC-22 (2.1), SEC-23 (4.6, 5.5), SEC-24 (4.7), SEC-25 (4.6), SEC-26 (4.7, 5.7), SEC-27 (4.2), SEC-28 (proposed in PRD-security v3; 4.7, 5.6). The invariants SEC-INV-1 to SEC-INV-11 and their platform enforcement points are in 4.7.

**Who owns which file** (`sdd.config.json` path ownership against SPEC 19; recorded here so the implementer does not guess; `tests/integration` is in the platform paths, owner decision, 2026-10-22):

| Name or path | Design lives in | Code path owned by | Note |
| --- | --- | --- | --- |
| `build_mcp`, `@tool_boundary` in `mcp_app/server.py` | this LLD (2.3, 5.6; PLAT-60 to PLAT-63, SPEC 19) | search component (`src/research_mcp/mcp_app`) | Platform designs the boundary and the transport; the search component's work units write the file and the tool catalog |
| `tests/contract/` | this LLD for PLAT-60 to PLAT-63 (9) | search component | Platform criteria are cited in files the search component owns |
| `core/specs.py`, `core/models.py` | [LLD-sources](LLD-sources-v2.md) 2.1, 2.2 and 3.1 (SPEC 4, 19) | platform (`src/research_mcp/core`) | PLAT-6 verifies that they validate |
| `core/ids.py` | [LLD-search](LLD-search-v2.md) 5.2 | search component | Not changed here |
| `services/backup.py` (`BackupService`) | requirement and settings here (3.3); the service design in [LLD-cache](LLD-cache-v2.md) 5 (SPEC 10, 19) | cache component | |
| `services/health.py`, `credentials.py`, `notify.py`, `disk.py` | [LLD-health](LLD-health-v2.md) | health component | Platform provides the ports they use |

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

Machine-readable contract: [envelope and error codes v1](../contracts/envelope-and-errors-v1.md), approved at Gate 3 (2026-10-23) (decided in section 10: the envelope and the error codes get a contract; the CLI, the launchd templates and the endpoints do not). The CLI is a human-facing surface verified by PLAT-80 and tabulated in 2.4; the endpoint shapes belong to [LLD-health](LLD-health-v2.md) 2; the tool catalog and its schemas are emitted by the MCP SDK from the Pydantic models (PLAT-30), so a separate file would only duplicate them.

### 2.1 Errors and the envelope (SPEC-v2 3.7; PLAT-FR-25, PLAT-FR-30, PLAT-FR-32)

```python
class ErrorCode(StrEnum):
    INVALID_ARGUMENT = "invalid_argument"; NOT_FOUND = "not_found"; UNCONFIGURED = "unconfigured"
    AUTH_FAILED = "auth_failed"; RATE_LIMITED = "rate_limited"; UPSTREAM_ERROR = "upstream_error"
    UPSTREAM_TIMEOUT = "upstream_timeout"; BUDGET_EXHAUSTED = "budget_exhausted"; TOO_LARGE = "too_large"
    BLOCKED_BY_POLICY = "blocked_by_policy"; DISABLED = "disabled"; EXTRACT_FAILED = "extract_failed"
    INTERNAL = "internal"

class ToolError(Exception):  code: ErrorCode; message: str; retryable: bool; correlation_id: str

class SourceStatus(BaseModel):          # core/envelope.py
    source: str
    state: Literal["ok","empty","timeout","rate_limited","error","unconfigured",
                   "disabled","skipped_unhealthy","budget_exhausted","not_needed"]
    count: int = 0; latency_ms: int | None = None; retry_after_ms: int | None = None
    error_code: ErrorCode | None = None

class Untrusted(BaseModel):  untrusted: Literal[True] = True; source: str; content: str

class ToolResult(BaseModel, Generic[T]):
    data: T; source_status: list[SourceStatus] = []; warnings: list[str] = []
    next_cursor: str | None = None; truncated: bool = False
```

- `budget_exhausted` replaces `skipped_budget` (SRCH-FR-27). A source whose budget or daily cap is spent is selected and reported `budget_exhausted` without a call; a `web` source that the fallback chain did not need is reported `not_needed` (SPEC 5, 11.1; HLTH-FR-12). The states are part of the contract file. The earlier `Literal` in `core/envelope.py` still lists `skipped_budget`; the implementer changes it, and [LLD-sources](LLD-sources-v2.md) and [LLD-search](LLD-search-v2.md), which quote this block, follow.
- `HttpError` lives in `core/errors.py` and the `correlation_id` `ContextVar` in `core/context.py` (both M0-03), so neither the platform nor the MCP layer needs to import the other. The client raises `HttpError(code: ErrorCode, status: int | None, retry_after_ms: int | None, detail: str | None)` (SPEC-v2 3.3).
- Fetched text is returned only as `Untrusted` (PLAT-FR-25; PLAT-33). The `read`, `search_cache` and `get_work` tools wrap their text this way (SEC-22, held by the search and cache LLDs).

### 2.2 HTTP ports (SPEC-v2 3.3)

Policies, credentials and telemetry are injected, so the HTTP layer does not depend on the source layer:

```python
class PolicyResolver(Protocol):
    def policy(self, source: str) -> SourcePolicy: ...            # core/specs.py (LLD-sources 2.2)
class CredentialResolver(Protocol):
    def secret_for(self, source: str) -> Secret | None: ...
class CallSink(Protocol):
    def record(self, call: CallRecord) -> None: ...               # non-blocking; buffered

class HttpPort(Protocol):
    async def get_json(self, url: str, *, source: str, params: Mapping[str, str] | None = None,
                       headers: Mapping[str, str] | None = None, max_bytes: int | None = None,
                       auth: AuthUse = AuthUse.SPEC) -> JsonValue: ...
    async def post_json(self, url: str, *, source: str, json: JsonValue, ...) -> JsonValue: ...
    async def get_text(self, url: str, *, source: str, ...) -> TextResponse: ...

class HttpClient(HttpPort):
    def __init__(self, policies: PolicyResolver, credentials: CredentialResolver, sink: CallSink,
                 clock: Clock, sleeper: Sleeper, contact_email: str | None, transport: httpx.AsyncBaseTransport | None = None): ...
```

`SourcePolicy`, `AuthSpec`, `RateSpec`, `Clock`, `Sleeper`, `AuthUse`, `TextResponse`, `DownloadedFile` and `CallRecord` are defined in SPEC-v2 4 (`core/specs.py`, `core/models.py`), whose design [LLD-sources](LLD-sources-v2.md) 2.1, 2.2 and 3.1 holds; PLAT-6 checks that they validate (9).

### 2.3 MCP transport and the composition root (SPEC-v2 7.4)

- `build_mcp(services)` creates a **new** `FastMCP` for each app. It is configured with `streamable_http_path="/"`, `stateless_http=True` and `json_response=True`, and the SDK's `TransportSecuritySettings` allow only the loopback hosts and origins (PLAT-FR-3).
- `build_app(settings, *, secrets: SecretProvider | None = None, transport: httpx.AsyncBaseTransport | None = None, clock: Clock | None = None, sleeper: Sleeper | None = None, adapters: Iterable[tuple[SourceSpec, type[SourceAdapter]]] | None = None, launchctl: LaunchctlPort | None = None)` mounts it at `/mcp` and runs `mcp.session_manager.run()` inside the Starlette lifespan. The keyword arguments are the test seams; the daemon passes none of them and gets the real Keychain, network, clock and discovered adapters. It installs no signal handler (5.10).
- `build_app` puts `app.state.reload_credentials`, an async function that re-reads the secrets (5.10), where the UI action "Reload credentials" ([LLD-ui](LLD-ui-v2.md)) and the `SIGHUP` handler in `daemon.py` both call it.
- Stateless HTTP means a daemon restart never invalidates a client session. If the shim gets a 404 or 400 for a session, it replays `initialize` once anyway (PLAT-77).

`app.py` builds the Starlette app and mounts `/mcp`, `/ui`, `/healthz`, `/readyz` and `/api` (SPEC-v2 1). Every MCP tool carries `@tool_boundary` (5.6). Tool annotations (PLAT-FR-26; PLAT-60), argument bounds (PLAT-FR-31) and the server instructions (PLAT-61) are part of the tool catalog in SPEC-v2 7.2 and 7.3, which the search component's LLD holds ([LLD-search](LLD-search-v2.md) 2.1, 2.3); the file ownership is in section 1.

### 2.4 CLI (SPEC-v2 12.1)

Scripts: `research-mcp = research_mcp.cli:main` and `research-mcpd = research_mcp.daemon:main`.

| Command | Purpose |
|---|---|
| `serve` | Run the daemon in the foreground. |
| `stdio` | The stdio shim for MCP clients. |
| `doctor [--json] [--notify] [--quick] [--liveness]` | Run health checks (see [LLD-health](LLD-health-v2.md) 5). |
| `ui [--path P]` | Open the UI with a one-time login. |
| `sources [check --live [--id] [--refresh-fixtures]]` | Source inventory and live checks. |
| `config get\|set <key> [value]` | Read or change config. |
| `install [--print-client-config]` | Install the launchd jobs and print client config. |
| `upgrade` | Upgrade with rollback (5.9). |
| `secrets list\|import [--dry-run]\|scrub-client-configs\|rotate-token` | Manage Keychain items. |
| `import-legacy <path> [--dry-run] [--mode]` | Import the v1 corpus (9.6). |

- The ten commands above are the platform CLI that PLAT-FR-50 and PLAT-80 name (PRD-platform v4). `sources --markdown` is removed: the inventory is generated by `tools/gen_inventory.py` (SRC-FR-25).
- `archive reindex [--dry-run]` is a command of the cache component (CACHE-FR-51; [LLD-cache](LLD-cache-v2.md) 5), registered by that component's work unit with the same command table. It is not a platform command, so PRD-platform v4 does not name it, and it does appear in `--help`. PLAT-80 checks that the ten names above are listed, so an eleventh listed command does not fail it.
- `secrets list` prints names, fingerprints and states only. `secrets rotate-token` is the only way the daemon token changes (PLAT-FR-59; 4.5); no UI page or MCP tool rotates it.
- `config set` validates the whole resulting settings model before it writes `config.toml`, so a value that fails validation (for example a placeholder `contact.email`, a non-loopback `server.host` or a non-Keychain `server.token`) is never saved (PLAT-8, PLAT-10, PLAT-11).

### 2.5 launchd templates (SPEC-v2 12.2)

**Templates** in `src/research_mcp/packaging/launchd/` (package data):

| Template | Runs | Schedule and options |
|---|---|---|
| `local.research-mcpd.plist.template` | `__VENV__/bin/research-mcpd` | `RunAtLoad` true, `KeepAlive` true, `ThrottleInterval` 30, `ProcessType` Background, `StandardErrorPath` `__LOGS__/daemon.err.log` |
| `local.research-mcp-doctor.plist.template` | `research-mcp doctor --notify` | `StartCalendarInterval` Hour 8 Minute 52 |
| `local.research-mcp-watchdog.plist.template` | `research-mcp doctor --liveness --notify` | `StartInterval` 900 |

The plists hold no secret and no environment variable (PLAT-81). `__VENV__`, `__LOGS__` and `__HOME__` are the only placeholders; install fails if any `__...__` remains after filling.

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

This version adds no table, column or migration. The two settings keys it adds (7.1) are configuration, not schema.

### 3.1 Stores and migrations (SPEC-v2 3.5; PLAT-FR-5, PLAT-FR-56)

- `Database(path)` holds one `aiosqlite` connection for writes, serialized through an `asyncio.Lock`, and a small pool for reads. Pragmas: `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`, `synchronous=NORMAL` (PLAT-52).
- `Migrator` applies `migrations/<db>/NNNN_*.sql` in order, at daemon start (PLAT-FR-56).
  - Each script runs inside an explicit `BEGIN IMMEDIATE` and `COMMIT` that the Migrator issues itself. It never uses `executescript`, which commits implicitly (PLAT-50).
  - It sets `PRAGMA user_version` and refuses to open a database whose `user_version` is newer than the newest migration (PLAT-51); the daemon then does not start.
  - At start it asserts `sqlite3.sqlite_version_info >= (3, 37, 0)`.
- Migration `.sql` files ship as package data. M0-01 configures this in `pyproject.toml`.
- `StateStore` and `CacheStore` expose typed methods only. No SQL appears outside `platform/stores.py` and the `services/*` repositories (SEC-INV-8, 4.7). Methods M0 needs (all defined in M0-08):
  - `StateStore.record_call(call)` (buffered) and `flush()`;
  - `job_insert(job)`, `job_update(job_id, **fields)`, `job_get(job_id)`, `job_list(state=None)`;
  - `schedule_get(job)`, `schedule_set(job, last_run_at, next_due_at)`;
  - `source_health_get(source)`, `source_health_list()`, `source_health_put(row)`;
  - `CacheStore.outbox_drain(limit) -> list[OutboxRow]` (the rest of `CacheStore` arrives in M2 as `services/*` repositories).
- **Cross-database events.** `documents.decided_*` in `cache.db` is authoritative. Each lifecycle transition also writes a row to `cache.db.outbox` in the same transaction. A drainer copies outbox rows to `state.db.review_events` and deletes them, so neither database needs a transaction that spans both. (This is the only place a stored event is removed from `cache.db` outside purge; the row is a transfer queue, and the event log itself lives in `state.db`.)

The first migration of each database is `platform/migrations/state/0001_init.sql` and `platform/migrations/cache/0001_init.sql` (SPEC-v2 1). Their tables are specified in SPEC-v2 8.1 (`cache.db`) and 10.1 (`state.db`), which the [cache](LLD-cache-v2.md) and [health](LLD-health-v2.md) LLDs hold; PLAT-53 checks the created schemas from the stores side.

### 3.2 Data stores and locations (SPEC 10)

| Store | Location | Owns | Backed up |
|---|---|---|---|
| `state.db` (SQLite, WAL) | `~/Library/Application Support/research-mcp/` | Credential metadata, source health, call telemetry and rollups, searches, jobs, schedule runs, notifications, review batches and a copy of review events | Nightly, the last 7 kept |
| `cache.db` (SQLite, WAL, FTS5, vector BLOBs) | `~/Library/Application Support/research-mcp/cache/` | Works, identifiers, source records, documents and lifecycle (including pins, decisions and archive paths), files, extractions, chunks, FTS, embeddings, collections, outbox | Nightly, the last 7 kept |
| Files | `~/Library/Application Support/research-mcp/cache/files/` (by SHA-256) and `trash/` | Cached PDFs and HTML | No (re-fetchable; archived copies live in Drive) |
| Model cache | `~/Library/Caches/research-mcp/models/` | Embedding model files | No (re-downloadable) |
| Archive | Drive sync folder `My Drive/Research Archive/<year>/` | Archived files and sidecars (their text stays in `cache.db`) | By Google Drive; also the source for the archive rebuild job |
| Config | `~/.config/research-mcp/config.toml` | Settings and secret references | Nightly with `state.db` |
| Logs | `~/Library/Logs/research-mcp/` | `research-mcp.jsonl` and `daemon.err.log`, redacted | No; both rotated by size, 5 files of 10 MB (4.3, 5.10; PLAT-FR-40) |
| Secrets | macOS login Keychain, `research-mcp/<NAME>` | Credential values and the daemon token | By Keychain |

Nothing the lifecycle depends on lives in `~/Library/Caches`, which macOS and cleaning tools may purge. Both databases are backed up; only re-fetchable files are not. Directories are created at daemon start with mode `0700` (PLAT-9; SPEC-v2 2).

### 3.3 Backups (PLAT-FR-57)

The service is `BackupService` in `services/backup.py`; the cache component owns the file and the [LLD-cache](LLD-cache-v2.md) 5 holds its detailed design (SPEC 10, 19). This section is the platform requirement it must meet and the keys it reads.

- `BackupService.backup_state()` runs nightly at 03:30 as the job `backup_state` (5.5). It uses the SQLite online backup API to copy `state.db` and `cache.db`, and it copies `config.toml`. Stored files and the trash are not backed up (SPEC 10).
- The copies go to `state_dir/backups/<local date>/`, written to a temporary folder and renamed when complete. The folder is mode `0700` and the files `0600`. A second run on the same day replaces that day's folder.
- **Retention: the last 7 nightly backups** (PLAT-FR-57; owner decision, 2026-10-22). `backup.keep` (default 7) is a count of nightly folders, not days: after a successful backup the service deletes the oldest nightly folders beyond `backup.keep`. A failed backup deletes nothing. Folders named `pre-upgrade-*` are not nightly backups; they are written by `research-mcp upgrade` (5.9) and only the newest one is kept [assumption: the sources give no retention for it].
- **Drive copy (optional).** With `backup.drive_copy = true`, after the local backup is verified (each database copy is opened and passes `PRAGMA integrity_check`), the service copies the day's folder to `Research Archive/_state/<date>/` inside the confirmed archive target (`archive.confirmed_path`; [LLD-cache](LLD-cache-v2.md) 5), then prunes that folder to the same `backup.keep` count. Rules: it never uses the local archive fallback; if the target is unconfirmed or unavailable it skips the copy and logs a warning, and the local backup still counts; it never modifies anything else in the Drive folder. The default is `false`, so no personal data leaves the Mac by this path unless the owner switches it on. This is a security-relevant default; the owner decided on 2026-10-22 to build the copy behind `backup.drive_copy`, default off, with this design (owner decision, 2026-10-22). The service design for this copy goes into the next version of LLD-cache; this LLD defines only the key and the contract. Verified by owner check OC-10 (PLAT-FR-57; test plan v4 3).
- Verified by CACHE-49 (cache component) and owner check OC-10.

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

This section is the platform's security contract for secrets, redaction, credential scoping and local access. The security component's LLD references it rather than restating it. Draft by the `component-designer` at the caller's instruction. Reviewed by `security-reviewer` at Gate 3 (2026-10-23).

### 4.1 Secrets (SPEC-v2 3.1; PLAT-FR-10, PLAT-FR-11, PLAT-FR-15)

```python
@dataclass(frozen=True)
class SecretRef:            # parsed from "keychain:research-mcp/CORE_API_KEY" or "env:NAME"
    backend: Literal["keychain", "env"]
    name: str               # CORE_API_KEY
    service: str            # research-mcp/CORE_API_KEY ("" for env)

@dataclass(frozen=True)
class SecretMeta: name: str; modified_at: datetime | None

class Secret:
    def __init__(self, ref: SecretRef, value: str): ...
    def reveal(self) -> str: ...            # called only in platform/http.py, platform/mcp_client.py and platform/auth.py
    @property
    def fingerprint(self) -> str: ...       # sha256(value)[:8]
    def __repr__(self) -> str: return f"Secret(name={self.ref.name}, fp={self.fingerprint})"
    __str__ = __repr__

class SecretState(StrEnum): OK="ok"; MISSING="missing"; LOCKED="keychain_locked"; ERROR="error"; INVALID="invalid"

class SecretProvider(Protocol):
    def get(self, ref: SecretRef) -> tuple[SecretState, Secret | None]: ...
    def metadata(self, ref: SecretRef) -> SecretMeta | None: ...   # no value
    def set(self, ref: SecretRef, value: str) -> None: ...          # value never in argv

class KeychainProvider:
    def __init__(self, user: str, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run): ...
class FakeProvider: ...      # tests; also records every argv it would have used

class SecretCache:           # what the daemon uses; implements CredentialResolver with a source->names map
    def __init__(self, provider: SecretProvider, refs: Mapping[str, SecretRef], sources: Mapping[str, str] | None = None): ...
    def load(self) -> None: ...
    def get(self, name: str) -> Secret | None: ...
    def state(self, name: str) -> SecretState: ...
    def reload(self) -> list[str]: ...      # names whose fingerprint changed
```

- **`SecretState.INVALID`** (decision 1 of section 10). The credential states of HLTH-FR-20 to HLTH-FR-25 include `invalid`, and HLTH-24 requires a refused Google sign-in refresh to be reported `invalid`. So `SecretState` gains `INVALID = "invalid"`. Only `GoogleAdcProvider` (4.2) returns it. `KeychainProvider` and `FakeProvider` never do. The [health](LLD-health-v2.md) LLD, which quotes `SecretState`, follows in its next version; [LLD-security v2](LLD-security-v2.md) 5.1 already lists the fifth member. The code's `SecretState` still has four members; the implementer adds the fifth.
- **Read:** `/usr/bin/security find-generic-password -s <service> -a <user> -w`, run with a 5 s timeout (SEC-2).
  - Exit 44 (not found) maps to `missing`.
  - Exit 36 or 51, or "User interaction is not allowed", maps to `keychain_locked`.
  - Anything else maps to `error`.
  - stderr text is never logged or returned.
- **Metadata:** the same command without `-w`; only the `mdat` attribute is parsed (SEC-3).
- **Write:** `/usr/bin/security -i` with `add-generic-password -U -s <service> -a <user> -w <value>` written to stdin, so the value never appears in a process argument list (SEC-13; SEC-INV-6). Values are checked for printable characters first, so `security -w` never returns a hex dump.
- **Keychain items:** service `research-mcp/<NAME>`, account `$USER`. The names are:
  - `DAEMON_TOKEN`, `NOTIFY_WEBHOOK_TOKEN`
  - `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `CORE_API_KEY`, `GOOGLE_DEVKNOWLEDGE_API_KEY`, `GITHUB_TOKEN`
  - `ZENODO_TOKEN`, `NCBI_API_KEY`, `NVD_API_KEY`, `ADS_API_TOKEN`, `LENS_API_TOKEN`, `OPENCITATIONS_TOKEN`
  - `BRAVE_SEARCH_API_KEY`, `SERPAPI_API_KEY` (M1). `GOOGLE_DEVKNOWLEDGE_API_KEY` is shared by `google_devknowledge` and `google_pse`, as in v1; each source's `origins` limit where it is sent.
- **Cursor signing key:** HKDF-SHA256 over `DAEMON_TOKEN` with info `research-mcp cursor v1`. No separate secret is stored.
- **ACL behavior:** items written by `/usr/bin/security` trust that binary, so reads by the daemon do not prompt, even after Python upgrades (owner check OC-02).
- **Where `env:` references may be used** (decision 9 of section 10). The parser accepts both forms (PLAT-12), but configuration holds only Keychain references (PLAT-FR-10; NFR-3). `Settings` therefore rejects an `env:` reference in every key that takes a reference, and `server.token` must be a `keychain:` reference; `config set` and `RESEARCH_MCP_*` overrides go through the same validator. `env:` exists only as a code-level backend: tests and CI build `SecretCache` refs with `SecretRef.parse("env:NAME")` against `FakeProvider(environ=...)` or `KeychainProvider.get`, and `SecretProvider.set` refuses an `env:` reference. The daemon and the shim build their refs only from validated settings, so neither ever reads a secret from the environment. The `env:` backend is not part of the production configuration surface.
- **Reload** (PLAT-FR-15): secrets are read once at start and kept in memory; `SecretCache.reload()` re-reads them and returns the names whose fingerprint changed (SEC-4). When a re-read gives `keychain_locked` or `error` for a name that held a good value, the cache keeps the previous `Secret` and reports the new state, so a locked Keychain at reload time does not strip the daemon of working credentials [assumption: no source says; it follows from the single-notification rule for a locked Keychain, HLTH-13]. A `missing` result clears the value. `reload` is called by `app.state.reload_credentials` (5.10).

| Unit | Section | Requirement |
| --- | --- | --- |
| M0-05 | 3.1; AT-PLAT-12, AT-SEC-13 | `SecretRef` MUST validate on construction: the name matches the allowed pattern, and a Keychain reference's service is exactly `research-mcp/<NAME>`. No control character (in particular a newline) may reach the `security -i` script. `FakeProvider.metadata` MUST behave like `KeychainProvider.metadata` (no metadata for `env:` references). |

(SPEC-v2 0.6)

### 4.2 Google sign-in, M1 (SPEC-v2 3.1.1; SRC-FR-23, SEC-27, SEC-INV-11)

`vertex_search` does not use a Keychain item. `SecretRef` gains the backend `gcloud_adc` (reference text `gcloud_adc:GOOGLE_SIGNIN`), resolved by `platform/google_adc.py`:

```python
class GoogleAdcProvider:                     # implements SecretProvider for backend "gcloud_adc"; extra gcp
    def __init__(self, loader: Callable[[], tuple[Credentials, str | None]] = default_loader,
                 sink: CallSink | None = None, clock: Clock = SYSTEM_CLOCK): ...
    def get(self, ref: SecretRef) -> tuple[SecretState, Secret | None]: ...   # cached token; refresh when < 5 min left
    def metadata(self, ref: SecretRef) -> SecretMeta | None: ...              # account email, token expiry; no token
    def set(self, ref: SecretRef, value: str) -> None: raise NotImplementedError   # gcloud owns the sign-in
```

- `default_loader` calls `google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])`. Loading and refreshing are blocking, so the daemon calls them through `anyio.to_thread.run_sync`, never on the event loop.
- `DefaultCredentialsError` maps to `missing`; `RefreshError` (for example `invalid_grant`, reauthentication required) maps to `SecretState.INVALID` (4.1), which the health component shows as the credential state `invalid` (HLTH-FR-25; HLTH-24). The exception text is never logged or returned.
- The refresh request goes from `google-auth` to `oauth2.googleapis.com` only; the provider records it as a `CallRecord` with `source="google_signin"`.
- The access token is wrapped in `Secret` (name `GOOGLE_SIGNIN`), held in memory, and revealed only by `platform/http.py` for origins in the Vertex spec (`https://discoveryengine.googleapis.com`), as a bearer token plus `X-Goog-User-Project: <project>`.
- v2's own code never opens, copies or writes the credential file (SEC-INV-11); the `google-auth` library is the only reader. The loader is injected so SEC-27 can use a fake credential file and then scan the configuration, Application Support and log folders.
- A missing `gcp` extra reports `vertex_search` as `unconfigured` with the install command (PLAT-13).

### 4.3 Redaction and logging (SPEC-v2 3.2; PLAT-FR-13, PLAT-FR-40, PLAT-FR-41, PLAT-FR-42)

- `Redactor` holds the set of revealed secret values (registered when loaded or reloaded) and the patterns in PLAT-FR-13. Registered values are never removed for the life of the process, so a rotated-out key stays masked.
  - API: `redact(text) -> str`, plus `RedactingFilter(logging.Filter)`, which rewrites `record.msg`, `record.args` and the exception text.
- `configure_logging(settings)` is called only by `daemon.py` and `cli.py`.
  - It attaches `RedactingFilter` to **every handler**, not to a logger, so records propagated from child and third-party loggers are covered (SEC-5).
  - It sets the `httpx`, `httpcore`, `uvicorn.access` and `mcp` loggers to `WARNING` (SEC-14).
  - Handlers:
    - `RotatingFileHandler(log_dir/research-mcp.jsonl, maxBytes=10 MB, backupCount=4)` with a JSON formatter;
    - `StreamHandler(stderr)` at `WARNING`.
  - **Rotation count** (decision 4 of section 10). PLAT-FR-40 and SPEC 10 say "5 files of 10 MB" (owner decision, 2026-10-22). `backupCount=5` would keep six files (the live file plus five), so the handler uses `backupCount=4`: the live file plus four rotated files is five files, at most 50 MB. SPEC-v2 3.2 wrote `(10 MB, 5)`; this value replaces it. PLAT-40 checks the file count.
- **`daemon.err.log`** is the file launchd opens for the daemon's stderr (2.5). `RotatingFileHandler` does not rotate it, because launchd holds the file descriptor. Its rotation is designed in 5.10 (the `log_rotate` job: copy then truncate, 10 MB, 5 files). Because it receives everything written to stderr, including uncaught tracebacks and library prints that never pass a logging handler, `daemon.py` replaces `sys.stderr` with `RedactingStream`, a text stream that passes each write through `Redactor.redact` (SEC-INV-4) [assumption: no source covers the raw stderr path; this closes it].
- **Debug logging** (decision 5 of section 10). Setting `logging.debug` (default `false`; environment override `RESEARCH_MCP_LOGGING__DEBUG`) sets the `research_mcp` logger to `DEBUG` instead of `INFO` and lets the logging layer record the query text of a search in clear text, still through the redactor. It never changes the stderr level (warnings and errors only), the redaction or the field list. The setting is read at daemon start; changing it takes a restart.
- **Query text with debug off** (PLAT-FR-42; PLAT-42): the log fields `query_hash` and `query_len` replace the text. `query_hash` is `sha256(unicodedata.normalize("NFC", text).casefold())` as lowercase hex, truncated to the first 16 characters; `query_len` is the length of the NFC-normalized text in characters. The function is `platform.logging.query_hash(text) -> str`; the search component stores the same value in `state.db.searches.query_hash` ([LLD-health](LLD-health-v2.md) 3, [LLD-search](LLD-search-v2.md) 5.4), so a log line and a telemetry row can be matched. Casefolding and NFC make equal queries hash equal. The hash is not salted: the owner is the only reader and the matching across logs and telemetry is the purpose. The sources name no algorithm, so this is a design choice for the owner to confirm at Gate 3; it changes a stored value's format only for rows not yet written (no search is recorded before M1).
- Log record fields are listed in PLAT-FR-41. `correlation_id` comes from a `contextvars.ContextVar` set per tool call and per job.

### 4.4 Credential scoping in the HTTP client (SPEC-v2 3.3; PLAT-FR-12)

- **Hosts:** a request whose host is not in `policy.hosts` fails with `blocked_by_policy` (PLAT-36).
- **Auth:**
  - The secret comes from `CredentialResolver`.
  - It is attached only when the request origin is in `policy.auth.origins` (SEC-8; SEC-INV-5). The downloader (5.4) has no `CredentialResolver`, so a download never carries a credential.
  - Placement is `header` (name from the spec), `bearer`, or `query` (parameter name from the spec).
  - Query placement is used only where the API offers nothing else (SerpAPI), and then the URL is never logged and the redactor masks the parameter (SEC-9).
- **Errors:** the message text is generic; details go to the log through the redactor (SEC-10).

### 4.5 Local access: loopback, the daemon token and endpoints (PLAT-FR-3, PLAT-FR-59)

- `server.host` defaults to `127.0.0.1`; validation rejects any non-loopback value (PLAT-10). `server.token` is `keychain:research-mcp/DAEMON_TOKEN`, the bearer for the shim and API (SPEC-v2 2); it must be a Keychain reference (4.1).
- `daemon.py` runs `research-mcpd`: settings, then `build_app`, then uvicorn on `127.0.0.1` with `access_log` off (SPEC-v2 1). Immediately before binding, `daemon.py` asserts again that the host is loopback, so a settings object built without validation still cannot bind elsewhere (PLAT-71).
- `platform/auth.py` holds the daemon token: mint, compare (`hmac.compare_digest` on the encoded bytes), the HKDF cursor key, and UI one-time tokens (SPEC-v2 1). It is also the module through which the shim reveals the token (`bearer_header(secret)`), so `Secret.reveal` stays confined to `http.py`, `mcp_client.py` and `auth.py` (PLAT-FR-11).
- **The auth gate** (owner decision, 2026-10-22). `BearerAuthMiddleware` is renamed `AuthGate`: one deny-by-default ASGI gate in `app.py` in front of every mount. It classifies each path ([LLD-security v2](LLD-security-v2.md) 4.3 E3), checks the bearer token (SEC-11) and runs the Host and Origin check (SEC-12) on all paths. A request without a valid credential for its class gets 401. The UI session check and the CSRF check stay in `ui/` ([LLD-ui](LLD-ui-v2.md)); `/api/status` accepts a bearer token or a UI session, and `/ui/login` accepts a one-time token. Unauthenticated surfaces are `/healthz`, `/readyz` and `/ui/login` (gated by its one-time token), and `/ui/static/*` needs a UI session (NFR-7; SEC-INV-2). PRD-security v3 records this wording (drafted separately); PRD-v7 NFR-7 may need the same change. The gate reads the token from `SecretCache` on each request, so a reload changes which token is valid.
- **Tool results** (owner decision, 2026-10-22). `@tool_boundary` passes every string in a successful tool result through `Redactor.redact` (LLD-security v2 E39). The check is SEC-28, proposed in PRD-security v3 (4.7, 9).
- `build_mcp` configures the SDK's `TransportSecuritySettings` to allow only the loopback hosts and origins (SPEC-v2 7.4; SEC-12).
- **Token lifecycle** (PLAT-FR-59; owner decision, 2026-10-22). `research-mcp install` generates `DAEMON_TOKEN` through `SecretProvider.set` if it is absent. `research-mcp secrets rotate-token` is the only rotation path (no UI action, no MCP tool; SPEC 8, 9, 12):
  1. mint a new token, `secrets.token_urlsafe(32)`;
  2. write it through `SecretProvider.set` (stdin, never argv; SEC-13);
  3. ask launchd to send `SIGHUP` to the daemon (`launchctl kill SIGHUP gui/$UID/local.research-mcpd`), which runs the reload (5.10) so the daemon holds the new token and the old one stops working (PLAT-83);
  4. print the fingerprint, never the value.
  If the daemon is not running, step 3 is skipped; the next start reads the new token. Open shims hold the old token: on a 401 a shim re-reads the Keychain once and retries (5.7). The cursor key is derived from the token, so outstanding cursors become invalid and fail with `invalid_argument`; this is the intended effect.
- Endpoint authentication (SPEC-v2 10.5, held by the [health LLD](LLD-health-v2.md)):

| Endpoint | Auth | Returns |
|---|---|---|
| `/healthz` | none | `{"status":"ok","version":"3.x.y"}` |
| `/readyz` | none | Ok when the stores are open, the scheduler is running and the Keychain is readable; 503 otherwise (HLTH-FR-43) |
| `/api/status` | bearer token or a UI session | JSON of sources, credential metadata, quotas, jobs, cache stats, disk, the archive target and the last 20 notifications |

The UI session, CSRF and Host checks are specified in SPEC-v2 11 and held by the [UI LLD](LLD-ui-v2.md).

### 4.6 Local files and destructive actions (PLAT-FR-20, PLAT-FR-21, PLAT-FR-22, PLAT-FR-27)

- The downloader writes only under `data_dir` (`tmp/` then `files/`), and the model never chooses a path (5.4; SPEC 9; SEC-25).
- There is no SQL tool (PLAT-FR-20; SEC-21), no caller-chosen path, and files are read only under the cache root (PLAT-FR-21; CACHE-11). Platform code exposes no raw SQL entry point to tools (3.1).
- **DuckDB** (decision 8 of section 10). ADR 0011 keeps SQLite as the only store and says DuckDB is not used, and PLAT-4 requires the base dependencies to exclude `duckdb`. So PLAT-FR-22, which applies "if DuckDB is used internally", is satisfied by not using it: no module imports `duckdb`, and no extra declares it. PLAT-4 and SEC-21 stay as the checks (SEC-21 also asserts that no `duckdb` import exists in `src/`). If a later change adds DuckDB, its next LLD version must configure `enable_external_access=false`, `allowed_directories` limited to the cache root, `autoinstall_known_extensions=false`, `autoload_known_extensions=false` and `lock_configuration=true` before the first query, as PLAT-FR-22 requires. This replaces the "if used" wording of v1.
- No hard delete in MCP; annotations mark state-changing tools (PLAT-FR-26, PLAT-FR-27; SEC-20). The tool rules are part of the tool catalog in SPEC-v2 7.2.

SPEC 9 threat rows enforced by this component:

| Threat | Control |
| --- | --- |
| Secret leaks into chat or logs | Keychain (the Google sign-in and the scrub backups excepted, see SPEC 9); `Secret` type; origin-scoped attachment; header placement; one redaction filter on logs, errors, UI and notifications and a redacting stderr stream; errors carry codes, not exception text. |
| Google sign-in token misuse | `gcloud` owns the sign-in; v2 holds only a short-lived access token in memory and attaches it only to `discoveryengine.googleapis.com`. |
| SSRF and hostile downloads | One downloader: https, per-hop host policy, public IPs only with the connection pinned to the checked IP (no second DNS lookup), byte cap, magic bytes, atomic write. |
| Hostile PDFs | Parsing in a separate subprocess per document with a CPU limit, an RSS watchdog, a wall-clock timeout and a page cap; a crash affects only that document. |
| Other local processes call the daemon | Loopback only, bearer token, Host and Origin checks; UI session cookie plus CSRF. MCP clients reach the daemon only through the stdio shim, which reads the token from the Keychain (5.7). Same-user processes sit inside trust boundary 2 (accepted residual risk, SPEC 9; owner decision, 2026-10-22). |
| Daemon token exposed | Rotation only from the CLI, new value through `security -i` on stdin (4.5). |
| Supply chain | Lock file, weekly dependency audit, SHA-pinned CI actions, secret scan (5.8). |

### 4.7 Invariant enforcement points in platform code (SEC-INV-1 to SEC-INV-11)

The Security component owns the invariants (PRD-security v3 1.6); this table lists where platform code enforces each, and the criteria that check it. The enforcement points of other components are in their LLDs and in [LLD-security v2](LLD-security-v2.md) 4.3 and 4.4.

| Invariant | Platform enforcement point | Criteria |
| --- | --- | --- |
| SEC-INV-1 Listen on a non-loopback address | `ServerSettings.host` validator; the second assertion in `daemon.py` before binding (4.5); `TransportSecuritySettings` host list | SEC-12; PLAT-10, PLAT-71 |
| SEC-INV-2 Serve a request with neither bearer token nor UI session, except `/healthz`, `/readyz` and `/ui/login` (one-time token) | `AuthGate` in `app.py` in front of every mount; the unauthenticated list is exactly those three paths (4.5) | SEC-11, SEC-12; PLAT-70 |
| SEC-INV-3 Keep a secret at rest outside the Keychain | Settings validators (references only; `server.token` Keychain only; `notify.webhook_url` without credentials); `install`, startup and reload write nothing secret to `config.toml`, the Application Support folder or the logs; the rotated token goes through `security -i`; `state.db` credential rows are metadata (HLTH-43) | SEC-24, SEC-2, SEC-3; PLAT-81 |
| SEC-INV-4 Put a secret in any output | `Secret` text form; `Redactor` on every handler and on the redacting stderr stream; generic `HttpError` and `ToolError` messages; `@tool_boundary` maps unknown exceptions to `internal` and redacts every string in a successful result (5.6) | SEC-1, SEC-5, SEC-6, SEC-7, SEC-9, SEC-10, SEC-14, SEC-28 (proposed in PRD-security v3); PLAT-62 |
| SEC-INV-5 Send a credential outside its origin | `policy.auth.origins` check in `HttpClient`; the downloader has no credential access | SEC-8, SEC-9; PLAT-36 |
| SEC-INV-6 Pass a secret in a process argument list | `KeychainProvider.set` writes the script to `security -i` on stdin; no other subprocess call (`launchctl`, `uv`, `terminal-notifier`, `osascript`) takes a secret; `FakeProvider` records argv | SEC-13 |
| SEC-INV-7 Read a local file beyond the cache, or accept a caller-chosen path | The downloader writes only under `data_dir`; no tool takes a path; `PathSettings` normalizes paths | SEC-25, SEC-21; CACHE-11, CACHE-1 |
| SEC-INV-8 Expose a free-form SQL tool | Stores expose typed methods only (3.1); no SQL tool is registered | SEC-21 |
| SEC-INV-9 Hard-delete through any MCP tool | No platform store method for deletion is reachable from a tool; `destructiveHint` on every state-changing tool (PLAT-60) | SEC-20 |
| SEC-INV-10 Give an MCP client the daemon token | The shim reads the token from the Keychain only and clients launch it (5.7); `install --print-client-config` prints `research-mcp stdio` entries with no token and no URL; `server.token` cannot be an `env:` reference | SEC-26; PLAT-82 |
| SEC-INV-11 Copy the owner's Google sign-in | `GoogleAdcProvider.set` raises; the loader runs in memory; no platform code opens the credential file (4.2) | SEC-27 |

**SEC-24 (no registered secret at rest after `install`, a daemon start and a reload).** Enforcement is by construction (the validators and write paths above) and the check is an integration test: with `FakeProvider` values registered, run `install`, build and start the app, run `reload_credentials`, then scan every file under the configuration folder and the Application Support folder, including `config.toml` and `state.db`, for the registered values.

**SEC-26 (the shim reads the daemon token only from the Keychain).** The shim builds a `KeychainProvider` and parses `settings.server.token`, which validation guarantees is a `keychain:` reference. It reads no `DAEMON_TOKEN` or similar from the environment, no command line argument and no file. The test starts the shim with a decoy token in the environment and a `FakeProvider`, and asserts that the bearer sent is the Keychain value and that the provider recorded the read.

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

### 5.1 Conventions and layout (SPEC-v2 1; SPEC 15)

- Python 3.12 (uv-managed interpreter, which bundles a current SQLite), `uv`, `src/` layout, package `research_mcp`, version `3.0.0` (PLAT-FR-50, PLAT-FR-58; PLAT-1).
- Typing: mypy strict on `src/`; Pydantic v2 models for everything that crosses a module boundary or the MCP boundary.
- Async: `anyio`; HTTP with `httpx.AsyncClient`; SQLite with `aiosqlite` through the store classes only.
- Time: UTC everywhere (`datetime` with `tzinfo=UTC`), stored as ISO 8601 text; the scheduler converts to local time for 09:00 and quiet hours.
- IDs: ULIDs for internal rows (`works.work_id`, `documents.doc_id`, jobs, batches).
- Tests: pytest with `--import-mode=importlib`; test folders have no `__init__.py`; shared test helpers live in the package `research_mcp.testing` so tests import them by absolute name.
- No em dashes or en dashes in code comments, docs or UI strings (NFR-11).

```
src/research_mcp/
  __init__.py  version.py
  cli.py                      # research-mcp: serve | stdio | doctor | ui | sources | config | install | upgrade | secrets | import-legacy | archive (cache)
  daemon.py                   # research-mcpd entry: settings -> logging -> build_app -> uvicorn on 127.0.0.1 (access_log off); SIGHUP receiver
  app.py                      # build_app(settings) -> Starlette app (mounts /mcp, /ui, /healthz, /readyz, /api)
  shim.py                     # stdio <-> streamable HTTP relay
  settings.py                 # Settings, SourceSettings, paths
  core/      ids.py models.py specs.py errors.py context.py envelope.py budget.py timeutil.py
  platform/
    secrets.py                # SecretRef, Secret, SecretMeta, SecretProvider, KeychainProvider, FakeProvider, SecretCache
    redact.py                 # Redactor (handler filter + str API), RedactingStream
    logging.py                # configure_logging(settings), query_hash, rotate_stderr_log
    http.py                   # HttpPort, HttpClient (httpx), CredentialResolver, CallSink, PolicyResolver, build_user_agent
    google_adc.py             # GoogleAdcProvider: Google sign-in access tokens via google-auth (M1, extra gcp)
    auth.py                   # daemon token: mint, compare (hmac.compare_digest), HKDF cursor key, UI one-time tokens, bearer_header
    download.py               # DownloadPolicy, Downloader, Resolver, PinnedTransport
    ratelimit.py              # TokenBucket, ConcurrencyGate, RateRegistry
    mcp_client.py             # McpUpstreamPort (MCP client over the shared HTTP client)
    stores.py                 # Database (aiosqlite), Migrator, StateStore, CacheStore
    migrations/state/0001_init.sql ...   migrations/cache/0001_init.sql ...
    workers.py                # WorkerRunner (one subprocess per task) and worker_entry
    jobs.py                   # JobService, Job, JobKind
    scheduler.py              # Scheduler (wall-clock, catches up missed runs)
  sources/                    # sources component
  services/                   # search, cache, health and migration components
  mcp_app/
    server.py                 # build_mcp(services) -> FastMCP; instructions text; @tool_boundary
    ...
  ui/                         # UI component
  testing/                    # importable fakes for tests: clock.py adapters.py launchctl.py notifier.py
  packaging/launchd/          # *.plist.template (package data, so `research-mcp install` finds them in an installed wheel)
tests/
  unit/ ...   integration/ (platform criteria at the integration level, 9)
  sources/<id>/fixtures/ + test_<id>.py   sources/test_conformance.py
  services/   contract/ (in-memory MCP client)   ui/   security/   live/ (opt-in)
tools/ci.sh  tools/gen_inventory.py  tools/gen_test_plan.py  tools/gen_m0_plan.py
```

The `sources/`, `services/`, `mcp_app/` and `ui/` subtrees are abridged here; SPEC-v2 1 lists them in full.

| Unit | Section | Requirement |
| --- | --- | --- |
| M0-01 | 1; AT-PLAT-03 | Import side effects MUST be attributed to `research_mcp` when any frame of the stack belongs to it, not only the innermost frame; a dependency doing I/O on behalf of a `research_mcp` import (for example settings construction reading the environment at import time) counts. Include that case as a regression test. |

(SPEC-v2 0.6)

### 5.2 Layers and the composition root (SPEC 3; PLAT-FR-4, PLAT-FR-5)

The daemon is one Python process built in layers. Each layer depends only on the layers below it.

```
 transport    mcp_app (tools, resources, prompts)      ui (pages)      http_api (status)
                 |                                        |                 |
 services     federation   works   cache   health   notify   jobs   scheduler
                 |            |       |       |        |
 sources      registry -> adapters (one module per source; SourceSpec)
                 |
 platform     http client (rate limits, retries, redaction, telemetry)   secrets (Keychain)
              stores (state.db, cache.db; migrations)   workers (subprocess per task)   settings   logging
 core         ids, models, errors, envelope, time (no I/O)
```

- `core` has no I/O and no third-party service dependencies.
- Adapters translate only; they never retry, sleep, read secrets or write files (ADR 0006).
- Tools are thin: validate arguments, call one service, wrap the result in the envelope.
- One composition root, `build_app(settings)`, creates everything inside a lifespan and closes it in reverse order (PLAT-70). Nothing happens at import (PLAT-3).
- Network I/O is async; CPU-heavy work (PDF parsing, chunking, embedding) runs in one short-lived subprocess per task, killed on timeout or memory limit; SQLite access runs in a thread with one writer per database (PLAT-75).

### 5.3 HTTP client (SPEC-v2 3.3; PLAT-FR-33)

- **Client:** one `httpx.AsyncClient` per daemon. HTTP/2 is on. Connection limits are 50 in total and 8 per host.
- **User agent** (decision 10 of section 10; PLAT-39, NFR-8). `build_user_agent(version, contact_email)` returns `research-mcp/<major>.<minor> (+mailto:<contact>)` when `contact.email` is set. When it is unset the client sends `research-mcp/<major>.<minor>` with no `mailto` part and never invents or defaults an address. A placeholder address cannot reach the client, because settings validation rejects it and the daemon does not start (PLAT-11; SRC-FR-24; SPEC 4). With no contact, only the `needs_contact` sources are `unconfigured`, so no request that needs the contact is made without one. The version comes from `research_mcp.version.__version__`.
- **Hosts and auth:** 4.4.
- **Rate limits:** each source gets a `TokenBucket(rate, burst)` and a `ConcurrencyGate(n)` from `policy.rate`. These are kept in one `RateRegistry` for the daemon, so they are global across clients (PLAT-37). arXiv runs at 1 request per 3 s, burst 1, concurrency 1.
- **Retries:** 6.1.
- **Size:** responses are streamed; passing `max_bytes` (default from the policy) aborts the call with `too_large` before the whole body is read (PLAT-38).
- **Telemetry:** every attempt produces a `CallRecord` for the `CallSink`. In the daemon the sink is `StateStore.record_call`, flushed every second (PLAT-39).

### 5.4 Downloader (SPEC-v2 3.4; CACHE-1, CACHE-2)

`Downloader(resolver: Resolver, policy: DownloadPolicy, ...)`. The algorithm is a port of v1's `security.download_pdf_atomic`, with DNS pinning added:

1. Require `https`. Resolve the host through the injected `Resolver` (the system resolver in the daemon, a fake in tests). Reject private, loopback, link-local, multicast and reserved addresses, for both IPv4 and IPv6.
2. Connect through `PinnedTransport` to the **checked IP**, with SNI and the `Host` header set to the hostname. httpx never resolves the name a second time, which closes the DNS-rebinding gap.
3. Set `follow_redirects=False` and follow up to 5 redirects by hand. On every hop, repeat steps 1 and 2 and re-check the scheme and the host policy (`policy.allowed_hosts`, or `public_any`).
4. Stream into `data_dir/tmp/<ulid>.part` with a byte cap. Check `Content-Type` against `policy.media_types`, and check the first bytes: `%PDF-` for PDF; for HTML, `<` after any whitespace.
5. Run `fsync`, compute SHA-256, and move the file atomically to `data_dir/files/<sha256[:2]>/<sha256>.<ext>`. If that file already exists, reuse it.
6. Return `DownloadedFile` (LLD-sources 3.1).

**File deletion rule:** a stored file is removed only when no `files` row with the same `sha256` belongs to a document in a non-terminal state (`cached`, `pinned`, `expiring`, `kept`), and no discard of it is still within its trash period.

The downloader's criteria (CACHE-1, CACHE-2 in M0-07) belong to the cache component.

### 5.5 Workers, jobs and the scheduler (SPEC-v2 3.6; PLAT-FR-5, PLAT-FR-6)

`WorkerRunner` runs every CPU-heavy task in its own subprocess. `ProcessPoolExecutor` is not used, because on macOS it cannot enforce memory limits or kill a running task.

- The task is launched with `anyio.open_process([python, "-m", "research_mcp.platform.workers", <task>])`. Input goes in as JSON on stdin; the result comes back as JSON on stdout.
- In the child, `RLIMIT_CPU` is 120 s. `RLIMIT_AS` is not relied on, because macOS does not enforce it.
- The parent enforces a 180 s wall clock and samples the child's RSS every second with `psutil`. Past 2 GB, or at the timeout, it sends SIGKILL.
- A crash or kill affects only that task, which ends with code `extract_failed`.
- Tasks: `extract_pdf`, `extract_html`, `chunk`, `embed`. At most 2 run at once.

`JobService` provides `submit(kind, params) -> job_id`, `status(job_id)`, `cancel(job_id)` and `list(state)` (PLAT-74).

- Job state lives in `state.db.jobs`.
- Progress is pushed to MCP `Context.report_progress` while the caller waits.
- Resumable job kinds store a cursor.
- A retry from the UI resubmits through `JobService.submit` with the same parameters (UI-FR-13).

`Scheduler` is driven by the wall clock, not by asyncio timers, which stall while the Mac sleeps (PLAT-76).

- Every 60 s it compares the wall clock with each job's next due time.
- A job missed because the Mac was asleep or the daemon was down runs once at start or on wake. It never runs once per missed day.
- Daily schedules:

| Job | Local time |
|---|---|
| `review` | 09:00 |
| `digest` | 08:00 |
| `backup_state` | 03:30 |
| `maintenance_daily` | 04:00 |
| `trash_purge_notice` and `trash_purge` | 10:00 |

- Interval schedules: probes at their own cadence; `disk_sample` every 15 minutes; `outbox_drain` every 5 s; `log_rotate` every 15 minutes (5.10; new in v2, PLAT-FR-40).

`WorkerRunner` arrives in M2 (SPEC-v2 12.4); `JobService` and `Scheduler` are M0-15.

### 5.6 Budget, cursors and the tool boundary (SPEC-v2 3.7; PLAT-FR-14, PLAT-FR-30)

**Budget.** `core.budget.fit(result, limit_bytes)` trims list items from the end, and shortens long text fields to a marker, until the JSON size fits. It then sets `truncated` and keeps the cursor and `source_status` (PLAT-31, PLAT-63).

**Cursors.** Cursors are base64url JSON with an HMAC-SHA256 tag. `core.budget` takes the key as a parameter (the daemon derives it as described in 4.1), so that agents cannot forge cursors (PLAT-34).

**`@tool_boundary`** is defined in `mcp_app/server.py` (M0-14; file owner in section 1). Every MCP tool carries this one decorator. It:

- sets the correlation id;
- turns `ToolError` and `HttpError` into the error result (the shape is in the [contract](../contracts/envelope-and-errors-v1.md));
- maps any other exception to `internal`, logging the traceback through the redactor (PLAT-62);
- applies the budget;
- passes every string in a successful result through `Redactor.redact` (owner decision, 2026-10-22; SEC-28, proposed in PRD-security v3).

| Unit | Section | Requirement |
| --- | --- | --- |
| M0-03 | 3.7, 4; AT-PLAT-31, FR-SRCH-04 | `Budget.fit` MUST keep `FederatedResult.statuses` (one status per source) and MUST fail explicitly when mandatory metadata cannot fit. Its prefix search MUST distinguish "does not validate" from "too large". |

(SPEC-v2 0.6)

### 5.7 Stdio shim (PLAT-FR-2; SEC-INV-10, SEC-26)

`shim.py` relays stdio to streamable HTTP (SPEC-v2 1). **The shim is the only way an MCP client reaches the daemon.** Every client configuration launches `research-mcp stdio`; no client is given the loopback URL or the token (SPEC 2; owner decision, 2026-10-22). `install --print-client-config` prints only entries of that form (PLAT-82).

Algorithm:

1. Build a `KeychainProvider` and read `settings.server.token`. The shim reads the token only from the Keychain (SEC-26; 4.7) and reveals it only through `platform/auth.py`.
2. Probe `GET /readyz`. If the daemon answers, relay.
3. If it does not, ask launchd to start it through `LaunchctlPort` (`kickstart` for a loaded job, `bootstrap` of the installed plist if the job is not loaded; `FakeLaunchctl` in tests), then poll `/readyz` every 0.5 s with the injected `Sleeper` for up to 20 s. Repeat the start request up to 3 times in total (PLAT-73).
4. If the daemon is still not reachable, return one MCP error: the `internal` code, `retryable` true, with the fixed message "The research-mcp daemon is not reachable; run `research-mcp doctor`." (assumption: the sources fix no code or text, only "one clear MCP error").
5. Relay. On a 401, re-read the Keychain token once and retry the request once, which covers a token rotated while the shim ran (4.5); if it fails again, return `auth_failed`.
6. On a 404 or 400 for a session, replay `initialize` once (2.3; PLAT-77).

### 5.8 Packaging and CI (SPEC-v2 12.1; PLAT-FR-50 to PLAT-FR-53)

- **Dependencies** in `pyproject.toml`: `mcp>=1.27,<2`, `httpx[http2]`, `anyio`, `pydantic>=2`, `pydantic-settings`, `aiosqlite`, `uvicorn`, `starlette`, `jinja2`, `selectolax`, `defusedxml`, `python-ulid`, `psutil`, `tomli-w`. No `duckdb` (4.6; PLAT-4).
- **Extras** (PLAT-FR-51): `pdf = ["pymupdf"]`, `embeddings = ["fastembed", "numpy"]` and `macos = ["pyobjc-framework-Cocoa; sys_platform == 'darwin'"]`; from M1, `gcp = ["google-auth"]` (with `google.*` added to the mypy `ignore_missing_imports` overrides). A search-only install needs none of them and imports none of them (PLAT-4, PLAT-13, PLAT-84). PLAT-84 also requires that a missing optional extra for the archive upload check is reported as the upload state `unknown`; that reporting is `ArchiveService.reconcile` in the cache component ([LLD-cache](LLD-cache-v2.md) 5), and the platform side is the declaration and the import guard.
- **Dev group:** `pytest`, `pytest-asyncio`, `pytest-cov`, `respx`, `hypothesis`, `ruff` and `mypy`.
- **`[tool.pytest.ini_options]`:** `addopts = "--import-mode=importlib -m 'not live'"`, `asyncio_mode = "auto"` and `markers = ["live: real upstream calls"]`.
- **`[tool.ruff]`:** `line-length = 100`, `target-version = "py312"`, `extend-exclude = ["tools/gen_m0_plan.py"]` (a design-time generator, kept outside the code rules); `[tool.ruff.lint] select = ["E","F","I","W","B","UP","SIM","ASYNC","BLE","S","C90"]`; `[tool.ruff.lint.per-file-ignores] "tests/**" = ["S101","S105","S106","S108"]`; `[tool.ruff.lint.mccabe] max-complexity = 12`.
- **`[tool.mypy]`:** `strict = true`, `python_version = "3.12"`, `files = ["src"]`; `[[tool.mypy.overrides]] module = ["fitz.*","fastembed.*","objc.*","Foundation.*","selectolax.*"] ignore_missing_imports = true`.
- **Dev stubs:** `types-defusedxml`, `types-psutil`.
- **Package data:** `research_mcp/platform/migrations/**/*.sql`, `research_mcp/ui/templates/*.html`, `research_mcp/ui/static/*` `research_mcp/packaging/launchd/*.plist.template` and, from M1, `research_mcp/packaging/defaults.toml`.
- **Scripts:** `research-mcp = research_mcp.cli:main` and `research-mcpd = research_mcp.daemon:main`.

`tools/ci.sh` must start with `#!/usr/bin/env bash` and be executable; the ECC gate runs commands without a shell (PLAT-2). It has two modes (PLAT-FR-52).

**`tools/ci.sh --python-only`** runs on every work unit:

1. `uv run ruff check`
2. `uv run ruff format --check`
3. `uv run mypy src`
4. `uv run pytest -q --cov=research_mcp --cov-report=term` (coverage is reported, not gated)
5. Each generator check, run only when its script exists:
   - `uv run python tools/gen_m0_plan.py --check`
   - `uv run python tools/gen_inventory.py --check` (SRC-FR-25)
6. The SDD checks (`node tools/sdd/cli.mjs check`).

**`tools/ci.sh`** with no flag runs at milestone exit and in GitHub Actions. It adds:

- `--cov-fail-under=85`;
- `uv build`;
- `uv run research-mcp --help`, once `research_mcp/cli.py` exists.

| Unit | Section | Requirement |
| --- | --- | --- |
| M0-01 | 12.1; FR-PLAT-53 | The CI workflow MUST run on macOS and Linux with Python 3.12 and 3.13, pin every action by commit SHA, scan for secrets, and run a weekly dependency audit. |

(SPEC-v2 0.6)

### 5.9 launchd, install and upgrade (SPEC-v2 12.2; PLAT-FR-54, PLAT-FR-55, PLAT-FR-59)

The daemon runs under the `local.research-mcpd` LaunchAgent (2.5). Install is `uv tool install` (or a venv) for the package, then `research-mcp install` (SPEC 12).

**`research-mcp install`:**

1. Fills the placeholders and renders the three plists (PLAT-81).
2. Creates the folders, mode `0700`.
3. Generates `DAEMON_TOKEN` through `SecretProvider.set` if it is absent (PLAT-83; the generation and the rotation are in 4.5).
4. Runs the foreground `archive_access` write (9.3); this step is added in M2 with the archive service.
5. Loads the three jobs with `launchctl bootstrap gui/$UID`; a job that is already loaded is first removed with `launchctl bootout`, so a second install is idempotent.
6. Prints the client configs: `research-mcp stdio` entries only (PLAT-82).

**`research-mcp upgrade`** (PLAT-FR-55; decision 11 of section 10). `KeepAlive` restarts a daemon that is merely stopped, so the job must be unloaded before any file changes:

1. Records the current lock file, the installed version and the `uv tool` environment path.
2. Unloads the daemon job with `launchctl bootout gui/$UID/local.research-mcpd`, then waits for the process to exit. It does the same for the watchdog and doctor jobs, so neither fires against a half-replaced environment.
3. Backs up `state.db` and `cache.db` (online backup API) to `state_dir/backups/pre-upgrade-<timestamp>/`, mode `0700`, files `0600`.
4. Runs `uv tool upgrade research-mcp` (or `uv sync` for a source checkout).
5. Loads the three jobs again with `launchctl bootstrap` and waits for `/readyz` for up to 60 s. The daemon runs the migrations at start (PLAT-FR-56); a database newer than the code, or a failing script, stops it from becoming ready.
6. Runs the new environment's `doctor --quick --json` as a subprocess (not an import, because the running upgrade command still holds the old code). `--quick` runs only free probes, so an upgrade spends no metered query (HLTH-FR-21).
7. If the daemon did not become ready or `doctor` exits non-zero (it exits non-zero when a check is `install_critical`, [LLD-health](LLD-health-v2.md) 5.9), the upgrade is failed and rolls back: unload the jobs, reinstall the recorded version (`uv tool install research-mcp==<old>`), restore both databases from step 3, load the jobs and confirm `/readyz`. It prints what failed and exits non-zero. Writes made between step 5 and the rollback are lost with the restore; the window is the length of one start and one doctor run.

Migrations are forward-only; the step 3 backup is what makes rollback possible. PLAT-FR-55 says a failed `doctor` rolls back to the previous environment; restoring the databases with it is required because a migrated database may be newer than the old code (PLAT-51). The sources do not say whether a warning-level `doctor` result also rolls back; only a critical check does (exit code 0 otherwise). Owner check OC-09 forces a `doctor` failure.

### 5.10 Daemon start, credential reload and log rotation (PLAT-FR-15, PLAT-FR-40)

**Start order in `daemon.main`:** (1) load `Settings`, the only place the environment is read; a validation error is printed (redacted, no input echoed) and the process exits non-zero, so a placeholder `contact.email` or a non-loopback host keeps the daemon from starting (PLAT-10, PLAT-11); (2) `create_directories()`; (3) `configure_logging` and replace `sys.stderr` with `RedactingStream` (4.3); (4) assert the host is loopback; (5) build `SecretCache` from validated references, `load()` it and register every value with the `Redactor`; (6) `build_app`, whose lifespan opens the stores and runs the migrations; (7) serve with uvicorn inside a task group that also runs the signal receiver below.

**`reload_credentials`** is `app.state.reload_credentials`, built by `build_app`:

```python
async def reload_credentials() -> list[str]:
    async with reload_lock:                       # one reload at a time
        changed = await anyio.to_thread.run_sync(secret_cache.reload)   # blocking subprocess calls
        for name in changed: redactor.register(secret_cache.get(name))
        await credentials_changed(changed)        # port to the health component: records fingerprint change (HLTH-FR-23)
        return changed                            # names only, never values
```

It is called by the UI action "Reload credentials" and by the `SIGHUP` handler. Only names and fingerprints are logged.

**`SIGHUP`** (decision 6 of section 10). `daemon.py` runs, beside the uvicorn server in the same task group:

```python
async with anyio.open_signal_receiver(signal.SIGHUP) as signals:
    async for _ in signals:
        with contextlib.suppress(Exception):      # a failed reload never stops the daemon
            await app.state.reload_credentials()
```

`build_app` does not install it, so tests that build the app (PLAT-70) do not touch process signals; the handler is tested by calling `reload_credentials` and, separately, by sending `SIGHUP` to a daemon started in a subprocess. A failure inside the handler is logged as a warning without exception text. `SIGHUP` re-reads secrets only (PLAT-FR-15); it does not reload settings, so a settings change needs a restart.

**Log rotation of `daemon.err.log`** (PLAT-FR-40; SPEC 12 hands this to this LLD). launchd opens the file in append mode and keeps the descriptor, so renaming it would leave launchd writing to the renamed file. The `log_rotate` interval job (every 15 minutes, and once at start) calls `rotate_stderr_log(path, max_bytes=10 MB, keep=5)`: if the file is at least 10 MB, shift `daemon.err.log.3` to `.4`, and so on down to the live file, copy the live file to `daemon.err.log.1`, then truncate the live file to zero length. Total: the live file plus four rotated files, five files of at most about 10 MB each, matching the main log. A few lines written between the copy and the truncate can be lost; the structured log has them. The rotated files are written mode `0600`. Rotation failure is logged as a warning and retried at the next run; it never raises.

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

### 6.1 HTTP retries (SPEC-v2 3.3; PLAT-35, PLAT-36)

- **Retries:** up to 3 attempts on 429, 500, 502, 503 and 504, and on connection errors. If every attempt gets a 429, the call fails with `rate_limited` and the last `retry_after_ms`.
  - The delay is `Retry-After` when present. A delay over 60 s is not waited for; the call fails with `rate_limited` and `retry_after_ms`.
  - Without `Retry-After`, the delay is exponential from a 0.5 s base, with full jitter.
  - Other 4xx responses are not retried.
  - All waiting goes through the injected `Sleeper`, so tests never sleep for real.
- **Errors:** the client raises `HttpError(code: ErrorCode, status: int | None, retry_after_ms: int | None, detail: str | None)`, defined in `core/errors.py`. Before the generic mapping, a non-2xx response is passed to `policy.error_classifier` when the source declares one (for example OpenAlex maps an "Insufficient budget" 429 to `budget_exhausted` with `detail="daily budget"`). The message text is generic; details go to the log through the redactor (SEC-10).
- **Status to code** (generic mapping; the 4xx rows other than 401, 403, 404 and 429 are an assumption, since the sources only say they are not retried): 401 and 403 give `auth_failed`; 404 gives `not_found`; 429 gives `rate_limited`; 500, 502, 503, 504 and connection errors give `upstream_error` after the retries; a timeout gives `upstream_timeout`; a body past the byte cap gives `too_large`; a host outside the policy gives `blocked_by_policy`; any other 4xx gives `upstream_error` without a retry.

### 6.2 Error mapping elsewhere

| Where | Condition | Result | Source |
| --- | --- | --- | --- |
| `@tool_boundary` | `ToolError` or `HttpError` | The error result with code, message, retryable and correlation_id | SPEC-v2 3.7 |
| `@tool_boundary` | Any other exception | `internal`; traceback logged through the redactor | SPEC-v2 3.7 |
| `KeychainProvider` | Exit 44; exit 36 or 51 or "User interaction is not allowed"; anything else | `missing`; `keychain_locked`; `error`; stderr never logged or returned | SPEC-v2 3.1 |
| `GoogleAdcProvider` | `DefaultCredentialsError`; `RefreshError` | `missing`; `invalid`; exception text never logged or returned | SPEC-v2 3.1.1; HLTH-24 |
| `SecretCache.reload` | A name that held a value now reads `keychain_locked` or `error` | The previous value is kept and the new state is reported; `missing` clears it | 4.1 |
| `reload_credentials` and the `SIGHUP` handler | Any exception | Logged as a warning without exception text; the daemon keeps running | 5.10 |
| `daemon.main` | A settings validation error (placeholder `contact.email`, non-loopback host, bad reference) | A redacted message and a non-zero exit; the daemon does not start | PLAT-10, PLAT-11 |
| `WorkerRunner` | Crash, RSS past 2 GB, or 180 s wall clock | SIGKILL; the task ends with `extract_failed` | SPEC-v2 3.6 |
| `Migrator` | A failing script | The explicit transaction leaves no partial schema | SPEC-v2 3.5 |
| `Migrator` | `user_version` newer than the newest migration; SQLite older than 3.37 | Refuses to open; asserts at start | SPEC-v2 3.5 |
| Shim | Daemon down after the launchd start and retry | One clear MCP error | PLAT-FR-2 |
| Shim | 401 from the daemon | Re-read the Keychain token once and retry once, then `auth_failed` | 5.7 |
| `research-mcp upgrade` | The daemon is not ready, or `doctor` exits non-zero | Reinstall the recorded version, restore both databases, restart | PLAT-FR-55; SPEC 12 |
| `BackupService` | A failed nightly backup; a failed Drive copy | Nothing is pruned; a Drive failure is a warning and the local backup stands | 3.3 |
| `rotate_stderr_log` | Any I/O error | A warning; retried at the next run | 5.10 |

### 6.3 Idempotency

- The scheduler runs a missed job once at start or on wake, never once per missed day (SPEC-v2 3.6).
- The shim replays `initialize` once on a session error; stateless HTTP keeps sessions valid across restarts (SPEC-v2 7.4).
- Install generates `DAEMON_TOKEN` only if it is absent, and a second install boots out each loaded job before loading it (SPEC-v2 12.2).
- `secrets rotate-token` always replaces the token; running it twice yields two rotations, each of which invalidates the previous token.
- The downloader reuses an existing file with the same SHA-256 (SPEC-v2 3.4).
- Keychain writes use `add-generic-password -U` (update if present) (SPEC-v2 3.1).
- A reload is idempotent: with no change in the Keychain it returns an empty list.
- A backup on the same day replaces that day's folder; pruning removes only folders beyond `backup.keep`.
- Outbox rows are copied to `state.db.review_events` and then deleted, so each database commits on its own (SPEC-v2 3.5).

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

### 7.1 Settings (SPEC-v2 2; PLAT-FR-8, PLAT-FR-9)

`settings.Settings` (pydantic-settings), loaded from `~/.config/research-mcp/config.toml`, then `RESEARCH_MCP_*` environment overrides (nested with `__`). Loading happens only in `daemon.py` and `cli.py` (PLAT-FR-4). Every rejected value is reported without echoing it (PLAT-8).

| Key | Default | Notes |
|---|---|---|
| `server.host` | `127.0.0.1` | Validation rejects any non-loopback value (PLAT-10). |
| `server.port` | `7319` | MCP at `/mcp`, UI at `/ui`. |
| `server.token` | `keychain:research-mcp/DAEMON_TOKEN` | Bearer for the shim and API. Must be a `keychain:` reference; an `env:` reference or any other text is rejected (4.1; SEC-INV-3, SEC-INV-10). The code's validator does not check this yet; the implementer adds it. |
| `paths.state_dir` | `~/Library/Application Support/research-mcp` | `state.db`, `backups/`, `imports/` |
| `paths.data_dir` | `~/Library/Application Support/research-mcp/cache` | `cache.db`, `files/`, `trash/`, `tmp/` (not in `~/Library/Caches`, which macOS and cleaners may purge) |
| `paths.model_cache_dir` | `~/Library/Caches/research-mcp/models` | Embedding model files only (re-downloadable) |
| `paths.log_dir` | `~/Library/Logs/research-mcp` | `research-mcp.jsonl`, `daemon.err.log` |
| `contact.email` | none | Crossref `mailto`, Unpaywall `email`, user agent (5.3). A placeholder domain (`example.com`, `example.org`, `test`, `invalid`, and their subdomains) is a validation error, so the daemon does not start. If unset, only the sources with `needs_contact` are `unconfigured`; the daemon starts and the user agent has no `mailto` part (SRC-FR-24; PLAT-11). |
| `logging.debug` | `false` | New in v2 (4.3). Debug level for `research_mcp` loggers and query text in clear in the log file. Read at start. |
| `limits.response_bytes` | `65536` | Envelope budget |
| `limits.download_bytes` | `52428800` | |
| `limits.pdf_pages` | `500` | |
| `limits.chunk_hard_cap_chars` | `4000` | |
| `federation.deadline_s` | `8.0` | |
| `federation.default_groups` | `["scholarly", "preprints"]` | |
| `cache.retention_days` | `120` | Fixed from fetch (ADR 0011) |
| `cache.review_lead_days` | `3` | |
| `cache.review_time_local` | `"09:00"` | |
| `cache.batch_open_hours` | `24` | Unanswered items become `kept` when the batch closes |
| `cache.reask_days` | `7` | |
| `cache.trash_days` | `7` | |
| `archive.target` | `auto` | `auto` finds the single `~/Library/CloudStorage/GoogleDrive-*/My Drive`; else an absolute path |
| `archive.confirmed_path` | none | Set when the owner confirms the detected target in the UI or with `config set`; archiving to `auto` waits for this confirmation |
| `archive.subfolder` | `Research Archive/{year}` | |
| `archive.fallback` | `~/Research Archive/{year}` | |
| `notify.macos` | `true` | `terminal-notifier` if present, else `osascript` (no click-through) |
| `notify.webhook_url` | none | OpenClaw inbox (O5 closed, PRD-v7 1.6); any token goes in Keychain `NOTIFY_WEBHOOK_TOKEN`, never in the URL, and a URL with credentials, a query or a fragment is rejected |
| `notify.quiet_hours` | `"21:00-08:00"` | |
| `disk.cache_warn_bytes` | `5368709120` | |
| `disk.free_warn_bytes` / `free_crit_bytes` | `16106127360` / `5368709120` | |
| `backup.keep` | `7` | Number of nightly backups kept of `state.db`, `cache.db` and `config.toml` (3.3; PLAT-FR-57) |
| `backup.drive_copy` | `false` | New in v2. Optional copy of each nightly backup to `Research Archive/_state/` in the confirmed Drive folder (3.3). Default off (owner decision, 2026-10-22). |
| `sources.<id>.enabled` | spec default | |
| `sources.<id>.budget_cap` | none (`100` for `web` sources) | Daily call cap for metered sources (UI Quota page); resets at local midnight |
| `sources.vertex_<name>` | none | `{ instance_of = "vertex_search", project = "...", location = "global", engine_id = "...", title = "..." }`; one per Vertex AI Search engine ([LLD-sources](LLD-sources-v2.md) 5.7) |
| `sources.google_pse.engine_id` | none | Programmable Search engine id (v1 `GOOGLE_PSE_CX`); not a secret |
| `web.strategy` | `"fallback"` | `fallback` or `all` ([LLD-sources](LLD-sources-v2.md) 5.9) |
| `web.order` | `["vertex_*", "brave_search", "serpapi", "google_pse"]` | `vertex_*` expands to the configured Vertex instances in name order |
| `site_sets.<name>` | `v1_docs` ([LLD-sources](LLD-sources-v2.md) 3.3) | A list of domains; names match `[a-z0-9_]{1,40}`. Edited in the file or with `config set`; the UI shows them read-only (SRC-FR-18; UI-FR-21) |
| `sources.<id>.<field>` | per spec | For example `sources.dspace_penn.base_url` |
| `credentials.<NAME>.rotate_by` | none | Optional override |

Directories are created at daemon start with mode `0700`.

Per-source sections come from each `SourceSpec` (PLAT-FR-8). The settings model is loaded by `daemon.py` and `cli.py`; importing `settings.py` reads nothing (PLAT-FR-4).

| Unit | Section | Requirement |
|---|---|---|
| M0-04 | 2; AT-PLAT-08, AT-PLAT-09 | Paths MUST be normalized (resolving `..`) before the durable-location check. Credential names MUST keep their canonical case across TOML and `RESEARCH_MCP_` environment overrides, so an environment override updates the same credential the TOML defines. |

(SPEC-v2 0.6)

### 7.2 Optional behavior

A feature-flags PRD does not exist: there is no such file in `docs/prd/components/`, and neither AGENTS.md nor the SDD standard defines a flag registry for this repository. So no registration rule applies, and this table is the platform's list of optional behavior. Each row says what switching it off does; all are safe in the sense that no data is lost, the MCP tool list does not change and the daemon still starts (decision 15 of section 10).

| Flag | Default | Safe to switch off? |
| --- | --- | --- |
| `sources.<id>.enabled` | spec default; every `web` source is off until configured (ADR 0012) | Yes: each source can be disabled with a flag; it is reported `disabled` (SPEC 18) |
| Extras `pdf`, `embeddings`, `macos`, `gcp` | not installed; a search-only install needs none of them (PLAT-FR-51) | Yes: without `gcp`, `vertex_search` shows `unconfigured` with the install command (PLAT-13); without the `macos` extra the archive upload state is `unknown` (PLAT-84) |
| `contact.email` | none | Yes: sources with `needs_contact` become `unconfigured`; the daemon still starts and the user agent has no `mailto` part (5.3) |
| `notify.macos` | `true` | Yes, with one cost. Off: no macOS notification is shown. Notices are still stored in `state.db` (HLTH-FR-35), shown in the UI banner and sent to the webhook if one is set (HLTH-FR-32); no data is lost. The cost: the 15-minute watchdog's dead-daemon notice (NFR-12) then reaches the owner only through the webhook, because the UI is down with the daemon; `doctor` output still shows it. |
| `notify.webhook_url` | none (channel off) | Yes: the macOS notification and the UI banner remain; nothing is queued for the webhook. |
| `logging.debug` | `false` | Yes: off is the default and the safe state; query text is then logged only as hash and length (PLAT-FR-42). It is read at start, so a change needs a restart. |
| `backup.drive_copy` | `false` | Yes: off means backups stay in `state_dir/backups/` only; nothing already in Drive is removed. |

## 8. Observability

> **Owner:** A · **Persona:** `sre`

Reviewed by the `sre` persona against SPEC-v5 12, PRD-v7 NFRs and PRD-platform-v4; not approved.

- **Logs:** JSON lines in `log_dir/research-mcp.jsonl`, `RotatingFileHandler` at 10 MB with 4 rotated files kept, so 5 files in all (PLAT-FR-40; PLAT-40; PRD-v7 2.4); stderr at `WARNING` (4.3). The launchd daemon job also writes `__LOGS__/daemon.err.log` (2.5), rotated by the `log_rotate` job to 5 files of 10 MB (5.10). The UI shows recent warnings and errors (SPEC 12; UI-FR-18).
- **Log fields:** time, level, event, correlation id, tool, source, operation, status, error code, latency, bytes, job id, attempt (PLAT-FR-41; PLAT-41). `correlation_id` is set per tool call and per job (4.3).
- **Query text** is logged as `query_hash` and `query_len` unless `logging.debug` is on (PLAT-FR-42; PLAT-42; 4.3).
- **Noise and leaks:** the `httpx`, `httpcore`, `uvicorn.access` and `mcp` loggers run at `WARNING`; uvicorn access logging is off; stderr passes through the redactor (4.3; SPEC-v2 1).
- **Call telemetry:** every HTTP attempt emits a `CallRecord` with time, source, operation, status, error code, latency, bytes, rate-limit headers, credential expiry, correlation id and attempt; the daemon's sink is `StateStore.record_call`, flushed every second (5.3; SPEC-v2 4). The Google sign-in refresh is recorded with `source="google_signin"` (4.2).
- **Credential reloads:** each reload logs the names whose fingerprint changed, never values (5.10).
- **Liveness and readiness:** `/healthz` and `/readyz` (4.5). The watchdog LaunchAgent runs `doctor --liveness --notify` every 900 s, and the doctor LaunchAgent runs `doctor --notify` daily at 08:52 (2.5; HLTH-FR-41).
- **Backups:** nightly, the last 7 kept, and a failed backup prunes nothing (PLAT-FR-57; CACHE-49; OC-10). `doctor` reports `backup_recent` (a backup in the last 48 hours; [LLD-cache](LLD-cache-v2.md) 8). `backup.drive_copy` is off by default; when on, a failed Drive copy is a warning in the log and the local backup stands.
- **Settings read at start:** `logging.debug` (default `false`) needs a restart to change; with it off, query text is only hash and length (NFR-4; PLAT-FR-42).
- **Thresholds:** the event loop heartbeat gap stays under 200 ms while a slow source runs (PLAT-75; NFR-2). A dead daemon is reported within 15 minutes (watchdog every 900 s; NFR-12; OUT-4). Any secret value in a log line is a breach, not a threshold (NFR-4; SEC-INV-4). There is no uptime or response-time target (NFR-12). Alerting, probes and notifications belong to the health component (SPEC 7); this component defines no alert of its own.

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

Reviewed by `test-architect` at Gate 3 (2026-10-23) against test plan v4 (draft) and PRD-platform v4: every PLAT criterion has a row, and the sync convergence rule of AGENTS.md does not apply because this component changes no sync or apply code. Planned files follow [test plan v4](../test/test-plan-v4.md) 2.1 where it names them; for the rest the file is chosen by best fit [inferred]. Existing tests cite the earlier `AT-PLAT-nn` IDs in some docstrings; new and changed tests cite the new IDs (AGENTS.md).

**Level of PLAT-70 to PLAT-77** (decision 13 of section 10). PRD-platform v4 and test plan v4 give these eight criteria the level integration, so they are integration tests: they use real components with fakes from `research_mcp.testing` and a blocked network (test plan v4 1.1). v1 placed them under `tests/unit/`, which does not match their level. They move to `tests/integration/`. That folder is now in the platform paths of `sdd.config.json` (owner decision, 2026-10-22).

| Criterion | Planned tests | Level | Status |
| --- | --- | --- | --- |
| PLAT-1 | `tests/unit/test_version.py::test_version_is_3x_and_matches_metadata` | unit | test linked |
| PLAT-2 | `tests/unit/test_version.py::test_ci_script_is_executable_bash` | unit | test linked |
| PLAT-3 | `tests/unit/test_import_side_effects.py::test_importing_research_mcp_does_no_work`, `test_third_party_modules_cover_base_dependencies`, `test_probe_detects_import_side_effects`, `test_probe_detects_work_done_through_a_dependency` | unit | test linked |
| PLAT-5 | `tests/unit/test_network_guard.py::test_blocks_connect_before_io`, `test_blocks_create_connection_before_io`, `test_blocks_datagrams_before_io`, `test_blocks_name_lookup_before_io`, `test_blocks_reverse_lookup_before_io`, `test_blocks_loopback_lookalikes_before_io`, `test_blocks_async_http_client`, `test_passes_loopback_through`, `test_allows_loopback_server`, `test_live_tests_deselected_by_default`, `test_live_tests_run_unguarded_when_selected`, `test_guard_covers_session_fixtures`, `test_guard_covers_collection` | unit | test linked |
| PLAT-4 | `tests/unit/test_version.py::test_heavy_dependencies_are_extras` (also asserts no `duckdb`, 4.6) | unit | test linked |
| PLAT-30 | `tests/unit/core/test_envelope.py::test_envelope` | unit | test linked |
| PLAT-31 | `tests/unit/core/test_budget.py::test_budget`, `test_statuses_are_mandatory`, `test_invalid_prefix_is_not_a_size_result` | unit | test linked |
| PLAT-32 | `tests/unit/core/test_envelope.py::test_errors` | unit | test linked |
| PLAT-33 | `tests/unit/core/test_envelope.py::test_untrusted` | unit | test linked |
| PLAT-6 | `tests/unit/core/test_models.py::test_models_and_clock` | unit | test linked |
| PLAT-34 | `tests/unit/core/test_budget.py::test_cursors` | unit | test linked |
| PLAT-8 | `tests/unit/test_settings.py::test_defaults`, `test_toml_and_environment`, `test_typed_web_source_defaults`, `test_invalid_values`, `test_webhook_rejects_tokens`, `test_webhook_accepts_plain_url`, `test_rotate_by_is_utc`; planned additions: `test_token_must_be_keychain_reference`, `test_logging_debug_default_off`, `test_backup_drive_copy_default_off` | unit | test linked, additions planned |
| PLAT-9 | `tests/unit/test_settings.py::test_paths_and_creation`, `test_reject_purgeable_paths`, `test_normalization_and_symlinks` | unit | test linked |
| PLAT-10 | `tests/unit/test_settings.py::test_non_loopback`, `test_loopback` | unit | test linked |
| PLAT-11 | `tests/unit/test_settings.py::test_placeholder_email`, `test_optional_email`; planned: `tests/unit/platform/test_http.py::test_user_agent_without_contact` (5.3) | unit | test linked, addition planned |
| PLAT-12 | `tests/unit/platform/test_secrets.py::test_parse_valid_references`, `test_parse_rejects_malformed_references`, `test_direct_construction_validates`, `test_parse_error_does_not_echo_input` | unit | test linked |
| PLAT-40 | `tests/unit/platform/test_logging.py::test_rotating_file_is_5_files_of_10mb`, `test_stderr_warnings_only`; `test_rotate_stderr_log` (5.10) | unit | planned |
| PLAT-41 | `tests/unit/platform/test_logging.py::test_records_carry_fields_and_correlation_id` | unit | planned |
| PLAT-42 | `tests/unit/platform/test_logging.py::test_query_text_is_hash_and_length`, `test_debug_logs_query_text_through_redactor`, `test_query_hash_is_nfc_casefold_stable` | unit | planned |
| PLAT-35 | `tests/unit/platform/test_http.py::test_retry_after_and_rate_limited` | unit | planned |
| PLAT-36 | `tests/unit/platform/test_http.py::test_retries_5xx_and_policy_block` | unit | planned |
| PLAT-37 | `tests/unit/platform/test_ratelimit.py::test_shared_bucket_spaces_arxiv_calls` | unit | planned |
| PLAT-38 | `tests/unit/platform/test_http.py::test_byte_cap_aborts_before_full_body` | unit | planned |
| PLAT-39 | `tests/unit/platform/test_http.py::test_user_agent_and_call_record_per_attempt` | unit | planned |
| PLAT-50 | `tests/unit/platform/test_stores.py::test_migrator_transaction_and_user_version` | unit | planned |
| PLAT-51 | `tests/unit/platform/test_stores.py::test_newer_database_is_refused` | unit | planned |
| PLAT-52 | `tests/unit/platform/test_stores.py::test_pragmas_and_serialized_writes` | unit | planned |
| PLAT-53 | `tests/unit/platform/test_stores.py::test_schemas_match_spec` | unit | planned |
| PLAT-60 | `tests/contract/test_tool_contract.py::test_every_tool_declares_annotations` (M0-14; file owned by the search component, section 1) | contract | planned |
| PLAT-61 | `tests/contract/test_tool_contract.py::test_instructions_state_untrusted_and_owner_decision_rules` | contract | planned |
| PLAT-62 | `tests/contract/test_tool_contract.py::test_internal_error_has_no_exception_text` | contract | planned |
| PLAT-63 | `tests/contract/test_tool_contract.py::test_result_never_exceeds_response_bytes` | contract | planned |
| SEC-28 (proposed in PRD-security v3) | `tests/security/test_no_secret_in_tool_results.py::test_successful_tool_results_hold_no_registered_secret` (proposed name; the same test as in LLD-security v2 9; M2) | contract | planned |
| PLAT-70 | `tests/integration/test_app.py::test_lifespan_opens_and_closes_everything`, `test_healthz_and_readyz` (M0-15) | integration | planned |
| PLAT-71 | `tests/integration/test_app.py::test_daemon_refuses_non_loopback_bind` | integration | planned |
| PLAT-72 | `tests/integration/test_shim.py::test_full_mcp_session_through_shim` | integration | planned |
| PLAT-73 | `tests/integration/test_shim.py::test_down_daemon_starts_via_launchctl_then_one_error` | integration | planned |
| PLAT-74 | `tests/integration/test_jobs.py::test_submit_status_progress_cancel_persist` | integration | planned |
| PLAT-75 | `tests/integration/test_app.py::test_event_loop_heartbeat_under_slow_source` | integration | planned |
| PLAT-76 | `tests/integration/test_scheduler.py::test_missed_daily_job_runs_once` | integration | planned |
| PLAT-77 | `tests/integration/test_shim.py::test_stateless_restart_and_initialize_replay` | integration | planned |
| PLAT-80 | `tests/unit/test_cli.py::test_help_lists_platform_commands` (checks the ten names; extra commands allowed, 2.4) | unit | planned |
| PLAT-81 | `tests/unit/test_install.py::test_plists_parse_and_hold_nothing_secret` | unit | planned |
| PLAT-82 | `tests/unit/test_install.py::test_client_config_launches_stdio_without_secret_or_url` | unit | planned |
| PLAT-83 | `tests/unit/test_install.py::test_install_generates_token_if_absent`, `test_rotate_token_replaces_and_old_token_fails` | unit | planned |
| PLAT-13 | `tests/unit/test_version.py::test_gcp_extra_is_optional_and_vertex_unconfigured_when_missing` (M1; no file named in test plan v4) | unit | planned |
| PLAT-84 | `tests/unit/test_version.py::test_macos_extra_is_optional_and_reported_when_missing` (test plan v4; M2). The `unknown` upload state itself is `ArchiveService.reconcile` in the cache component | unit | planned |

**Additional tests for the design in this version.** They cite existing criteria; no new criterion ID is created.

| Behavior | Planned test | Cites |
| --- | --- | --- |
| The `SIGHUP` handler and "Reload credentials" call `reload_credentials`; a locked Keychain keeps the old secret; a failing reload does not stop the daemon | `tests/integration/test_reload.py` | SEC-4 (PLAT-FR-15) |
| The shim sends the Keychain token and ignores a decoy in the environment; a 401 triggers one re-read and retry | `tests/unit/test_shim.py` (the file test plan v4 names for SEC-26; the 401 retry case is a second test there) | SEC-26 |
| After `install`, a daemon start and a reload, no registered secret is in the configuration or Application Support folders | `tests/security/test_no_secret_at_rest.py::test_config_and_state_db_hold_no_secret` (the file test plan v4 names for SEC-24) | SEC-24 |
| `server.token` and any reference key reject `env:` | `tests/unit/test_settings.py::test_env_references_rejected_in_config` | PLAT-12, SEC-24 |
| Upgrade unloads the jobs before replacing files, and a failed `doctor` or readiness rolls back and restores both databases | `tests/unit/test_install.py::test_upgrade_boots_out_then_rolls_back` (fake launchctl, fake `uv`) | owner check OC-09 (PLAT-FR-55); no criterion |
| Nightly backups prune to 7; a failed backup prunes nothing | `tests/services/test_backup.py` (cache component) | owner check OC-10, CACHE-49 (PLAT-FR-57) |

The offline guard behind PLAT-5:

| Unit | Section | Requirement |
| --- | --- | --- |
| M0-01 | 1, 12.1; AT-PLAT-05, NFR-09 | The offline network guard MUST be installed for the whole test session (a session-scoped autouse fixture or a plugin active before collection), not per test. It MUST refuse, before any I/O, `socket.socket.connect`, `connect_ex`, `sendto`, `sendmsg` and `socket.create_connection` to non-loopback addresses, and `getaddrinfo`, `gethostbyname`, `gethostbyname_ex` and `gethostbyaddr` for non-loopback names. Loopback MUST keep working. Negative tests MUST prove each refusal happens before I/O. |

(SPEC-v2 0.6)

Fakes used by these tests: `FakeProvider` (`platform/secrets.py`), `FakeClock` and a fake `Sleeper` (`testing/clock.py`), fake adapters (`testing/adapters.py`), `FakeLaunchctl` (`testing/launchctl.py`) and the in-memory MCP client (`tests/contract/conftest.py`) (test plan v4 1.3). Owner checks OC-01, OC-02, OC-08, OC-09 and OC-10 cover PLAT-FR-1, PLAT-FR-10, PLAT-FR-53, PLAT-FR-55 and PLAT-FR-57 on the Mac (test plan v4 3).

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| One daemon per Mac with a stdio shim (ADR 0002) | Each v1 client started its own process, so rate limits broke across clients and there was no shared health (REVIEW-v1 3, finding 13) | One process per client (v1) |
| MCP clients reach the daemon only through the shim (SPEC 2; PLAT-FR-2; SEC-INV-10; owner decision, 2026-10-22) | The token stays in the Keychain, and no client config holds a URL or a token | Offering direct loopback HTTP to clients |
| Secrets in the Keychain, references in config (ADR 0003) | v1 kept three plaintext copies of keys in client configs (OPS-11) | Environment variables in client configs (v1) |
| One composition root; no work at import (ADR 0004) | Import-time side effects in v1 (REVIEW-v1 3, finding 2) | not stated |
| Async I/O; CPU work in worker processes (ADR 0005) | Every v1 tool blocked the event loop (REVIEW-v1 3, finding 3) | not stated |
| One subprocess per CPU task | On macOS `ProcessPoolExecutor` cannot enforce memory limits or kill a running task (SPEC-v2 3.6) | `ProcessPoolExecutor` |
| Parent enforces RSS and wall clock | macOS does not enforce `RLIMIT_AS` (SPEC-v2 3.6) | `RLIMIT_AS` in the child |
| Scheduler on the wall clock | asyncio timers stall while the Mac sleeps (SPEC-v2 3.6) | asyncio timers |
| Migrator issues `BEGIN IMMEDIATE` and `COMMIT` itself | `executescript` commits implicitly (SPEC-v2 3.5) | `executescript` |
| Outbox between `cache.db` and `state.db` | Neither database needs a transaction that spans both (SPEC-v2 3.5) | A cross-database transaction |
| Downloader pins the connection to the checked IP | httpx never resolves the name a second time, which closes the DNS-rebinding gap (SPEC-v2 3.4) | Letting httpx resolve the name |
| Redaction filter on every handler, plus a redacting stderr stream | Records propagated from child and third-party loggers are covered (SPEC-v2 3.2); raw stderr reaches `daemon.err.log` without passing a handler (SEC-INV-4) [assumption] | A filter on a logger |
| Keychain writes through `security -i` on stdin | The value never appears in a process argument list (SPEC-v2 3.1) | Passing `-w <value>` as an argument |
| Cursor key derived from `DAEMON_TOKEN` by HKDF | No separate secret is stored; agents cannot forge cursors (SPEC-v2 3.1, 3.7) | A separate stored key |
| Stateless streamable HTTP at `/mcp` | A daemon restart never invalidates a client session (SPEC-v2 7.4) | Stateful sessions |
| SQLite is the only store (ADR 0008, ADR 0011) | No separate archive database is needed; DuckDB is not used for storage | A persisted DuckDB index (REVIEW-v1 6, dropped) |
| Google sign-in through `google-auth` (ADR 0012) | `gcloud` owns the credential; v2 holds only a short-lived token in memory | An API key in the Keychain |
| Forward-only migrations with a pre-upgrade backup | The step 3 backup makes rollback possible (5.9) | Down migrations |

**Decisions that settle the open questions of LLD-platform v1** (each answered from the approved sources; the question is deleted from section 11):

| # | Question in v1 | Decision and source |
| --- | --- | --- |
| 1 | `RefreshError` maps to `invalid`, but `SecretState` had no such member | `SecretState` gains `INVALID`, returned only by `GoogleAdcProvider`. The credential states in PRD-health v4 (the table of states, `invalid` for OAuth `invalid_grant`) and HLTH-24 require a refused refresh to be `invalid`, and the provider is where the mapping happens (4.1, 4.2). Alternative: map to `error`, which loses the distinction HLTH-24 tests. |
| 2 | Should `--help` list `archive` and PLAT-FR-50 name it? | PRD-platform v4 names ten commands in PLAT-FR-50 and PLAT-80 and not `archive`. The platform CLI is those ten. `archive reindex` belongs to the cache component (CACHE-FR-51) and is listed in `--help` by being registered there; PLAT-80 passes with extra commands (2.4). |
| 3 | Where is the Drive copy of backups designed? | SPEC 10 and 12 describe the copy as optional and not yet designed, and the PRD says "optionally copied" (PLAT-FR-57; OC-10). So a Drive copy exists as an optional, flagged feature: `backup.drive_copy`, default off, contract in 3.3, service design in LLD-cache. The owner decided on 2026-10-22 to build it with the default off (owner decision, 2026-10-22). Alternative: do not build it in the first release. |
| 4 | "5 files kept" against `RotatingFileHandler(..., 10 MB, 5)` | PLAT-FR-40, SPEC 10 and the owner decision of 2026-10-22 say 5 files of 10 MB. `backupCount=4` gives the live file plus four rotated, five in all (4.3). The `daemon.err.log` rotation that SPEC 12 assigns here is `rotate_stderr_log` (5.10). |
| 5 | The debug logging key and the query hash | The sources define neither. Key `logging.debug` (default `false`); hash is truncated SHA-256 of the NFC, casefolded text (4.3). Choices, for the owner to confirm at Gate 3. |
| 6 | Where is `SIGHUP` wired? | `daemon.py` runs an `anyio` signal receiver beside uvicorn and calls `app.state.reload_credentials`, which `build_app` provides and the UI action also calls (5.10). |
| 7 | UI rotation of the daemon token | None. PLAT-FR-59 and SPEC 8, 9, 12 (owner decision, 2026-10-22): the token rotates only from `secrets rotate-token`, which signals the daemon to reload (4.5). |
| 8 | PLAT-FR-22 and DuckDB | ADR 0011 and PLAT-4: DuckDB is not used and is not a dependency. PLAT-FR-22 is met by not using it; the lockdown settings are kept as a precondition for any future use (4.6). |
| 9 | Where may `env:` references be used? | PLAT-12 requires parsing both forms, PLAT-FR-10 and NFR-3 require configuration to hold Keychain references only. So `env:` parses but is rejected in every settings key and override; it is a code-level backend for tests and CI (4.1). |
| 10 | User agent without a contact | `research-mcp/<major>.<minor>` with no `mailto` part; never a default or placeholder address (5.3). A placeholder address is a validation error and the daemon does not start; an unset address only makes `needs_contact` sources `unconfigured` (SRC-FR-24; PLAT-11; SPEC 4). |
| 11 | Upgrade and rollback | The job is unloaded with `launchctl bootout` before any file changes; the new environment's `doctor --quick` runs after the daemon is ready; non-zero exit (an `install_critical` check, LLD-health v2 5.9) or no readiness rolls back and restores both databases (PLAT-FR-55; SPEC 12; 5.9). |
| 12 | Who owns `build_mcp`, `@tool_boundary`, `tests/contract/`, `core/specs.py`, `core/models.py`, `services/backup.py` | The table in section 1: design and criteria stay in this LLD for `build_mcp`, `@tool_boundary` and PLAT-60 to PLAT-63; the file paths follow `sdd.config.json` (search for `mcp_app` and `tests/contract`, platform for `core/specs.py` and `core/models.py`, cache for `services/backup.py`); the type design is LLD-sources 2.1, 2.2 and 3.1; the backup service design is LLD-cache 5 (SPEC 19). |
| 13 | Level of PLAT-70 to PLAT-77 | Integration, as PRD-platform v4 and test plan v4 say; files move to `tests/integration/` (9). |
| 14 | Which contracts get a machine-readable file | The envelope and the error codes: [envelope and error codes v1](../contracts/envelope-and-errors-v1.md), a draft for the owner (a C item). Not the CLI (a human surface verified by PLAT-80), the launchd templates (package files), or the endpoints (the health LLD owns `/api/status`; `/healthz` and `/readyz` are two fixed shapes in 4.5). The tool schemas are emitted by the SDK (PLAT-30). |
| 15 | Flags for `notify.macos`, `notify.webhook_url` and debug logging | No feature-flag PRD or registry exists in this repository (checked `docs/prd/components/` and the SDD standard), so no registration rule applies. Behavior when off is in the table in 7.2. |

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

No question is open. The owner answered all of them on 2026-10-22: the Drive copy of backups is built behind `backup.drive_copy`, default off (3.3); `tests/integration` is in the platform paths of `sdd.config.json` (9); the auth gate and the redaction of tool results are in 4.5 and 5.6.

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| Kenny Hill (Engineering) | 2026-10-23 | approved (envelope-and-errors-v1) | approved: none (adds no table, column or migration) | approved (security-reviewer persona drafted/reviewed; control owner Kenny Hill) | Approved in chat; recorded by Claude in the owner's name at his direction |
