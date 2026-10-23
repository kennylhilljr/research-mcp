---
title: "Sources low level design"
type: lld
version: 1
status: draft
owner: "Kenny Hill"
prefix: SRC
component: sources
parent: docs/spec/SPEC-v3.md
artifact_type: low-level-design
scope_level: L3
scope_name: "research-mcp"
derives_from: docs-archive/spec/SPEC-v2.md
date: 2026-10-22
---

# LLD: Sources (v1)

This LLD carries the sources design out of [SPEC v2](../../docs-archive/spec/SPEC-v2.md) sections 4 (specs, models and the source contract) and 5.1 to 5.5 (registry, fixtures and conformance, live check, new-source checklist, site sets, docs sites and web search), with the shape from [HLD v3](../../docs-archive/design/HLD-v3.md) section 4. Names are unchanged from SPEC-v2. Requirements and criteria are in [PRD-sources v4](../prd/components/PRD-sources-v4.md). Code paths: `src/research_mcp/sources` and `tests/sources` (`sdd.config.json`).

## 1. Scope and requirements

> **Owner:** A · **Persona:** `component-designer`

Governing section: SPEC-v3 section 4.

| Requirement | Criteria | SPEC section |
| --- | --- | --- |
| SRC-FR-1 | SRC-1 | SPEC-v3 section 4 |
| SRC-FR-2 | SRC-6 | SPEC-v3 section 4 |
| SRC-FR-3 | SRC-7 | SPEC-v3 section 4 |
| SRC-FR-4 | SRC-2, SRC-21 | SPEC-v3 section 4 |
| SRC-FR-5 | SRC-3, SRC-8 | SPEC-v3 section 4 |
| SRC-FR-6 | SRC-4, SRC-8 | SPEC-v3 section 4 |
| SRC-FR-7 | SRC-5 | SPEC-v3 section 4 |
| SRC-FR-8 | SRC-6, SRC-10, SRC-11, SRC-12, SRC-20 | SPEC-v3 section 4 |
| SRC-FR-9 | SRC-6, SRC-10, SRC-11, SRC-12, SRC-20 | SPEC-v3 section 4 |
| SRC-FR-10 | SRC-22 | SPEC-v3 section 4 |
| SRC-FR-11 | SRC-4, SRC-11 | SPEC-v3 section 4 |
| SRC-FR-12 | SRC-25 | SPEC-v3 section 4 |
| SRC-FR-13 | SRC-13 | SPEC-v3 section 4 |
| SRC-FR-14 | SRC-24 | SPEC-v3 section 4 |
| SRC-FR-15 | SRC-23 | SPEC-v3 section 4 |
| SRC-FR-16 | SRC-20 | SPEC-v3 section 4 |
| SRC-FR-17 | SRC-26 | SPEC-v3 section 4 |
| SRC-FR-18 | SRC-26, SRC-27 | SPEC-v3 section 4 |
| SRC-FR-19 | SRC-28, SRC-33 | SPEC-v3 section 4 |
| SRC-FR-20 | SRC-29 | SPEC-v3 section 4 |
| SRC-FR-21 | SRC-30 | SPEC-v3 section 4 |
| SRC-FR-22 | SRC-31 | SPEC-v3 section 4 |
| SRC-FR-23 | SRC-32 | SPEC-v3 section 4 |
| NFR-8 | SRC-10 | SPEC-v3 section 4 |
| NFR-10 | SRC-13 | SPEC-v3 section 4 |
| HLTH-FR-12 | SRC-29 | SPEC-v3 section 4 |
| HLTH-FR-42 | SRC-8 | SPEC-v3 section 4 |
| PLAT-FR-10 | SRC-32 | SPEC-v3 section 4 |
| PLAT-FR-12 | SRC-33 | SPEC-v3 section 4 |
| PLAT-FR-13 | SRC-33 | SPEC-v3 section 4 |

The last seven rows are requirements owned by the parent PRD or by other components that criteria of this component also verify.

## 2. Contracts

> **Owner:** C · **Persona:** `component-designer` drafts; the contract owner approves public and cross-team contracts

No machine-readable contract for this component exists in `docs/contracts/` yet (see 11).

### 2.1 Source contract (`sources/base.py`)

From SPEC-v2 4:

```python
class Capability(StrEnum): SEARCH="search"; GET="get"; FULLTEXT="fulltext"; CITATIONS="citations"
                           AUTHORS="authors"; UPDATES="updates"; CRAWL="crawl"

@dataclass(frozen=True)
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
    shutdown_on: date | None = None
    docs_url: str = ""
    instance_of: str | None = None           # "dspace" for dspace_mit
    error_classifier: ErrorClassifier | None = None
    def policy(self) -> SourcePolicy: ...

class McpUpstreamPort(Protocol):              # implemented in M1 by platform/mcp_client.py
    async def call_tool(self, server: str, tool: str, arguments: Mapping[str, JsonValue], *, source: str) -> JsonValue: ...

class SourceContext:                         # given to each adapter instance
    http: HttpPort; mcp: McpUpstreamPort | None; settings: SourceSettings; clock: Clock

class SourceAdapter(Protocol):
    spec: SourceSpec
    async def search(self, req: SearchRequest) -> SearchPage: ...
    async def get(self, ident: Identifier) -> WorkRecord | None: ...
    async def fulltext_candidates(self, work: WorkRecord) -> list[FulltextCandidate]: ...
    async def citations(self, ident: Identifier, direction: Literal["citing","cited"],
                        cursor: str | None, limit: int) -> CitationPage: ...
    async def probe(self) -> ProbeResult: ...
```

