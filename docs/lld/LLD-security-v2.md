---
title: "Security low level design"
type: lld
version: 2
status: approved
approved_by: "Kenny Hill (Engineering)"
approved: 2026-10-23
owner: "Kenny Hill"
prefix: SEC
component: security
parent: docs/spec/SPEC-v5.md
supersedes: docs/lld/LLD-security-v1.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# LLD: Security (v2)

This LLD is cross-cutting. The controls it lists are implemented in modules that other LLDs own, chiefly [LLD-platform-v2](LLD-platform-v2.md) (settings, secrets, redaction, logging, HTTP client, `platform/auth.py`, downloader, workers, stores, the MCP app and the daemon), [LLD-ui-v2](LLD-ui-v2.md) (UI routes, `ui/auth.py`, `ui/csrf.py`), [LLD-health-v2](LLD-health-v2.md) (notifications and the webhook) and [LLD-migration-v2](LLD-migration-v2.md) (secrets import, scrub, legacy import). Those LLDs own the names; this one owns the trust boundaries, the enforcement points, the checks and the security test plan. Names below are quoted unchanged from the owning LLDs, which took them from SPEC-v2. Product requirements are in [PRD-security-v3](../prd/components/PRD-security-v3.md); the system design is [SPEC-v5](../spec/SPEC-v5.md) (draft) section 9; the parent product document is PRD-v8 (draft).

**Changes in v2** (Gate 3 draft, 2026-10-22). This version follows the approved PRD-security-v2, PRD-v7, SPEC-v4 and test plan v3 (history note: those were the versions current when this draft began; the citations in the body now point to PRD-security-v3, PRD-v8 and SPEC-v5, all draft). It adds the scrub backup row, the migration-reads exception, the shim sentence and the halt rule; gives SEC-24 to SEC-27 their control, enforcement point and planned test; fixes the cursor and token rotation design; and resolves the version 1 open questions from the approved documents (section 10 records each answer with its source). History note: the version 1 criteria table cited earlier requirement IDs; PLAT-FR-16 is now PLAT-FR-59 (the token rotates from the CLI only), `skipped_budget` is now `budget_exhausted`, and the removed IDs are not used. Authentication and authorization enforcement (section 4) is drafted for the control owner, Kenny Hill (PRD-security-v3 1.7); the control owner answered the five open questions of this draft on 2026-10-22 and each answer is recorded in the text as "owner decision, 2026-10-22" (section 11 holds no open question). SEC-28 is proposed in PRD-security v3, which is drafted separately; until that PRD is approved the ID is a proposal. **Review update (2026-10-23, still draft).** Adds SEC-29, SEC-30 and SEC-32 (PRD-security-v3) with enforcement points E44 (`safe_next`), E45 (token minting) and E46 (`/ui/static/*`), their planned tests and coverage rows; adds E47 (`retire-v1 --confirm`, MIG-35); records the owner decisions of 2026-10-23 (halt marker cleared by hand; client config symlinks refused). Section numbers of SPEC-v5, PRD-v8 and PRD-security-v3 are assumed equal to those of the versions cited before (assumption; checked for PRD-security-v3 and SPEC-v5 headings).

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

Governing section: SPEC-v5 section 9 (security architecture), with sections 2, 10, 12 and 17.

This component defines no functional requirement of its own and no `SEC-FR-n` (PRD-security-v3 2.4; owner decision, 2026-10-22). It satisfies the following requirements of other components and the parent through its criteria. Security owns the shared invariants SEC-INV-1 to SEC-INV-11 (PRD-security-v3 1.6); the platform PRD cites them instead of repeating them.

| Requirement | Criteria | SPEC section |
| --- | --- | --- |
| PLAT-FR-2 | SEC-26 | SPEC 2, 9 |
| PLAT-FR-3 | SEC-11, SEC-12 | SPEC 2, 9 |
| PLAT-FR-10 | SEC-2, SEC-13, SEC-24, SEC-26, SEC-27 | SPEC 9, 10 |
| PLAT-FR-11 | SEC-1 | SPEC 9 |
| PLAT-FR-12 | SEC-8, SEC-9 | SPEC 9 |
| PLAT-FR-13 | SEC-5, SEC-6, SEC-14, SEC-7, SEC-28 (proposed in PRD-security v3) | SPEC 9 |
| PLAT-FR-14 | SEC-9, SEC-10 | SPEC 9 |
| PLAT-FR-15 | SEC-4 | SPEC 7, 9 |
| PLAT-FR-20 | SEC-21 | SPEC 9 |
| PLAT-FR-21 | SEC-25 | SPEC 9 |
| PLAT-FR-22 | SEC-21 | SPEC 9 |
| PLAT-FR-25 | SEC-22 | SPEC 9 |
| PLAT-FR-27 | SEC-20 | SPEC 9 |
| PLAT-FR-59 | SEC-13, SEC-30 (PRD-security-v3) | SPEC 9, 12 |
| UI-FR-2 | SEC-29, SEC-32 (PRD-security-v3) | SPEC 8, 9 |
| CACHE-FR-3 | SEC-8 | SPEC 9 |
| CACHE-FR-10 | SEC-23 | SPEC 6, 9 |
| HLTH-FR-20 | SEC-3, SEC-24 | SPEC 7, 9 |
| HLTH-FR-23 | SEC-4 | SPEC 7, 9 |
| SRC-FR-23 | SEC-27 | SPEC 4, 9 |
| NFR-3 | SEC-2, SEC-24, SEC-27 | SPEC 9, 10 |
| NFR-4 | SEC-1, SEC-5, SEC-7, SEC-10, SEC-28 (proposed in PRD-security v3) | SPEC 9, 17 |
| NFR-6 | SEC-22 | SPEC 9 |
| NFR-7 | SEC-11 | SPEC 2, 9 |

Criteria of this component: SEC-1 to SEC-14, SEC-20 to SEC-27, and SEC-28 to SEC-32 (PRD-security-v3; P1; SEC-28 by owner decision, 2026-10-22) (SEC-15 to SEC-19 were never defined and are unused, PRD-security-v3 2.16). Invariants: SEC-INV-1 to SEC-INV-11. The scrub backup controls are verified by MIG-25 and MIG-26, and the migration read boundary by the migration criteria named in section 4.3 (E36, E37); they belong to the migration component and are mapped here because they are exceptions to SEC-INV-3 and SEC-INV-7.

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

No machine-readable contract exists in `docs/contracts/` yet. The security-relevant wire contracts, from SPEC-v5 sections 2 and 9 and the LLDs that hold them:

**Who connects how** (SPEC-v5 2; owner decision, 2026-10-22). MCP clients connect only through the stdio shim (`research-mcp stdio`, PLAT-FR-2). Loopback streamable HTTP is the transport between the shim and the daemon, and the UI's transport: the owner's browser reaches `/ui` with a UI session, and the CLI reaches `/api` with the bearer token (for example `POST /api/ui-token`). No MCP client is offered direct loopback HTTP, and no client holds the daemon token (SEC-INV-10; SEC-26). This closes the version 1 question about "stdio or loopback HTTP".

**Endpoint authentication** (LLD-platform-v2 4.5, from SPEC-v2 10.5):

| Endpoint | Auth | Returns |
|---|---|---|
| `/healthz` | none | `{"status":"ok","version":"3.x.y"}` |
| `/readyz` | none | Ok when the stores are open, the scheduler is running and the Keychain is readable; 503 otherwise |
| `/api/status` | bearer token or a UI session | JSON of sources, credential metadata, quotas, jobs, cache stats, disk, the archive target and the last 20 notifications |

The complete request-class table, including the routes the SPEC leaves implicit, is in section 4.3 (E3).

