from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.bots.models import Bot, BotVersion


@pytest.mark.django_db
def test_create_save_publish_flow_for_runtime(auth_client: APIClient, user):
    bot = Bot.objects.create(owner=user, name="Demo bot")

    created = auth_client.post(
        f"/api/v1/bots/{bot.id}/flows",
        {"name": "Hello", "description": "Ответ в Discord"},
        format="json",
    )
    assert created.status_code == 201, created.data
    flow = created.data
    assert len(flow["nodes"]) == 2

    action = flow["nodes"][1]
    action["data"]["config"]["text"] = "Привет из Discord"
    saved = auth_client.put(
        f"/api/v1/bots/{bot.id}/flows/{flow['id']}",
        {"nodes": flow["nodes"], "edges": flow["edges"]},
        format="json",
    )
    assert saved.status_code == 200, saved.data

    validated = auth_client.post(
        f"/api/v1/bots/{bot.id}/flows/{flow['id']}/validate",
        {"nodes": flow["nodes"], "edges": flow["edges"]},
        format="json",
    )
    assert validated.status_code == 200, validated.data
    assert validated.data == []

    published = auth_client.post(
        f"/api/v1/bots/{bot.id}/flows/{flow['id']}/publish",
        {"comment": "Live demo"},
        format="json",
    )
    assert published.status_code == 200, published.data
    bot.refresh_from_db()
    assert bot.active_version is not None
    assert BotVersion.objects.filter(bot=bot).count() == 1

    content = bot.active_version.content
    assert content["commands"][0]["name"] == "hello"
    assert content["flows"][0]["trigger"]["type"] == "slash_command"
    assert content["flows"][0]["nodes"][1]["type"] == "send_message"
    assert content["flows"][0]["nodes"][1]["params"]["content"] == "Привет из Discord"


@pytest.mark.django_db
def test_flow_endpoints_are_scoped_to_bot_owner(
    other_auth_client: APIClient,
    user,
):
    bot = Bot.objects.create(owner=user, name="Private bot")
    response = other_auth_client.get(f"/api/v1/bots/{bot.id}/flows")
    assert response.status_code == 404
