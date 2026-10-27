from __future__ import annotations

import asyncio
from typing import Any

import pytest

from runtime.errors import InvalidTokenError, SupervisorCapacityError
from runtime.models import BotSpec, DesiredState, RuntimeCommand
from runtime.supervisor import BotRunner, Supervisor


class FakeLock:
    def __init__(self) -> None:
        self.released = False

    async def release(self) -> None:
        self.released = True


class FakeRepository:
    def __init__(self, bots: list[BotSpec]) -> None:
        self.bots = {bot.id: bot for bot in bots}
        self.statuses: dict[str, tuple[str, str | None]] = {}
        self.desired: dict[str, str] = {}
        self.heartbeats: list[dict[str, Any]] = []
        self.commands: list[str] = []
        self.locks: list[FakeLock] = []

    async def list_running_bots(self) -> list[BotSpec]:
        return [
            bot
            for bot in self.bots.values()
            if bot.desired_state == DesiredState.RUNNING
        ]

    async def get_bot(self, bot_id: str) -> BotSpec | None:
        return self.bots.get(bot_id)

    async def set_bot_status(
        self,
        bot_id: str,
        status: str,
        *,
        error: str | None = None,
        worker_id: str = "",
        guild_count: int = 0,
        version_number: int | None = None,
    ) -> None:
        self.statuses[bot_id] = (status, error)

    async def set_bot_desired_state(self, bot_id: str, desired_state: str) -> None:
        self.desired[bot_id] = desired_state

    async def write_heartbeat(
        self,
        bot_id: str,
        worker_id: str,
        status: str,
        latency_ms: int,
        uptime_seconds: int,
        *,
        guild_count: int = 0,
        version_number: int | None = None,
    ) -> None:
        self.heartbeats.append(
            {
                "bot_id": bot_id,
                "worker_id": worker_id,
                "status": status,
                "latency_ms": latency_ms,
                "uptime_seconds": uptime_seconds,
                "guild_count": guild_count,
                "version_number": version_number,
            }
        )

    async def mark_command(
        self,
        command_id: str,
        status: str,
        *,
        error: str | None = None,
    ) -> None:
        self.commands.append(status)

    async def acquire_bot_lock(self, bot_id: str) -> FakeLock:
        lock = FakeLock()
        self.locks.append(lock)
        return lock


class FakeClient:
    def __init__(self, spec: BotSpec, mode: str = "ok") -> None:
        self.spec = spec
        self.mode = mode
        self.closed = asyncio.Event()
        self.reloaded = False
        self.latency_ms = 42
        self.guild_count = 3

    async def start(self) -> None:
        if self.mode == "permanent":
            raise InvalidTokenError("invalid token")
        if self.mode.startswith("fail"):
            raise RuntimeError("connection failed")

    async def stop(self) -> None:
        self.closed.set()

    async def wait_closed(self) -> None:
        await self.closed.wait()

    async def reload(self, config: dict[str, Any]) -> None:
        self.reloaded = True


class FakeFactory:
    def __init__(self, modes: list[str] | None = None) -> None:
        self.modes = list(modes or [])
        self.created: list[FakeClient] = []

    def __call__(self, spec: BotSpec) -> FakeClient:
        mode = self.modes.pop(0) if self.modes else "ok"
        client = FakeClient(spec, mode)
        self.created.append(client)
        return client


async def wait_for_status(runner: BotRunner, status: str, timeout: float = 2.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if runner.status == status:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"runner status is {runner.status}, expected {status}")


def bot(bot_id: str = "b1") -> BotSpec:
    return BotSpec(
        id=bot_id,
        name=f"Bot {bot_id}",
        token="token",
        config={"schema_version": 1, "flows": [], "commands": []},
    )


async def test_start_bot_online_and_graceful_shutdown():
    repository = FakeRepository([bot()])
    factory = FakeFactory()
    supervisor = Supervisor(
        repository,
        factory,
        max_bots=2,
        heartbeat_interval=3600,
        reconcile_interval=3600,
    )
    await supervisor.start()
    runner = supervisor.runners["b1"]
    await wait_for_status(runner, "online")
    assert repository.statuses["b1"][0] == "online"
    assert runner.latency_ms == 42

    await supervisor.shutdown()
    assert repository.statuses["b1"][0] == "stopped"
    assert repository.locks[0].released
    assert supervisor.runners == {}


async def test_worker_capacity_marks_extra_bots_suspended():
    repository = FakeRepository([bot("b1"), bot("b2")])
    supervisor = Supervisor(
        repository,
        FakeFactory(),
        max_bots=1,
        heartbeat_interval=3600,
        reconcile_interval=3600,
    )
    await supervisor.start()
    assert "b1" in supervisor.runners
    assert repository.statuses["b2"][0] == "suspended"
    await supervisor.shutdown()


async def test_capacity_error_on_manual_start():
    repository = FakeRepository([bot("b1"), bot("b2")])
    supervisor = Supervisor(repository, FakeFactory(), max_bots=1)
    await supervisor.start_bot("b1")
    with pytest.raises(SupervisorCapacityError):
        await supervisor.start_bot("b2")
    await supervisor.shutdown()


