---
title: "Sources low level design"
type: lld
version: 2
status: draft
owner: "Kenny Hill"
prefix: SRC
component: sources
parent: docs/spec/SPEC-v5.md
supersedes: docs/lld/LLD-sources-v1.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# LLD: Sources (v2)

This LLD carries the sources design out of [SPEC v5](../spec/SPEC-v5.md) section 4 (sources), with sections 5, 9 and 13 where they touch the `web` group and the inventory. Detail that SPEC-v2 held in its sections 4 (specs, models and the source contract) and 5.1 to 5.5 (registry, fixtures and conformance, live check, new-source checklist, site sets, docs sites and web search) is kept here under the same subsection numbers that SPEC-v5 section 4 cites. Requirements and criteria are in [PRD-sources v5](../prd/components/PRD-sources-v5.md); the cross-cutting security rules are in [PRD-security v3](../prd/components/PRD-security-v3.md) and [LLD-security v2](LLD-security-v2.md); platform types, the HTTP client and the flag table are in [LLD-platform v2](LLD-platform-v2.md); the test plan is [test plan v4](../test/test-plan-v4.md) (draft). Code paths: `src/research_mcp/sources` and `tests/sources` (`sdd.config.json`). The machine-readable contract is [source adapter v1](../contracts/source-adapter-v1.md) (draft, new).

**Changes in v2.** This version follows the approved PRD-sources v5 and SPEC-v4, which win wherever v1 disagreed. History note: SRC-FR-11 is replaced by SRC-FR-24 (a placeholder contact address stops the daemon starting), SRC-FR-13 by SRC-FR-25 (the inventory comes only from `tools/gen_inventory.py`) and SRC-FR-16 by SRC-FR-26 (the new-source checklist without its old step 5); the source state `skipped_budget` is now `budget_exhausted`, and the `web` fallback adds `not_needed`. Added: `SourceSpec` validation and its bounds (2.1, SRC-1); the registry's selection order, fix hints and `SourceView` (5.2); the instance and discovery rules (2.3, 3.2); site-set merging (3.2, 3.3); the docs-site allowlist and `robots.txt` design (5.11); the DSpace and upstream MCP details (5.6, 5.12); the web-source cap check (5.9); the live check design (5.4); the catalog to module map (5.1); a feature flag table that answers the v1 question about flags (7); a planned test for every criterion (9). The fourteen open questions of v1 are settled from the approved documents and the owner decisions of 2026-10-22 (section 10 records each answer with its source); the four questions that section 11 kept were answered by the owner on 2026-10-22 and are recorded in section 10.

**Reviewer note.** Sections 4, 8 and 9 belong to other personas (`security-reviewer`, `sre`, `test-architect`). What is written there was drafted by the `component-designer` and has been reviewed in Gate 3 on 2026-10-23: section 4 by `security-reviewer`, section 8 by `sre` and section 9 by `test-architect`; nothing in it has been verified by the owner. Rationale inferred from existing code is tagged `[inferred]`; a design value with no source is tagged `[assumption]`.

Section numbers inside text copied from SPEC-v2 (for example "(SPEC-v2 5.5)") refer to the archived SPEC-v2; in tables, "SPEC n" means section n of SPEC-v5; bare numbers in this LLD's own prose (for example "(5.9)") refer to this LLD.

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

Governing section: SPEC 4 (sources). SPEC 5 and 9 govern the `web` group; SPEC 13 governs the inventory and maintainability.

| Requirement | Criteria | SPEC section | Detailed in |
| --- | --- | --- | --- |
| SRC-FR-1 | SRC-1 (also PLAT-6) | SPEC 4 | 2.1, 2.2 |
| SRC-FR-2 | SRC-6 | SPEC 4 | 2.1, 5.3 |
| SRC-FR-3 | SRC-7 (also SRC-6) | SPEC 4, 15 | 2.1, 4, 5.3 |
| SRC-FR-4 | SRC-2, SRC-21 | SPEC 4 | 2.3, 3.2, 5.2, 5.12 |
| SRC-FR-5 | SRC-3, SRC-8 (also UI-10) | SPEC 4 | 5.2, 6 |
| SRC-FR-6 | SRC-4, SRC-8 | SPEC 4 | 5.2, 6 |
| SRC-FR-7 | SRC-5 (also PLAT-13) | SPEC 4 | 5.2 |
| SRC-FR-8 | SRC-6, SRC-10, SRC-11, SRC-12, SRC-20 | SPEC 4, 17 | 3.4, 5.3 |
| SRC-FR-9 | SRC-6, SRC-10, SRC-11, SRC-12, SRC-20 | SPEC 4 | 3.1, 5.3 |
| SRC-FR-10 | SRC-22 | SPEC 4 | 5.6 |
| SRC-FR-12 | SRC-25 | SPEC 4 | 5.4 |
| SRC-FR-14 | SRC-24 | SPEC 4 | 2.1, 5.2 |
| SRC-FR-15 | SRC-23 | SPEC 4 | 4, 5.11 |
| SRC-FR-17 | SRC-26 | SPEC 4 | 3.3 |
| SRC-FR-18 | SRC-26, SRC-27 | SPEC 4 | 3.2, 3.3, 5.8 |
| SRC-FR-19 | SRC-28, SRC-33 | SPEC 4, 5, 9 | 5.7, 5.9 |
| SRC-FR-20 | SRC-29 | SPEC 4, 5, 9 | 5.9 |
| SRC-FR-21 | SRC-30 | SPEC 4, 5, 9 | 5.9 |
| SRC-FR-22 | SRC-31 | SPEC 4, 5 | 5.8 |
| SRC-FR-23 | SRC-32 | SPEC 4, 9 | 4, 5.7 |
| SRC-FR-24 (replaces SRC-FR-11) | SRC-4, SRC-11 (also PLAT-11) | SPEC 4, 13 | 3.2, 5.2 |
| SRC-FR-25 (replaces SRC-FR-13) | SRC-13 | SPEC 4, 13 | 5.10 |
| SRC-FR-26 (replaces SRC-FR-16) | SRC-20 (owner check OC-11) | SPEC 4, 13 | 5.5 |
| NFR-8 | SRC-10 | SPEC 4, 13 | 5.1, 5.3 |
| NFR-10 | SRC-13 | SPEC 4, 13, 17 | 5.10 |
| HLTH-FR-12 | SRC-29 | SPEC 4, 7 | 5.2, 5.9 |
| HLTH-FR-42 | SRC-8 | SPEC 4, 7 | 2.4, 5.2 |
| PLAT-FR-10 | SRC-32 | SPEC 4, 9 | 4 |
| PLAT-FR-12 | SRC-33 | SPEC 4, 9 | 4 |
| PLAT-FR-13 | SRC-33 | SPEC 4, 9 | 4 |

The last seven rows are requirements owned by the parent PRD or by other components that criteria of this component also verify.

All 31 criteria of PRD-sources v5 appear above: SRC-1 to SRC-8, SRC-10 to SRC-13 and SRC-20 to SRC-33. SRC-FR-1 to SRC-FR-10 and SRC-1 to SRC-8 and SRC-10 to SRC-13 are M0; SRC-FR-12 and SRC-FR-14 to SRC-FR-23 and SRC-20 to SRC-33 are M1.

**Invariants** (PRD-sources v5 1.6) and where this LLD enforces them:

| Invariant | Enforcement point | Verified by |
| --- | --- | --- |
| SRC-INV-1 Call a disabled source | Registry returns a `skip` for it; federation calls only `Selected` with `skip is None` (5.2) | SRC-3 |
| SRC-INV-2 Adapter sleeps, retries, reads secrets, writes files, logs credential URLs, or imports an HTTP library | Static import check; `Sleeper` injected only into the HTTP client (4, 5.3) | SRC-7, SRC-6 |
| SRC-INV-3 Docs-site host or path outside the allowlist, or substring matching | `DocsSiteAllowlist.allows` on parsed host and path (5.11) | SRC-23 |
| SRC-INV-4 Web source in the default fan-out | `select` removes `web` from auto selection (5.2) | SRC-28 |
| SRC-INV-5 Google sign-in file opened or copied, token kept beyond memory, or sent beyond `discoveryengine.googleapis.com` | `AuthSpec.origins` of the Vertex spec; the provider is LLD-platform v2 4.2 | SRC-32 |
| SRC-INV-6 A source's key sent to another host | `AuthSpec.origins` checked in the spec and in the HTTP client (4) | SEC-8 |

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

The adapter contract is a cross-team contract: M1 adapters are written by separate work units against it, and the conformance suite and the live check consume it. It is written down in [source adapter v1](../contracts/source-adapter-v1.md) (draft for the owner to approve at Gate 3; see 10). The Python below is the implementation form; where the two differ, the contract file is wrong and the owner is told. The tool and resource shapes that expose the registry belong to [LLD-search](LLD-search-v2.md) 2.1 and 2.3 and are listed in 2.4 only because the registry feeds them.

### 2.1 Source contract (`sources/base.py`)

```python
class Capability(StrEnum): SEARCH="search"; GET="get"; FULLTEXT="fulltext"; CITATIONS="citations"
                           AUTHORS="authors"; UPDATES="updates"; CRAWL="crawl"

GROUPS = frozenset({"scholarly", "preprints", "biomed", "repositories", "standards", "vendor_docs",
                    "code", "integrity", "education", "web", "reference"})        # PRD-sources v5 1.3
KNOWN_EXTRAS = frozenset({"pdf", "embeddings", "macos", "gcp"})                      # LLD-platform v2 7.2

@dataclass(frozen=True, config=ConfigDict(defer_build=True))      # pydantic dataclass, as core/specs.py
class SourceSpec:
    id: str; title: str; group: str
    capabilities: frozenset[Capability]
    id_schemes: frozenset[str]
    hosts: frozenset[str]                    # every host the adapter may call
    auth: AuthSpec | None
    rate: RateSpec
    timeout_s: float = 5.0
    max_page_size: int = 50
    max_bytes: int = 5_000_000
    needs_contact: bool = False
    extras: frozenset[str] = frozenset()
    probe: ProbeSpec = ProbeSpec(3600, "free", "")
    enabled_by_default: bool = True
    shutdown_on: date | None = None          # the status note of SRC-FR-1 (5.2, SRC-24)
    docs_url: str = ""
    instance_of: str | None = None           # "dspace" for dspace_mit
    error_classifier: ErrorClassifier | None = None
    def __post_init__(self) -> None: ...     # validation, below
    def policy(self, *, daily_quota: int | None = None) -> SourcePolicy: ...
    def deprecated_days(self, today: date) -> int | None: ...    # max(0, (shutdown_on - today).days); None if unset

class McpUpstreamPort(Protocol):              # implemented in M1 by platform/mcp_client.py
    async def call_tool(self, server: str, tool: str, arguments: Mapping[str, JsonValue], *, source: str) -> JsonValue: ...

@dataclass(frozen=True)
class SourceContext:                         # given to each adapter instance
    http: HttpPort; mcp: McpUpstreamPort | None; settings: SourceSettings; clock: Clock
    contact_email: str | None                # new in v2: Crossref and Unpaywall send it as a parameter (SRC-FR-24)

class SourceAdapter(Protocol):
    spec: SourceSpec
    def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None: ...
    async def search(self, req: SearchRequest) -> SearchPage: ...
    async def get(self, ident: Identifier) -> WorkRecord | None: ...
    async def fulltext_candidates(self, work: WorkRecord) -> list[FulltextCandidate]: ...
    async def citations(self, ident: Identifier, direction: Literal["citing","cited"],
                        cursor: str | None, limit: int) -> CitationPage: ...
    async def search_authors(self, query: str | None, orcid: str | None,
                             limit: int) -> list[AuthorRecord]: ...   # only for Capability.AUTHORS
    async def updates(self, ident: Identifier) -> list[UpdateNotice]: ...  # only for Capability.UPDATES
    async def probe(self) -> ProbeResult: ...
```