- **MCP endpoint** (LLD-platform-v2 2.3): `build_mcp(services)` creates a **new** `FastMCP` for each app, with `streamable_http_path="/"`, `stateless_http=True` and `json_response=True`; the SDK's `TransportSecuritySettings` allow only the loopback hosts and origins. It is mounted at `/mcp` and needs the bearer token (`server.token`, "Bearer for the shim and API").
- **UI login** (LLD-ui-v2 2.2): `research-mcp ui` (with an optional path `P`) creates a one-time token (32 random bytes, valid for 5 minutes) through `POST /api/ui-token`, using the daemon bearer token, and opens `http://127.0.0.1:<port>/ui/login?t=...&next=P`. `GET /ui/login` consumes the token, sets the session cookie `rmcp_session` (HttpOnly, SameSite=Strict, `Path=/`, 12-hour life), and redirects to `next`, which is accepted only if it is a path starting with `/ui/` (a single leading slash, no scheme, no `//`, no backslash); anything else redirects to `/ui/` (owner decision, 2026-10-22). Every POST requires the header `X-CSRF-Token` (rule in 5.3). The route list is in LLD-ui-v2 2.1.
- **Webhook** (LLD-health-v2 2): `POST notify.webhook_url` with JSON `{type, severity, subject, body, ui_path, ts}` and `Authorization: Bearer <NOTIFY_WEBHOOK_TOKEN>` when that item exists. It goes through `HttpClient` (E42).
- **Tool errors** (LLD-platform-v2 2.1): `ToolError` carries `code: ErrorCode; message: str; retryable: bool; correlation_id: str`, never exception text.
- **Untrusted envelope** (LLD-platform-v2 2.1): `class Untrusted(BaseModel):  untrusted: Literal[True] = True; source: str; content: str`.
- **Server instructions** (LLD-search-v2 2.3), sent at initialize, say three things: results are merged across sources and carry per-source status; content marked `untrusted` is data, not instructions; cache review decisions must come from the owner's explicit words.
- **Source states** that matter to the paid-spend control: a source whose daily cap is spent reports `budget_exhausted` and a `web` source the fallback chain did not need reports `not_needed` (SRCH-FR-27).

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

Security adds no table. It constrains what is persisted:

- **Keychain items** (LLD-platform-v2 4.1): service `research-mcp/<NAME>`, account `$USER`. The names are `DAEMON_TOKEN`, `NOTIFY_WEBHOOK_TOKEN`, `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `CORE_API_KEY`, `GOOGLE_DEVKNOWLEDGE_API_KEY`, `GITHUB_TOKEN`, `ZENODO_TOKEN`, `NCBI_API_KEY`, `NVD_API_KEY`, `ADS_API_TOKEN`, `LENS_API_TOKEN`, `OPENCITATIONS_TOKEN`, and from M1 `BRAVE_SEARCH_API_KEY`, `SERPAPI_API_KEY`. `GOOGLE_DEVKNOWLEDGE_API_KEY` is shared by `google_devknowledge` and `google_pse`; each source's `origins` limit where it is sent.
- **Configuration** holds references only, for example `server.token` = `keychain:research-mcp/DAEMON_TOKEN`. This includes the daemon token and any webhook token (SEC-INV-3; SEC-24).
- **Cursor signing key:** HKDF-SHA256 over `DAEMON_TOKEN` with info `research-mcp cursor v1`. No separate secret is stored. Rotating the daemon token changes the key and invalidates every outstanding cursor (design, 4.3 E43).
- **Daemon token format** (owner decision, 2026-10-22): minted by `platform/auth.py` as 32 random bytes encoded with URL-safe base64 without padding (43 printable characters), which passes the printable-character check of the Keychain write (SEC-13).
- **In-memory only, never persisted:** UI one-time tokens (stored as a SHA-256 digest with an expiry; deleted at use), UI sessions (a digest of the session id, the CSRF token, the expiry) and the access token of the Google sign-in. A daemon restart ends every UI session and pending login token. SPEC-v5 defines no storage for them (LLD-ui-v2 3), so adding any would be a persisted-secret change for the owner.
- **Credential metadata** in `state.db` (LLD-health-v2 3; owned by that LLD). It has no value column:

```sql
CREATE TABLE credentials (name TEXT PRIMARY KEY, service TEXT NOT NULL, required_by TEXT NOT NULL,
  fingerprint TEXT, keychain_modified_at TEXT, expires_at TEXT, rotate_by TEXT,
  last_validated_at TEXT, last_result TEXT, state TEXT NOT NULL, last_used_at TEXT, updated_at TEXT NOT NULL);
