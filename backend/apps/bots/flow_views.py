"""Minimal flow API used by the visual editor and Discord Runtime."""

from __future__ import annotations

import re
import uuid
from copy import deepcopy

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Bot, BotDraft, BotVersion, DesiredState
from .services import request_reload, request_restart


def _bot_for_user(request, bot_id, *, lock=False) -> Bot:
    bots = Bot.objects.filter(owner=request.user)
    if lock:
        bots = bots.select_for_update()
    return get_object_or_404(bots, id=bot_id)


def _author_name(user) -> str:
    return str(getattr(user, "display_name", "") or getattr(user, "email", ""))


def _draft_for(bot: Bot, user) -> BotDraft:
    draft, _ = BotDraft.objects.get_or_create(
        bot=bot,
        defaults={"content": {"flows": [], "commands": []}, "updated_by": user},
    )
    return draft


def _flow_list(draft: BotDraft) -> list[dict]:
    flows = draft.content.get("flows", []) if isinstance(draft.content, dict) else []
    return flows if isinstance(flows, list) else []


def _find_flow(draft: BotDraft, flow_id) -> dict | None:
    return next((flow for flow in _flow_list(draft) if str(flow.get("id")) == str(flow_id)), None)


def _save_draft(draft: BotDraft, user, flows: list[dict]) -> None:
    content = draft.content if isinstance(draft.content, dict) else {}
    content = {**content, "flows": flows}
    draft.content = content
    draft.updated_by = user
    draft.save(update_fields=["content", "updated_by", "updated_at"])


def _version(flow: dict, *, author: str, comment: str, state: str) -> dict:
    snapshot = {"nodes": deepcopy(flow.get("nodes", [])), "edges": deepcopy(flow.get("edges", []))}
    return {
        "id": str(uuid.uuid4()),
        "version": int(flow.get("version", 1)),
        "comment": comment,
        "author": author,
        "createdAt": timezone.now().isoformat(),
        "status": state,
        "nodeCount": len(snapshot["nodes"]),
        "edgeCount": len(snapshot["edges"]),
        "snapshot": snapshot,
    }


def _default_flow(bot: Bot, user, name: str, description: str) -> dict:
    flow_id = str(uuid.uuid4())
    trigger_id = str(uuid.uuid4())
    action_id = str(uuid.uuid4())
    flow = {
        "id": flow_id,
        "botId": str(bot.id),
        "name": name,
        "description": description,
        "status": "draft",
        "enabled": True,
        "version": 1,
        "updatedAt": timezone.now().isoformat(),
        "nodes": [
            {
                "id": trigger_id,
                "type": "block",
                "position": {"x": 40, "y": 40},
                "data": {
                    "blockId": "trigger.slash",
                    "label": "Slash-команда",
                    "config": {"commandName": "hello"},
                },
            },
            {
                "id": action_id,
                "type": "block",
                "position": {"x": 40, "y": 220},
                "data": {
                    "blockId": "action.send_message",
                    "label": "Отправить ответ",
                    "config": {"channelId": "", "text": "Привет! Это новый сценарий."},
                },
            },
        ],
        "edges": [{"id": str(uuid.uuid4()), "source": trigger_id, "target": action_id}],
        "versions": [],
    }
    flow["versions"] = [
        _version(flow, author=_author_name(user), comment="Создан черновик", state="draft")
    ]
    return flow


