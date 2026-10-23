---
title: "Platform and Security low level design"
type: lld
version: 1
status: draft
owner: "Kenny Hill"
prefix: PLAT
component: platform
parent: docs/spec/SPEC-v3.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# LLD: Platform and Security (v1)

This LLD carries over SPEC-v2 sections 1 (conventions and layout), 2 (settings and paths), 3.1 to 3.7 (secrets, Google sign-in, redaction and logging, HTTP client, downloader, stores and migrations, workers and jobs, errors and the envelope), 7.4 (MCP transport), 12.1 (packaging and CI) and 12.2 (launchd, install and upgrade), with HLD-v3 sections 3, 10 and 12 for context. Names are unchanged from SPEC-v2. Requirements and criteria are in [PRD-platform v3](../prd/components/PRD-platform-v3.md).

Section numbers inside text copied from the SPEC (for example "(9.3)" or "section 4") refer to SPEC-v2; bare section numbers in this LLD's own text (for example "(4.4)" or "(11)") refer to this LLD. Requirement and criterion IDs in copied text use the new IDs; rows marked "(SPEC-v2 0.6)" are verbatim and keep the old IDs.

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

Governing sections: SPEC-v3 section 3 (component architecture), SPEC-v3 section 10 (data stores) and SPEC-v3 section 12 (deployment and operations).

| Requirement | Criteria | SPEC section | Detailed in |
| --- | --- | --- | --- |
| PLAT-FR-1 | none in PRD-platform (owner check OC-01) | SPEC-v3 section 3, SPEC-v3 section 12 | 5.9 |
| PLAT-FR-2 | PLAT-72, PLAT-73, PLAT-77 | SPEC-v3 section 3 | 2.3, 5.7 |
| PLAT-FR-3 | PLAT-10, PLAT-71 | SPEC-v3 section 3 | 4.5 |
| PLAT-FR-4 | PLAT-3, PLAT-70 | SPEC-v3 section 3 | 2.3, 5.1, 5.2 |
| PLAT-FR-5 | PLAT-52, PLAT-75 | SPEC-v3 section 3 | 3.1, 5.5 |
| PLAT-FR-6 | PLAT-74, PLAT-76 | SPEC-v3 section 3 | 5.5 |
| PLAT-FR-8 | PLAT-8 | SPEC-v3 section 3 | 7.1 |
| PLAT-FR-9 | PLAT-9 | SPEC-v3 section 10 | 3.2, 7.1 |
| PLAT-FR-10 | PLAT-12 | SPEC-v3 section 3 | 4.1, 4.2 |
| PLAT-FR-11 | none in PRD-platform (SEC-1) | SPEC-v3 section 3 | 4.1 |
| PLAT-FR-12 | none in PRD-platform (SEC-8, SEC-9, SRC-33) | SPEC-v3 section 3 | 4.4 |
| PLAT-FR-13 | none in PRD-platform (SEC-5, SEC-6, SEC-7, SEC-14, SRC-33) | SPEC-v3 section 3 | 4.3 |
| PLAT-FR-14 | PLAT-62 | SPEC-v3 section 3 | 5.6, 6 |
| PLAT-FR-15 | none in PRD-platform (SEC-4) | SPEC-v3 section 3 | 4.1 |
| PLAT-FR-16 | PLAT-83 | SPEC-v3 section 3 | 4.5, 5.9 |
| PLAT-FR-20 | none in PRD-platform (SEC-21) | SPEC-v3 section 3 | 4.6 |
| PLAT-FR-21 | none in PRD-platform (CACHE-11) | SPEC-v3 section 3 | 4.6, 5.4 |
| PLAT-FR-22 | none in PRD-platform (SEC-21) | SPEC-v3 section 3 | 4.6 |
| PLAT-FR-25 | PLAT-33, PLAT-61 | SPEC-v3 section 3 | 2.1 |
| PLAT-FR-26 | PLAT-60 | SPEC-v3 section 3 | 2.3 |
| PLAT-FR-27 | none in PRD-platform (CACHE-34, SEC-20) | SPEC-v3 section 3 | 4.6 |
| PLAT-FR-30 | PLAT-6, PLAT-30, PLAT-31, PLAT-63 | SPEC-v3 section 3 | 2.1, 5.6 |
| PLAT-FR-31 | none in PRD-platform (SRCH-21) | SPEC-v3 section 3 | 2.3 |
| PLAT-FR-32 | PLAT-32, PLAT-62 | SPEC-v3 section 3 | 2.1, 6 |
| PLAT-FR-33 | PLAT-35, PLAT-36, PLAT-37, PLAT-38, PLAT-39 | SPEC-v3 section 3 | 2.2, 5.3, 6 |
| PLAT-FR-40 | PLAT-40 | SPEC-v3 section 3, SPEC-v3 section 12 | 4.3, 8 |
| PLAT-FR-41 | PLAT-41 | SPEC-v3 section 3 | 8 |
| PLAT-FR-42 | PLAT-42 | SPEC-v3 section 3 | 8 |
| PLAT-FR-50 | PLAT-80 | SPEC-v3 section 12 | 2.4, 5.8 |
| PLAT-FR-51 | PLAT-4, PLAT-13 | SPEC-v3 section 12 | 5.8, 7.2 |
| PLAT-FR-52 | PLAT-2 | SPEC-v3 section 12 | 5.8 |
| PLAT-FR-53 | none in PRD-platform (owner check OC-08) | SPEC-v3 section 12 | 5.8 |
| PLAT-FR-54 | PLAT-81, PLAT-82 | SPEC-v3 section 12 | 2.5, 5.9 |
| PLAT-FR-55 | none in PRD-platform (owner check OC-09) | SPEC-v3 section 12 | 5.9, 6 |
| PLAT-FR-56 | PLAT-50, PLAT-51 | SPEC-v3 section 10 | 3.1 |
| PLAT-FR-57 | none in PRD-platform (CACHE-49, owner check OC-10) | SPEC-v3 section 10, SPEC-v3 section 12 | 3.3 |
| PLAT-FR-58 | PLAT-1 | SPEC-v3 section 12 | 5.1 |
| SRC-FR-1 (sources) | PLAT-6 | SPEC-v3 section 3 | 2.2 |
| SRC-FR-7 (sources) | PLAT-13 | SPEC-v3 section 12 | 7.2 |
| SRC-FR-11 (sources) | PLAT-11 | SPEC-v3 section 3 | 7.1 |
| SRCH-FR-6 (search) | PLAT-34 | SPEC-v3 section 3 | 5.6 |
| CACHE-FR-30, CACHE-FR-36, CACHE-FR-55 (cache) | PLAT-8, PLAT-53 | SPEC-v3 section 10 | 3.1, 7.1 |
| NFR-9 (parent) | PLAT-5 | SPEC-v3 section 12 | 9 |

All 45 criteria of PRD-platform v3 appear above: PLAT-1 to PLAT-6, PLAT-8 to PLAT-13, PLAT-30 to PLAT-42, PLAT-50 to PLAT-53, PLAT-60 to PLAT-63, PLAT-70 to PLAT-77 and PLAT-80 to PLAT-83.

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

No machine-readable contract for this component exists yet in `docs/contracts/` (11).

### 2.1 Errors and the envelope (SPEC-v2 3.7)

