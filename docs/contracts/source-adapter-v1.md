---
title: "Source adapter contract"
type: contract
version: 1
status: draft
owner: "Kenny Hill"
component: sources
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
date: 2026-10-22
---

# Contract: source adapter and registry (v1)

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves at Gate 3 with [LLD-sources v2](../lld/LLD-sources-v2.md). This is a draft for the owner. It changes no behavior of an approved document; it writes down the shapes that [PRD-sources v5](../prd/components/PRD-sources-v5.md) (SRC-FR-1 to SRC-FR-10, SRC-FR-19 to SRC-FR-26) and [SPEC-v5](../spec/SPEC-v5.md) 4 already require. The implementation form is the Python in LLD-sources v2 2.1 and 3.1; if the two disagree, tell the owner.

Every source is one module with a `SourceSpec` and an adapter. A work unit that adds a source, the conformance suite, the live check and the inventory generator all rely on what is written here. The envelope and error codes are in [envelope and error codes v1](envelope-and-errors-v1.md).

## Operations

### Module contract

A source module defines a module-level `SPEC: SourceSpec` and `ADAPTER`, a class constructed as `ADAPTER(spec, ctx)` with the operations below (`search_authors` and `updates` only when the spec declares the capability). Adapters are in-tree only: nothing outside the `research_mcp.sources` package is loaded (owner decision, 2026-10-22). An instance kind (`dspace`, `docs_site`, `vertex_search`) also defines `INSTANCE_MODEL` (a strict Pydantic model of its settings) and `instance_spec(base, instance_id, cfg)`. A module may define `ADAPTER_VERSION` (recorded in provenance), `LIVE_QUERY` and `LIVE_GET_ID` (used only by the live check).

An adapter performs all I/O through `ctx.http` (or `ctx.mcp` for an upstream MCP server). It never sleeps, retries, reads a secret, writes a file, logs a URL that carries a credential, or imports an HTTP library, `socket`, `urllib.request`, `http.client`, `research_mcp.platform.secrets` or an XML parser other than `defusedxml` (SRC-FR-3; SRC-7).

### `SourceSpec` fields (SRC-FR-1)

| Field | Rule |
| --- | --- |
| `id`, `title`, `group` | `id` matches `[a-z][a-z0-9_]{1,39}`; `group` is one of `scholarly`, `preprints`, `biomed`, `repositories`, `standards`, `vendor_docs`, `code`, `integrity`, `education`, `web`, `reference` |
| `capabilities` | Not empty; values from `search`, `get`, `fulltext`, `citations`, `authors`, `updates`, `crawl`. A method for a capability not listed is never called |
| `id_schemes`, `hosts` | `hosts` is every host the adapter may call (lowercase bare host names); a request elsewhere is `blocked_by_policy` |
| `auth` | None, or credential names (`secrets`, Keychain items `research-mcp/<NAME>`), `required`, `placement` (`header`, `query`, `bearer`), `param`, `origins` (not empty, each host in `hosts`), `signup_url` |
| `rate` | `rps` in (0, 50]; `burst` 1 to 50; `concurrency` 1 to 16; `daily_quota` none or at least 1 |
| `timeout_s`, `max_page_size`, `max_bytes` | 0.5 to 60; 1 to 1000; 1024 to 50 000 000 |
| `needs_contact`, `extras` | `needs_contact` sources receive the owner's address; `extras` is a subset of `pdf`, `embeddings`, `macos`, `gcp` |
| `probe` | `cadence_s` 60 to 604 800; `cost` `free` or `metered` (metered at least 3600) |
| `enabled_by_default`, `shutdown_on`, `docs_url`, `instance_of`, `error_classifier` | A `web` source is not enabled by default; `shutdown_on` drives `deprecated(days)` |

Bounds other than those PRD-sources v5 names are design values (LLD-sources v2 2.1).

### Adapter operations (SRC-FR-2, SRC-FR-9)

