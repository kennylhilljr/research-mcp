"""Validated configuration, loaded explicitly by callers without import-time I/O."""

from __future__ import annotations

import ipaddress
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, field_validator
from pydantic_core import PydanticCustomError
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


def _hide_inputs(exc: ValidationError) -> ValidationError:
    # hide_input_in_errors only covers str(); errors() and json() still carry the
    # rejected value, which may be a token, so the errors are rebuilt without it.
    return ValidationError.from_exception_data(
        exc.title,
        [
            {"type": PydanticCustomError(e["type"], e["msg"]), "loc": e["loc"], "input": "[hidden]"}
            for e in exc.errors(include_url=False, include_context=False, include_input=False)
        ],
        hide_input=True,
    )


class _Config(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True, defer_build=True)

    def __init__(self, **values: Any) -> None:
        try:
            super().__init__(**values)
        except ValidationError as exc:
            error = _hide_inputs(exc)
        else:
            return
        raise error


class ServerSettings(_Config):
    host: str = "127.0.0.1"
    port: int = Field(default=7319, ge=1, le=65535)
    token: str = "keychain:research-mcp/DAEMON_TOKEN"  # noqa: S105 - reference, not a secret

    @field_validator("host")
    @classmethod
    def loopback(cls, value: str) -> str:
        try:
            address = ipaddress.ip_address(value)
        except ValueError as exc:
            raise ValueError("server.host must be a loopback IP address") from exc
        if not address.is_loopback or "%" in value:
            raise ValueError("server.host must be a loopback IP address")
        return value


