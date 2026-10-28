"""The Google sign-in provider for ``vertex_search`` (LLD-platform-v3 4.2; SEC-INV-11).

Every loader is a fake or reads a fake credential file under ``tmp_path``, and every token
request goes to an ``httpx.MockTransport``, so no real sign-in is read and nothing touches
the network.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import google.auth
import httpx
import pytest
from google.auth import exceptions
from google.oauth2.credentials import Credentials as UserCredentials

from research_mcp.core.models import CallRecord
from research_mcp.platform import google_adc
from research_mcp.platform.google_adc import GoogleAdcProvider, default_loader
from research_mcp.platform.secrets import SecretMeta, SecretRef, SecretState
from research_mcp.testing.clock import FakeClock

SIGNIN = SecretRef.parse("gcloud_adc:GOOGLE_SIGNIN")
NOW = datetime(2026, 10, 27, 12, tzinfo=UTC)
# Generated for these tests; not real credentials.
TOKEN = "ya29.test-access-token-0f3b9c"
FRESH = "ya29.test-fresh-token-7d21e4"
PRIVATE = "diagnostic text that names a refresh token rt-test-91ac"


class Sink:
    def __init__(self) -> None:
        self.records: list[CallRecord] = []

    def record(self, call: CallRecord) -> None:
        self.records.append(call)


class FakeCredentials:
    """The part of ``google.auth.credentials.Credentials`` the provider uses."""

    def __init__(
        self,
        token: str | None = None,
        expiry: datetime | None = None,
        *,
        error: Exception | None = None,
        account: str = "owner@example.com",
    ) -> None:
        self.token = token
        self.expiry = expiry
        self.account = account
        self.error = error
        self.refreshes = 0

    def refresh(self, request: Any) -> None:
        self.refreshes += 1
        if self.error is not None:
            raise self.error
        self.token = FRESH
        # google-auth keeps expiry as a naive UTC time.
        self.expiry = (NOW + timedelta(hours=1)).replace(tzinfo=None)


def loader_of(creds: FakeCredentials | Exception, calls: list[int] | None = None) -> Any:
    def load() -> tuple[FakeCredentials, str | None]:
        if calls is not None:
            calls.append(1)
        if isinstance(creds, Exception):
            raise creds
        return creds, "owner-project"

    return load


def test_get_refreshes_a_missing_or_expiring_token_and_caches_it() -> None:
    """The token is held in memory and refreshed only when under 5 min remain."""
    clock = FakeClock(NOW)
    creds = FakeCredentials()
    calls: list[int] = []
    provider = GoogleAdcProvider(loader_of(creds, calls), clock=clock)

    state, secret = provider.get(SIGNIN)
    assert state is SecretState.OK
    assert secret is not None and secret.reveal() == FRESH
    assert secret.ref == SIGNIN and secret.ref.name == "GOOGLE_SIGNIN"
    assert FRESH not in repr(secret)
    assert creds.refreshes == 1

    clock.advance(54 * 60)  # 6 min left: the cached token is used
    assert provider.get(SIGNIN)[1] is not None
    assert creds.refreshes == 1
    clock.advance(2 * 60)  # 4 min left
    assert provider.get(SIGNIN)[0] is SecretState.OK
    assert creds.refreshes == 2
    assert calls == [1]  # loaded once


def test_valid_token_from_the_loader_is_not_refreshed() -> None:
    """A loaded token with time left is used as it is."""
    creds = FakeCredentials(TOKEN, (NOW + timedelta(minutes=30)).replace(tzinfo=None))
    state, secret = GoogleAdcProvider(loader_of(creds), clock=FakeClock(NOW)).get(SIGNIN)
    assert state is SecretState.OK
    assert secret is not None and secret.reveal() == TOKEN
    assert creds.refreshes == 0


@pytest.mark.parametrize(
    ("failure", "state"),
    [
        (exceptions.DefaultCredentialsError(PRIVATE), SecretState.MISSING),
        (ImportError(PRIVATE), SecretState.MISSING),
        (exceptions.TransportError(PRIVATE), SecretState.ERROR),
        (OSError(PRIVATE), SecretState.ERROR),
    ],
)
def test_load_failures_map_to_states_without_their_text(
    failure: Exception, state: SecretState, caplog: pytest.LogCaptureFixture
) -> None:
    """@spec SEC-27: no sign-in is missing, other failures error; the text reaches no log."""
    caplog.set_level(logging.DEBUG)
    calls: list[int] = []
    provider = GoogleAdcProvider(loader_of(failure, calls), clock=FakeClock(NOW))
    assert provider.get(SIGNIN) == (state, None)
    assert provider.metadata(SIGNIN) is None
    # A failed load is retried: the owner may sign in while the daemon runs.
    assert provider.get(SIGNIN) == (state, None)
    assert len(calls) == 3
    assert PRIVATE not in caplog.text


@pytest.mark.parametrize(
    ("failure", "state"),
    [
        (exceptions.RefreshError(PRIVATE), SecretState.INVALID),
        (exceptions.TransportError(PRIVATE), SecretState.ERROR),
        (ValueError(PRIVATE), SecretState.ERROR),
    ],
)
def test_refresh_failures_map_to_states_without_their_text(
    failure: Exception, state: SecretState, caplog: pytest.LogCaptureFixture
) -> None:
    """@spec SEC-27: a refused refresh is invalid (HLTH-24); its text reaches no log."""
    caplog.set_level(logging.DEBUG)
    creds = FakeCredentials(error=failure)
    assert GoogleAdcProvider(loader_of(creds), clock=FakeClock(NOW)).get(SIGNIN) == (state, None)
    assert PRIVATE not in caplog.text


def test_empty_token_after_refresh_is_error() -> None:
    """A refresh that leaves no token gives ``error``, not an empty secret."""

    class Empty(FakeCredentials):
        def refresh(self, request: Any) -> None:
            self.token = ""

    provider = GoogleAdcProvider(loader_of(Empty()), clock=FakeClock(NOW))
    assert provider.get(SIGNIN) == (SecretState.ERROR, None)


def test_metadata_gives_account_and_expiry_without_a_token_or_refresh() -> None:
    """@spec SEC-27: metadata is the account email and the token expiry, never the token."""
    expiry = NOW + timedelta(minutes=30)
    creds = FakeCredentials(TOKEN, expiry.replace(tzinfo=None))
    provider = GoogleAdcProvider(loader_of(creds), clock=FakeClock(NOW))
    meta = provider.metadata(SIGNIN)
    assert meta == SecretMeta("GOOGLE_SIGNIN", None, account="owner@example.com", expires_at=expiry)
    assert TOKEN not in repr(meta)
    assert creds.refreshes == 0

    unnamed = FakeCredentials(account="")
    meta = GoogleAdcProvider(loader_of(unnamed), clock=FakeClock(NOW)).metadata(SIGNIN)
    assert meta == SecretMeta("GOOGLE_SIGNIN", None)


def test_service_account_email_is_the_account() -> None:
    """Service-account sign-ins name their account in ``service_account_email``."""

    class ServiceAccount(FakeCredentials):
        service_account_email = "robot@owner-project.iam.gserviceaccount.com"

    meta = GoogleAdcProvider(loader_of(ServiceAccount(account="")), clock=FakeClock(NOW)).metadata(
        SIGNIN
    )
    assert meta is not None
    assert meta.account == "robot@owner-project.iam.gserviceaccount.com"


def test_other_backends_are_not_served_and_set_is_refused() -> None:
    """@spec SEC-27: only gcloud_adc references are served; gcloud owns the sign-in, so no set."""
    calls: list[int] = []
    provider = GoogleAdcProvider(loader_of(FakeCredentials(TOKEN), calls), clock=FakeClock(NOW))
    for text in ("keychain:research-mcp/GOOGLE_SIGNIN", "env:GOOGLE_SIGNIN"):
        ref = SecretRef.parse(text)
        assert provider.get(ref) == (SecretState.MISSING, None)
        assert provider.metadata(ref) is None
    assert calls == []
    with pytest.raises(NotImplementedError):
        provider.set(SIGNIN, TOKEN)


# The token request: google-auth's own refresh over the provider's transport.


def user_credentials(endpoint: str = "https://oauth2.googleapis.com/token") -> UserCredentials:
    return UserCredentials(
        token=None,
        refresh_token="rt-test-5e8a",
        client_id="test-client.apps.googleusercontent.com",
        client_secret="cs-test-2b7f",
        token_uri=endpoint,
        account="owner@example.com",
    )


def token_reply(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200, json={"access_token": TOKEN, "expires_in": 3599, "token_type": "Bearer"}
    )


def test_refresh_goes_to_oauth2_only_and_is_recorded() -> None:
    """The refresh goes to oauth2.googleapis.com and is recorded as a google_signin call."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return token_reply(request)

    sink = Sink()
    provider = GoogleAdcProvider(
        lambda: (user_credentials(), None),
        sink=sink,
        clock=FakeClock(NOW),
        transport=httpx.MockTransport(handler),
    )
    state, secret = provider.get(SIGNIN)
    assert state is SecretState.OK
    assert secret is not None and secret.reveal() == TOKEN
    (request,) = seen
    assert request.method == "POST"
    assert request.url == "https://oauth2.googleapis.com/token"
    assert b"grant_type=refresh_token" in request.content
    (record,) = sink.records
    assert record.source == "google_signin"
    assert record.op == "refresh"
    assert record.status == 200
    assert record.error_code is None
    assert record.ts == NOW
    assert record.attempt == 1
    assert TOKEN not in record.model_dump_json()


