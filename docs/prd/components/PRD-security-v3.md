---
title: "Security"
type: prd-component
version: 3
status: approved
approved_by: "Kenny Hill (Product)"
approved: 2026-10-23
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
prefix: SEC
component: security
parent: docs/prd/PRD-v8.md
supersedes: docs/prd/components/PRD-security-v2.md
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
date: 2026-10-22
---

# Component PRD: Security (v3)

This component holds the cross-cutting security controls of research-mcp: the invariants, the security acceptance criteria (the former `AT-SEC-*` suite) and their mapping to the requirements of other components. Before version 1, these tests lived under the Platform and Security PRD (PRD-platform-v2 3). The controls are implemented in other components' modules; the [LLD](../../lld/LLD-security-v2.md) names each enforcement point. Parent: [PRD-v8](../PRD-v8.md). Vision: [vision-v2](../../vision/vision-v2.md). Design: [SPEC-v5](../../spec/SPEC-v5.md). Supersedes [PRD-security-v2](PRD-security-v2.md). Version 3 reopens Gate 1 and records the owner's answers of 2026-10-22 on tool-result redaction (SEC-28), the unauthenticated surfaces, and the authorization point.

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

The parent PRD states the problem (PRD-v6 1.1). The security parts, as the sources state them:

- **Credentials are invisible.** Keys sit in plaintext in three MCP client configs, can leak into chat through error messages, and nobody is told when one expires or stops working (PRD-v4 2.3).
- **v1 is unsafe in ways that matter on a personal Mac:** arbitrary local file reads through SQL, keys sent to third-party hosts, downloads that go anywhere (PRD-v4 2.5).
- The review verified these holes: SQL tools can read arbitrary local files, including the MCP client configs that hold every API key in plaintext; the CORE key is sent to third-party PDF hosts; Google and SerpAPI keys travel in URLs and can be echoed into chat (REVIEW-v1 2.4; OPS-01 to OPS-04, ARCH-08).
- Why now: v2 is a rebuild in a new repository, because v1 is not a sound base for the next year of use, and the upstream breakage is current (PRD-v8 1.1). The rebuild is the moment to design these controls in rather than add them to v1.

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| The owner, through an agent (Claude Code, Claude desktop, Codex, OpenClaw agents) over MCP (PRD-v4 4) | Safe by default: no local file read beyond the cache, no credential sent outside its origin, no secret in any output or log (PRD-v4 3.1 G7) | One person (PRD-v6 1.2) |
| The owner, directly, through the local web UI (PRD-v4 4) | Only the owner's UI session can call the daemon (HLD-v3 2, trust boundary 2) | One person (PRD-v6 1.2) |
| The owner, passively, through notifications (PRD-v4 4) | Notifications never contain a secret value (PRD-v4 NFR-04) | One person (PRD-v6 1.2) |

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- The threats and controls of the security architecture (HLD-v3 9): prompt-injected file reads and deletions, secret leaks into chat or logs, runaway paid web-search spend, Google sign-in token misuse, SSRF and hostile downloads, hostile PDFs, other local processes calling the daemon, upstream drift, and the supply chain.
- The three trust boundaries: upstream content is untrusted; local callers are authenticated; secrets never leave the HTTP layer except to the origin they belong to (HLD-v3 2).
- The invariants in 1.6 and the security acceptance criteria in 2.4.

This component adds no non-goal beyond the parent's: both rows below restate non-goals of PRD-v6 1.3 (owner decision, 2026-10-22).

| Non-goal | Why it is excluded |
| --- | --- |
| Remote or multi-user access | The server binds to loopback on the owner's Mac (PRD-v4 3.2). |
| Free-form SQL over local files | v1's SQL tools allowed arbitrary local file reads; v2 exposes no SQL tool (PRD-v4 3.2; ADR 0009; owner decision O4). |

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

This component serves parent outcome OUT-7, "Safe by default", whose measure is: security test suite green; secret-leak tests cover every error path. It is due at the M2 exit, after fetch and the cache add their paths, and stays green at every milestone exit (PRD-v6 1.4). The parent outcomes OUT-1 to OUT-8 and NFR-1 to NFR-12 suffice, and no component outcome or target is added (owner decision, 2026-10-22).

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |

## 1.5 Leaps of faith

> **Owner:** H · **Persona:** none

Drafted from the sources by the product writer (owner decision, 2026-10-22, to draft them).

| Leap of faith | How we will validate it | By when |
| --- | --- | --- |
| Keychain items written by `/usr/bin/security` trust that binary, so the daemon reads every item without a prompt, even after Python upgrades (SPEC-v2 3.1; LLD-security-v2 4.1). | Owner check OC-02 (the daemon reads every Keychain item with no prompt) and SEC-2 | M0 exit |
| The masking of registered secret values plus the credential patterns of PLAT-FR-13 cover every credential format in use, closing the v1 leaks through URLs and exception text (PLAT-FR-13; REVIEW-v1 2.4, finding 7). | SEC-6 and the SEC-7 property test at M0; the OUT-7 measure (secret-leak tests cover every error path) | M0 exit for SEC-6 and SEC-7; M2 exit for OUT-7 |
| Taking SQL, hard delete and caller-chosen paths off the tool surface, and labeling fetched text untrusted, is enough to stop a prompt-injected model from reading local files or deleting data (HLD-v3 9 threat model; ADR 0009). | SEC-20, SEC-21, SEC-22, SEC-25 and CACHE-11 | M2 exit |

