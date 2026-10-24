"""Grouping, merging and ``get_work`` (LLD-search-v2 5.3).

Every source is a scripted in-memory adapter registered through ``extra_adapters``; no
adapter module is discovered and nothing reaches the network.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from research_mcp.core.errors import ErrorCode, HttpError, ToolError
from research_mcp.core.ids import Identifier, IdentifierError
from research_mcp.core.models import Author, OaLocation, Provenance, WorkRecord
from research_mcp.core.specs import RateSpec
from research_mcp.services.works import Group, WorkLookupError, WorksService, group, merge
from research_mcp.settings import Settings, SourceSettings
from research_mcp.sources.base import Capability, SourceContext, SourceSpec
from research_mcp.sources.registry import SourceRegistry
from research_mcp.testing.clock import FakeClock

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
Get = Callable[[Identifier], Awaitable[WorkRecord | None]]


class OfflineSettings(Settings):
    """Settings from keyword arguments only: no config file, no environment."""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Any, init_settings: Any, **rest: Any
    ) -> tuple[Any, ...]:
        return (init_settings,)


def rec(
    source: str,
    uid: str,
    title: str,
    *ids: tuple[str, str],
    year: int | None = None,
    authors: tuple[str, ...] = (),
    oa: tuple[str, ...] = (),
    retracted: bool | None = None,
    venue: str | None = None,
) -> WorkRecord:
    return WorkRecord(
        ids=[Identifier(scheme, value) for scheme, value in ids],
        title=title,
        year=year,
        venue=venue,
        authors=[Author(name=name, family=name.split()[-1]) for name in authors],
        oa_locations=[OaLocation(url=url, source=source, kind="pdf") for url in oa],
        is_retracted=retracted,
        provenance=Provenance(
            source=source, upstream_id=uid, adapter_version="1", retrieved_at=NOW
        ),
    )


def spec(id: str, *schemes: str, capabilities: frozenset[Capability] | None = None) -> SourceSpec:
    return SourceSpec(
        id=id,
        title=f"{id} source",
        group="scholarly",
        capabilities=capabilities or frozenset({Capability.SEARCH, Capability.GET}),
        id_schemes=frozenset(schemes),
        hosts=frozenset({f"api.{id}.org"}),
        auth=None,
        rate=RateSpec(rps=5.0),
    )


class Harness:
    """A registry of scripted sources that records every ``get`` it receives."""

    def __init__(self) -> None:
        self.adapters: list[tuple[SourceSpec, type[Any]]] = []
        self.calls: list[tuple[str, Identifier]] = []

    def add(self, source: SourceSpec, get: Get) -> None:
        calls = self.calls

        class Scripted:
            def __init__(self, spec: SourceSpec, ctx: SourceContext) -> None:
                self.spec = spec

            async def get(self, ident: Identifier) -> WorkRecord | None:
                calls.append((self.spec.id, ident))
                return await get(ident)

        self.adapters.append((source, Scripted))

    def service(self, **settings: Any) -> WorksService:
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
            modules=[],
            extra_adapters=self.adapters,
        )
        return WorksService(registry, config)


def returns(record: WorkRecord | None) -> Get:
    async def get(ident: Identifier) -> WorkRecord | None:
        return record

    return get


def test_shared_identifier_merges() -> None:
    """@spec SRCH-4: records sharing any identifier become one work listing every source."""
    records = [
        rec("crossref", "c1", "Attention", ("doi", "10.1/att")),
        rec("other", "x1", "Unrelated paper", ("doi", "10.1/other")),
        rec("openalex", "o1", "Attention", ("doi", "10.1/att"), ("openalex", "W1")),
        # Shares only the OpenAlex id with the second record: the merge is transitive.
        rec("arxiv", "a1", "Attention", ("openalex", "W1"), ("arxiv", "1706.03762")),
    ]
    groups = group(records)
    assert [len(g.records) for g in groups] == [3, 1]
    work = merge(groups[0])
    assert work.found_in == ["crossref", "openalex", "arxiv"]
    assert [(i.scheme, i.value) for i in work.ids] == [
        ("doi", "10.1/att"),
        ("openalex", "W1"),
        ("arxiv", "1706.03762"),
    ]
    assert work.fuzzy is False
    assert merge(groups[1]).found_in == ["other"]


def test_shared_identifier_ignores_arxiv_version() -> None:
    """@spec SRCH-4: two versions of one arXiv id are one shared identifier."""
    first = rec("arxiv", "a1", "T", ("arxiv", "2410.18291"))
    second = rec("openalex", "o1", "T", ("doi", "10.1/x"))
    second.ids.append(Identifier("arxiv", "2410.18291", 2))
    assert len(group([first, second])) == 1


def test_fuzzy_merge_flagged() -> None:
    """@spec SRCH-5: records matching on title, year and first author merge and are fuzzy."""
    records = [
        rec(
            "crossref",
            "c1",
            "The Deep Learning Survey",
            ("doi", "10.1/a"),
            year=2020,
            authors=("Ada Lovelace", "Alan Turing"),
        ),
        rec(
            "arxiv",
            "a1",
            "Deep learning survey!",
            ("arxiv", "2001.00001"),
            year=2020,
            authors=("A. Lovelace",),
        ),
        # Same title and author, another year: a different work.
        rec(
            "dblp",
            "d1",
            "Deep learning survey",
            ("dblp", "x"),
            year=2021,
            authors=("Ada Lovelace",),
        ),
        # Same title and year, another first author.
        rec(
            "core",
            "k1",
            "Deep learning survey",
            ("core", "9"),
            year=2020,
            authors=("Grace Hopper",),
        ),
    ]
    groups = group(records)
    assert [(len(g.records), g.fuzzy) for g in groups] == [(2, True), (1, False), (1, False)]
    work = merge(groups[0])
    assert work.fuzzy is True
    assert work.found_in == ["crossref", "arxiv"]

    # With federation.fuzzy_merge off, only shared identifiers merge (LLD-search-v2 7.2).
    assert [len(g.records) for g in group(records, fuzzy=False)] == [1, 1, 1, 1]


def test_fuzzy_merge_needs_every_key() -> None:
    """@spec SRCH-5: a record without a year or an author never merges on title alone."""
    records = [
        rec("crossref", "c1", "Same title", ("doi", "10.1/a")),
        rec("arxiv", "a1", "Same title", ("arxiv", "2001.00001")),
    ]
    assert [len(g.records) for g in group(records)] == [1, 1]


def test_conflicts_recorded_with_sources() -> None:
    """@spec SRCH-9: disagreeing title, year and retraction status are kept per source."""
    records = [
        rec(
            "openalex",
            "o1",
            "A study of things",
            ("doi", "10.1/a"),
            year=2019,
            retracted=True,
            venue="OpenAlex Venue",
        ),
        rec(
            "crossref",
            "c1",
            "A Study of Things: Revisited",
            ("doi", "10.1/a"),
            year=2020,
            retracted=False,
        ),
        rec("arxiv", "a1", "A study of things.", ("doi", "10.1/a")),
    ]
    work = merge(Group(records))
    # Fields come by source priority: crossref first, then openalex, then the rest.
    assert work.title == "A Study of Things: Revisited"
    assert work.year == 2020
    assert work.venue == "OpenAlex Venue"
    conflicts = {c.field: c.values for c in work.conflicts}
    assert conflicts == {
        "title": {
            "crossref": "A Study of Things: Revisited",
            "openalex": "A study of things",
            "arxiv": "A study of things.",
        },
        "year": {"crossref": 2020, "openalex": 2019},
        "is_retracted": {"crossref": False, "openalex": True},
    }


def test_no_conflict_when_sources_agree() -> None:
    """@spec SRCH-9: titles equal up to case and punctuation are not a disagreement."""
    records = [
        rec("crossref", "c1", "A Study of Things", ("doi", "10.1/a"), year=2020),
        rec("openalex", "o1", "A study of things.", ("doi", "10.1/a"), year=2020),
    ]
    assert merge(Group(records)).conflicts == []


async def test_get_work_merges_and_lists_oa() -> None:
    """@spec SRCH-17: get_work merges every source that understands the id and lists OA."""
    harness = Harness()
    harness.add(
        spec("crossref", "doi"),
        returns(
            rec(
                "crossref", "c1", "Paper", ("doi", "10.1234/abc"), oa=("https://pub.example/a.pdf",)
            )
        ),
    )
    harness.add(
        spec("openalex", "doi", "openalex"),
        returns(
            rec(
                "openalex",
                "W9",
                "Paper",
                ("doi", "10.1234/abc"),
                ("openalex", "W9"),
                oa=("https://repo.example/a.pdf", "https://pub.example/a.pdf"),
            )
        ),
    )
    harness.add(spec("arxiv", "arxiv"), returns(rec("arxiv", "a", "Paper", ("arxiv", "1"))))
    harness.add(
        spec("searchonly", "doi", capabilities=frozenset({Capability.SEARCH})),
        returns(None),
    )
    harness.add(spec("missing", "doi"), returns(None))

    async def broken(ident: Identifier) -> WorkRecord | None:
        raise HttpError(ErrorCode.UPSTREAM_ERROR, status=503)

    harness.add(spec("brokensrc", "doi"), broken)

    work, statuses = await harness.service().get_work("https://doi.org/10.1234/ABC")

    called = sorted(source for source, _ in harness.calls)
    assert called == ["brokensrc", "crossref", "missing", "openalex"]
    assert {ident for _, ident in harness.calls} == {Identifier("doi", "10.1234/abc")}
    assert work.found_in == ["crossref", "openalex"]
    assert [loc.url for loc in work.oa_locations] == [
        "https://pub.example/a.pdf",
        "https://repo.example/a.pdf",
    ]
    states = {s.source: (s.state, s.count, s.error_code) for s in statuses}
    assert states == {
        "brokensrc": ("error", 0, ErrorCode.UPSTREAM_ERROR),
        "crossref": ("ok", 1, None),
        "missing": ("empty", 0, None),
        "openalex": ("ok", 1, None),
    }


async def test_get_work_reports_skipped_sources() -> None:
    """@spec SRCH-17: a disabled source that understands the id gets a status, not a call."""
    harness = Harness()
    harness.add(spec("crossref", "doi"), returns(rec("crossref", "c", "P", ("doi", "10.1234/a"))))
    harness.add(spec("offline", "doi"), returns(None))
    service = harness.service(sources={"offline": {"enabled": False}})
    work, statuses = await service.get_work("doi:10.1234/a")
    assert [source for source, _ in harness.calls] == ["crossref"]
    assert {s.source: s.state for s in statuses} == {"crossref": "ok", "offline": "disabled"}
    assert work.found_in == ["crossref"]


async def test_get_work_not_found_and_bad_id() -> None:
    """@spec SRCH-17: no record from any source is not_found; a bad id never calls a source."""
    harness = Harness()
    harness.add(spec("crossref", "doi"), returns(None))
    service = harness.service()
    with pytest.raises(ToolError) as caught:
        await service.get_work("10.1234/none")
    assert caught.value.code is ErrorCode.NOT_FOUND
    harness.calls.clear()
    with pytest.raises(IdentifierError):
        await service.get_work("doi_10.1145_3649835")
    assert harness.calls == []


async def test_get_work_outage_is_not_not_found() -> None:
    """@spec SRCH-17: when no source answers, get_work fails as upstream and keeps statuses."""
    harness = Harness()

    async def broken(ident: Identifier) -> WorkRecord | None:
        raise HttpError(ErrorCode.UPSTREAM_ERROR, status=503)

    harness.add(spec("crossref", "doi"), broken)
    harness.add(spec("offline", "doi"), returns(None))
    service = harness.service(sources={"offline": {"enabled": False}})
    with pytest.raises(WorkLookupError) as caught:
        await service.get_work("10.1234/down")
    assert caught.value.code is ErrorCode.UPSTREAM_ERROR
    assert caught.value.retryable
    assert {s.source: s.state for s in caught.value.statuses} == {
        "crossref": "error",
        "offline": "disabled",
    }

    # One source that answers without a record makes it not_found; the statuses stay.
    with pytest.raises(WorkLookupError) as caught:
        await harness.service().get_work("10.1234/down")
    assert caught.value.code is ErrorCode.NOT_FOUND
    assert {s.source: s.state for s in caught.value.statuses} == {
        "crossref": "error",
        "offline": "empty",
    }
