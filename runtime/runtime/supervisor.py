from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from runtime.errors import PermanentBotError, SupervisorCapacityError
from runtime.models import BotSpec, BotStatus, DesiredState, RuntimeCommand

log = logging.getLogger("runtime.supervisor")


class BotClient(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def wait_closed(self) -> None: ...

    async def reload(self, config: dict[str, Any]) -> None: ...

    @property
    def latency_ms(self) -> int: ...


class BotClientFactory(Protocol):
    def __call__(self, bot: BotSpec) -> BotClient: ...


class SupervisorRepository(Protocol):
    async def list_running_bots(self) -> list[BotSpec]: ...

    async def get_bot(self, bot_id: str) -> BotSpec | None: ...

    async def set_bot_status(
        self,
        bot_id: str,
        status: str,
        *,
        error: str | None = None,
        worker_id: str = "",
    ) -> None: ...

    async def set_bot_desired_state(self, bot_id: str, desired_state: str) -> None: ...

    async def write_heartbeat(
        self,
        bot_id: str,
        worker_id: str,
        status: str,
        latency_ms: int,
        uptime_seconds: int,
    ) -> None: ...

    async def mark_command(
        self,
        command_id: str,
        status: str,
        *,
        error: str | None = None,
    ) -> None: ...

    async def acquire_bot_lock(self, bot_id: str) -> Any | None: ...


@dataclass(slots=True)
class SupervisorMetrics:
    commands_total: int = 0
    commands_failed: int = 0
    restarts_total: int = 0
    started_at: float = field(default_factory=time.monotonic)


@dataclass(slots=True)
class BotRunner:
    spec: BotSpec
    repository: SupervisorRepository
    factory: BotClientFactory
    worker_id: str
    restart_limit: int = 5
    backoff_base: float = 1.0
    max_backoff: float = 30.0
    stability_period: float = 60.0
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    _client: BotClient | None = None
    _task: asyncio.Task[None] | None = None
    _desired: str = DesiredState.RUNNING
    _status: str = BotStatus.STOPPED
    _attempts: int = 0
    _started_at: float | None = None
    _stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    permanent_failure: bool = False

    @property
    def status(self) -> str:
        return self._status

    @property
    def desired(self) -> str:
        return self._desired

    @property
    def latency_ms(self) -> int:
        if self._client is None:
            return 0
        return self._client.latency_ms

    @property
    def uptime_seconds(self) -> int:
        if self._started_at is None:
            return 0
        return int(time.monotonic() - self._started_at)

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._desired = DesiredState.RUNNING
        self._attempts = 0
        self.permanent_failure = False
        self._stop_event.clear()
        self._task = asyncio.create_task(self._supervise(), name=f"bot-{self.spec.id}")

    async def stop(self, *, grace: float = 10.0) -> None:
        self._desired = DesiredState.STOPPED
        self._stop_event.set()
        client = self._client
        if client is not None:
            try:
                await asyncio.wait_for(client.stop(), timeout=grace)
            except Exception as exc:
                log.warning("bot %s: stop failed: %s", self.spec.id, exc)
        task = self._task
        if task is not None and not task.done():
            try:
                await asyncio.wait_for(task, timeout=grace)
            except TimeoutError:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            except asyncio.CancelledError:
                pass
        self._task = None
        self._client = None
        if self._status not in {BotStatus.STOPPED, BotStatus.SUSPENDED}:
            self._status = BotStatus.STOPPED
            await self.repository.set_bot_status(
                self.spec.id,
                BotStatus.STOPPED,
                worker_id=self.worker_id,
            )

    async def reload(self, config: dict[str, Any]) -> None:
        self.spec.config = config
        if self._client is not None and self._status == BotStatus.ONLINE:
            await self._client.reload(config)

    async def wait_until_settled(self, timeout: float = 5.0) -> str:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._status in {
                BotStatus.ONLINE,
                BotStatus.ERROR,
                BotStatus.SUSPENDED,
                BotStatus.STOPPED,
            }:
                return self._status
            await asyncio.sleep(0.01)
        raise TimeoutError(f"bot {self.spec.id} did not settle in {timeout}s")

    async def _supervise(self) -> None:
        while self._desired == DesiredState.RUNNING:
            if self._attempts >= self.restart_limit:
                await self._mark_suspended()
                return

            client = self.factory(self.spec)
            self._client = client
            self._status = BotStatus.STARTING
            await self.repository.set_bot_status(
                self.spec.id,
                BotStatus.STARTING,
                worker_id=self.worker_id,
            )
            try:
                await client.start()
            except asyncio.CancelledError:
                raise
            except PermanentBotError as exc:
                self.permanent_failure = True
                self._status = BotStatus.ERROR
                await self.repository.set_bot_status(
                    self.spec.id,
                    BotStatus.ERROR,
                    error=str(exc),
                    worker_id=self.worker_id,
                )
                await self.repository.set_bot_desired_state(self.spec.id, DesiredState.STOPPED)
                self._desired = DesiredState.STOPPED
                return
            except Exception as exc:
                self._attempts += 1
                self._status = BotStatus.ERROR
                await self.repository.set_bot_status(
                    self.spec.id,
                    BotStatus.ERROR,
                    error=str(exc),
                    worker_id=self.worker_id,
                )
                if self._attempts >= self.restart_limit:
                    await self._mark_suspended()
                    return
                await self.sleep(self._backoff())
                continue

            self._status = BotStatus.ONLINE
            self._started_at = time.monotonic()
            await self.repository.set_bot_status(
                self.spec.id,
                BotStatus.ONLINE,
                worker_id=self.worker_id,
            )
            try:
                await client.wait_closed()
            except asyncio.CancelledError:
                raise
            if self._desired != DesiredState.RUNNING:
                break

            uptime = time.monotonic() - (self._started_at or time.monotonic())
            self._attempts = 0 if uptime >= self.stability_period else self._attempts + 1
            self._status = BotStatus.ERROR
            self._started_at = None
            await self.repository.set_bot_status(
                self.spec.id,
                BotStatus.ERROR,
                error="gateway connection lost",
                worker_id=self.worker_id,
            )
            if self._attempts >= self.restart_limit:
                await self._mark_suspended()
                return
            await self.sleep(self._backoff())

        if self._status != BotStatus.SUSPENDED:
            self._status = BotStatus.STOPPED
            await self.repository.set_bot_status(
                self.spec.id,
                BotStatus.STOPPED,
                worker_id=self.worker_id,
            )

    def _backoff(self) -> float:
        return float(min(self.max_backoff, self.backoff_base * (2 ** max(0, self._attempts - 1))))

    async def _mark_suspended(self) -> None:
        self._status = BotStatus.SUSPENDED
        await self.repository.set_bot_status(
            self.spec.id,
            BotStatus.SUSPENDED,
            error=f"autorestart limit {self.restart_limit} exceeded",
            worker_id=self.worker_id,
        )


class Supervisor:
    def __init__(
        self,
        repository: SupervisorRepository,
        factory: BotClientFactory,
        *,
        worker_id: str = "worker-1",
        max_bots: int = 25,
        heartbeat_interval: float = 15.0,
        reconcile_interval: float = 10.0,
        restart_limit: int = 5,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._repository = repository
        self._factory = factory
        self.worker_id = worker_id
        self._max_bots = max_bots
        self._heartbeat_interval = heartbeat_interval
        self._reconcile_interval = reconcile_interval
        self._restart_limit = restart_limit
        self._sleep = sleep
        self._runners: dict[str, BotRunner] = {}
        self._locks: dict[str, Any] = {}
        self._tasks: list[asyncio.Task[None]] = []
        self._stopping = False
        self.metrics = SupervisorMetrics()

    @property
    def runners(self) -> dict[str, BotRunner]:
        return dict(self._runners)

    async def start(self) -> None:
        self._stopping = False
        self._tasks = [
            asyncio.create_task(self._heartbeat_loop(), name="runtime-heartbeat"),
            asyncio.create_task(self._reconcile_loop(), name="runtime-reconcile"),
        ]
        await self.reconcile()

    async def reconcile(self) -> None:
        bots = await self._repository.list_running_bots()
        running_ids = {bot.id for bot in bots}
        for bot_id in list(self._runners):
            runner = self._runners[bot_id]
            if bot_id not in running_ids or runner.desired != DesiredState.RUNNING:
                await self.stop_bot(bot_id)

        for bot in bots:
            if bot.id in self._runners:
                continue
            if len(self._runners) >= self._max_bots:
                await self._repository.set_bot_status(
                    bot.id,
                    BotStatus.SUSPENDED,
                    error=f"worker {self.worker_id} is at capacity ({self._max_bots})",
                    worker_id=self.worker_id,
                )
                continue
            try:
                await self.start_bot(bot.id)
            except SupervisorCapacityError:
                break

    async def start_bot(self, bot_id: str) -> None:
        if bot_id in self._runners:
            if self._runners[bot_id].desired != DesiredState.RUNNING:
                await self._runners[bot_id].start()
            return
        if len(self._runners) >= self._max_bots:
            raise SupervisorCapacityError(f"worker {self.worker_id} is at capacity")

        spec = await self._repository.get_bot(bot_id)
        if spec is None or spec.desired_state != DesiredState.RUNNING:
            return

        lock = await self._repository.acquire_bot_lock(bot_id)
        if lock is None:
            log.info("bot %s is locked by another worker", bot_id)
            return
        self._locks[bot_id] = lock
        runner = BotRunner(
            spec=spec,
            repository=self._repository,
            factory=self._factory,
            worker_id=self.worker_id,
            restart_limit=self._restart_limit,
            sleep=self._sleep,
        )
        self._runners[bot_id] = runner
        await runner.start()

    async def stop_bot(self, bot_id: str) -> None:
        runner = self._runners.pop(bot_id, None)
        if runner is not None:
            await runner.stop()
        lock = self._locks.pop(bot_id, None)
        await _release_lock(lock)

    async def restart_bot(self, bot_id: str) -> None:
        self.metrics.restarts_total += 1
        await self.stop_bot(bot_id)
        await self.start_bot(bot_id)

    async def reload_bot(self, bot_id: str) -> None:
        spec = await self._repository.get_bot(bot_id)
        if spec is None:
            return
        runner = self._runners.get(bot_id)
        if runner is None:
            return
        runner.spec.name = spec.name
        runner.spec.token = spec.token
        await runner.reload(spec.config)

    async def handle_command(self, command: RuntimeCommand) -> None:
        self.metrics.commands_total += 1
        try:
            await self._repository.mark_command(command.id, "acked")
            if command.command == "start":
                await self.start_bot(command.bot_id)
            elif command.command == "stop":
                await self.stop_bot(command.bot_id)
            elif command.command == "restart":
                await self.restart_bot(command.bot_id)
            elif command.command == "reload":
                await self.reload_bot(command.bot_id)
            else:
                raise ValueError(f"unknown runtime command: {command.command}")
            await self._repository.mark_command(command.id, "done")
        except Exception as exc:
            self.metrics.commands_failed += 1
            log.exception("runtime command %s failed", command.id)
            await self._repository.mark_command(command.id, "failed", error=str(exc))

    async def shutdown(self, grace: float = 10.0) -> None:
        self._stopping = True
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        bot_ids = list(self._runners)
        await asyncio.gather(
            *(self.stop_bot(bot_id) for bot_id in bot_ids),
            return_exceptions=True,
        )
        for lock in list(self._locks.values()):
            await _release_lock(lock)
        self._locks.clear()

    def health_snapshot(self) -> dict[str, Any]:
        statuses: dict[str, int] = {}
        bots: list[dict[str, Any]] = []
        for bot_id, runner in sorted(self._runners.items()):
            statuses[runner.status] = statuses.get(runner.status, 0) + 1
            bots.append(
                {
                    "id": bot_id,
                    "name": runner.spec.name,
                    "status": runner.status,
                    "latency_ms": runner.latency_ms,
                    "uptime_seconds": runner.uptime_seconds,
                }
            )
        return {
            "worker_id": self.worker_id,
            "stopping": self._stopping,
            "capacity": self._max_bots,
            "statuses": statuses,
            "bots": bots,
            "metrics": {
                "commands_total": self.metrics.commands_total,
                "commands_failed": self.metrics.commands_failed,
                "restarts_total": self.metrics.restarts_total,
                "uptime_seconds": int(time.monotonic() - self.metrics.started_at),
            },
        }

    async def _heartbeat_loop(self) -> None:
        while not self._stopping:
            for bot_id, runner in list(self._runners.items()):
                if runner.status not in {BotStatus.STARTING, BotStatus.ONLINE}:
                    continue
                try:
                    await self._repository.write_heartbeat(
                        bot_id,
                        self.worker_id,
                        runner.status,
                        runner.latency_ms,
                        runner.uptime_seconds,
                    )
                except Exception:
                    log.exception("heartbeat failed for bot %s", bot_id)
            await self._sleep(self._heartbeat_interval)

    async def _reconcile_loop(self) -> None:
        while not self._stopping:
            await self._sleep(self._reconcile_interval)
            try:
                await self.reconcile()
            except Exception:
                log.exception("reconcile failed")


async def _release_lock(lock: Any) -> None:
    if lock is None:
        return
    release = getattr(lock, "release", None)
    if release is None:
        return
    result = release()
    if inspect.isawaitable(result):
        await result