## 1.6 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

Each row restates a "never" or "no" statement a source already makes. The owner confirmed them as component invariants (owner decision, 2026-10-22). Each one has at least one P1 criterion, here or in another component. The LLD maps each one to its enforcement points (LLD-security-v2 4).

| ID | The system must never | Source (regulation, policy, contract) | P1 criteria |
| --- | --- | --- | --- |
| SEC-INV-1 | Listen on a non-loopback address. | PRD-v4 NFR-07 ("Nothing listens on a non-loopback address"); PRD-v4 3.2 | SEC-12; PLAT-10, PLAT-71, UI-1 |
| SEC-INV-2 | Serve an HTTP request, other than the `/healthz`, `/readyz` and `/ui/login` requests, that has neither a bearer token nor a UI session. `/ui/login` takes a one-time token and sets a UI session; `/ui/static/*` needs a UI session (owner decision, 2026-10-22). | PRD-v4 NFR-07, which names only `/healthz` and `/readyz`; the owner's answer of 2026-10-22 adds `/ui/login` | SEC-11, SEC-12, SEC-29, SEC-32; PLAT-70, UI-2, UI-3 |
| SEC-INV-3 | Keep a secret at rest outside the Keychain: configuration files hold references only, including for the daemon token and any webhook token, and `state.db` holds credential metadata, never values. The one exception is the owner's Google sign-in, which `gcloud` stores. | PRD-v4 NFR-03; ADR 0003 | SEC-24, SEC-2, SEC-3, SEC-30; PLAT-81, HLTH-32 |
| SEC-INV-4 | Put a secret value in any output: tool results, errors, logs, UI pages, notifications or test snapshots. | PRD-v4 NFR-04; PRD-v4 3.1 G7 | SEC-1, SEC-5, SEC-6, SEC-7, SEC-9, SEC-10, SEC-14, SEC-28; PLAT-62 |
| SEC-INV-5 | Send a credential outside its origin. | PRD-v4 3.1 G7; HLD-v3 2 (trust boundary 3) | SEC-8, SEC-9, SEC-31; PLAT-36, SRC-32 |
| SEC-INV-6 | Pass a secret value in a process argument list (Keychain writes pass the value on stdin). | ADR 0003 | SEC-13; HLTH-32 |
| SEC-INV-7 | Read a local file beyond the cache, or accept a caller-chosen path in any tool. | PRD-v4 3.1 G7; ADR 0009; HLD-v3 9 | SEC-25, SEC-21; CACHE-11, CACHE-1 |
| SEC-INV-8 | Expose a free-form SQL tool. | PRD-v4 3.2; ADR 0009; HLD-v3 9 | SEC-21 |
| SEC-INV-9 | Hard-delete through any MCP tool. | ADR 0009 ("no tool hard-deletes"); HLD-v3 9 | SEC-20 |
| SEC-INV-10 | Give an MCP client the daemon token: clients launch the stdio shim, which reads it from the Keychain. | ADR 0003 ("MCP clients never hold the daemon token") | SEC-26; PLAT-82 |
| SEC-INV-11 | Copy the owner's Google sign-in. | PRD-v4 NFR-03 ("v2 never copies"); HLD-v3 9 | SEC-27; SRC-32 |

**Approved exception.** The scrub backups of the v1 client configs hold plaintext v1 keys outside the Keychain. The owner approved them as an exception that lasts until v1 is retired; they are written owner-only and deleted at retirement (PRD-v8 1.5; MIG-FR-26; MIG-25, MIG-26; owner decision, 2026-10-22). The invariant itself is unchanged.

**Approved exception for owner-run migration commands.** SEC-INV-7 is excepted per command, until v1 retirement, for the owner-run migration commands only; MCP tools and agent-triggered actions stay bound by it, so SEC-25 and CACHE-11 are unchanged. The read set of each command is in PRD-migration-v6 2.4 (SPEC-v5 9; owner decision, 2026-10-22).

## 1.7 Known constraints and decisions

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