`search_authors` and `updates` are added because the search component needs them for `authors` and `check_integrity` (LLD-search v2 5.8, 5.10, 12). `AuthorRecord` is defined in LLD-search v2 3 (assumption: moved to `core/models.py`); `UpdateNotice` (kind, related identifier, date, source) is a new model whose exact fields the implementer fixes with the Crossref fixtures `[assumption]`. Like `citations`, each is called only when the spec lists the capability.

Adapters parse XML with `defusedxml`. They may import `urllib.parse` and `urllib.robotparser`, but not `urllib.request`, `http.client`, `socket`, `httpx`, `requests`, `time.sleep`, `asyncio.sleep`, or `research_mcp.platform.secrets` (SRC-7). Unsupported capabilities are declared in the spec, not stubbed: a method for a capability the spec does not list is never called (SRC-FR-2).

**`SourceSpec` validation (SRC-1).** `__post_init__` raises `ValueError` (pydantic wraps it in `ValidationError`, a `ValueError`) for any of these; a missing required field is the constructor's `TypeError`. The bounds are design values `[assumption]`: no source sets numbers, and they are chosen to admit every catalog source and to reject a typo that would hammer or stall an upstream.

| Field | Rule |
| --- | --- |
| `id` | Matches `[a-z][a-z0-9_]{1,39}`; also the pattern for an instance id |
| `title` | 1 to 120 characters |
| `group` | In `GROUPS` |
| `capabilities` | Not empty |
| `hosts` | Not empty; each entry is a lowercase bare host name (no scheme, path, port or userinfo) |
| `auth` | If set: `origins` not empty (SRC-1), every origin's host is in `hosts`, `secrets` not empty with each name matching `[A-Z][A-Z0-9_]{0,63}` (the `SecretRef` pattern), and `signup_url` is an `https` URL when `required` |
| `rate.rps` | Greater than 0 and at most 50 |
| `rate.burst` | 1 to 50 |
| `rate.concurrency` | 1 to 16 |
| `rate.daily_quota` | None, or at least 1 |
| `timeout_s` | 0.5 to 60 |
| `max_page_size` | 1 to 1000 |
| `max_bytes` | 1024 to 50 000 000 (the download cap `limits.download_bytes` is the ceiling) |
| `extras` | Subset of `KNOWN_EXTRAS` |
| `probe.cadence_s` | 60 to 604 800; for `cost="metered"`, at least 3600 |
| `docs_url` | Empty, or an `https` URL |
| `group == "web"` | `enabled_by_default` must be false and `probe.cost` must be `"metered"` unless the probe is free (5.7) |
| `shutdown_on` | A `date` or None |

`SourceRegistry` also refuses to register two specs with the same id (error at construction, not at the first call).

**Why `shutdown_on` is the status note.** SRC-FR-1 lists "status note (for example a shutdown date)"; SPEC-v5 4 and ADR 0006 list only the shutdown date; SRC-FR-14 and SRC-24 define the one note v2 shows, `deprecated(days)`. So `shutdown_on` and `docs_url` are the whole of it; a free-text field would be a note nothing displays (resolved from PRD-sources v5 SRC-FR-14, SPEC 4; was a v1 question).

### 2.2 Policy types (`core/specs.py`)

`core/specs.py` holds the pure policy types. They are shared by the HTTP layer (M0-07) and the source layer (M0-09). They are implemented as specified and are not changed in v2 except for `AuthSpec`, which keeps its origin-format check:

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

@dataclass(frozen=True)
class RateSpec: rps: float; burst: int = 1; concurrency: int = 2; daily_quota: int | None = None

@dataclass(frozen=True)
class ProbeSpec: cadence_s: int; cost: Literal["free", "metered"]; description: str

ErrorClassifier = Callable[[int, bytes], tuple[ErrorCode, str | None] | None]   # status, body -> (code, detail)

@dataclass(frozen=True)
class SourcePolicy:
    source: str; hosts: frozenset[str]; auth: AuthSpec | None; rate: RateSpec
    timeout_s: float; max_bytes: int; error_classifier: ErrorClassifier | None = None
```

`AuthSpec.__post_init__` already rejects a malformed origin (scheme, credentials, path). The empty-origins rule of SRC-1 lives in `SourceSpec.__post_init__` because an empty `origins` is a valid `AuthSpec` for tests of the HTTP client that attach nothing. `SourceSpec.policy(daily_quota=...)` copies `rate` with the given `daily_quota`; the registry passes the source's `budget_cap` (5.9). `AuthSpec.secrets` holds the Keychain item names, so a source's Keychain name lives in its `SourceSpec` and nowhere else (owner decision, 2026-10-22; SRC-FR-26).

### 2.3 Discovery contract

- **Built-in adapters** are discovered by scanning the `research_mcp.sources` package with `pkgutil.iter_modules`. Any module that defines a module-level `SPEC: SourceSpec` and `ADAPTER: type[SourceAdapter]` is registered. No central list is edited when a source is added (SRC-FR-26).
- **Instance kinds** (`dspace`, `docs_site`, `vertex_search`) also define `INSTANCE_MODEL: type[BaseModel]` (strict, `extra="forbid"`) and `instance_spec(base: SourceSpec, instance_id: str, cfg: BaseModel) -> SourceSpec`. The registry builds one source per settings entry whose `instance_of` names the kind (3.2), validates the entry against `INSTANCE_MODEL`, and calls `instance_spec` for the instance's `id`, `title` and `hosts`. A kind listed in the catalog with no configured instance (`docs_site`, `vertex_search`) is listed once, `unconfigured`, with the fix "add a `sources.<name>` entry with `instance_of = ...`" `[inferred from PRD-sources v5 1.3 rows 34 and 39]`. `dspace` is instance-only.
- **Adapters are in-tree only** (owner decision, 2026-10-22). Entry-point discovery of third-party adapters is dropped: nothing outside the `research_mcp.sources` package is loaded, so no installed code runs inside the daemon that holds the secrets cache.

### 2.4 Surfaces that expose the registry

These belong to other components and are listed here because the registry feeds them.

| Surface | Contract | Owner |
| --- | --- | --- |
| `list_sources` tool | `group: str = None, state: str = None`; service registry + health; annotations RO; M0 | [LLD-search](LLD-search-v2.md) 2.1 (unit M0-14) |
| `research://sources` resource | M0 resource | LLD-search 2.3 (unit M0-14) |
| `search` tool `site_set` argument | `site_set: str = None (M1; a configured site set)` | LLD-search 2.1 |
| `research-mcp sources check --live [--id X] [--refresh-fixtures]` | Live check (5.4) | [LLD-platform v2](LLD-platform-v2.md) 2.4 (command); 5.4 here (behavior) |
| `tools/gen_inventory.py` and `gen_inventory.py --check` | Writes `docs/generated/sources.md` from the registered adapters; the check is a CI gate. There is no `sources --markdown` command (SRC-FR-25) | 5.10 here (unit M0-16) |

The registry supplies one `SourceView` per source to `list_sources`, `research://sources`, `/api/status` and the UI source board (5.2). The `list_sources` result adds health fields from `source_health`; the field list of the tool is LLD-search's.

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

### 3.1 Shared models (`core/models.py`)

`core/models.py` holds the shared data types. The listing below shows the v2 changes in comments; every other model is as in the code today (`src/research_mcp/core/models.py`):

```python
JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
class Clock(Protocol): def now(self) -> datetime: ...           # UTC
class Sleeper(Protocol): async def sleep(self, seconds: float) -> None: ...
class AuthUse(StrEnum): SPEC="spec"; NONE="none"

from research_mcp.core.ids import Identifier                    # frozen dataclass (re-exported)
class Author(BaseModel): name: str; family: str | None = None; orcid: str | None = None
class OaLocation(BaseModel): url: str; source: str; kind: Literal["pdf","html","landing"]
                             license: str | None = None; version: str | None = None
class Provenance(BaseModel): source: str; upstream_id: str; adapter_version: str; retrieved_at: datetime
class WorkRecord(BaseModel):
    ids: list[Identifier]; title: str; authors: list[Author] = []; year: int | None = None
    published_at: date | None = None; venue: str | None = None; work_type: str = "article"
    abstract: str | None = None; oa_locations: list[OaLocation] = []; is_retracted: bool | None = None
    extra: dict[str, JsonValue] = {}; provenance: Provenance
class SearchFilters(BaseModel):
    year_from: int | None = None; year_to: int | None = None; work_type: str | None = None
    oa_only: bool = False; provider: str | None = None; repository: str | None = None
class SearchRequest(BaseModel):
    query: str; filters: SearchFilters = SearchFilters(); limit: int = 10; cursor: str | None = None
    site_set: str | None = None                       # new: the set's name, for logs and results
    site_domains: tuple[str, ...] = ()                # new: the set's domains, resolved by federation (5.8)
class SearchPage(BaseModel):
    records: list[WorkRecord]; total: int | None = None; next_cursor: str | None = None
    truncated: bool = False                           # new: the adapter dropped site-set domains (5.8)
class FulltextCandidate(BaseModel): location: OaLocation; priority: int
class CitationPage(BaseModel): ids: list[Identifier]; records: list[WorkRecord] = []; next_cursor: str | None = None
class ProbeResult(BaseModel):
    ok: bool; latency_ms: int; shape_ok: bool; detail_code: str | None = None
    quota_remaining: str | None = None; credential_expires_at: datetime | None = None
    api_version: str | None = None                    # new: DSpace version and similar; health stores it as api_version_seen
# Conflict, Work, FederatedResult, TextResponse, DownloadedFile, CallRecord: unchanged
```

