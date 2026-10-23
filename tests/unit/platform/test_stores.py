"""Stores and migrations: Database, Migrator, StateStore and CacheStore."""

from __future__ import annotations

import asyncio
import re
import sqlite3
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiosqlite
import pytest

from research_mcp.core.models import CallRecord
from research_mcp.platform.stores import (
    CACHE_MIGRATIONS,
    STATE_MIGRATIONS,
    CacheStore,
    Database,
    JobRow,
    MigrationError,
    Migrator,
    SourceHealthRow,
    StateStore,
)

DOCS = Path(__file__).resolve().parents[3] / "docs"
T0 = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)


def sql_block(doc: Path, heading: str) -> str:
    """The first ```sql block after the heading line that starts with ``heading``."""
    text = doc.read_text(encoding="utf-8")
    start = text.index("\n" + heading)
    match = re.search(r"```sql\n(.*?)```", text[start:], re.DOTALL)
    assert match is not None, f"no sql block after {heading!r} in {doc.name}"
    return match.group(1)


def statements(script: str) -> list[str]:
    out: list[str] = []
    buf = ""
    for line in script.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            out.append(buf.strip())
            buf = ""
    return out


def expected_state_schema() -> str:
    """LLD-health-v2 3 (owner of state.db) with `searches` as LLD-search-v2 3 extends it."""
    health = statements(sql_block(DOCS / "lld/LLD-health-v2.md", "## 3. Data model"))
    searches = statements(sql_block(DOCS / "lld/LLD-search-v2.md", "## 3."))
    replaced = [searches[0] if s.startswith("CREATE TABLE searches") else s for s in health]
    return "\n".join(replaced)


def expected_cache_schema() -> str:
    return sql_block(DOCS / "lld/LLD-cache-v2.md", "### 3.1 `cache.db` schema")


def normalized(sql: str) -> str:
    """The statement without comments, with whitespace collapsed."""
    return " ".join(re.sub(r"--[^\n]*", "", sql).split())


def describe(conn: sqlite3.Connection) -> dict[str, object]:
    """Tables with their columns, foreign keys, constraints and indexes; triggers; FTS tables."""
    shape: dict[str, object] = {}
    objects = conn.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' "
        "AND name NOT LIKE 'chunks_fts_%' ORDER BY type, name"
    ).fetchall()
    for kind, name, sql in objects:
        if kind == "table":
            shape[f"table:{name}"] = {
                "columns": conn.execute(f"PRAGMA table_xinfo({name})").fetchall(),
                "foreign_keys": conn.execute(f"PRAGMA foreign_key_list({name})").fetchall(),
                "sql": normalized(sql),
            }
        elif kind == "index":
            shape[f"index:{name}"] = conn.execute(f"PRAGMA index_info({name})").fetchall()
        elif kind == "trigger":
            shape[f"trigger:{name}"] = normalized(sql)
    return shape


def reference(script: str) -> dict[str, object]:
    conn = sqlite3.connect(":memory:")
    try:
        for statement in statements(script):
            conn.execute(statement)
        return describe(conn)
    finally:
        conn.close()


def migrated(path: Path) -> dict[str, object]:
    conn = sqlite3.connect(path)
    try:
        return describe(conn)
    finally:
        conn.close()


@pytest.fixture
async def state_db(tmp_path: Path) -> AsyncIterator[Database]:
    db = Database(tmp_path / "state.db")
    await db.open(Migrator(STATE_MIGRATIONS))
    yield db
    await db.close()


@pytest.fixture
async def cache_db(tmp_path: Path) -> AsyncIterator[Database]:
    (tmp_path / "cache").mkdir()
    db = Database(tmp_path / "cache" / "cache.db")
    await db.open(Migrator(CACHE_MIGRATIONS))
    yield db
    await db.close()