```

- **Directories** are created at daemon start with mode `0700` (SPEC-v2 2, LLD-platform-v2 7.1).
- **Scrub backups** (approved exception, 4.2 and E37): files with plaintext v1 keys, written by `scrub-client-configs` into a directory with mode `0700`, each file with mode `0600`. The directory is outside the config folder, the Application Support folder and the log folder, and never inside a synced folder (Google Drive, iCloud); [LLD-migration-v2](LLD-migration-v2.md) 5.3 sets the exact path at Gate 3 (SPEC-v5 9). This LLD fixes only the constraints.

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

The SPEC fixes most of these controls; where it left a choice open, the control owner decided it on 2026-10-22 (recorded in place). The control owner is Kenny Hill (PRD-security-v3 1.7; owner decision, 2026-10-22).

### 4.1 Trust boundaries

From SPEC-v5 2, with who is trusted and why.

| Boundary | Who is trusted | Why | Main enforcement points |
| --- | --- | --- | --- |
| 1. Upstream content is untrusted | No one: everything that comes from an API or a downloaded file is data; it is labeled untrusted when returned to a model (SPEC-v5 2) | Fetched documents can carry prompt injection that steers a model toward unsafe tools (ADR 0009 context, OPS-10) | E24, E25, E27, E31, E32, E33 |
| 2. Local callers are authenticated | Only the shim (with the bearer token it reads from the Keychain) and the UI (with a session) can call the daemon; the CLI uses the same bearer token, for example for `POST /api/ui-token` (SPEC-v5 2). Accepted residual risk: any process running as the owner can launch `research-mcp stdio` or read the Keychain item without a prompt, so same-user code sits inside this boundary (owner decision, 2026-10-22; SPEC-v5 9) | Other local processes may call the daemon (SPEC-v5 9) | E1 to E11, E30, E38, E43 |
| 3. Secrets never leave the HTTP layer except to their origin | Only `platform/http.py`, `platform/mcp_client.py` and `platform/auth.py` may reveal a secret (ADR 0003); a secret goes only to an origin in `policy.auth.origins` (LLD-platform-v2 4.4) | v1 sent the CORE key to third-party hosts and echoed keys from URLs into chat (OPS-03, OPS-04) | E12 to E23, E42 |
| Keychain access | `/usr/bin/security`: items written by it trust that binary, so reads by the daemon do not prompt, even after Python upgrades (ADR 0003) | Avoids a prompt per read; the trust is in the system binary, not the interpreter | E13, E14 |
| Google sign-in | `gcloud` owns the sign-in; v2 holds only a short-lived access token in memory (SPEC-v5 9) | The one credential outside the Keychain (ADR 0012) | E20 |
| Owner-run migration commands | The owner, at the command line, reading files outside the v2 data tree (approved exception, see 4.2); a symbolic link as a client config is refused (owner decision, 2026-10-23) | The owner moves v1 credentials and data into v2 (test plan v4 section 4) | E36, E37, E47 |

### 4.2 Threat model

SPEC-v5 9, with the Gate 1 and Gate 2 additions. The rows added or changed since version 1 are marked.

| Threat | Control |
|---|---|
| Prompt-injected model tries to read local files | No SQL tool; no caller-chosen paths; files only under the cache root; DuckDB is not used in v2 (ADR 0008, ADR 0011), and any internal use would be locked down ([ADR 0009](../adr/0009-no-sql-untrusted-content.md); section 10). **Approved exception**, scoped per owner-run migration command: `secrets import` (MIG-FR-1) and `scrub-client-configs` (MIG-FR-5) read only the MCP client configs; only the legacy import (MIG-FR-10) reads the v1 folder (`~/arxiv-papers`, the v1 database), read only (INV-10; MIG-INV-1). MCP tools and anything an agent can trigger stay bound by INV-4 and SEC-INV-7. Recorded in test plan v4 section 4 (owner decision, 2026-10-22). Enforced at E36. (changed) |
| Prompt-injected model tries to delete data | No hard delete in MCP; the only MCP discard is a review decision inside an open batch, recorded as an agent decision, sent to a 7-day trash and announced to the owner at once with an undo link; the owner is notified again 24 hours before any purge; annotations mark state-changing tools. |
| Secret leaks into chat or logs | Keychain (the Google sign-in and the scrub backups excepted); `Secret` type; origin-scoped attachment; header placement; one redaction filter on logs, errors, UI and notifications; errors carry codes, not exception text. |
| Paid web-search spend runs away | Web sources off until configured, never in the default fan-out, fallback order (one paid query per page), daily caps that switch a source to `budget_exhausted`. |
| Google sign-in token misuse | `gcloud` owns the sign-in; v2 holds only a short-lived access token in memory and attaches it only to `discoveryengine.googleapis.com`. |
| Plaintext v1 keys in scrub backups (new) | An approved exception to INV-6, NFR-3 and SEC-INV-3, not SEC-INV-6, until v1 is retired (PRD-v8 1.5; MIG-FR-25, MIG-FR-26). `scrub-client-configs` writes each backup owner-only (mode 0600) in a 0700 directory; the backups serve only to restore the v1 entries on rollback; retiring v1 deletes them (MIG-25, MIG-26). They live outside v2's config, Application Support and log folders, so SEC-24 and the NFR-3 scan apply without exception, and never inside a synced folder, so the keys never leave the Mac (SPEC-v5 9; owner decision, 2026-10-22). Enforced at E37. |
| SSRF and hostile downloads | One downloader: https, per-hop host policy, public IPs only with the connection pinned to the checked IP (no second DNS lookup), byte cap, magic bytes, atomic write. |
| Hostile PDFs | Parsing in a separate subprocess per document with a CPU limit, an RSS watchdog, a wall-clock timeout and a page cap; a crash affects only that document. |
| Other local processes call the daemon (changed) | Loopback only, bearer token, Host and Origin checks; UI session cookie plus CSRF. MCP clients reach the daemon only through the stdio shim, which reads the token from the Keychain; no client holds it (SEC-INV-10; SEC-26). Accepted residual risk as in 4.1 (owner decision, 2026-10-22). |
| Daemon token exposed (new) | The token rotates only from the CLI with `research-mcp secrets rotate-token`, never from the UI; the new value is written through `security -i` on stdin (PLAT-FR-59; SEC-13; PLAT-83). Rotation also invalidates outstanding cursors (E43). |
| Upstream drift returns wrong data | Probes check response shape; fixtures pinned in tests; per-source disable. |
| Supply chain | Lock file, weekly dependency audit, SHA-pinned CI actions, secret scan (PLAT-FR-53; owner check OC-08). |

### 4.3 Enforcement points

Criteria from other components use their IDs (for example `PLAT-10`, `UI-2`). E1 to E35 keep their version 1 numbers; E36 to E47 are new.

| # | Control | Enforcement point | Check | Invariant | Criteria |
| --- | --- | --- | --- | --- | --- |
| E1 | Loopback bind | `settings.Settings`, key `server.host` (default `127.0.0.1`); `daemon.py` runs uvicorn on 127.0.0.1 (access_log off) | Validation rejects any non-loopback value | SEC-INV-1 | PLAT-10, PLAT-71, UI-1 |
| E2 | MCP Host and Origin | `build_mcp(services)` with `TransportSecuritySettings`; and the auth gate (E3) for every path | Allow only the loopback hosts and origins (LLD-platform-v2 2.3) | SEC-INV-1, SEC-INV-2 | SEC-12 |
| E3 | Auth gate: bearer token, UI session, Host and Origin for `/mcp`, `/api` and `/ui` | One ASGI gate in `app.py` (composition root `build_app`) in front of every mount, calling `platform/auth.py` (daemon token mint, `hmac.compare_digest`) and `ui/auth.py` (session lookup). Owner decision, 2026-10-22: one deny-by-default gate for the bearer token and for Host and Origin on all paths; the UI session check and CSRF stay in `ui/`. In LLD-platform the `BearerAuthMiddleware` is renamed to this gate | Deny by default (see the request-class table below). The Host must be `127.0.0.1:<port>` or `localhost:<port>` and a present Origin must match, for every path (SEC-12). A missing or wrong token gets 401. The session cookie is never accepted on `/mcp` or `/api/ui-token` | SEC-INV-2, SEC-INV-1 | SEC-11, SEC-12, SEC-29, SEC-32, UI-20, PLAT-70 |
| E4 | Unauthenticated endpoints | `app.py` mounts `/healthz` and `/readyz` | Only these two answer without a credential (LLD-platform-v2 4.5) | SEC-INV-2 | PLAT-70 |
| E5 | `/api/status` | `app.py` | Bearer token or a UI session | SEC-INV-2 | SEC-11 |
| E6 | UI one-time token | `platform/auth.py` (UI one-time tokens); `ui/auth.py`; `POST /api/ui-token`; `GET /ui/login` | 32 random bytes, valid 5 minutes, minted with the daemon bearer token, consumed once on login, never written to a log (E10) | SEC-INV-2 | UI-2 |
| E7 | UI session | `ui/auth.py`, cookie `rmcp_session` | HttpOnly, SameSite=Strict, `Path=/`, 12-hour life; the server holds a digest of the session id in memory | SEC-INV-2 | UI-2 |
| E8 | CSRF | `ui/csrf.py` | Every POST requires the header `X-CSRF-Token`, compared with the session's token (rule in 5.3) | SEC-INV-2 | UI-3 |
| E9 | UI Host and Origin | The auth gate (E3) for the shared check; `ui/auth.py` [inferred: the SPEC names the check, not the module] for UI specifics | The Host must be `127.0.0.1:<port>` or `localhost:<port>`; if an Origin header is present, it must match | SEC-INV-1, SEC-INV-2 | UI-20, SEC-12 |
| E10 | Tokens kept out of access logs | `daemon.py` (uvicorn access_log off) | Uvicorn access logging is off, so tokens never reach a log | SEC-INV-4 | UI-2 |
| E11 | No token in notifications | `services/notify.py`; `cli.py` `ui` command | The `ui` command mints its one-time login token when the notification is clicked, so no token sits in the notification itself, in a process argument list or in Notification Center | SEC-INV-4, SEC-INV-6 | HLTH-32 |
| E12 | Secret wrapper | `platform/secrets.py` `Secret` | Text form `Secret(name=..., fp=...)`; `reveal()` called only in `platform/http.py`, `platform/mcp_client.py` and `platform/auth.py` | SEC-INV-4 | SEC-1 |
| E13 | Keychain read | `KeychainProvider.get` | `/usr/bin/security find-generic-password -s <service> -a <user> -w`, 5 s timeout; stderr text is never logged or returned | SEC-INV-4 | SEC-2 |
| E14 | Keychain write | `KeychainProvider.set`; `SecretRef` | `/usr/bin/security -i` with the command on stdin; values checked for printable characters first; `SecretRef` validates on construction | SEC-INV-6 | SEC-13 |
| E15 | Metadata without value | `SecretProvider.metadata` | The read command without `-w`; only the `mdat` attribute is parsed | SEC-INV-3 | SEC-3 |
| E16 | Metadata and references only at rest | `state.db` table `credentials`; `config.toml` | No value column; configuration holds references only, including `server.token` and any webhook token | SEC-INV-3 | SEC-24, SEC-3, PLAT-81, HLTH-43 |
| E17 | Rotation without restart | `SecretCache.reload` | Re-reads secrets and returns the names whose fingerprint changed | (supports rotation) | SEC-4 |
| E18 | Origin-scoped attachment | `HttpClient` (`platform/http.py`) with `CredentialResolver` and `AuthSpec.origins` | Attached only when the request origin is in `policy.auth.origins`; placement `header`, `bearer` or `query`; query only where the API offers nothing else, and then the URL is never logged | SEC-INV-5, SEC-INV-4 | SEC-8, SEC-9 |
| E19 | Host policy | `HttpClient` | A request whose host is not in `policy.hosts` fails with `blocked_by_policy` | SEC-INV-5 | PLAT-36 |
| E20 | Google sign-in | `platform/google_adc.py` `GoogleAdcProvider`; `platform/http.py` | Token revealed only by `platform/http.py` for origins in the Vertex spec (`https://discoveryengine.googleapis.com`); v2's own code never opens, copies or writes the credential file, and writes neither the token nor the file's content to any file | SEC-INV-5, SEC-INV-11 | SEC-27, SRC-32 |
| E21 | Webhook token | `services/notify.py`; settings key `notify.webhook_url` | Any token goes in Keychain `NOTIFY_WEBHOOK_TOKEN`, never in the URL (settings validation rejects a URL with embedded credentials); sent as `Authorization: Bearer` through E42 | SEC-INV-3, SEC-INV-4 | HLTH-32, SEC-24 |
| E22 | Redaction of logs | `platform/redact.py` `Redactor`, `RedactingFilter`; `platform/logging.py` `configure_logging` | Filter on every handler; `httpx`, `httpcore`, `uvicorn.access` and `mcp` loggers at `WARNING` | SEC-INV-4 | SEC-5, SEC-6, SEC-7, SEC-14 |
| E23 | Generic errors | `HttpError` (`core/errors.py`); `@tool_boundary` (`mcp_app/server.py`) | Message text is generic, details go to the log through the redactor; any other exception maps to `internal` with the traceback logged through the redactor | SEC-INV-4 | SEC-10, PLAT-62 |
| E24 | Untrusted envelope | `core/envelope.py` `Untrusted`; server instructions in `mcp_app/server.py` | Fetched text in `read`, `search_cache` and `get_work` is inside the envelope; instructions say it is data | (NFR-6) | SEC-22, PLAT-33 |
| E25 | No SQL tool | Tool catalog in `mcp_app/` | None of the registered tools is a SQL tool | SEC-INV-8 | SEC-21 |
| E26 | No DuckDB, or a locked one | `pyproject.toml` (base dependencies exclude duckdb); any future internal DuckDB connection factory | v2 uses no DuckDB (ADR 0008, ADR 0011). If one is ever added, its connection has external access off, allowed directories limited to the cache, extension auto-install and auto-load off, and configuration locked (PLAT-FR-22; ADR 0009) | SEC-INV-7 | SEC-21, PLAT-4 |
| E27 | No caller-chosen path | Tool signatures in `mcp_app/`; cache service | No tool reads local files outside the cache root or accepts a caller-chosen path | SEC-INV-7 | SEC-25, CACHE-11 |
| E28 | No hard delete | `mcp_app/tools_library.py`, `mcp_app/tools_review.py` [inferred: the SPEC names the tools, not their files] | `library` cannot discard; the only MCP discard is `cache_review_decide`, only for items in an open batch, recorded with `decided_by="agent"` and `decided_channel="mcp"`, with an immediate notification and undo link; there is no hard-delete tool | SEC-INV-9 | SEC-20, CACHE-34, CACHE-48 |
| E29 | Tool annotations | `@tool_boundary` and tool registration | Every tool declares MCP annotations (ADR 0009) | SEC-INV-9 | PLAT-60 |
| E30 | Clients never hold the token | `shim.py` (`research-mcp stdio`); `cli.py` `install` | The shim reads the token only from the Keychain; printed client configs launch `research-mcp stdio` and contain no secret (ADR 0002, ADR 0003) | SEC-INV-10 | SEC-26, PLAT-82 |
| E31 | Hostile PDFs | `platform/workers.py` `WorkerRunner` | One subprocess per task; `RLIMIT_CPU` 120 s; 180 s wall clock; RSS sampled every second, SIGKILL past 2 GB; a crash ends that task with `extract_failed`; page cap `limits.pdf_pages` | (threat model) | SEC-23, CACHE-14 |
| E32 | SSRF and hostile downloads | `platform/download.py` `Downloader`, `PinnedTransport` | See [LLD-platform-v2](LLD-platform-v2.md) 5.4; writes only under the data directory | SEC-INV-7 | CACHE-1 |
| E33 | Adapter isolation | `sources/*` | Adapters parse XML with `defusedxml` and may not import `httpx`, `socket` or `research_mcp.platform.secrets`, among others | SEC-INV-5 | SRC-7 |
| E34 | Cursor integrity | `core/budget.py` with the key from `platform/auth.py` | HMAC-SHA256 tag so that agents cannot forge cursors | (none) | PLAT-34 |
| E35 | Supply chain | `.github/workflows/ci.yml`; `pyproject.toml` (ruff rule set `S`) | SHA-pinned actions, `permissions: contents: read`, secret scan, weekly dependency audit, lock file (PLAT-FR-53) | (threat model) | None by design; owner check OC-08 (test plan v4 section 3) and structural checks PLAT-2, PLAT-4 |
| E36 | Migration read boundary (approved exception) | `cli.py` commands `secrets import`, `secrets scrub-client-configs`, `import-legacy`; `services/legacy_import.py` | Per command: `secrets import` and `scrub-client-configs` read only the MCP client configs (Claude desktop, Claude Code, OpenClaw); only `import-legacy` reads the v1 folder, opens the v1 database immutable and never modifies it. All three are owner-run CLI commands: no MCP tool, no `/api` route and no UI route starts them, so MCP tools and agent-triggered actions stay bound by SEC-INV-7. The paths to read are fixed in the migration code or typed by the owner on the command line, never taken from tool arguments (proposal for [LLD-migration-v2](LLD-migration-v2.md) 5.1 to 5.3 to confirm) | SEC-INV-7 (exception, per command), SEC-INV-4 | MIG-1, MIG-5, MIG-10; one P1 migration criterion per command, to be added by the migration PRD at Gate 3 (SPEC-v5 20; ID not yet assigned) |
| E37 | Scrub backup permissions, location and deletion (approved exception) | `scrub-client-configs` in the migration service; v1 retirement step (MIG-FR-24) | Each backup is created with `os.open(..., O_CREAT \| O_EXCL, 0o600)` so it is never readable by others, even briefly; its directory has mode 0700; the location is outside the config, Application Support and log folders and outside any synced folder; retirement deletes every backup. The backups are the only plaintext v1 keys on disk | SEC-INV-3 (time-boxed exception), SEC-INV-6 unchanged | MIG-25, MIG-26, SEC-24 (scan of the v2 folders runs with no exception) |
| E38 | Credential reload paths | `daemon.py` lifespan (a `SIGHUP` handler registered with the event loop) and the UI "Reload credentials" action, both calling `SecretCache.reload` | Both paths do exactly one thing: re-read secrets through the provider (blocking reads off the event loop) and record names whose fingerprint changed, through the redactor; no value is returned or logged. `SIGHUP` takes no argument and no input (PLAT-FR-15; HLTH-FR-23) | SEC-INV-4, SEC-INV-2 | SEC-4 |
| E39 | Redaction of tool results | `@tool_boundary` (`mcp_app/server.py`) | Before the result is returned, every string in it is passed through `Redactor.redact` (registered values and the PLAT-FR-13 patterns); the Untrusted envelope content is covered like any other string (PLAT-FR-13) | SEC-INV-4 | SEC-28 (proposed in PRD-security v3; owner decision, 2026-10-22) |
| E40 | Redaction of UI pages | `ui/routes.py` page rendering; Events page log lines | Rendered HTML and the log lines shown on the Events page pass through `Redactor.redact` before they are sent; pages read only services that return fingerprints and dates (UI-FR-4) | SEC-INV-4 | UI-4 |
| E41 | Redaction of notifications | `services/notify.py` | Subject and body pass through `Redactor.redact` once, before any channel (macOS, webhook, UI banner, digest) sees them | SEC-INV-4 | HLTH-34, HLTH-32 |
| E42 | Webhook through the HTTP layer | `services/notify.py` calling `HttpClient` with a policy built from `notify.webhook_url` | The webhook is a request like any other: `policy.hosts` and `policy.auth.origins` are exactly the origin (scheme, host, port) of the configured URL; the token is `bearer` placement from `NOTIFY_WEBHOOK_TOKEN` and is revealed only inside `platform/http.py`; redirects are not followed to another origin; 5 s timeout, at most 2 retries (assumption: this origin policy follows trust boundary 3). Scheme rule (owner decision, 2026-10-22): `notify.webhook_url` must be `https`, or `http` only when the host is loopback; settings validation rejects any other scheme, so the bearer token never crosses a network in clear text | SEC-INV-5, SEC-INV-4 | HLTH-32, SEC-8, SEC-31 |
| E43 | Daemon token rotation | `cli.py` `secrets rotate-token`; `platform/auth.py`; `shim.py` | Rotation is available only from the CLI; there is no UI or MCP route. The new value is written through `security -i` on stdin (SEC-13). After the daemon reloads (E38), the old token gets 401 (PLAT-83) and the cursor key derived from it changes, so every outstanding cursor is rejected with `invalid_argument` and the client starts that listing again (design; the PRD ties the key to the token and is silent on the effect, PRD-security-v3 2.6; ADR 0003). A running shim that gets 401 re-reads the Keychain once and retries (proposal for LLD-platform-v2 5.7) | SEC-INV-10, SEC-INV-2 | SEC-13, PLAT-83, PLAT-34 |
| E44 | Login `next` accepts `/ui/` paths only | `safe_next` in `ui/auth.py`, called by `GET /ui/login` ([LLD-ui-v2](LLD-ui-v2.md) 2.2) | Returns the value only if it starts with `/ui/` with a single leading slash, no backslash, no control character, no `%2f` or `%5c` after one round of percent-decoding, at most 512 characters; otherwise `/ui/`. No scheme or host can occur (owner decision, 2026-10-22) | SEC-INV-2 | SEC-29, UI-2 |
| E45 | Daemon token format at minting | `platform/auth.py` mint, called by `research-mcp install` and `secrets rotate-token` | 32 bytes from `secrets.token_bytes`, URL-safe base64 without padding, 43 characters; stored only through `SecretProvider.set` (owner decision, 2026-10-22) | SEC-INV-3, SEC-INV-10 | SEC-30, SEC-13, PLAT-83 |
| E46 | `/ui/static/*` needs a UI session | The auth gate (E3), request class `/ui/static/*`; `ui_guard` in `ui/` | A request without a valid UI session gets 401 (`no_session`) and no asset; `/ui/login` serves no asset. The bearer token alone does not open it (owner decision, 2026-10-22) | SEC-INV-2 | SEC-32, UI-2 |
| E47 | `retire-v1 --confirm` deletes only the scrub backups | `cli.py` `retire-v1`; `ClientConfigService.retire_v1()` ([LLD-migration-v2](LLD-migration-v2.md) 5.5; MIG-FR-26; owner decision, 2026-10-23) | Without `--confirm` it refuses and deletes nothing; with it, it deletes only the files of the backup manifest in the fixed backup folder and reports each path; a symbolic link as the folder or any entry is refused; it is an owner-run CLI command with no MCP, `/api` or UI route; it is refused while the halt marker exists (cleared by hand, owner decision, 2026-10-23) | SEC-INV-3 (ends the time-boxed exception), SEC-INV-7 | MIG-35, MIG-26 |

