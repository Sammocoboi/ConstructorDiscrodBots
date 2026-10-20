"""
Кэширование данных Discord (каналы, роли, эмодзи, гильдии) на 60 секунд.
Соответствие ТЗ §4.7 (FR-7.1) и задаче SAN-6.
"""

import time
from typing import Any, Callable, Dict, Optional, Tuple

class DiscordDataCache:
    """
    In-memory кэш для каналов, ролей и эмодзи Discord с TTL 60 секунд
    и поддержкой принудительного сброса.
    """

    def __init__(self, default_ttl: int = 60):
        self.default_ttl = default_ttl
        # Хранилище: ключ -> (значение, expires_at)
        self._cache: Dict[str, Tuple[Any, float]] = {}

    def _make_key(self, prefix: str, *args: str) -> str:
        return f"{prefix}:" + ":".join(args)

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, expires_at = self._cache[key]
            if time.time() < expires_at:
                return value
            # Истек срок жизни
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        duration = ttl if ttl is not None else self.default_ttl
        self._cache[key] = (value, time.time() + duration)

    def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)

    def invalidate_guild(self, guild_id: str) -> None:
        """Сброс кэша по гильдии (принудительное обновление по кнопке)."""
        prefix = f"guild:{guild_id}"
        keys_to_del = [k for k in self._cache if k.startswith(prefix)]
        for k in keys_to_del:
            del self._cache[k]

    def get_or_set(self, key: str, fetcher: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        fresh = fetcher()
        self.set(key, fresh, ttl)
        return fresh


default_discord_cache = DiscordDataCache(default_ttl=60)
