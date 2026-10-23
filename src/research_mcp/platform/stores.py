"""SQLite stores: Database (aiosqlite), Migrator, StateStore and CacheStore.

No SQL appears outside this module and the ``services/*`` repositories (SEC-INV-8). Every
connection runs in autocommit mode, so each transaction is the explicit ``BEGIN IMMEDIATE``
and ``COMMIT`` issued here (LLD-platform-v2 3.1).
"""

from __future__ import annotations

import asyncio
import re
import sqlite3
from collections.abc import AsyncIterator, Callable, Iterable, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

import aiosqlite
from pydantic import BaseModel, ConfigDict, field_validator

from research_mcp.core.models import CallRecord

MIN_SQLITE_VERSION = (3, 37, 0)
BUSY_TIMEOUT_MS = 5000

# @spec PLAT-53
STATE_MIGRATIONS = Path(__file__).with_name("migrations") / "state"
CACHE_MIGRATIONS = Path(__file__).with_name("migrations") / "cache"

_SCRIPT_NAME = re.compile(r"(\d{4})_[a-z0-9_]+\.sql")
_CONNECTION_PRAGMAS = (
    "PRAGMA journal_mode = WAL",
    "PRAGMA foreign_keys = ON",
    f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}",
    "PRAGMA synchronous = NORMAL",
)


class MigrationError(RuntimeError):
    """A database cannot be opened at the schema this code expects."""


# @spec PLAT-50
def check_sqlite_version() -> None:
    if sqlite3.sqlite_version_info < MIN_SQLITE_VERSION:
        raise MigrationError(
            f"SQLite {sqlite3.sqlite_version} is too old; research-mcp needs SQLite 3.37 or later"
        )


def split_statements(script: str) -> list[str]:
    """Split a script into single statements without ``executescript``, which commits."""
    statements: list[str] = []
    pending = ""
    pieces = script.split(";")
    for index, piece in enumerate(pieces):
        pending += piece if index == len(pieces) - 1 else piece + ";"
        if sqlite3.complete_statement(pending):
            statements.append(pending.strip())
            pending = ""
    if re.sub(r"--[^\n]*", "", pending).strip():
        raise MigrationError(f"incomplete statement at the end of the script: {pending.strip()!r}")
    return statements


async def _run(conn: aiosqlite.Connection, sql: str, params: Sequence[Any] = ()) -> None:
    cursor = await conn.execute(sql, params)
    await cursor.close()


async def _scalar(conn: aiosqlite.Connection, sql: str) -> Any:
    cursor = await conn.execute(sql)
    row = await cursor.fetchone()
    await cursor.close()
    return None if row is None else row[0]