Adapters parse XML with `defusedxml`. They may import `urllib.parse`, but not `urllib.request`, `http.client`, `socket`, `httpx`, `requests`, `time.sleep`, `asyncio.sleep`, or `research_mcp.platform.secrets` (SPEC-v2 4). Unsupported capabilities are declared in the spec, not stubbed (SRC-FR-2).

### 2.2 Policy types (`core/specs.py`)

`core/specs.py` holds the pure policy types. They are shared by the HTTP layer (M0-07) and the source layer (M0-09) (SPEC-v2 4):

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

### 2.3 Discovery contract

- **Built-in adapters** are discovered by scanning the `research_mcp.sources` package with `pkgutil.iter_modules`. Any module that defines a module-level `SPEC: SourceSpec` and `ADAPTER: type[SourceAdapter]` is registered. No central list is edited when a source is added.
- **Third-party adapters** can register through the entry point group `research_mcp.sources`.

(SPEC-v2 5.1)

### 2.4 Surfaces that expose the registry

These belong to other components and are listed here because the registry feeds them.

| Surface | Contract | Owner (SPEC-v2) |
| --- | --- | --- |
| `list_sources` tool | `group: str = None, state: str = None`; service registry + health; annotations RO; M0 | 7.2, unit M0-14 |
| `research://sources` resource | M0 resource | 7.3, unit M0-14 |
| `search` tool `site_set` argument | `site_set: str = None (M1; a configured site set)` | 7.2 |
| `research-mcp sources check --live [--id X] [--refresh-fixtures]` | Live check (5.4 below) | 5.3 |
| `tools/gen_inventory.py` and `gen_inventory.py --check` | Writes `docs/generated/sources.md` from the registered adapters; the check is a CI gate | 12.1, 12.3 (M0-16) |

## 3. Data model, schema and migrations

> **Owner:** C · **Persona:** `component-designer` drafts; the owner approves anything persisted

### 3.1 Shared models (`core/models.py`)

`core/models.py` holds the shared data types (SPEC-v2 4):

```python
JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
class Clock(Protocol): def now(self) -> datetime: ...           # UTC
class Sleeper(Protocol): async def sleep(self, seconds: float) -> None: ...
class AuthUse(StrEnum): SPEC="spec"; NONE="none"

from research_mcp.core.ids import Identifier                    # frozen dataclass, section 6 (re-exported)
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
class SearchRequest(BaseModel): query: str; filters: SearchFilters = SearchFilters(); limit: int = 10
                                cursor: str | None = None
class SearchPage(BaseModel): records: list[WorkRecord]; total: int | None = None; next_cursor: str | None = None
class FulltextCandidate(BaseModel): location: OaLocation; priority: int
class CitationPage(BaseModel): ids: list[Identifier]; records: list[WorkRecord] = []; next_cursor: str | None = None
class ProbeResult(BaseModel): ok: bool; latency_ms: int; shape_ok: bool; detail_code: str | None = None
                              quota_remaining: str | None = None; credential_expires_at: datetime | None = None
class Conflict(BaseModel): field: str; values: dict[str, JsonValue]       # source -> value
class Work(BaseModel):
    work_id: str | None = None; ids: list[Identifier]; title: str; authors: list[Author]
    year: int | None; venue: str | None; work_type: str; abstract: str | None
    oa_locations: list[OaLocation]; found_in: list[str]; fuzzy: bool = False
    conflicts: list[Conflict] = []; integrity_status: str = "unknown"; cache_state: str = "none"
class FederatedResult(BaseModel): works: list[Work]; statuses: list[SourceStatus]; next_cursor: str | None
class TextResponse(BaseModel): url: str; status: int; content_type: str; text: str
class DownloadedFile(BaseModel): sha256: str; size: int; media_type: str; storage_path: str; final_url: str
                                 http_status: int; etag: str | None; last_modified: str | None
class CallRecord(BaseModel): ts: datetime; source: str; op: str; status: int | None; error_code: str | None
                             latency_ms: int; bytes: int; rl_remaining: str | None; rl_reset: str | None
                             cred_expires_at: str | None; correlation_id: str | None; attempt: int
```

Every adapter maps upstream records to `WorkRecord` with `Provenance` (source id, upstream id, adapter version, retrieval time) and normalized identifiers (SRC-FR-9).

Clarification carried from SPEC-v2 0.6 (it cites section 4; `FederatedResult` is defined here):

| Unit | Section | Requirement |
|---|---|---|
| M0-03 | 3.7, 4; AT-PLAT-31, FR-SRCH-04 | `Budget.fit` MUST keep `FederatedResult.statuses` (one status per source) and MUST fail explicitly when mandatory metadata cannot fit. Its prefix search MUST distinguish "does not validate" from "too large". |

(SPEC-v2 0.6)

### 3.2 Settings keys read by this component

From SPEC-v2 2 (`settings.Settings`, loaded from `~/.config/research-mcp/config.toml`, then `RESEARCH_MCP_*` environment overrides nested with `__`):