def write_migrations(folder: Path, scripts: dict[str, str]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for name, body in scripts.items():
        (folder / name).write_text(body, encoding="utf-8")
    return folder


def user_version(path: Path) -> int:
    conn = sqlite3.connect(path)
    try:
        return int(conn.execute("PRAGMA user_version").fetchone()[0])
    finally:
        conn.close()


def table_names(path: Path) -> set[str]:
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


# PLAT-50


async def test_migrator_transaction_and_user_version(tmp_path: Path) -> None:
    """@spec PLAT-50: each script runs in an explicit BEGIN IMMEDIATE and COMMIT, a failing
    script leaves no partial schema, user_version is set for both databases, and SQLite older
    than 3.37 is refused."""
    for name, folder in (("state.db", STATE_MIGRATIONS), ("cache.db", CACHE_MIGRATIONS)):
        path = tmp_path / name
        db = Database(path)
        trace: list[str] = []
        await db.open(Migrator(folder), trace=trace.append)
        await db.close()
        latest = Migrator(folder).latest
        assert latest >= 1
        assert user_version(path) == latest
        begins = [s for s in trace if s.strip().upper().startswith("BEGIN")]
        commits = [s for s in trace if s.strip().upper() == "COMMIT"]
        assert begins == ["BEGIN IMMEDIATE"] * latest
        assert len(commits) == latest

    folder = write_migrations(
        tmp_path / "bad",
        {
            "0001_init.sql": "CREATE TABLE a (x INTEGER);\n",
            "0002_more.sql": "CREATE TABLE b (y INTEGER);\nCREATE TABLE c (z INTEGER;\n",
        },
    )
    path = tmp_path / "bad.db"
    db = Database(path)
    with pytest.raises(MigrationError, match="0002_more.sql"):
        await db.open(Migrator(folder))
    await db.close()
    assert table_names(path) == {"a"}
    assert user_version(path) == 1


async def test_migrator_refuses_old_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """@spec PLAT-50: the store refuses SQLite older than 3.37 before it touches the file."""
    monkeypatch.setattr(sqlite3, "sqlite_version_info", (3, 36, 9))
    monkeypatch.setattr(sqlite3, "sqlite_version", "3.36.9")
    path = tmp_path / "state.db"
    db = Database(path)
    with pytest.raises(MigrationError, match=r"3\.37"):
        await db.open(Migrator(STATE_MIGRATIONS))
    await db.close()
    assert not path.exists()


async def test_migrator_applies_only_new_scripts(tmp_path: Path) -> None:
    """@spec PLAT-50: a second open applies only scripts newer than user_version."""
    folder = write_migrations(tmp_path / "m", {"0001_init.sql": "CREATE TABLE a (x INTEGER);\n"})
    path = tmp_path / "x.db"
    db = Database(path)
    await db.open(Migrator(folder))
    await db.close()
    write_migrations(folder, {"0002_more.sql": "CREATE TABLE b (y INTEGER);\n"})
    db = Database(path)
    trace: list[str] = []
    await db.open(Migrator(folder), trace=trace.append)
    await db.close()
    assert table_names(path) == {"a", "b"}
    assert user_version(path) == 2
    assert not any("CREATE TABLE a" in s for s in trace)


def test_migrator_rejects_gaps_in_numbering(tmp_path: Path) -> None:
    """@spec PLAT-50: migration numbers start at 1 and have no gaps."""
    folder = write_migrations(
        tmp_path / "gap", {"0001_init.sql": "SELECT 1;\n", "0003_x.sql": "SELECT 1;\n"}
    )
    with pytest.raises(MigrationError, match="0002"):
        Migrator(folder)


# PLAT-51


async def test_newer_database_is_refused(tmp_path: Path) -> None:
    """@spec PLAT-51: a database whose user_version is newer than the newest migration fails
    to open with a clear error and is left unchanged."""
    path = tmp_path / "state.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE future (x INTEGER)")
    conn.execute("PRAGMA user_version = 99")
    conn.commit()
    conn.close()

    latest = Migrator(STATE_MIGRATIONS).latest
    db = Database(path)
    with pytest.raises(MigrationError) as info:
        await db.open(Migrator(STATE_MIGRATIONS))
    await db.close()
    message = str(info.value)
    assert "state.db" in message
    assert "99" in message
    assert str(latest) in message
    assert "newer" in message
    assert user_version(path) == 99
    assert table_names(path) == {"future"}


