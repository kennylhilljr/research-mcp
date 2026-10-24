"""Shared setup for the source conformance suite (LLD-sources-v2 5.3).

``conformance_registry`` is the registry the suite is parametrized over: the adapters the
scan of ``research_mcp.sources`` finds, plus the fake adapter from
``research_mcp.testing.adapters``. ``Harness`` serves one fixture for every request through
an ``httpx.MockTransport``, with a ``FakeClock``, a ``FakeSleeper``, a fake contact address
and ``FakeProvider`` secrets, so no check reaches the network, the Keychain or a real clock.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from research_mcp.core.models import CallRecord
from research_mcp.platform.http import HttpClient
from research_mcp.platform.secrets import FakeProvider, SecretCache, SecretRef
from research_mcp.settings import Settings
from research_mcp.sources.base import SourceAdapter, SourceContext, SourceSpec
from research_mcp.sources.registry import RegisteredSource, SourceRegistry
from research_mcp.testing.adapters import FAKE_SPEC, FakeAdapter
from research_mcp.testing.clock import FakeClock, FakeSleeper

SOURCES_TESTS = Path(__file__).parent
CONTACT_EMAIL = "conformance@research-mcp.dev"
CONTENT_TYPES = {".json": "application/json", ".xml": "application/atom+xml"}


class OfflineSettings(Settings):
    """Settings from keyword arguments only: no config file, no environment."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


def conformance_registry() -> SourceRegistry:
    """Every registered adapter, built with default settings and every source available."""

    def no_context(spec: SourceSpec) -> SourceContext:
        raise AssertionError("the parametrizing registry never builds an adapter")

    return SourceRegistry(
        OfflineSettings(contact={"email": CONTACT_EMAIL}),
        no_context,
        has_credential=lambda name: True,
        has_extra=lambda extra: True,
        extra_adapters=[(FAKE_SPEC, FakeAdapter)],
    )


@dataclass(frozen=True)
class Fixture:
    name: str
    file_name: str
    content: bytes

    @property
    def content_type(self) -> str:
        return CONTENT_TYPES.get(Path(self.file_name).suffix, "application/octet-stream")


def fixture_folder(spec: SourceSpec) -> Path:
    """``tests/sources/<id>/fixtures``; an instance kind's instances share the kind's folder."""
    return SOURCES_TESTS / (spec.instance_of or spec.id) / "fixtures"


def load_fixtures(source: RegisteredSource) -> dict[str, Fixture]:
    """The seven fixtures of SRC-FR-8, in memory for the fake and on disk for the rest."""
    in_memory: Mapping[str, tuple[str, bytes]] | None = getattr(
        source.adapter_cls, "FIXTURES", None
    )
    if in_memory is not None:
        return {name: Fixture(name, *in_memory[name]) for name in in_memory}
    folder = fixture_folder(source.spec)
    found: dict[str, Fixture] = {}
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            name = path.name if path.name == "oversize.marker" else path.name.split(".")[0]
            if path.is_file():
                found[name] = Fixture(name, path.name, path.read_bytes())
    return found


def error_fixture(fixture: Fixture) -> tuple[int, dict[str, str], bytes]:
    """``err_429`` and ``err_5xx`` hold ``{"status", "headers", "body"?}`` as JSON."""
    data = json.loads(fixture.content)
    body = data.get("body", "")
    content = body.encode() if isinstance(body, str) else json.dumps(body).encode()
    return int(data["status"]), dict(data.get("headers", {})), content


class WireBody(httpx.AsyncByteStream):
    """A body that arrives unread, as from a network transport, so the byte cap applies."""

    def __init__(self, content: bytes) -> None:
        self.content = content

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.content

    async def aclose(self) -> None:
        return None