**Request classes handled by the auth gate (E3).** Deny by default: a path not listed gets 401 without a credential and 404 with one. Owner decision, 2026-10-22 (E3), derived from SPEC-v5 2, 9 and 11, PLAT-FR-3 and NFR-7. The unauthenticated surfaces are `/healthz`, `/readyz` and `/ui/login` (the last one is gated by its one-time token, not open).

| Path | Method | Credential required | Notes |
| --- | --- | --- | --- |
| `/healthz`, `/readyz` | GET | none | Unauthenticated, with `/ui/login` below |
| `/mcp` and below | any | bearer token | The session cookie is not accepted |
| `/api/ui-token` | POST | bearer token | Mints one login token; the session cookie is not accepted |
| `/api/status` | GET | bearer token or UI session | |
| `/ui/login` | GET | the one-time token in `t` | Session-establishing request, counted as an unauthenticated surface (no bearer, no session; owner decision, 2026-10-22, see section 10); consumed once; a wrong, expired or reused token gets 401 |
| `/ui/static/*` | GET | UI session | SEC-INV-2 admits no other reading; the login route needs no asset (section 10) |
| `/ui/*` pages | GET | UI session | |
| `/ui/*` actions | POST | UI session and `X-CSRF-Token` | |

For every row the Host and Origin check of E3 runs first. A foreign Host or Origin is refused whatever the credential.

