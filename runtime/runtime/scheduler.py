from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

log = logging.getLogger("runtime.scheduler")

MONTH_NAMES = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
DOW_NAMES = {
    "sun": 0,
    "mon": 1,
    "tue": 2,
    "wed": 3,
    "thu": 4,
    "fri": 5,
    "sat": 6,
}


class CronError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CronField:
    values: frozenset[int]
    wildcard: bool

    @classmethod
    def parse(
        cls,
        expression: str,
        minimum: int,
        maximum: int,
        *,
        aliases: dict[str, int] | None = None,
        normalize: Callable[[int], int] | None = None,
    ) -> CronField:
        expression = expression.strip()
        if not expression:
            raise CronError("empty cron field")
        values: set[int] = set()
        for part in expression.split(","):
            part = part.strip()
            if not part:
                raise CronError(f"invalid cron field: {expression}")
            step = 1
            base = part
            if "/" in part:
                base, step_text = part.split("/", 1)
                try:
                    step = int(step_text)
                except ValueError as exc:
                    raise CronError(f"invalid step: {part}") from exc
                if step <= 0:
                    raise CronError(f"step must be positive: {part}")
            if base == "*":
                start, end = minimum, maximum
            elif "-" in base:
                start_text, end_text = base.split("-", 1)
                start = _parse_value(start_text, aliases)
                end = _parse_value(end_text, aliases)
            else:
                value = _parse_value(base, aliases)
                if "/" in part:
                    start, end = value, maximum
                else:
                    start = end = value
            if start < minimum or end > maximum or start > end:
                raise CronError(f"cron value out of range: {part}")
            for value in range(start, end + 1, step):
                values.add(normalize(value) if normalize else value)
        if not values:
            raise CronError(f"empty cron field: {expression}")
        return cls(frozenset(values), expression == "*")


def _parse_value(text: str, aliases: dict[str, int] | None) -> int:
    normalized = text.strip().lower()
    if aliases and normalized in aliases:
        return aliases[normalized]
    try:
        return int(normalized)
    except ValueError as exc:
        raise CronError(f"invalid cron value: {text}") from exc


@dataclass(frozen=True, slots=True)
class CronExpression:
    minute: CronField
    hour: CronField
    day_of_month: CronField
    month: CronField
    day_of_week: CronField

    @classmethod
    def parse(cls, expression: str) -> CronExpression:
        parts = expression.split()
        if len(parts) != 5:
            raise CronError("cron expression must have exactly 5 fields")
        return cls(
            minute=CronField.parse(parts[0], 0, 59),
            hour=CronField.parse(parts[1], 0, 23),
            day_of_month=CronField.parse(parts[2], 1, 31),
            month=CronField.parse(parts[3], 1, 12, aliases=MONTH_NAMES),
            day_of_week=CronField.parse(
                parts[4],
                0,
                7,
                aliases=DOW_NAMES,
                normalize=lambda value: 0 if value == 7 else value,
            ),
        )

    def matches(self, moment: datetime) -> bool:
        if moment.minute not in self.minute.values:
            return False
        if moment.hour not in self.hour.values:
            return False
        if moment.month not in self.month.values:
            return False
        day_of_week = (moment.weekday() + 1) % 7
        dom_match = moment.day in self.day_of_month.values
        dow_match = day_of_week in self.day_of_week.values
        if self.day_of_month.wildcard or self.day_of_week.wildcard:
            return dom_match and dow_match
        return dom_match or dow_match

    def next_after(self, moment: datetime, *, search_days: int = 366) -> datetime:
        current = moment.replace(second=0, microsecond=0) + timedelta(minutes=1)
        limit = current + timedelta(days=search_days)
        while current <= limit:
            if self.matches(current):
                return current
            current += timedelta(minutes=1)
        raise CronError("could not find next run within search window")


@dataclass(slots=True)
class ScheduledJob:
    id: str
    name: str
    cron: str
    handler: str
    payload: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    next_run_at: datetime | None = None
    last_error: str | None = None


JobHandler = Callable[[dict[str, Any]], Awaitable[None]]


class SchedulerRepository(Protocol):
    async def list_due_jobs(self, now: datetime, limit: int = 20) -> list[ScheduledJob]: ...

    async def mark_job_finished(
        self,
        job_id: str,
        status: str,
        *,
        next_run_at: datetime | None,
        error: str | None = None,
    ) -> None: ...


class SchedulerService:
    def __init__(self, repository: SchedulerRepository) -> None:
        self._repository = repository
        self._handlers: dict[str, JobHandler] = {}
        self._task: asyncio.Task[None] | None = None
        self._stopping = False
        self.runs_total = 0
        self.runs_failed = 0

    def register(self, name: str, handler: JobHandler) -> None:
        self._handlers[name] = handler

    def register_default_handlers(self) -> None:
        async def cleanup_runtime_commands(payload: dict[str, Any]) -> None:
            days = int(payload.get("days", 14))
            await _call_repo(self._repository, "cleanup_runtime_commands", days)

        async def cleanup_flow_traces(payload: dict[str, Any]) -> None:
            days = int(payload.get("days", 30))
            await _call_repo(self._repository, "cleanup_flow_traces", days)

        async def reset_usage_counters(payload: dict[str, Any]) -> None:
            await _call_repo(self._repository, "reset_usage_counters")

        self.register("cleanup_runtime_commands", cleanup_runtime_commands)
        self.register("cleanup_flow_traces", cleanup_flow_traces)
        self.register("reset_usage_counters", reset_usage_counters)

    async def process_due(self, now: datetime | None = None) -> int:
        moment = now or datetime.now(UTC)
        jobs = await self._repository.list_due_jobs(moment)
        processed = 0
        for job in jobs:
            processed += 1
            self.runs_total += 1
            handler = self._handlers.get(job.handler)
            error: str | None = None
            try:
                if handler is None:
                    raise LookupError(f"unknown job handler: {job.handler}")
                await handler(job.payload)
                status = "idle"
            except Exception as exc:
                error = str(exc)
                status = "error"
                self.runs_failed += 1
                log.exception("scheduled job %s failed", job.name)
            try:
                next_run = CronExpression.parse(job.cron).next_after(moment)
            except CronError:
                next_run = None
            await self._repository.mark_job_finished(
                job.id,
                status,
                next_run_at=next_run,
                error=error,
            )
        return processed

    async def start(self, interval: float = 30.0) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stopping = False
        self._task = asyncio.create_task(self._run(interval))

    async def _run(self, interval: float) -> None:
        while not self._stopping:
            try:
                await self.process_due()
            except Exception:
                log.exception("scheduler iteration failed")
            await asyncio.sleep(interval)

    async def stop(self) -> None:
        self._stopping = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


async def _call_repo(repository: Any, method: str, *args: Any) -> Any:
    handler = getattr(repository, method, None)
    if handler is None:
        return None
    result = handler(*args)
    if asyncio.iscoroutine(result):
        return await result
    return result