# PLAT-52


async def test_pragmas_and_serialized_writes(state_db: Database) -> None:
    """@spec PLAT-52: every connection uses WAL, foreign_keys=ON, busy_timeout=5000 and
    synchronous=NORMAL, and writes are serialized through one writer."""
    async with state_db.write() as conn:
        rows = [await (await conn.execute(f"PRAGMA {p}")).fetchone() for p in PRAGMAS]
        assert [r[0] if r else None for r in rows] == ["wal", 1, 5000, 1]
    async with state_db.read() as conn:
        rows = [await (await conn.execute(f"PRAGMA {p}")).fetchone() for p in PRAGMAS]
        assert [r[0] if r else None for r in rows] == ["wal", 1, 5000, 1]
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            await conn.execute("DELETE FROM schedule_runs")

    async with state_db.write() as conn:
        await conn.execute(
            "INSERT INTO schedule_runs (job, last_run_at, next_due_at) VALUES ('n', NULL, '0')"
        )

    active = 0
    peak = 0

    async def bump() -> None:
        nonlocal active, peak
        async with state_db.write() as conn:
            active += 1
            peak = max(peak, active)
            cur = await conn.execute("SELECT next_due_at FROM schedule_runs WHERE job = 'n'")
            row = await cur.fetchone()
            assert row is not None
            await asyncio.sleep(0)
            await conn.execute(
                "UPDATE schedule_runs SET next_due_at = ? WHERE job = 'n'", (str(int(row[0]) + 1),)
            )
            active -= 1

    await asyncio.gather(*(bump() for _ in range(25)))
    assert peak == 1
    async with state_db.read() as conn:
        cur = await conn.execute("SELECT next_due_at FROM schedule_runs WHERE job = 'n'")
        assert await cur.fetchone() == ("25",)


PRAGMAS = ("journal_mode", "foreign_keys", "busy_timeout", "synchronous")


async def test_failed_write_rolls_back(state_db: Database) -> None:
    """@spec PLAT-52: an exception inside a write block rolls the transaction back."""
    with pytest.raises(RuntimeError):
        async with state_db.write() as conn:
            await conn.execute(
                "INSERT INTO schedule_runs (job, last_run_at, next_due_at) VALUES ('r', NULL, 'x')"
            )
            raise RuntimeError("boom")
    async with state_db.read() as conn:
        cur = await conn.execute("SELECT count(*) FROM schedule_runs")
        assert await cur.fetchone() == (0,)


async def test_foreign_keys_enforced(cache_db: Database) -> None:
    """@spec PLAT-52: foreign_keys=ON rejects a row that points at no parent."""
    with pytest.raises(sqlite3.IntegrityError):
        async with cache_db.write() as conn:
            await conn.execute(
                "INSERT INTO identifiers VALUES ('doi', '10.1/x', '10.1/x', 'missing', 's', 't')"
            )


# PLAT-53


async def test_schemas_match_spec(state_db: Database, cache_db: Database) -> None:
    """@spec PLAT-53: the created state.db and cache.db schemas match the SPEC 8.1 and 10.1
    schemas held in LLD-health-v2 3, LLD-search-v2 3 and LLD-cache-v2 3.1."""
    assert migrated(state_db.path) == reference(expected_state_schema())
    assert migrated(cache_db.path) == reference(expected_cache_schema())


