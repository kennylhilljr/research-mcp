---
title: "Security"
type: prd-component
version: 1
status: draft
owner: "Kenny Hill"
decision_makers: "Kenny Hill"
prefix: SEC
component: security
parent: docs/prd/PRD-v5.md
artifact_type: product-specification
scope_level: L3
scope_name: "research-mcp"
date: 2026-10-22
---

# Component PRD: Security (v1)

This component holds the cross-cutting security controls of research-mcp: the invariants, the security acceptance criteria (the former `AT-SEC-*` suite) and their mapping to the requirements of other components. It is new in this version; before it, these tests lived under the Platform and Security PRD (PRD-platform-v2 3). The controls are implemented in other components' modules; the [LLD](../../lld/LLD-security-v1.md) names each enforcement point.

---

## 1.1 Problem and why now

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

The parent PRD states the problem (PRD-v4 2). The security parts, as the sources state them:

- **Credentials are invisible.** Keys sit in plaintext in three MCP client configs, can leak into chat through error messages, and nobody is told when one expires or stops working (PRD-v4 2.3).
- **v1 is unsafe in ways that matter on a personal Mac:** arbitrary local file reads through SQL, keys sent to third-party hosts, downloads that go anywhere (PRD-v4 2.5).
- The review verified these holes: SQL tools can read arbitrary local files, including the MCP client configs that hold every API key in plaintext; the CORE key is sent to third-party PDF hosts; Google and SerpAPI keys travel in URLs and can be echoed into chat (REVIEW-v1 2.4; OPS-01 to OPS-04, ARCH-08).
- Why now: v1 is not a sound base for the next year of use, and v2 is a rebuild in a new repository (REVIEW-v1 2).

## 1.2 Customers and users

> **Owner:** H · **Persona:** none (`analyst` may interview) · **Seed question:** 1

| User or stakeholder | Need | Relative size |
| --- | --- | --- |
| The owner, through an agent (Claude Code, Claude desktop, Codex, OpenClaw agents) over MCP (PRD-v4 4) | Safe by default: no local file read beyond the cache, no credential sent outside its origin, no secret in any output or log (PRD-v4 3.1 G7) | Not stated |
| The owner, directly, through the local web UI (PRD-v4 4) | Only the owner's UI session can call the daemon (HLD-v3 2, trust boundary 2) | Not stated |
| The owner, passively, through notifications (PRD-v4 4) | Notifications never contain a secret value (PRD-v4 NFR-04) | Not stated |

## 1.3 Scope and non-goals

> **Owner:** H · **Persona:** none · **Seed question:** 4

**In scope**

- The threats and controls of the security architecture (HLD-v3 9): prompt-injected file reads and deletions, secret leaks into chat or logs, runaway paid web-search spend, Google sign-in token misuse, SSRF and hostile downloads, hostile PDFs, other local processes calling the daemon, upstream drift, and the supply chain.
- The three trust boundaries: upstream content is untrusted; local callers are authenticated; secrets never leave the HTTP layer except to the origin they belong to (HLD-v3 2).
- The invariants in 1.6 and the security acceptance criteria in 2.4.

| Non-goal | Why it is excluded |
| --- | --- |
| Remote or multi-user access | The server binds to loopback on the owner's Mac (PRD-v4 3.2). |
| Free-form SQL over local files | v1's SQL tools allowed arbitrary local file reads; v2 exposes no SQL tool (PRD-v4 3.2; ADR 0009; owner decision O4). |

## 1.4 Measurable outcomes

> **Owner:** H · **Persona:** none · **Seed question:** 2

This component serves parent outcome OUT-7, "Safe by default", whose measure is: security test suite green; secret-leak tests cover every error path (PRD-v4 3.1 G7). The sources set no component outcome of its own.

| ID | Metric | Baseline | Target | By when |
| --- | --- | --- | --- | --- |

- [ ] Q: Should this component have outcomes of its own beyond OUT-7, and if so, with what baseline, target and date?

## 1.5 Leaps of faith

> **Owner:** H · **Persona:** none

| Leap of faith | How we will validate it | By when |
| --- | --- | --- |

- [ ] Q: What bets must hold for these controls to succeed (for example, that the Keychain ACL never prompts the daemon, or that the redaction patterns cover every credential format in use)?

## 1.6 Invariants: what must never happen

> **Owner:** H · **Persona:** none · **Seed question:** 5

Each row restates a "never" or "no" statement a source already makes. The LLD maps each one to its enforcement points and criteria (LLD-security-v1 4).

