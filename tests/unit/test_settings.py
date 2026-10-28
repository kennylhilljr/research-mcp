"""Settings acceptance tests use only an isolated home and synthetic configuration."""

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from research_mcp.settings import NotifySettings, Settings, SourceSettings


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    for name in os.environ:
        if name.startswith("RESEARCH_MCP_"):
            monkeypatch.delenv(name)


def write_config(home: Path, text: str) -> None:
    config = home / ".config/research-mcp/config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(text)


V1_DOCS = [
    "keycloak.org",
    "ory.sh",
    "supertokens.com",
    "authelia.com",
    "goauthentik.io",
    "zitadel.com",
    "logto.io",
    "casdoor.org",
    "authgear.com",
    "kanidm.github.io",
    "freeipa.org",
    "syncope.apache.org",
    "openpolicyagent.org",
    "cerbos.dev",
    "authzed.com",
    "casbin.org",
    "permify.co",
    "topaz.sh",
    "warrant.dev",
    "pomerium.com",
    "developer.hashicorp.com",
    "infisical.com",
    "webauthn.guide",
    "jwt.io",
    "datatracker.ietf.org",
    "zanzibar.academy",
]
DOCS_SITES = {
    "docs_site_keycloak": "www.keycloak.org",
    "docs_site_ory": "www.ory.sh",
    "docs_site_opa": "www.openpolicyagent.org",
    "docs_site_vault": "developer.hashicorp.com",
    "docs_site_syncope": "syncope.apache.org",
    "docs_site_freeipa": "www.freeipa.org",
}
DSPACES = {"dspace_mit", "dspace_harvard", "dspace_cornell", "dspace_penn"}
DEFAULT_INSTANCES = set(DOCS_SITES) | DSPACES


def test_defaults(tmp_path: Path) -> None:
    """@spec PLAT-8: Defaults match the settings contract without creating directories."""
    settings = Settings()
    actual = settings.model_dump(exclude={"paths", "site_sets", "sources"})
    assert actual == {
        "server": {
            "host": "127.0.0.1",
            "port": 7319,
            "token": "keychain:research-mcp/DAEMON_TOKEN",
        },
        "contact": {"email": None},
        "limits": {
            "response_bytes": 65536,
            "download_bytes": 52428800,
            "pdf_pages": 500,
            "chunk_hard_cap_chars": 4000,
        },
        "federation": {
            "deadline_s": 8.0,
            "default_groups": ["scholarly", "preprints"],
            "fuzzy_merge": True,
            "record_searches": True,
        },
        "logging": {"debug": False},
        "cache": {
            "retention_days": 120,
            "review_lead_days": 3,
            "review_time_local": "09:00",
            "batch_open_hours": 24,
            "reask_days": 7,
            "trash_days": 7,
        },
        "archive": {
            "target": "auto",
            "confirmed_path": None,
            "subfolder": "Research Archive/{year}",
            "fallback": "~/Research Archive/{year}",
        },
        "notify": {"macos": True, "webhook_url": None, "quiet_hours": "21:00-08:00"},
        "disk": {
            "cache_warn_bytes": 5368709120,
            "free_warn_bytes": 16106127360,
            "free_crit_bytes": 5368709120,
        },
        "backup": {"keep": 7, "drive_copy": False},
        "web": {
            "strategy": "fallback",
            "order": ["vertex_*", "brave_search", "serpapi", "google_pse"],
        },
        "credentials": {},
    }
    assert len(settings.site_sets["v1_docs"]) == 26
    assert "datatracker.ietf.org" in settings.site_sets["v1_docs"]
    # The only default sources are the instances that defaults.toml ships (LLD-sources 3.3).
    assert set(settings.sources) == DEFAULT_INSTANCES
    assert not (tmp_path / "Library").exists()
    assert SourceSettings().enabled is None
    assert SourceSettings().budget_cap is None