| Decision or constraint | Status (made or open) | Rationale or link |
| --- | --- | --- |
| Secrets live in the macOS Keychain; configuration holds references; Keychain access goes through `/usr/bin/security` | Made (ADR status: Accepted, 2026-10-22, with Gate 1 approval of the parent PRD) | [ADR 0003](../../adr/0003-secrets-in-keychain.md) |
| No free-form SQL; fetched content is labeled untrusted | Made (ADR status: Accepted, 2026-10-22, with Gate 1 approval of the parent PRD) | [ADR 0009](../../adr/0009-no-sql-untrusted-content.md) |
| No SQL or dataset tool in the first release | Made (owner decision O4) | PRD-v4 11; REVIEW-v1 7 |
| The Google sign-in for Vertex AI Search is the one secret outside the Keychain; `gcloud` stores it | Made | PRD-v4 NFR-03; [ADR 0012](../../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md) |
| Untrusted content is labeled: fetched text is returned inside an envelope marked untrusted | Made | PRD-v4 NFR-06; ADR 0009 |
| Loopback only; every HTTP request except `/healthz`, `/readyz` and `/ui/login` needs a bearer token or a UI session; `/ui/login` takes a one-time token and sets a UI session; `/ui/static/*` needs a UI session | Made (owner decision, 2026-10-22) | PRD-v4 NFR-07, extended by the owner's answer of 2026-10-22 |
| Nothing is deleted without an owner answer (the cache lifecycle owns this rule; this component covers only the MCP hard-delete control) | Made (owner decision D3, amended by ADR 0011: retention is 120 days) | REVIEW-v1 1 D3; PRD-v4 3.1 G6 |
| A locked Keychain is one `keychain_locked` state and one notification, not a notice per key | Made | PRD-v4 12 |
| PyMuPDF parsing runs in a worker process with CPU, memory, page and time limits | Made (owner decision O3) | PRD-v4 11 O3, 12 |
| The security controls stay requirements of the platform, cache and health components; this component defines no `SEC-FR-n`, and its criteria cite those requirements | Made (owner decision, 2026-10-22) | 2.4 |
| Kenny Hill is the control owner who approves the authorization enforcement points at Gate 3 | Made (owner decision, 2026-10-22) | [LLD-security-v2](../../lld/LLD-security-v2.md) 4 |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| Kenny Hill (Product) | 2026-10-22 | Approved in chat; recorded by Claude in the owner's name at his direction |

---

## 2.1 Customer discovery

> **Owner:** A · **Persona:** `analyst`

The [deep review of v1](../../../docs-archive/review/REVIEW-v1.md) is the evidence. Its findings that drive this component:

- Finding 1 (Critical): arbitrary local file read through `analytics_sql` and a bypassable `dataset_query` sandbox, verified on DuckDB 1.5 (OPS-01, OPS-02).
- Finding 7 (High): credential leaks; the CORE bearer goes to third-party hosts, and keys in URL query strings are echoed through `str(e)` (OPS-03, OPS-04, ARCH-08, FUNC-14).
- Finding 8 (High): downloads follow redirects anywhere, accept http and private IPs, have no size or PDF check, and the model can choose any path (OPS-05, OPS-08, FUNC-15, FUNC-33).
- v1's unwired foundation means every safety flag (`RESEARCH_MCP_AUTH_TOKEN`, expert SQL, crawler, custom paths) does nothing (ARCH-02, OPS-06, FUNC-36).

## 2.2 User stories and priority

> **Owner:** C for stories (`product-writer`), H for priority · **Seed question:** 3

This component has no requirements of its own (2.4), so it has no user stories: its criteria trace to the requirements of other components, whose stories they serve (owner decision, 2026-10-22).

| ID | As a... I want... so that... | Priority | Why this priority |
| --- | --- | --- | --- |

## 2.3 User experience

> **Owner:** C · **Persona:** `product-writer` drafts the narrative; designers own the design artifacts · **Seed question:** 3

The security controls are mostly invisible. The owner meets them in three places, as the sources describe:

- **Rotating a credential** (PLAT-FR-15). The owner updates the Keychain item and presses "Reload credentials"; no restart is needed (ADR 0003). The Credentials page shows the value-free `security` command (HLD-v3 11.4).
- **Opening the UI** (UI-FR-2, UI-FR-3). A session starts from a one-time token URL at `/ui/login`; all writes need CSRF tokens and confirmation (HLD-v3 8).
- **Reviewing agent discards** (CACHE-FR-35). The only MCP discard is a review decision inside an open batch, recorded as an agent decision, sent to a 7-day trash and announced to the owner at once with an undo link (HLD-v3 9).

## 2.4 Functional requirements and acceptance criteria

> **Owner:** C · **Persona:** `product-writer` drafts requirements and criteria as options; the owner selects and approves · **Seed questions:** 3, 12

This component defines no `SEC-FR-n`: the security controls stay requirements of the platform, cache and health components (owner decision, 2026-10-22). The criteria below verify those requirements (`PLAT-FR-*`, `CACHE-FR-*`, `HLTH-FR-*`, and `SRC-FR-23` for the Google sign-in) and the parent NFRs. The requirement table is therefore empty, and each criterion names the requirements it verifies.

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |

| ID | Criterion | Requirement | Priority | Level | Milestone |
| --- | --- | --- | --- | --- | --- |
| SEC-1 | The `Secret` type shall keep its value out of its repr, str, format and logging output and give a fingerprint of sha256[:8]. | PLAT-FR-11, NFR-4 | P1 | unit | M0 |
| SEC-2 | When `KeychainProvider` runs with an injected runner, the provider shall call `/usr/bin/security` with the expected argv and a 5 s timeout, map exit 44 to missing and a locked keychain to `keychain_locked`, and never echo stderr. | PLAT-FR-10, NFR-3 | P1 | unit | M0 |
| SEC-13 | When `SecretProvider.set` writes a value, the provider shall write it through `security -i` on stdin, so the value never appears in any recorded argv. | PLAT-FR-10, PLAT-FR-59 | P1 | unit | M0 |
| SEC-3 | When the Keychain metadata lookup runs, the provider shall never pass `-w` and return the modification date only. | HLTH-FR-20 | P1 | unit | M0 |
| SEC-4 | When `SecretCache.reload` runs, the cache shall re-read the secrets and return the names whose fingerprints changed. | PLAT-FR-15, HLTH-FR-23 | P1 | unit | M0 |
| SEC-5 | The redactor shall mask known secret values in log messages, args and exception text, including records from child and third-party loggers, through its filter on handlers. | PLAT-FR-13, NFR-4 | P1 | unit | M0 |
| SEC-6 | The redactor shall mask the credential patterns `key=`, `api_key=`, `token=`, `Authorization`, `X-Subscription-Token`, `x-goog-api-key`, `AIza`, `ghp_` and `github_pat_`. | PLAT-FR-13 | P1 | unit | M0 |
| SEC-14 | `configure_logging` shall set the `httpx`, `httpcore`, `uvicorn.access` and `mcp` loggers to WARNING, so an INFO httpx record with `api_key` in the URL never reaches a handler unmasked. | PLAT-FR-13 | P1 | unit | M0 |
| SEC-7 | The redactor shall keep every random secret registered with it out of every formatted log record, as checked by a property test. | PLAT-FR-13, NFR-4 | P1 | unit | M0 |
| SEC-8 | The HTTP client shall attach a credential only when the request origin is in its spec origins, so the CORE key is not sent to a third-party PDF host. | PLAT-FR-12, CACHE-FR-3 | P1 | unit | M0 |
| SEC-9 | The HTTP client shall use header placement when the spec allows it (`x-goog-api-key`) and, with query placement, keep the URL out of logs and errors. | PLAT-FR-12, PLAT-FR-14 | P1 | unit | M0 |
| SEC-10 | The HTTP client shall raise `HttpError` messages that contain no exception text, URL query or upstream body. | PLAT-FR-14, NFR-4 | P1 | unit | M0 |
| SEC-11 | If an MCP or `/api` request arrives without the bearer token, then the daemon shall answer 401, comparing the token with `hmac.compare_digest`. | PLAT-FR-3, NFR-7 | P1 | integration | M0 |
| SEC-12 | If a request carries a foreign Host or Origin, then the daemon shall refuse it. | PLAT-FR-3 | P1 | integration | M0 |
| SEC-20 | The MCP server shall offer no tool that performs a hard delete. | PLAT-FR-27 | P1 | contract | M2 |
| SEC-21 | The MCP server shall register no SQL tool and run any internal DuckDB connection with external access off and configuration locked. | PLAT-FR-20, PLAT-FR-22 | P1 | contract | M2 |
| SEC-22 | The `read`, `search_cache` and `get_work` tools shall always return fetched text inside the untrusted envelope. | PLAT-FR-25, NFR-6 | P1 | contract | M2 |
| SEC-23 | If the daemon parses the hostile PDF corpus (malformed files, huge page counts, decompression bombs), then the daemon shall never crash. | CACHE-FR-10 | P1 | integration | M2 |
| SEC-24 | When `install`, a daemon start and a credential reload run with registered fake secrets, the system shall leave no registered secret value in any file of the configuration folder or the Application Support folder, including `config.toml` and `state.db`. | PLAT-FR-10, HLTH-FR-20, NFR-3 | P1 | integration | M0 |
| SEC-25 | When the security suite calls every MCP tool with path-like arguments (absolute paths and `..` segments), the MCP server shall open no file outside the cache root. | PLAT-FR-21 | P1 | contract | M2 |
| SEC-26 | When `research-mcp stdio` starts, the shim shall read the daemon token only from the Keychain. | PLAT-FR-2, PLAT-FR-10 | P1 | unit | M0 |
| SEC-27 | When `GoogleAdcProvider` refreshes an access token from a fake credential file, the system shall write neither the file's content nor the token to any file in the configuration, Application Support or log folders. | PLAT-FR-10, SRC-FR-23, NFR-3 | P1 | integration | M1 |
| SEC-28 | When a tool call returns a successful result, the MCP server shall redact every string in that result for registered secrets at the tool boundary. | PLAT-FR-13, NFR-4, SEC-INV-4 | P1 | contract | M2 |
| SEC-29 | When `/ui/login` is given a `next` value, the UI shall follow it only if it is a path under `/ui/`. | UI-FR-2, SEC-INV-2 | P1 | integration | M3 |
| SEC-30 | When the CLI generates `DAEMON_TOKEN`, the CLI shall produce 32 random bytes encoded as URL-safe base64, 43 characters long. | PLAT-FR-59, SEC-INV-3 | P1 | unit | M0 |
| SEC-31 | When the OpenClaw webhook URL is configured, the daemon shall accept it only if its scheme is https, or http on a loopback host. | HLTH-FR-32, SEC-INV-5 | P1 | unit | M3 |
| SEC-32 | If a request for `/ui/static/*` carries no UI session, then the daemon shall refuse it. | UI-FR-2, SEC-INV-2 | P1 | integration | M3 |