```python
class ErrorCode(StrEnum):
    INVALID_ARGUMENT = "invalid_argument"; NOT_FOUND = "not_found"; UNCONFIGURED = "unconfigured"
    AUTH_FAILED = "auth_failed"; RATE_LIMITED = "rate_limited"; UPSTREAM_ERROR = "upstream_error"
    UPSTREAM_TIMEOUT = "upstream_timeout"; BUDGET_EXHAUSTED = "budget_exhausted"; TOO_LARGE = "too_large"
    BLOCKED_BY_POLICY = "blocked_by_policy"; DISABLED = "disabled"; EXTRACT_FAILED = "extract_failed"
    INTERNAL = "internal"

class ToolError(Exception):  code: ErrorCode; message: str; retryable: bool; correlation_id: str

class SourceStatus(BaseModel):
    source: str; state: Literal["ok","empty","timeout","rate_limited","error","unconfigured",
                                "disabled","skipped_unhealthy","skipped_budget"]
    count: int = 0; latency_ms: int | None = None; retry_after_ms: int | None = None
    error_code: ErrorCode | None = None

class Untrusted(BaseModel):  untrusted: Literal[True] = True; source: str; content: str

class ToolResult(BaseModel, Generic[T]):
    data: T; source_status: list[SourceStatus] = []; warnings: list[str] = []
    next_cursor: str | None = None; truncated: bool = False
```

`HttpError` lives in `core/errors.py` and the `correlation_id` `ContextVar` in `core/context.py` (both M0-03), so neither the platform nor the MCP layer needs to import the other. The client raises `HttpError(code: ErrorCode, status: int | None, retry_after_ms: int | None, detail: str | None)` (SPEC-v2 3.3).

### 2.2 HTTP ports (SPEC-v2 3.3)

Policies, credentials and telemetry are injected, so the HTTP layer does not depend on the source layer:

```python
class PolicyResolver(Protocol):
    def policy(self, source: str) -> SourcePolicy: ...            # core/specs.py (section 4)
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

`SourcePolicy`, `AuthSpec`, `RateSpec`, `Clock`, `Sleeper`, `AuthUse`, `TextResponse`, `DownloadedFile` and `CallRecord` are defined in SPEC-v2 4 (`core/specs.py`, `core/models.py`); PLAT-6 checks that they validate (11).

### 2.3 MCP transport and the composition root (SPEC-v2 7.4)

- `build_mcp(services)` creates a **new** `FastMCP` for each app. It is configured with `streamable_http_path="/"`, `stateless_http=True` and `json_response=True`, and the SDK's `TransportSecuritySettings` allow only the loopback hosts and origins.
- `build_app(settings, *, secrets: SecretProvider | None = None, transport: httpx.AsyncBaseTransport | None = None, clock: Clock | None = None, sleeper: Sleeper | None = None, adapters: Iterable[tuple[SourceSpec, type[SourceAdapter]]] | None = None, launchctl: LaunchctlPort | None = None)` mounts it at `/mcp` and runs `mcp.session_manager.run()` inside the Starlette lifespan. The keyword arguments are the test seams; the daemon passes none of them and gets the real Keychain, network, clock and discovered adapters.
- Stateless HTTP means a daemon restart never invalidates a client session. If the shim gets a 404 or 400 for a session, it replays `initialize` once anyway.

`app.py` builds the Starlette app and mounts `/mcp`, `/ui`, `/healthz`, `/readyz` and `/api` (SPEC-v2 1). Every MCP tool carries `@tool_boundary` (5.6). Tool annotations (PLAT-FR-26), argument bounds (PLAT-FR-31) and the server instructions (PLAT-61) are part of the tool catalog in SPEC-v2 7.2 and 7.3, which the search component's LLD holds (11).

### 2.4 CLI (SPEC-v2 12.1)

Scripts: `research-mcp = research_mcp.cli:main` and `research-mcpd = research_mcp.daemon:main`.

| Command | Purpose |
|---|---|
| `serve` | Run the daemon in the foreground. |
| `stdio` | The stdio shim for MCP clients. |
| `doctor [--json] [--notify] [--quick] [--liveness]` | Run health checks (10.5). |
| `ui [--path P]` | Open the UI with a one-time login. |
| `sources [--markdown] [check --live [--id] [--refresh-fixtures]]` | Source inventory and live checks. |
| `config get\|set <key> [value]` | Read or change config. |
| `install [--print-client-config]` | Install the launchd jobs and print client config. |
| `upgrade` | Upgrade with rollback (12.2). |
| `secrets list\|import [--dry-run]\|scrub-client-configs\|rotate-token` | Manage Keychain items. |
| `import-legacy <path> [--dry-run] [--mode]` | Import the v1 corpus (9.6). |
| `archive reindex [--dry-run]` | Rebuild the searchable archive from the Drive folder (9.7). |

`secrets list` prints names, fingerprints and states only.

### 2.5 launchd templates (SPEC-v2 12.2)

**Templates** in `src/research_mcp/packaging/launchd/` (package data):

| Template | Runs | Schedule and options |
|---|---|---|
| `local.research-mcpd.plist.template` | `__VENV__/bin/research-mcpd` | `RunAtLoad` true, `KeepAlive` true, `ThrottleInterval` 30, `ProcessType` Background, `StandardErrorPath` `__LOGS__/daemon.err.log` |
| `local.research-mcp-doctor.plist.template` | `research-mcp doctor --notify` | `StartCalendarInterval` Hour 8 Minute 52 |
| `local.research-mcp-watchdog.plist.template` | `research-mcp doctor --liveness --notify` | `StartInterval` 900 |

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

### 3.1 Stores and migrations (SPEC-v2 3.5)

- `Database(path)` holds one `aiosqlite` connection for writes, serialized through an `asyncio.Lock`, and a small pool for reads. Pragmas: `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`, `synchronous=NORMAL`.
- `Migrator` applies `migrations/<db>/NNNN_*.sql` in order.
  - Each script runs inside an explicit `BEGIN IMMEDIATE` and `COMMIT` that the Migrator issues itself. It never uses `executescript`, which commits implicitly.
  - It sets `PRAGMA user_version` and refuses to open a database whose `user_version` is newer than the newest migration.
  - At start it asserts `sqlite3.sqlite_version_info >= (3, 37, 0)`.
- Migration `.sql` files ship as package data. M0-01 configures this in `pyproject.toml`.
- `StateStore` and `CacheStore` expose typed methods only. No SQL appears outside `platform/stores.py` and the `services/*` repositories. Methods M0 needs (all defined in M0-08):
  - `StateStore.record_call(call)` (buffered) and `flush()`;
  - `job_insert(job)`, `job_update(job_id, **fields)`, `job_get(job_id)`, `job_list(state=None)`;
  - `schedule_get(job)`, `schedule_set(job, last_run_at, next_due_at)`;
  - `source_health_get(source)`, `source_health_list()`, `source_health_put(row)`;
  - `CacheStore.outbox_drain(limit) -> list[OutboxRow]` (the rest of `CacheStore` arrives in M2 as `services/*` repositories).
- **Cross-database events.** `documents.decided_*` in `cache.db` is authoritative. Each lifecycle transition also writes a row to `cache.db.outbox` in the same transaction. A drainer copies outbox rows to `state.db.review_events` and deletes them, so neither database needs a transaction that spans both.

The first migration of each database is `platform/migrations/state/0001_init.sql` and `platform/migrations/cache/0001_init.sql` (SPEC-v2 1). Their tables are specified in SPEC-v2 8.1 (`cache.db`) and 10.1 (`state.db`), which the cache and health LLDs hold; PLAT-53 checks the created schemas from the stores side.

### 3.2 Data stores and locations (HLD-v3 10)

| Store | Location | Owns | Backed up |
|---|---|---|---|
| `state.db` (SQLite, WAL) | `~/Library/Application Support/research-mcp/` | Credential metadata, source health, call telemetry and rollups, searches, jobs, schedule runs, notifications, review batches and a copy of review events | Nightly, 7 kept |
| `cache.db` (SQLite, WAL, FTS5, vector BLOBs) | `~/Library/Application Support/research-mcp/cache/` | Works, identifiers, source records, documents and lifecycle (including pins, decisions and archive paths), files, extractions, chunks, FTS, embeddings, collections, outbox | Nightly, 7 kept |
| Files | `~/Library/Application Support/research-mcp/cache/files/` (by SHA-256) and `trash/` | Cached PDFs and HTML | No (re-fetchable; archived copies live in Drive) |
| Model cache | `~/Library/Caches/research-mcp/models/` | Embedding model files | No (re-downloadable) |
| Archive | Drive sync folder `My Drive/Research Archive/<year>/` | Archived files and sidecars (their text stays in `cache.db`) | By Google Drive; also the source for the archive rebuild job |
| Config | `~/.config/research-mcp/config.toml` | Settings and secret references | Nightly with `state.db` |
| Secrets | macOS login Keychain, `research-mcp/<NAME>` | Credential values and the daemon token | By Keychain |

Nothing the lifecycle depends on lives in `~/Library/Caches`, which macOS and cleaning tools may purge. Both databases are backed up; only re-fetchable files are not. Directories are created at daemon start with mode `0700` (SPEC-v2 2).

### 3.3 Backups

`BackupService.backup_state()` runs nightly at 03:30. It uses the SQLite online backup API to copy `state.db` and `cache.db`, and it copies `config.toml`. The copies go to `state_dir/backups/<date>/`, and `backup.keep` days are kept. The stored files and the trash are not backed up (SPEC-v2 9.8, held by the cache LLD; scheduled as `backup_state` in 5.5). The optional Drive copy in PLAT-FR-57 has no design yet (11).

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

This section is the platform's security contract for secrets, redaction, credential scoping and local access. The security component's LLD references it rather than restating it.

### 4.1 Secrets (SPEC-v2 3.1)

```python
@dataclass(frozen=True)
class SecretRef:            # parsed from "keychain:research-mcp/CORE_API_KEY" or "env:NAME"
    backend: Literal["keychain", "env"]
    name: str               # CORE_API_KEY
    service: str            # research-mcp/CORE_API_KEY

@dataclass(frozen=True)
class SecretMeta: name: str; modified_at: datetime | None

class Secret:
    def __init__(self, ref: SecretRef, value: str): ...
    def reveal(self) -> str: ...            # called only in platform/http.py, platform/mcp_client.py and platform/auth.py
    @property
    def fingerprint(self) -> str: ...       # sha256(value)[:8]
    def __repr__(self) -> str: return f"Secret(name={self.ref.name}, fp={self.fingerprint})"
    __str__ = __repr__

class SecretState(StrEnum): OK="ok"; MISSING="missing"; LOCKED="keychain_locked"; ERROR="error"

class SecretProvider(Protocol):
    def get(self, ref: SecretRef) -> tuple[SecretState, Secret | None]: ...
    def metadata(self, ref: SecretRef) -> SecretMeta | None: ...   # no value
    def set(self, ref: SecretRef, value: str) -> None: ...          # value never in argv

class KeychainProvider:
    def __init__(self, user: str, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run): ...
class FakeProvider: ...      # tests; also records every argv it would have used

class SecretCache:           # what the daemon uses; implements CredentialResolver with a source->names map
    def __init__(self, provider: SecretProvider, refs: Mapping[str, SecretRef]): ...
    def load(self) -> None: ...
    def get(self, name: str) -> Secret | None: ...
    def state(self, name: str) -> SecretState: ...
    def reload(self) -> list[str]: ...      # names whose fingerprint changed
```

- **Read:** `/usr/bin/security find-generic-password -s <service> -a <user> -w`, run with a 5 s timeout.
  - Exit 44 (not found) maps to `missing`.
  - Exit 36 or 51, or "User interaction is not allowed", maps to `keychain_locked`.
  - Anything else maps to `error`.
  - stderr text is never logged or returned.
- **Metadata:** the same command without `-w`; only the `mdat` attribute is parsed.
- **Write:** `/usr/bin/security -i` with `add-generic-password -U -s <service> -a <user> -w <value>` written to stdin, so the value never appears in a process argument list. Values are checked for printable characters first, so `security -w` never returns a hex dump.
- **Keychain items:** service `research-mcp/<NAME>`, account `$USER`. The names are:
  - `DAEMON_TOKEN`, `NOTIFY_WEBHOOK_TOKEN`
  - `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `CORE_API_KEY`, `GOOGLE_DEVKNOWLEDGE_API_KEY`, `GITHUB_TOKEN`
  - `ZENODO_TOKEN`, `NCBI_API_KEY`, `NVD_API_KEY`, `ADS_API_TOKEN`, `LENS_API_TOKEN`, `OPENCITATIONS_TOKEN`
  - `BRAVE_SEARCH_API_KEY`, `SERPAPI_API_KEY` (M1). `GOOGLE_DEVKNOWLEDGE_API_KEY` is shared by `google_devknowledge` and `google_pse`, as in v1; each source's `origins` limit where it is sent.
- **Cursor signing key:** HKDF-SHA256 over `DAEMON_TOKEN` with info `research-mcp cursor v1`. No separate secret is stored.
- **ACL behavior:** items written by `/usr/bin/security` trust that binary, so reads by the daemon do not prompt, even after Python upgrades.

| Unit | Section | Requirement |
|---|---|---|
| M0-05 | 3.1; AT-PLAT-12, AT-SEC-13 | `SecretRef` MUST validate on construction: the name matches the allowed pattern, and a Keychain reference's service is exactly `research-mcp/<NAME>`. No control character (in particular a newline) may reach the `security -i` script. `FakeProvider.metadata` MUST behave like `KeychainProvider.metadata` (no metadata for `env:` references). |

(SPEC-v2 0.6)

### 4.2 Google sign-in, M1 (SPEC-v2 3.1.1)

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
- `DefaultCredentialsError` maps to `missing`; `RefreshError` (for example `invalid_grant`, reauthentication required) maps to `invalid` (10.3). The exception text is never logged or returned.
- The refresh request goes from `google-auth` to `oauth2.googleapis.com` only; the provider records it as a `CallRecord` with `source="google_signin"`.
- The access token is wrapped in `Secret` (name `GOOGLE_SIGNIN`), held in memory, and revealed only by `platform/http.py` for origins in the Vertex spec (`https://discoveryengine.googleapis.com`), as a bearer token plus `X-Goog-User-Project: <project>`.
- v2's own code never opens, copies or writes the credential file.

### 4.3 Redaction and logging (SPEC-v2 3.2)

- `Redactor` holds the set of revealed secret values (registered when loaded) and the patterns in PLAT-FR-13.
  - API: `redact(text) -> str`, plus `RedactingFilter(logging.Filter)`, which rewrites `record.msg`, `record.args` and the exception text.
- `configure_logging(settings)` is called only by `daemon.py` and `cli.py`.
  - It attaches `RedactingFilter` to **every handler**, not to a logger, so records propagated from child and third-party loggers are covered.
  - It sets the `httpx`, `httpcore`, `uvicorn.access` and `mcp` loggers to `WARNING`.
  - Handlers:
    - `RotatingFileHandler(log_dir/research-mcp.jsonl, 10 MB, 5)` with a JSON formatter;
    - `StreamHandler(stderr)` at `WARNING`.
- Log record fields are listed in PLAT-FR-41. `correlation_id` comes from a `contextvars.ContextVar` set per tool call and per job.

### 4.4 Credential scoping in the HTTP client (SPEC-v2 3.3)

- **Hosts:** a request whose host is not in `policy.hosts` fails with `blocked_by_policy`.
- **Auth:**
  - The secret comes from `CredentialResolver`.
  - It is attached only when the request origin is in `policy.auth.origins`.
  - Placement is `header` (name from the spec), `bearer`, or `query` (parameter name from the spec).
  - Query placement is used only where the API offers nothing else, and then the URL is never logged.
- **Errors:** the message text is generic; details go to the log through the redactor.

### 4.5 Local access: loopback, the daemon token and endpoints

- `server.host` defaults to `127.0.0.1`; validation rejects any non-loopback value. `server.token` is `keychain:research-mcp/DAEMON_TOKEN`, the bearer for the shim and API (SPEC-v2 2).
- `daemon.py` runs `research-mcpd`: settings, then `build_app`, then uvicorn on `127.0.0.1` with `access_log` off (SPEC-v2 1).
- `platform/auth.py` holds the daemon token: mint, compare (`hmac.compare_digest`), the HKDF cursor key, and UI one-time tokens (SPEC-v2 1).
- `build_mcp` configures the SDK's `TransportSecuritySettings` to allow only the loopback hosts and origins (SPEC-v2 7.4).
- `research-mcp install` generates `DAEMON_TOKEN` through `SecretProvider.set` if it is absent (SPEC-v2 12.2); `secrets rotate-token` replaces it (SPEC-v2 12.1; PLAT-83).
- Endpoint authentication (SPEC-v2 10.5, held by the health LLD):

| Endpoint | Auth | Returns |
|---|---|---|
| `/healthz` | none | `{"status":"ok","version":"3.x.y"}` |
| `/readyz` | none | Ok when the stores are open, the scheduler is running and the Keychain is readable; 503 otherwise |
| `/api/status` | bearer token or a UI session | JSON of sources, credential metadata, quotas, jobs, cache stats, disk, the archive target and the last 20 notifications |

The UI session, CSRF and Host checks are specified in SPEC-v2 11 and held by the UI LLD.

### 4.6 Local files and destructive actions

- The downloader writes only under `data_dir` (`tmp/` then `files/`), and the model never chooses a path (5.4; HLD-v3 9).
- There is no SQL tool, no caller-chosen path, and files are read only under the cache root; DuckDB, if used internally, is locked down (HLD-v3 9; ADR 0009). SPEC-v2 has no DuckDB design, and the base dependencies exclude duckdb (PLAT-4) (11).
- No hard delete in MCP; annotations mark state-changing tools (HLD-v3 9). The tool rules are part of the tool catalog in SPEC-v2 7.2.

HLD-v3 9 threat rows enforced by this component:

| Threat | Control |
|---|---|
| Secret leaks into chat or logs | Keychain (the Google sign-in excepted, see below); `Secret` type; origin-scoped attachment; header placement; one redaction filter on logs, errors, UI and notifications; errors carry codes, not exception text. |
| Google sign-in token misuse | `gcloud` owns the sign-in; v2 holds only a short-lived access token in memory and attaches it only to `discoveryengine.googleapis.com`. |
| SSRF and hostile downloads | One downloader: https, per-hop host policy, public IPs only with the connection pinned to the checked IP (no second DNS lookup), byte cap, magic bytes, atomic write. |
| Hostile PDFs | Parsing in a separate subprocess per document with a CPU limit, an RSS watchdog, a wall-clock timeout and a page cap; a crash affects only that document. |
| Other local processes call the daemon | Loopback only, bearer token, Host and Origin checks; UI session cookie plus CSRF. |
| Supply chain | Lock file, weekly dependency audit, SHA-pinned CI actions, secret scan. |

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

### 5.1 Conventions and layout (SPEC-v2 1)

- Python 3.12 (uv-managed interpreter, which bundles a current SQLite), `uv`, `src/` layout, package `research_mcp`, version `3.0.0`.
- Typing: mypy strict on `src/`; Pydantic v2 models for everything that crosses a module boundary or the MCP boundary.
- Async: `anyio`; HTTP with `httpx.AsyncClient`; SQLite with `aiosqlite` through the store classes only.
- Time: UTC everywhere (`datetime` with `tzinfo=UTC`), stored as ISO 8601 text; the scheduler converts to local time for 09:00 and quiet hours.
- IDs: ULIDs for internal rows (`works.work_id`, `documents.doc_id`, jobs, batches).
- Tests: pytest with `--import-mode=importlib`; test folders have no `__init__.py`; shared test helpers live in the package `research_mcp.testing` so tests import them by absolute name.
- No em dashes or en dashes in code comments, docs or UI strings.

```
src/research_mcp/
  __init__.py  version.py
  cli.py                      # research-mcp: serve | stdio | doctor | ui | sources | config | install | upgrade | secrets | import-legacy | archive
  daemon.py                   # research-mcpd entry: settings -> build_app -> uvicorn on 127.0.0.1 (access_log off)
  app.py                      # build_app(settings) -> Starlette app (mounts /mcp, /ui, /healthz, /readyz, /api)
  shim.py                     # stdio <-> streamable HTTP relay
  settings.py                 # Settings, SourceSettings, paths
  core/      ids.py models.py specs.py errors.py context.py envelope.py budget.py timeutil.py
  platform/
    secrets.py                # SecretRef, Secret, SecretMeta, SecretProvider, KeychainProvider, FakeProvider
    redact.py                 # Redactor (handler filter + str API)
    logging.py                # configure_logging(settings)
    http.py                   # HttpPort, HttpClient (httpx), CredentialResolver, CallSink, PolicyResolver
    google_adc.py             # GoogleAdcProvider: Google sign-in access tokens via google-auth (M1, extra gcp)
    auth.py                   # daemon token: mint, compare (hmac.compare_digest), HKDF cursor key, UI one-time tokens
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
    server.py                 # build_mcp(services) -> FastMCP; instructions text
    ...
  ui/                         # UI component
  testing/                    # importable fakes for tests: clock.py adapters.py launchctl.py notifier.py
  packaging/launchd/          # *.plist.template (package data, so `research-mcp install` finds them in an installed wheel)
tests/
  unit/ ...   sources/<id>/fixtures/ + test_<id>.py   sources/test_conformance.py
  services/   contract/ (in-memory MCP client)   ui/   security/   live/ (opt-in)
tools/ci.sh  tools/gen_inventory.py  tools/gen_test_plan.py  tools/gen_m0_plan.py
```

The `sources/`, `services/`, `mcp_app/` and `ui/` subtrees are abridged here; SPEC-v2 1 lists them in full.

| Unit | Section | Requirement |
|---|---|---|
| M0-01 | 1; AT-PLAT-03 | Import side effects MUST be attributed to `research_mcp` when any frame of the stack belongs to it, not only the innermost frame; a dependency doing I/O on behalf of a `research_mcp` import (for example settings construction reading the environment at import time) counts. Include that case as a regression test. |

(SPEC-v2 0.6)

### 5.2 Layers and the composition root (HLD-v3 3)

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
- One composition root, `build_app(settings)`, creates everything inside a lifespan. Nothing happens at import.
- Network I/O is async; CPU-heavy work (PDF parsing, chunking, embedding) runs in one short-lived subprocess per task, killed on timeout or memory limit; SQLite access runs in a thread with one writer per database.

### 5.3 HTTP client (SPEC-v2 3.3)

- **Client:** one `httpx.AsyncClient` per daemon. HTTP/2 is on. Connection limits are 50 in total and 8 per host. The user agent is `research-mcp/3.0 (+mailto:<contact>)`.
- **Hosts and auth:** 4.4.
- **Rate limits:** each source gets a `TokenBucket(rate, burst)` and a `ConcurrencyGate(n)` from `policy.rate`. These are kept in one `RateRegistry` for the daemon, so they are global across clients. arXiv runs at 1 request per 3 s, burst 1, concurrency 1.
- **Retries:** 6.1.
- **Size:** responses are streamed; passing `max_bytes` (default from the policy) aborts the call with `too_large`.
- **Telemetry:** every attempt produces a `CallRecord` for the `CallSink`. In the daemon the sink is `StateStore.record_call`, flushed every second.

### 5.4 Downloader (SPEC-v2 3.4)

`Downloader(resolver: Resolver, policy: DownloadPolicy, ...)`. The algorithm is a port of v1's `security.download_pdf_atomic`, with DNS pinning added:

1. Require `https`. Resolve the host through the injected `Resolver` (the system resolver in the daemon, a fake in tests). Reject private, loopback, link-local, multicast and reserved addresses, for both IPv4 and IPv6.
2. Connect through `PinnedTransport` to the **checked IP**, with SNI and the `Host` header set to the hostname. httpx never resolves the name a second time, which closes the DNS-rebinding gap.
3. Set `follow_redirects=False` and follow up to 5 redirects by hand. On every hop, repeat steps 1 and 2 and re-check the scheme and the host policy (`policy.allowed_hosts`, or `public_any`).
4. Stream into `data_dir/tmp/<ulid>.part` with a byte cap. Check `Content-Type` against `policy.media_types`, and check the first bytes: `%PDF-` for PDF; for HTML, `<` after any whitespace.
5. Run `fsync`, compute SHA-256, and move the file atomically to `data_dir/files/<sha256[:2]>/<sha256>.<ext>`. If that file already exists, reuse it.
6. Return `DownloadedFile` (section 4).

**File deletion rule:** a stored file is removed only when no `files` row with the same `sha256` belongs to a document in a non-terminal state (`cached`, `pinned`, `expiring`, `kept`), and no discard of it is still within its trash period.

The downloader's criteria (CACHE-1, CACHE-2 in M0-07) belong to the cache component.

### 5.5 Workers, jobs and the scheduler (SPEC-v2 3.6)

`WorkerRunner` runs every CPU-heavy task in its own subprocess. `ProcessPoolExecutor` is not used, because on macOS it cannot enforce memory limits or kill a running task.

- The task is launched with `anyio.open_process([python, "-m", "research_mcp.platform.workers", <task>])`. Input goes in as JSON on stdin; the result comes back as JSON on stdout.
- In the child, `RLIMIT_CPU` is 120 s. `RLIMIT_AS` is not relied on, because macOS does not enforce it.
- The parent enforces a 180 s wall clock and samples the child's RSS every second with `psutil`. Past 2 GB, or at the timeout, it sends SIGKILL.
- A crash or kill affects only that task, which ends with code `extract_failed`.
- Tasks: `extract_pdf`, `extract_html`, `chunk`, `embed`. At most 2 run at once.

`JobService` provides `submit(kind, params) -> job_id`, `status(job_id)`, `cancel(job_id)` and `list(state)`.

- Job state lives in `state.db.jobs`.
- Progress is pushed to MCP `Context.report_progress` while the caller waits.
- Resumable job kinds store a cursor.

`Scheduler` is driven by the wall clock, not by asyncio timers, which stall while the Mac sleeps.

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

- Interval schedules: probes at their own cadence; `disk_sample` every 15 minutes; `outbox_drain` every 5 s.

`WorkerRunner` arrives in M2 (SPEC-v2 12.4); `JobService` and `Scheduler` are M0-15.

### 5.6 Budget, cursors and the tool boundary (SPEC-v2 3.7)

**Budget.** `core.budget.fit(result, limit_bytes)` trims list items from the end, and shortens long text fields to a marker, until the JSON size fits. It then sets `truncated` and keeps the cursor.

**Cursors.** Cursors are base64url JSON with an HMAC-SHA256 tag. `core.budget` takes the key as a parameter (the daemon derives it as described in 3.1), so that agents cannot forge cursors.

**`@tool_boundary`** is defined in `mcp_app/server.py` (M0-14). Every MCP tool carries this one decorator. It:

- sets the correlation id;
- turns `ToolError` and `HttpError` into the error result;
- maps any other exception to `internal`, logging the traceback through the redactor;
- applies the budget.

| Unit | Section | Requirement |
|---|---|---|
| M0-03 | 3.7, 4; AT-PLAT-31, FR-SRCH-04 | `Budget.fit` MUST keep `FederatedResult.statuses` (one status per source) and MUST fail explicitly when mandatory metadata cannot fit. Its prefix search MUST distinguish "does not validate" from "too large". |

(SPEC-v2 0.6)

### 5.7 Stdio shim

`shim.py` relays stdio to streamable HTTP (SPEC-v2 1). It sends the bearer token from the Keychain; clients never hold it (ADR 0003). If the daemon is down, it asks launchd to start it (through `LaunchctlPort`; `FakeLaunchctl` in tests), retries, and returns one clear MCP error if that fails (PLAT-FR-2). On a 404 or 400 for a session it replays `initialize` once (2.3).

### 5.8 Packaging and CI (SPEC-v2 12.1)

- **Dependencies** in `pyproject.toml`: `mcp>=1.27,<2`, `httpx[http2]`, `anyio`, `pydantic>=2`, `pydantic-settings`, `aiosqlite`, `uvicorn`, `starlette`, `jinja2`, `selectolax`, `defusedxml`, `python-ulid`, `psutil`, `tomli-w`.
- **Extras:** `pdf = ["pymupdf"]`, `embeddings = ["fastembed", "numpy"]` and `macos = ["pyobjc-framework-Cocoa"]`; from M1, `gcp = ["google-auth"]` (with `google.*` added to the mypy `ignore_missing_imports` overrides).
- **Dev group:** `pytest`, `pytest-asyncio`, `pytest-cov`, `respx`, `hypothesis`, `ruff` and `mypy`.
- **`[tool.pytest.ini_options]`:** `addopts = "--import-mode=importlib -m 'not live'"`, `asyncio_mode = "auto"` and `markers = ["live: real upstream calls"]`.
- **`[tool.ruff]`:** `line-length = 100`, `target-version = "py312"`, `extend-exclude = ["tools/gen_test_plan.py", "tools/gen_m0_plan.py"]` (design-time generators, kept outside the code rules); `[tool.ruff.lint] select = ["E","F","I","W","B","UP","SIM","ASYNC","BLE","S","C90"]`; `[tool.ruff.lint.per-file-ignores] "tests/**" = ["S101","S105","S106","S108"]`; `[tool.ruff.lint.mccabe] max-complexity = 12`.
- **`[tool.mypy]`:** `strict = true`, `python_version = "3.12"`, `files = ["src"]`; `[[tool.mypy.overrides]] module = ["fitz.*","fastembed.*","objc.*","Foundation.*","selectolax.*"] ignore_missing_imports = true`.
- **Dev stubs:** `types-defusedxml`, `types-psutil`.
- **Package data:** `research_mcp/platform/migrations/**/*.sql`, `research_mcp/ui/templates/*.html`, `research_mcp/ui/static/*` `research_mcp/packaging/launchd/*.plist.template` and, from M1, `research_mcp/packaging/defaults.toml`.
- **Scripts:** `research-mcp = research_mcp.cli:main` and `research-mcpd = research_mcp.daemon:main`.

`tools/ci.sh` must start with `#!/usr/bin/env bash` and be executable; the ECC gate runs commands without a shell. It has two modes.

**`tools/ci.sh --python-only`** runs on every work unit:

1. `uv run ruff check`
2. `uv run ruff format --check`
3. `uv run mypy src`
4. `uv run pytest -q --cov=research_mcp --cov-report=term` (coverage is reported, not gated)
5. Each generator check, run only when its script exists:
   - `uv run python tools/gen_test_plan.py --check`
   - `uv run python tools/gen_m0_plan.py --check`
   - `uv run python tools/gen_inventory.py --check`

**`tools/ci.sh`** with no flag runs at milestone exit and in GitHub Actions. It adds:

- `--cov-fail-under=85`;
- `uv build`;
- `uv run research-mcp --help`, once `research_mcp/cli.py` exists.

| Unit | Section | Requirement |
|---|---|---|
| M0-01 | 12.1; FR-PLAT-53 | The CI workflow MUST run on macOS and Linux with Python 3.12 and 3.13, pin every action by commit SHA, scan for secrets, and run a weekly dependency audit. |

(SPEC-v2 0.6)

### 5.9 launchd, install and upgrade (SPEC-v2 12.2)

The daemon runs under the `local.research-mcpd` LaunchAgent (2.5). Install is `uv tool install` (or a venv) for the package, then `research-mcp install` (HLD-v3 12).

**`research-mcp install`:**

1. Fills the placeholders.
2. Creates the folders.
3. Generates `DAEMON_TOKEN` through `SecretProvider.set` if it is absent.
4. Runs the foreground `archive_access` write (9.3); this step is added in M2 with the archive service.
5. Loads the three jobs with `launchctl bootstrap gui/$UID`.
6. Prints the client configs.

**`research-mcp upgrade`:**

1. Records the current lock file and the `uv tool` environment path.
2. Stops the daemon.
3. Backs up `state.db` and `cache.db` (online backup API) to `state_dir/backups/pre-upgrade-<timestamp>/`.
4. Runs `uv tool upgrade research-mcp` (or `uv sync` for a source checkout).
5. Runs the migrations, then `doctor --quick`, then restarts the daemon.
6. If doctor reports a critical check, reinstalls the recorded version (`uv tool install research-mcp==<old>`), restores both databases from step 3, and restarts the daemon.

Migrations are forward-only; the step 3 backup is what makes rollback possible.

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

### 6.1 HTTP retries (SPEC-v2 3.3)

- **Retries:** up to 3 attempts on 429, 500, 502, 503 and 504, and on connection errors. If every attempt gets a 429, the call fails with `rate_limited` and the last `retry_after_ms`.
  - The delay is `Retry-After` when present. A delay over 60 s is not waited for; the call fails with `rate_limited` and `retry_after_ms`.
  - Without `Retry-After`, the delay is exponential from a 0.5 s base, with full jitter.
  - Other 4xx responses are not retried.
  - All waiting goes through the injected `Sleeper`, so tests never sleep for real.
- **Errors:** the client raises `HttpError(code: ErrorCode, status: int | None, retry_after_ms: int | None, detail: str | None)`, defined in `core/errors.py`. Before the generic mapping, a non-2xx response is passed to `policy.error_classifier` when the source declares one (for example OpenAlex maps an "Insufficient budget" 429 to `budget_exhausted` with `detail="daily budget"`). The message text is generic; details go to the log through the redactor.

### 6.2 Error mapping elsewhere

| Where | Condition | Result | Source |
| --- | --- | --- | --- |
| `@tool_boundary` | `ToolError` or `HttpError` | The error result with code, message, retryable and correlation_id | SPEC-v2 3.7 |
| `@tool_boundary` | Any other exception | `internal`; traceback logged through the redactor | SPEC-v2 3.7 |
| `KeychainProvider` | Exit 44; exit 36 or 51 or "User interaction is not allowed"; anything else | `missing`; `keychain_locked`; `error`; stderr never logged or returned | SPEC-v2 3.1 |
| `GoogleAdcProvider` | `DefaultCredentialsError`; `RefreshError` | `missing`; `invalid`; exception text never logged or returned | SPEC-v2 3.1.1 |
| `WorkerRunner` | Crash, RSS past 2 GB, or 180 s wall clock | SIGKILL; the task ends with `extract_failed` | SPEC-v2 3.6 |
| `Migrator` | A failing script | The explicit transaction leaves no partial schema | SPEC-v2 3.5 |
| `Migrator` | `user_version` newer than the newest migration; SQLite older than 3.37 | Refuses to open; asserts at start | SPEC-v2 3.5 |
| Shim | Daemon down after the launchd start and retry | One clear MCP error | PLAT-FR-2 |
| `research-mcp upgrade` | Doctor reports a critical check | Reinstall the recorded version, restore both databases, restart | SPEC-v2 12.2 |

### 6.3 Idempotency

- The scheduler runs a missed job once at start or on wake, never once per missed day (SPEC-v2 3.6).
- The shim replays `initialize` once on a session error; stateless HTTP keeps sessions valid across restarts (SPEC-v2 7.4).
- Install generates `DAEMON_TOKEN` only if it is absent (SPEC-v2 12.2).
- The downloader reuses an existing file with the same SHA-256 (SPEC-v2 3.4).
- Keychain writes use `add-generic-password -U` (update if present) (SPEC-v2 3.1).
- Outbox rows are copied to `state.db.review_events` and then deleted, so each database commits on its own (SPEC-v2 3.5).

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

### 7.1 Settings (SPEC-v2 2)

`settings.Settings` (pydantic-settings), loaded from `~/.config/research-mcp/config.toml`, then `RESEARCH_MCP_*` environment overrides (nested with `__`).

| Key | Default | Notes |
|---|---|---|
| `server.host` | `127.0.0.1` | Validation rejects any non-loopback value. |
| `server.port` | `7319` | MCP at `/mcp`, UI at `/ui`. |
| `server.token` | `keychain:research-mcp/DAEMON_TOKEN` | Bearer for the shim and API. |
| `paths.state_dir` | `~/Library/Application Support/research-mcp` | `state.db`, `backups/`, `imports/` |
| `paths.data_dir` | `~/Library/Application Support/research-mcp/cache` | `cache.db`, `files/`, `trash/`, `tmp/` (not in `~/Library/Caches`, which macOS and cleaners may purge) |
| `paths.model_cache_dir` | `~/Library/Caches/research-mcp/models` | Embedding model files only (re-downloadable) |
| `paths.log_dir` | `~/Library/Logs/research-mcp` | |
| `contact.email` | none | Crossref `mailto`, Unpaywall `email`, user agent. Placeholder domains (`example.com`, `example.org`, `test`, `invalid`) are rejected. If unset, sources with `needs_contact` are `unconfigured`; the daemon still starts. |
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
| `notify.webhook_url` | none | OpenClaw inbox (open decision O5); any token goes in Keychain `NOTIFY_WEBHOOK_TOKEN`, never in the URL |
| `notify.quiet_hours` | `"21:00-08:00"` | |
| `disk.cache_warn_bytes` | `5368709120` | |
| `disk.free_warn_bytes` / `free_crit_bytes` | `16106127360` / `5368709120` | |
| `backup.keep` | `7` | Nightly copies of `state.db`, `cache.db` and `config.toml` |
| `sources.<id>.enabled` | spec default | |
| `sources.<id>.budget_cap` | none (`100` for `web` sources) | Daily call cap for metered sources (UI Quota page); resets at local midnight |
| `sources.vertex_<name>` | none | `{ instance_of = "vertex_search", project = "...", location = "global", engine_id = "...", title = "..." }`; one per Vertex AI Search engine (5.5) |
| `sources.google_pse.engine_id` | none | Programmable Search engine id (v1 `GOOGLE_PSE_CX`); not a secret |
| `web.strategy` | `"fallback"` | `fallback` or `all` (5.5) |
| `web.order` | `["vertex_*", "brave_search", "serpapi", "google_pse"]` | `vertex_*` expands to the configured Vertex instances in name order |
| `site_sets.<name>` | `v1_docs` (5.5) | A list of domains; names match `[a-z0-9_]{1,40}` |
| `sources.<id>.<field>` | per spec | For example `sources.dspace_penn.base_url` |
| `credentials.<NAME>.rotate_by` | none | Optional override |

Directories are created at daemon start with mode `0700`.

Per-source sections come from each `SourceSpec` (PLAT-FR-8). The settings model is loaded by `daemon.py` and `cli.py`; importing `settings.py` reads nothing (PLAT-FR-4).

| Unit | Section | Requirement |
|---|---|---|
| M0-04 | 2; AT-PLAT-08, AT-PLAT-09 | Paths MUST be normalized (resolving `..`) before the durable-location check. Credential names MUST keep their canonical case across TOML and `RESEARCH_MCP_` environment overrides, so an environment override updates the same credential the TOML defines. |

(SPEC-v2 0.6)

### 7.2 Optional behavior

| Flag | Default | Safe to switch off? |
| --- | --- | --- |
| `sources.<id>.enabled` | spec default; every `web` source is off until configured (ADR 0012) | Yes: each source can be disabled with a flag (PRD-v4 12) |
| Extras `pdf`, `embeddings`, `macos`, `gcp` | not installed; a search-only install needs none of them (PLAT-FR-51) | Yes: without `gcp`, `vertex_search` shows `unconfigured` with the install command (ADR 0012; PLAT-13) |
| `contact.email` | none | Yes: sources with `needs_contact` become `unconfigured`; the daemon still starts (SPEC-v2 2) |
| `notify.macos` | `true` | not stated (11) |
| `notify.webhook_url` | none | not stated (11) |
| Debug logging (PLAT-FR-42) | no settings key in SPEC-v2 2 | not stated (11) |

## 8. Observability

> **Owner:** A · **Persona:** `sre`

- **Logs:** JSON lines in `log_dir/research-mcp.jsonl`, `RotatingFileHandler` at 10 MB with 5 kept; stderr at `WARNING` (4.3). The launchd daemon job also writes `__LOGS__/daemon.err.log` (2.5). The UI shows recent warnings and errors (HLD-v3 12).
- **Log fields:** time, level, event, correlation id, tool, source, operation, status, error code, latency, bytes, job id, attempt (PLAT-FR-41). `correlation_id` is set per tool call and per job (4.3).
- **Query text** is logged as a hash and length unless debug logging is on (PLAT-FR-42).
- **Noise and leaks:** the `httpx`, `httpcore`, `uvicorn.access` and `mcp` loggers run at `WARNING`; uvicorn access logging is off (4.3; SPEC-v2 1).
- **Call telemetry:** every HTTP attempt emits a `CallRecord` with time, source, operation, status, error code, latency, bytes, rate-limit headers, credential expiry, correlation id and attempt; the daemon's sink is `StateStore.record_call`, flushed every second (5.3; SPEC-v2 4). The Google sign-in refresh is recorded with `source="google_signin"` (4.2).
- **Liveness and readiness:** `/healthz` and `/readyz` (4.5). The watchdog LaunchAgent runs `doctor --liveness --notify` every 900 s, and the doctor LaunchAgent runs `doctor --notify` daily at 08:52 (2.5).
- **Thresholds:** the event loop heartbeat gap stays under 200 ms while a slow source runs (PLAT-75; NFR-2). Alerting, probes and notifications belong to the health component (HLD-v3 7); this component defines no alert of its own.

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

Existing tests cite the earlier `AT-PLAT-nn` IDs in their docstrings. Planned files come from the unit scopes in SPEC-v2 12.3; where a unit has several test files, the file is chosen by best fit [inferred].

| Criterion | Planned tests | Level | Status |
| --- | --- | --- | --- |
| PLAT-1 | `tests/unit/test_version.py::test_version_is_3x_and_matches_metadata` | unit | test linked |
| PLAT-2 | `tests/unit/test_version.py::test_ci_script_is_executable_bash` | unit | test linked |
| PLAT-3 | `tests/unit/test_import_side_effects.py::test_importing_research_mcp_does_no_work`, `test_third_party_modules_cover_base_dependencies`, `test_probe_detects_import_side_effects`, `test_probe_detects_work_done_through_a_dependency` | unit | test linked |
| PLAT-5 | `tests/unit/test_network_guard.py::test_blocks_connect_before_io`, `test_blocks_create_connection_before_io`, `test_blocks_datagrams_before_io`, `test_blocks_name_lookup_before_io`, `test_blocks_reverse_lookup_before_io`, `test_blocks_loopback_lookalikes_before_io`, `test_blocks_async_http_client`, `test_passes_loopback_through`, `test_allows_loopback_server`, `test_live_tests_deselected_by_default`, `test_live_tests_run_unguarded_when_selected`, `test_guard_covers_session_fixtures`, `test_guard_covers_collection` | unit | test linked |
| PLAT-4 | `tests/unit/test_version.py::test_heavy_dependencies_are_extras` | unit | test linked |
| PLAT-30 | `tests/unit/core/test_envelope.py::test_envelope` | unit | test linked |
| PLAT-31 | `tests/unit/core/test_budget.py::test_budget`, `test_statuses_are_mandatory`, `test_invalid_prefix_is_not_a_size_result` | unit | test linked |
| PLAT-32 | `tests/unit/core/test_envelope.py::test_errors` | unit | test linked |
| PLAT-33 | `tests/unit/core/test_envelope.py::test_untrusted` | unit | test linked |
| PLAT-6 | `tests/unit/core/test_models.py::test_models_and_clock` | unit | test linked |
| PLAT-34 | `tests/unit/core/test_budget.py::test_cursors` | unit | test linked |
| PLAT-8 | `tests/unit/test_settings.py::test_defaults`, `test_toml_and_environment`, `test_typed_web_source_defaults`, `test_invalid_values`, `test_webhook_rejects_tokens`, `test_webhook_accepts_plain_url`, `test_rotate_by_is_utc` | unit | test linked |
| PLAT-9 | `tests/unit/test_settings.py::test_paths_and_creation`, `test_reject_purgeable_paths`, `test_normalization_and_symlinks` | unit | test linked |
| PLAT-10 | `tests/unit/test_settings.py::test_non_loopback`, `test_loopback` | unit | test linked |
| PLAT-11 | `tests/unit/test_settings.py::test_placeholder_email`, `test_optional_email` | unit | test linked |
| PLAT-12 | `tests/unit/platform/test_secrets.py::test_parse_valid_references`, `test_parse_rejects_malformed_references`, `test_direct_construction_validates`, `test_parse_error_does_not_echo_input` | unit | test linked |
| PLAT-40 | `tests/unit/platform/test_logging.py` (M0-06) | unit | planned |
| PLAT-41 | `tests/unit/platform/test_logging.py` (M0-06) | unit | planned |
| PLAT-42 | `tests/unit/platform/test_logging.py` (M0-06) | unit | planned |
| PLAT-35 | `tests/unit/platform/test_http.py` (M0-07) | unit | planned |
| PLAT-36 | `tests/unit/platform/test_http.py` (M0-07) | unit | planned |
| PLAT-37 | `tests/unit/platform/test_ratelimit.py` (M0-07) | unit | planned |
| PLAT-38 | `tests/unit/platform/test_http.py` (M0-07) | unit | planned |
| PLAT-39 | `tests/unit/platform/test_http.py` (M0-07) | unit | planned |
| PLAT-50 | `tests/unit/platform/test_stores.py` (M0-08) | unit | planned |
| PLAT-51 | `tests/unit/platform/test_stores.py` (M0-08) | unit | planned |
| PLAT-52 | `tests/unit/platform/test_stores.py` (M0-08) | unit | planned |
| PLAT-53 | `tests/unit/platform/test_stores.py` (M0-08) | unit | planned |
| PLAT-60 | `tests/contract/test_tool_contract.py` (M0-14) | contract | planned |
| PLAT-61 | `tests/contract/test_tool_contract.py` (M0-14) | contract | planned |
| PLAT-62 | `tests/contract/test_tool_contract.py` (M0-14) | contract | planned |
| PLAT-63 | `tests/contract/test_tool_contract.py` (M0-14) | contract | planned |
| PLAT-70 | `tests/unit/test_app.py` (M0-15) | integration | planned |
| PLAT-71 | `tests/unit/test_app.py` (M0-15) | integration | planned |
| PLAT-72 | `tests/unit/test_shim.py` (M0-15) | integration | planned |
| PLAT-73 | `tests/unit/test_shim.py` (M0-15) | integration | planned |
| PLAT-74 | `tests/unit/test_jobs.py` (M0-15) | integration | planned |
| PLAT-75 | `tests/unit/test_app.py` (M0-15) | integration | planned |
| PLAT-76 | `tests/unit/test_scheduler.py` (M0-15) | integration | planned |
| PLAT-77 | `tests/unit/test_shim.py` (M0-15) | integration | planned |
| PLAT-80 | `tests/unit/test_cli.py` (M0-16) | unit | planned |
| PLAT-81 | `tests/unit/test_install.py` (M0-16) | unit | planned |
| PLAT-82 | `tests/unit/test_install.py` (M0-16) | unit | planned |
| PLAT-83 | `tests/unit/test_install.py` (M0-16) | unit | planned |
| PLAT-13 | planned (M1; no file named) | unit | planned |

The offline guard behind PLAT-5:

| Unit | Section | Requirement |
|---|---|---|
| M0-01 | 1, 12.1; AT-PLAT-05, NFR-09 | The offline network guard MUST be installed for the whole test session (a session-scoped autouse fixture or a plugin active before collection), not per test. It MUST refuse, before any I/O, `socket.socket.connect`, `connect_ex`, `sendto`, `sendmsg` and `socket.create_connection` to non-loopback addresses, and `getaddrinfo`, `gethostbyname`, `gethostbyname_ex` and `gethostbyaddr` for non-loopback names. Loopback MUST keep working. Negative tests MUST prove each refusal happens before I/O. |

(SPEC-v2 0.6)

Fakes used by these tests: `FakeProvider` (`platform/secrets.py`), `FakeClock` and a fake `Sleeper` (`testing/clock.py`), fake adapters (`testing/adapters.py`), `FakeLaunchctl` (`testing/launchctl.py`) and the in-memory MCP client (`tests/contract/conftest.py`) (TEST-PLAN-v3 7). Owner checks OC-01, OC-02, OC-08, OC-09 and OC-10 cover PLAT-FR-1, PLAT-FR-10, PLAT-FR-53, PLAT-FR-55 and PLAT-FR-57 on the Mac (TEST-PLAN-v3 6).

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| One daemon per Mac with a stdio shim (ADR 0002) | Each v1 client started its own process, so rate limits broke across clients and there was no shared health (REVIEW-v1 3, finding 13) | One process per client (v1) |
| Secrets in the Keychain, references in config (ADR 0003) | v1 kept three plaintext copies of keys in client configs (OPS-11) | Environment variables in client configs (v1) |
| One composition root; no work at import (ADR 0004) | Import-time side effects in v1 (REVIEW-v1 3, finding 2) | not stated |
| Async I/O; CPU work in worker processes (ADR 0005) | Every v1 tool blocked the event loop (REVIEW-v1 3, finding 3) | not stated |
| One subprocess per CPU task | On macOS `ProcessPoolExecutor` cannot enforce memory limits or kill a running task (SPEC-v2 3.6) | `ProcessPoolExecutor` |
| Parent enforces RSS and wall clock | macOS does not enforce `RLIMIT_AS` (SPEC-v2 3.6) | `RLIMIT_AS` in the child |
| Scheduler on the wall clock | asyncio timers stall while the Mac sleeps (SPEC-v2 3.6) | asyncio timers |
| Migrator issues `BEGIN IMMEDIATE` and `COMMIT` itself | `executescript` commits implicitly (SPEC-v2 3.5) | `executescript` |
| Outbox between `cache.db` and `state.db` | Neither database needs a transaction that spans both (SPEC-v2 3.5) | A cross-database transaction |
| Downloader pins the connection to the checked IP | httpx never resolves the name a second time, which closes the DNS-rebinding gap (SPEC-v2 3.4) | Letting httpx resolve the name |
| Redaction filter on every handler | Records propagated from child and third-party loggers are covered (SPEC-v2 3.2) | A filter on a logger |
| Keychain writes through `security -i` on stdin | The value never appears in a process argument list (SPEC-v2 3.1) | Passing `-w <value>` as an argument |
| Cursor key derived from `DAEMON_TOKEN` by HKDF | No separate secret is stored; agents cannot forge cursors (SPEC-v2 3.1, 3.7) | A separate stored key |
| Stateless streamable HTTP at `/mcp` | A daemon restart never invalidates a client session (SPEC-v2 7.4) | Stateful sessions |
| SQLite is the only store (ADR 0008, ADR 0011) | No separate archive database is needed; DuckDB is not used for storage | A persisted DuckDB index (REVIEW-v1 6, dropped) |
| Google sign-in through `google-auth` (ADR 0012) | `gcloud` owns the credential; v2 holds only a short-lived token in memory | An API key in the Keychain |
| Forward-only migrations with a pre-upgrade backup | The step 3 backup makes rollback possible (SPEC-v2 12.2) | Down migrations |

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

- [ ] Q: SPEC-v2 3.1.1 maps `RefreshError` to `invalid`, but `SecretState` in SPEC-v2 3.1 has only `ok`, `missing`, `keychain_locked` and `error`. Does `SecretState` gain `invalid`, or does `RefreshError` map to another state?
- [ ] Q: PLAT-FR-50 and PLAT-80 list ten CLI subcommands, but SPEC-v2 1 and 12.1 also define `archive` (`archive reindex`). Should `--help` list `archive`, and should PLAT-FR-50 name it?
- [ ] Q: PLAT-FR-57 says backups are optionally copied to `Research Archive/_state/` in Drive, but SPEC-v2 9.8 and the settings table in SPEC-v2 2 have no Drive copy and no key for it. Where is that copy designed?
- [ ] Q: PLAT-FR-40 says logs rotate "with 5 files kept"; SPEC-v2 3.2 uses `RotatingFileHandler(..., 10 MB, 5)`, whose backup count of 5 keeps five old files plus the current one. Which count is intended?
- [ ] Q: PLAT-FR-42 depends on "debug logging", but SPEC-v2 2 has no settings key for it, and no hash algorithm is named for query text (`state.db` has `searches.query_hash`, SPEC-v2 10.1). What are the key and the algorithm?
- [ ] Q: PLAT-FR-15 says `SIGHUP` re-reads secrets. SPEC-v2 3.1 defines `SecretCache.reload()`, but no section wires a `SIGHUP` handler. Where is it specified?
- [ ] Q: PLAT-FR-16 says the daemon token can be rotated from the UI; SPEC-v2 specifies only the CLI command `secrets rotate-token`. Which UI action rotates it?
- [ ] Q: PLAT-FR-22 constrains DuckDB "if used internally", but ADR 0011 says DuckDB is not used for storage, SPEC-v2 12.1 lists no duckdb dependency, and PLAT-4 requires the base dependencies to exclude duckdb. Is PLAT-FR-22 still needed?
- [ ] Q: PLAT-FR-10 says configuration holds only `keychain:research-mcp/<NAME>` references, while SPEC-v2 3.1 and PLAT-12 also accept `env:NAME`, and NFR-3 allows no secrets at rest outside the Keychain. Where may `env:` references be used?
- [ ] Q: The user agent is `research-mcp/3.0 (+mailto:<contact>)` (SPEC-v2 3.3), but `contact.email` may be unset (SPEC-v2 2). What user agent is sent without a contact?
- [ ] Q: PLAT-FR-55 says upgrade runs `doctor` and rolls back on a failed `doctor`; SPEC-v2 12.2 runs `doctor --quick` and rolls back only on a critical check, and also restores both databases. Which behavior is the requirement?
- [ ] Q: `build_mcp`, `@tool_boundary` and the server instructions live in `mcp_app/server.py`, and `tests/contract/` holds PLAT-60 to PLAT-63, but `sdd.config.json` maps both paths to the search component. Which component owns them?
- [ ] Q: SPEC-v2 4 (`core/specs.py`, `core/models.py`) is in this component's paths in `sdd.config.json` and is checked by PLAT-6, but it was not among this LLD's sources. Should this LLD carry SPEC-v2 4, or does another LLD own it?
- [ ] Q: PLAT-FR-57 is a platform requirement, but `services/backup.py` (`BackupService`) is mapped to the cache component. Which LLD owns the backup design?
- [ ] Q: PLAT-70 to PLAT-77 are integration criteria, but SPEC-v2 12.3 places their test files under `tests/unit/`. Should the files move to an integration folder, or is the level wrong?
- [ ] Q: No machine-readable contract exists in `docs/contracts/` for the envelope, the error codes, the CLI or the endpoints. Which of these should get one?
- [ ] Q: Is it safe to switch off `notify.macos`, `notify.webhook_url` and debug logging (7.2)? The sources do not say.

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