def test_toml_and_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """@spec PLAT-8: Nested environment overrides merge with TOML using canonical names."""
    write_config(
        tmp_path,
        """
[server]
port = 8000
[cache]
retention_days = 60
review_lead_days = 5
[credentials.CORE_API_KEY]
rotate_by = "2027-01-01T00:00:00Z"
[credentials.GITHUB_TOKEN]
rotate_by = "2027-02-01T00:00:00Z"
[sources.google_pse]
engine_id = "fixture-engine"
[sources.vertex_library]
instance_of = "vertex_search"
project = "fixture-project"
location = "global"
engine_id = "fixture-engine"
title = "Library"
[sources.dspace_penn]
base_url = "https://repository.invalid"
""",
    )
    from_toml = Settings()
    assert from_toml.server.port == 8000
    assert from_toml.cache.retention_days == 60
    monkeypatch.setenv("RESEARCH_MCP_SERVER__PORT", "17319")
    monkeypatch.setenv("RESEARCH_MCP_CACHE__RETENTION_DAYS", "90")
    monkeypatch.setenv("RESEARCH_MCP_CREDENTIALS__CORE_API_KEY__ROTATE_BY", "2028-01-01T00:00:00Z")
    monkeypatch.setenv("RESEARCH_MCP_SOURCES__GOOGLE_PSE__ENABLED", "true")
    monkeypatch.setenv("RESEARCH_MCP_FEDERATION__DEFAULT_GROUPS", '["reference"]')
    settings = Settings()
    assert settings.server.port == 17319
    assert settings.cache.retention_days == 90
    assert settings.cache.review_lead_days == 5
    assert set(settings.credentials) == {"CORE_API_KEY", "GITHUB_TOKEN"}
    assert settings.credentials["CORE_API_KEY"].rotate_by == datetime(2028, 1, 1, tzinfo=UTC)
    assert settings.credentials["GITHUB_TOKEN"].rotate_by == datetime(2027, 2, 1, tzinfo=UTC)
    assert settings.sources["google_pse"].enabled is True
    assert settings.sources["google_pse"].budget_cap == 100
    assert settings.sources["google_pse"].engine_id == "fixture-engine"
    assert settings.sources["vertex_library"].budget_cap == 100
    assert settings.sources["vertex_library"].enabled is False
    assert settings.sources["dspace_penn"].base_url == "https://repository.invalid"
    assert settings.federation.default_groups == ["reference"]


