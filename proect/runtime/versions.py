from __future__ import annotations

import copy
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from runtime.secrets import find_secrets

MAX_VERSIONS = 30
MAX_CONFIG_BYTES = 2 * 1024 * 1024


class VersionStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@dataclass(slots=True)
class BotVersion:
    id: str
    bot_id: str
    number: int
    status: VersionStatus
    config: dict[str, Any]
    comment: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ConfigDiff:
    path: str
    change: str
    before: Any = None
    after: Any = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "change": self.change,
            "before": self.before,
            "after": self.after,
        }


class ConfigValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class VersionRepository(Protocol):
    async def list_versions(self, bot_id: str) -> list[BotVersion]: ...

    async def get_version(self, version_id: str) -> BotVersion | None: ...

    async def create_version(self, version: BotVersion) -> BotVersion: ...

    async def update_version(self, version: BotVersion) -> BotVersion: ...

    async def delete_version(self, version_id: str) -> None: ...

    async def set_active_version(self, bot_id: str, version_id: str) -> None: ...


def validate_config(config: dict[str, Any]) -> None:
    errors: list[str] = []
    if not isinstance(config, dict):
        raise ConfigValidationError(["config must be an object"])
    if config.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    try:
        payload = json.dumps(config, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ConfigValidationError([f"config is not JSON serializable: {exc}"]) from exc
    if len(payload) > MAX_CONFIG_BYTES:
        errors.append("config exceeds 2 MB")
    errors.extend(find_secrets(config))
    if errors:
        raise ConfigValidationError(errors)


def diff_configs(
    before: dict[str, Any],
    after: dict[str, Any],
    path: str = "",
) -> list[ConfigDiff]:
    changes: list[ConfigDiff] = []
    keys = set(before) | set(after)
    for key in sorted(keys, key=str):
        current_path = f"{path}.{key}" if path else str(key)
        if key not in before:
            changes.append(ConfigDiff(current_path, "added", after=after[key]))
        elif key not in after:
            changes.append(ConfigDiff(current_path, "removed", before=before[key]))
        else:
            left, right = before[key], after[key]
            if left == right:
                continue
            if isinstance(left, dict) and isinstance(right, dict):
                changes.extend(diff_configs(left, right, current_path))
            else:
                changes.append(ConfigDiff(current_path, "changed", before=left, after=right))
    return changes


class InMemoryVersionRepository:
    def __init__(self) -> None:
        self.versions: dict[str, BotVersion] = {}
        self.active: dict[str, str] = {}

    async def list_versions(self, bot_id: str) -> list[BotVersion]:
        versions = [version for version in self.versions.values() if version.bot_id == bot_id]
        return sorted(versions, key=lambda version: version.number, reverse=True)

    async def get_version(self, version_id: str) -> BotVersion | None:
        return self.versions.get(version_id)

    async def create_version(self, version: BotVersion) -> BotVersion:
        self.versions[version.id] = version
        return version

    async def update_version(self, version: BotVersion) -> BotVersion:
        self.versions[version.id] = version
        return version

    async def delete_version(self, version_id: str) -> None:
        self.versions.pop(version_id, None)

    async def set_active_version(self, bot_id: str, version_id: str) -> None:
        self.active[bot_id] = version_id


class VersionService:
    def __init__(
        self,
        repository: VersionRepository,
        *,
        validator: Callable[[dict[str, Any]], None] = validate_config,
        max_versions: int = MAX_VERSIONS,
    ) -> None:
        self._repository = repository
        self._validator = validator
        self._max_versions = max_versions

    async def list_versions(self, bot_id: str) -> list[BotVersion]:
        return await self._repository.list_versions(bot_id)

    async def save_draft(
        self,
        bot_id: str,
        config: dict[str, Any],
        comment: str = "",
    ) -> BotVersion:
        self._validator(config)
        versions = await self._repository.list_versions(bot_id)
        draft = next(
            (version for version in versions if version.status is VersionStatus.DRAFT),
            None,
        )
        if draft is not None:
            draft.config = copy.deepcopy(config)
            draft.comment = comment
            draft.created_at = datetime.now(UTC)
            return await self._repository.update_version(draft)
        version = await self._new_version(bot_id, config, comment, versions)
        await self._prune(bot_id)
        return version

    async def publish(self, version_id: str) -> BotVersion:
        version = await self._require(version_id)
        versions = await self._repository.list_versions(version.bot_id)
        for other in versions:
            if other.id != version.id and other.status is VersionStatus.PUBLISHED:
                other.status = VersionStatus.ARCHIVED
                await self._repository.update_version(other)
        version.status = VersionStatus.PUBLISHED
        await self._repository.update_version(version)
        await self._repository.set_active_version(version.bot_id, version.id)
        return version

    async def rollback(self, version_id: str, comment: str = "") -> BotVersion:
        target = await self._require(version_id)
        versions = await self._repository.list_versions(target.bot_id)
        note = comment or f"Rollback to v{target.number}"
        return await self._new_version(target.bot_id, target.config, note, versions)

    async def diff(self, from_version_id: str, to_version_id: str) -> list[ConfigDiff]:
        left = await self._require(from_version_id)
        right = await self._require(to_version_id)
        return diff_configs(left.config, right.config)

    async def _require(self, version_id: str) -> BotVersion:
        version = await self._repository.get_version(version_id)
        if version is None:
            raise KeyError(f"version not found: {version_id}")
        return version

    async def _new_version(
        self,
        bot_id: str,
        config: dict[str, Any],
        comment: str,
        versions: list[BotVersion],
    ) -> BotVersion:
        number = max((version.number for version in versions), default=0) + 1
        version = BotVersion(
            id=str(uuid.uuid4()),
            bot_id=bot_id,
            number=number,
            status=VersionStatus.DRAFT,
            config=copy.deepcopy(config),
            comment=comment,
        )
        return await self._repository.create_version(version)

    async def _prune(self, bot_id: str) -> None:
        versions = await self._repository.list_versions(bot_id)
        for version in versions[self._max_versions :]:
            if version.status is VersionStatus.PUBLISHED:
                continue
            await self._repository.delete_version(version.id)
