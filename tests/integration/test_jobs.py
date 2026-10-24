"""The job service over a real ``state.db`` (LLD-platform-v2 5.5)."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

import anyio
import pytest

from research_mcp.core.errors import ErrorCode, ToolError
from research_mcp.platform.jobs import JobContext, JobService
from research_mcp.platform.stores import STATE_MIGRATIONS, Database, Migrator, StateStore
from research_mcp.testing.clock import FakeClock

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)


async def open_store(path: Path) -> StateStore:
    db = Database(path)
    await db.open(Migrator(STATE_MIGRATIONS))
    return StateStore(db)


async def until(check: Callable[[], Awaitable[bool]], *, limit_s: float = 5.0) -> None:
    """Poll a row in state.db; the store has no change event to wait on."""
    with anyio.fail_after(limit_s):
        while not await check():  # noqa: ASYNC110 - polling persisted state
            await anyio.sleep(0.01)


async def test_submit_status_progress_cancel_persist(tmp_path: Path) -> None:
    """@spec PLAT-74: submit, status, progress and cancel are rows of state.db.jobs."""
    clock = FakeClock(NOW)
    store = await open_store(tmp_path / "state.db")
    go, release = anyio.Event(), anyio.Event()

    async def count(job: JobContext) -> dict[str, int]:
        await go.wait()
        await job.progress(0.5)
        await job.checkpoint("page-2")
        await release.wait()
        return {"n": job.params["n"]}

    async def forever(job: JobContext) -> None:
        await job.progress(0.25)
        await anyio.sleep_forever()

    seen: list[float] = []

    async def on_progress(value: float) -> None:
        seen.append(value)

    async with JobService(store, clock, {"count": count, "forever": forever}) as jobs:
        first = await jobs.submit("count", {"n": 3})
        row = await store.job_get(first)
        assert row is not None and row.kind == "count"
        assert json.loads(row.params_json) == {"n": 3}

        async with anyio.create_task_group() as tasks:
            waited: list[object] = []

            async def wait_first() -> None:
                waited.append(await jobs.wait(first, on_progress=on_progress))

            tasks.start_soon(wait_first)
            await anyio.sleep(0.05)
            go.set()

            async def checkpointed() -> bool:
                found = await store.job_get(first)
                return found is not None and found.cursor == "page-2"

            await until(checkpointed)
            running = await jobs.status(first)
            assert (running.state, running.progress, running.cursor) == ("running", 0.5, "page-2")
            release.set()

        done = waited[0]
        assert done == await jobs.status(first)
        assert (done.state, done.result, done.progress) == ("succeeded", {"n": 3}, 1.0)  # type: ignore[attr-defined]
        assert seen[0] == 0.5 and seen[-1] == 1.0

        second = await jobs.submit("forever", {})

        async def started() -> bool:
            return (await jobs.status(second)).progress == 0.25

        await until(started)
        cancelled = await jobs.cancel(second)
        assert cancelled.state == "cancelled"
        assert [job.job_id for job in await jobs.list("cancelled")] == [second]
        assert (await jobs.cancel(first)).state == "succeeded"  # a final job stays final

        with pytest.raises(ToolError) as unknown:
            await jobs.submit("no_such_kind", {})
        assert unknown.value.code is ErrorCode.INVALID_ARGUMENT
        with pytest.raises(ToolError) as missing:
            await jobs.status("01NOTAJOB")
        assert missing.value.code is ErrorCode.NOT_FOUND
    await store.db.close()

    # Everything above is in state.db, so a new service over a new connection reads it back.
    reopened = await open_store(tmp_path / "state.db")
    async with JobService(reopened, clock) as again:
        assert (await again.status(first)).state == "succeeded"
        assert (await again.status(second)).state == "cancelled"
        assert {job.job_id for job in await again.list()} == {first, second}
    await reopened.db.close()


async def test_failed_job_records_its_code(tmp_path: Path) -> None:
    """@spec PLAT-74: a job that raises ends failed, with a code and no exception text."""
    store = await open_store(tmp_path / "state.db")

    async def broken(job: JobContext) -> None:
        raise RuntimeError("secret-looking detail")

    async def tool_error(job: JobContext) -> None:
        raise ToolError(ErrorCode.UPSTREAM_ERROR, "upstream failed")

    async with JobService(store, FakeClock(NOW), {"broken": broken, "tool": tool_error}) as jobs:
        first = await jobs.wait(await jobs.submit("broken", {}))
        second = await jobs.wait(await jobs.submit("tool", {}))
    assert (first.state, first.error_code, first.result) == ("failed", "internal", None)
    assert (second.state, second.error_code) == ("failed", "upstream_error")
    row = await store.job_get(first.job_id)
    assert row is not None and "secret-looking" not in row.model_dump_json()
    await store.db.close()