| Key | Default | Notes |
|---|---|---|
| `contact.email` | none | Crossref `mailto`, Unpaywall `email`, user agent. Placeholder domains (`example.com`, `example.org`, `test`, `invalid`) are rejected. If unset, sources with `needs_contact` are `unconfigured`; the daemon still starts. |
| `federation.default_groups` | `["scholarly", "preprints"]` | |
| `sources.<id>.enabled` | spec default | |
| `sources.<id>.budget_cap` | none (`100` for `web` sources) | Daily call cap for metered sources (UI Quota page); resets at local midnight |
| `sources.vertex_<name>` | none | `{ instance_of = "vertex_search", project = "...", location = "global", engine_id = "...", title = "..." }`; one per Vertex AI Search engine (5.5) |
| `sources.google_pse.engine_id` | none | Programmable Search engine id (v1 `GOOGLE_PSE_CX`); not a secret |
| `web.strategy` | `"fallback"` | `fallback` or `all` (5.5) |
| `web.order` | `["vertex_*", "brave_search", "serpapi", "google_pse"]` | `vertex_*` expands to the configured Vertex instances in name order |
| `site_sets.<name>` | `v1_docs` (5.5) | A list of domains; names match `[a-z0-9_]{1,40}` |
| `sources.<id>.<field>` | per spec | For example `sources.dspace_penn.base_url` |

**Instances** come from settings. For example, `sources.dspace_mit = { instance_of = "dspace", base_url = "https://dspace.mit.edu/server/api", title = "DSpace@MIT" }`. The same form covers `dspace_harvard`, `dspace_cornell` and `dspace_penn`, and the `docs_site_<name>` entries with their `allowed_hosts` and `path_prefixes`. An instance's `hosts` come from its base URL (SPEC-v2 5.1).

### 3.3 Default data (`defaults.toml`)

From SPEC-v2 5.5. `src/research_mcp/packaging/defaults.toml` (package data) holds data the owner can override in `config.toml`. It carries every v1 endpoint forward (SRC-FR-17):

- `site_sets.v1_docs`: v1's docs-domain list, verbatim: `keycloak.org`, `ory.sh`, `supertokens.com`, `authelia.com`, `goauthentik.io`, `zitadel.com`, `logto.io`, `casdoor.org`, `authgear.com`, `kanidm.github.io`, `freeipa.org`, `syncope.apache.org`, `openpolicyagent.org`, `cerbos.dev`, `authzed.com`, `casbin.org`, `permify.co`, `topaz.sh`, `warrant.dev`, `pomerium.com`, `developer.hashicorp.com`, `infisical.com`, `webauthn.guide`, `jwt.io`, `datatracker.ietf.org`, `zanzibar.academy`.
- `docs_site_*` instances for v1's six crawl projects, with the same seeds and filters:

| Instance | Seeds | Follow links | Path prefixes |
|---|---|---|---|
| `docs_site_keycloak` | sitemap `https://www.keycloak.org/sitemap.xml` | sitemap | `/docs/`, `/securing-apps/`, `/guides/` |
| `docs_site_ory` | sitemap `https://www.ory.sh/sitemap.xml` | sitemap | `/docs/` |
| `docs_site_opa` | sitemap `https://www.openpolicyagent.org/sitemap.xml` | sitemap | `/docs/` |
| `docs_site_vault` | `https://developer.hashicorp.com/vault/docs` | yes | `/vault/docs` |
| `docs_site_syncope` | the 4.1 and 4.0 reference guide and getting-started pages | no | (the seed pages only) |
| `docs_site_freeipa` | `https://www.freeipa.org/page/Documentation.html` | yes | `/page/` |

A `docs_site` instance has `allowed_hosts`, `path_prefixes`, and either `sitemap` or `seed_urls` with `follow_links`.

### 3.4 Fixtures on disk

Each source has a fixtures folder, `tests/sources/<id>/fixtures/`, with these fixtures (SPEC-v2 5.2):

| Fixture | Contents |
|---|---|
| `search_ok`, `search_empty`, `get_ok` | Normal responses |
| `err_429` | Status and headers, as JSON |
| `err_5xx` | JSON |
| `malformed` | A broken body |
| `oversize.marker` | A marker only; the test generates the large body |

Body fixtures use the upstream's format: `.json` for JSON APIs, `.xml` for Atom (arXiv).

### 3.5 Persisted state

This component owns no database table. Each call to a web source counts against its cap in `StateStore` (`quota_used` in `source_health`); at the cap the source reports `budget_exhausted(reset=next local midnight)` (SPEC-v2 5.5). `source_health` belongs to the `state.db` schema (SPEC-v2 10.1, health component).

## 4. Authentication and authorization enforcement points

> **Owner:** C · **Persona:** `security-reviewer` drafts; the control owner approves

Drafted from SPEC-v2 text; for the security reviewer and control owner to confirm.

- **Adapters hold no secrets.** Nothing under `sources/` imports `research_mcp.platform.secrets` (2.1). Credential presence and health come into the registry as callables, so nothing under `sources/` imports the secrets or health modules (SPEC-v2 5.1).
- **Host policy.** Every `SourceSpec` lists `hosts`, every host the adapter may call. In the HTTP client, a request whose host is not in `policy.hosts` fails with `blocked_by_policy` (SPEC-v2 3.3). Conformance check 7 verifies every request goes to a host in `spec.hosts` (SPEC-v2 5.2).
- **Credential attachment** (SPEC-v2 3.3):
  - The secret comes from `CredentialResolver`.
  - It is attached only when the request origin is in `policy.auth.origins`.
  - Placement is `header` (name from the spec), `bearer`, or `query` (parameter name from the spec).
  - Query placement is used only where the API offers nothing else, and then the URL is never logged.
