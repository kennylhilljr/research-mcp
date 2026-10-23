---
title: "Security low level design"
type: lld
version: 1
status: draft
owner: "Kenny Hill"
prefix: SEC
component: security
parent: docs/spec/SPEC-v3.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# LLD: Security (v1)

This LLD is cross-cutting. The controls it lists are implemented in modules that other LLDs own, chiefly [LLD-platform-v1](LLD-platform-v1.md) (settings, secrets, redaction, logging, HTTP client, `platform/auth.py`, downloader, workers, stores, the MCP app and the daemon) and [LLD-ui-v1](LLD-ui-v1.md) (UI routes, `ui/auth.py`, `ui/csrf.py`). Those LLDs own the names; this one owns the trust boundaries, the enforcement points, the checks and the security test plan. Every name below is quoted from SPEC-v2 unchanged. Product requirements are in [PRD-security-v1](../prd/components/PRD-security-v1.md).

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

Governing section: SPEC-v3 section 9 (security architecture; SPEC-v3 keeps HLD-v3's numbering).

This component defines no functional requirement of its own (PRD-security-v1 2.4). It satisfies the following requirements of other components and the parent through its criteria.

| Requirement | Criteria | SPEC section |
| --- | --- | --- |
| PLAT-FR-3 | SEC-11, SEC-12 | SPEC-v3 section 9 |
| PLAT-FR-10 | SEC-2, SEC-13 | SPEC-v3 section 9 |
| PLAT-FR-11 | SEC-1 | SPEC-v3 section 9 |
| PLAT-FR-12 | SEC-8, SEC-9 | SPEC-v3 section 9 |
| PLAT-FR-13 | SEC-5, SEC-6, SEC-14, SEC-7 | SPEC-v3 section 9 |
| PLAT-FR-14 | SEC-9, SEC-10 | SPEC-v3 section 9 |
| PLAT-FR-15 | SEC-4 | SPEC-v3 section 9 |
| PLAT-FR-16 | SEC-13 | SPEC-v3 section 9 |
| PLAT-FR-20 | SEC-21 | SPEC-v3 section 9 |
| PLAT-FR-22 | SEC-21 | SPEC-v3 section 9 |
| PLAT-FR-25 | SEC-22 | SPEC-v3 section 9 |
| PLAT-FR-27 | SEC-20 | SPEC-v3 section 9 |
| CACHE-FR-3 | SEC-8 | SPEC-v3 section 9 |
| CACHE-FR-10 | SEC-23 | SPEC-v3 section 9 |
| HLTH-FR-20 | SEC-3 | SPEC-v3 section 9 |
| HLTH-FR-23 | SEC-4 | SPEC-v3 section 9 |
| NFR-3 | SEC-2 | SPEC-v3 section 9 |
| NFR-4 | SEC-1, SEC-5, SEC-7, SEC-10 | SPEC-v3 section 9 |
| NFR-6 | SEC-22 | SPEC-v3 section 9 |
| NFR-7 | SEC-11 | SPEC-v3 section 9 |

Criteria of this component: SEC-1, SEC-2, SEC-13, SEC-3, SEC-4, SEC-5, SEC-6, SEC-14, SEC-7, SEC-8, SEC-9, SEC-10, SEC-11, SEC-12, SEC-20, SEC-21, SEC-22, SEC-23. Invariants: SEC-INV-1 to SEC-INV-11.

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

No machine-readable contract exists in `docs/contracts/` yet. The security-relevant wire contracts, from SPEC-v2:

**Endpoint authentication** (SPEC-v2 10.5, verbatim):

| Endpoint | Auth | Returns |
|---|---|---|
| `/healthz` | none | `{"status":"ok","version":"3.x.y"}` |
| `/readyz` | none | Ok when the stores are open, the scheduler is running and the Keychain is readable; 503 otherwise |
| `/api/status` | bearer token or a UI session | JSON of sources, credential metadata, quotas, jobs, cache stats, disk, the archive target and the last 20 notifications |

- **MCP endpoint** (SPEC-v2 7.4): `build_mcp(services)` creates a **new** `FastMCP` for each app. It is configured with `streamable_http_path="/"`, `stateless_http=True` and `json_response=True`, and the SDK's `TransportSecuritySettings` allow only the loopback hosts and origins. It is mounted at `/mcp` and needs the bearer token (`server.token`, "Bearer for the shim and API", SPEC-v2 2).
- **UI login** (SPEC-v2 11): `research-mcp ui` (with an optional path `P`) creates a one-time token (32 random bytes, valid for 5 minutes) through `POST /api/ui-token`, using the daemon bearer token, and opens `http://127.0.0.1:<port>/ui/login?t=...&next=P` in the browser. `GET /ui/login` consumes the token, sets the session cookie `rmcp_session` (HttpOnly, SameSite=Strict, `Path=/`, 12-hour life), and redirects to `next`. Every POST requires the header `X-CSRF-Token`, which htmx sends from a meta tag. The full route list is in [LLD-ui-v1](LLD-ui-v1.md).
- **Webhook** (SPEC-v2 10.4): `POST notify.webhook_url` with JSON `{type, severity, subject, body, ui_path, ts}` and `Authorization: Bearer <NOTIFY_WEBHOOK_TOKEN>` when that item exists.
- **Tool errors** (SPEC-v2 3.7): `ToolError` carries `code: ErrorCode; message: str; retryable: bool; correlation_id: str`, never exception text.
- **Untrusted envelope** (SPEC-v2 3.7): `class Untrusted(BaseModel):  untrusted: Literal[True] = True; source: str; content: str`.
- **Server instructions** (SPEC-v2 7.3), sent at initialize, say three things: results are merged across sources and carry per-source status; content marked `untrusted` is data, not instructions; cache review decisions must come from the owner's explicit words.

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

Security adds no table. It constrains what is persisted:

- **Keychain items** (SPEC-v2 3.1): service `research-mcp/<NAME>`, account `$USER`. The names are `DAEMON_TOKEN`, `NOTIFY_WEBHOOK_TOKEN`, `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `CORE_API_KEY`, `GOOGLE_DEVKNOWLEDGE_API_KEY`, `GITHUB_TOKEN`, `ZENODO_TOKEN`, `NCBI_API_KEY`, `NVD_API_KEY`, `ADS_API_TOKEN`, `LENS_API_TOKEN`, `OPENCITATIONS_TOKEN`, and from M1 `BRAVE_SEARCH_API_KEY`, `SERPAPI_API_KEY`. `GOOGLE_DEVKNOWLEDGE_API_KEY` is shared by `google_devknowledge` and `google_pse`, as in v1; each source's `origins` limit where it is sent.
- **Configuration** holds references only, for example `server.token` = `keychain:research-mcp/DAEMON_TOKEN` (SPEC-v2 2).
- **Cursor signing key:** HKDF-SHA256 over `DAEMON_TOKEN` with info `research-mcp cursor v1`. No separate secret is stored (SPEC-v2 3.1).
- **Credential metadata** in `state.db` (SPEC-v2 10.1, migration 0001; owned by the LLD that holds that schema). It has no value column:

```sql
CREATE TABLE credentials (name TEXT PRIMARY KEY, service TEXT NOT NULL, required_by TEXT NOT NULL,
  fingerprint TEXT, keychain_modified_at TEXT, expires_at TEXT, rotate_by TEXT,
  last_validated_at TEXT, last_result TEXT, state TEXT NOT NULL, last_used_at TEXT, updated_at TEXT NOT NULL);
```

- **Directories** are created at daemon start with mode `0700` (SPEC-v2 2).

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

The SPEC fixes most of these controls; where it leaves a choice open, the choice is listed in section 11 for the control owner instead of being decided here.

### 4.1 Trust boundaries

From HLD-v3 2, with who is trusted and why.

| Boundary | Who is trusted | Why | Main enforcement points |
| --- | --- | --- | --- |
| 1. Upstream content is untrusted | No one: everything that comes from an API or a downloaded file is data; it is labeled untrusted when returned to a model (HLD-v3 2) | Fetched documents can carry prompt injection that steers a model toward unsafe tools (ADR 0009 context, OPS-10) | E24, E25, E27, E31, E32, E33 |
| 2. Local callers are authenticated | Only the shim (with the bearer token) and the UI (with a session) can call the daemon (HLD-v3 2); the CLI uses the same bearer token for `POST /api/ui-token` (SPEC-v2 11) | Other local processes may call the daemon (HLD-v3 9) | E1 to E11, E30 |
| 3. Secrets never leave the HTTP layer except to their origin | Only `platform/http.py`, `platform/mcp_client.py` and `platform/auth.py` may reveal a secret (ADR 0003); a secret goes only to an origin in `policy.auth.origins` (SPEC-v2 3.3) | v1 sent the CORE key to third-party hosts and echoed keys from URLs into chat (OPS-03, OPS-04) | E12 to E23 |
| Keychain access | `/usr/bin/security`: items written by it trust that binary, so reads by the daemon do not prompt, even after Python upgrades (SPEC-v2 3.1) | Avoids a prompt per read; the trust is in the system binary, not the interpreter | E13, E14 |
| Google sign-in | `gcloud` owns the sign-in; v2 holds only a short-lived access token in memory (HLD-v3 9) | The one credential outside the Keychain (ADR 0012) | E20 |

### 4.2 Threat model

HLD-v3 9, verbatim:

| Threat | Control |
|---|---|
| Prompt-injected model tries to read local files | No SQL tool; no caller-chosen paths; files only under the cache root; DuckDB (if used internally) locked down ([ADR 0009](../adr/0009-no-sql-untrusted-content.md)). |
| Prompt-injected model tries to delete data | No hard delete in MCP; the only MCP discard is a review decision inside an open batch, recorded as an agent decision, sent to a 7-day trash and announced to the owner at once with an undo link; the owner is notified again 24 hours before any purge; annotations mark state-changing tools. |
| Secret leaks into chat or logs | Keychain (the Google sign-in excepted, see below); `Secret` type; origin-scoped attachment; header placement; one redaction filter on logs, errors, UI and notifications; errors carry codes, not exception text. |
| Paid web-search spend runs away | Web sources off until configured, never in the default fan-out, fallback order (one paid query per page), daily caps that switch a source to `budget_exhausted`. |
| Google sign-in token misuse | `gcloud` owns the sign-in; v2 holds only a short-lived access token in memory and attaches it only to `discoveryengine.googleapis.com`. |
| SSRF and hostile downloads | One downloader: https, per-hop host policy, public IPs only with the connection pinned to the checked IP (no second DNS lookup), byte cap, magic bytes, atomic write. |
| Hostile PDFs | Parsing in a separate subprocess per document with a CPU limit, an RSS watchdog, a wall-clock timeout and a page cap; a crash affects only that document. |
| Other local processes call the daemon | Loopback only, bearer token, Host and Origin checks; UI session cookie plus CSRF. |
| Upstream drift returns wrong data | Probes check response shape; fixtures pinned in tests; per-source disable. |
| Supply chain | Lock file, weekly dependency audit, SHA-pinned CI actions, secret scan. |

### 4.3 Enforcement points

Criteria from other components use their new IDs (for example `PLAT-10` for `AT-PLAT-10`, `UI-2` for `AT-UI-02`).

| # | Control | Enforcement point | Check | Invariant | Criteria |
| --- | --- | --- | --- | --- | --- |
| E1 | Loopback bind | `settings.Settings`, key `server.host` (default `127.0.0.1`); `daemon.py` runs uvicorn on 127.0.0.1 (access_log off) | "Validation rejects any non-loopback value" (SPEC-v2 2) | SEC-INV-1 | PLAT-10, PLAT-71 |
| E2 | MCP Host and Origin | `build_mcp(services)` with `TransportSecuritySettings` | Allow only the loopback hosts and origins (SPEC-v2 7.4) | SEC-INV-1, SEC-INV-2 | SEC-12 |
| E3 | Bearer token on `/mcp` and `/api` | `platform/auth.py` (daemon token: mint, compare) | Missing or wrong token gets 401; comparison with `hmac.compare_digest` | SEC-INV-2 | SEC-11 |
| E4 | Unauthenticated endpoints | `app.py` mounts `/healthz` and `/readyz` | Only these two answer without auth (SPEC-v2 10.5) | SEC-INV-2 | PLAT-70 |
| E5 | `/api/status` | `app.py` | Bearer token or a UI session (SPEC-v2 10.5) | SEC-INV-2 | SEC-11 |
| E6 | UI one-time token | `platform/auth.py` (UI one-time tokens); `ui/auth.py`; `POST /api/ui-token`; `GET /ui/login` | 32 random bytes, valid 5 minutes, minted with the daemon bearer token, consumed on login (SPEC-v2 11) | SEC-INV-2 | UI-2 |
| E7 | UI session | `ui/auth.py`, cookie `rmcp_session` | HttpOnly, SameSite=Strict, `Path=/`, 12-hour life (SPEC-v2 11) | SEC-INV-2 | UI-2 |
| E8 | CSRF | `ui/csrf.py` | Every POST requires the header `X-CSRF-Token` (SPEC-v2 11) | SEC-INV-2 | UI-3 |
| E9 | UI Host and Origin | `ui/auth.py` [inferred: the SPEC names the check, not the module] | The Host must be `127.0.0.1:<port>` or `localhost:<port>`; if an Origin header is present, it must match (SPEC-v2 11) | SEC-INV-1, SEC-INV-2 | UI-2 |
| E10 | Tokens kept out of access logs | `daemon.py` (uvicorn access_log off) | "Uvicorn access logging is off, so tokens never reach a log" (SPEC-v2 11) | SEC-INV-4 | UI-2 |
| E11 | No token in notifications | `services/notify.py`; `cli.py` `ui` command | The `ui` command mints its one-time login token when the notification is clicked, so no token sits in the notification itself, in a process argument list or in Notification Center (SPEC-v2 10.4) | SEC-INV-4, SEC-INV-6 | HLTH-32 |
| E12 | Secret wrapper | `platform/secrets.py` `Secret` | Text form `Secret(name=..., fp=...)`; `reveal()` called only in `platform/http.py`, `platform/mcp_client.py` and `platform/auth.py` (SPEC-v2 3.1) | SEC-INV-4 | SEC-1 |
| E13 | Keychain read | `KeychainProvider.get` | `/usr/bin/security find-generic-password -s <service> -a <user> -w`, 5 s timeout; stderr text is never logged or returned (SPEC-v2 3.1) | SEC-INV-4 | SEC-2 |
| E14 | Keychain write | `KeychainProvider.set`; `SecretRef` | `/usr/bin/security -i` with the command on stdin; values checked for printable characters first; `SecretRef` validates on construction (SPEC-v2 3.1, 0.6) | SEC-INV-6 | SEC-13 |
| E15 | Metadata without value | `SecretProvider.metadata` | The read command without `-w`; only the `mdat` attribute is parsed (SPEC-v2 3.1) | SEC-INV-3 | SEC-3 |
| E16 | Metadata only at rest | `state.db` table `credentials` | No value column (SPEC-v2 10.1) | SEC-INV-3 | SEC-3 |
| E17 | Rotation without restart | `SecretCache.reload` | Re-reads secrets and returns the names whose fingerprint changed (SPEC-v2 3.1) | (supports rotation) | SEC-4 |
| E18 | Origin-scoped attachment | `HttpClient` (`platform/http.py`) with `CredentialResolver` and `AuthSpec.origins` | Attached only when the request origin is in `policy.auth.origins`; placement `header`, `bearer` or `query`; query only where the API offers nothing else, and then the URL is never logged (SPEC-v2 3.3) | SEC-INV-5, SEC-INV-4 | SEC-8, SEC-9 |
| E19 | Host policy | `HttpClient` | A request whose host is not in `policy.hosts` fails with `blocked_by_policy` (SPEC-v2 3.3) | SEC-INV-5 | PLAT-36 |
| E20 | Google sign-in | `platform/google_adc.py` `GoogleAdcProvider`; `platform/http.py` | Token revealed only by `platform/http.py` for origins in the Vertex spec (`https://discoveryengine.googleapis.com`); v2's own code never opens, copies or writes the credential file (SPEC-v2 3.1.1) | SEC-INV-5, SEC-INV-11 | SRC-32 |
| E21 | Webhook token | `services/notify.py`; settings key `notify.webhook_url` | Any token goes in Keychain `NOTIFY_WEBHOOK_TOKEN`, never in the URL; sent as `Authorization: Bearer` (SPEC-v2 2, 10.4) | SEC-INV-3, SEC-INV-4 | HLTH-32 |
| E22 | Redaction | `platform/redact.py` `Redactor`, `RedactingFilter`; `platform/logging.py` `configure_logging` | Filter on every handler; `httpx`, `httpcore`, `uvicorn.access` and `mcp` loggers at `WARNING` (SPEC-v2 3.2) | SEC-INV-4 | SEC-5, SEC-6, SEC-7, SEC-14 |
| E23 | Generic errors | `HttpError` (`core/errors.py`); `@tool_boundary` (`mcp_app/server.py`) | Message text is generic, details go to the log through the redactor; any other exception maps to `internal` with the traceback logged through the redactor (SPEC-v2 3.3, 3.7) | SEC-INV-4 | SEC-10, PLAT-62 |
| E24 | Untrusted envelope | `core/envelope.py` `Untrusted`; server instructions in `mcp_app/server.py` | Fetched text in `read`, `search_cache` and `get_work` is inside the envelope; instructions say it is data (SPEC-v2 3.7, 7.3) | (NFR-6) | SEC-22, PLAT-33, PLAT-61 |
| E25 | No SQL tool | Tool catalog in `mcp_app/` (17 tools) | None of the 17 tools is a SQL tool (SPEC-v2 7.2) | SEC-INV-8 | SEC-21 |
| E26 | DuckDB lockdown | Any internal DuckDB connection | External access off, allowed directories limited, extension auto-install and auto-load off, configuration locked (ADR 0009) | SEC-INV-7 | SEC-21 |
| E27 | No caller-chosen path | Tool signatures in `mcp_app/`; cache service | No tool reads local files outside the cache root or accepts a caller-chosen path (ADR 0009) | SEC-INV-7 | CACHE-11 |
| E28 | No hard delete | `mcp_app/tools_library.py`, `mcp_app/tools_review.py` [inferred: the SPEC names the tools, not their files] | `library` cannot discard; the only MCP discard is `cache_review_decide`, only for items in an open batch, recorded with `decided_by="agent"` and `decided_channel="mcp"`, with an immediate notification and undo link; there is no hard-delete tool (SPEC-v2 7.2) | SEC-INV-9 | SEC-20, CACHE-34, CACHE-48 |
| E29 | Tool annotations | `@tool_boundary` and tool registration | Every tool declares MCP annotations (ADR 0009; SPEC-v2 7.2) | SEC-INV-9 | PLAT-60 |
| E30 | Clients never hold the token | `shim.py` (`research-mcp stdio`); `cli.py` `install` | The shim reads the token from the Keychain; printed client configs contain no secret (ADR 0002, ADR 0003) | SEC-INV-10 | PLAT-82 |
| E31 | Hostile PDFs | `platform/workers.py` `WorkerRunner` | One subprocess per task; `RLIMIT_CPU` 120 s; 180 s wall clock; RSS sampled every second, SIGKILL past 2 GB; a crash ends that task with `extract_failed`; page cap `limits.pdf_pages` (SPEC-v2 3.6, 2) | (HLD-v3 9) | SEC-23, CACHE-14 |
| E32 | SSRF and hostile downloads | `platform/download.py` `Downloader`, `PinnedTransport` | See [LLD-platform-v1](LLD-platform-v1.md) (SPEC-v2 3.4) | SEC-INV-7 | CACHE-1 |
| E33 | Adapter isolation | `sources/*` | Adapters parse XML with `defusedxml` and may not import `httpx`, `socket` or `research_mcp.platform.secrets`, among others (SPEC-v2 4) | SEC-INV-5 | SRC-7, SRC-1 |
| E34 | Cursor integrity | `core/budget.py` with the key from `platform/auth.py` | HMAC-SHA256 tag so that agents cannot forge cursors (SPEC-v2 3.7) | (none) | PLAT-34 |
| E35 | Supply chain | `.github/workflows/ci.yml`; `pyproject.toml` (ruff rule set `S`) | SHA-pinned actions, secret scan, weekly dependency audit, lock file (HLD-v3 9; SPEC-v2 0.6, 12.1) | (HLD-v3 9) | planned |

### 4.4 Invariant coverage

Every invariant mapped to its enforcement points and the P1 criteria that check it. A gap is listed in section 11.

| Invariant | Enforcement points | Criteria (this component) | Criteria (other components) | Gap |
| --- | --- | --- | --- | --- |
| SEC-INV-1 | E1, E2, E9 | SEC-12 | PLAT-10, PLAT-71, UI-1 | None |
| SEC-INV-2 | E2 to E9 | SEC-11, SEC-12 | PLAT-70, UI-2, UI-3 | None |
| SEC-INV-3 | E15, E16, E21 | SEC-2, SEC-3 | PLAT-12, PLAT-81, HLTH-32 | No criterion scans files at rest (config, `state.db`, backups) for secret values |
| SEC-INV-4 | E10 to E13, E18, E22, E23 | SEC-1, SEC-5, SEC-6, SEC-7, SEC-9, SEC-10, SEC-14 | HLTH-34, UI-4, PLAT-62 | Tool results are covered only by PLAT-62 (errors); no criterion scans successful tool results for secrets |
| SEC-INV-5 | E18, E19, E20, E33 | SEC-8, SEC-9 | PLAT-36, SRC-32, SRC-7 | None |
| SEC-INV-6 | E11, E14 | SEC-13 | HLTH-32 | None |
| SEC-INV-7 | E26, E27, E32 | SEC-21 (DuckDB part only) | CACHE-11, CACHE-1 | No SEC criterion of its own |
| SEC-INV-8 | E25 | SEC-21 | none | None |
| SEC-INV-9 | E28, E29 | SEC-20 | CACHE-34, CACHE-48, PLAT-60 | None |
| SEC-INV-10 | E30 | none | PLAT-82 | No SEC criterion of its own |
| SEC-INV-11 | E20 | none | SRC-32 | No SEC criterion of its own (M1) |

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

The modules belong to other LLDs. This section quotes the parts that carry the security checks.

**Layout entries** (SPEC-v2 1):

```
  platform/
    secrets.py                # SecretRef, Secret, SecretMeta, SecretProvider, KeychainProvider, FakeProvider
    redact.py                 # Redactor (handler filter + str API)
    logging.py                # configure_logging(settings)
    http.py                   # HttpPort, HttpClient (httpx), CredentialResolver, CallSink, PolicyResolver
    google_adc.py             # GoogleAdcProvider: Google sign-in access tokens via google-auth (M1, extra gcp)
    auth.py                   # daemon token: mint, compare (hmac.compare_digest), HKDF cursor key, UI one-time tokens
  ui/
    routes.py auth.py csrf.py
```

**Secrets** (SPEC-v2 3.1, verbatim):

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

- **Read:** `/usr/bin/security find-generic-password -s <service> -a <user> -w`, run with a 5 s timeout. Exit 44 (not found) maps to `missing`. Exit 36 or 51, or "User interaction is not allowed", maps to `keychain_locked`. Anything else maps to `error`. stderr text is never logged or returned.
- **Metadata:** the same command without `-w`; only the `mdat` attribute is parsed.
- **Write:** `/usr/bin/security -i` with `add-generic-password -U -s <service> -a <user> -w <value>` written to stdin, so the value never appears in a process argument list. Values are checked for printable characters first, so `security -w` never returns a hex dump.
- **Clarification** (SPEC-v2 0.6), verbatim: "| M0-05 | 3.1; AT-PLAT-12, AT-SEC-13 | `SecretRef` MUST validate on construction: the name matches the allowed pattern, and a Keychain reference's service is exactly `research-mcp/<NAME>`. No control character (in particular a newline) may reach the `security -i` script. `FakeProvider.metadata` MUST behave like `KeychainProvider.metadata` (no metadata for `env:` references). |" (SPEC-v2 0.6)

**Google sign-in** (SPEC-v2 3.1.1, M1): `GoogleAdcProvider` implements `SecretProvider` for backend `gcloud_adc` (reference text `gcloud_adc:GOOGLE_SIGNIN`); `set` raises `NotImplementedError` because `gcloud` owns the sign-in. Loading and refreshing run through `anyio.to_thread.run_sync`. The refresh request goes from `google-auth` to `oauth2.googleapis.com` only and is recorded as a `CallRecord` with `source="google_signin"`. The access token is wrapped in `Secret` (name `GOOGLE_SIGNIN`), held in memory, and revealed only by `platform/http.py` for `https://discoveryengine.googleapis.com`, as a bearer token plus `X-Goog-User-Project: <project>`.

**Redaction and logging** (SPEC-v2 3.2, verbatim):

- `Redactor` holds the set of revealed secret values (registered when loaded) and the patterns in FR-PLAT-13.
  - API: `redact(text) -> str`, plus `RedactingFilter(logging.Filter)`, which rewrites `record.msg`, `record.args` and the exception text.
- `configure_logging(settings)` is called only by `daemon.py` and `cli.py`.
  - It attaches `RedactingFilter` to **every handler**, not to a logger, so records propagated from child and third-party loggers are covered.
  - It sets the `httpx`, `httpcore`, `uvicorn.access` and `mcp` loggers to `WARNING`.

The patterns of PLAT-FR-13 are `key=`, `api_key=`, `token=`, `Authorization`, `X-Subscription-Token`, `x-goog-api-key`, `AIza`, `ghp_` and `github_pat_` prefixes.

**Credential attachment** (SPEC-v2 3.3 and 4):

```python
@dataclass(frozen=True)
class AuthSpec:
    secrets: tuple[str, ...]                 # Keychain names
    required: bool
    placement: Literal["header", "query", "bearer"]
    param: str                               # header or query name
    origins: tuple[str, ...]                 # credential attached only for these origins (scheme://host)
    signup_url: str
    validation: Literal["probe", "github_rate_limit", "header_expiry", "none"] = "probe"
```

- The secret comes from `CredentialResolver`.
- It is attached only when the request origin is in `policy.auth.origins`.
- Placement is `header` (name from the spec), `bearer`, or `query` (parameter name from the spec).
- Query placement is used only where the API offers nothing else, and then the URL is never logged.

**Daemon token** (`platform/auth.py`, SPEC-v2 1 and 3.1): mint, compare with `hmac.compare_digest`, HKDF cursor key, UI one-time tokens. `research-mcp install` generates `DAEMON_TOKEN` through `SecretProvider.set` if it is absent (SPEC-v2 12.2); `secrets rotate-token` replaces it (SPEC-v2 12.1).

**Tool boundary** (SPEC-v2 3.7): every MCP tool carries `@tool_boundary`, which sets the correlation id, turns `ToolError` and `HttpError` into the error result, maps any other exception to `internal` (logging the traceback through the redactor), and applies the budget.

**Supply chain** (SPEC-v2 0.6), verbatim: "| M0-01 | 12.1; FR-PLAT-53 | The CI workflow MUST run on macOS and Linux with Python 3.12 and 3.13, pin every action by commit SHA, scan for secrets, and run a weekly dependency audit. |" (SPEC-v2 0.6)

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

| Situation | Behavior | Source |
| --- | --- | --- |
| Keychain item not found | Exit 44 maps to `missing` | SPEC-v2 3.1 |
| Keychain locked | Exit 36 or 51, or "User interaction is not allowed", maps to `keychain_locked`; every credential shows `keychain_locked` and only one notification fires | SPEC-v2 3.1, 10.3 |
| Other Keychain failure | `error`; stderr never logged or returned | SPEC-v2 3.1 |
| Google sign-in absent or refused | `DefaultCredentialsError` maps to `missing`; `RefreshError` maps to `invalid`; the exception text is never logged or returned | SPEC-v2 3.1.1 |
| Upstream error | `HttpError(code, status, retry_after_ms, detail)` with generic message text; details go to the log through the redactor | SPEC-v2 3.3 |
| Request to a host outside the policy | `blocked_by_policy` | SPEC-v2 3.3 |
| Unexpected exception in a tool | `@tool_boundary` maps it to `internal` and logs the traceback through the redactor | SPEC-v2 3.7 |
| Missing or wrong bearer token | 401 | SEC-11 |
| Foreign Host or Origin | Refused | SEC-12 |
| Tampered or foreign cursor | Rejected with `invalid_argument` | PLAT-34 |
| Parser crash or kill | Only that task ends, with `extract_failed` | SPEC-v2 3.6 |

Idempotency: Keychain writes use `add-generic-password -U`, which updates an existing item (SPEC-v2 3.1). Retries: webhook posts have a 5 s timeout and at most 2 retries, and failures are logged (SPEC-v2 10.4). No retry is stated for Keychain reads.

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

Security-relevant settings (SPEC-v2 2, verbatim rows):

| Key | Default | Notes |
|---|---|---|
| `server.host` | `127.0.0.1` | Validation rejects any non-loopback value. |
| `server.port` | `7319` | MCP at `/mcp`, UI at `/ui`. |
| `server.token` | `keychain:research-mcp/DAEMON_TOKEN` | Bearer for the shim and API. |
| `limits.download_bytes` | `52428800` | |
| `limits.pdf_pages` | `500` | |
| `notify.webhook_url` | none | OpenClaw inbox (open decision O5); any token goes in Keychain `NOTIFY_WEBHOOK_TOKEN`, never in the URL |
| `credentials.<NAME>.rotate_by` | none | Optional override |

| Flag | Default | Safe to switch off? |
| --- | --- | --- |

No security control is optional in the sources, so none has a feature flag. Switching a control off would breach an invariant.

## 8. Observability

> **Owner:** A · **Persona:** `sre`

- Logs are JSON lines through the redaction filter on every handler; stderr receives warnings and errors only (SPEC-v2 3.2).
- Uvicorn access logging is off, so tokens never reach a log (SPEC-v2 11).
- Every HTTP attempt produces a `CallRecord`, including the Google sign-in refresh with `source="google_signin"` (SPEC-v2 3.3, 3.1.1).
- `doctor` runs `keychain_readable` and one check per credential; `/readyz` returns 503 when the Keychain is not readable (SPEC-v2 10.5).
- A locked Keychain raises one notification, "Keychain locked" (SPEC-v2 10.3).
- `secrets list` prints names, fingerprints and states only (SPEC-v2 12.1).

No numeric security threshold is stated, so no alert traces to an NFR target.

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

Test files named for M0 come from the unit scopes in SPEC-v2 12.3; where a unit names several test files, all are listed because the SPEC does not assign criteria to files. M2 contract criteria have no file named yet.

| Criterion | Planned tests | Level | Status |
| --- | --- | --- | --- |
| SEC-1 | `tests/unit/platform/test_secrets.py`: `test_secret_text_forms_hide_value`, `test_secret_has_no_dict_and_refuses_pickle` | unit | test linked |
| SEC-2 | `tests/unit/platform/test_secrets.py`: `test_keychain_read_argv_and_timeout`, `test_keychain_read_exit_codes`, `test_keychain_read_failures_are_error`, `test_keychain_empty_output_is_error`, `test_env_reference_reads_environment`, `test_keychain_rejects_unsafe_account` | unit | test linked |
| SEC-13 | `tests/unit/platform/test_secrets.py`: `test_keychain_set_writes_through_stdin`, `test_keychain_set_quotes_value`, `test_keychain_set_rejects_unprintable_values`, `test_keychain_set_failure_hides_stderr`, `test_keychain_set_timeout_does_not_chain_stderr`, `test_set_refuses_env_reference`, `test_fake_provider_set_records_argv_without_value` | unit | test linked |
| SEC-3 | `tests/unit/platform/test_secrets.py`: `test_keychain_metadata_never_passes_w`, `test_keychain_metadata_without_mdat_and_failures`, `test_env_reference_has_no_metadata_in_both_providers`, `test_fake_provider_metadata_matches_keychain` | unit | test linked |
| SEC-4 | `tests/unit/platform/test_secrets.py`: `test_secret_cache_reload_returns_changed_names` | unit | test linked |
| SEC-5 | `tests/unit/platform/test_redact.py`, `tests/unit/platform/test_logging.py`, `tests/security/test_no_secret_in_logs.py` (M0-06 scope, SPEC-v2 12.3) | unit | planned |
| SEC-6 | `tests/unit/platform/test_redact.py`, `tests/unit/platform/test_logging.py`, `tests/security/test_no_secret_in_logs.py` (M0-06 scope, SPEC-v2 12.3) | unit | planned |
| SEC-14 | `tests/unit/platform/test_redact.py`, `tests/unit/platform/test_logging.py`, `tests/security/test_no_secret_in_logs.py` (M0-06 scope, SPEC-v2 12.3) | unit | planned |
| SEC-7 | `tests/unit/platform/test_redact.py`, `tests/unit/platform/test_logging.py`, `tests/security/test_no_secret_in_logs.py` (M0-06 scope, SPEC-v2 12.3) | unit | planned |
| SEC-8 | `tests/unit/platform/test_http.py`, `tests/security/test_scoped_credentials.py` (M0-07 scope, SPEC-v2 12.3) | unit | planned |
| SEC-9 | `tests/unit/platform/test_http.py`, `tests/security/test_scoped_credentials.py` (M0-07 scope, SPEC-v2 12.3) | unit | planned |
| SEC-10 | `tests/unit/platform/test_http.py`, `tests/security/test_scoped_credentials.py` (M0-07 scope, SPEC-v2 12.3) | unit | planned |
| SEC-11 | `tests/security/test_loopback_auth.py` (M0-15 scope, SPEC-v2 12.3) | integration | planned |
| SEC-12 | `tests/security/test_loopback_auth.py` (M0-15 scope, SPEC-v2 12.3) | integration | planned |
| SEC-20 | planned (contract test through the in-memory MCP client, TEST-PLAN-v3 2) | contract | planned |
| SEC-21 | planned (contract test through the in-memory MCP client, TEST-PLAN-v3 2) | contract | planned |
| SEC-22 | planned (contract test through the in-memory MCP client, TEST-PLAN-v3 2) | contract | planned |
| SEC-23 | planned (fixture corpus `tests/fixtures/pdf/hostile/`, TEST-PLAN-v3 7) | integration | planned |

Test rules that apply to the whole suite: only `FakeProvider` with generated values; the security suite registers those values with the redactor and scans every output (TEST-PLAN-v3 2). The cross-cutting rows "No secret in any output", "Loopback and auth" and "Untrusted content" stay green in every milestone (TEST-PLAN-v3 3).

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| Secrets live in the macOS Keychain; configuration holds references ([ADR 0003](../adr/0003-secrets-in-keychain.md)) | v1 kept three plaintext copies of every key, readable through the SQL file-read hole, and leaked keys through URLs and exception text | Not recorded in the ADR |
| No free-form SQL; fetched content is labeled untrusted ([ADR 0009](../adr/0009-no-sql-untrusted-content.md)) | v1's SQL tools allowed arbitrary local file reads; fetched documents can carry prompt injection | A narrow, parameterized SQL tool may come later (open decision O4) |
| One daemon; clients use a stdio shim ([ADR 0002](../adr/0002-one-daemon-with-stdio-shims.md)) | Every client goes through the shim, so no client config holds the token | Not recorded in the ADR |
| The UI is server-rendered inside the daemon ([ADR 0010](../adr/0010-localhost-ui-stack.md)) | One process on `127.0.0.1`; sessions start from a one-time token URL; writes need a CSRF token and confirmation; no page shows a secret | Streamlit, Gradio, NiceGUI and a React single-page app (rejected in the ADR) |
| The Google sign-in stays with `gcloud` ([ADR 0012](../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md)) | v2 keeps only a short-lived access token in memory and sends it only to `discoveryengine.googleapis.com` | Not recorded in the ADR |

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

- [ ] Q: HLD-v3 2 shows OpenClaw agents and Codex reaching the daemon over "stdio or loopback HTTP", and PRD-v4 4 lists "loopback streamable HTTP" as an MCP surface, but ADR 0002 and ADR 0003 say every client goes through the stdio shim and no MCP client holds the daemon token (SEC-INV-10). Which is intended?
- [ ] Q: PRD-v4 NFR-07 lists only `/healthz` and `/readyz` as unauthenticated, but `GET /ui/login` is authenticated by a one-time token rather than a bearer token or a session (SPEC-v2 11), and the SPEC does not say whether `/ui/static/*` needs a session. Should NFR-07 name these, and does static content need a session?
- [ ] Q: SPEC-v2 names `platform/auth.py` for the bearer comparison but not where the check is mounted (middleware in `app.py`, or per mount). Where is the enforcement point, and does one check cover `/mcp` and `/api` alike?
- [ ] Q: SEC-12 (foreign Host or Origin refused) verifies PLAT-FR-3 (the MCP endpoint). The `/ui` check is in SPEC-v2 11 and the `/mcp` check in SPEC-v2 7.4, but no Host or Origin check is stated for `/api`. Does SEC-12 cover `/api` and `/ui`, and what check applies to `/api`?
- [ ] Q: `GET /ui/login` redirects to `next` (SPEC-v2 11), and no rule limits `next` to a `/ui` path. Should the control owner require one?
- [ ] Q: SPEC-v2 11 requires `X-CSRF-Token` on every POST but does not say how the token is minted, bound to the session or compared. What is the rule (to be written in LLD-ui-v1)?
- [ ] Q: SPEC-v2 does not state the length or encoding of `DAEMON_TOKEN` when `platform/auth.py` mints it. What should they be?
- [ ] Q: The cursor key is derived from `DAEMON_TOKEN` (SPEC-v2 3.1), so `secrets rotate-token` invalidates every outstanding cursor. Is that intended?
- [ ] Q: The webhook carries `NOTIFY_WEBHOOK_TOKEN` (SPEC-v2 10.4), but only `platform/http.py`, `platform/mcp_client.py` and `platform/auth.py` may reveal a secret (ADR 0003; SPEC-v2 3.1). Does the webhook post go through `HttpClient`, and with which origin policy?
- [ ] Q: PLAT-FR-13 requires redaction of tool results, UI pages and notifications, and HLD-v3 9 names "logs, errors, UI and notifications", but SPEC-v2 3.2 wires `RedactingFilter` only into logging. Which code calls `Redactor.redact` for tool results, UI pages and notifications?
- [ ] Q: PLAT-FR-15 says `SIGHUP` re-reads secrets, but SPEC-v2 names no `SIGHUP` handler. Where is it?
- [ ] Q: SEC-21 and ADR 0009 lock down "any internal DuckDB connection", but SPEC-v2 12.1 lists no DuckDB dependency or extra and ADR 0008 keeps vectors in SQLite. Is any DuckDB use planned, or is that clause of SEC-21 vacuous?
- [ ] Q: PLAT-FR-16 says the daemon token can be rotated from the UI, but the SPEC-v2 11 routes and PLAT-83 name only `secrets rotate-token` in the CLI. Is UI rotation still required?
- [ ] Q: Should SEC-INV-3, SEC-INV-7, SEC-INV-10 and SEC-INV-11 each get a P1 criterion in this component (section 4.4 gaps), for example a scan of config, `state.db` and backups for registered fake secrets, and a scan of successful tool results?
- [ ] Q: The supply chain control (E35) has no acceptance criterion in the generator. Should one be added?

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