Why the four additions (all internal models, no public contract changes): the adapter needs the resolved domains to build a query, so federation resolves the name once (an unknown name is `invalid_argument` before any call, SRC-31) and passes both; an adapter that drops domains must tell federation, which sets the envelope `truncated` and a warning; SRC-21 needs the DSpace version to reach `source_health.api_version_seen` (LLD-health v1 3), and `ProbeResult` is the only value `probe` returns; Crossref and Unpaywall need the owner's address as a request parameter (SRC-FR-24), which `HttpClient` already holds for the user agent but does not expose to adapters. `ProbeResult.api_version` and `SearchPage.truncated` default to their old behavior, so the M0 contract stays valid.

Every adapter maps upstream records to `WorkRecord` with `Provenance` (source id, upstream id, adapter version, retrieval time) and normalized identifiers (SRC-FR-9). `adapter_version` is the adapter module's `ADAPTER_VERSION: str` (a constant bumped when the mapping changes) `[assumption]`. Records from `web` sources have `work_type="webpage"`, the result URL as a `url` identifier and the snippet as `abstract`, which the search component wraps as untrusted (NFR-6; LLD-search 4).

Clarification carried from SPEC-v2 0.6 (it cites section 4; `FederatedResult` is defined here):

| Unit | Section | Requirement |
|---|---|---|
| M0-03 | 3.7, 4; PLAT-31, SRCH-FR-27 (was SRCH-FR-4) | `Budget.fit` MUST keep `FederatedResult.statuses` (one status per source) and MUST fail explicitly when mandatory metadata cannot fit. Its prefix search MUST distinguish "does not validate" from "too large". |

(SPEC-v2 0.6; the owning LLD for `Budget.fit` is [LLD-platform v2](LLD-platform-v2.md) 5.6, which carries the same row; this LLD keeps it only because `FederatedResult` is defined here. SPEC-v5 19 lists both.)

### 3.2 Settings keys read by this component

From [LLD-platform v2](LLD-platform-v2.md) 7.1, which owns `settings.Settings` (loaded from `~/.config/research-mcp/config.toml`, then `RESEARCH_MCP_*` environment overrides nested with `__`):

| Key | Default | Notes |
|---|---|---|
| `contact.email` | none | Crossref `mailto`, Unpaywall `email`, user agent. A placeholder domain (`example.com`, `example.org`, `test`, `invalid`, and their subdomains) is a settings validation error, so the daemon does not start until it is fixed. If unset, only the sources with `needs_contact` are `unconfigured`; the daemon starts (SRC-FR-24; PLAT-11; owner decision, 2026-10-22). |
| `federation.default_groups` | `["scholarly", "preprints"]` | The registry removes `web` from auto selection even if it is listed here (5.2). |
| `sources.<id>.enabled` | spec default (`False` for `web` sources, ADS and Lens) | |
| `sources.<id>.budget_cap` | none (`100` for `web` sources) | Daily call cap for metered sources (UI Quota page); resets at local midnight |
| `sources.vertex_<name>` | none | `{ instance_of = "vertex_search", project = "...", location = "global", engine_id = "...", title = "..." }`; one per Vertex AI Search engine (5.7) |
| `sources.google_pse.engine_id` | none | Programmable Search engine id (v1 `GOOGLE_PSE_CX`); not a secret |
| `web.strategy` | `"fallback"` | `fallback` or `all` (5.9) |
| `web.order` | `["vertex_*", "brave_search", "serpapi", "google_pse"]` | `vertex_*` expands to the configured Vertex instances in name order |
| `site_sets.<name>` | `v1_docs` (3.3) | A list of domains; names match `[a-z0-9_]{1,40}` |
| `sources.<id>.<field>` | per spec | For example `sources.dspace_penn.base_url` |

**Instances** come from settings. For example, `sources.dspace_mit = { instance_of = "dspace", base_url = "https://dspace.mit.edu/server/api", title = "DSpace@MIT" }`. The same form covers `dspace_harvard`, `dspace_cornell` and `dspace_penn`, and the `docs_site_<name>` entries with their `allowed_hosts` and `path_prefixes`. An instance's `hosts` come from its base URL (docs sites: from `allowed_hosts`) through `instance_spec` (2.3). `SourceSettings` allows extra fields (`model_config = ConfigDict(extra="allow")`), so the instance fields reach the registry unchanged and are validated there against `INSTANCE_MODEL`.

**Merging defaults with config (SRC-27).** `defaults.toml` is the lowest layer, below `config.toml` and the environment. Tables merge by key: a `site_sets.<name>` or `sources.<id>` in the config replaces the default entry with that name and leaves the others. A site set whose list is empty is treated as removed (an unknown name), which is how the owner removes `v1_docs` `[assumption]`. An invalid set name (not `[a-z0-9_]{1,40}`) is a settings error (`Settings.site_set_names`, already in the code).

### 3.3 Default data (`defaults.toml`)

`src/research_mcp/packaging/defaults.toml` (package data) holds data the owner can override in `config.toml`. It carries every v1 endpoint forward (SRC-FR-17, SRC-26):

- `site_sets.v1_docs`: v1's docs-domain list, verbatim, 26 domains: `keycloak.org`, `ory.sh`, `supertokens.com`, `authelia.com`, `goauthentik.io`, `zitadel.com`, `logto.io`, `casdoor.org`, `authgear.com`, `kanidm.github.io`, `freeipa.org`, `syncope.apache.org`, `openpolicyagent.org`, `cerbos.dev`, `authzed.com`, `casbin.org`, `permify.co`, `topaz.sh`, `warrant.dev`, `pomerium.com`, `developer.hashicorp.com`, `infisical.com`, `webauthn.guide`, `jwt.io`, `datatracker.ietf.org`, `zanzibar.academy`.
- Four `dspace_*` instances (catalog rows 24 to 27) and six `docs_site_*` instances for v1's crawl projects, with the same seeds and filters:

| Instance | Allowed host (`[inferred]` from the seed) | Seeds | Follow links | Path prefixes |
| --- | --- | --- | --- | --- |
| `docs_site_keycloak` | `www.keycloak.org` | sitemap `https://www.keycloak.org/sitemap.xml` | sitemap | `/docs/`, `/securing-apps/`, `/guides/` |
| `docs_site_ory` | `www.ory.sh` | sitemap `https://www.ory.sh/sitemap.xml` | sitemap | `/docs/` |
| `docs_site_opa` | `www.openpolicyagent.org` | sitemap `https://www.openpolicyagent.org/sitemap.xml` | sitemap | `/docs/` |
| `docs_site_vault` | `developer.hashicorp.com` | `https://developer.hashicorp.com/vault/docs` | yes | `/vault/docs` |
| `docs_site_syncope` | `syncope.apache.org` | the 4.1 and 4.0 reference guide and getting-started pages (URLs: build step below) | no | (the seed pages only) |
| `docs_site_freeipa` | `www.freeipa.org` | `https://www.freeipa.org/page/Documentation.html` | yes | `/page/` |

A `docs_site` instance has `allowed_hosts`, `path_prefixes`, and either `sitemap` or `seed_urls` with `follow_links` (`INSTANCE_MODEL` of `docs_site`). Example entry form in `defaults.toml`:

```toml
[sources.docs_site_ory]
instance_of = "docs_site"
title = "Ory documentation"
allowed_hosts = ["www.ory.sh"]
path_prefixes = ["/docs/"]
sitemap = "https://www.ory.sh/sitemap.xml"
```

**Build step for the default values (owner decision, 2026-10-22).** The base URLs of `dspace_harvard`, `dspace_cornell` and `dspace_penn` and the seed pages of `docs_site_syncope` are not in any approved document, and this LLD leaves the values out. The implementing unit reads them from the read-only v1 source and the repository documentation, never reads real credentials, and lists them in its handoff; the owner confirms the list at review (the M1 exit). The test for SRC-26 asserts the 26 domains, the six instance names and their seeds from this table.

### 3.4 Fixtures on disk

Each source has a fixtures folder, `tests/sources/<id>/fixtures/` (an instance kind has one folder named for the kind; for `dspace` the instances share it), with the seven fixtures of SRC-FR-8 (owner decision, 2026-10-22: seven, not six):

| Fixture | Contents |
| --- | --- |
| `search_ok`, `search_empty`, `get_ok` | Normal responses |
| `err_429` | Status and headers, as JSON; includes `Retry-After` |
| `err_5xx` | JSON |
| `malformed` | A broken body |
| `oversize.marker` | A marker only; the test generates the large body |

Body fixtures use the upstream's format: `.json` for JSON APIs, `.xml` for Atom (arXiv). Fixtures are recorded with credentials removed (repository rule: no secrets in fixtures). The live check writes refreshed ones to `_review/` only (5.4).

### 3.5 Persisted state

This component owns no database table and adds no column or migration. Each call to a web source counts against its cap through the `calls_today` figure of `source_health` in `state.db` (LLD-health v1 3, SPEC 10); at the cap the source reports `budget_exhausted` until the next local midnight (5.9). SPEC-v2 5.5 called the figure `quota_used`; the schema has no such column (see 5.13). `source_health` belongs to the health component.

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

Drafted from the approved documents; **Reviewed by `security-reviewer` at Gate 3 (2026-10-23)**, and the control owner confirms. No policy is invented here; where a rule is a design choice it is tagged.

- **Adapters hold no secrets** (SRC-FR-3, SRC-INV-2). Nothing under `sources/` imports `research_mcp.platform.secrets` (SRC-7). Credential presence and health come into the registry as callables, so nothing under `sources/` imports the secrets or health modules.
- **Host policy.** Every `SourceSpec` lists `hosts`, every host the adapter may call. In the HTTP client, a request whose host is not in `policy.hosts` fails with `blocked_by_policy` (LLD-platform v2 4.4; PLAT-36). Conformance check 7 verifies every request goes to a host in `spec.hosts` (5.3). An instance's hosts are derived from validated settings (`https` only; a `base_url` with credentials, a query or a fragment is a settings error) `[assumption]`.
- **Credential attachment** (LLD-platform v2 4.4; PLAT-FR-12):
  - The secret comes from `CredentialResolver`.
  - It is attached only when the request origin is in `policy.auth.origins` (SEC-8; SEC-INV-5). `SourceSpec` validation additionally requires every origin's host to be in `hosts` (2.1).
  - Placement is `header` (name from the spec), `bearer`, or `query` (parameter name from the spec).
  - Query placement is used only where the API offers nothing else (SerpAPI), and then the URL is never logged and the redactor masks the parameter (SEC-9).
