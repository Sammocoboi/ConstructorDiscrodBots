
import time
from typing import Any, Dict, List, Optional, Set, Tuple

class CommandAccessRule:

    def __init__(
        self,
        default_member_permissions: Optional[str] = None,
        allowed_roles: Optional[List[str]] = None,
        denied_roles: Optional[List[str]] = None,
        allowed_channels: Optional[List[str]] = None,
        denied_channels: Optional[List[str]] = None,
        allowed_users: Optional[List[str]] = None,
        denied_users: Optional[List[str]] = None,
        no_permission_message: str = "У вас недостаточно прав для использования этой команды."
    ):
        self.default_member_permissions = default_member_permissions
        self.allowed_roles = set(allowed_roles or [])
        self.denied_roles = set(denied_roles or [])
        self.allowed_channels = set(allowed_channels or [])
        self.denied_channels = set(denied_channels or [])
        self.allowed_users = set(allowed_users or [])
        self.denied_users = set(denied_users or [])
        self.no_permission_message = no_permission_message

    def is_allowed(
        self,
        user_id: str,
        user_roles: List[str],
        channel_id: str,
        user_permissions_int: int = 0
    ) -> Tuple[bool, Optional[str]]:
        if user_id in self.denied_users:
            return False, self.no_permission_message

        if self.allowed_users and user_id not in self.allowed_users:
            return False, self.no_permission_message

        if channel_id in self.denied_channels:
            return False, "Команда отключена в этом канале."
        if self.allowed_channels and channel_id not in self.allowed_channels:
            return False, "Команду можно использовать только в разрешенных каналах."

        user_role_set = set(user_roles)
        if self.denied_roles.intersection(user_role_set):
            return False, self.no_permission_message

        if self.allowed_roles and not self.allowed_roles.intersection(user_role_set):
            return False, self.no_permission_message

        if self.default_member_permissions:
            try:
                required = int(self.default_member_permissions)
                if (user_permissions_int & required) != required and (user_permissions_int & 0x8) != 0x8:
                    return False, self.no_permission_message
            except ValueError:
                pass

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "default_member_permissions": self.default_member_permissions,
            "allowed_roles": list(self.allowed_roles),
            "denied_roles": list(self.denied_roles),
            "allowed_channels": list(self.allowed_channels),
            "denied_channels": list(self.denied_channels),
            "allowed_users": list(self.allowed_users),
            "denied_users": list(self.denied_users),
            "no_permission_message": self.no_permission_message,
        }

class CommandCooldownTracker:

    def __init__(self):
        self._history: Dict[Tuple[str, str, str], List[float]] = {}

    def check_and_update(
        self,
        command_slug: str,
        scope: str,
        identifier: str,
        cooldown_seconds: int = 5,
        max_uses: int = 1,
        window_seconds: Optional[int] = None
    ) -> Tuple[bool, float]:
        now = time.time()
        window = window_seconds if window_seconds is not None else cooldown_seconds
        key = (scope, identifier, command_slug)

        timestamps = self._history.get(key, [])
        valid_timestamps = [t for t in timestamps if now - t < window]

        if len(valid_timestamps) >= max_uses:
            oldest_relevant = valid_timestamps[0]
            remaining = round(window - (now - oldest_relevant), 1)
            self._history[key] = valid_timestamps
            return False, max(0.1, remaining)

        valid_timestamps.append(now)
        self._history[key] = valid_timestamps
        return True, 0.0

    def reset(self, command_slug: str, scope: str, identifier: str) -> None:
        key = (scope, identifier, command_slug)
        self._history.pop(key, None)

default_cooldown_tracker = CommandCooldownTracker()
