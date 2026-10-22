from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.bots.models import Bot, RuntimeCommand


@pytest.mark.django_db
def test_bot_crud_is_scoped_to_owner(auth_client: APIClient, other_auth_client: APIClient):
    created = auth_client.post("/api/v1/bots/", {"name": "Мой бот"}, format="json")
    assert created.status_code == 201, created.data
    bot_id = created.data["id"]
    assert created.data["name"] == "Мой бот"
    assert created.data["has_token"] is False
    assert "token_encrypted" not in created.data

    listed = auth_client.get("/api/v1/bots/")
    assert listed.status_code == 200
    assert len(listed.data["results"]) == 1

    other_list = other_auth_client.get("/api/v1/bots/")
    assert other_list.status_code == 200
    assert other_list.data["results"] == []

    # IDOR: чужой бот недоступен даже по UUID.
    assert other_auth_client.get(f"/api/v1/bots/{bot_id}/").status_code == 404
    assert (
        other_auth_client.patch(
            f"/api/v1/bots/{bot_id}/", {"name": "Угнан"}, format="json"
        ).status_code
        == 404
    )
    assert other_auth_client.delete(f"/api/v1/bots/{bot_id}/").status_code == 404


@pytest.mark.django_db
def test_bot_lifecycle_creates_runtime_commands(auth_client: APIClient):
    created = auth_client.post("/api/v1/bots/", {"name": "Lifecycle"}, format="json")
    bot_id = created.data["id"]

    started = auth_client.post(f"/api/v1/bots/{bot_id}/start/", {}, format="json")
    assert started.status_code == 202, started.data
    assert started.data["bot"]["desired_state"] == "running"
    assert started.data["bot"]["status"] == "starting"
    assert started.data["runtime_command"]["command"] == "start"
    assert (
        RuntimeCommand.objects.filter(bot_id=bot_id, command=RuntimeCommand.Command.START).count()
        == 1
    )

    status = auth_client.get(f"/api/v1/bots/{bot_id}/status/")
    assert status.status_code == 200
    assert status.data["status"] == "starting"
    assert status.data["runtime"] is None

    stopped = auth_client.post(f"/api/v1/bots/{bot_id}/stop/", {}, format="json")
    assert stopped.status_code == 202
    assert stopped.data["bot"]["desired_state"] == "stopped"
    assert stopped.data["runtime_command"]["command"] == "stop"

    restarted = auth_client.post(f"/api/v1/bots/{bot_id}/restart/", {}, format="json")
    assert restarted.status_code == 202
    assert restarted.data["runtime_command"]["command"] == "restart"
    assert RuntimeCommand.objects.filter(bot_id=bot_id).count() == 3


@pytest.mark.django_db
def test_soft_deleted_bot_is_not_listed(auth_client: APIClient):
    created = auth_client.post("/api/v1/bots/", {"name": "Удаляемый"}, format="json")
    bot_id = created.data["id"]
    assert auth_client.delete(f"/api/v1/bots/{bot_id}/").status_code == 204
    assert auth_client.get(f"/api/v1/bots/{bot_id}/").status_code == 404
    assert Bot.objects.count() == 0
    assert Bot.all_objects.filter(id=bot_id).count() == 1
