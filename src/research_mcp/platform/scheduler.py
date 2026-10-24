"""The wall-clock scheduler (LLD-platform-v2 5.5).

asyncio timers stall while the Mac sleeps, so every ``TICK_S`` the scheduler compares the
wall clock with each job's next due time in ``state.db.schedule_runs``. A daily job that
was missed, however many days ago, runs once and is then due at its next local time; an
interval job runs once at start and then each time its interval has passed.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, time, timedelta, tzinfo

import anyio
from anyio.abc import TaskStatus

from research_mcp.core.context import correlation_id
from research_mcp.core.models import Clock, Sleeper
from research_mcp.platform.stores import StateStore

_log = logging.getLogger(__name__)

TICK_S = 60.0

ScheduledJob = Callable[[], Awaitable[None]]


@dataclass(frozen=True)
class Daily:
    """Once a day at a local time."""

    at: time


@dataclass(frozen=True)
class Every:
    """Every ``seconds``."""

    seconds: float


class _AnyioSleeper:
    async def sleep(self, seconds: float) -> None:
        await anyio.sleep(seconds)


@dataclass(frozen=True)
class _Entry:
    name: str
    schedule: Daily | Every
    run: ScheduledJob


class Scheduler:
    """Runs registered jobs when their wall-clock due time has passed.

    ``tz`` is the zone of daily times; ``None`` is the system's local zone.
    """

    def __init__(
        self,
        state: StateStore,
        clock: Clock,
        *,
        tz: tzinfo | None = None,
        sleeper: Sleeper | None = None,
        tick_s: float = TICK_S,
    ) -> None:
        self._state = state
        self._clock = clock
        self._tz = tz
        self._sleeper = sleeper or _AnyioSleeper()
        self._tick_s = tick_s
        self._entries: list[_Entry] = []
        self.last_tick: datetime | None = None
        self.running = False

    def add(self, name: str, schedule: Daily | Every, run: ScheduledJob) -> None:
        self._entries.append(_Entry(name, schedule, run))

    async def run(self, *, task_status: TaskStatus[None] = anyio.TASK_STATUS_IGNORED) -> None:
        """Tick now, report started, then tick every ``tick_s`` until cancelled."""
        self.running = True
        try:
            await self.tick()
            task_status.started()
            while True:
                await self._sleeper.sleep(self._tick_s)
                await self.tick()
        finally:
            self.running = False

    # @spec PLAT-76
    async def tick(self) -> list[str]:
        """Run every job that is due now; return their names in registration order."""
        now = self._clock.now()
        ran: list[str] = []
        for entry in self._entries:
            row = await self._state.schedule_get(entry.name)
            if row is None and isinstance(entry.schedule, Daily):
                # First sight of a daily job: due at its next local time, not now.
                await self._state.schedule_set(entry.name, None, self._next(entry, now))
                continue
            if row is not None and now < row.next_due_at:
                continue
            await self._run(entry)
            ran.append(entry.name)
            # The next due time counts from now, so missed days collapse into this one run.
            await self._state.schedule_set(entry.name, now, self._next(entry, now))
        self.last_tick = now
        return ran

    async def _run(self, entry: _Entry) -> None:
        token = correlation_id.set(uuid.uuid4().hex)
        try:
            await entry.run()
        except Exception:  # noqa: BLE001 - one failing job never stops the scheduler
            # No exception text: it may carry a path, an upstream body or a secret.
            _log.warning("scheduler.job_failed", extra={"operation": entry.name})
        finally:
            correlation_id.reset(token)

    def _next(self, entry: _Entry, now: datetime) -> datetime:
        schedule = entry.schedule
        if isinstance(schedule, Every):
            return now + timedelta(seconds=schedule.seconds)
        local = now.astimezone(self._tz)
        day = local.date()
        while True:
            due = self._local(datetime.combine(day, schedule.at))
            if due > now:
                return due
            day += timedelta(days=1)

    def _local(self, naive: datetime) -> datetime:
        if self._tz is None:
            return naive.astimezone()  # the system zone, with its offset on that day
        return naive.replace(tzinfo=self._tz)