async def test_permanent_error_stops_autorestart():
    repository = FakeRepository([bot()])
    factory = FakeFactory(["permanent"])
    runner = BotRunner(
        spec=bot(),
        repository=repository,
        factory=factory,
        worker_id="w1",
        restart_limit=5,
        sleep=asyncio.sleep,
    )
    await runner.start()
    await wait_for_status(runner, "error")
    await asyncio.sleep(0)
    assert runner.permanent_failure
    assert repository.desired["b1"] == "stopped"


async def test_autorestart_until_online():
    repository = FakeRepository([bot()])
    factory = FakeFactory(["fail", "fail", "ok"])

    async def fast_sleep(seconds: float) -> None:
        await asyncio.sleep(0)

    runner = BotRunner(
        spec=bot(),
        repository=repository,
        factory=factory,
        worker_id="w1",
        restart_limit=5,
        sleep=fast_sleep,
    )
    await runner.start()
    await wait_for_status(runner, "online")
    assert len(factory.created) == 3
    await runner.stop()


async def test_autorestart_limit_marks_suspended():
    repository = FakeRepository([bot()])
    factory = FakeFactory(["fail"] * 6)

    async def fast_sleep(seconds: float) -> None:
        await asyncio.sleep(0)

    runner = BotRunner(
        spec=bot(),
        repository=repository,
        factory=factory,
        worker_id="w1",
        restart_limit=3,
        sleep=fast_sleep,
    )
    await runner.start()
    await wait_for_status(runner, "suspended")
    assert repository.statuses["b1"][0] == "suspended"


async def test_runtime_commands_reload_and_stop():
    repository = FakeRepository([bot()])
    factory = FakeFactory()
    supervisor = Supervisor(repository, factory, max_bots=1)
    await supervisor.start_bot("b1")
    runner = supervisor.runners["b1"]
    await wait_for_status(runner, "online")
    client = factory.created[0]

    await supervisor.handle_command(
        RuntimeCommand(id="c1", bot_id="b1", command="reload")
    )
    assert client.reloaded
    assert repository.commands == ["acked", "done"]

    await supervisor.handle_command(
        RuntimeCommand(id="c2", bot_id="b1", command="stop")
    )
    assert runner.status == "stopped"
    await supervisor.shutdown()


async def test_heartbeat_loop_writes_state():
    repository = FakeRepository([bot()])
    supervisor = Supervisor(
        repository,
        FakeFactory(),
        max_bots=1,
        heartbeat_interval=0.01,
        reconcile_interval=3600,
    )
    await supervisor.start()
    await wait_for_status(supervisor.runners["b1"], "online")
    await asyncio.sleep(0.05)
    assert repository.heartbeats
    assert repository.heartbeats[0]["latency_ms"] == 42
    await supervisor.shutdown()


async def test_heartbeat_includes_guilds_and_version():
    spec = BotSpec(
        id="b1",
        name="Bot b1",
        token="token",
        config={},
        version_number=7,
    )
    repository = FakeRepository([spec])
    supervisor = Supervisor(
        repository,
        FakeFactory(),
        max_bots=1,
        heartbeat_interval=0.01,
        reconcile_interval=3600,
    )
    await supervisor.start()
    await wait_for_status(supervisor.runners["b1"], "online")
    await asyncio.sleep(0.05)
    heartbeat = repository.heartbeats[0]
    assert heartbeat["guild_count"] == 3
    assert heartbeat["version_number"] == 7
    await supervisor.shutdown()


async def test_token_decryption_error_is_permanent_and_does_not_start_client():
    spec = bot()
    spec.token_error = "token decryption failed"
    repository = FakeRepository([spec])
    factory = FakeFactory()
    runner = BotRunner(
        spec=spec,
        repository=repository,
        factory=factory,
        worker_id="w1",
        restart_limit=5,
    )
    await runner.start()
    await wait_for_status(runner, "error")
    await asyncio.sleep(0)
    assert runner.permanent_failure
    assert factory.created == []
    assert repository.statuses["b1"] == ("error", "token decryption failed")
    assert repository.desired["b1"] == "stopped"

    # A later reconcile removes the runner because desired_state is stopped;
    # that cleanup must not erase the error visible to the backend.
    await runner.stop()
    assert repository.statuses["b1"] == ("error", "token decryption failed")


async def test_reload_updates_version_number():
    repository = FakeRepository([bot()])
    factory = FakeFactory()
    supervisor = Supervisor(repository, factory, max_bots=1)
    await supervisor.start_bot("b1")
    runner = supervisor.runners["b1"]
    await wait_for_status(runner, "online")

    updated = bot()
    updated.config = {"schema_version": 1, "flows": [], "commands": [], "revision": 2}
    updated.version_number = 4
    repository.bots["b1"] = updated

    await supervisor.reload_bot("b1")
    assert runner.spec.version_number == 4
    assert runner.spec.config["revision"] == 2
    assert factory.created[0].reloaded
    await supervisor.shutdown()