- **Keychain items** used by sources (LLD-security v2 4.1; each is in the `AuthSpec.secrets` of its `SourceSpec`): `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `CORE_API_KEY`, `GOOGLE_DEVKNOWLEDGE_API_KEY`, `GITHUB_TOKEN`; `ZENODO_TOKEN`, `NCBI_API_KEY`, `NVD_API_KEY`, `ADS_API_TOKEN`, `LENS_API_TOKEN`, `OPENCITATIONS_TOKEN`; `BRAVE_SEARCH_API_KEY`, `SERPAPI_API_KEY` (M1). `GOOGLE_DEVKNOWLEDGE_API_KEY` is shared by `google_devknowledge` and `google_pse`, as in v1; each source's `origins` limit where it is sent (SRC-INV-6; SEC-8). A new source adds its Keychain name to its own `SourceSpec` and the generated inventory; this document and the SPEC are not edited (SRC-FR-26; owner decision, 2026-10-22).
- **Google sign-in for `vertex_search`** (LLD-platform v2 4.2; SRC-FR-23; SEC-27; SEC-INV-11):
  - `vertex_search` does not use a Keychain item. Its `AuthSpec` names the secret `GOOGLE_SIGNIN`, `placement="bearer"`, `origins=("https://discoveryengine.googleapis.com",)`, `validation="probe"`.
  - `SecretRef` gains the backend `gcloud_adc`, resolved by `platform/google_adc.py` (`GoogleAdcProvider`, extra `gcp`). Loading and refreshing run through `anyio.to_thread.run_sync`, never on the event loop. The refresh goes from `google-auth` to `oauth2.googleapis.com` only and is recorded as a `CallRecord` with `source="google_signin"`.
  - The access token is held in memory as a `Secret` and revealed only by `platform/http.py`, as a bearer token plus `X-Goog-User-Project: <project>` (the project comes from the instance settings, which are not secrets).
  - v2's own code never opens, copies or writes the credential file. The Vertex adapter never sees the token.
- **Web-source auth** (5.7): `brave_search` uses the `X-Subscription-Token` header; `serpapi` uses the `api_key` query parameter (URL never logged); `google_pse` uses the `x-goog-api-key` header.
- **Docs-site allowlist** (SRC-FR-15; SRC-INV-3). v1 matched filters as URL substrings; v2 matches the parsed host against `allowed_hosts` and the parsed path against `path_prefixes` (5.11), and honors `robots.txt`.
- **Contact email.** The owner's address is personal data sent on purpose to the sources that ask for it (PRD-sources v5 2.6). A placeholder address is rejected by settings validation and never reaches an adapter (SRC-FR-24; PLAT-11).
- **Tool results.** Every string in a successful tool result, including source snippets and titles, is redacted for registered secrets in `@tool_boundary` (SEC-28, PRD-security v3; owner decision, 2026-10-22). Adapters do not redact; they cannot see secrets. The `Untrusted` wrapping of web snippets is the search component's (LLD-search 4).
- **Clients and the daemon.** Sources add no listener, route or token. Clients reach the daemon only through the stdio shim (SEC-INV-10).

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

### 5.1 Layout

```
  sources/
    base.py                   # SourceSpec, Capability, GROUPS, SourceAdapter, SourceContext, translate_errors
    registry.py               # SourceRegistry, Selected, SourceView, RegisteredSource
    mcp_upstream.py           # UpstreamMcpAdapter base
    robots.py                 # RobotsCache: robots.txt rules for docs sites (5.11)
    docs_allowlist.py         # DocsSiteAllowlist: host and path matching (5.11)
    arxiv.py crossref.py openalex.py semantic_scholar.py datacite.py core_ac.py unpaywall.py
    openaire.py doaj.py zenodo.py hal.py dblp.py orcid.py ads.py lens.py
    osf.py biorxiv.py medrxiv.py ssrn.py hf_papers.py
    europe_pmc.py pubmed.py clinical_trials.py
    dspace.py                 # one adapter, instances from config
    ietf.py nist.py nvd.py aws_knowledge.py ms_learn.py google_devknowledge.py docs_site.py
    vertex_search.py brave_search.py serpapi.py google_pse.py    # group "web" (5.7)
    loc.py open_library.py wikipedia.py                       # group "reference"
    sitequery.py              # pure helpers: site_set -> provider query strings and batches
    github.py opencitations.py crossref_updates.py eric.py
  testing/                    # importable fakes for tests: clock.py adapters.py livecheck.py launchctl.py notifier.py
tests/
  unit/sources/ ...   sources/<id>/fixtures/ + test_<id>.py   sources/conftest.py   sources/test_conformance.py
tools/gen_inventory.py        # writes docs/generated/sources.md; --check gates CI
```

`robots.py` and `docs_allowlist.py` define neither `SPEC` nor `ADAPTER`, so discovery skips them like `base.py` and `registry.py`.

Related platform modules: `platform/mcp_client.py` (`McpUpstreamPort`, MCP client over the shared HTTP client) and `platform/google_adc.py` (`GoogleAdcProvider`, M1, extra `gcp`).

**Catalog to module map** (PRD-sources v5 1.3; sources by row number):

| Rows | Module | Notes |
| --- | --- | --- |
| 1 to 3 | `arxiv`, `crossref`, `openalex` | M0 |
| 4 to 23 | `semantic_scholar`, `datacite`, `core_ac` (source id `core`), `unpaywall`, `openaire`, `doaj`, `zenodo`, `hal`, `dblp`, `orcid`, `ads`, `lens`, `osf`, `biorxiv`, `medrxiv`, `ssrn`, `hf_papers`, `europe_pmc`, `pubmed`, `clinical_trials` | one source each |
| 24 to 27 | `dspace` | four default instances (5.12) |
| 28 to 33 | `ietf`, `nist`, `nvd`, `aws_knowledge`, `ms_learn`, `google_devknowledge` | the two upstream MCP sources use `mcp_upstream.py` (5.6) |
| 34 | `docs_site` | six default instances (3.3). M1 delivers `get`, the allowlist and `robots.txt` only; `search` (local) and `crawl` land in M2 per SPEC v5 section 14 (owner decision, 2026-10-22) |
| 35 to 38 | `github`, `opencitations`, `crossref_updates`, `eric` | |
| 39 to 42 | `vertex_search`, `brave_search`, `serpapi`, `google_pse` | group `web` (5.7) |
| 43 to 45 | `loc`, `open_library`, `wikipedia` | group `reference` |

With the default configuration the registry lists at least 45 sources (rows 1 to 45, with `docs_site` replaced by its six instances and `vertex_search` listed once as `unconfigured`), which meets the M1 exit of 45 (PRD-v7 OUT-1; owner decision, 2026-10-22). NFR-8 values (arXiv 1 request per 3 s, concurrency 1) are in the three M0 specs below.

**The three M0 adapters** (PRD-sources v5 SRC-10 to SRC-12). Values tagged `[assumption]` are confirmed by the unit from the provider's published limits and recorded in the unit's handoff.

| Spec field | `arxiv` | `crossref` | `openalex` |
| --- | --- | --- | --- |
| group, capabilities | `preprints`; search, get, fulltext | `scholarly`; search, get, updates | `scholarly`; search, get, fulltext, citations, authors |
| hosts | `export.arxiv.org` `[assumption]` | `api.crossref.org` | `api.openalex.org` |
| auth | none | none; `needs_contact=True` (the address goes in the `mailto` parameter) | `OPENALEX_API_KEY`, required, placement per the provider (query or header, set in the unit from the provider's docs), origin `https://api.openalex.org` |
| rate | `RateSpec(rps=1/3, burst=1, concurrency=1)`, https only (NFR-8; SRC-10) | polite pool tier `[assumption]` | provider tier `[assumption]` |
| page size | provider default | provider default | at most 100 (SRC-12) |
| XML | Atom, parsed with `defusedxml` | JSON | JSON; uses `topics` and `last_known_institutions` |
| error classifier | none | none | `classify_openalex(status, body)`: a 429 whose body contains "Insufficient budget" (case-insensitive) returns `(ErrorCode.BUDGET_EXHAUSTED, "daily budget")`; anything else returns None (SRC-12) |

### 5.2 Registry (`sources/registry.py`)

```python
@dataclass(frozen=True)
class RegisteredSource: spec: SourceSpec; adapter_cls: type[SourceAdapter]; settings: SourceSettings; instance: BaseModel | None

@dataclass(frozen=True)
class Selected: source: str; adapter: SourceAdapter; skip: SourceStatus | None

@dataclass(frozen=True)
class SourceView:                            # one per source, for list_sources, research://sources, /api/status, UI
    id: str; title: str; group: str; capabilities: tuple[str, ...]
    state: str                               # see "States" below
    reason: str | None; fix_hint: str | None # exact fix; names Keychain items and URLs, never values
    enabled: bool; shutdown_on: date | None; deprecated_days: int | None
    signup_url: str | None; docs_url: str | None
    budget_cap: int | None; calls_today: int | None; budget_reset_at: datetime | None
```

