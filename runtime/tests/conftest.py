from __future__ import annotations

from typing import Any

import pytest

from runtime.interpreter.handlers import build_default_registry
from runtime.interpreter.registry import BlockRegistry


class FakeActions:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
        self.dms: list[dict[str, Any]] = []
        self.roles_added: list[dict[str, Any]] = []
        self.roles_removed: list[dict[str, Any]] = []

    async def send_message(
        self,
        *,
        channel_id: str | None,
        content: str | None,
        embed: dict[str, Any] | None,
        ephemeral: bool,
    ) -> None:
        self.messages.append(
            {
                "channel_id": channel_id,
                "content": content,
                "embed": embed,
                "ephemeral": ephemeral,
            }
        )

    async def send_dm(
        self,
        *,
        user_id: str,
        content: str | None,
        embed: dict[str, Any] | None,
    ) -> None:
        self.dms.append({"user_id": user_id, "content": content, "embed": embed})

    async def add_role(self, *, user_id: str, role_id: str) -> None:
        self.roles_added.append({"user_id": user_id, "role_id": role_id})

    async def remove_role(self, *, user_id: str, role_id: str) -> None:
        self.roles_removed.append({"user_id": user_id, "role_id": role_id})


@pytest.fixture
def registry() -> BlockRegistry:
    return build_default_registry(BlockRegistry())


@pytest.fixture
def actions() -> FakeActions:
    return FakeActions()
