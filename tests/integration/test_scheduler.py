"""The wall-clock scheduler over a real ``state.db`` (LLD-platform-v2 5.5)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

import anyio
import pytest

from research_mcp.platform.scheduler import TICK_S, Daily, Every, Scheduler
from research_mcp.platform.stores import STATE_MIGRATIONS, Database, Migrator, StateStore
from research_mcp.testing.clock import FakeClock

MONDAY_8AM = datetime(2026, 10, 19, 8, 0, tzinfo=UTC)


async def open_store(path: Path) -> StateStore:
    db = Database(path)
    await db.open(Migrator(STATE_MIGRATIONS))
    return StateStore(db)


async def test_missed_daily_job_runs_once(tmp_path: Path) -> None:
    """@spec PLAT-76: a daily job missed over a sleep or a restart runs exactly once."""
    clock = FakeClock(MONDAY_8AM)
    store = await open_store(tmp_path / "state.db")
    runs: list[datetime] = []

    async def review() -> None:
        runs.append(clock.now())

    scheduler = Scheduler(store, clock, tz=UTC)
    scheduler.add("review", Daily(time(9, 0)), review)
    assert await scheduler.tick() == []  # first sight: due at 09:00 today, not now
    row = await store.schedule_get("review")
    assert row is not None and row.next_due_at == MONDAY_8AM.replace(hour=9)

    clock.advance(3 * 86_400)  # the Mac slept through three 09:00s
    assert await scheduler.tick() == ["review"]
    assert await scheduler.tick() == []
    assert len(runs) == 1
    row = await store.schedule_get("review")
    assert row is not None
    assert row.last_run_at == MONDAY_8AM + timedelta(days=3)
    assert row.next_due_at == MONDAY_8AM.replace(day=22, hour=9)
    await store.db.close()

    # The daemon was down for two days: a new scheduler reads the due time from state.db.
    clock.advance(2 * 86_400 + 5 * 3600)
    store = await open_store(tmp_path / "state.db")
    restarted = Scheduler(store, clock, tz=UTC)
    restarted.add("review", Daily(time(9, 0)), review)
    assert await restarted.tick() == ["review"]
    assert await restarted.tick() == []
    assert len(runs) == 2
    await store.db.close()


async def test_wall_clock_compared_every_60_seconds(tmp_path: Path) -> None:
    """@spec PLAT-76: the loop compares wall-clock due times every 60 s; a failure is logged."""
    clock = FakeClock(MONDAY_8AM)
    store = await open_store(tmp_path / "state.db")
    sleeps: list[float] = []
    enough = anyio.Event()

    class CountingSleeper:
        async def sleep(self, seconds: float) -> None:
            sleeps.append(seconds)
            clock.advance(seconds)
            if len(sleeps) == 3:
                enough.set()
                await anyio.sleep_forever()
            await anyio.lowlevel.checkpoint()

    rotations: list[datetime] = []

    async def log_rotate() -> None:
        rotations.append(clock.now())

    async def broken() -> None:
        raise RuntimeError("boom")

    scheduler = Scheduler(store, clock, tz=UTC, sleeper=CountingSleeper())
    scheduler.add("log_rotate", Every(120), log_rotate)
    scheduler.add("broken", Every(60), broken)
    async with anyio.create_task_group() as tasks:
        tasks.start_soon(scheduler.run)
        with anyio.fail_after(5):
            await enough.wait()
        tasks.cancel_scope.cancel()

    assert TICK_S == 60 and sleeps == [60, 60, 60]
    # An interval job runs once at start, then each time its interval has passed.
    assert rotations == [MONDAY_8AM, MONDAY_8AM + timedelta(seconds=120)]
    assert scheduler.last_tick == MONDAY_8AM + timedelta(seconds=120)
    row = await store.schedule_get("broken")
    assert row is not None and row.last_run_at == MONDAY_8AM + timedelta(seconds=120)
    await store.db.close()


async def test_failing_job_is_a_warning_without_exception_text(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """@spec PLAT-76: one failing job neither stops the tick nor logs its exception text."""
    clock = FakeClock(MONDAY_8AM)
    store = await open_store(tmp_path / "state.db")
    ran: list[str] = []

    async def broken() -> None:
        raise RuntimeError("token=abc123")

    async def fine() -> None:
        ran.append("fine")

    scheduler = Scheduler(store, clock, tz=UTC)
    scheduler.add("broken", Every(60), broken)
    scheduler.add("fine", Every(60), fine)
    with caplog.at_level(logging.WARNING, logger="research_mcp.platform.scheduler"):
        assert await scheduler.tick() == ["broken", "fine"]
    assert ran == ["fine"]
    assert "abc123" not in caplog.text and "scheduler.job_failed" in caplog.text
    await store.db.close()