- **Keychain items** used by sources (SPEC-v2 3.1): `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `CORE_API_KEY`, `GOOGLE_DEVKNOWLEDGE_API_KEY`, `GITHUB_TOKEN`; `ZENODO_TOKEN`, `NCBI_API_KEY`, `NVD_API_KEY`, `ADS_API_TOKEN`, `LENS_API_TOKEN`, `OPENCITATIONS_TOKEN`; `BRAVE_SEARCH_API_KEY`, `SERPAPI_API_KEY` (M1). `GOOGLE_DEVKNOWLEDGE_API_KEY` is shared by `google_devknowledge` and `google_pse`, as in v1; each source's `origins` limit where it is sent.
- **Google sign-in for `vertex_search`** (SPEC-v2 3.1.1):
  - `vertex_search` does not use a Keychain item. `SecretRef` gains the backend `gcloud_adc` (reference text `gcloud_adc:GOOGLE_SIGNIN`), resolved by `platform/google_adc.py` (`GoogleAdcProvider`).
  - `default_loader` calls `google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])`. Loading and refreshing are blocking, so the daemon calls them through `anyio.to_thread.run_sync`, never on the event loop.
  - The refresh request goes from `google-auth` to `oauth2.googleapis.com` only; the provider records it as a `CallRecord` with `source="google_signin"`.
  - The access token is wrapped in `Secret` (name `GOOGLE_SIGNIN`), held in memory, and revealed only by `platform/http.py` for origins in the Vertex spec (`https://discoveryengine.googleapis.com`), as a bearer token plus `X-Goog-User-Project: <project>`.
  - v2's own code never opens, copies or writes the credential file.
- **Web-source auth** (SPEC-v2 5.5): `brave_search` uses the `X-Subscription-Token` header; `serpapi` uses the `api_key` query parameter (URL never logged); `google_pse` uses the `x-goog-api-key` header.
- **Docs-site allowlist.** v1 matched filters as URL substrings; v2 matches the parsed host against `allowed_hosts` and the parsed path against `path_prefixes` (SPEC-v2 5.5; SRC-FR-15). Docs-site sources honor `robots.txt` (SRC-FR-15).
- **Contact email.** Placeholder domains (`example.com`, `example.org`, `test`, `invalid`) are rejected (SPEC-v2 2).

## 5. Module structure, interfaces and algorithms

> **Owner:** A · **Persona:** `component-designer`

### 5.1 Layout

From SPEC-v2 1:

```
  sources/
    base.py                   # SourceSpec, Capability, SourceAdapter, SourceContext
    registry.py               # SourceRegistry, Selected
    mcp_upstream.py           # UpstreamMcpAdapter base
    arxiv.py crossref.py openalex.py semantic_scholar.py datacite.py core_ac.py unpaywall.py
    openaire.py doaj.py zenodo.py hal.py dblp.py orcid.py ads.py lens.py
    osf.py biorxiv.py medrxiv.py ssrn.py hf_papers.py
    europe_pmc.py pubmed.py clinical_trials.py
    dspace.py                 # one adapter, instances from config
    ietf.py nist.py nvd.py aws_knowledge.py ms_learn.py google_devknowledge.py docs_site.py
    vertex_search.py brave_search.py serpapi.py google_pse.py    # group "web" (5.5)
    loc.py open_library.py wikipedia.py                       # group "reference"
    sitequery.py              # pure helpers: site_set -> provider query strings and batches
    github.py opencitations.py crossref_updates.py eric.py
  testing/                    # importable fakes for tests: clock.py adapters.py launchctl.py notifier.py
tests/
  unit/ ...   sources/<id>/fixtures/ + test_<id>.py   sources/test_conformance.py
```

Related platform modules: `platform/mcp_client.py` (`McpUpstreamPort`, MCP client over the shared HTTP client) and `platform/google_adc.py` (`GoogleAdcProvider`, M1, extra `gcp`).

### 5.2 Registry (`sources/registry.py`)

From SPEC-v2 5.1:

- **Construction.** `SourceRegistry(settings, ctx_factory, *, has_credential: Callable[[str], bool], health: Callable[[str], str | None] = lambda s: None, modules: Iterable[str] | None = None, extra_adapters: Iterable[tuple[SourceSpec, type[SourceAdapter]]] = ())`. Tests pass `modules=[]` and `extra_adapters` from `research_mcp.testing.adapters`; the daemon passes the defaults. Credential presence and health come in as callables, so nothing under `sources/` imports the secrets or health modules.
- **Selection.** `SourceRegistry.select(groups, capability, filters, explicit) -> list[Selected]` combines the enabled flags, credential presence, contact presence, extras and current health state. `Selected` holds the `source`, the `adapter`, and a `skip: SourceStatus | None`.
- **Policies.** The registry implements `PolicyResolver` from each spec's `policy()`.

Discovery and instances are in 2.3 and 3.2. `FederationService.search` calls `registry.select(...)` first; statuses for skipped sources are created immediately (SPEC-v2 7.1).