def test_typed_web_source_defaults() -> None:
    """@spec PLAT-8: Typed SourceSettings input gets the same web defaults as a table."""
    typed = Settings(
        sources={
            "brave_search": SourceSettings(),
            "serpapi": SourceSettings(enabled=True, budget_cap=5),
            "vertex_library": SourceSettings(instance_of="vertex_search"),
            "crossref": SourceSettings(),
        }
    ).sources
    assert typed["brave_search"] == Settings(sources={"brave_search": {}}).sources["brave_search"]
    assert (typed["brave_search"].enabled, typed["brave_search"].budget_cap) == (False, 100)
    assert (typed["serpapi"].enabled, typed["serpapi"].budget_cap) == (True, 5)
    assert (typed["vertex_library"].enabled, typed["vertex_library"].budget_cap) == (False, 100)
    assert (typed["crossref"].enabled, typed["crossref"].budget_cap) == (None, None)


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("SERVER__PORT", "0", "server.port"),
        ("SERVER__PORT", "text", "server.port"),
        ("CACHE__RETENTION_DAYS", "-1", "cache.retention_days"),
        ("CACHE__REVIEW_TIME_LOCAL", "25:00", "cache.review_time_local"),
        ("LIMITS__RESPONSE_BYTES", "0", "limits.response_bytes"),
        ("WEB__STRATEGY", "random", "web.strategy"),
        ("ARCHIVE__TARGET", "relative/path", "archive.target"),
        ("SITE_SETS", '{"Bad-Name": []}', "site_sets"),
    ],
)
def test_invalid_values(
    key: str, value: str, message: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@spec PLAT-8: Invalid configuration reports the field that failed validation."""
    monkeypatch.setenv("RESEARCH_MCP_" + key, value)
    with pytest.raises(ValidationError, match=message):
        Settings()


def test_paths_and_creation(tmp_path: Path) -> None:
    """@spec PLAT-9: Durable data, model cache and logs use private directories."""
    paths = Settings().paths
    assert paths.state_dir == tmp_path / "Library/Application Support/research-mcp"
    assert paths.data_dir == paths.state_dir / "cache"
    assert paths.model_cache_dir == tmp_path / "Library/Caches/research-mcp/models"
    assert paths.log_dir == tmp_path / "Library/Logs/research-mcp"
    paths.create_directories()
    paths.log_dir.chmod(0o755)
    paths.create_directories()
    for path in paths.model_dump().values():
        assert path.is_dir()
        assert path.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("field", ["state_dir", "data_dir"])
@pytest.mark.parametrize(
    "suffix",
    ["Library/Caches", "Library/Caches/data", "Library/Application Support/../Caches/data"],
)
def test_reject_purgeable_paths(field: str, suffix: str, tmp_path: Path) -> None:
    """@spec PLAT-9: Normalize traversal before enforcing durable locations."""
    with pytest.raises(ValidationError, match="durable state and data"):
        Settings(paths={field: tmp_path / suffix})


def test_normalization_and_symlinks(tmp_path: Path) -> None:
    """@spec PLAT-9: Resolve aliases and accept normalized durable paths."""
    cache = tmp_path / "Library/Caches"
    cache.mkdir(parents=True)
    alias = tmp_path / "alias"
    alias.symlink_to(cache, target_is_directory=True)
    with pytest.raises(ValidationError, match="durable state and data"):
        Settings(paths={"data_dir": alias / "data"})
    settings = Settings(paths={"data_dir": "~/Library/Caches/../Application Support/data"})
    assert settings.paths.data_dir == tmp_path / "Library/Application Support/data"


@pytest.mark.parametrize(
    "host",
    ["0.0.0.0", "::", "192.168.1.1", "8.8.8.8", "example.org"],  # noqa: S104 - refusal cases
)
def test_non_loopback(host: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """@spec PLAT-10: Refuse any non-loopback listener before it can bind."""
    monkeypatch.setenv("RESEARCH_MCP_SERVER__HOST", host)
    with pytest.raises(ValidationError, match="loopback"):
        Settings()


@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.2", "::1"])
def test_loopback(host: str) -> None:
    """@spec PLAT-10: Numeric loopback addresses remain usable without DNS."""
    assert Settings(server={"host": host}).server.host == host


@pytest.mark.parametrize(
    "email",
    [
        "person@example.com",
        "person@EXAMPLE.ORG",
        "person@sub.example.com",
        "person@host.test",
        "person@host.invalid",
        "person@host.invalid.",
        "not-an-address",
        "person@test",
        "person@invalid",
    ],
)
def test_placeholder_email(email: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """@spec PLAT-11: Reject placeholder or malformed contact email values."""
    monkeypatch.setenv("RESEARCH_MCP_CONTACT__EMAIL", email)
    with pytest.raises(ValidationError, match="contact.email"):
        Settings()


def test_optional_email() -> None:
    """@spec PLAT-11: Contact is optional, and an ordinary address is accepted."""
    assert Settings().contact.email is None
    assert Settings(contact={"email": "researcher@university.edu"}).contact.email == (
        "researcher@university.edu"
    )


@pytest.mark.parametrize(
    "token",
    [
        "not-a-reference",
        "keychain:wrong-service/DAEMON_TOKEN",
        "keychain:research-mcp/lowercase",
    ],
)
def test_token_must_be_keychain_reference(token: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """@spec PLAT-8: server.token must parse as a keychain:research-mcp/<NAME> reference."""
    monkeypatch.setenv("RESEARCH_MCP_SERVER__TOKEN", token)
    with pytest.raises(ValidationError, match="server.token"):
        Settings()


def test_env_references_rejected_in_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """@spec PLAT-12: server.token rejects an env: reference even though it parses."""
    with pytest.raises(ValidationError, match="server.token"):
        Settings(server={"token": "env:DAEMON_TOKEN"})
    monkeypatch.setenv("RESEARCH_MCP_SERVER__TOKEN", "env:DAEMON_TOKEN")
    with pytest.raises(ValidationError, match="server.token"):
        Settings()


def test_logging_debug_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """@spec PLAT-8: logging.debug defaults to false and takes an environment override."""
    assert Settings().logging.debug is False
    monkeypatch.setenv("RESEARCH_MCP_LOGGING__DEBUG", "true")
    assert Settings().logging.debug is True


def test_backup_drive_copy_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """@spec PLAT-8: backup.drive_copy defaults to false and takes an environment override."""
    assert Settings().backup.drive_copy is False
    monkeypatch.setenv("RESEARCH_MCP_BACKUP__DRIVE_COPY", "true")
    assert Settings().backup.drive_copy is True


@pytest.mark.parametrize(
    "url",
    [
        "https://notify.invalid/inbox?token=synthetic-marker",
        "https://notify.invalid/inbox?synthetic-marker",
        "https://notify.invalid/inbox#synthetic-marker",
        "https://user:synthetic-marker@notify.invalid/inbox",
        "https://synthetic-marker@notify.invalid/inbox",
        "ftp://notify.invalid/synthetic-marker",
        "synthetic-marker",
        "https://[synthetic-marker]/inbox",
        "https://[synthetic-marker/inbox",
        "https://notify.invalid:synthetic-marker/inbox",
    ],
)
def test_webhook_rejects_tokens(url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """@spec PLAT-8: A webhook token is refused in the URL and never echoed in the error."""

    def assert_hidden(error: ValidationError) -> None:
        for output in (str(error), repr(error), error.json(), repr(error.errors())):
            assert "synthetic-marker" not in output

    with pytest.raises(ValidationError, match="notify.webhook_url") as caught:
        Settings(notify={"webhook_url": url})
    assert_hidden(caught.value)
    with pytest.raises(ValidationError, match="notify.webhook_url") as caught:
        NotifySettings(webhook_url=url)
    assert_hidden(caught.value)
    monkeypatch.setenv("RESEARCH_MCP_NOTIFY__WEBHOOK_URL", url)
    with pytest.raises(ValidationError, match="notify.webhook_url") as caught:
        Settings()
    assert_hidden(caught.value)


def test_webhook_accepts_plain_url() -> None:
    """@spec PLAT-8: A webhook URL without credentials is accepted."""
    url = "https://notify.invalid/inbox"
    assert Settings(notify={"webhook_url": url}).notify.webhook_url == url


def test_rotate_by_is_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    """@spec PLAT-8: Credential rotate_by is normalized to UTC and needs a timezone."""
    settings = Settings(credentials={"CORE_API_KEY": {"rotate_by": "2027-01-01T05:00:00+05:00"}})
    rotate_by = settings.credentials["CORE_API_KEY"].rotate_by
    assert rotate_by == datetime(2027, 1, 1, tzinfo=UTC)
    assert rotate_by is not None
    assert rotate_by.tzinfo is UTC
    for naive in ("2027-01-01T00:00:00", datetime(2027, 1, 1)):  # noqa: DTZ001 - refusal case
        with pytest.raises(ValidationError, match="rotate_by"):
            Settings(credentials={"CORE_API_KEY": {"rotate_by": naive}})
    monkeypatch.setenv("RESEARCH_MCP_CREDENTIALS__CORE_API_KEY__ROTATE_BY", "2027-01-01T00:00:00")
    with pytest.raises(ValidationError, match="rotate_by"):
        Settings()


def test_site_sets_override_by_name_empty_list_removes_and_invalid_name_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@spec SRC-27: Site sets load from defaults and config; config wins by name.

    A set in the config replaces the default set of that name and leaves the others, an
    empty list removes a set, and an invalid set name fails validation.
    """
    assert Settings().site_sets == {"v1_docs": V1_DOCS}
    write_config(tmp_path, '[site_sets]\niam_core = ["keycloak.org", "ory.sh"]\n')
    assert Settings().site_sets == {"v1_docs": V1_DOCS, "iam_core": ["keycloak.org", "ory.sh"]}
    write_config(tmp_path, '[site_sets]\nv1_docs = ["jwt.io"]\n')
    assert Settings().site_sets == {"v1_docs": ["jwt.io"]}
    write_config(tmp_path, '[site_sets]\nv1_docs = []\niam_core = ["keycloak.org"]\n')
    assert Settings().site_sets == {"iam_core": ["keycloak.org"]}
    # The environment sits above the config file and merges by name the same way.
    monkeypatch.setenv("RESEARCH_MCP_SITE_SETS", '{"iam_core": [], "authz": ["cerbos.dev"]}')
    assert Settings().site_sets == {"authz": ["cerbos.dev"]}
    monkeypatch.delenv("RESEARCH_MCP_SITE_SETS")
    for bad in ("Bad-Name", "x" * 41, ""):
        write_config(tmp_path, f'[site_sets]\n"{bad}" = ["jwt.io"]\n')
        with pytest.raises(ValidationError, match="site_sets"):
            Settings()
    # An invalid name fails even when its list is empty and would remove nothing.
    write_config(tmp_path, "")
    with pytest.raises(ValidationError, match="site_sets"):
        Settings(site_sets={"Bad-Name": []})
    assert Settings(site_sets={"mine": ["jwt.io"]}).site_sets["v1_docs"] == V1_DOCS


def test_defaults_ship_the_v1_instances_and_config_replaces_an_entry_by_id(
    tmp_path: Path,
) -> None:
    """``defaults.toml`` holds the four DSpace and six docs-site instances (LLD-sources 3.3).

    A ``sources.<id>`` table in the config replaces the default entry of that id and leaves
    the other defaults in place.
    """
    sources = Settings().sources
    for name, host in DOCS_SITES.items():
        entry = sources[name].model_extra or {}
        assert entry["instance_of"] == "docs_site"
        assert entry["allowed_hosts"] == [host]
        assert entry["title"]
        assert entry.get("sitemap") or entry.get("seed_urls")
    extra = {name: sources[name].model_extra or {} for name in DEFAULT_INSTANCES}
    assert extra["docs_site_ory"]["sitemap"] == "https://www.ory.sh/sitemap.xml"
    assert extra["docs_site_keycloak"]["path_prefixes"] == ["/docs/", "/securing-apps/", "/guides/"]
    assert extra["docs_site_vault"]["seed_urls"] == ["https://developer.hashicorp.com/vault/docs"]
    assert extra["docs_site_vault"]["follow_links"] is True
    assert extra["docs_site_syncope"]["follow_links"] is False
    for name in DSPACES:
        assert extra[name]["instance_of"] == "dspace"
        assert extra[name]["base_url"].startswith("https://")
        assert extra[name]["base_url"].endswith("/server/api")
    assert extra["dspace_mit"]["base_url"] == "https://dspace.mit.edu/server/api"
    write_config(
        tmp_path,
        '[sources.dspace_mit]\ninstance_of = "dspace"\n'
        'base_url = "https://dspace.mit.edu/server/api"\ntitle = "MIT, my title"\n'
        "enabled = false\n",
    )
    sources = Settings().sources
    assert set(sources) == DEFAULT_INSTANCES
    assert sources["dspace_mit"].enabled is False
    assert (sources["dspace_mit"].model_extra or {})["title"] == "MIT, my title"
    assert sources["dspace_penn"].enabled is None