async def test_fts_triggers_keep_index_in_sync(cache_db: Database) -> None:
    """@spec PLAT-53: the external-content FTS table follows inserts, updates and deletes of
    chunks through triggers, and snippet() returns the chunk text."""
    async with cache_db.write() as conn:
        await insert_document(conn, "d1", state="cached")
        await conn.execute(
            "INSERT INTO files VALUES ('f1','d1','aa',1,'application/pdf',"
            "NULL,NULL,NULL,NULL,NULL,NULL,NULL,'t')"
        )
        await conn.execute("INSERT INTO extractions VALUES ('e1','f1','p','1','1',0,'t')")
        await conn.execute(
            "INSERT INTO chunks (chunk_id, extraction_id, doc_id, ord, section, title, content,"
            " content_sha256) VALUES (1, 'e1', 'd1', 0, 'Intro', 'Policy as code',"
            " 'Governance pipelines adopt policy engines.', 'h')"
        )

    async def search(term: str) -> list[tuple[int, str]]:
        async with cache_db.read() as conn:
            cur = await conn.execute(
                "SELECT rowid, snippet(chunks_fts, 0, '[', ']', '...', 8) FROM chunks_fts "
                "WHERE chunks_fts MATCH ?",
                (term,),
            )
            return [(int(r[0]), str(r[1])) for r in await cur.fetchall()]

    hits = await search("pipelines")
    assert hits == [(1, "Governance [pipelines] adopt policy engines.")]
    assert [h[0] for h in await search("title:policy")] == [1]
    assert [h[0] for h in await search("section:intro")] == [1]

    async with cache_db.write() as conn:
        await conn.execute("UPDATE chunks SET content = 'Rewritten body text.' WHERE chunk_id = 1")
    assert await search("pipelines") == []
    assert [h[0] for h in await search("rewritten")] == [1]

    async with cache_db.write() as conn:
        await conn.execute("DELETE FROM chunks WHERE chunk_id = 1")
    assert await search("rewritten") == []
    async with cache_db.write() as conn:
        await conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('integrity-check')")


async def insert_document(
    conn: aiosqlite.Connection, doc_id: str, *, state: str, **extra: object
) -> None:
    columns = {
        "doc_id": doc_id,
        "kind": "pdf",
        "source": "arxiv",
        "state": state,
        "cached_at": "2026-10-23T09:00:00+00:00",
        "fetch_recipe_json": "{}",
        **extra,
    }
    names = ", ".join(columns)
    marks = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO documents ({names}) VALUES ({marks})"  # noqa: S608 (test constants)
    await conn.execute(sql, tuple(columns.values()))


async def test_document_checks_and_collection_default(cache_db: Database) -> None:
    """@spec PLAT-53: CHECK constraints reject an archived document without archive_path and a
    discarded document without discarded_at, and a new collection does not pin its members."""
    for state, column, value in (
        ("archived", "archive_path", "/archive/2026/x.pdf"),
        ("discarded", "discarded_at", "2026-10-23T09:00:00+00:00"),
    ):
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            async with cache_db.write() as conn:
                await insert_document(conn, f"bad-{state}", state=state)
        async with cache_db.write() as conn:
            await insert_document(conn, f"ok-{state}", state=state, **{column: value})

    async with cache_db.write() as conn:
        await conn.execute("INSERT INTO collections (name, created_at) VALUES ('c', 't')")
    async with cache_db.read() as conn:
        cur = await conn.execute("SELECT pin_members FROM collections WHERE name = 'c'")
        assert await cur.fetchone() == (0,)
        cur = await conn.execute("SELECT pin_direct FROM documents WHERE doc_id = 'ok-archived'")
        assert await cur.fetchone() == (0,)


# StateStore and CacheStore methods M0 needs (LLD-platform-v2 3.1)


def call(source: str, offset: int) -> CallRecord:
    return CallRecord(
        ts=T0 + timedelta(seconds=offset),
        source=source,
        op="search",
        status=200,
        error_code=None,
        latency_ms=12,
        bytes=345,
        rl_remaining="9/10",
        rl_reset=None,
        cred_expires_at=None,
        correlation_id="c1",
        attempt=1,
    )


async def test_record_call_buffers_until_flush(state_db: Database) -> None:
    """record_call buffers in memory; flush writes the batch and returns it."""
    store = StateStore(state_db)
    store.record_call(call("arxiv", 0))
    store.record_call(call("crossref", 1))
    async with state_db.read() as conn:
        cur = await conn.execute("SELECT count(*) FROM calls")
        assert await cur.fetchone() == (0,)
    flushed = await store.flush()
    assert [c.source for c in flushed] == ["arxiv", "crossref"]
    assert await store.flush() == []
    async with state_db.read() as conn:
        cur = await conn.execute("SELECT ts, source, status, rl_remaining, attempt FROM calls")
        assert await cur.fetchall() == [
            ("2026-10-23T09:00:00+00:00", "arxiv", 200, "9/10", 1),
            ("2026-10-23T09:00:01+00:00", "crossref", 200, "9/10", 1),
        ]


