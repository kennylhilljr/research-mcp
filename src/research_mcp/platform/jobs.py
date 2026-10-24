"""The job service: background work whose state lives in ``state.db.jobs`` (LLD-platform-v2 5.5).

``JobService.submit(kind, params)`` is the only way a job starts, including a retry from the
UI. Each kind has a handler registered by the component that owns it; the handler gets a
``JobContext`` to report progress and store a resume cursor. Progress is written to the row
and pushed to every caller waiting in ``wait``, which a tool connects to MCP
``Context.report_progress``.
"""

from __future__ import annotations

import builtins
import json
import logging
import uuid
from collections.abc import Awaitable, Callable, Mapping
from contextlib import AsyncExitStack
from datetime import datetime
from enum import StrEnum
from types import TracebackType
from typing import Any, Self

import anyio
from anyio.abc import TaskGroup
from pydantic import BaseModel, ConfigDict, JsonValue
from ulid import ULID

from research_mcp.core.context import correlation_id
from research_mcp.core.errors import ErrorCode, ToolError
from research_mcp.core.models import Clock
from research_mcp.platform.stores import JobRow, JobState, StateStore

_log = logging.getLogger(__name__)

FINAL: frozenset[JobState] = frozenset({"succeeded", "failed", "cancelled"})


class JobKind(StrEnum):
    """The job kinds the LLDs name; each owning component registers its handler."""

    LEGACY_IMPORT = "legacy_import"
    ARCHIVE = "archive"
    ARCHIVE_REINDEX = "archive_reindex"
    INTEGRITY_RECHECK = "integrity_recheck"
    REBUILD_FTS = "rebuild_fts"
    REEMBED_MISSING = "reembed_missing"
    CLEAN_ORPHANS = "clean_orphans"
    BACKUP_STATE = "backup_state"


