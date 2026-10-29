from __future__ import annotations

from datetime import UTC, datetime

import pytest

from runtime.scheduler import (
    CronError,
    CronExpression,
    ScheduledJob,
    SchedulerService,
)


class FakeSchedulerRepository:
    def __init__(self, jobs: list[ScheduledJob]) -> None:
        self.jobs = jobs
        self.finished: list[dict] = []

    async def list_due_jobs(self, now: datetime, limit: int = 20) -> list[ScheduledJob]:
        self.jobs = [job for job in self.jobs if job.next_run_at is None or job.next_run_at <= now]
        return self.jobs[:limit]

    async def mark_job_finished(
        self,
        job_id: str,
        status: str,
        *,
        next_run_at: datetime | None,
        error: str | None = None,
    ) -> None:
        self.finished.append(
            {"id": job_id, "status": status, "next_run_at": next_run_at, "error": error}
        )


def test_cron_matches_and_next_run():
    cron = CronExpression.parse("*/15 9-17 * * mon-fri")
    monday = datetime(2026, 1, 5, 9, 30, tzinfo=UTC)
    saturday = datetime(2026, 1, 10, 9, 30, tzinfo=UTC)
    assert cron.matches(monday)
    assert not cron.matches(saturday)
    assert cron.next_after(datetime(2026, 1, 5, 9, 31, tzinfo=UTC)) == datetime(
        2026, 1, 5, 9, 45, tzinfo=UTC
    )


def test_cron_lists_ranges_and_errors():
    cron = CronExpression.parse("0 0 1,15 * *")
    assert cron.matches(datetime(2026, 2, 15, 0, 0, tzinfo=UTC))
    assert not cron.matches(datetime(2026, 2, 14, 0, 0, tzinfo=UTC))
    for expression in ("* * * *", "60 * * * *", "*/0 * * * *", "a b c d e"):
        with pytest.raises(CronError):
            CronExpression.parse(expression)


def test_cron_day_of_week_aliases():
    cron = CronExpression.parse("0 12 * * SUN")
    assert cron.matches(datetime(2026, 1, 4, 12, 0, tzinfo=UTC))


async def test_scheduler_processes_due_jobs():
    job = ScheduledJob(
        id="job-1",
        name="cleanup",
        cron="0 3 * * *",
        handler="cleanup",
        next_run_at=datetime(2026, 1, 1, 2, 0, tzinfo=UTC),
    )
    repository = FakeSchedulerRepository([job])
    scheduler = SchedulerService(repository)
    calls: list[dict] = []

    async def cleanup(payload):
        calls.append(payload)

    scheduler.register("cleanup", cleanup)
    processed = await scheduler.process_due(datetime(2026, 1, 1, 3, 0, tzinfo=UTC))
    assert processed == 1
    assert calls == [{}]
    assert repository.finished[0]["status"] == "idle"
    assert repository.finished[0]["next_run_at"] == datetime(2026, 1, 2, 3, 0, tzinfo=UTC)


async def test_scheduler_marks_unknown_handler_failed():
    job = ScheduledJob(
        id="job-2",
        name="broken",
        cron="0 3 * * *",
        handler="missing",
        next_run_at=datetime(2026, 1, 1, 2, 0, tzinfo=UTC),
    )
    repository = FakeSchedulerRepository([job])
    scheduler = SchedulerService(repository)
    await scheduler.process_due(datetime(2026, 1, 1, 3, 0, tzinfo=UTC))
    assert repository.finished[0]["status"] == "error"
    assert "unknown job handler" in repository.finished[0]["error"]