def test_refused_refresh_is_invalid_and_recorded() -> None:
    """An invalid_grant reply gives ``invalid`` and a failed call record."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant", "error_description": PRIVATE})

    sink = Sink()
    provider = GoogleAdcProvider(
        lambda: (user_credentials(), None),
        sink=sink,
        clock=FakeClock(NOW),
        transport=httpx.MockTransport(handler),
    )
    assert provider.get(SIGNIN) == (SecretState.INVALID, None)
    (record,) = sink.records
    assert (record.source, record.status, record.error_code) == (
        "google_signin",
        400,
        "upstream_error",
    )


@pytest.mark.parametrize(
    "token_uri",
    [
        "https://sts.googleapis.com/v1/token",
        "http://oauth2.googleapis.com/token",
        "https://oauth2.googleapis.com.evil.test/token",
        "https://oauth2.googleapis.com:8443/token",
    ],
)
def test_token_request_to_any_other_origin_is_refused(token_uri: str) -> None:
    """The provider's transport sends nothing beyond oauth2.googleapis.com."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return token_reply(request)

    sink = Sink()
    provider = GoogleAdcProvider(
        lambda: (user_credentials(token_uri), None),
        sink=sink,
        clock=FakeClock(NOW),
        transport=httpx.MockTransport(handler),
    )
    assert provider.get(SIGNIN) == (SecretState.ERROR, None)
    assert seen == []
    assert sink.records == []


