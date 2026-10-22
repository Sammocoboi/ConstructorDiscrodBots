from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

_PATH_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_-]+)*)\}")


class FlowActions(Protocol):
    async def send_message(
        self,
        *,
        channel_id: str | None,
        content: str | None,
        embed: dict[str, Any] | None,
        ephemeral: bool,
    ) -> Any: ...

    async def send_dm(
        self,
        *,
        user_id: str,
        content: str | None,
        embed: dict[str, Any] | None,
    ) -> Any: ...

    async def add_role(self, *, user_id: str, role_id: str) -> None: ...

    async def remove_role(self, *, user_id: str, role_id: str) -> None: ...


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


@dataclass(slots=True)
class Context:
    user: dict[str, Any] = field(default_factory=dict)
    guild: dict[str, Any] = field(default_factory=dict)
    channel: dict[str, Any] = field(default_factory=dict)
    message: dict[str, Any] = field(default_factory=dict)
    args: dict[str, Any] = field(default_factory=dict)
    bot: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    flows: dict[str, dict[str, Any]] = field(default_factory=dict)
    actions: FlowActions | None = None
    dry_run: bool = False
    depth: int = 0

    def as_mapping(self) -> dict[str, Any]:
        mapping: dict[str, Any] = {"variables": self.variables}
        mapping.update(self.variables)
        mapping.update(
            {
                "user": self.user,
                "guild": self.guild,
                "channel": self.channel,
                "message": self.message,
                "args": self.args,
                "bot": self.bot,
            }
        )
        return mapping

    def get(self, path: str, default: Any = None) -> Any:
        current: Any = self.as_mapping()
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
                continue
            if isinstance(current, (list, tuple)) and part.isdigit():
                index = int(part)
                if -len(current) <= index < len(current):
                    current = current[index]
                    continue
            return default
        return current

    def set(self, name: str, value: Any) -> None:
        self.variables[name] = value

    def resolve(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        whole = _PATH_RE.fullmatch(value)
        if whole:
            return self.get(whole.group(1))
        return _PATH_RE.sub(lambda match: stringify(self.get(match.group(1))), value)

    def resolve_deep(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.resolve(value)
        if isinstance(value, list):
            return [self.resolve_deep(item) for item in value]
        if isinstance(value, dict):
            return {key: self.resolve_deep(item) for key, item in value.items()}
        return value