### 4.4 Invariant coverage

Every invariant mapped to its enforcement points and the P1 criteria that check it (PRD-security-v3 1.6). Criteria are those of the PRD; no gap remains.

| Invariant | Enforcement points | Criteria (this component) | Criteria (other components) | Gap |
| --- | --- | --- | --- | --- |
| SEC-INV-1 | E1, E2, E3, E9 | SEC-12 | PLAT-10, PLAT-71, UI-1, UI-20 | None |
| SEC-INV-2 | E2 to E9, E38, E43, E44, E46 | SEC-11, SEC-12, SEC-29, SEC-32 | PLAT-70, UI-2, UI-3 | None |
| SEC-INV-3 | E15, E16, E21, E37, E45, E47 | SEC-24, SEC-2, SEC-3, SEC-30 | PLAT-81, HLTH-32, HLTH-43 | None. Time-boxed exception for the scrub backups (E37), checked by MIG-25 and MIG-26, outside the folders SEC-24 scans |
| SEC-INV-4 | E10 to E13, E18, E22, E23, E38 to E42 | SEC-1, SEC-5, SEC-6, SEC-7, SEC-9, SEC-10, SEC-14, SEC-28 | HLTH-32, HLTH-34, UI-4, PLAT-62, MIG-22 | None. SEC-28 (proposed in PRD-security v3; owner decision, 2026-10-22) scans successful tool results for registered secrets (E39); PLAT-62 covers errors |
| SEC-INV-5 | E18, E19, E20, E33, E42 | SEC-8, SEC-9 | PLAT-36, SRC-32, SRC-7 | None |
| SEC-INV-6 | E11, E14 | SEC-13 | HLTH-32 | None |
| SEC-INV-7 | E26, E27, E32, E36 | SEC-25, SEC-21 | CACHE-11, CACHE-1 | None for MCP tools. The migration commands are excepted (E36); their per-command criterion is not yet defined (SPEC-v5 20) |
| SEC-INV-8 | E25 | SEC-21 | none | None |
| SEC-INV-9 | E28, E29 | SEC-20 | CACHE-34, CACHE-48, PLAT-60 | None |
| SEC-INV-10 | E30, E43 | SEC-26 | PLAT-82 | None |
| SEC-INV-11 | E20 | SEC-27 | SRC-32 | None (M1) |

**Halts.** The rollout halts on a breach of any invariant, SEC-INV-1 to SEC-INV-11 included, as well as the other conditions of PRD-v8 2.6 (owner decision, 2026-10-22; SPEC-v5 12). Detection is by the cross-cutting tests that every milestone keeps green (test plan v4 1.2: no secret in any output, no secret at rest, loopback and auth, untrusted content, no silent deletion) and by the owner checks OC-02, OC-06, OC-08 and OC-14. A red criterion in those rows, or an owner observation of a breach, stops the rollout; the owner is the only responder and no response target exists (PRD-security-v3 2.9). The approved exceptions (scrub backups, migration reads) are not breaches while they stay inside their limits (E36, E37); a backup that is not mode 0600, sits outside the approved location or survives retirement is a breach.

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

The modules belong to other LLDs. This section quotes the parts that carry the security checks, and adds the algorithms of the new enforcement points.

### 5.1 Layout and quoted contracts

**Layout entries** (LLD-platform-v2 5.1):

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

**Secrets** (LLD-platform-v2 4.1, verbatim):

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

class SecretState(StrEnum): OK="ok"; MISSING="missing"; LOCKED="keychain_locked"; ERROR="error"; INVALID="invalid"   # INVALID only from GoogleAdcProvider (HLTH-24)

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

- **Read:** `/usr/bin/security find-generic-password -s <service> -a <user> -w`, run with a 5 s timeout. Exit 44 (not found) maps to `missing`. Exit 36 or 51, or "User interaction is not allowed", maps to `keychain_locked`. Anything else maps to `error`. stderr text is never logged or returned.
- **Metadata:** the same command without `-w`; only the `mdat` attribute is parsed.
- **Write:** `/usr/bin/security -i` with `add-generic-password -U -s <service> -a <user> -w <value>` written to stdin, so the value never appears in a process argument list. Values are checked for printable characters first, so `security -w` never returns a hex dump.
- **Clarification** (SPEC-v2 0.6), verbatim: "| M0-05 | 3.1; AT-PLAT-12, AT-SEC-13 | `SecretRef` MUST validate on construction: the name matches the allowed pattern, and a Keychain reference's service is exactly `research-mcp/<NAME>`. No control character (in particular a newline) may reach the `security -i` script. `FakeProvider.metadata` MUST behave like `KeychainProvider.metadata` (no metadata for `env:` references). |" (SPEC-v2 0.6)

**Google sign-in** (LLD-platform-v2 4.2, M1): `GoogleAdcProvider` implements `SecretProvider` for backend `gcloud_adc` (reference text `gcloud_adc:GOOGLE_SIGNIN`); `set` raises `NotImplementedError` because `gcloud` owns the sign-in. Loading and refreshing run through `anyio.to_thread.run_sync`. The refresh request goes from `google-auth` to `oauth2.googleapis.com` only and is recorded as a `CallRecord` with `source="google_signin"`. The access token is wrapped in `Secret` (name `GOOGLE_SIGNIN`), held in memory, and revealed only by `platform/http.py` for `https://discoveryengine.googleapis.com`, as a bearer token plus `X-Goog-User-Project: <project>`. The refresh must write neither the credential file's content nor the token to any file (SEC-27).