| ID | The system must never | Source (regulation, policy, contract) |
| --- | --- | --- |
| SEC-INV-1 | Listen on a non-loopback address. | PRD-v4 NFR-07 ("Nothing listens on a non-loopback address"); PRD-v4 3.2 |
| SEC-INV-2 | Serve an HTTP request, other than the `/healthz` and `/readyz` checks, that has neither a bearer token nor a UI session. | PRD-v4 NFR-07 |
| SEC-INV-3 | Keep a secret at rest outside the Keychain: configuration files hold references only, including for the daemon token and any webhook token, and `state.db` holds credential metadata, never values. The one exception is the owner's Google sign-in, which `gcloud` stores. | PRD-v4 NFR-03; ADR 0003 |
| SEC-INV-4 | Put a secret value in any output: tool results, errors, logs, UI pages, notifications or test snapshots. | PRD-v4 NFR-04; PRD-v4 3.1 G7 |
| SEC-INV-5 | Send a credential outside its origin. | PRD-v4 3.1 G7; HLD-v3 2 (trust boundary 3) |
| SEC-INV-6 | Pass a secret value in a process argument list (Keychain writes pass the value on stdin). | ADR 0003 |
| SEC-INV-7 | Read a local file beyond the cache, or accept a caller-chosen path in any tool. | PRD-v4 3.1 G7; ADR 0009; HLD-v3 9 |
| SEC-INV-8 | Expose a free-form SQL tool. | PRD-v4 3.2; ADR 0009; HLD-v3 9 |
| SEC-INV-9 | Hard-delete through any MCP tool. | ADR 0009 ("no tool hard-deletes"); HLD-v3 9 |
| SEC-INV-10 | Give an MCP client the daemon token: clients launch the stdio shim, which reads it from the Keychain. | ADR 0003 ("MCP clients never hold the daemon token") |
| SEC-INV-11 | Copy the owner's Google sign-in. | PRD-v4 NFR-03 ("v2 never copies"); HLD-v3 9 |

## 1.7 Known constraints and decisions

> **Owner:** H · **Persona:** none · **Seed questions:** 9, 10

| Decision or constraint | Status (made or open) | Rationale or link |
| --- | --- | --- |
| Secrets live in the macOS Keychain; configuration holds references; Keychain access goes through `/usr/bin/security` | Made (ADR status: Proposed, accepted when the owner approves the PRD) | [ADR 0003](../../adr/0003-secrets-in-keychain.md) |
| No free-form SQL; fetched content is labeled untrusted | Made (ADR status: Proposed, accepted when the owner approves the PRD) | [ADR 0009](../../adr/0009-no-sql-untrusted-content.md) |
| No SQL or dataset tool in the first release | Made (owner decision O4) | PRD-v4 11; REVIEW-v1 7 |
| The Google sign-in for Vertex AI Search is the one secret outside the Keychain; `gcloud` stores it | Made | PRD-v4 NFR-03; [ADR 0012](../../adr/0012-domain-neutral-scope-keep-v1-endpoints-web-search-sources.md) |
| Untrusted content is labeled: fetched text is returned inside an envelope marked untrusted | Made | PRD-v4 NFR-06; ADR 0009 |
| Loopback only; every HTTP request except `/healthz` and `/readyz` needs a bearer token or a UI session | Made | PRD-v4 NFR-07 |
| Nothing is deleted without an owner answer (the cache lifecycle owns this rule; this component covers only the MCP hard-delete control) | Made (owner decision D3, retention since changed to 120 days by ADR 0011) | REVIEW-v1 1 D3; PRD-v4 3.1 G6 |
| A locked Keychain is one `keychain_locked` state and one notification, not a notice per key | Made | PRD-v4 12 |
| PyMuPDF parsing runs in a worker process with CPU, memory, page and time limits | Made (owner decision O3) | PRD-v4 11 O3, 12 |

### Intake checkpoint: Problem approved

| Approver | Date | Notes |
| --- | --- | --- |
| | | |

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

| ID | As a... I want... so that... | Priority | Why this priority |
| --- | --- | --- | --- |

No stories exist yet (see 2.13).

## 2.3 User experience

> **Owner:** C · **Persona:** `product-writer` drafts the narrative; designers own the design artifacts · **Seed question:** 3

The security controls are mostly invisible. The owner meets them in three places, as the sources describe:

- **Rotating a credential.** The owner updates the Keychain item and presses "Reload credentials"; no restart is needed (ADR 0003). The Credentials page shows the value-free `security` command (HLD-v3 11.4).
- **Opening the UI.** A session starts from a one-time token URL; all writes need CSRF tokens and confirmation (HLD-v3 8).
- **Reviewing agent discards.** The only MCP discard is a review decision inside an open batch, recorded as an agent decision, sent to a 7-day trash and announced to the owner at once with an undo link (HLD-v3 9).

## 2.4 Functional requirements and acceptance criteria