### 5.3 Conformance suite (`tests/sources/test_conformance.py`)

From SPEC-v2 5.2. `tests/sources/test_conformance.py` is parametrized over `SourceRegistry.all()`. It serves the fixtures through an `httpx.MockTransport`, uses a fake `Sleeper` and a `FakeClock`, and checks:

1. `search_ok` maps to at least one `WorkRecord` with a normalized identifier and provenance.
2. `search_empty` returns an empty page, not an error.
3. 429 raises `HttpError(rate_limited)` with `retry_after_ms`, and the fake sleeper records the wait.
4. 5xx raises `upstream_error` once the retry budget is spent.
5. A malformed body raises `upstream_error`, never `KeyError`, `TypeError` or `ValueError`.
6. An oversize body raises `too_large` before the whole body is read.
7. Every request goes to a host in `spec.hosts`.
8. `probe` returns `ok=True, shape_ok=True` against `get_ok`, and `shape_ok=False` against `malformed`.

Run a single source with `-k <id>`. The fake adapter in `research_mcp.testing.adapters` carries its own seven fixtures in memory and is registered through `extra_adapters`, so the suite runs in M0-09 before any real adapter exists.

### 5.4 Live check

`research-mcp sources check --live [--id X] [--refresh-fixtures]` calls each enabled source once through the daemon's client. With `--refresh-fixtures`, it writes new fixtures to `tests/sources/<id>/fixtures/_review/`. It never overwrites the committed fixtures (SPEC-v2 5.3).

### 5.5 New-source checklist (definition of done)

From SPEC-v2 5.4:

1. Add `src/research_mcp/sources/<id>.py` with `SPEC` and `ADAPTER`. No other source file changes.
2. Discovery is automatic.
3. Add a fixtures folder with the seven fixtures. The conformance suite passes with `-k <id>`.
4. Add unit tests for any source-specific mapping.
5. If the source needs a credential, add the Keychain name to section 3.1 in the next version of this document, and put the signup URL in the spec.
6. Regenerate the inventory (`tools/gen_inventory.py`). In milestone plans, one closing unit does this for all new sources.

### 5.6 Upstream MCP adapters

Upstream MCP servers (AWS Knowledge, Microsoft Learn) are adapters that use an MCP client instead of HTTP JSON (HLD-v3 4). They call `McpUpstreamPort.call_tool` (2.1), implemented in M1 by `platform/mcp_client.py` over the shared HTTP client, and build on the `UpstreamMcpAdapter` base in `sources/mcp_upstream.py` (SPEC-v2 1, 4, 12.4).

### 5.7 Web sources

From SPEC-v2 5.5. All four have `group="web"`, `enabled_by_default=False` (enabled once settings and credential are present), `probe.cost="metered"` where no free probe exists, `rate.daily_quota` from `budget_cap`, and return `work_type="webpage"` records with the URL as identifier and the snippet as an untrusted abstract.

| Source | Endpoint | Auth | Free probe and quota |
|---|---|---|---|
| `vertex_search` (instances `vertex_<name>`) | `POST https://discoveryengine.googleapis.com/v1/projects/{project}/locations/{location}/collections/default_collection/engines/{engine_id}/servingConfigs/default_search:search` with `{"query", "pageSize", "pageToken"}` | Google sign-in (3.1.1) | `GET .../engines/{engine_id}` every 6 h (no query cost) |
| `brave_search` | `GET https://api.search.brave.com/res/v1/web/search?q=&count=` | `X-Subscription-Token` header | none free: one query every 24 h; rate-limit headers parsed passively on every call |
| `serpapi` | `GET https://serpapi.com/search.json?engine=google&q=&num=` | `api_key` query parameter (URL never logged) | `GET https://serpapi.com/account.json` (free; gives searches left) every 6 h |
| `google_pse` | `GET https://www.googleapis.com/customsearch/v1?cx=&q=&num=` | `x-goog-api-key` header | none free: one query every 24 h; `shutdown_on = 2027-01-01` |

### 5.8 Site sets in queries (`sources/sitequery.py`)

Pure functions (SPEC-v2 5.5):