**Redaction and logging** (LLD-platform-v2 4.3, verbatim):

- `Redactor` holds the set of revealed secret values (registered when loaded) and the patterns in PLAT-FR-13.
  - API: `redact(text) -> str`, plus `RedactingFilter(logging.Filter)`, which rewrites `record.msg`, `record.args` and the exception text.
- `configure_logging(settings)` is called only by `daemon.py` and `cli.py`.
  - It attaches `RedactingFilter` to **every handler**, not to a logger, so records propagated from child and third-party loggers are covered.
  - It sets the `httpx`, `httpcore`, `uvicorn.access` and `mcp` loggers to `WARNING`.

The patterns of PLAT-FR-13 are `key=`, `api_key=`, `token=`, `Authorization`, `X-Subscription-Token`, `x-goog-api-key`, `AIza`, `ghp_` and `github_pat_` prefixes.

**Credential attachment** (LLD-platform-v2 4.4 and LLD-sources-v2 2):

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

**Tool boundary** (LLD-platform-v2 5.6): every MCP tool carries `@tool_boundary`, which sets the correlation id, turns `ToolError` and `HttpError` into the error result, maps any other exception to `internal` (logging the traceback through the redactor), and applies the budget.

**Supply chain** (SPEC-v2 0.6), verbatim: "| M0-01 | 12.1; FR-PLAT-53 | The CI workflow MUST run on macOS and Linux with Python 3.12 and 3.13, pin every action by commit SHA, scan for secrets, and run a weekly dependency audit. |" (SPEC-v2 0.6; now PLAT-FR-53)

### 5.2 Daemon token and the auth gate

`platform/auth.py` holds the daemon token: mint (32 bytes from `secrets.token_bytes`, URL-safe base64 without padding, 43 characters; owner decision, 2026-10-22), compare with `hmac.compare_digest` against the token held in `SecretCache`, derive the cursor key with HKDF-SHA256 (info `research-mcp cursor v1`), and issue UI one-time tokens. `research-mcp install` generates `DAEMON_TOKEN` through `SecretProvider.set` if it is absent; `secrets rotate-token` replaces it (PLAT-FR-59, PLAT-83). The gate (E3) runs per request in this order:

1. Check Host (exactly `127.0.0.1:<port>` or `localhost:<port>`) and, if present, Origin (same host and port). Refuse on mismatch.
2. Classify the path with the request-class table. An unlisted path with no credential gets 401.
3. Check the credential the class allows: bearer by `hmac.compare_digest` against the current daemon token; session by a lookup of the SHA-256 digest of the cookie value in the in-memory session table (not expired); login by a lookup of the digest of `t` in the one-time table.
4. For a UI POST, check the CSRF token (5.3).
5. Pass the request to the mount. The bearer token and the cookie are not copied into any log field, and the uvicorn access log is off (E10).

### 5.3 UI login, session and CSRF rule

The UI LLD implements this rule (answer to the version 1 question; PRD-ui-v4 UI-FR-3).

- **One-time token.** `POST /api/ui-token` mints 32 random bytes (URL-safe text) and stores its SHA-256 digest with an expiry of 5 minutes. `GET /ui/login` looks up the digest, deletes the entry whether or not the rest of the request succeeds, and refuses an expired or unknown token. A token is therefore valid once.
- **Session.** On success the server mints a 32-byte session id and a separate 32-byte CSRF token, stores the digest of the id with the CSRF token and a 12-hour expiry, and sets `rmcp_session` (HttpOnly, SameSite=Strict, `Path=/`). The cookie value is the session id only. The sessions are in memory.
- **CSRF token delivery.** Each rendered page carries the session's CSRF token in a meta tag; htmx sends it as `X-CSRF-Token` on every request (`hx-headers`).
- **CSRF check.** A POST needs a valid session and a header that equals the session's CSRF token under `hmac.compare_digest`. A missing header, a mismatch or a missing session gets 403 and no state change (UI-3). The token is per session, not per request, so htmx fragments work; it is bound to the session, so a token from another session fails. GET requests never change state.
- **Layers.** SameSite=Strict, the Host and Origin check and the CSRF token are independent; any one of them refusing is enough.

### 5.4 Redaction call sites

PLAT-FR-13 requires masking in every log record, error message, tool result, UI page and notification, and LLD-platform-v2 4.3 wires the filter only into logging (version 1 question). The call sites are: logs (E22, handler filter); errors and tool results (E23 and E39, in `@tool_boundary`, so every tool is covered once); UI pages and Events log lines (E40); notifications and the webhook payload (E41). `Redactor` registers each secret value when `SecretCache` loads or reloads it (E38), so a rotated value is masked from the first moment it is read. Names of modules are those of the owning LLDs; each of those LLDs must name the call in its next version.

### 5.5 Scrub backups and migration reads

Described in E36 and E37. `scrub-client-configs` asks for explicit confirmation, writes each backup first (mode 0600 at creation, in the 0700 directory), then edits the client config. Rollback after scrubbing restores values from the backup (MIG-FR-25); retirement deletes every backup (MIG-26).

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

| Situation | Behavior | Source |
| --- | --- | --- |
| Keychain item not found | Exit 44 maps to `missing` | LLD-platform-v2 4.1 |
| Keychain locked | Exit 36 or 51, or "User interaction is not allowed", maps to `keychain_locked`; every credential shows `keychain_locked` and only one notification fires | LLD-platform-v2 4.1; HLTH-FR-23 |
| Other Keychain failure | `error`; stderr never logged or returned | LLD-platform-v2 4.1 |
| Google sign-in absent or refused | `DefaultCredentialsError` maps to `missing`; `RefreshError` maps to `invalid`; the exception text is never logged or returned | LLD-platform-v2 4.2 |
| Upstream error | `HttpError(code, status, retry_after_ms, detail)` with generic message text; details go to the log through the redactor | LLD-platform-v2 4.4 |
| Request to a host outside the policy | `blocked_by_policy` | LLD-platform-v2 4.4 |
| Unexpected exception in a tool | `@tool_boundary` maps it to `internal` and logs the traceback through the redactor | LLD-platform-v2 5.6 |
| Missing or wrong bearer token | 401 | SEC-11 |
| Foreign Host or Origin | Refused, on every path | SEC-12, UI-20 |
| Wrong, expired or reused login token | 401; no session set | UI-2 |
| POST without a valid CSRF token | 403; no state change | UI-3 |
| Tampered, foreign or pre-rotation cursor | Rejected with `invalid_argument`; the client restarts the listing | PLAT-34; E43 |
| Old daemon token after rotation | 401 once the daemon has reloaded; a running shim re-reads the Keychain once and retries (proposal) | PLAT-83; E43 |
| Parser crash or kill | Only that task ends, with `extract_failed` | LLD-platform-v2 5.5 |
| `SIGHUP` while the Keychain is locked | Reload reports `keychain_locked`; the secrets already in memory stay in use | E38; HLTH-FR-23 |
| Webhook failure | Logged through the redactor; timeout 5 s, at most 2 retries; the token never appears in the log | LLD-health-v2 |
| Backup cannot be created with mode 0600 | `scrub-client-configs` stops before editing the client config (proposal for LLD-migration-v2) | E37; MIG-25 |

Idempotency: Keychain writes use `add-generic-password -U`, which updates an existing item. A login token and a reload are safe to repeat. No retry is stated for Keychain reads.

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

Security-relevant settings (LLD-platform-v2 7.1, verbatim rows):

| Key | Default | Notes |
|---|---|---|
| `server.host` | `127.0.0.1` | Validation rejects any non-loopback value. |
| `server.port` | `7319` | MCP at `/mcp`, UI at `/ui`. |
| `server.token` | `keychain:research-mcp/DAEMON_TOKEN` | Bearer for the shim and API. |
| `limits.download_bytes` | `52428800` | |
| `limits.pdf_pages` | `500` | |
| `notify.webhook_url` | none | OpenClaw inbox; any token goes in Keychain `NOTIFY_WEBHOOK_TOKEN`, never in the URL |
| `credentials.<NAME>.rotate_by` | none | Optional override |

| Flag | Default | Safe to switch off? |
| --- | --- | --- |