def test_transport_failure_is_error_and_recorded() -> None:
    """A connection failure during refresh gives ``error`` and a call record with no status."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(PRIVATE)

    sink = Sink()
    provider = GoogleAdcProvider(
        lambda: (user_credentials(), None),
        sink=sink,
        clock=FakeClock(NOW),
        transport=httpx.MockTransport(handler),
    )
    assert provider.get(SIGNIN) == (SecretState.ERROR, None)
    assert [(r.status, r.error_code) for r in sink.records][:1] == [(None, "upstream_error")]


def test_default_loader_asks_google_auth_for_cloud_platform_and_allows_no_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``default_loader`` calls ``google.auth.default`` with the cloud-platform scope.

    Its request object refuses every host, so finding the sign-in never calls the network
    (for example the GCE metadata server).
    """
    seen: dict[str, Any] = {}

    def fake_default(**kwargs: Any) -> tuple[str, str]:
        seen.update(kwargs)
        with pytest.raises(exceptions.TransportError):
            kwargs["request"](url="http://169.254.169.254/", method="GET")
        return "creds", "owner-project"

    monkeypatch.setattr(google.auth, "default", fake_default)
    assert default_loader() == ("creds", "owner-project")
    assert seen["scopes"] == ["https://www.googleapis.com/auth/cloud-platform"]
    assert google_adc.SCOPES == ("https://www.googleapis.com/auth/cloud-platform",)


def test_default_loader_reads_a_fake_credential_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With a fake gcloud credential file, the default loader gives user credentials."""
    gcloud = tmp_path / "gcloud"
    gcloud.mkdir()
    (gcloud / "application_default_credentials.json").write_text(
        json.dumps(
            {
                "type": "authorized_user",
                "client_id": "test-client.apps.googleusercontent.com",
                "client_secret": "cs-test-2b7f",
                "refresh_token": "rt-test-5e8a",
                "quota_project_id": "owner-project",
                "account": "owner@example.com",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLOUDSDK_CONFIG", str(gcloud))
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    # google-auth asks the gcloud CLI for a project; with no gcloud on PATH none runs.
    no_tools = tmp_path / "no-tools"
    no_tools.mkdir()
    monkeypatch.setenv("PATH", str(no_tools))
    creds, project = default_loader()
    assert isinstance(creds, UserCredentials)
    assert creds.token is None
    assert creds.account == "owner@example.com"
    assert project is None  # the Vertex project comes from the instance settings
    assert sorted(gcloud.iterdir()) == [gcloud / "application_default_credentials.json"]