def _flow_issues(flow: dict, nodes=None, edges=None) -> list[dict]:
    graph_nodes = nodes if isinstance(nodes, list) else flow.get("nodes", [])
    graph_edges = edges if isinstance(edges, list) else flow.get("edges", [])
    issues: list[dict] = []
    node_ids = {str(node.get("id")) for node in graph_nodes if isinstance(node, dict)}
    triggers = [
        node for node in graph_nodes
        if isinstance(node, dict)
        and str(node.get("data", {}).get("blockId", "")).startswith("trigger.")
    ]
    actions = [
        node for node in graph_nodes
        if isinstance(node, dict)
        and str(node.get("data", {}).get("blockId", "")).startswith("action.")
    ]

    def add(code: str, message: str, severity: str = "error", node_id: str | None = None) -> None:
        item = {"id": f"{code}_{node_id}" if node_id else code, "code": code,
                "severity": severity, "message": message}
        if node_id:
            item["nodeId"] = node_id
        issues.append(item)

    if not graph_nodes:
        add("empty_flow", "Добавьте триггер и действие.")
    if not triggers:
        add("no_trigger", "Нет триггера. Сценарий не сможет запуститься.")
    if not actions:
        add("no_action", "Нет действий. Сценарий ничего не делает.", "warning")
    for node in triggers:
        data = node.get("data", {})
        config = data.get("config", {}) if isinstance(data, dict) else {}
        if data.get("blockId") == "trigger.slash":
            command_name = str(config.get("commandName", "")).strip()
            if not re.fullmatch(r"[a-z0-9_-]{1,32}", command_name):
                add("invalid_command_name", "Имя slash-команды: 1–32 символа, строчные латинские буквы, цифры, _ или -.", node_id=str(node.get("id")))
    for edge in graph_edges:
        if not isinstance(edge, dict) or str(edge.get("source")) not in node_ids or str(edge.get("target")) not in node_ids:
            add("dangling_edge", "Связь ссылается на отсутствующий блок.")
    return issues