class Migrator:
    """Applies ``migrations/<db>/NNNN_*.sql`` in order, one transaction per script."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.scripts = self._discover(directory)

    @property
    def latest(self) -> int:
        return len(self.scripts)

    @staticmethod
    def _discover(directory: Path) -> list[Path]:
        scripts = sorted(directory.glob("*.sql"))
        for expected, script in enumerate(scripts, start=1):
            match = _SCRIPT_NAME.fullmatch(script.name)
            if match is None or int(match.group(1)) != expected:
                raise MigrationError(
                    f"{directory}: expected migration {expected:04d}_*.sql, found {script.name}"
                )
        return scripts

    # @spec PLAT-50, PLAT-51
    async def apply(self, conn: aiosqlite.Connection, label: str) -> int:
        """Bring the database to ``latest``; refuse one whose schema is newer."""
        current = int(await _scalar(conn, "PRAGMA user_version"))
        self._refuse_newer(current, label)
        for version in range(current + 1, self.latest + 1):
            script = self.scripts[version - 1]
            statements = split_statements(script.read_text(encoding="utf-8"))
            await _run(conn, "BEGIN IMMEDIATE")
            try:
                # Another process may have migrated while this one waited for the lock.
                found = int(await _scalar(conn, "PRAGMA user_version"))
                self._refuse_newer(found, label)
                if found < version:
                    for statement in statements:
                        await _run(conn, statement)
                    await _run(conn, f"PRAGMA user_version = {version}")
                await _run(conn, "COMMIT")
            except sqlite3.Error as exc:
                if conn.in_transaction:
                    await _run(conn, "ROLLBACK")
                raise MigrationError(f"{label}: migration {script.name} failed: {exc}") from exc
            except BaseException:
                if conn.in_transaction:
                    await _run(conn, "ROLLBACK")
                raise
        return max(current, self.latest)

    def _refuse_newer(self, version: int, label: str) -> None:
        if version > self.latest:
            raise MigrationError(
                f"{label} has schema version {version}, newer than this version of research-mcp "
                f"supports ({self.latest}); upgrade research-mcp or restore a backup"
            )


# @spec PLAT-52
class Database:
    """One writer connection behind an ``asyncio.Lock`` and a small pool of readers."""

    def __init__(self, path: Path, *, readers: int = 2) -> None:
        if readers < 1:
            raise ValueError("readers must be at least 1")
        self.path = path
        self._reader_count = readers
        self._writer: aiosqlite.Connection | None = None
        self._readers: asyncio.Queue[aiosqlite.Connection] = asyncio.Queue()
        self._open_readers: list[aiosqlite.Connection] = []
        self._write_lock = asyncio.Lock()

    async def open(self, migrator: Migrator, *, trace: Callable[[str], None] | None = None) -> None:
        check_sqlite_version()
        try:
            self._writer = await self._connect(trace)
            await migrator.apply(self._writer, self.path.name)
            for _ in range(self._reader_count):
                reader = await self._connect(None)
                await _run(reader, "PRAGMA query_only = ON")
                self._open_readers.append(reader)
                self._readers.put_nowait(reader)
        except BaseException:
            await self.close()
            raise

    async def _connect(self, trace: Callable[[str], None] | None) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.path, isolation_level=None)
        try:
            if trace is not None:
                await conn.set_trace_callback(trace)
            for pragma in _CONNECTION_PRAGMAS:
                await _run(conn, pragma)
            mode = await _scalar(conn, "PRAGMA journal_mode")
            if str(mode).lower() != "wal":
                raise MigrationError(f"{self.path.name}: cannot enable WAL (journal_mode={mode})")
        except BaseException:
            await conn.close()
            raise
        return conn

    async def close(self) -> None:
        connections = [*self._open_readers, *([self._writer] if self._writer else [])]
        self._open_readers = []
        self._readers = asyncio.Queue()
        self._writer = None
        for conn in connections:
            await conn.close()

    @asynccontextmanager
    async def write(self) -> AsyncIterator[aiosqlite.Connection]:
        """One serialized ``BEGIN IMMEDIATE`` transaction; an exception rolls it back."""
        if self._writer is None:
            raise RuntimeError(f"{self.path.name} is not open")
        conn = self._writer
        async with self._write_lock:
            await _run(conn, "BEGIN IMMEDIATE")
            try:
                yield conn
                await _run(conn, "COMMIT")
            except BaseException:
                if conn.in_transaction:
                    await _run(conn, "ROLLBACK")
                raise

    @asynccontextmanager
    async def read(self) -> AsyncIterator[aiosqlite.Connection]:
        """A read-only connection from the pool."""
        if not self._open_readers:
            raise RuntimeError(f"{self.path.name} is not open")
        conn = await self._readers.get()
        try:
            yield conn
        finally:
            self._readers.put_nowait(conn)


def _to_db(value: Any) -> Any:
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, bool):
        return int(value)
    return value


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("stored times need a timezone")
    return value.astimezone(UTC).isoformat()


class _Row(BaseModel):
    model_config = ConfigDict(frozen=True, defer_build=True)

    @field_validator("*", mode="after")
    @classmethod
    def _utc(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("stored times need a timezone")
            return value.astimezone(UTC)
        return value

    @classmethod
    def columns(cls) -> list[str]:
        return list(cls.model_fields)

    @classmethod
    def from_db(cls, row: Iterable[Any]) -> Self:
        return cls.model_validate(dict(zip(cls.columns(), row, strict=True)))

    def to_db(self) -> tuple[Any, ...]:
        return tuple(_to_db(getattr(self, name)) for name in self.columns())


JobState = Literal["pending", "running", "succeeded", "failed", "cancelled"]


class JobRow(_Row):
    """A row of ``state.db.jobs``."""

    job_id: str
    kind: str
    state: JobState
    params_json: str
    progress: float = 0.0
    cursor: str | None = None
    result_json: str | None = None
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class ScheduleRow(_Row):
    """A row of ``state.db.schedule_runs``."""

    job: str
    last_run_at: datetime | None
    next_due_at: datetime


class SourceHealthRow(_Row):
    """A row of ``state.db.source_health`` (column meanings in LLD-health-v2 3)."""

    source: str
    state: str
    reason: str | None = None
    fix_hint: str | None = None
    last_probe_at: datetime | None = None
    last_probe_ok: bool | None = None
    consecutive_failures: int = 0
    rate_limited_until: datetime | None = None
    budget_reset_at: datetime | None = None
    quota_remaining: str | None = None
    quota_reset: str | None = None
    baseline_p95_ms: int | None = None
    calls_today: int = 0
    api_version_seen: str | None = None
    enabled: bool = True
    updated_at: datetime


class OutboxRow(_Row):
    """A row of ``cache.db.outbox``: a transfer queue to ``state.db.review_events``."""

    outbox_id: int
    ts: datetime
    kind: str
    payload_json: str


def _select(row: type[_Row], table: str) -> str:
    return f"SELECT {', '.join(row.columns())} FROM {table}"  # noqa: S608 (names are constants)


def _insert(row: type[_Row], table: str, verb: str = "INSERT") -> str:
    names = row.columns()
    marks = ", ".join("?" for _ in names)
    return f"{verb} INTO {table} ({', '.join(names)}) VALUES ({marks})"


_CALL_COLUMNS = list(CallRecord.model_fields)
_INSERT_CALL = (
    f"INSERT INTO calls ({', '.join(_CALL_COLUMNS)}) "  # noqa: S608 (names are model fields)
    f"VALUES ({', '.join('?' for _ in _CALL_COLUMNS)})"
)


class StateStore:
    """Typed access to ``state.db`` for the methods M0 needs (LLD-platform-v2 3.1)."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self._calls: list[CallRecord] = []

    def record_call(self, call: CallRecord) -> None:
        """Buffer one call record; ``flush`` writes the buffer."""
        self._calls.append(call)

    async def flush(self) -> list[CallRecord]:
        """Write the buffered calls in one transaction and return them.

        A failed write drops the batch and raises, so a broken store cannot grow the buffer.
        """
        batch, self._calls = self._calls, []
        if batch:
            rows = [tuple(_to_db(getattr(c, name)) for name in _CALL_COLUMNS) for c in batch]
            async with self.db.write() as conn:
                await conn.executemany(_INSERT_CALL, rows)
        return batch

    async def job_insert(self, job: JobRow) -> None:
        async with self.db.write() as conn:
            await _run(conn, _insert(JobRow, "jobs"), job.to_db())

    async def job_update(self, job_id: str, /, **fields: Any) -> JobRow:
        """Change the named columns of one job and return the new row."""
        unknown = sorted(set(fields) - (set(JobRow.columns()) - {"job_id"}))
        if unknown:
            raise ValueError(f"not an updatable jobs column: {', '.join(unknown)}")
        async with self.db.write() as conn:
            cursor = await conn.execute(_select(JobRow, "jobs") + " WHERE job_id = ?", (job_id,))
            found = await cursor.fetchone()
            await cursor.close()
            if found is None:
                raise KeyError(job_id)
            updated = JobRow.model_validate({**JobRow.from_db(found).model_dump(), **fields})
            if fields:
                assignments = ", ".join(f"{name} = ?" for name in fields)
                values = [_to_db(getattr(updated, name)) for name in fields]
                await _run(
                    conn,
                    f"UPDATE jobs SET {assignments} WHERE job_id = ?",  # noqa: S608 (checked names)
                    (*values, job_id),
                )
        return updated

    async def job_get(self, job_id: str) -> JobRow | None:
        rows = await self._fetch(JobRow, "jobs", " WHERE job_id = ?", (job_id,))
        return rows[0] if rows else None

    async def job_list(self, state: JobState | None = None) -> list[JobRow]:
        if state is None:
            return await self._fetch(JobRow, "jobs", " ORDER BY created_at, job_id")
        return await self._fetch(
            JobRow, "jobs", " WHERE state = ? ORDER BY created_at, job_id", (state,)
        )

    async def schedule_get(self, job: str) -> ScheduleRow | None:
        rows = await self._fetch(ScheduleRow, "schedule_runs", " WHERE job = ?", (job,))
        return rows[0] if rows else None

    async def schedule_set(
        self, job: str, last_run_at: datetime | None, next_due_at: datetime
    ) -> None:
        row = ScheduleRow(job=job, last_run_at=last_run_at, next_due_at=next_due_at)
        async with self.db.write() as conn:
            await _run(
                conn, _insert(ScheduleRow, "schedule_runs", "INSERT OR REPLACE"), row.to_db()
            )

    async def source_health_get(self, source: str) -> SourceHealthRow | None:
        rows = await self._fetch(SourceHealthRow, "source_health", " WHERE source = ?", (source,))
        return rows[0] if rows else None

    async def source_health_list(self) -> list[SourceHealthRow]:
        return await self._fetch(SourceHealthRow, "source_health", " ORDER BY source")

    async def source_health_put(self, row: SourceHealthRow) -> None:
        async with self.db.write() as conn:
            await _run(
                conn, _insert(SourceHealthRow, "source_health", "INSERT OR REPLACE"), row.to_db()
            )

    async def _fetch[R: _Row](
        self, row: type[R], table: str, where: str, params: Sequence[Any] = ()
    ) -> list[R]:
        return await _fetch_rows(self.db, row, table, where, params)


class CacheStore:
    """Typed access to ``cache.db``; M2 adds the ``services/*`` repositories."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def outbox_drain(self, limit: int) -> list[OutboxRow]:
        """The oldest outbox rows, up to ``limit``. Rows stay until ``outbox_delete``, so the
        drainer copies them to ``state.db.review_events`` before they are removed."""
        if limit < 1:
            raise ValueError("limit must be at least 1")
        return await _fetch_rows(
            self.db, OutboxRow, "outbox", " ORDER BY outbox_id LIMIT ?", (limit,)
        )

    async def outbox_delete(self, outbox_ids: Iterable[int]) -> None:
        ids = [(int(i),) for i in outbox_ids]
        if ids:
            async with self.db.write() as conn:
                await conn.executemany("DELETE FROM outbox WHERE outbox_id = ?", ids)


async def _fetch_rows[R: _Row](
    db: Database, row: type[R], table: str, where: str, params: Sequence[Any] = ()
) -> list[R]:
    async with db.read() as conn:
        cursor = await conn.execute(_select(row, table) + where, params)
        found = await cursor.fetchall()
        await cursor.close()
    return [row.from_db(r) for r in found]