- `site_query(query, domains) -> str` builds `(<query>) (site:a OR site:b ...)`, as v1 did.
- `site_batches(query, domains, max_chars, max_batches) -> list[str]` splits the domains so each query fits; the domains the query names come first (v1's ranking). Brave uses `max_chars=380`, `max_batches=3`; SerpAPI and Programmable Search use one query (`max_batches=1`) and report `truncated` when domains are dropped.
- Vertex ignores `site_query`; when `site_set` is given, results are filtered after the call by host.

### 5.9 Federation of the `web` group

Implemented in `FederationService` (SPEC-v2 7.1, search component); the rules come from SPEC-v2 5.5:

- `auto` selection never includes `web`, because `federation.default_groups` excludes it.
- When a caller names the group (or more than one web source) and `web.strategy == "fallback"`, the web sources run one at a time in `web.order`, skipping any whose status is `disabled`, `unconfigured`, `budget_exhausted`, `rate_limited` or `down`. The first that returns at least one result without error ends the chain; the others report `state="not_needed"`. Non-web sources in the same call still fan out in parallel, and the web chain shares the overall deadline.
- With `strategy == "all"`, web sources fan out like any other group.
- Each call to a web source counts against its cap in `StateStore` (`quota_used` in `source_health`); at the cap the source reports `budget_exhausted(reset=next local midnight)`.

### 5.10 Source inventory

`tools/gen_inventory.py` writes `docs/generated/sources.md` from the registered adapters, and `gen_inventory.py --check` is a gate (SPEC-v2 changes from v1, item 2). CI runs `uv run python tools/gen_inventory.py --check` (SPEC-v2 12.1). Adapter units do not touch `docs/generated/sources.md`; one closing unit regenerates the inventory (SPEC-v2 12.4).

## 6. Error handling, retries and idempotency

> **Owner:** A · **Persona:** `component-designer`

- **Adapters never retry or sleep** (SRC-FR-3). The shared HTTP client does both, from the spec's policy (ADR 0006). From SPEC-v2 3.3:
  - Retries: up to 3 attempts on 429, 500, 502, 503 and 504, and on connection errors. If every attempt gets a 429, the call fails with `rate_limited` and the last `retry_after_ms`.
  - The delay is `Retry-After` when present. A delay over 60 s is not waited for; the call fails with `rate_limited` and `retry_after_ms`.
  - Without `Retry-After`, the delay is exponential from a 0.5 s base, with full jitter.
  - Other 4xx responses are not retried.
  - All waiting goes through the injected `Sleeper`, so tests never sleep for real.
  - Size: responses are streamed; passing `max_bytes` (default from the policy) aborts the call with `too_large`.
- **Error classifier.** The client raises `HttpError(code: ErrorCode, status: int | None, retry_after_ms: int | None, detail: str | None)`, defined in `core/errors.py`. Before the generic mapping, a non-2xx response is passed to `policy.error_classifier` when the source declares one (for example OpenAlex maps an "Insufficient budget" 429 to `budget_exhausted` with `detail="daily budget"`). The message text is generic; details go to the log through the redactor (SPEC-v2 3.3).
- **Error codes** (SPEC-v2 3.7):

```python
class ErrorCode(StrEnum):
    INVALID_ARGUMENT = "invalid_argument"; NOT_FOUND = "not_found"; UNCONFIGURED = "unconfigured"
    AUTH_FAILED = "auth_failed"; RATE_LIMITED = "rate_limited"; UPSTREAM_ERROR = "upstream_error"
    UPSTREAM_TIMEOUT = "upstream_timeout"; BUDGET_EXHAUSTED = "budget_exhausted"; TOO_LARGE = "too_large"
    BLOCKED_BY_POLICY = "blocked_by_policy"; DISABLED = "disabled"; EXTRACT_FAILED = "extract_failed"
    INTERNAL = "internal"

class SourceStatus(BaseModel):
    source: str; state: Literal["ok","empty","timeout","rate_limited","error","unconfigured",
                                "disabled","skipped_unhealthy","skipped_budget"]
    count: int = 0; latency_ms: int | None = None; retry_after_ms: int | None = None
    error_code: ErrorCode | None = None
```

- **Adapter error behavior** is fixed by conformance checks 3 to 6 (5.3): 429 raises `HttpError(rate_limited)` with `retry_after_ms`; 5xx raises `upstream_error` once the retry budget is spent; a malformed body raises `upstream_error`, never `KeyError`, `TypeError` or `ValueError`; an oversize body raises `too_large` before the whole body is read. An empty result is an empty page, not an error.
- **Skips, not failures.** A disabled source is never called and is skipped with state `disabled`; a source with a missing required credential, an unset contact for `needs_contact`, or a missing extra is `unconfigured` with the fix; a web source at its cap is `budget_exhausted` (SRC-FR-5 to SRC-FR-7, SRC-FR-20; 5.2, 5.9).
- **Unknown site set.** An unknown set name is `invalid_argument` before any call (SRC-FR-22; SRC-31).
- **Idempotency.** Adapters are translators with no writes of their own (SRC-FR-3). The live check writes only to `tests/sources/<id>/fixtures/_review/` and never overwrites committed fixtures (5.4).

## 7. Configuration and feature flags

> **Owner:** A · **Persona:** `component-designer`

| Flag | Default | Safe to switch off? |
| --- | --- | --- |
| `sources.<id>.enabled` | Spec default (`enabled_by_default`; `False` for the four `web` sources, SPEC-v2 5.5; ADS and Lens are disabled by default, PRD-sources-v4 1.3) | Yes: a disabled source is never called, is listed `disabled` and is skipped by federation; no code change (SRC-FR-5) |
| `--live` on `research-mcp sources check` | Off (opt-in) | Yes: default test runs make no network calls; `live` tests are deselected by default (NFR-9; TEST-PLAN-v3 2) |
| `--refresh-fixtures` on the live check | Off | Yes: without it no fixtures are written (5.4) |
| Optional extra `gcp` (`google-auth`) | Not installed | Yes: without it `vertex_search` shows `unconfigured` with the install command (ADR 0012; SRC-FR-7) |

Other settings that shape behavior are in 3.2: `sources.<id>.budget_cap` (default none, `100` for `web` sources), `web.strategy` (`"fallback"`), `web.order`, `site_sets.<name>`, `federation.default_groups` and `contact.email`.

## 8. Observability

> **Owner:** A · **Persona:** `sre`

- **Call records.** Every HTTP attempt produces a `CallRecord` for the `CallSink`; in the daemon the sink is `StateStore.record_call`, flushed every second (SPEC-v2 3.3). The Google sign-in refresh is recorded as a `CallRecord` with `source="google_signin"` (SPEC-v2 3.1.1).
- **Probes.** Each spec declares `probe: ProbeSpec(cadence_s, cost, description)` (default `ProbeSpec(3600, "free", "")`); `probe()` returns `ProbeResult` with `ok`, `latency_ms`, `shape_ok`, `detail_code`, `quota_remaining` and `credential_expires_at` (2.1, 3.1). `HealthService` schedules each source's probe at `spec.probe.cadence_s` with 0 to 10% jitter, and `evaluate(source)` uses `spec.shutdown_on` among its inputs (SPEC-v2 10.2).
- **Web-source probes and quota** are in the 5.7 table: Vertex every 6 h at no query cost; SerpAPI `account.json` every 6 h; Brave and Programmable Search one query every 24 h; Brave rate-limit headers parsed passively on every call. Quota use is `quota_used` in `source_health` (3.5).
- **Inventory.** `docs/generated/sources.md` is generated from the registry; CI fails when it is stale (5.10; NFR-10).

No alert thresholds for this component trace to an NFR yet (see 11).

## 9. Test strategy for this component

> **Owner:** C · **Persona:** `test-architect` drafts; the owner approves at Gate 3

No test in `tests/` cites an `AT-SRC` id yet. Planned files come from the SPEC-v2 12.3 unit scopes and the SPEC-v2 1 layout; where a unit lists several test files, the file chosen for a criterion is `[inferred]`.

| Criterion | Planned tests | Level | Status |
| --- | --- | --- | --- |
| SRC-1 | `tests/unit/sources/test_registry.py` (M0-09 scope; file choice `[inferred]`) | unit | planned |
| SRC-2 | `tests/unit/sources/test_registry.py` (M0-09) | unit | planned |
| SRC-3 | `tests/unit/sources/test_registry.py` (M0-09) | unit | planned |
| SRC-4 | `tests/unit/sources/test_registry.py` (M0-09) | unit | planned |
| SRC-5 | `tests/unit/sources/test_registry.py` (M0-09) | unit | planned |
| SRC-6 | `tests/sources/test_conformance.py` (M0-09; SPEC-v2 5.2) | unit | planned |
| SRC-7 | `tests/unit/sources/test_adapter_imports.py` (M0-09) | unit | planned |
| SRC-10 | `tests/sources/arxiv/test_arxiv.py` and `tests/sources/test_conformance.py -k arxiv` (M0-10) | integration | planned |
| SRC-11 | `tests/sources/crossref/test_crossref.py` and `tests/sources/test_conformance.py -k crossref` (M0-11) | integration | planned |
| SRC-12 | `tests/sources/openalex/test_openalex.py` and `tests/sources/test_conformance.py -k openalex` (M0-12) | integration | planned |
| SRC-8 | `tests/contract/test_tools_discovery.py` (M0-14 scope; file choice `[inferred]`) | contract | planned |
| SRC-13 | `tests/unit/test_cli.py` (M0-16 scope; file choice `[inferred]`) | unit | planned |
| SRC-20 | `tests/sources/test_conformance.py` with each adapter's `tests/sources/<id>/fixtures/` | integration | planned |
| SRC-21 | `tests/sources/<id>/test_<id>.py` pattern (SPEC-v2 1) for `dspace` | integration | planned |
| SRC-22 | `tests/sources/<id>/test_<id>.py` pattern (SPEC-v2 1) for `aws_knowledge` and `ms_learn` | integration | planned |
| SRC-23 | `tests/sources/<id>/test_<id>.py` pattern (SPEC-v2 1) for `docs_site` | integration | planned |
| SRC-24 | planned | unit | planned |
| SRC-25 | planned, under `tests/live/` (opt-in; SPEC-v2 1) | live | planned |
| SRC-26 | planned | unit | planned |
| SRC-27 | planned | unit | planned |
| SRC-28 | planned | integration | planned |
| SRC-29 | planned | integration | planned |
| SRC-30 | planned | integration | planned |
| SRC-31 | planned | unit | planned |
| SRC-32 | `tests/sources/<id>/test_<id>.py` pattern (SPEC-v2 1) for `vertex_search` | integration | planned |
| SRC-33 | `tests/sources/<id>/test_<id>.py` pattern (SPEC-v2 1) for `brave_search`, `serpapi` and `google_pse` | integration | planned |

Each test names its criterion first in its docstring (repository instructions; TEST-PLAN-v3 1, item 3).

## 10. Decisions and alternatives

> **Owner:** A · **Persona:** `component-designer`

| Decision | Rationale | Alternatives considered |
| --- | --- | --- |
| Every source is one module with a `SourceSpec` and an adapter that only translates; the shared HTTP client retries, sleeps and attaches secrets | Breadth is the product (D1), yet v1 had no source abstraction (ADR 0006) | v1's per-source tools (DSpace as eight copy-paste tools) (ADR 0006) |
| Policy types live in `core/specs.py` | So the HTTP layer does not depend on the source layer (ADR 0006) | Not recorded |
| Discovery by `pkgutil.iter_modules` plus an entry point group; no central list | Adding a source edits no shared file (SPEC-v2 5.1; 12.3 notes) | Not recorded |
| Credential presence and health are injected into the registry as callables | Nothing under `sources/` imports the secrets or health modules (SPEC-v2 5.1) | Not recorded |
| One `dspace` adapter with four configured instances | Instances come from configuration alone (SRC-FR-4; ADR 0006) | Separate tools per repository, as in v1 (REVIEW-v1 3, finding 6) |
| AWS Knowledge and Microsoft Learn run through v2 as upstream MCP sources over `McpUpstreamPort` | They appear on the source board and in federated search; rate limits, host policy, telemetry and redaction still apply (O6; SRC-FR-10) | Add the MCP servers to clients separately (O6, REVIEW-v1 7); keep v1's undocumented site-search endpoints (REVIEW-v1 4) |
| Web search is the optional, capped `web` group with a `fallback` strategy by default | Spend stays deliberate (ADR 0012) | Remove all web-search providers (REVIEW-v1 D7, O1), superseded by ADR 0012 |
| `vertex_search` uses the owner's Google sign-in through `google-auth`, not a Keychain item | `gcloud` owns the credential file; v2 keeps the token in memory only (ADR 0012) | Not recorded |
| Docs-site filters match the parsed host and path | v1 matched URL substrings (SPEC-v2 5.5) | v1's substring matching |
| v1's docs-domain list and crawl projects ship as data in `defaults.toml` | Topic coverage is configuration, not code (ADR 0012) | Not recorded |

## 11. Open questions

> **Owner:** A · **Persona:** `component-designer`

- [ ] Q: Fixture count. SRC-FR-8, ADR 0006 and SPEC-v2 5.2 say seven fixtures per adapter; PRD-sources-v3 section 4 says "at least the six conformance fixtures".
- [ ] Q: Source count. PRD-v4 (G1 and the M1 exit) and PRD-sources-v3 say 45 sources; TEST-PLAN-v3 section 8 (M1 exit gate) says "all 38 sources registered and passing conformance"; ADR 0012 counts 38 to 42 (before the reference group).
- [ ] Q: Inventory generator. SRC-FR-13 says the inventory is generated by `research-mcp sources --markdown`; SPEC-v2 12.1 and 12.3 and SRC-13 use `tools/gen_inventory.py` and its `--check` flag. Is the CLI command also required?
- [ ] Q: Status names. `SourceStatus.state` (SPEC-v2 3.7) allows `ok`, `empty`, `timeout`, `rate_limited`, `error`, `unconfigured`, `disabled`, `skipped_unhealthy` and `skipped_budget`, but SPEC-v2 5.5, SRC-FR-20 and SRC-30 use `not_needed` and `budget_exhausted`, and the fallback chain skips sources whose status is `down`. Which values belong in the literal?
- [ ] Q: `SourceSpec` validation. SRC-1 requires checks on required fields and on rate and timeout bounds, but SPEC-v2 4 defines no bounds and no validation hook on the frozen dataclass. What are the bounds, and where is validation done?
- [ ] Q: Web-source enablement. SRC-FR-19 says each web source is disabled until its settings and credential are present; SPEC-v2 5.5 says `enabled_by_default=False (enabled once settings and credential are present)`. Does presence alone enable the source, or must the owner also set `sources.<id>.enabled = true`?
- [ ] Q: Placeholder contact. SRC-FR-11 says the server refuses to start an affected source with a placeholder address; SPEC-v2 2 says placeholder domains are rejected (settings validation) and an unset address leaves `needs_contact` sources `unconfigured` while the daemon still starts. Does a configured placeholder fail settings load or only hold back the affected sources?
- [ ] Q: Status note. SRC-FR-1 lists a "status note (for example a shutdown date)", but `SourceSpec` has `shutdown_on` and `docs_url` and no free-text note field. Is `shutdown_on` enough?
- [ ] Q: `robots.txt`. SRC-FR-15 and SRC-23 require docs-site sources to honor `robots.txt`, but SPEC-v2 5.5 does not say where it is fetched, cached or enforced (the `docs_site` adapter is M1; `crawl_site` and crawl jobs are M2, SPEC-v2 7.2 and 12.4).
- [ ] Q: `docs_site_syncope` seeds. SPEC-v2 5.5 names "the 4.1 and 4.0 reference guide and getting-started pages" without URLs, so `defaults.toml` cannot be written from the SPEC alone (SRC-26).
- [ ] Q: New-source checklist versus OUT-3. Step 5 of SPEC-v2 5.4 asks for a SPEC change for each new credential, while SRC-FR-16 and PRD-v4 G3 say no other hand-written file changes.
- [ ] Q: Contracts. No machine-readable contract exists in `docs/contracts/` for the source contract, the `list_sources` tool or the `research://sources` resource. Should one be added at Gate 3?
- [ ] Q: Owning LLD for the SPEC-v2 0.6 row M0-03 (`Budget.fit` and `FederatedResult.statuses`). It is carried in 3.1 because it cites section 4; `Budget.fit` itself is in SPEC-v2 3.7.
- [ ] Q: Observability thresholds. No NFR sets alert thresholds for sources (for example probe failure counts); confirm that thresholds belong to the health component.

### Gate 3: Detailed design reviewed

| Reviewer | Date | Contracts | Schema | AuthZ | Notes |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