class Job(BaseModel):
    """What ``status`` and ``list`` return: one ``jobs`` row with its JSON decoded."""

    model_config = ConfigDict(frozen=True, defer_build=True)

    job_id: str
    kind: str
    state: JobState
    params: dict[str, JsonValue]
    progress: float
    cursor: str | None
    result: JsonValue
    error_code: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: JobRow) -> Job:
        return cls(
            job_id=row.job_id,
            kind=row.kind,
            state=row.state,
            params=json.loads(row.params_json),
            progress=row.progress,
            cursor=row.cursor,
            result=None if row.result_json is None else json.loads(row.result_json),
            error_code=row.error_code,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


ProgressSink = Callable[[float], Awaitable[None]]


class JobContext:
    """What a handler gets: its parameters, the stored cursor and the progress calls."""

    def __init__(self, service: JobService, job: Job) -> None:
        self._service = service
        self.job_id = job.job_id
        self.kind = job.kind
        self.params = job.params
        self.cursor = job.cursor

    async def progress(self, fraction: float) -> None:
        """Record progress between 0 and 1 and push it to every waiting caller."""
        await self._service._progress(self.job_id, min(max(fraction, 0.0), 1.0))

    async def checkpoint(self, cursor: str) -> None:
        """Store the resume cursor of a resumable kind."""
        self.cursor = cursor
        await self._service._update(self.job_id, cursor=cursor)


JobHandler = Callable[[JobContext], Awaitable[JsonValue]]


class JobService:
    """Runs submitted jobs in a task group and keeps their state in ``state.db``.

    Use it as an async context manager; leaving it cancels the jobs still running.
    """

    def __init__(
        self,
        state: StateStore,
        clock: Clock,
        handlers: Mapping[str, JobHandler] | None = None,
    ) -> None:
        self._state = state
        self._clock = clock
        self._handlers: dict[str, JobHandler] = dict(handlers or {})
        self._scopes: dict[str, anyio.CancelScope] = {}
        self._waiters: dict[str, list[ProgressSink]] = {}
        self._done: dict[str, anyio.Event] = {}
        self._stack: AsyncExitStack | None = None
        self._tasks: TaskGroup | None = None

    def register(self, kind: str, handler: JobHandler) -> None:
        self._handlers[kind] = handler

    async def __aenter__(self) -> Self:
        stack = AsyncExitStack()
        self._tasks = await stack.enter_async_context(anyio.create_task_group())
        stack.callback(self._tasks.cancel_scope.cancel)
        self._stack = stack
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        stack, self._stack, self._tasks = self._stack, None, None
        if stack is not None:
            await stack.aclose()

    # @spec PLAT-74
    async def submit(self, kind: str, params: Mapping[str, JsonValue]) -> str:
        """Store a pending job and start it; return its id."""
        handler = self._handlers.get(kind)
        if handler is None:
            raise ToolError(ErrorCode.INVALID_ARGUMENT, "Unknown job kind.")
        if self._tasks is None:
            raise RuntimeError("the job service is not running")
        now = self._clock.now()
        job_id = str(ULID())
        await self._state.job_insert(
            JobRow(
                job_id=job_id,
                kind=kind,
                state="pending",
                params_json=json.dumps(dict(params), sort_keys=True),
                created_at=now,
                updated_at=now,
            )
        )
        scope = anyio.CancelScope()
        self._scopes[job_id] = scope
        self._done[job_id] = anyio.Event()
        self._tasks.start_soon(self._run, job_id, handler, scope)
        return job_id

    async def status(self, job_id: str) -> Job:
        row = await self._state.job_get(job_id)
        if row is None:
            raise ToolError(ErrorCode.NOT_FOUND, "No such job.")
        return Job.from_row(row)

    async def list(self, state: JobState | None = None) -> builtins.list[Job]:
        return [Job.from_row(row) for row in await self._state.job_list(state)]

    async def cancel(self, job_id: str) -> Job:
        """Cancel a pending or running job; a finished job is returned unchanged."""
        job = await self.status(job_id)
        if job.state in FINAL:
            return job
        scope = self._scopes.get(job_id)
        if scope is not None:
            scope.cancel()
        job = await self._finish(job_id, "cancelled")
        return job

    async def wait(self, job_id: str, on_progress: ProgressSink | None = None) -> Job:
        """Wait until the job ends, pushing its progress to ``on_progress`` meanwhile."""
        job = await self.status(job_id)
        done = self._done.get(job_id)
        if job.state in FINAL or done is None:
            return job
        sinks = self._waiters.setdefault(job_id, [])
        if on_progress is not None:
            sinks.append(on_progress)
        try:
            await done.wait()
        finally:
            if on_progress is not None:
                sinks.remove(on_progress)
            if not sinks:
                self._waiters.pop(job_id, None)
        return await self.status(job_id)

    async def _run(self, job_id: str, handler: JobHandler, scope: anyio.CancelScope) -> None:
        token = correlation_id.set(uuid.uuid4().hex)
        try:
            with scope:
                job = Job.from_row(await self._update(job_id, state="running"))
                try:
                    result = await handler(JobContext(self, job))
                except ToolError as exc:
                    await self._finish(job_id, "failed", error_code=exc.code.value)
                except Exception:  # noqa: BLE001 - a job failure is a state, not a crash
                    # No exception text: it may carry a path, an upstream body or a secret.
                    _log.warning("job.failed", extra={"job_id": job_id, "operation": job.kind})
                    await self._finish(job_id, "failed", error_code=ErrorCode.INTERNAL.value)
                else:
                    await self._progress(job_id, 1.0)
                    await self._finish(job_id, "succeeded", result_json=json.dumps(result))
        finally:
            correlation_id.reset(token)
            self._scopes.pop(job_id, None)
            done = self._done.pop(job_id, None)
            if done is not None:
                done.set()

    async def _finish(self, job_id: str, state: JobState, **fields: Any) -> Job:
        current = await self._state.job_get(job_id)
        if current is not None and current.state in FINAL:
            return Job.from_row(current)
        return Job.from_row(await self._update(job_id, state=state, **fields))

    async def _progress(self, job_id: str, fraction: float) -> None:
        await self._update(job_id, progress=fraction)
        for sink in list(self._waiters.get(job_id, [])):
            await sink(fraction)

    async def _update(self, job_id: str, **fields: Any) -> JobRow:
        # Shielded: a cancel arriving mid-write must not interrupt the transaction's rollback.
        with anyio.CancelScope(shield=True):
            row = await self._state.job_update(job_id, updated_at=self._clock.now(), **fields)
        return row