SEC-24 to SEC-27 give SEC-INV-3, SEC-INV-7, SEC-INV-10 and SEC-INV-11 a P1 criterion in this component (owner decision, 2026-10-22). SEC-28 is new in version 3: it closes the tool-result path of SEC-INV-4, because SEC-5 covers logs and SEC-10 covers errors only (owner decision, 2026-10-22). SEC-29 to SEC-32 are new in version 3: they give the `/ui/login` `next` rule, the `DAEMON_TOKEN` format, the webhook scheme rule and the `/ui/static/*` session rule a P1 contract criterion here, traced to the requirement or invariant that covers each, because this component has no `SEC-FR-n` (owner decision, 2026-10-22). The test plan maps SEC-28 to SEC-32 to their tests as it does every other criterion; their rows are added to the test plan as Gap until a test exists.

Verified elsewhere (owner decision, 2026-10-22): this component has no requirement of its own, so no requirement here relies only on another component's criterion or an owner check. Other components' criteria that also check an invariant are named in the last column of 1.6, and they stay with their components.

## 2.5 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

The parent outcomes OUT-1 to OUT-8 and NFR-1 to NFR-12 suffice, and no component NFR or target is added (owner decision, 2026-10-22). Design defaults such as timeouts stay in the LLD. The parent NFRs this component verifies:

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |

| Parent NFR | Requirement (PRD-v6 2.3) | Criteria here |
| --- | --- | --- |
| NFR-3 | No secrets at rest outside the Keychain; config files hold references only, including the daemon token and any webhook token; the one exception is the owner's Google sign-in, which `gcloud` stores and v2 never copies. The scrub backups of the v1 client configs are an approved exception until v1 is retired (PRD-v8 1.5; MIG-FR-26). | SEC-2, SEC-24, SEC-27 |
| NFR-4 | No secret in any output: tool results, errors, logs, UI pages, notifications and test snapshots never contain a secret value. | SEC-1, SEC-5, SEC-7, SEC-10, SEC-28 |
| NFR-6 | Untrusted content is labeled: text fetched from the internet is returned inside an envelope marked untrusted. | SEC-22 |
| NFR-7 | Loopback only: nothing listens on a non-loopback address; every HTTP request except `/healthz`, `/readyz` and `/ui/login` needs a bearer token or a UI session. `/ui/login` takes a one-time token and sets a UI session; `/ui/static/*` needs a UI session (owner decision, 2026-10-22). PRD-v7 NFR-7 names only `/healthz` and `/readyz` (see 2.13). | SEC-11 |

## 2.6 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

Every item is personal and confidential (PRD-v6 2.4). Retention follows the parent rule for the same kind of data; credential metadata follows the nearest parent rule (owner decision, 2026-10-22).

| Data | Classification | Source or owner | Retention | Notes |
| --- | --- | --- | --- | --- |
| Credential values (API keys, tokens) | Personal, confidential; secret (PRD-v6 2.4) | macOS login Keychain, `research-mcp/<NAME>` (HLD-v3 10) | Until revoked or replaced (PRD-v6 2.4) | Read once at daemon start into `Secret` (ADR 0003) |
| Daemon token and webhook token | Personal, confidential; secret (PRD-v6 2.4) | Keychain items (ADR 0003) | Until revoked or replaced (PRD-v6 2.4) | The cursor signing key is derived from the daemon token (ADR 0003) |
| Credential metadata (fingerprint, modification date, expiry, rotate-by date, validation result) | Personal, confidential (PRD-v6 2.4) | `state.db` (ADR 0003; HLD-v3 10) | Until the credential is revoked or replaced (owner decision, 2026-10-22) | Never values (ADR 0003) |
| Google sign-in | Personal, confidential; secret (PRD-v6 2.4) | `gcloud` (PRD-v4 NFR-03) | Not stored by v2 (PRD-v6 2.4) | v2 holds only a short-lived access token in memory (HLD-v3 9) |
| Fetched upstream content | Personal, confidential; untrusted content (PRD-v6 2.4) | Upstream APIs and downloaded files (HLD-v3 2) | 120 days from fetch; keep, unpin, undo and collection changes grant a fresh 120 days; pinned and archived items never expire (PRD-v6 2.4; ADR 0011) | Untrusted; labeled when returned to a model (HLD-v3 2) |
| Logs | Personal, confidential; must contain no secret (PRD-v6 2.4) | `~/Library/Logs/research-mcp` | Rotated by size: 5 files of 10 MB (PLAT-FR-40; owner decision, 2026-10-22) | Pass through one redaction filter (HLD-v3 9) |

## 2.7 Integrations and owners

> **Owner:** H confirms owners and SLAs · **Persona:** `architect` may draft · **Seed question:** 8

Kenny Hill owns every integration. None has an SLA; upstream services are best effort and tracked by probes (PRD-v6 2.5; owner decision, 2026-10-22).

| System | Owner | Relationship (depends on, feeds, replaces) | SLA |
| --- | --- | --- | --- |
| macOS Keychain through `/usr/bin/security` | Kenny Hill | Depends on: holds every secret (ADR 0003) | None |
| `gcloud` and `google-auth` | Kenny Hill | Depends on: owns the Google sign-in (PRD-v4 NFR-03) | None |
| MCP clients through the stdio shim | Kenny Hill | Feeds: the only MCP callers, authenticated by the shim's bearer token (HLD-v3 2) | None |
| GitHub Actions secret scan and weekly dependency audit | Kenny Hill | Depends on: supply chain control (HLD-v3 9) | None |