class PathSettings(_Config):
    state_dir: Path = Path("~/Library/Application Support/research-mcp")
    data_dir: Path = Path("~/Library/Application Support/research-mcp/cache")
    model_cache_dir: Path = Path("~/Library/Caches/research-mcp/models")
    log_dir: Path = Path("~/Library/Logs/research-mcp")

    @field_validator("state_dir", "data_dir", "model_cache_dir", "log_dir")
    @classmethod
    def normalize(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator("state_dir", "data_dir")
    @classmethod
    def durable(cls, value: Path) -> Path:
        if value.is_relative_to((Path.home() / "Library/Caches").resolve()):
            raise ValueError("durable state and data must not be stored under ~/Library/Caches")
        return value

    def create_directories(self) -> None:
        """Called at daemon start, never while loading configuration."""
        for path in (self.state_dir, self.data_dir, self.model_cache_dir, self.log_dir):
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.chmod(0o700)


class ContactSettings(_Config):
    email: str | None = None

    @field_validator("email")
    @classmethod
    def real_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("contact.email must be an email address")
        domain = value.rsplit("@", 1)[1].lower().rstrip(".")
        if any(
            domain == item or domain.endswith("." + item)
            for item in ("example.com", "example.org", "test", "invalid")
        ):
            raise ValueError("contact.email must not use a placeholder domain")
        return value


class LimitSettings(_Config):
    response_bytes: int = Field(default=65536, gt=0)
    download_bytes: int = Field(default=52428800, gt=0)
    pdf_pages: int = Field(default=500, gt=0)
    chunk_hard_cap_chars: int = Field(default=4000, gt=0)


class FederationSettings(_Config):
    deadline_s: float = Field(default=8.0, gt=0)
    default_groups: list[str] = Field(default_factory=lambda: ["scholarly", "preprints"])


class CacheSettings(_Config):
    retention_days: int = Field(default=120, gt=0)
    review_lead_days: int = Field(default=3, ge=0)
    review_time_local: str = Field(default="09:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    batch_open_hours: int = Field(default=24, gt=0)
    reask_days: int = Field(default=7, gt=0)
    trash_days: int = Field(default=7, gt=0)


class ArchiveSettings(_Config):
    target: str = "auto"
    confirmed_path: Path | None = None
    subfolder: str = "Research Archive/{year}"
    fallback: str = "~/Research Archive/{year}"

    @field_validator("target")
    @classmethod
    def absolute_target(cls, value: str) -> str:
        if value != "auto" and not Path(value).is_absolute():
            raise ValueError("archive.target must be auto or an absolute path")
        return value


class NotifySettings(_Config):
    macos: bool = True
    webhook_url: str | None = None
    quiet_hours: str = Field(
        default="21:00-08:00",
        pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d-(?:[01]\d|2[0-3]):[0-5]\d$",
    )

    @field_validator("webhook_url")
    @classmethod
    def tokenless(cls, value: str | None) -> str | None:
        if value is None:
            return None
        # Parser errors quote the input, so they are replaced by a fixed message.
        try:
            url = urlsplit(value)
            valid = url.scheme in {"http", "https"} and bool(url.hostname)
            url.port  # noqa: B018 - raises ValueError on a malformed port
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("notify.webhook_url must be an http or https URL")
        # The token belongs in Keychain NOTIFY_WEBHOOK_TOKEN, sent as a bearer header.
        if "@" in url.netloc or url.query or url.fragment or "?" in value or "#" in value:
            raise ValueError(
                "notify.webhook_url must not carry credentials, a query or a fragment; "
                "store the token in Keychain NOTIFY_WEBHOOK_TOKEN"
            )
        return value


class DiskSettings(_Config):
    cache_warn_bytes: int = Field(default=5368709120, ge=0)
    free_warn_bytes: int = Field(default=16106127360, ge=0)
    free_crit_bytes: int = Field(default=5368709120, ge=0)


class BackupSettings(_Config):
    keep: int = Field(default=7, gt=0)


class SourceSettings(_Config):
    # An absent enabled flag defers to the adapter's SourceSpec.
    model_config = ConfigDict(extra="allow")
    enabled: bool | None = None
    budget_cap: int | None = Field(default=None, ge=0)


class WebSettings(_Config):
    strategy: Literal["fallback", "all"] = "fallback"
    order: list[str] = Field(
        default_factory=lambda: ["vertex_*", "brave_search", "serpapi", "google_pse"]
    )


class CredentialSettings(_Config):
    rotate_by: AwareDatetime | None = None

    @field_validator("rotate_by")
    @classmethod
    def utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else value.astimezone(UTC)


def _site_sets() -> dict[str, list[str]]:
    return {
        "v1_docs": [
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
    }


class _Environment(EnvSettingsSource):
    def __call__(self) -> dict[str, Any]:
        data = super().__call__()
        # EnvSettingsSource folds nested keys to lowercase; restore credential identity
        # before pydantic-settings merges this source with TOML.
        if isinstance(data.get("credentials"), dict):
            data["credentials"] = {key.upper(): value for key, value in data["credentials"].items()}
        return data


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        defer_build=True,
        env_prefix="RESEARCH_MCP_",
        env_nested_delimiter="__",
        extra="forbid",
        # A rejected value such as a webhook URL may carry a token; errors never echo input.
        hide_input_in_errors=True,
        validate_default=True,
    )

    def __init__(self, **values: Any) -> None:
        try:
            super().__init__(**values)
        except ValidationError as exc:
            error = _hide_inputs(exc)
        else:
            return
        raise error

    server: ServerSettings = Field(default_factory=ServerSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    contact: ContactSettings = Field(default_factory=ContactSettings)
    limits: LimitSettings = Field(default_factory=LimitSettings)
    federation: FederationSettings = Field(default_factory=FederationSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    archive: ArchiveSettings = Field(default_factory=ArchiveSettings)
    notify: NotifySettings = Field(default_factory=NotifySettings)
    disk: DiskSettings = Field(default_factory=DiskSettings)
    backup: BackupSettings = Field(default_factory=BackupSettings)
    sources: dict[str, SourceSettings] = Field(default_factory=dict)
    web: WebSettings = Field(default_factory=WebSettings)
    site_sets: dict[str, list[str]] = Field(default_factory=_site_sets)
    credentials: dict[str, CredentialSettings] = Field(default_factory=dict)

    @field_validator("site_sets")
    @classmethod
    def site_set_names(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        if any(not re.fullmatch(r"[a-z0-9_]{1,40}", name) for name in value):
            raise ValueError("site set names must match [a-z0-9_]{1,40}")
        return value

    @field_validator("sources", mode="before")
    @classmethod
    def web_defaults(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        result = dict(value)
        for name, config in value.items():
            if isinstance(config, SourceSettings):
                # Only explicitly set fields override the web-source defaults.
                config = config.model_dump(exclude_unset=True)
            if isinstance(config, dict) and (
                name in {"brave_search", "serpapi", "google_pse", "vertex_search"}
                or config.get("instance_of") == "vertex_search"
            ):
                result[name] = {"enabled": False, "budget_cap": 100, **config}
        return result

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            _Environment(settings_cls),
            TomlConfigSettingsSource(
                settings_cls, toml_file=Path.home() / ".config/research-mcp/config.toml"
            ),
        )