- **Construction.** `SourceRegistry(settings, ctx_factory, *, has_credential: Callable[[str], bool], health: Callable[[str], str | None] = lambda s: None, calls_today: Callable[[str], int] = lambda s: 0, has_extra: Callable[[str], bool] = default_has_extra, clock: Clock = SYSTEM_CLOCK, modules: Iterable[str] | None = None, extra_adapters: Iterable[tuple[SourceSpec, type[SourceAdapter]]] = ())`. Tests pass `modules=[]` and `extra_adapters` from `research_mcp.testing.adapters`; the daemon passes the defaults. Credential presence, health, the daily call count and extra detection come in as callables, so nothing under `sources/` imports the secrets, health or store modules. `default_has_extra` maps an extra to its import (`gcp` to `google.auth`) with `importlib.util.find_spec` and does not import the package `[inferred]`.
- **Lookup.** `all() -> list[RegisteredSource]`, `get(id)`, `by_group(group)`, `view(id=None) -> list[SourceView]`, `policy(source) -> SourcePolicy` (the registry implements `PolicyResolver`, LLD-platform v2 2.2, from each spec's `policy(daily_quota=<budget_cap>)`).
- **Selection.** `select(groups, capability, filters, explicit) -> list[Selected]`.
  - `explicit` (source ids) wins over `groups`; an unknown id raises `ToolError(INVALID_ARGUMENT)`.
  - With neither, selection is automatic: `groups = federation.default_groups` **minus `web`**, even if the owner listed `web` there (SRC-28; SRC-INV-4). A caller names `web` through `groups=["web"]` or an id.
  - Sources lacking the `capability` are left out (not skipped). The `filters` are passed through to adapters and do not change selection.
  - Each remaining source gets a `skip` computed in this order; the first match wins:

| # | Condition | `skip.state` | Fix hint or reason |
| --- | --- | --- | --- |
| 1 | `settings.enabled` is false, or unset and `enabled_by_default` is false | `disabled` | "Disabled in settings. Enable it with `research-mcp config set sources.<id>.enabled true`" (SRC-3; SRC-FR-5) |
| 2 | An extra in `spec.extras` is not installed | `unconfigured` | "Install the extra: `uv tool install 'research-mcp[gcp]'`" `[assumption]` (SRC-5; SRC-FR-7) |
| 3 | `spec.auth.required` and `has_credential` is false for a name in `auth.secrets` | `unconfigured` | "Add Keychain item `research-mcp/<NAME>` (sign up: `<signup_url>`)" with the command from LLD-health 5 (`security add-generic-password -U -s research-mcp/<NAME> -a "$USER" -w`, no value) (SRC-4; SRC-FR-6) |
| 4 | `spec.needs_contact` and `contact.email` is unset | `unconfigured` | "Set `contact.email` to your own address: `research-mcp config set contact.email <address>`" (SRC-4; SRC-FR-24) |
| 5 | An instance kind with no valid instance settings | `unconfigured` | "Add or complete `sources.<name>` (`instance_of = ...`)" |
| 6 | `budget_cap` is set and `calls_today(id) >= budget_cap` | `budget_exhausted` | "Daily cap reached; resets at local midnight" (SRC-29) |
| 7 | `health(id)` is `down` | `skipped_unhealthy` | the health reason (HLTH-FR-12) |
| 8 | `health(id)` is `rate_limited` or `budget_exhausted` | `rate_limited` or `budget_exhausted` | until or reset time (HLTH-FR-12) |

  - A skipped source is never called (SRC-INV-1). A source with state `disabled` or `unconfigured` never reaches the HTTP layer; a source with `budget_exhausted` is selected and reported without a call (SRCH-FR-27).
  - A source with a shutdown date is not skipped; `SourceView.deprecated_days` carries `deprecated(days)` and the health service shows the badge (SRC-24, SRC-FR-14).
- **States in `SourceView`.** The registry's own states are `disabled`, `unconfigured` and `budget_exhausted` from rows 1 to 6, else the health state string (`ok`, `degraded`, `down`, `rate_limited(until)`, `quota_low`, and so on; HLTH-FR-10), else `ok`. `deprecated(days)` is a badge shown with the state, as the health PRD defines it `[inferred]`.
- **Web chain.** `web_chain(strategy, order) -> list[Selected]` expands `vertex_*` to the configured Vertex instance ids in name order, drops names that are not registered, and returns the sources in `web.order` with their `skip`s (5.9).
- **Instance building.** For each settings entry with `instance_of`, validate against the kind's `INSTANCE_MODEL`, call `instance_spec` and construct `ADAPTER(spec, ctx_factory(spec))`. An invalid entry yields row 5 for that entry and never stops the daemon. A duplicate id between a built-in and an instance is a construction error.

Discovery and instances are in 2.3 and 3.2. `FederationService.search` calls `registry.select(...)` first; statuses for skipped sources are created immediately (LLD-search 5.4).

### 5.3 Conformance suite (`tests/sources/test_conformance.py`)

`tests/sources/test_conformance.py` is parametrized over `SourceRegistry.all()`. It serves the fixtures through an `httpx.MockTransport`, uses a fake `Sleeper` and a `FakeClock`, and checks (SRC-6; SRC-20):

1. `search_ok` maps to at least one `WorkRecord` with a normalized identifier and provenance.
2. `search_empty` returns an empty page, not an error.
3. 429 raises `HttpError(rate_limited)` with `retry_after_ms`, and the fake sleeper records the wait.
4. 5xx raises `upstream_error` once the retry budget is spent.
5. A malformed body raises `upstream_error`, never `KeyError`, `TypeError` or `ValueError`.
6. An oversize body raises `too_large` before the whole body is read.
7. Every request goes to a host in `spec.hosts`.
8. `probe` returns `ok=True, shape_ok=True` against `get_ok`, and `shape_ok=False` against `malformed`.

Run a single source with `-k <id>`. The fake adapter in `research_mcp.testing.adapters` carries its own seven fixtures in memory and is registered through `extra_adapters`, so the suite runs in M0-09 before any real adapter exists (SRC-6). A source that declares `needs_contact` or an `auth` gets a fake contact address and a `FakeProvider` secret from `tests/sources/conftest.py`. A conformance run also asserts the seven fixture files exist for the adapter (SRC-FR-8) and, for each adapter that declares an `error_classifier`, that its test file exercises it.

**Adapter error discipline.** `base.translate_errors` is a decorator for adapter methods that maps `KeyError`, `TypeError`, `ValueError`, `pydantic.ValidationError` and `defusedxml` exceptions to `HttpError(UPSTREAM_ERROR, detail="malformed_body")`, so check 5 holds without per-adapter code. An `HttpError` passes through unchanged.

**Adapter import check (SRC-7).** `tests/unit/sources/test_adapter_imports.py` parses every module under `src/research_mcp/sources/` with `ast` and fails on: an import of `httpx`, `requests`, `urllib.request` (including `from urllib import request`), `http.client`, `socket` or `research_mcp.platform.secrets`; a call of `time.sleep` or `asyncio.sleep` (including `from time import sleep`); and, stricter than SRC-7 and tied to SRC-FR-3 and the XML rule of the security LLD, an import of `xml.etree`, `xml.dom`, `xml.sax` or `lxml` (use `defusedxml`) and a call of `open(` or `Path.write_text` or `Path.write_bytes`. `urllib.parse` and `urllib.robotparser` are allowed.

### 5.4 Live check

`research-mcp sources check --live [--id X] [--refresh-fixtures]` calls each enabled source once through the daemon's client (SRC-FR-12; SRC-25). The command is registered by `cli.py` (platform, unit M0-16) and calls `research_mcp.testing.livecheck.run` (new, sources; it is an importable helper, not an adapter).

1. Select the enabled sources (all, or the one named by `--id`). A `web` source or any source with `probe.cost == "metered"` is called only when `--id` names it, so a bare `--live` never spends `[assumption]`.
2. For each, call `search` with the module's optional `LIVE_QUERY` (default `"research"` `[assumption]`) and `get` with `LIVE_GET_ID` when set, through a `RecordingHttp` wrapper around the daemon's `HttpPort`. The wrapper keeps the status, a header allow-list (`Retry-After`, `Content-Type`, rate-limit headers) and the body; it never keeps request headers, and it passes bodies and URLs through the `Redactor` before they are held.
3. Print one line per source: the state, latency and whether `probe` returned `shape_ok`.
4. With `--refresh-fixtures`, write the recorded responses to `tests/sources/<id>/fixtures/_review/` only. The target path is built from the validated source id and a fixed file name, resolved, and refused unless it lies under that `_review` folder. Existing files in `fixtures/` are never opened for writing. Files in `_review/` replace earlier files in `_review/`. The owner reviews and moves them by hand (SRC-25).

The live test (`pytest -m live`) drives the same function against real upstreams and is deselected by default (NFR-9).

### 5.5 New-source checklist (definition of done)

The SPEC-v2 5.4 checklist without its old step 5 (SRC-FR-26; owner decision, 2026-10-22):

1. Add `src/research_mcp/sources/<id>.py` with `SPEC` and `ADAPTER`. No other source file changes.
2. Discovery is automatic.
3. Add a fixtures folder with the seven fixtures. The conformance suite passes with `-k <id>`.
4. Add unit tests for any source-specific mapping.
5. If the source needs a credential, put its Keychain name and signup URL in the spec (`AuthSpec.secrets`, `AuthSpec.signup_url`). No document is edited: the name appears in the generated inventory (SRC-FR-26).
6. Regenerate the inventory (`tools/gen_inventory.py`). In milestone plans, one closing unit does this for all new sources.

The files a new-source unit may touch are the module, its fixtures folder and its tests; owner check OC-11 verifies it (SRC-OUT-2).

### 5.6 Upstream MCP adapters

Upstream MCP servers (AWS Knowledge, Microsoft Learn) are adapters that use an MCP client instead of HTTP JSON (SPEC 4). They call `McpUpstreamPort.call_tool` (2.1), implemented in M1 by `platform/mcp_client.py` over the shared HTTP client, so rate limits, host policy, telemetry and redaction apply (SRC-FR-10; SRC-22), and build on the `UpstreamMcpAdapter` base in `sources/mcp_upstream.py`:

```python
class UpstreamMcpAdapter:                    # base for aws_knowledge and ms_learn
    server: str                              # the MCP endpoint URL; its host is in spec.hosts
    search_tool: str; get_tool: str
    def map_search(self, payload: JsonValue) -> list[WorkRecord]: ...    # per adapter
    def map_get(self, payload: JsonValue) -> WorkRecord | None: ...
```

`search` calls `ctx.mcp.call_tool(self.server, self.search_tool, {...}, source=self.spec.id)`; the platform client turns an MCP-level error into `HttpError` so the same classification applies. Endpoint URLs and tool names are `[assumption]`: AWS Knowledge `https://knowledge-mcp.global.api.aws` (tools `aws___search_documentation`, `aws___read_documentation`) and Microsoft Learn `https://learn.microsoft.com/api/mcp` (tools `microsoft_docs_search`, `microsoft_docs_fetch`); the unit confirms them against the vendor and records them in the spec and the fixtures. Both are free, unauthenticated sources in group `vendor_docs` with `auth=None`. SRC-22 tests run against an in-memory MCP server fake (`research_mcp.testing.adapters`), and assert that a call to a host outside `spec.hosts` is `blocked_by_policy` and that telemetry has a `CallRecord` for the call.

### 5.7 Web sources

All four have `group="web"`, `enabled_by_default=False`, `probe.cost="metered"` where no free probe exists, `rate.daily_quota` from `budget_cap`, and return `work_type="webpage"` records with the URL as identifier and the snippet as an untrusted abstract (SRC-FR-19).

| Source | Endpoint | Auth | Free probe and quota |
|---|---|---|---|
| `vertex_search` (instances `vertex_<name>`) | `POST https://discoveryengine.googleapis.com/v1/projects/{project}/locations/{location}/collections/default_collection/engines/{engine_id}/servingConfigs/default_search:search` with `{"query", "pageSize", "pageToken"}` | Google sign-in (4) | `GET .../engines/{engine_id}` every 6 h (no query cost) |
| `brave_search` | `GET https://api.search.brave.com/res/v1/web/search?q=&count=` | `X-Subscription-Token` header | none free: one query every 24 h; rate-limit headers parsed passively on every call |
| `serpapi` | `GET https://serpapi.com/search.json?engine=google&q=&num=` | `api_key` query parameter (URL never logged) | `GET https://serpapi.com/account.json` (free; gives searches left) every 6 h |
| `google_pse` | `GET https://www.googleapis.com/customsearch/v1?cx=&q=&num=` | `x-goog-api-key` header | none free: one query every 24 h; `shutdown_on = 2027-01-01` |

`google_pse` and `google_devknowledge` share `GOOGLE_DEVKNOWLEDGE_API_KEY` (4); `google_pse` shows `deprecated(days)` until removal (SRC-33). Vertex's `project`, `location` and `engine_id` come from the instance settings and are not secrets (SRC-FR-23). The Vertex adapter works without the `gcp` extra only in tests: without the extra the registry reports `unconfigured` (row 2).

**A configured web source also needs `enabled = true`** (owner decision, 2026-10-22). Presence of settings and credential never enables an outside call. The settings default `enabled = false` for every `web` source and `budget_cap = 100`, so a web source runs only when the owner sets `enabled = true` and the settings and credential are present. The PRD wording would read "configured and enabled".

### 5.8 Site sets in queries (`sources/sitequery.py`)

Pure functions (SRC-FR-22; SRC-31):

- `resolve_site_set(name: str, site_sets: Mapping[str, Sequence[str]]) -> tuple[str, ...]` returns the domains, or raises `ToolError(INVALID_ARGUMENT)` for an unknown or empty set. Federation calls it before any source is called, so an unknown name makes no call.
- `site_query(query, domains) -> str` builds `(<query>) (site:a OR site:b ...)`, as v1 did.
- `site_batches(query, domains, max_chars, max_batches) -> SiteBatches` where `SiteBatches` holds `queries: list[str]` and `truncated: bool` (v1 returned a bare list; the flag is how a dropped domain is reported). The domains the query names come first (v1's ranking: a domain ranks first when its registrable label, such as `keycloak`, appears in the lowercased query; the rest keep set order). Domains are packed greedily into queries of at most `max_chars` characters including the fixed text; a query with no room for one domain raises `invalid_argument`. When domains remain after `max_batches` queries, `truncated` is true.
  - Brave: `max_chars=380`, `max_batches=3`; the adapter runs the batches as separate calls (each counts against the cap, 5.9) and merges results.
  - SerpAPI and Programmable Search: `max_batches=1`; `truncated` is true when domains are dropped, and the adapter sets `SearchPage.truncated`.
- Vertex ignores `site_query`; when `site_domains` is set, results are filtered after the call by the parsed host of each result URL (a host matches a domain exactly or as a subdomain `host == d or host.endswith("." + d)`), never by substring. A page whose results are all filtered out is `empty`.

Federation sets the envelope `truncated` and a warning when any source reports `SearchPage.truncated` (LLD-search 5.4).

### 5.9 Federation of the `web` group

Implemented in `FederationService` ([LLD-search](LLD-search-v2.md) 5.4); the rules and the registry side are here (SRC-FR-19 to SRC-FR-21; SPEC 5):

- `auto` selection never includes `web` (5.2).
- When a caller names the group (or more than one web source) and `web.strategy == "fallback"`, the web sources run one at a time in `registry.web_chain` order. A source whose `skip` is set (`disabled`, `unconfigured`, `budget_exhausted`, `rate_limited` or `skipped_unhealthy`, the last being the health state `down`) is passed over with that status. The first that returns at least one record without error ends the chain; the sources after it report `state="not_needed"`. A source that returns no records reports `empty` and the chain continues; one that errors reports its error and the chain continues. Non-web sources in the same call still fan out in parallel, and the chain shares the overall deadline (`federation.deadline_s`).
- With `strategy == "all"`, web sources fan out like any other group.
- A page costs one paid query under `fallback` (SRC-30). The next page of a chain goes to the source that answered the first page; the combined cursor carries its id `[assumption, to be fixed in LLD-search 5.4]`.
- **Cap.** `budget_cap` defaults to 100 calls a day for web sources. The count is the source's `calls_today` (every HTTP attempt recorded for it since local midnight, including a metered probe and each Brave batch). At the cap the registry returns `skip=budget_exhausted` with the reset `next_local_midnight(clock.now())`, computed in the system time zone and tested with `FakeClock` (SRC-29). The HTTP client does not enforce `RateSpec.daily_quota`, so the registry check is the enforcement; with a chain running one source at a time, the check-then-call gap is one call.

### 5.10 Source inventory

`tools/gen_inventory.py` writes `docs/generated/sources.md` from the registered adapters (the registry built with default settings and the default adapters), and `tools/gen_inventory.py --check` fails when the committed file differs from the generated text (SRC-FR-25; SRC-13; NFR-10). The inventory lists each source's id, title, group, capabilities, auth (Keychain names, signup URL), rate, hosts, extras, default state, probe cadence and cost, and shutdown date, sorted by id with no timestamp so that regeneration is deterministic. CI runs `uv run python tools/gen_inventory.py --check` (LLD-platform v2 5.8). The inventory is the only generator: there is no `research-mcp sources --markdown` (owner decision, 2026-10-22). Adapter units do not touch `docs/generated/sources.md`; one closing unit regenerates the inventory.

### 5.11 Docs-site allowlist and `robots.txt` (SRC-FR-15; SRC-23)

`sources/docs_allowlist.py`:

```python
@dataclass(frozen=True)
class DocsSiteAllowlist:
    allowed_hosts: frozenset[str]; path_prefixes: tuple[str, ...]
    def allows(self, url: str) -> bool: ...
```

`allows` parses with `urllib.parse.urlsplit` and returns true only if all of these hold: the scheme is `https`; there is no userinfo; the port is None or 443; the host, lowercased with a trailing dot removed and converted to its ASCII (IDNA) form, equals an entry of `allowed_hosts` exactly (never `endswith`, never `in`); and the path, after one percent-decode and removal of `.` and `..` segments, contains no encoded slash or backslash and starts with a prefix at a segment boundary (prefix `/docs/` matches `/docs` and `/docs/x`, not `/docsx`). The query and fragment never count. The tests for SRC-23 cover: `https://keycloak.org.evil.example/docs/`, `https://evil.example/?next=www.keycloak.org/docs/`, `https://www.keycloak.org@evil.example/docs/`, `https://www.keycloak.org/docs/../admin`, `https://www.keycloak.org/%2e%2e/admin`, `https://www.keycloak.org/docsx/`, an `http` URL, and a redirect to a path outside the prefixes.

If the HTTP client followed a redirect, the adapter checks `TextResponse.url` against the allowlist and raises `HttpError(BLOCKED_BY_POLICY)` for a final URL outside it, discarding the body. The host policy in the HTTP client already refuses another host.

`sources/robots.py`:

```python
class RobotsCache:
    def __init__(self, http: HttpPort, clock: Clock, source: str, user_agent: str = "research-mcp", ttl_s: int = 86400): ...
    async def allowed(self, url: str) -> bool: ...
```

`allowed` fetches `https://<host>/robots.txt` once per host through `ctx.http.get_text(..., source=<instance id>)` (so it passes host policy and telemetry; the host is in `allowed_hosts` and so in `spec.hosts`), keeps the parsed rules in memory for `ttl_s` by the injected `Clock`, and answers with `urllib.robotparser.RobotFileParser.parse(lines)` and `can_fetch`. No file is written. A 404 or other 4xx for `robots.txt` means everything is allowed; a 5xx, a timeout or a body that is too large means everything is disallowed until the next refresh `[assumption: conservative]`. A disallowed URL is not fetched and the call raises `HttpError(BLOCKED_BY_POLICY, detail="robots")`. The same two helpers serve the M2 crawl job; crawl jobs and local search over crawled pages land in M2 (SPEC v5 section 14; owner decision, 2026-10-22), so in M1 `docs_site` serves `get`, the allowlist and `robots.txt` only.

### 5.12 DSpace instances

One adapter, `sources/dspace.py`, serves every DSpace repository. `INSTANCE_MODEL` has `base_url` (https, no credentials, query or fragment) and `title`; `instance_spec` sets `hosts` to the base URL's host, `id_schemes` to `handle` and `doi`, and the group to `repositories`. The DSpace 7 REST API shapes (`discover/search/objects`, `core/items/{uuid}`, bitstreams for `fulltext_candidates`) are fixed by the fixtures `[inferred]`. `probe` calls the REST root and returns the reported version in `ProbeResult.api_version` (for example the value of `dspaceVersion`), which the health service stores as `api_version_seen`; every record also carries it in `extra["dspace_version"]` (SRC-21; SRC-FR-4). A DSpace 8 repository is the same adapter with a different recorded version.

### 5.13 Code divergences the implementers must fix

The code in `src/research_mcp` today differs from this design in these places. They are listed so the owning unit fixes them; none is an owner decision.

| Where | Today | Required |
| --- | --- | --- |
| `core/envelope.py` `SourceStatus.state` | Lists `skipped_budget`, lacks `budget_exhausted` and `not_needed` | The literal of LLD-platform v2 2.1 (platform owns the file) |
| `core/models.py` | No `site_set`, `site_domains`, `SearchPage.truncated` or `ProbeResult.api_version` | 3.1 |
| `settings.py` `_site_sets()` | Site sets are a code default; a `site_sets` table in the config replaces the whole default | Load `defaults.toml` as the lowest layer and merge by key (3.2); the 26 domains are already correct |
| `settings.py` | `SourceSettings` has no `INSTANCE_MODEL` validation | Done in the registry (5.2) |
| `packaging/` | No `defaults.toml` | 3.3 |
| `sources/` | Empty | 5.1 |
| `tests/sources/` | Does not exist | 5.3 |
| `source_health` column | SPEC-v2 5.5 says `quota_used`; the schema has `calls_today` | Use `calls_today` (3.5); this LLD never says `quota_used` for the web call count |
| `SourceAdapter` protocol | No `search_authors` or `updates` | Add both (2.1) |
| `doi_resolver` helper spec | Does not exist | A non-searching helper `SourceSpec` for `doi.org` with its own rate limit, used by `cite` (LLD-search v2 5.9; owner decision, 2026-10-22). It has no search capability, sits outside the 45-source inventory and the `tools/gen_inventory.py` count, and is listed by the registry only as a helper `[assumption: group `reference`, hidden from `list_sources`]` |

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

- **Adapters never retry or sleep** (SRC-FR-3). The shared HTTP client does both, from the spec's policy (ADR 0006). The retry rules are [LLD-platform v2](LLD-platform-v2.md) 6.1 (PLAT-35):
  - Up to 3 attempts on 429, 500, 502, 503 and 504, and on connection errors. If every attempt gets a 429, the call fails with `rate_limited` and the last `retry_after_ms`.
  - The delay is `Retry-After` when present; a delay over 60 s is not waited for (the call fails with `rate_limited` and `retry_after_ms`). Without it, exponential from a 0.5 s base with full jitter. Other 4xx responses are not retried. All waiting goes through the injected `Sleeper`.
  - Responses are streamed; passing `max_bytes` (default from the policy) aborts the call with `too_large`.
- **Error classifier.** The client raises `HttpError(code, status, retry_after_ms, detail)`, defined in `core/errors.py`. Before the generic mapping, a non-2xx response is passed to `policy.error_classifier` when the source declares one (for example OpenAlex, 5.1). The message text is generic; details go to the log through the redactor (SEC-10).
- **Error codes** are the contract of [envelope and error codes v1](../contracts/envelope-and-errors-v1.md); the sources add none. `SourceStatus.state` is, as in LLD-platform v2 2.1:

```python
class SourceStatus(BaseModel):          # core/envelope.py
    source: str
    state: Literal["ok","empty","timeout","rate_limited","error","unconfigured",
                   "disabled","skipped_unhealthy","budget_exhausted","not_needed"]
    count: int = 0; latency_ms: int | None = None; retry_after_ms: int | None = None
    error_code: ErrorCode | None = None
```

  `skipped_budget` is gone; `down` is a health state that appears in a status as `skipped_unhealthy`; `deprecated(days)` is a badge, not a status (resolved from SRCH-FR-27 and LLD-platform v2 2.1; was a v1 question).
- **Adapter error behavior** is fixed by conformance checks 3 to 6 (5.3) and `translate_errors`. An empty result is an empty page, not an error. A source that is switched off or unconfigured is skipped in the registry (5.2), so an adapter never raises `disabled` or `unconfigured` itself; the registry returns those as statuses with the fix.
- **Skips, not failures.** A disabled source is never called and is skipped with state `disabled`; a source with a missing required credential, an unset contact for `needs_contact`, or a missing extra is `unconfigured` with the fix; a web source at its cap is `budget_exhausted` (SRC-FR-5 to SRC-FR-7, SRC-FR-20, SRC-FR-24; 5.2, 5.9).
- **Settings errors.** A placeholder `contact.email` is a settings validation error and the daemon does not start (LLD-platform v2 6.2; SRC-FR-24; owner decision, 2026-10-22). An invalid instance entry makes only that instance `unconfigured`, and an invalid `SourceSpec` in a built-in module fails daemon construction and CI (SRC-1).
- **Unknown site set.** An unknown or empty set name is `invalid_argument` before any call (SRC-FR-22; SRC-31).
- **Idempotency.** Adapters are translators with no writes of their own (SRC-FR-3). `search`, `get` and `probe` are reads and safe to repeat. The live check writes only to `tests/sources/<id>/fixtures/_review/` and never opens committed fixtures for writing (5.4). Registry construction is deterministic and has no side effects at import (PLAT-3).

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

No feature-flag PRD exists, so this table follows the platform LLD's list of optional behavior ([LLD-platform v2](LLD-platform-v2.md) 7.2). Each flag is safe to switch off: no data is lost, the MCP tool list does not change and the daemon still starts.

| Flag | Default | Safe to switch off? |
| --- | --- | --- |
| `sources.<id>.enabled` | Spec default (`enabled_by_default`; `False` for the four `web` sources and their instances, ADS and Lens; PRD-sources v5 1.3). A configured web source also needs `enabled = true` (owner decision, 2026-10-22) | Yes: a disabled source is never called, is listed `disabled` and is skipped by federation; no code change (SRC-FR-5). This is the switch for every instance too (`dspace_*`, `docs_site_*`, `vertex_*`) |
| `sources.<id>.budget_cap` | None; `100` for `web` sources | Yes: removing the cap on a free source changes nothing; the cap on a web source is a spend control, so it is not removed lightly (SRC-FR-20). A cap of `0` blocks the source |
| `web.strategy` | `"fallback"` | Yes: `all` is the other value; the `web` group stays off unless a source is enabled and named |
| `web.order` | `["vertex_*", "brave_search", "serpapi", "google_pse"]` | Yes: an order is data; an unlisted web source is not part of a `fallback` chain |
| `site_sets.<name>` | `v1_docs` | Yes: a missing or empty set makes `site_set=<name>` an `invalid_argument`; the `search` call without `site_set` is unchanged |
| `--live` on `research-mcp sources check` | Off (opt-in) | Yes: default test runs make no network calls; `live` tests are deselected by default (NFR-9; test plan v4 1.1) |
| `--refresh-fixtures` on the live check | Off | Yes: without it no fixtures are written (5.4) |
| Optional extra `gcp` (`google-auth`) | Not installed | Yes: without it `vertex_search` shows `unconfigured` with the install command (SRC-FR-7; PLAT-13; ADR 0012) |

**Answer to the v1 question about flags.** The `web` fallback and the `site_set` argument need no flag of their own: per-source enablement and `web.strategy` already switch the web group off, and `site_set` is an optional per-call argument that changes no stored state (resolved from SRC-FR-19, SRC-FR-21 and the platform LLD's rule that a flag is a setting that switches behavior off).

Other settings that shape behavior are in 3.2: `web.strategy`, `web.order`, `site_sets.<name>`, `federation.default_groups` and `contact.email`. A placeholder or unset `contact.email` is not a flag (6). Per-source timeout, rate and page-size defaults live in the `SourceSpec`, not in settings (PRD-sources v5 2.5: design defaults stay in the LLD).

## 8. Observability

> **Owner:** A · **Persona:** `sre`

Reviewed by the `sre` persona against SPEC-v5 12, PRD-v8 NFRs and the sources PRD, and consistent with LLD-platform v2 8; not approved. It sets no threshold of its own, because none traces to an NFR.

- **Call records.** Every HTTP attempt produces a `CallRecord` for the `CallSink`; in the daemon the sink is `StateStore.record_call`, flushed every second (PLAT-39). The Google sign-in refresh is recorded as a `CallRecord` with `source="google_signin"`. A call that `robots.py` makes for `robots.txt` is recorded under the docs-site instance id.
- **Probes.** Each spec declares `probe: ProbeSpec(cadence_s, cost, description)` (default `ProbeSpec(3600, "free", "")`); `probe()` returns `ProbeResult` with `ok`, `latency_ms`, `shape_ok`, `detail_code`, `quota_remaining`, `credential_expires_at` and, new, `api_version` (3.1). `HealthService` schedules each source's probe at `spec.probe.cadence_s` with 0 to 10% jitter, and `evaluate(source)` uses `spec.shutdown_on` (and `SourceSpec.deprecated_days`) among its inputs.
- **Web-source probes and quota** are in the 5.7 table: Vertex every 6 h at no query cost; SerpAPI `account.json` every 6 h; Brave and Programmable Search one query every 24 h; Brave rate-limit headers parsed passively on every call. The daily count is `calls_today` in `source_health` (3.5).
- **Logs.** The registry logs, at `INFO` through the redactor, each state it computes when it changes (source id, state, reason code; never a Keychain value or a URL with a query; NFR-4). Invalid instance settings log the field name only. Records carry the platform fields, including `source` and `correlation_id` (PLAT-FR-41). The registry adds no new metric or event prefix beyond the `CallRecord` fields.
- **Inventory.** `docs/generated/sources.md` is generated from the registry; CI fails when it is stale (5.10; NFR-10).

No alert thresholds for this component trace to an NFR; thresholds belong to the health component (LLD-health 5), which owns probe failure counts and error-rate rules (resolved from NFR-12 and LLD-health 5; was a v1 question).

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

Drafted by the component designer. Reviewed by `test-architect` at Gate 3 (2026-10-23). Every criterion maps to a design element and a planned test. No test in `tests/` cites a SRC criterion yet, so every row is `planned`. Test files for M0 follow the scope lists of the [M0 plan](../build/M0-plan-v1.md); M1 files follow the `tests/sources/<id>/test_<id>.py` pattern and `tests/unit/sources/`. Where a file is a choice the plan does not fix, it is tagged `[inferred]`. Each test names its criterion first in its docstring (`"""@spec SRC-3: ..."""`; test plan v4 1).

| Criterion | Design element | Planned tests | Level | Status |
| --- | --- | --- | --- | --- |
| SRC-1 | `SourceSpec.__post_init__` (2.1) | `tests/unit/sources/test_registry.py::test_spec_rejects_missing_field_out_of_bounds_rate_and_auth_without_origins` (one parametrized case per bound in the 2.1 table; file `[inferred]`; M0-09) | unit | planned |
| SRC-2 | Discovery and instances (2.3, 5.2) | `tests/unit/sources/test_registry.py::test_discovers_builtin_and_builds_two_instances_from_settings` (M0-09) | unit | planned |
| SRC-3 | Selection row 1 (5.2) | `tests/unit/sources/test_registry.py::test_disabled_source_is_skipped_and_records_no_request` (M0-09) | unit | planned |
| SRC-4 | Selection rows 3 and 4 (5.2) | `tests/unit/sources/test_registry.py::test_missing_credential_or_contact_is_unconfigured_with_exact_fix` (M0-09) | unit | planned |
| SRC-5 | Selection row 2 (5.2) | `tests/unit/sources/test_registry.py::test_missing_extra_is_unconfigured_with_install_command` (M0-09) | unit | planned |
| SRC-6 | Conformance suite (5.3) | `tests/sources/test_conformance.py::test_conformance_passes_for_fake_adapter` over the fake adapter from `research_mcp.testing.adapters` (M0-09) | unit | planned |
| SRC-7 | Import check (5.3) | `tests/unit/sources/test_adapter_imports.py::test_forbidden_import_or_call_in_adapter_module_fails` (positive case on a temp module per forbidden import and call; M0-09) | unit | planned |
| SRC-8 | `SourceView` (5.2) | `tests/contract/test_tools_discovery.py::test_list_sources_and_resource_list_every_source_with_state_and_fix` (M0-14; file `[inferred]`) | contract | planned |
| SRC-10 | arXiv spec (5.1) | `tests/sources/arxiv/test_arxiv.py::test_arxiv_https_version_mapping_rate_and_concurrency` and `tests/sources/test_conformance.py::test_conformance_passes[arxiv]` (M0-10) | integration | planned |
| SRC-11 | Crossref spec (5.1) | `tests/sources/crossref/test_crossref.py::test_crossref_mailto_doi_date_mapping_and_updates_capability` and `tests/sources/test_conformance.py::test_conformance_passes[crossref]` (M0-11) | integration | planned |
| SRC-12 | OpenAlex spec and classifier (5.1) | `tests/sources/openalex/test_openalex.py::test_openalex_key_placement_page_size_and_budget_429_classified` and `tests/sources/test_conformance.py::test_conformance_passes[openalex]` (M0-12) | integration | planned |
| SRC-13 | Inventory (5.10) | `tests/unit/test_cli.py::test_gen_inventory_check_fails_on_stale_inventory` (M0-16; file `[inferred]`) | unit | planned |
| SRC-20 | Conformance for every adapter (5.3) | `tests/sources/test_conformance.py::test_conformance_passes[<id>]` (one case per adapter, with `tests/sources/<id>/fixtures/`) and `tests/unit/sources/test_catalog.py::test_45_catalog_ids_registered_each_with_seven_fixtures` (M1) | integration | planned |
| SRC-21 | DSpace instances (5.12) | `tests/sources/dspace/test_dspace.py::test_four_instances_record_api_version_and_dspace_version` (M1) | integration | planned |
| SRC-22 | Upstream MCP (5.6) | `tests/sources/aws_knowledge/test_aws_knowledge.py::test_calls_go_through_upstream_port_with_policy_and_telemetry` and `tests/sources/ms_learn/test_ms_learn.py::test_calls_go_through_upstream_port_with_policy_and_telemetry` against the MCP server fake (M1) | integration | planned |
| SRC-23 | Allowlist and robots (5.11) | `tests/sources/docs_site/test_docs_site.py::test_allowlist_substring_traversal_and_robots_disallow_refused` (M1) | integration | planned |
| SRC-24 | `deprecated_days` (2.1, 5.2) | `tests/unit/sources/test_registry.py::test_deprecated_days_counts_down_to_shutdown_on` (`FakeClock`; M1) | unit | planned |
| SRC-25 | Live check (5.4) | `tests/live/test_sources_live.py::test_live_check_writes_only_under_review` (opt-in `live` mark) and non-live `tests/unit/sources/test_live_check.py::test_path_outside_review_is_refused` (M1) | live | planned |
| SRC-26 | Defaults and v1 map (3.3) | `tests/unit/sources/test_v1_map.py::test_v1_endpoint_map_with_aws_and_learn_substitution` and `tests/unit/sources/test_v1_map.py::test_defaults_hold_26_domains_and_six_docs_site_instances` (M1) | unit | planned |
| SRC-27 | Merge rule (3.2) | `tests/unit/test_settings.py::test_site_sets_override_by_name_empty_list_removes_and_invalid_name_fails` (M1; file `[inferred]`) | unit | planned |
| SRC-28 | Selection (5.2, 5.7) | `tests/services/test_web_group.py::test_web_sources_disabled_until_enabled_and_configured`, `tests/services/test_web_group.py::test_web_removed_from_auto_even_when_in_default_groups` and `tests/services/test_web_group.py::test_web_selected_by_group_name_or_source_id` (M1) | integration | planned |
| SRC-29 | Cap (5.9) | `tests/services/test_web_group.py::test_daily_cap_gives_budget_exhausted_until_local_midnight_and_federation_skips` (`FakeClock`; M1) | integration | planned |
| SRC-30 | Chain (5.9) | `tests/services/test_federation_web.py::test_fallback_chain_one_paid_query_per_page`, `tests/services/test_federation_web.py::test_all_strategy_fans_out_to_every_web_source` and `tests/services/test_federation_web.py::test_non_web_sources_run_in_parallel_inside_deadline` (M1; file `[inferred]`) | integration | planned |
| SRC-31 | Site sets (5.8) | `tests/unit/sources/test_sitequery.py::test_brave_batches_at_most_3_of_380_chars_query_domains_first`, `tests/unit/sources/test_sitequery.py::test_serpapi_and_pse_single_query_with_truncated`, `tests/unit/sources/test_sitequery.py::test_vertex_filters_results_by_host` and `tests/unit/sources/test_sitequery.py::test_unknown_site_set_is_invalid_argument_with_no_call` (M1) | unit | planned |
| SRC-32 | Vertex (4, 5.7) | `tests/sources/vertex_search/test_vertex_search.py::test_refresh_off_loop_token_only_to_discoveryengine_with_project_header_and_call_record` and `tests/unit/sources/test_vertex_static.py::test_no_src_module_opens_the_credential_file` (M1) | integration | planned |
| SRC-33 | Brave, SerpAPI, PSE (5.7) | `tests/sources/brave_search/test_brave_search.py::test_brave_headers`, `tests/sources/google_pse/test_google_pse.py::test_pse_reports_deprecated_days`, `tests/sources/serpapi/test_serpapi.py::test_serpapi_key_never_in_logs_errors_call_records_or_tool_results` (M1) | integration | planned |

Owner checks that touch this component: OC-11 (a new free source added in one work unit) and OC-14 (a live web-group search with `v1_docs` through the Vertex engine) are not tests (test plan v4 section 3). Verified elsewhere (PRD-sources v5 2.4): PLAT-6 for `SourcePolicy` and `AuthSpec`, UI-10 for the disable control, PLAT-13 for the `gcp` extra, PLAT-11 for placeholder rejection, SEC-8 for SRC-INV-6.

**Conformance and fixtures.** Network is blocked in all non-live tests (`tests/conftest.py` socket guard); fixtures go through `httpx.MockTransport`; sleeping uses the fake `Sleeper`; secrets are `FakeProvider` values registered with the redactor.

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| Every source is one module with a `SourceSpec` and an adapter that only translates; the shared HTTP client retries, sleeps and attaches secrets | Breadth is the product (D1), yet v1 had no source abstraction (ADR 0006) | v1's per-source tools (DSpace as eight copy-paste tools) (ADR 0006) |
| Policy types live in `core/specs.py` | So the HTTP layer does not depend on the source layer (ADR 0006) | Not recorded |
| Discovery by `pkgutil.iter_modules`; no central list | Adding a source edits no shared file (SRC-FR-26) | A central list (rejected by OUT-3) |
| Adapters are in-tree only; entry-point discovery of third-party adapters is dropped | It would run installed code in the daemon that holds the secrets cache and is in no approved requirement (owner decision, 2026-10-22) | Keep it behind a `sources.entry_points` setting; keep it on (both rejected) |
| Credential presence, health, the daily call count and extra detection are injected into the registry as callables | Nothing under `sources/` imports the secrets, health or store modules; tests need no Keychain (SPEC-v2 5.1) | The registry reading `StateStore` directly |
| One `dspace` adapter with four configured instances; instance kinds define `INSTANCE_MODEL` and `instance_spec` | Instances come from configuration alone (SRC-FR-4; ADR 0006); a typo in an instance fails that instance only | Separate tools per repository, as in v1 (REVIEW-v1 3, finding 6) |
| The AWS and Microsoft Learn MCP servers run through v2 as upstream MCP sources over `McpUpstreamPort` | They appear on the source board and in federated search; rate limits, host policy, telemetry and redaction apply (O6, closed by the owner; SRC-FR-10) | Add the MCP servers to clients separately (O6) |
| Web search is the optional, capped `web` group with a `fallback` strategy by default; `select` removes `web` from auto even if listed in `default_groups` | Spend stays deliberate (ADR 0012; SRC-INV-4) | Trusting settings alone to keep `web` out of auto |
| The daily cap is enforced by the registry from `calls_today`, not by the HTTP client | The platform design has no daily-quota enforcement; the chain runs one web source at a time (LLD-platform v2 5.3) `[inferred]` | A counter in the HTTP client, which needs a platform change |
| `vertex_search` uses the owner's Google sign-in through `google-auth`, not a Keychain item | `gcloud` owns the credential file; v2 keeps the token in memory only (ADR 0012) | Not recorded |
| Docs-site filters match the parsed host and path; `robots.txt` is fetched through `HttpPort` and cached in memory | v1 matched URL substrings (SRC-FR-15); adapters may not do their own I/O or write files (SRC-FR-3) | A cache on disk (forbidden for adapters) |
| v1's docs-domain list and crawl projects ship as data in `defaults.toml`, merged by key under the owner's config | Topic coverage is configuration, not code (ADR 0012; SRC-27) | Code defaults, as `settings.py` has them today |
| `SourceSpec` bounds are validated in `__post_init__` with the 2.1 table | SRC-1 needs bounds; no source gives any (`[assumption]`) | A separate `validate_spec` function |
| `shutdown_on` is the status note | SPEC-v5 4 and SRC-FR-14 define no other note | A free-text `note` field |
| Seven fixtures per adapter; 45 sources at the M1 exit; `tools/gen_inventory.py` is the only inventory generator; a new source's Keychain name lives in its `SourceSpec` | Owner decisions, 2026-10-22 (SRC-FR-8, SRC-OUT-1, SRC-FR-25, SRC-FR-26) | Six fixtures; 38 sources; a `sources --markdown` command; a SPEC edit per credential (all superseded) |
| A placeholder `contact.email` is a settings error and the daemon does not start; an unset address leaves only `needs_contact` sources `unconfigured` | Owner decision, 2026-10-22 (SRC-FR-24; PLAT-11) | Holding back only the affected sources (SRC-FR-11, superseded) |
| An adapter-contract file is added under `docs/contracts/` | The contract is consumed by many work units and the conformance suite; the owner approves it at Gate 3 | Leave the Python in this LLD as the only form |
| Observability thresholds stay with the health component | No NFR sets one for sources (NFR-12; LLD-health 5) | Thresholds in this LLD |

**Resolved questions of v1** (each deleted from section 11; source in brackets):

| v1 question | Answer |
| --- | --- |
| Fixture count: six or seven | Seven (PRD-sources v5 1.7, SRC-FR-8; owner decision, 2026-10-22) |
| Source count: 38 or 45 | 45 at the M1 exit (PRD-v7 OUT-1; SPEC 4; owner decision, 2026-10-22). Test plan v3 section 8 already follows PRD-v7 |
| Inventory generator: CLI command or script | `tools/gen_inventory.py` and its `--check` only; no `sources --markdown` (SRC-FR-25; owner decision, 2026-10-22) |
| Which values belong in `SourceStatus.state` | The literal of 6 and LLD-platform v2 2.1; `down` is reported as `skipped_unhealthy`; `deprecated(days)` is a badge (SRCH-FR-27) |
| `SourceSpec` bounds and where validated | 2.1 table, in `SourceSpec.__post_init__` `[assumption]` (SRC-1) |
| Placeholder contact: settings error or hold back sources | Settings validation error; the daemon does not start; unset only affects `needs_contact` sources (SRC-FR-24; PLAT-11; owner decision, 2026-10-22) |
| Status note | `shutdown_on` and `docs_url` are enough (2.1) |
| `robots.txt` | Fetched through `HttpPort`, cached in memory by `RobotsCache` (5.11) `[assumption]` |
| New-source checklist step 5 versus OUT-3 | Step 5 is superseded; the Keychain name lives in the `SourceSpec` (SRC-FR-26; owner decision, 2026-10-22; 5.5) |
| Contracts | Yes: [source adapter v1](../contracts/source-adapter-v1.md), for the owner to approve at Gate 3 |
| Owning LLD for the SPEC-v2 0.6 row M0-03 | `Budget.fit` is carried by LLD-platform v2 5.6; this LLD keeps the row because `FederatedResult` is defined here (SPEC-v5 19, 3.1) |
| Observability thresholds | Belong to the health component (8) |
| Web-source enablement | A configured web source also needs `enabled = true`; presence alone never enables a call (owner decision, 2026-10-22; 5.7) |
| Default DSpace URLs and `docs_site_syncope` seeds | Read from the v1 source by the implementer and confirmed by the owner at review; values not in this LLD (owner decision, 2026-10-22; 3.3) |
| Third-party adapters by entry point | Dropped; adapters are in-tree only (owner decision, 2026-10-22; 2.3) |
| `docs_site` in M1 | `get`, the allowlist and `robots.txt` only; `search` and `crawl` in M2 (owner decision, 2026-10-22; 5.11) |

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

All four questions are answered (owner decisions, 2026-10-22; section 10) and no question is open. Divergences for other documents are listed in 5.13. Dependencies on sibling LLDs: LLD-platform v2 (no `sources.entry_points` setting is added; the `cite` extra and the four search settings are listed in LLD-search v2 12), LLD-security v2 (no change; adapters in-tree only), LLD-cache-v2 (no change) and LLD-health v2 (`calls_today` stays the web count; no rename).

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