## 2.8 Product risks

> **Owner:** H · **Persona:** none

| Risk | Question | Assessment | Mitigation |
| --- | --- | --- | --- |
| Value | Will customers choose to use this? | The owner asked for these controls: they answer problem 5 of PRD-v6 1.1 and findings 1, 7 and 8 of REVIEW-v1. The value risk is a breach that leaves v2 no safer than v1; any secret in an output halts the rollout (PRD-v6 2.6). | The OUT-7 suite stays green at every milestone exit (PRD-v6 1.4), and every invariant in 1.6 has a P1 criterion. |
| Usability | Can customers use it, including with accessibility needs? | A locked or unreadable Keychain, for example right after login, could stop the sources that need a key (PRD-v6 2.10). | Reads go through `/usr/bin/security` with a timeout; a locked Keychain is one `keychain_locked` state and one notification, not a notice per key; `doctor` gives the fix (PRD-v6 2.10). SEC-2 and owner check OC-02 check it. |
| Viability | Does it work for the business: economics, legal, compliance, operations? | Not stated | Not stated |

## 2.9 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | As in PRD-v6 2.6: v1 stays read-only and running until cutover; cutover (M4) switches client configs; v1 is archived after 14 days of daily use on v2 with no fallback to v1 (owner decision, 2026-10-22). |
| Business conditions that must halt the rollout | The PRD-v8 2.6 conditions: any deletion without a recorded owner decision, any secret in an output, a fallback to v1 during the 14-day window, or a breach of any invariant, which includes SEC-INV-1 to SEC-INV-11 (PRD-v8 2.6; owner decision, 2026-10-22). |
| Support owner and escalation path | The owner is the only support; there is no escalation path (PRD-v6 2.6; owner decision, 2026-10-22). |
| Response targets by severity (S0 to S4) | None (PRD-v6 2.6; owner decision, 2026-10-22). |

## 2.10 Measurement and experimentation

> **Owner:** C · **Persona:** `product-writer` drafts; the owner decides

| Outcome | Measured by | Experiment (if any) |
| --- | --- | --- |
| OUT-7 (parent) | Security test suite green; secret-leak tests cover every error path; due at the M2 exit and green at every milestone exit (PRD-v6 1.4) | None stated |

## 2.11 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

The component is done when every P1 criterion in 2.4 passes and the exit of the milestone that delivers it is met (PRD-v6 2.9): M0 for SEC-1 to SEC-14, SEC-24, SEC-26 and SEC-30; M1 for SEC-27; M2 for SEC-20 to SEC-23, SEC-25 and SEC-28; M3 for SEC-29, SEC-31 and SEC-32. Every milestone keeps the cross-cutting tests green: no secret in any output, loopback and auth, and untrusted content (TEST-PLAN-v3 3). The owner checks in [test-plan-v2](../../test/test-plan-v2.md) section 3 that cover this component's controls count: OC-02 (Keychain reads with no prompt, PLAT-FR-10), OC-08 (CI secret scan and weekly audit) and OC-14 (the Google sign-in, SRC-FR-23). No extra demonstration or review step is added (owner decision, 2026-10-22).

## 2.12 Edge cases and error behavior

> **Owner:** A · **Persona:** `product-writer`

- **Keychain locked** (for example right after login): reads go through `/usr/bin/security` with a timeout; a locked Keychain is one `keychain_locked` state and one notification (PRD-v4 12). Covered by SEC-2.
- **Secret in an exception or URL:** errors carry codes, not exception text (HLD-v3 9). Covered by SEC-9 and SEC-10.
- **Secret in a successful tool result** (for example a fetched page or an upstream body that echoes a key): every string in the result is redacted at the tool boundary. Covered by SEC-28.
- **Third-party logger emits a record with a key:** the redaction filter sits on handlers, so propagated records are covered. Covered by SEC-5 and SEC-14.
- **Credential would go to a different host** (for example the CORE key to a third-party PDF host): it is not attached. Covered by SEC-8.
- **Hostile PDFs:** parsing runs in a separate subprocess per document; a crash affects only that document (HLD-v3 9). Covered by SEC-23.
- **Prompt-injected model:** it cannot read local files or hard-delete data (HLD-v3 9). Covered by SEC-20 and SEC-21.
- **Prompt-injected model passes a path to a tool:** no tool accepts a caller-chosen path, and no file outside the cache root is opened (ADR 0009). Covered by SEC-25 and CACHE-11.
- **A secret lands in a file at rest** (configuration, `state.db`, or a file written after a Google token refresh): none may hold a value (NFR-3). Covered by SEC-24 and SEC-27.
- **A request reaches an unauthenticated surface:** only `/healthz`, `/readyz` and `/ui/login` answer without a bearer token or a UI session; `/ui/login` accepts a one-time token and sets a UI session, and `/ui/static/*` needs a UI session (SEC-INV-2; owner decision, 2026-10-22). Covered by SEC-11 and PLAT-70; the `/ui/static/*` session rule is covered by SEC-32, and the `/ui/login` behavior by UI-2 and UI-3.
- **A request reaches any mount without a credential:** one deny-by-default gate in `app.py` stands in front of every mount, so a route with no explicit rule is refused (owner decision, 2026-10-22). Covered by SEC-11 and SEC-12.
- **`/ui/login` is given a `next` value:** it accepts `/ui/` paths only; any other value is not followed (owner decision, 2026-10-22). Covered by SEC-29.
- **The daemon token is minted:** `DAEMON_TOKEN` is 32 random bytes in URL-safe base64, 43 characters (owner decision, 2026-10-22). It is stored only in the Keychain (SEC-INV-3). Covered by SEC-30 and, for generation, PLAT-83.
- **The OpenClaw webhook URL is configured:** the webhook accepts https, or http on loopback only (owner decision, 2026-10-22). Covered by SEC-31.

