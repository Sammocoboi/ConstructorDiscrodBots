from dataclasses import dataclass, field
from typing import Any


@dataclass
class Context:
    user: dict[str, Any] = field(default_factory=dict)
    guild: dict[str, Any] = field(default_factory=dict)
    channel: dict[str, Any] = field(default_factory=dict)
    args: dict[str, Any] = field(default_factory=dict)
    message: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)

    def resolve(self, template: str) -> str:
        """Подставляет {user.id}, {guild.name} и т.д."""
        result = template
        for key, value in self._flatten():
            result = result.replace("{" + key + "}", str(value))
        return result

    def _flatten(self):
        for section in ("user", "guild", "channel", "args", "message"):
            data = getattr(self, section)
            for k, v in data.items():
                yield f"{section}.{k}", v