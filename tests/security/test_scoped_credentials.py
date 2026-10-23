"""Credentials reach only their origin and never an error, a log or a download.

LLD-platform-v2 4.4; LLD-security-v2 4.3 (E18, E19, E23, E32); SEC-INV-4, SEC-INV-5.
The secret values are generated per test and never real.
"""

from __future__ import annotations

import logging
import secrets
import traceback
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from research_mcp.core.errors import ErrorCode, HttpError
from research_mcp.core.models import AuthUse, CallRecord
from research_mcp.core.specs import AuthSpec, RateSpec, SourcePolicy
from research_mcp.platform.download import Downloader, DownloadPolicy
from research_mcp.platform.http import HttpClient
from research_mcp.platform.secrets import Secret, SecretRef
from research_mcp.testing.clock import FakeClock, FakeSleeper

Handler = Callable[[httpx.Request], httpx.Response]


def make_secret(name: str) -> Secret:
    return Secret(SecretRef("keychain", name, f"research-mcp/{name}"), secrets.token_urlsafe(24))


def policy(source: str, placement: str, param: str, hosts: set[str], origins: tuple[str, ...]):
    return SourcePolicy(
        source=source,
        hosts=frozenset(hosts),
        auth=AuthSpec(
            secrets=(source.upper() + "_KEY",),
            required=True,
            placement=placement,  # type: ignore[arg-type]
            param=param,
            origins=origins,
            signup_url="https://signup.test/",
        ),
        rate=RateSpec(rps=1000.0, burst=1000),
        timeout_s=10.0,
        max_bytes=1_000_000,
    )


CORE = policy(
    "core",
    "bearer",
    "",
    {"api.core.ac.uk", "core.ac.uk", "pdfs.publisher.test"},
    ("https://api.core.ac.uk",),
)
SERPAPI = policy("serpapi", "query", "api_key", {"serpapi.com"}, ("https://serpapi.com",))
GOOGLE = policy(
    "google_cse",
    "header",
    "x-goog-api-key",
    {"customsearch.googleapis.com"},
    ("https://customsearch.googleapis.com",),
)


class Resolver:
    def __init__(self, policies: list[SourcePolicy], keys: dict[str, Secret]) -> None:
        self._policies = {p.source: p for p in policies}
        self._keys = keys

    def policy(self, source: str) -> SourcePolicy:
        return self._policies[source]

    def secret_for(self, source: str) -> Secret | None:
        return self._keys.get(source)


class Sink:
    def __init__(self) -> None:
        self.records: list[CallRecord] = []

    def record(self, call: CallRecord) -> None:
        self.records.append(call)


def client_for(handler: Handler, resolver: Resolver) -> tuple[HttpClient, list[httpx.Request]]:
    sent: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return handler(request)

    clock = FakeClock()
    client = HttpClient(
        resolver,
        resolver,
        Sink(),
        clock,
        FakeSleeper(clock),
        "owner@uni.edu",
        transport=httpx.MockTransport(recording),
    )
    return client, sent


def ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"ok": True})


def wire(request: httpx.Request) -> str:
    """Everything a request puts on the wire, as text."""
    headers = "\n".join(f"{k}: {v}" for k, v in request.headers.multi_items())
    return f"{request.method} {request.url}\n{headers}\n{request.content.decode(errors='replace')}"


def error_text(error: BaseException) -> str:
    """The error as a log or a client would show it, with any chained exception it shows."""
    parts = [str(error), repr(error), repr(vars(error)), *traceback.format_exception_only(error)]
    chained = error.__cause__ or (None if error.__suppress_context__ else error.__context__)
    if chained is not None:
        parts.append(error_text(chained))
    return "\n".join(parts)


async def test_credential_only_sent_to_spec_origin() -> None:
    """@spec SEC-8: the CORE key goes to api.core.ac.uk only, never to a PDF host it lists."""
    key = make_secret("CORE_KEY")
    client, sent = client_for(ok, Resolver([CORE], {"core": key}))

    await client.get_json("https://api.core.ac.uk/v3/search/works", source="core")
    assert sent[-1].headers["Authorization"] == f"Bearer {key.reveal()}"

    for url in (
        "https://core.ac.uk/download/pdf/123.pdf",
        "https://pdfs.publisher.test/paper.pdf",
        "http://api.core.ac.uk/v3/search/works",
        "https://api.core.ac.uk:8443/v3/search/works",
    ):
        await client.get_json(url, source="core")
        assert key.reveal() not in wire(sent[-1]), url
        assert "authorization" not in sent[-1].headers

    await client.get_json("https://api.core.ac.uk/v3/x", source="core", auth=AuthUse.NONE)
    assert key.reveal() not in wire(sent[-1])


async def test_origin_match_ignores_case_and_default_port() -> None:
    """@spec SEC-8: the origin check compares scheme, host and port, not spelling."""
    key = make_secret("CORE_KEY")
    client, sent = client_for(ok, Resolver([CORE], {"core": key}))
    await client.get_json("https://API.Core.ac.uk:443/v3/x", source="core")
    assert sent[-1].headers["Authorization"] == f"Bearer {key.reveal()}"