| Operation | Input | Output | Rule |
| --- | --- | --- | --- |
| `search` | `SearchRequest` (query, filters, limit, cursor, `site_set`, `site_domains`) | `SearchPage` (records, total, next cursor, `truncated`) | No match is an empty page, not an error. A site-set restriction that drops domains sets `truncated` |
| `get` | an `Identifier` | `WorkRecord` or none | Unknown identifier is none, not an error |
| `fulltext_candidates` | a `WorkRecord` | list of candidates with priority | Candidates are locations only; nothing is downloaded |
| `citations` | identifier, direction `citing` or `cited`, cursor, limit | `CitationPage` | Only for sources that declare `citations` |
| `search_authors` | optional query, optional ORCID, limit | list of `AuthorRecord` | Only for sources that declare `authors`; added for the search component (LLD-sources v2 2.1) |
| `updates` | an `Identifier` | list of `UpdateNotice` (retractions, corrections) | Only for sources that declare `updates`; added for the search component (LLD-sources v2 2.1) |
| `probe` | none | `ProbeResult` (`ok`, `latency_ms`, `shape_ok`, `detail_code`, `quota_remaining`, `credential_expires_at`, `api_version`) | `shape_ok` is false when the response is not the expected shape; a probe of a metered source with no free endpoint is one query |

Every record carries `Provenance` (source id, upstream id, adapter version, retrieval time) and normalized identifiers. Web-source records have `work_type="webpage"`, the result URL as identifier and the snippet as an untrusted abstract.

### Registry operations (SRC-FR-4 to SRC-FR-7)

| Operation | Result |
| --- | --- |
| `all()`, `get(id)`, `by_group(group)` | The registered sources (built-ins and configured instances) |
| `select(groups, capability, filters, explicit)` | One `Selected(source, adapter, skip)` per candidate source. Automatic selection uses `federation.default_groups` without `web`. A source with a `skip` is never called |
| `view(id=None)` | One `SourceView` per source: id, title, group, capabilities, state, reason, exact fix hint, enabled, shutdown date, `deprecated_days`, signup and docs URLs, cap, calls today, reset time |
| `web_chain(strategy, order)` | The `web` sources in order, with `vertex_*` expanded to the configured instances |

Skip order (the first match wins): `disabled`; `unconfigured` (missing extra, then missing required credential, then unset contact for a `needs_contact` source, then invalid instance settings); `budget_exhausted` (daily cap reached, resets at local midnight); health `down` as `skipped_unhealthy`; health `rate_limited` or `budget_exhausted`.

### Fixtures (SRC-FR-8)

Each adapter ships seven recorded fixtures in `tests/sources/<id>/fixtures/`: `search_ok`, `search_empty`, `get_ok`, `err_429` (status and headers as JSON, with `Retry-After`), `err_5xx`, `malformed`, `oversize.marker`. Fixtures contain no credential. The conformance suite runs eight checks against every registered adapter (LLD-sources v2 5.3).

## Errors

Adapters raise `HttpError` (defined in `core/errors.py`) or let the shared HTTP client raise it; they use the error codes of [envelope and error codes v1](envelope-and-errors-v1.md) and add none.

| Condition | Adapter or registry behavior | Code or state |
| --- | --- | --- |
| Upstream 429 | Raised by the HTTP client with `retry_after_ms` | `rate_limited` |
| Upstream 5xx after the retry budget | Raised by the HTTP client | `upstream_error` |
| Malformed body, missing field, wrong type | Mapped by the adapter, never `KeyError`, `TypeError` or `ValueError` | `upstream_error` |
| Body past `max_bytes` | Aborted before the whole body is read | `too_large` |
| Request to a host outside `spec.hosts`, or a docs-site URL outside its allowlist or disallowed by `robots.txt` | Refused | `blocked_by_policy` |
| Provider budget message (for example OpenAlex "Insufficient budget") | Mapped by the spec's `error_classifier` | `budget_exhausted` |
| Source switched off | Registry skip, no call | status `disabled` |
| Missing credential, extra, contact address or instance settings | Registry skip, no call, with the exact fix | status `unconfigured` |
| Daily cap reached | Registry skip, no call | status `budget_exhausted` |
| Health `down` | Registry skip, no call | status `skipped_unhealthy` |
| `web` source not needed in a `fallback` chain | Not called | status `not_needed` |
| Unknown source id or unknown or empty site set | Rejected before any call | `invalid_argument` |

A placeholder `contact.email` is a settings error; the daemon does not start (SRC-FR-24).