async def test_jobs_round_trip(state_db: Database) -> None:
    """job_insert, job_update, job_get and job_list keep the jobs table typed."""
    store = StateStore(state_db)
    job = JobRow(
        job_id="01J0000000000000000000000A",
        kind="reindex",
        state="pending",
        params_json='{"a": 1}',
        created_at=T0,
        updated_at=T0,
    )
    await store.job_insert(job)
    assert await store.job_get(job.job_id) == job
    later = T0 + timedelta(minutes=1)
    await store.job_update(job.job_id, state="running", progress=0.5, updated_at=later)
    got = await store.job_get(job.job_id)
    assert got is not None
    assert (got.state, got.progress, got.updated_at) == ("running", 0.5, later)
    assert [j.job_id for j in await store.job_list()] == [job.job_id]
    assert [j.job_id for j in await store.job_list(state="running")] == [job.job_id]
    assert await store.job_list(state="failed") == []
    assert await store.job_get("missing") is None
    with pytest.raises(ValueError, match="job_id"):
        await store.job_update(job.job_id, job_id="other")
    with pytest.raises(ValueError, match="nope"):
        await store.job_update(job.job_id, nope=1)
    with pytest.raises(KeyError):
        await store.job_update("missing", state="running")


async def test_schedule_round_trip(state_db: Database) -> None:
    """schedule_set upserts the job's run times; schedule_get reads them back."""
    store = StateStore(state_db)
    assert await store.schedule_get("review") is None
    await store.schedule_set("review", None, T0)
    row = await store.schedule_get("review")
    assert row is not None
    assert (row.job, row.last_run_at, row.next_due_at) == ("review", None, T0)
    await store.schedule_set("review", T0, T0 + timedelta(days=1))
    row = await store.schedule_get("review")
    assert row is not None
    assert (row.last_run_at, row.next_due_at) == (T0, T0 + timedelta(days=1))


async def test_source_health_round_trip(state_db: Database) -> None:
    """source_health_put upserts one row per source; get and list read them back."""
    store = StateStore(state_db)
    row = SourceHealthRow(source="arxiv", state="ok", updated_at=T0)
    await store.source_health_put(row)
    assert await store.source_health_get("arxiv") == row
    changed = row.model_copy(update={"state": "down", "consecutive_failures": 3})
    await store.source_health_put(changed)
    await store.source_health_put(SourceHealthRow(source="crossref", state="ok", updated_at=T0))
    assert await store.source_health_get("arxiv") == changed
    assert [r.source for r in await store.source_health_list()] == ["arxiv", "crossref"]
    assert await store.source_health_get("missing") is None


async def test_outbox_drain_reads_oldest_first_then_deletes(cache_db: Database) -> None:
    """outbox_drain returns the oldest rows up to the limit; outbox_delete removes them."""
    async with cache_db.write() as conn:
        for i in range(3):
            await conn.execute(
                "INSERT INTO outbox (ts, kind, payload_json) VALUES (?, 'transition', ?)",
                (f"2026-10-23T09:00:0{i}+00:00", f'{{"i": {i}}}'),
            )
    store = CacheStore(cache_db)
    rows = await store.outbox_drain(2)
    assert [r.payload_json for r in rows] == ['{"i": 0}', '{"i": 1}']
    assert rows[0].ts == T0
    assert await store.outbox_drain(10) == [*rows, *(await store.outbox_drain(10))[2:]]
    await store.outbox_delete([r.outbox_id for r in rows])
    remaining = await store.outbox_drain(10)
    assert [r.payload_json for r in remaining] == ['{"i": 2}']


def test_naive_datetimes_are_rejected() -> None:
    """Stored times are UTC: a naive datetime is refused."""
    with pytest.raises(ValueError, match="timezone"):
        SourceHealthRow(source="arxiv", state="ok", updated_at=datetime(2026, 1, 1))