No security control is optional in the sources, so none has a feature flag. Switching a control off would breach an invariant.

## 8. Observability

> **Owner:** A · **Persona:** `sre`

- Logs are JSON lines through the redaction filter on every handler; stderr receives warnings and errors only.
- Uvicorn access logging is off, so tokens never reach a log.
- Every HTTP attempt produces a `CallRecord`, including the Google sign-in refresh with `source="google_signin"` and the webhook post.
- `doctor` runs `keychain_readable` and one check per credential; `/readyz` returns 503 when the Keychain is not readable.
- A locked Keychain raises one notification, "Keychain locked".
- `secrets list` prints names, fingerprints and states only.
- **Breach detection and halt** (added by the `security-reviewer`; confirmed by the `sre` against PRD-v8 2.6 and SPEC-v5 12, which halt on any secret in an output, any invariant breach INV-3 to INV-10 or SEC-INV-1 to SEC-INV-11; the owner is the only responder): the rollout halts on any invariant breach (PRD-v8 2.6). No runtime alert detects a breach by itself. Detection is the cross-cutting tests at each milestone exit and the owner checks listed in 4.4, plus the owner's own observation. No numeric security threshold is stated, so no alert traces to an NFR target.

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

Test files named for M0 come from the unit scopes in the M0 plan and test plan v4 section 2.2; where a unit names several test files, all are listed because the plan does not assign criteria to files. Rows marked "proposed" are the `security-reviewer`'s suggestion; the `test-architect` reviewed them against test plan v4 (draft) and PRD-security v3. SEC-20 to SEC-23 still name no test file (test plan v4 says "planned"), so they stay Gap until the `planner` assigns files. No security criterion touches sync or apply, so no convergence property test is required; SEC-7 keeps its generated-secret property test.