async def test_download_never_carries_a_credential(tmp_path: Path) -> None:
    """@spec SEC-8: the downloader has no credential resolver, so a download sends no key."""
    key = make_secret("CORE_KEY")
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(
            200, content=b"%PDF-1.7 test", headers={"Content-Type": "application/pdf"}
        )

    class PublicResolver:
        async def resolve(self, host: str) -> list[str]:
            return ["93.184.216.34"]

    downloader = Downloader(
        PublicResolver(),
        DownloadPolicy(
            media_types=frozenset({"application/pdf"}), max_bytes=10_000, public_any=True
        ),
        tmp_path,
        transport_factory=lambda host, ip: httpx.MockTransport(handler),
    )
    await downloader.download("https://api.core.ac.uk/download/1.pdf")
    (request,) = sent
    assert key.reveal() not in wire(request)
    assert "authorization" not in request.headers


async def test_header_placement_keeps_key_out_of_url() -> None:
    """@spec SEC-9: with header placement (x-goog-api-key) the key is in no URL."""
    key = make_secret("GOOGLE_CSE_KEY")
    client, sent = client_for(ok, Resolver([GOOGLE], {"google_cse": key}))
    await client.get_json(
        "https://customsearch.googleapis.com/customsearch/v1",
        source="google_cse",
        params={"q": "graphs"},
    )
    (request,) = sent
    assert request.headers["x-goog-api-key"] == key.reveal()
    assert key.reveal() not in str(request.url)


@pytest.mark.parametrize("failure", ["status", "connect", "timeout"])
async def test_query_placement_url_kept_out_of_logs_and_errors(
    failure: str, caplog: pytest.LogCaptureFixture
) -> None:
    """@spec SEC-9: with query placement the URL, and so the key, reaches no log and no error."""
    key = make_secret("SERPAPI_KEY")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["api_key"] == key.reveal()
        if failure == "connect":
            raise httpx.ConnectError(f"cannot reach {request.url}", request=request)
        if failure == "timeout":
            raise httpx.ReadTimeout(f"timed out on {request.url}", request=request)
        return httpx.Response(500, text=f"echo {request.url}")

    client, _ = client_for(handler, Resolver([SERPAPI], {"serpapi": key}))
    caplog.set_level(logging.DEBUG, logger="research_mcp")
    with pytest.raises(HttpError) as caught:
        await client.get_json("https://serpapi.com/search", source="serpapi", params={"q": "z"})

    assert caught.value.__cause__ is None
    text = error_text(caught.value)
    logged = "\n".join(
        [record.getMessage() for record in caplog.records]
        + [repr(vars(record)) for record in caplog.records]
    )
    for blob in (text, logged):
        assert key.reveal() not in blob
        assert "serpapi.com/search" not in blob
        assert "api_key" not in blob


async def test_http_error_has_no_exception_text_query_or_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """@spec SEC-10: HttpError text holds no exception text, URL query or upstream body."""
    resolver = Resolver([CORE], {})
    caplog.set_level(logging.DEBUG, logger="research_mcp")
    url = "https://api.core.ac.uk/v3/search?q=private-query-text"

    cases: list[Handler] = [
        lambda request: httpx.Response(404, text="UPSTREAM-BODY-404 detail"),
        lambda request: httpx.Response(400, text="UPSTREAM-BODY-400 detail"),
        lambda request: httpx.Response(503, text="UPSTREAM-BODY-503 detail"),
    ]

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("EXCEPTION-TEXT socket said no", request=request)

    def garbled(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="UPSTREAM-BODY-JSON {not json")

    for handler in [*cases, broken, garbled]:
        client, _ = client_for(handler, resolver)
        with pytest.raises(HttpError) as caught:
            await client.get_json(url, source="core")
        error = caught.value
        assert str(error) == error.code.value
        assert error.code in {
            ErrorCode.NOT_FOUND,
            ErrorCode.UPSTREAM_ERROR,
        }
        assert error.__cause__ is None
        assert error.__suppress_context__ or error.__context__ is None
        text = error_text(error)
        for leak in ("UPSTREAM-BODY", "EXCEPTION-TEXT", "private-query-text", "q="):
            assert leak not in text

    logged = "\n".join(record.getMessage() + repr(vars(record)) for record in caplog.records)
    assert "private-query-text" not in logged
    assert "UPSTREAM-BODY" not in logged
    assert "EXCEPTION-TEXT" not in logged


async def test_blocked_host_error_names_no_url() -> None:
    """@spec SEC-10: a policy block names neither the host nor the query it refused."""
    client, sent = client_for(ok, Resolver([CORE], {}))
    with pytest.raises(HttpError) as caught:
        await client.get_json("https://attacker.test/x?token=abc", source="core")
    assert caught.value.code is ErrorCode.BLOCKED_BY_POLICY
    text = error_text(caught.value)
    assert "attacker.test" not in text
    assert "token=abc" not in text
    assert sent == []