> **Owner:** C · **Persona:** `product-writer` drafts requirements and criteria as options; the owner selects and approves · **Seed questions:** 3, 12

The sources state no functional requirement for this component. Its criteria verify functional requirements of the platform (`PLAT-FR-*`), cache (`CACHE-FR-*`) and health (`HLTH-FR-*`) components and the parent NFRs.

| ID | Requirement | Story | Parent | Priority |
| --- | --- | --- | --- | --- |

| ID | Criterion | Requirement | Priority | Level | Milestone |
| --- | --- | --- | --- | --- | --- |
| SEC-1 | The `Secret` type shall keep its value out of its repr, str, format and logging output and give a fingerprint of sha256[:8]. | PLAT-FR-11, NFR-4 | P1 | unit | M0 |
| SEC-2 | When `KeychainProvider` runs with an injected runner, the provider shall call `/usr/bin/security` with the expected argv and a 5 s timeout, map exit 44 to missing and a locked keychain to `keychain_locked`, and never echo stderr. | PLAT-FR-10, NFR-3 | P1 | unit | M0 |
| SEC-13 | When `SecretProvider.set` writes a value, the provider shall write it through `security -i` on stdin, so the value never appears in any recorded argv. | PLAT-FR-10, PLAT-FR-16 | P1 | unit | M0 |
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

## 2.5 Non-functional requirements

> **Owner:** H for targets · **Persona:** `product-writer` makes them testable · **Seed question:** 6

The sources set no component NFR. The parent NFRs this component verifies:

| ID | Quality | Target | How it is measured |
| --- | --- | --- | --- |

| Parent NFR | Requirement (PRD-v4 6) | Criteria here |
| --- | --- | --- |
| NFR-3 | No secrets at rest outside the Keychain; config files hold references only, including the daemon token and any webhook token; the one exception is the owner's Google sign-in, which `gcloud` stores and v2 never copies. | SEC-2 |
| NFR-4 | No secret in any output: tool results, errors, logs, UI pages, notifications and test snapshots never contain a secret value. | SEC-1, SEC-5, SEC-7, SEC-10 |
| NFR-6 | Untrusted content is labeled: text fetched from the internet is returned inside an envelope marked untrusted. | SEC-22 |
| NFR-7 | Loopback only: nothing listens on a non-loopback address; every HTTP request except `/healthz` and `/readyz` needs a bearer token or a UI session. | SEC-11 |

## 2.6 Data and classification

> **Owner:** H · **Persona:** none · **Seed question:** 7

| Data | Classification | Source or owner | Retention | Notes |
| --- | --- | --- | --- | --- |
| Credential values (API keys, tokens) | Not stated | macOS login Keychain, `research-mcp/<NAME>` (HLD-v3 10) | Not stated | Read once at daemon start into `Secret` (ADR 0003) |
| Daemon token and webhook token | Not stated | Keychain items (ADR 0003) | Not stated | The cursor signing key is derived from the daemon token (ADR 0003) |
| Credential metadata (fingerprint, modification date, expiry, rotate-by date, validation result) | Not stated | `state.db` (ADR 0003; HLD-v3 10) | Not stated | Never values (ADR 0003) |
| Google sign-in | Not stated | `gcloud` (PRD-v4 NFR-03) | Not stated | v2 holds only a short-lived access token in memory (HLD-v3 9) |
| Fetched upstream content | Not stated | Upstream APIs and downloaded files (HLD-v3 2) | Not stated | Untrusted; labeled when returned to a model (HLD-v3 2) |
| Logs | Not stated | `~/Library/Logs/research-mcp` | Not stated | Pass through one redaction filter (HLD-v3 9) |

- [ ] Q: What is the classification of each data item above, and what retention applies to secrets, metadata and logs from a security point of view?

## 2.7 Integrations and owners

> **Owner:** H confirms owners and SLAs · **Persona:** `architect` may draft · **Seed question:** 8

| System | Owner | Relationship (depends on, feeds, replaces) | SLA |
| --- | --- | --- | --- |
| macOS Keychain through `/usr/bin/security` | Not stated | Depends on: holds every secret (ADR 0003) | Not stated |
| `gcloud` and `google-auth` | Not stated | Depends on: owns the Google sign-in (PRD-v4 NFR-03) | Not stated |
| MCP clients through the stdio shim | Not stated | Feeds: the only MCP callers, authenticated by the shim's bearer token (HLD-v3 2) | Not stated |
| GitHub Actions secret scan and weekly dependency audit | Not stated | Depends on: supply chain control (HLD-v3 9) | Not stated |

- [ ] Q: Who owns each integration above, and what SLA, if any, applies?

## 2.8 Product risks

> **Owner:** H · **Persona:** none