| Criterion | Planned tests | Level | Status |
| --- | --- | --- | --- |
| SEC-1 | `tests/unit/platform/test_secrets.py`: `test_secret_text_forms_hide_value`, `test_secret_has_no_dict_and_refuses_pickle` | unit | test linked |
| SEC-2 | `tests/unit/platform/test_secrets.py`: `test_keychain_read_argv_and_timeout`, `test_keychain_read_exit_codes`, `test_keychain_read_failures_are_error`, `test_keychain_empty_output_is_error`, `test_env_reference_reads_environment`, `test_keychain_rejects_unsafe_account` | unit | test linked |
| SEC-13 | `tests/unit/platform/test_secrets.py`: `test_keychain_set_writes_through_stdin`, `test_keychain_set_quotes_value`, `test_keychain_set_rejects_unprintable_values`, `test_keychain_set_failure_hides_stderr`, `test_keychain_set_timeout_does_not_chain_stderr`, `test_set_refuses_env_reference`, `test_fake_provider_set_records_argv_without_value` | unit | test linked |
| SEC-3 | `tests/unit/platform/test_secrets.py`: `test_keychain_metadata_never_passes_w`, `test_keychain_metadata_without_mdat_and_failures`, `test_env_reference_has_no_metadata_in_both_providers`, `test_fake_provider_metadata_matches_keychain` | unit | test linked |
| SEC-4 | `tests/unit/platform/test_secrets.py`: `test_secret_cache_reload_returns_changed_names` | unit | test linked |
| SEC-5 | `tests/unit/platform/test_redact.py`, `tests/unit/platform/test_logging.py`, `tests/security/test_no_secret_in_logs.py` (M0-06 scope) | unit | planned |
| SEC-6 | same files as SEC-5 | unit | planned |
| SEC-14 | same files as SEC-5 | unit | planned |
| SEC-7 | same files as SEC-5 (property test with generated secrets) | unit | planned |
| SEC-8 | `tests/unit/platform/test_http.py`, `tests/security/test_scoped_credentials.py` (M0-07 scope) | unit | planned |
| SEC-9 | same files as SEC-8 | unit | planned |
| SEC-10 | same files as SEC-8 | unit | planned |
| SEC-11 | `tests/security/test_loopback_auth.py` (M0-15 scope): missing and wrong token get 401 on `/mcp` and `/api`; a session cookie alone is refused on `/mcp` and `/api/ui-token` (proposed, E3) | integration | planned |
| SEC-12 | `tests/security/test_loopback_auth.py` (M0-15 scope): foreign Host and Origin refused on `/mcp`, `/api`, `/ui`, `/healthz` (proposed, E3) | integration | planned |
| SEC-20 | planned (contract test through the in-memory MCP client, test plan v4 2) | contract | planned |
| SEC-21 | planned (contract test through the in-memory MCP client); the DuckDB clause is checked by PLAT-4 (`tests/unit/test_version.py::test_heavy_dependencies_are_extras`) and a check that no module under `src/` imports `duckdb` (proposed) | contract | planned |
| SEC-22 | planned (contract test through the in-memory MCP client, test plan v4 2) | contract | planned |
| SEC-23 | planned (fixture corpus `tests/fixtures/pdf/hostile/`, test plan v4 7) | integration | planned |
| SEC-24 | `tests/security/test_no_secret_at_rest.py::test_config_and_state_db_hold_no_secret`. Control: references only in `config.toml`, metadata only in `state.db`. Enforcement: E16, E21. Runs `install`, a daemon start and a reload with registered fake secrets (including a fake daemon token and webhook token), then scans every file under the configuration and Application Support folders | integration | planned |
| SEC-25 | `tests/security/test_path_arguments.py::test_tools_open_no_file_outside_cache_root`. Control: no caller-chosen path. Enforcement: E27. Calls every tool with absolute paths and `..` segments and records every file open | contract | planned |
| SEC-26 | `tests/unit/test_shim.py::test_shim_reads_daemon_token_only_from_keychain`. Control: the shim obtains the token only from the Keychain provider. Enforcement: E30 | unit | planned |
| SEC-27 | `tests/security/test_no_secret_at_rest.py::test_google_adc_refresh_writes_no_credential`. Control: no copy of the credential file or token. Enforcement: E20. Refreshes from a fake credential file and scans the configuration, Application Support and log folders | integration | planned (M1) |
| SEC-28 (proposed in PRD-security v3) | `tests/security/test_no_secret_in_tool_results.py::test_successful_tool_results_hold_no_registered_secret` (proposed name). Control: every string in a successful tool result is redacted. Enforcement: E39. Calls every MCP tool through the in-memory client with registered fake secrets and scans the results | contract | planned (M2) |
| SEC-29 | `tests/ui/test_login.py::test_next_accepts_only_ui_paths` (the UI LLD's name; file owned by the UI component). Control: `next` follows `/ui/` paths only. Enforcement: E44. Cases `/ui/x`, `//evil`, `/\evil`, `https://evil`, `/ui/../x`, `%2f` | integration | planned (M3) |
| SEC-30 | `tests/unit/test_install.py::test_daemon_token_is_43_char_urlsafe_base64` (proposed name, next to `test_install_generates_token_if_absent`). Control: minted token is 32 random bytes, URL-safe base64, 43 characters, no padding. Enforcement: E45. Mints with a fake `SecretProvider` and checks length, alphabet and decoded length | unit | planned (M0; no owning unit in the M0 plan yet, so it does not gate M0 until the `planner` assigns one) |
| SEC-31 | `tests/unit/test_settings.py::test_webhook_scheme_https_or_loopback_http_only` | unit | planned (M3) |
| SEC-32 | `tests/ui/test_static.py::test_static_needs_a_session` (the UI LLD's name; file owned by the UI component). Control: no asset without a UI session. Enforcement: E46. Also asserts the bearer token alone is refused | integration | planned (M3) |

Test plan v3 section 5, item 4: SEC-24, SEC-26, SRCH-37 and SRCH-38 have no unit in the M0 plan, so they do not gate M0 until the `planner` assigns them. This LLD does not change that.

**Coverage of the enforcement points that no SEC criterion checks** (migration criteria belong to the migration LLD and test plan; listed so the exception stays tested):

| Enforcement point | Criterion | Planned test | Level |
| --- | --- | --- | --- |
| E37 backup mode | MIG-25 | `tests/unit/services/test_legacy_import.py::test_scrub_backup_is_owner_only` (the test plan names this file; the migration LLD should check it is the scrub service's file). Proposed extension: assert directory mode 0700 and the location rule | unit |
| E37 deletion at retirement | MIG-26 | `tests/migration/test_retirement.py::test_retire_deletes_scrub_backups` | integration |
| E36 legacy import never modifies v1 | MIG-10 | planned | integration |
| E36 client-config read boundary per command | the per-command migration criterion (SPEC-v5 20; ID not yet assigned) | proposed: record every file open of `secrets import` and `scrub-client-configs` on fake configs and assert only the fake client config paths; the same for `import-legacy` against a synthetic v1 folder, which is opened read only | integration |
| E47 `retire-v1 --confirm` | MIG-35 | `tests/migration/test_read_boundary.py::test_retire_v1_opens_only_scrub_backups` (also: no `--confirm` deletes nothing; a symbolic link is refused; refused while the halt marker exists) | integration |
| E35 supply chain | none by design | owner check OC-08 once a remote exists; structural PLAT-2, PLAT-4 | owner check |
| E39 tool results | SEC-28 (proposed in PRD-security v3) | the security suite calls every tool with fake secrets registered and scans the results (row above) | contract |

Test rules that apply to the whole suite: only `FakeProvider` with generated values; the security suite registers those values with the redactor and scans every output (test plan v4 1.2). The cross-cutting rows "No secret in any output", "No secret at rest", "Loopback and auth" and "Untrusted content" stay green in every milestone.

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| Secrets live in the macOS Keychain; configuration holds references ([ADR 0003](../adr/0003-secrets-in-keychain.md)) | v1 kept three plaintext copies of every key, readable through the SQL file-read hole, and leaked keys through URLs and exception text | Not recorded in the ADR |
| No free-form SQL; fetched content is labeled untrusted ([ADR 0009](../adr/0009-no-sql-untrusted-content.md)) | v1's SQL tools allowed arbitrary local file reads; fetched documents can carry prompt injection | A narrow, parameterized SQL tool may come later (owner decision O4: none in the first release) |
| One daemon; clients use a stdio shim ([ADR 0002](../adr/0002-one-daemon-with-stdio-shims.md)) | Every client goes through the shim, so no client config holds the token | Not recorded in the ADR |
| The UI is server-rendered inside the daemon ([ADR 0010](../adr/0010-localhost-ui-stack.md)) | One process on `127.0.0.1`; sessions start from a one-time token URL; writes need a CSRF token and confirmation; no page shows a secret | Streamlit, Gradio, NiceGUI and a React single-page app (rejected in the ADR) |
| The Google sign-in stays with `gcloud` ([ADR 0012](../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md)) | v2 keeps only a short-lived access token in memory and sends it only to `discoveryengine.googleapis.com` | Not recorded in the ADR |
| Scrub backups are an approved time-boxed exception, owner-only, outside the v2 folders and synced folders (PRD-v8 1.5; MIG-FR-26; SPEC-v5 9) | Rollback after scrubbing needs the values because v1 does not read the Keychain (MIG-FR-25) | No backup (rollback impossible after scrubbing) or a backup in the Keychain (rejected by the owner's exception choice; not recorded further) |
| Halt marker is cleared by hand (owner decision, 2026-10-23) | After a detected breach only the owner decides the rollout may continue; no command clears it, so no agent can | A `clear-halt` command (not adopted) |
| Client config symlinks are refused (owner decision, 2026-10-23) | A link could redirect a migration read or a backup deletion outside the fixed paths (E36, E47) | Follow links (not adopted) |
| Same-user processes sit inside trust boundary 2 (owner decision, 2026-10-22) | One personal Mac; the token stays out of client configs, not away from the owner's own processes | A per-process Keychain ACL or a separate token per client (not adopted) |

**Version 1 questions resolved in version 2.** Each answer is derived from the approved documents; none is a new product decision.

| Version 1 question | Answer | Source |
| --- | --- | --- |
| HLD "stdio or loopback HTTP" | MCP clients use the stdio shim only; loopback HTTP is the shim's and the UI's transport; no client holds the token | SPEC-v5 2; PRD-v8 1.2, NFR-1; PLAT-FR-2; SEC-INV-10 (owner decision, 2026-10-22) |
| `/ui/login` and `/ui/static/*` versus the "only health checks are unauthenticated" rule | `/ui/login` joins `/healthz` and `/readyz` as an unauthenticated surface (no bearer token, no session); its one-time token still gates it. `/ui/static/*` needs a UI session; the login route needs no asset (owner decision, 2026-10-22). Wording to use in PRD-security v3 (drafted separately): "Only `/healthz`, `/readyz` and `/ui/login` answer without a bearer token or a UI session; `/ui/login` requires a valid one-time login token, and `/ui/static/*` requires a UI session." PRD-v8 NFR-7 may need the same change, which belongs to the next PRD-v8 revision | SEC-INV-2; PRD-security-v3 1.6, 2.5; SPEC-v5 8 |
| Where the bearer check is mounted; Host and Origin for `/api` | One deny-by-default gate in `app.py` in front of all mounts (E3) for the bearer token and for Host and Origin on all paths; the UI session check stays in `ui/` (owner decision, 2026-10-22). SEC-12 states no path limit, so the Host and Origin check covers `/mcp`, `/api` and `/ui` | PLAT-FR-3; SEC-12; UI-20; SPEC-v5 9 |
| `next` redirect | Only a path starting with `/ui/` (single leading slash, no scheme, no `//`, no backslash); anything else redirects to `/ui/` (owner decision, 2026-10-22) | LLD-ui-v2 2.2 |
| CSRF token rule | Per-session random token in a meta tag, compared with `compare_digest` (5.3) for the UI LLD to implement | UI-FR-3; UI-3; SPEC-v5 8 |
| `DAEMON_TOKEN` length and encoding | 32 random bytes as URL-safe base64 without padding, 43 characters (owner decision, 2026-10-22) | SEC-13; PLAT-FR-59 |
| Cursor key after `rotate-token` | Outstanding cursors are invalidated; the client restarts the listing (E43). The PRD ties the key to the token and is silent on the effect, so this is the design | ADR 0003; PLAT-34; PLAT-FR-59 |
| Webhook secret path through `HttpClient` | Yes: the webhook is an `HttpClient` request with a policy limited to the configured URL's origin and bearer placement (E42), which keeps the token reveal inside `platform/http.py` | ADR 0003; SPEC-v5 2 (trust boundary 3); PLAT-FR-12. Scheme rule: `https`, or `http` on a loopback host only (owner decision, 2026-10-22) |
| Redaction call sites for tool results, UI pages and notifications | `@tool_boundary`, UI page rendering and Events lines, `services/notify.py` (E39 to E41, 5.4) | PLAT-FR-13; SPEC-v5 9 |
| `SIGHUP` handler | A signal handler registered in the `daemon.py` lifespan that calls `SecretCache.reload`, the same as the UI "Reload credentials" (E38) | PLAT-FR-15; HLTH-FR-23 |
| UI token rotation | Not offered; CLI only | PLAT-FR-59; SPEC-v5 8, 12 (owner decision, 2026-10-22) |
| DuckDB in SEC-21 and ADR 0009 | v2 uses no DuckDB: it is not a store (ADR 0008, ADR 0011) and the base dependencies exclude it (PLAT-4). The SEC-21 clause is conditional and holds only if a later version adds DuckDB internally (E26) | ADR 0008; ADR 0011; PLAT-FR-22; PLAT-4 |
| P1 coverage gaps for SEC-INV-3, SEC-INV-7, SEC-INV-10, SEC-INV-11 | Closed by SEC-24, SEC-25, SEC-26, SEC-27 (section 4.4) | PRD-security-v3 2.4 (owner decision, 2026-10-22) |
| Supply chain control (E35) has no criterion | None is needed: PLAT-FR-53 is P2 and its check is the owner check OC-08 once a remote exists, with PLAT-2 and PLAT-4 as structural checks. PRD-security-v3 2.11 counts OC-08 | PLAT-FR-53; PRD-security-v3 2.11; test plan v4 section 3 |

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

The control owner (Kenny Hill) answered the five open questions of this draft on 2026-10-22. Each answer is recorded where it applies, as "owner decision, 2026-10-22" (E3, E39, E42, 2, 3, 5.2 and the table in section 10). No question remains open.

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| Kenny Hill (Engineering) | 2026-10-23 | approved (no contract) | approved: none (adds no table) | approved (security-reviewer persona drafted/reviewed; control owner Kenny Hill) | Approved in chat; recorded by Claude in the owner's name at his direction |
