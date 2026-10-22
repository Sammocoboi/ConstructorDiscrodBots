from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from runtime.models import RuntimeCommand
from runtime.supervisor import Supervisor

log = logging.getLogger("runtime.listener")


class CommandRepository(Protocol):
    async def fetch_pending_commands(self, limit: int = 50) -> list[RuntimeCommand]: ...

    async def listen_commands(
        self,
        callback: Callable[[str], Awaitable[None]],
    ) -> Any: ...


class CommandListener:
    def __init__(
        self,
        repository: CommandRepository,
        supervisor: Supervisor,
        *,
        poll_interval: float = 30.0,
        batch_size: int = 50,
    ) -> None:
        self._repository = repository
        self._supervisor = supervisor
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._task: asyncio.Task[None] | None = None
        self._listener: Any | None = None
        self._stopping = False
        self._wakeup = asyncio.Event()

    async def start(self) -> None:
        self._stopping = False
        try:
            self._listener = await self._repository.listen_commands(self._on_notify)
        except Exception:
            log.exception("LISTEN/NOTIFY unavailable, falling back to polling")
            self._listener = None
        self._task = asyncio.create_task(self._run(), name="runtime-command-listener")
        await self.process_pending()

    async def _on_notify(self, payload: str) -> None:
        self._wakeup.set()

    async def _run(self) -> None:
        while not self._stopping:
            try:
                await asyncio.wait_for(self._wakeup.wait(), timeout=self._poll_interval)
            except TimeoutError:
                pass
            self._wakeup.clear()
            await self.process_pending()

    async def process_pending(self, command_id: str | None = None) -> int:
        commands = await self._repository.fetch_pending_commands(self._batch_size)
        if command_id:
            commands = [command for command in commands if command.id == command_id] or commands
        processed = 0
        for command in commands:
            await self._supervisor.handle_command(command)
            processed += 1
        return processed

    async def stop(self) -> None:
        self._stopping = True
        self._wakeup.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._listener is not None:
            close = getattr(self._listener, "close", None)
            if close is not None:
                result = close()
                if asyncio.iscoroutine(result):
                    await result
            self._listener = None