class CountingStream(httpx.AsyncByteStream):
    """A body far larger than the cap, counting the bytes the client actually pulled."""

    def __init__(self, total: int, chunk: int = 65_536) -> None:
        self.total = total
        self.chunk = chunk
        self.sent = 0

    async def __aiter__(self) -> AsyncIterator[bytes]:
        while self.sent < self.total:
            size = min(self.chunk, self.total - self.sent)
            self.sent += size
            yield b" " * size

    async def aclose(self) -> None:
        return None


@dataclass
class Sink:
    records: list[CallRecord] = field(default_factory=list)

    def record(self, call: CallRecord) -> None:
        self.records.append(call)


class Harness:
    """One adapter over a mock upstream that answers every request the same way."""

    def __init__(self, source: RegisteredSource) -> None:
        self.spec = source.spec
        self.clock = FakeClock(datetime(2026, 10, 23, 12, tzinfo=UTC))
        self.sleeper = FakeSleeper(self.clock)
        self.sink = Sink()
        self.requests: list[httpx.Request] = []
        self.respond: Any = lambda request: httpx.Response(500)
        self.settings = source.settings
        registry = SourceRegistry(
            OfflineSettings(contact={"email": CONTACT_EMAIL}),
            self._context,
            has_credential=lambda name: True,
            has_extra=lambda extra: True,
            clock=self.clock,
            modules=[],
            extra_adapters=[(source.spec, source.adapter_cls)],
        )
        self.http = HttpClient(
            registry,
            self._credentials(),
            self.sink,
            self.clock,
            self.sleeper,
            CONTACT_EMAIL,
            transport=httpx.MockTransport(self._handle),
        )
        self.adapter: SourceAdapter = source.adapter_cls(source.spec, self._context(source.spec))

    def _credentials(self) -> SecretCache:
        auth = self.spec.auth
        names = auth.secrets if auth is not None else ()
        provider = FakeProvider({name: f"fake-{name.lower()}" for name in names})
        refs = {name: SecretRef("keychain", name, f"research-mcp/{name}") for name in names}
        cache = SecretCache(provider, refs, {self.spec.id: names[0]} if names else {})
        cache.load()
        return cache

    def _context(self, spec: SourceSpec) -> SourceContext:
        return SourceContext(
            http=self.http,
            mcp=None,
            settings=self.settings,
            clock=self.clock,
            contact_email=CONTACT_EMAIL,
        )

    async def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response: httpx.Response = self.respond(request)
        return response

    def serve(self, fixture: Fixture) -> None:
        headers = {"content-type": fixture.content_type}
        self.respond = lambda request: httpx.Response(
            200, headers=headers, stream=WireBody(fixture.content)
        )

    @staticmethod
    def error_parts(fixture: Fixture) -> tuple[int, dict[str, str], bytes]:
        return error_fixture(fixture)

    def serve_error(self, fixture: Fixture) -> None:
        status, headers, content = error_fixture(fixture)
        self.respond = lambda request: httpx.Response(
            status, headers=headers, stream=WireBody(content)
        )

    def serve_stream(self, stream: CountingStream, content_type: str) -> None:
        self.respond = lambda request: httpx.Response(
            200, headers={"content-type": content_type}, stream=stream
        )

    async def aclose(self) -> None:
        await self.http.aclose()


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize ``registered_source`` over ``SourceRegistry.all()``; ``-k <id>`` picks one."""
    if "registered_source" in metafunc.fixturenames:
        sources = conformance_registry().all()
        metafunc.parametrize("registered_source", sources, ids=[s.spec.id for s in sources])


@pytest.fixture
def conformance() -> SourceRegistry:
    return conformance_registry()


@pytest.fixture
async def harness_for() -> AsyncIterator[Any]:
    """Build a ``Harness`` for a registered source; every one is closed after the test."""
    made: list[Harness] = []

    def build(source: RegisteredSource) -> Harness:
        made.append(Harness(source))
        return made[-1]

    yield build
    for harness in made:
        await harness.aclose()


@pytest.fixture
def fixtures_of() -> Any:
    return load_fixtures


@pytest.fixture
def counting_stream() -> type[CountingStream]:
    return CountingStream
