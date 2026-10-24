"""The in-memory MCP client against ``build_mcp``, with scripted sources (test plan v4).

Every source is a scripted adapter registered through ``extra_adapters``; no adapter
module is discovered and nothing reaches the network. ``Contract.connect`` runs the real
MCP session over the SDK's memory streams and keeps the initialize result, so the tests
see exactly what a client sees: the catalog, the instructions and each tool result.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

import anyio
import pytest
from mcp import types
from mcp.client.session import ClientSession
from mcp.shared.memory import create_client_server_memory_streams

from research_mcp.core.ids import Identifier
from research_mcp.core.models import Author, Provenance, SearchPage, SearchRequest, WorkRecord
from research_mcp.core.specs import RateSpec
from research_mcp.mcp_app.server import Services, build_mcp
from research_mcp.platform.redact import Redactor
from research_mcp.services.federation import FederationService
from research_mcp.services.works import WorksService
from research_mcp.settings import Settings, SourceSettings
from research_mcp.sources.base import Capability, SourceContext, SourceSpec
from research_mcp.sources.registry import SourceRegistry
from research_mcp.testing.clock import FakeClock

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
KEY = b"k" * 32
Search = Callable[[SearchRequest], Awaitable[SearchPage]]
Get = Callable[[Identifier], Awaitable[WorkRecord | None]]


class OfflineSettings(Settings):
    """Settings from keyword arguments only: no config file, no environment."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


def record(
    source: str,
    doi: str,
    *,
    authors: int = 1,
    abstract: str | None = None,
    title: str | None = None,
    year: int | None = 2024,
) -> WorkRecord:
    return WorkRecord(
        ids=[Identifier("doi", doi)],
        title=title or f"Work {doi}",
        authors=[Author(name=f"Author {n}", family=f"Family{n}") for n in range(authors)],
        year=year,
        abstract=abstract,
        provenance=Provenance(
            source=source, upstream_id=doi, adapter_version="1", retrieved_at=NOW
        ),
    )


def spec(id: str, **overrides: Any) -> SourceSpec:
    values: dict[str, Any] = {
        "id": id,
        "title": f"{id} source",
        "group": "scholarly",
        "capabilities": frozenset({Capability.SEARCH, Capability.GET}),
        "id_schemes": frozenset({"doi", "arxiv", "pmid"}),
        "hosts": frozenset({f"api.{id}.org"}),
        "auth": None,
        "rate": RateSpec(rps=5.0),
    }
    values.update(overrides)
    return SourceSpec(**values)


def page(*records: WorkRecord, next_cursor: str | None = None) -> Search:
    async def search(req: SearchRequest) -> SearchPage:
        return SearchPage(records=list(records), next_cursor=next_cursor)

    return search


async def nothing(ident: Identifier) -> WorkRecord | None:
    return None


@dataclass
class Session:
    client: ClientSession
    init: types.InitializeResult

    async def call(self, name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        return await self.client.call_tool(name, arguments)


def body(result: types.CallToolResult) -> dict[str, Any]:
    """The JSON object a tool result carries in its text content."""
    assert len(result.content) == 1
    block = result.content[0]
    assert isinstance(block, types.TextContent)
    return cast(dict[str, Any], json.loads(block.text))


class Contract:
    """Scripted sources, the services over them and an MCP session against ``build_mcp``.

    The helpers ride on the fixture because test modules cannot import this conftest.
    """

    record = staticmethod(record)
    spec = staticmethod(spec)
    page = staticmethod(page)
    body = staticmethod(body)

    def __init__(self) -> None:
        self.adapters: list[tuple[SourceSpec, type[Any]]] = []
        self.calls: list[tuple[str, str, Any]] = []
        self.redactor = Redactor()

    def add(self, source: SourceSpec, search: Search | None = None, get: Get = nothing) -> None:
        calls = self.calls
        search = search or page()

        class Scripted:
            def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
                self.spec = spec

            async def search(self, req: SearchRequest) -> SearchPage:
                calls.append((self.spec.id, "search", req))
                assert search is not None
                return await search(req)

            async def get(self, ident: Identifier) -> WorkRecord | None:
                calls.append((self.spec.id, "get", ident))
                return await get(ident)

        self.adapters.append((source, Scripted))

    def services(self, **settings: Any) -> Services:
        config = OfflineSettings(**settings)
        ctx = SourceContext(
            http=cast(Any, None),
            mcp=None,
            settings=SourceSettings(),
            clock=FakeClock(NOW),
            contact_email=None,
        )
        registry = SourceRegistry(
            config,
            lambda spec: ctx,
            has_credential=lambda name: False,
            clock=FakeClock(NOW),
            modules=[],
            extra_adapters=self.adapters,
        )
        return Services(
            settings=config,
            registry=registry,
            federation=FederationService(registry, config, KEY),
            works=WorksService(registry, config),
            redactor=self.redactor,
        )

    @asynccontextmanager
    async def connect(self, services: Services | None = None) -> AsyncIterator[Session]:
        mcp = build_mcp(services or self.services())
        server = mcp._mcp_server
        async with (
            create_client_server_memory_streams() as (client_streams, server_streams),
            anyio.create_task_group() as tasks,
        ):
            tasks.start_soon(
                lambda: server.run(
                    server_streams[0],
                    server_streams[1],
                    server.create_initialization_options(),
                    raise_exceptions=False,
                )
            )
            try:
                async with ClientSession(client_streams[0], client_streams[1]) as client:
                    init = await client.initialize()
                    yield Session(client, init)
            finally:
                tasks.cancel_scope.cancel()


@pytest.fixture
def contract() -> Contract:
    return Contract()
