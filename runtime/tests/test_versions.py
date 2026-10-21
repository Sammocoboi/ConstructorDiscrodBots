from __future__ import annotations

import pytest

from runtime.versions import (
    ConfigValidationError,
    InMemoryVersionRepository,
    VersionService,
    VersionStatus,
    diff_configs,
    validate_config,
)


def service(max_versions: int = 30) -> VersionService:
    return VersionService(InMemoryVersionRepository(), max_versions=max_versions)


def config(**extra):
    payload = {"schema_version": 1, "commands": [], "flows": []}
    payload.update(extra)
    return payload


async def test_save_draft_reuses_existing_draft():
    versions = service()
    first = await versions.save_draft("bot-1", config(), "first")
    second = await versions.save_draft("bot-1", config(profile={"status": "idle"}), "second")
    assert first.id == second.id
    assert second.number == 1
    assert second.comment == "second"
    assert second.config["profile"]["status"] == "idle"
    assert len(await versions.list_versions("bot-1")) == 1


async def test_publish_archives_previous_version():
    versions = service()
    first = await versions.save_draft("bot-1", config())
    published_first = await versions.publish(first.id)
    second = await versions.save_draft("bot-1", config(profile={"status": "idle"}))
    await versions.publish(second.id)
    all_versions = {item.id: item for item in await versions.list_versions("bot-1")}
    assert published_first.status is VersionStatus.ARCHIVED
    assert all_versions[second.id].status is VersionStatus.PUBLISHED


async def test_rollback_creates_draft_with_old_config():
    versions = service()
    first = await versions.save_draft("bot-1", config(profile={"status": "idle"}))
    await versions.publish(first.id)
    second = await versions.save_draft("bot-1", config(profile={"status": "dnd"}))
    await versions.publish(second.id)
    rollback = await versions.rollback(first.id)
    assert rollback.status is VersionStatus.DRAFT
    assert rollback.number == 3
    assert rollback.config == first.config


async def test_diff_versions():
    versions = service()
    first = await versions.save_draft("bot-1", config(profile={"status": "online"}))
    await versions.publish(first.id)
    second = await versions.save_draft(
        "bot-1",
        config(profile={"status": "idle"}, commands=[{"name": "ping"}]),
    )
    changes = await versions.diff(first.id, second.id)
    paths = {change.path for change in changes}
    assert "profile.status" in paths
    assert "commands" in paths


async def test_prune_keeps_latest_versions():
    versions = service(max_versions=3)
    for _index in range(5):
        draft = await versions.save_draft("bot-1", config(profile={"status": "online"}))
        await versions.publish(draft.id)
    remaining = await versions.list_versions("bot-1")
    assert len(remaining) <= 3
    assert remaining[0].number == 5


def test_validate_config_rejects_secrets_and_big_payload():
    with pytest.raises(ConfigValidationError):
        validate_config({"schema_version": 1, "password": "123"})
    with pytest.raises(ConfigValidationError):
        validate_config({"schema_version": 2})
    with pytest.raises(ConfigValidationError):
        validate_config({"schema_version": 1, "payload": "x" * (2 * 1024 * 1024 + 1)})


def test_diff_configs_nested():
    changes = diff_configs(
        {"a": {"b": 1, "c": 2}, "remove": True},
        {"a": {"b": 3}, "add": True},
    )
    assert [(change.path, change.change) for change in changes] == [
        ("a.b", "changed"),
        ("a.c", "removed"),
        ("add", "added"),
        ("remove", "removed"),
    ]