## 2.13 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves before Gate 1

**Resolved on 2026-10-22 (version 2).** The owner answered every open question of version 1: component outcomes (none beyond OUT-7; 1.4); leaps of faith (drafted for approval; 1.5); user stories (none, since the component has no requirements of its own; 2.2); no `SEC-FR-n`, with the controls staying in the platform, cache and health components (1.7, 2.4); a P1 criterion here for SEC-INV-3, SEC-INV-7, SEC-INV-10 and SEC-INV-11 (SEC-24 to SEC-27; 1.6, 2.4); `AT-SEC-15` to `AT-SEC-19` were never defined (2.16); Kenny Hill is the control owner at Gate 3 (1.7); data classification and retention (2.6); integration owners and SLAs (2.7); product risks (drafted for approval; 2.8); rollout and support (2.9); and the definition of done (2.11).

**Gate 1 follow-up (owner decision, 2026-10-22).** MCP clients connect only through the stdio shim; loopback streamable HTTP is the shim's and the UI's transport, so no client holds the daemon token (PRD-v8 1.2 and NFR-1, corrected; SEC-INV-10). Security owns the shared invariants: Platform 1.6 cites SEC-INV-1, SEC-INV-3, SEC-INV-4, SEC-INV-5, SEC-INV-7 and SEC-INV-9 instead of repeating them, and SEC-24 is the one criterion for no secret at rest after install, start and reload. The scrub backups are an approved exception to SEC-INV-3 until v1 is retired (PRD-v8 1.5; MIG-FR-26). A breach of any SEC-INV halts the rollout (PRD-v8 2.6) (owner decision, 2026-10-22).

**Reopened Gate 1 answers (version 3, owner decision, 2026-10-22).**

- Every string in a successful tool result is redacted for registered secrets at the tool boundary: SEC-28 (P1).
- The unauthenticated surfaces are `/healthz`, `/readyz` and `/ui/login`. `/ui/login` takes a one-time token and sets a UI session; `/ui/static/*` needs a UI session. SEC-INV-2, NFR-7 here and the 1.7 row now say so.
- The authorization point is one deny-by-default gate in `app.py`; `DAEMON_TOKEN` is 32 bytes in URL-safe base64; the `/ui/login` `next` value accepts `/ui/` paths only; the webhook allows https, or http on loopback. The last four each got a P1 criterion in this component: SEC-29 (`next`), SEC-30 (token format), SEC-31 (webhook) and SEC-32 (`/ui/static/*`), with the 43-character length and URL-safe base64 encoding of the token (owner decision, 2026-10-22).

**Assumptions**

- Assumption: SEC-28 is delivered at M2, because the MCP tools that return fetched text arrive at M2 (SEC-22 is also M2). The owner gave no milestone.
- Assumption: SEC-28 traces to PLAT-FR-13, NFR-4 and SEC-INV-4. The reopening note named SEC-INV-2, but SEC-INV-2 covers authentication; the invariant that SEC-28 serves is SEC-INV-4, and 1.6 lists it there.
- Assumption: SEC-29 and SEC-32 trace to UI-FR-2 and SEC-INV-2, SEC-30 to PLAT-FR-59 (the requirement behind PLAT-83) and SEC-INV-3, and SEC-31 to HLTH-FR-32 and SEC-INV-5 (the webhook sends a token). The owner named no requirement.
- Assumption: SEC-29, SEC-31 and SEC-32 are delivered at M3 with the UI and notification channels, and SEC-30 at M0 with SEC-26. The owner gave no milestone. The level of SEC-29 to SEC-32 is the writer's choice; the owner asked for a contract criterion, but unit or integration fits the behavior, so confirm it.
- Assumption: PRD-v7 NFR-7 needs the same wording change. PRD-v7 NFR-7 names only `/healthz` and `/readyz`, so it needs a new version to match 2.5.

**Open questions**

None. The owner chose to add one P1 criterion each in this component: SEC-29 to SEC-32 (owner decision, 2026-10-22).

## 2.14 Glossary

> **Owner:** A · **Persona:** `product-writer`

