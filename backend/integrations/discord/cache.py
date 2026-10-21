
import time
from collections.abc import Callable
from typing import Any


class DiscordDataCache:

    def __init__(self, default_ttl: int = 60):
        self.default_ttl = default_ttl
        self._cache: dict[str, tuple[Any, float]] = {}

    def _make_key(self, prefix: str, *args: str) -> str:
        return f"{prefix}:" + ":".join(args)

    def get(self, key: str) -> Any | None:
        if key in self._cache:
            value, expires_at = self._cache[key]
            if time.time() < expires_at:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        duration = ttl if ttl is not None else self.default_ttl
        self._cache[key] = (value, time.time() + duration)

    def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)

    def invalidate_guild(self, guild_id: str) -> None:
        prefix = f"guild:{guild_id}"
        keys_to_del = [k for k in self._cache if k.startswith(prefix)]
        for k in keys_to_del:
            del self._cache[k]

    def get_or_set(self, key: str, fetcher: Callable[[], Any], ttl: int | None = None) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        fresh = fetcher()
        self.set(key, fresh, ttl)
        return fresh

default_discord_cache = DiscordDataCache(default_ttl=60)
