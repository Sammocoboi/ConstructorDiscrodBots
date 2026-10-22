from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class BotStatus(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    ONLINE = "online"
    ERROR = "error"
    SUSPENDED = "suspended"


class DesiredState(StrEnum):
    RUNNING = "running"
    STOPPED = "stopped"


class CommandStatus(StrEnum):
    PENDING = "pending"
    ACKED = "acked"
    DONE = "done"
    FAILED = "failed"


@dataclass(slots=True)
class BotSpec:
    id: str
    name: str
    token: str
    config: dict[str, Any] = field(default_factory=dict)
    desired_state: str = DesiredState.RUNNING


@dataclass(slots=True)
class RuntimeCommand:
    id: str
    bot_id: str
    command: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: str = CommandStatus.PENDING
    error: str | None = None