| Term | Definition |
| --- | --- |
| `Secret` | The type that wraps a secret value; its text form shows only the name and a fingerprint (ADR 0003). |
| Fingerprint | The first 8 hex characters of the SHA-256 of a secret value, used to notice rotation (SPEC-v2 3.1). |
| Secret reference | A configuration value such as `keychain:research-mcp/<NAME>` that points to a Keychain item instead of holding the value (ADR 0003). |
| Daemon token | The bearer token the stdio shim, the CLI and the API use to call the daemon; a Keychain item of 32 random bytes in URL-safe base64 (ADR 0003; owner decision, 2026-10-22). |
| Origin | `scheme://host`; a credential is attached only for the origins its source declares (SPEC-v2 4). |
| Untrusted envelope | The wrapper marked `untrusted` with its source that carries fetched text back to a model (ADR 0009). |
| Redactor | The one redaction filter over logs, errors, UI and notifications (HLD-v3 9). |
| Registered secret | A generated fake secret value that the security suite registers with the redactor so that every output and file can be scanned for it (TEST-PLAN-v3 2). |
| Tool boundary | The point where a tool's result leaves the MCP server for the caller; SEC-28 redacts every string there. |
| One-time login token | The 32-byte token that `/ui/login` accepts once to set a UI session; it is the credential of that route (LLD-security-v2 10). |

## 2.15 ID history

> **Owner:** C · **Persona:** `product-writer` records; the owner confirms

No ID left this PRD in version 3.

| ID | Status | Replaced by | Reason |
| --- | --- | --- | --- |

The IDs added in version 3, and editorial changes that keep their ID; these rows are not definitions. Earlier additions (SEC-24 to SEC-27, version 2) keep their rows in PRD-security-v2.

| Changed or new ID | Change | Date | Reason |
| --- | --- | --- | --- |
| SEC-28 | Added: every string in a successful tool result is redacted for registered secrets at the tool boundary (SEC-INV-4) | 2026-10-22 | owner decision, 2026-10-22 |
| SEC-29 | Added: `/ui/login` follows a `next` value only under `/ui/` | 2026-10-22 | owner decision, 2026-10-22 |
| SEC-30 | Added: `DAEMON_TOKEN` is 32 bytes in URL-safe base64, 43 characters | 2026-10-22 | owner decision, 2026-10-22 |
| SEC-31 | Added: the webhook scheme is https, or http on loopback only | 2026-10-22 | owner decision, 2026-10-22 |
| SEC-32 | Added: `/ui/static/*` needs a UI session | 2026-10-22 | owner decision, 2026-10-22 |
| SEC-28 | Editorial: traced also to SEC-INV-4; the ID is kept | 2026-10-22 | owner decision, 2026-10-22 |
| SEC-INV-2 | Editorial: the invariant names `/ui/login` beside `/healthz` and `/readyz`, and `/ui/static/*` needs a UI session; the ID is kept | 2026-10-22 | owner decision, 2026-10-22 |

### Gate 1: Requirements approved

| Approver | Date | Notes |
| --- | --- | --- |
| Kenny Hill (Product) | 2026-10-23 | Approved in chat; recorded by Claude in the owner's name at his direction |

## 2.16 Earlier IDs

> **Owner:** A · **Persona:** `product-writer`

| Earlier ID | New ID |
| --- | --- |
| AT-SEC-01 | SEC-1 |
| AT-SEC-02 | SEC-2 |
| AT-SEC-13 | SEC-13 |
| AT-SEC-03 | SEC-3 |
| AT-SEC-04 | SEC-4 |
| AT-SEC-05 | SEC-5 |
| AT-SEC-06 | SEC-6 |
| AT-SEC-14 | SEC-14 |
| AT-SEC-07 | SEC-7 |
| AT-SEC-08 | SEC-8 |
| AT-SEC-09 | SEC-9 |
| AT-SEC-10 | SEC-10 |
| AT-SEC-11 | SEC-11 |
| AT-SEC-12 | SEC-12 |
| AT-SEC-15 to AT-SEC-19 | None: never defined in any surviving document, so `SEC-15` to `SEC-19` are unused (owner decision, 2026-10-22) |
| AT-SEC-20 | SEC-20 |
| AT-SEC-21 | SEC-21 |
| AT-SEC-22 | SEC-22 |
| AT-SEC-23 | SEC-23 |
| FR-PLAT-03 | PLAT-FR-3 |
| FR-PLAT-10 | PLAT-FR-10 |
| FR-PLAT-11 | PLAT-FR-11 |
| FR-PLAT-12 | PLAT-FR-12 |
| FR-PLAT-13 | PLAT-FR-13 |
| FR-PLAT-14 | PLAT-FR-14 |
| FR-PLAT-15 | PLAT-FR-15 |
| FR-PLAT-16 | PLAT-FR-16 (superseded by PLAT-FR-59) |
| FR-PLAT-20 | PLAT-FR-20 |
| FR-PLAT-22 | PLAT-FR-22 |
| FR-PLAT-25 | PLAT-FR-25 |
| FR-PLAT-27 | PLAT-FR-27 |
| FR-CACHE-03 | CACHE-FR-3 |
| FR-CACHE-10 | CACHE-FR-10 |
| FR-HLTH-20 | HLTH-FR-20 |
| FR-HLTH-23 | HLTH-FR-23 |
| NFR-03 | NFR-3 |
| NFR-04 | NFR-4 |
| NFR-06 | NFR-6 |
| NFR-07 | NFR-7 |
| G7 | OUT-7 |

The FR, NFR and goal rows are references to IDs owned by other PRDs; their own PRDs record those renames.
