---
title: "Tool result envelope and error codes"
type: contract
version: 1
status: draft
owner: "Kenny Hill"
component: platform
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
date: 2026-10-22
---

# Contract: tool result envelope and error codes (v1)

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves at Gate 3 with [LLD-platform-v2](../lld/LLD-platform-v2.md). This is a draft for the owner. It changes no behavior of an approved document; it writes down the shapes that [PRD-platform-v4](../prd/components/PRD-platform-v4.md) (PLAT-FR-14, PLAT-FR-25, PLAT-FR-30, PLAT-FR-32) and [SPEC-v5](../spec/SPEC-v5.md) 5 and 11.1 already require.

Every MCP tool returns this envelope or the error result below. Implementations are the Pydantic models in `research_mcp/core/envelope.py` and `research_mcp/core/errors.py`; the MCP SDK emits the JSON Schema from them (PLAT-30), and `ToolResult.model_json_schema()` is the machine-readable form. The tool catalog (which tool returns which `data`) is not part of this contract; it belongs to [LLD-search](../lld/LLD-search-v2.md).

## Operations

### The envelope (PLAT-FR-30)

| Field | Type | Rule |
| --- | --- | --- |
| `data` | the tool's typed payload | Required. Trimmed first when the result exceeds the budget. |
| `source_status` | list of `SourceStatus` | One entry per selected source; never trimmed (PLAT-31). |
| `warnings` | list of text | Never trimmed. Contains no exception text and no secret (PLAT-FR-14). |
| `next_cursor` | text or null | An opaque, HMAC-signed cursor; kept when the result is trimmed (PLAT-31, PLAT-34). |
| `truncated` | boolean | `true` when `data` was trimmed to fit `limits.response_bytes` (default 65536). |

A result larger than `limits.response_bytes` is never returned. If the mandatory fields alone do not fit, the tool returns the error `too_large` (PLAT-63).

### `SourceStatus`

| Field | Type | Rule |
| --- | --- | --- |
| `source` | text | The source id. |
| `state` | one of the values below | Required. |
| `count` | integer | Records returned by this source; default 0. |
| `latency_ms` | integer or null | |
| `retry_after_ms` | integer or null | Set with `rate_limited`. |
| `error_code` | an error code or null | Set when the state is `error`, `timeout` or `rate_limited`. |

`state` values (SRCH-FR-27; HLTH-FR-12): `ok`, `empty`, `timeout`, `rate_limited`, `error`, `unconfigured`, `disabled`, `skipped_unhealthy`, `budget_exhausted`, `not_needed`. `budget_exhausted` replaces the earlier `skipped_budget`. `not_needed` is reported for a `web` source the fallback chain did not have to call.

### `Untrusted` (PLAT-FR-25)

Text fetched from the internet (PDF text, web pages, READMEs, abstracts, snippets) is returned only as `{untrusted: true, source: <text>, content: <text>}`. The `untrusted` field is always `true`.

### Cursors (PLAT-34)

A cursor is base64url JSON with an HMAC-SHA256 tag. The key is derived from the daemon token (LLD-platform-v2 4.5). A cursor with a bad tag, or one made for another tool or key, is rejected with `invalid_argument`. Rotating the daemon token invalidates outstanding cursors, which is the intended effect.

## Errors

The error result, returned as the tool result with the MCP `isError` flag set (assumption: the SDK's error flag is the transport for it), carries exactly these fields and nothing else (PLAT-FR-14):

| Field | Type | Rule |
| --- | --- | --- |
| `code` | an error code | One of the values below. |
| `message` | text | A fixed, generic sentence per code. It never contains exception text, an upstream body, a URL query or a secret (SEC-10, PLAT-62). |
| `retryable` | boolean | The default in the table, unless the raiser sets it. |
| `correlation_id` | text | Also written to the redacted log, where the details are (PLAT-FR-14). |

| Code | Meaning | Raised by | Retryable by default |
| --- | --- | --- | --- |
| `invalid_argument` | An argument is out of bounds, malformed or a tampered cursor (PLAT-FR-31) | Tool validation, cursor check | no |
| `not_found` | The work, document or job does not exist | Services; HTTP 404 | no |
| `unconfigured` | The source or feature needs a setting, credential or extra that is absent | Registry, sources | no |
| `auth_failed` | The upstream refused the credential (HTTP 401 or 403) | HTTP client | no |
| `rate_limited` | The upstream limit applies, or a `Retry-After` over 60 s (PLAT-35) | HTTP client | yes |
| `upstream_error` | The upstream failed (HTTP 5xx after retries, connection errors, other 4xx) | HTTP client | yes |
| `upstream_timeout` | The upstream did not answer in time | HTTP client | yes |
| `budget_exhausted` | A metered source's daily cap or provider budget is spent | HTTP client classifier, budget tracker | no |
| `too_large` | A response or a result exceeds its byte cap (PLAT-38, PLAT-63) | HTTP client, budget | no |
| `blocked_by_policy` | A request names a host outside the source's policy (PLAT-36) | HTTP client, downloader | no |
| `disabled` | The source or feature is switched off | Registry | no |
| `extract_failed` | A worker task crashed, was killed or timed out | Worker runner | no |
| `internal` | Any other failure; the traceback goes to the redacted log (PLAT-62) | `@tool_boundary` | no |

The eleven codes of PLAT-FR-32 are all present; `disabled` and `extract_failed` are additions that the code already has. HTTP status to code mapping is in LLD-platform-v2 6.1.