| Risk | Question | Assessment | Mitigation |
| --- | --- | --- | --- |
| Value | Will customers choose to use this? | Not stated | Not stated |
| Usability | Can customers use it, including with accessibility needs? | Not stated | Not stated |
| Viability | Does it work for the business: economics, legal, compliance, operations? | Not stated | Not stated |

- [ ] Q: How does the owner assess value, usability and viability for the security controls?

## 2.9 Rollout risk tolerance and support

> **Owner:** H · **Persona:** none · **Seed question:** 11

| Question | Answer |
| --- | --- |
| Rollout appetite | Not stated |
| Business conditions that must halt the rollout | Not stated |
| Support owner and escalation path | Not stated |
| Response targets by severity (S0 to S4) | Not stated |

- [ ] Q: What rollout appetite, halt conditions, support owner and response targets apply, in particular to a breached invariant (an S0 or S1 incident)?

## 2.10 Measurement and experimentation

> **Owner:** C · **Persona:** `product-writer` drafts; the owner decides

| Outcome | Measured by | Experiment (if any) |
| --- | --- | --- |
| OUT-7 (parent) | Security test suite green; secret-leak tests cover every error path (PRD-v4 3.1 G7) | None stated |

## 2.11 Definition of done

> **Owner:** H · **Persona:** none · **Seed question:** 12

From the sources: the security test suite is green and secret-leak tests cover every error path (PRD-v4 3.1 G7). Every milestone keeps the cross-cutting tests green: no secret in any output, loopback and auth, and untrusted content (TEST-PLAN-v3 3). M0 exits when every M0 test passes; M2 exits when all M2 tests pass, including the hostile PDF corpus (TEST-PLAN-v3 8).

- [ ] Q: Is this the definition of done for the component, or does the owner add a demonstration (for example an on-Mac check) or a review step?

## 2.12 Edge cases and error behavior

> **Owner:** A · **Persona:** `product-writer`

- **Keychain locked** (for example right after login): reads go through `/usr/bin/security` with a timeout; a locked Keychain is one `keychain_locked` state and one notification (PRD-v4 12). Covered by SEC-2.
- **Secret in an exception or URL:** errors carry codes, not exception text (HLD-v3 9). Covered by SEC-9 and SEC-10.
- **Third-party logger emits a record with a key:** the redaction filter sits on handlers, so propagated records are covered. Covered by SEC-5 and SEC-14.
- **Credential would go to a different host** (for example the CORE key to a third-party PDF host): it is not attached. Covered by SEC-8.
- **Hostile PDFs:** parsing runs in a separate subprocess per document; a crash affects only that document (HLD-v3 9). Covered by SEC-23.
- **Prompt-injected model:** it cannot read local files or hard-delete data (HLD-v3 9). Covered by SEC-20 and SEC-21.

## 2.13 Assumptions and open questions

> **Owner:** A · **Persona:** `product-writer` surfaces; the owner resolves before Gate 1

- [ ] Q: Which user stories should this component have? Name them so criteria can cite a story.
- [ ] Q: The sources state no functional requirement for this component. Should the security controls stay as requirements of the platform, cache and health components (as now), or should some move here as `SEC-FR-n`?
- [ ] Q: Several invariants have no SEC criterion of their own and rely on other components' criteria or none (SEC-INV-3, SEC-INV-7, SEC-INV-10, SEC-INV-11; see LLD-security-v1 4). Should each get a P1 criterion here?
- [ ] Q: The former suite numbers jump from `AT-SEC-14` to `AT-SEC-20`. Were `AT-SEC-15` to `AT-SEC-19` ever defined, and if so, were they withdrawn?
- [ ] Q: Who is the control owner who approves the authorization enforcement points at Gate 3?

## 2.14 Glossary

> **Owner:** A · **Persona:** `product-writer`

| Term | Definition |
| --- | --- |
| `Secret` | The type that wraps a secret value; its text form shows only the name and a fingerprint (ADR 0003). |
| Fingerprint | The first 8 hex characters of the SHA-256 of a secret value, used to notice rotation (SPEC-v2 3.1). |
| Secret reference | A configuration value such as `keychain:research-mcp/<NAME>` that points to a Keychain item instead of holding the value (ADR 0003). |
| Daemon token | The bearer token the stdio shim, the CLI and the API use to call the daemon; a Keychain item (ADR 0003). |
| Origin | `scheme://host`; a credential is attached only for the origins its source declares (SPEC-v2 4). |
| Untrusted envelope | The wrapper marked `untrusted` with its source that carries fetched text back to a model (ADR 0009). |
| Redactor | The one redaction filter over logs, errors, UI and notifications (HLD-v3 9). |

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
| FR-PLAT-16 | PLAT-FR-16 |
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