def _snake_case(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def _runtime_flow(flow: dict) -> tuple[dict, dict | None]:
    trigger_node = next(
        (node for node in flow.get("nodes", [])
         if str(node.get("data", {}).get("blockId", "")).startswith("trigger.")),
        None,
    )
    trigger_data = trigger_node.get("data", {}) if trigger_node else {}
    trigger_id = str(trigger_node.get("id")) if trigger_node else ""
    trigger_block = str(trigger_data.get("blockId", ""))
    trigger_config = trigger_data.get("config", {}) if isinstance(trigger_data, dict) else {}
    runtime_trigger: dict = {"type": "message"}
    command = None
    command_id = str(flow["id"])

    if trigger_block == "trigger.slash":
        runtime_trigger = {"type": "slash_command", "command_id": command_id}
        command = {
            "id": command_id,
            "name": str(trigger_config.get("commandName", "hello")).strip().lower(),
            "description": str(flow.get("description") or flow.get("name") or "Команда конструктора")[:100],
            "options": [],
            "flow_id": str(flow["id"]),
        }
        trigger_type = "slash_command"
    elif trigger_block == "trigger.member_join":
        runtime_trigger = {"type": "join_member"}
        trigger_type = "join_member"
    elif trigger_block == "trigger.message":
        runtime_trigger = {"type": "message", "contains": str(trigger_config.get("contains", ""))}
        trigger_type = "message"
    else:
        trigger_type = "message"

    runtime_nodes = []
    for node in flow.get("nodes", []):
        data = node.get("data", {}) if isinstance(node, dict) else {}
        block_id = str(data.get("blockId", ""))
        config = data.get("config", {}) if isinstance(data, dict) else {}
        if block_id == "trigger.slash":
            block_type = "slash_command"
            params = {"command_id": command_id}
        elif block_id == "trigger.member_join":
            block_type = "join_member"
            params = {}
        elif block_id == "trigger.message":
            block_type = "message"
            params = {
                "prefix": config.get("prefix", ""),
                "contains": config.get("contains", ""),
                "regex": config.get("regex", ""),
            }
        else:
            block_type = "send_dm" if block_id == "action.dm" else block_id.split(".", 1)[-1]
            params = {_snake_case(str(key)): value for key, value in config.items()}
            if "text" in params and "content" not in params:
                params["content"] = params.pop("text")
            if not params.get("channel_id"):
                params.pop("channel_id", None)
        runtime_nodes.append({"id": str(node.get("id")), "type": block_type, "params": params})

    runtime_edges = [
        {"from": str(edge.get("source")), "to": str(edge.get("target"))}
        for edge in flow.get("edges", []) if isinstance(edge, dict)
    ]
    return {
        "id": str(flow["id"]),
        "name": str(flow.get("name", "")),
        "description": str(flow.get("description", "")),
        "enabled": flow.get("enabled", True),
        "trigger": runtime_trigger,
        "trigger_node_id": trigger_id,
        "trigger_type": trigger_type,
        "nodes": runtime_nodes,
        "edges": runtime_edges,
    }, command


def _active_content(bot: Bot) -> dict:
    content = bot.active_version.content if bot.active_version_id else None
    return content if isinstance(content, dict) else {}


def _without_runtime_flow(content: dict, flow_id: str) -> dict:
    return {
        **content,
        "flows": [flow for flow in content.get("flows", []) if str(flow.get("id")) != flow_id],
        "commands": [
            command for command in content.get("commands", [])
            if str(command.get("flow_id")) != flow_id
        ],
    }


def _privileged_triggers(content: dict) -> set[str]:
    return {
        flow["trigger"]["type"]
        for flow in content.get("flows", [])
        if flow.get("enabled", True) and flow.get("trigger", {}).get("type") in {"message", "join_member"}
    }


def _activate_content(bot: Bot, content: dict, user, comment: str) -> None:
    needs_reconnect = bool(_privileged_triggers(content) - _privileged_triggers(_active_content(bot)))
    latest = bot.versions.order_by("-version_number").first()
    bot.active_version = BotVersion.objects.create(
        bot=bot,
        version_number=latest.version_number + 1 if latest else 1,
        content=content,
        comment=comment[:255],
        created_by=user,
    )
    bot.save(update_fields=["active_version", "updated_at"])
    if bot.desired_state == DesiredState.RUNNING:
        if needs_reconnect:
            request_restart(bot, user)
        else:
            request_reload(bot, user)


def _set_enabled(bot: Bot, draft: BotDraft, flow: dict, user, enabled) -> Response:
    if not isinstance(enabled, bool):
        return Response({"message": "Укажите, включён ли сценарий."}, status=status.HTTP_400_BAD_REQUEST)
    content = _active_content(bot)
    runtime_flows = deepcopy(content.get("flows", []))
    runtime_flow = next((item for item in runtime_flows if str(item.get("id")) == str(flow["id"])), None)
    if flow.get("status") != "published" or runtime_flow is None:
        return Response(
            {"message": "Сначала опубликуйте сценарий."},
            status=status.HTTP_409_CONFLICT,
        )
    if flow.get("enabled", True) == enabled and runtime_flow.get("enabled", True) == enabled:
        return Response(flow)
    flow["enabled"] = enabled
    runtime_flow["enabled"] = enabled
    _save_draft(draft, user, _flow_list(draft))
    _activate_content(
        bot, {**content, "flows": runtime_flows}, user,
        f"{'Включён' if enabled else 'Выключен'} сценарий: {flow['name']}",
    )
    return Response(flow)


def _publish(bot: Bot, draft: BotDraft, flow: dict, user, comment: str) -> Response:
    issues = _flow_issues(flow)
    blocking = [issue for issue in issues if issue["severity"] == "error"]
    if blocking:
        return Response(
            {"code": "flow_invalid", "message": "Сценарий содержит ошибки.", "details": blocking},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    flow["version"] = int(flow.get("version", 1)) + 1
    flow["status"] = "published"
    flow["updatedAt"] = timezone.now().isoformat()
    for version in flow.get("versions", []):
        if version.get("status") == "published":
            version["status"] = "archived"
    flow.setdefault("versions", []).insert(
        0,
        _version(flow, author=_author_name(user), comment=comment or "Публикация", state="published"),
    )
    _save_draft(draft, user, _flow_list(draft))
    base = _active_content(bot) if bot.active_version_id else {**draft.content, "flows": [], "commands": []}
    content = _without_runtime_flow(base, str(flow["id"]))
    runtime_flow, command = _runtime_flow(flow)
    content["flows"].append(runtime_flow)
    if command:
        content["commands"].append(command)
    _activate_content(bot, content, user, comment or f"Published flow: {flow.get('name', '')}")
    return Response(flow)


class BotFlowListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, bot_id):
        bot = _bot_for_user(request, bot_id)
        draft = _draft_for(bot, request.user)
        return Response(sorted(_flow_list(draft), key=lambda item: item.get("updatedAt", ""), reverse=True))

    @transaction.atomic
    def post(self, request, bot_id):
        bot = _bot_for_user(request, bot_id, lock=True)
        draft = _draft_for(bot, request.user)
        name = str(request.data.get("name") or "Новый сценарий")[:100]
        description = str(request.data.get("description") or "Черновик сценария.")[:500]
        flow = _default_flow(bot, request.user, name, description)
        _save_draft(draft, request.user, [*_flow_list(draft), flow])
        return Response(flow, status=status.HTTP_201_CREATED)


class BotFlowDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, bot_id, flow_id):
        bot = _bot_for_user(request, bot_id)
        flow = _find_flow(_draft_for(bot, request.user), flow_id)
        return Response(flow) if flow else Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, bot_id, flow_id):
        return self._save(request, bot_id, flow_id)

    def patch(self, request, bot_id, flow_id):
        return self._save(request, bot_id, flow_id, partial=True)

    @transaction.atomic
    def _save(self, request, bot_id, flow_id, *, partial=False):
        bot = _bot_for_user(request, bot_id, lock=True)
        draft = _draft_for(bot, request.user)
        flow = _find_flow(draft, flow_id)
        if not flow:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not partial or "nodes" in request.data or "edges" in request.data:
            if not isinstance(request.data.get("nodes"), list) or not isinstance(request.data.get("edges"), list):
                return Response({"message": "nodes and edges must be arrays"}, status=status.HTTP_400_BAD_REQUEST)
            flow["nodes"] = request.data["nodes"]
            flow["edges"] = request.data["edges"]
        if request.data.get("name") is not None:
            name = request.data["name"]
            if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
                return Response(
                    {"message": "Введите название сценария длиной от 1 до 100 символов."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            flow["name"] = name.strip()
        if request.data.get("description") is not None:
            flow["description"] = str(request.data["description"])[:500]
        flow["updatedAt"] = timezone.now().isoformat()
        _save_draft(draft, request.user, _flow_list(draft))
        return Response(flow)

    @transaction.atomic
    def delete(self, request, bot_id, flow_id):
        bot = _bot_for_user(request, bot_id, lock=True)
        draft = _draft_for(bot, request.user)
        flows = [flow for flow in _flow_list(draft) if str(flow.get("id")) != str(flow_id)]
        if len(flows) == len(_flow_list(draft)):
            return Response(status=status.HTTP_404_NOT_FOUND)
        _save_draft(draft, request.user, flows)
        content = _active_content(bot)
        updated_content = _without_runtime_flow(content, str(flow_id))
        if len(updated_content["flows"]) != len(content.get("flows", [])):
            _activate_content(bot, updated_content, request.user, "Сценарий удалён")
        return Response(status=status.HTTP_204_NO_CONTENT)


class BotFlowActionView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, bot_id, flow_id, action):
        bot = _bot_for_user(request, bot_id, lock=action in {"publish", "rollback", "enabled"})
        draft = _draft_for(bot, request.user)
        flow = _find_flow(draft, flow_id)
        if not flow:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if action == "enabled":
            return _set_enabled(bot, draft, flow, request.user, request.data.get("enabled"))
        nodes = request.data.get("nodes")
        edges = request.data.get("edges")
        issues = _flow_issues(flow, nodes, edges)

        if action == "validate":
            return Response(issues)
        if action == "test":
            graph_nodes = nodes if isinstance(nodes, list) else flow.get("nodes", [])
            errors = [issue for issue in issues if issue["severity"] == "error"]
            steps = [
                {
                    "id": f"step_{index}",
                    "nodeId": node.get("id"),
                    "title": node.get("data", {}).get("label", "Блок"),
                    "status": "error" if errors and index == 0 else "ok",
                    "detail": "Обязательные поля не заполнены." if errors and index == 0 else "Блок выполнен в тестовом режиме.",
                }
                for index, node in enumerate(graph_nodes)
            ]
            return Response({
                "success": not errors,
                "durationMs": 1,
                "steps": steps,
                "variables": {},
                "output": next(
                    (str(node.get("data", {}).get("config", {}).get("text", ""))
                     for node in graph_nodes if node.get("data", {}).get("blockId") == "action.send_message"),
                    "",
                ),
            })
        if action == "publish":
            return _publish(bot, draft, flow, request.user, str(request.data.get("comment") or ""))
        if action == "rollback":
            version_id = str(request.data.get("versionId", ""))
            target = next((item for item in flow.get("versions", []) if str(item.get("id")) == version_id), None)
            if not target:
                return Response({"message": "Flow version not found"}, status=status.HTTP_404_NOT_FOUND)
            snapshot = target.get("snapshot", {})
            flow["nodes"] = snapshot.get("nodes", [])
            flow["edges"] = snapshot.get("edges", [])
            flow["updatedAt"] = timezone.now().isoformat()
            return _publish(bot, draft, flow, request.user, f"Rollback to v{target.get('version')}")
        return Response({"message": "Unknown flow action"}, status=status.HTTP_404_NOT_FOUND)
