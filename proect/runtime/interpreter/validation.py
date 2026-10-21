from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from runtime.interpreter.registry import BlockRegistry, UnknownBlockError
from runtime.secrets import find_secrets

MAX_CONFIG_BYTES = 2 * 1024 * 1024
MESSAGE_LIMIT = 2000
EMBED_TOTAL_LIMIT = 6000
MAX_EMBEDS = 10
MAX_FIELDS = 25
COMMAND_NAME_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
VALID_PROFILE_STATUSES = {"online", "idle", "dnd", "invisible"}
CONDITION_TYPES = {"if", "switch", "random_chance"}
TERMINAL_CATEGORIES = {"action", "data", "logic"}


@dataclass(slots=True)
class Issue:
    code: str
    message: str
    node_id: str | None = None
    severity: str = "error"

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }
        if self.node_id is not None:
            payload["node_id"] = self.node_id
        return payload


@dataclass(slots=True)
class ValidationResult:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, code: str, message: str, node_id: str | None = None) -> None:
        self.errors.append(Issue(code, message, node_id, "error"))

    def warning(self, code: str, message: str, node_id: str | None = None) -> None:
        self.warnings.append(Issue(code, message, node_id, "warning"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [issue.as_dict() for issue in self.errors],
            "warnings": [issue.as_dict() for issue in self.warnings],
        }


def _collect_incoming(edges: list[dict[str, Any]]) -> dict[str, int]:
    incoming: dict[str, int] = {}
    for edge in edges:
        target = str(edge.get("to"))
        incoming[target] = incoming.get(target, 0) + 1
    return incoming


def _find_cycles(nodes: dict[str, dict[str, Any]], edges: list[dict[str, Any]]) -> list[list[str]]:
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    for edge in edges:
        source = str(edge.get("from"))
        target = str(edge.get("to"))
        if source in adjacency and target in nodes:
            adjacency[source].append(target)

    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(node_id: str) -> None:
        if node_id in visiting:
            if node_id in stack:
                cycles.append(stack[stack.index(node_id) :] + [node_id])
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        stack.append(node_id)
        for target in adjacency.get(node_id, []):
            visit(target)
        stack.pop()
        visiting.discard(node_id)
        visited.add(node_id)

    for node_id in nodes:
        visit(node_id)
    return cycles


def _validate_embed(embed: dict[str, Any], path: str, result: ValidationResult) -> None:
    title = embed.get("title")
    if isinstance(title, str) and len(title) > 256:
        result.error("embed_title_too_long", f"{path}.title exceeds 256 characters")
    description = embed.get("description")
    if isinstance(description, str) and len(description) > 4096:
        result.error("embed_description_too_long", f"{path}.description exceeds 4096 characters")
    footer = embed.get("footer")
    if isinstance(footer, dict) and isinstance(footer.get("text"), str):
        if len(footer["text"]) > 2048:
            result.error("embed_footer_too_long", f"{path}.footer.text exceeds 2048 characters")
    author = embed.get("author")
    if isinstance(author, dict) and isinstance(author.get("name"), str):
        if len(author["name"]) > 256:
            result.error("embed_author_too_long", f"{path}.author.name exceeds 256 characters")
    fields = embed.get("fields")
    if isinstance(fields, list):
        if len(fields) > MAX_FIELDS:
            result.error("embed_too_many_fields", f"{path}.fields exceeds {MAX_FIELDS}")
        for index, item in enumerate(fields):
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("name"), str) and len(item["name"]) > 256:
                result.error(
                    "embed_field_name_too_long",
                    f"{path}.fields[{index}].name exceeds 256 characters",
                )
            if isinstance(item.get("value"), str) and len(item["value"]) > 1024:
                result.error(
                    "embed_field_value_too_long",
                    f"{path}.fields[{index}].value exceeds 1024 characters",
                )


def _validate_embed_limits(embed: Any, result: ValidationResult, path: str = "embed") -> None:
    if embed is None:
        return
    if isinstance(embed, list):
        if len(embed) > MAX_EMBEDS:
            result.error("too_many_embeds", f"{path} exceeds {MAX_EMBEDS} embeds")
        for index, item in enumerate(embed):
            if isinstance(item, dict):
                _validate_embed(item, f"{path}[{index}]", result)
        if len(json.dumps(embed, ensure_ascii=False)) > EMBED_TOTAL_LIMIT:
            result.warning("embed_total_soft_limit", f"{path} is close to Discord limits")
        return
    if isinstance(embed, dict):
        _validate_embed(embed, path, result)


def _validate_node_params(
    node_id: str,
    node_type: str,
    params: dict[str, Any],
    manifest: dict[str, Any],
    result: ValidationResult,
) -> None:
    schema = manifest.get("params")
    if not isinstance(schema, dict):
        return
    for name, definition in schema.items():
        if not isinstance(definition, dict):
            continue
        required = bool(definition.get("required", False))
        if required and name not in params:
            result.error(
                "missing_param",
                f"node {node_id}: missing required param '{name}'",
                node_id,
            )
        if name not in params:
            continue
        value = params[name]
        max_length = definition.get("max_length")
        if isinstance(max_length, int) and isinstance(value, str) and len(value) > max_length:
            result.error(
                "param_too_long",
                f"node {node_id}: param '{name}' exceeds {max_length} characters",
                node_id,
            )
        expected = definition.get("type")
        if expected == "string" and not isinstance(value, str):
            result.error("param_type", f"node {node_id}: '{name}' must be a string", node_id)
        elif expected == "boolean" and not isinstance(value, bool):
            result.error("param_type", f"node {node_id}: '{name}' must be a boolean", node_id)
        elif expected == "number" and not isinstance(value, (int, float)):
            result.error("param_type", f"node {node_id}: '{name}' must be a number", node_id)
        elif expected in {"channel", "role", "user"} and not isinstance(value, str):
            result.error("param_type", f"node {node_id}: '{name}' must be an id string", node_id)
    for name in params:
        if name not in schema:
            result.warning(
                "unknown_param",
                f"node {node_id}: unknown param '{name}' for block {node_type}",
                node_id,
            )

    if node_type in {"send_message", "send_dm"}:
        content = params.get("content")
        if isinstance(content, str) and len(content) > MESSAGE_LIMIT:
            result.error(
                "message_too_long",
                f"node {node_id}: content exceeds {MESSAGE_LIMIT} characters",
                node_id,
            )
        _validate_embed_limits(params.get("embed"), result, f"{node_id}.embed")


def validate_flow(
    flow: dict[str, Any],
    registry: BlockRegistry,
    *,
    bot_permissions: set[str] | None = None,
) -> ValidationResult:
    result = ValidationResult()
    if not isinstance(flow, dict):
        result.error("invalid_flow", "flow must be an object")
        return result

    if not isinstance(flow.get("id"), str) or not flow["id"]:
        result.error("missing_flow_id", "flow.id is required")

    nodes_list = flow.get("nodes")
    if not isinstance(nodes_list, list) or not nodes_list:
        result.error("missing_nodes", "flow.nodes must be a non-empty list")
        return result

    nodes: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes_list):
        if not isinstance(node, dict):
            result.error("invalid_node", f"nodes[{index}] must be an object")
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            result.error("missing_node_id", f"nodes[{index}] has no id")
            continue
        if node_id in nodes:
            result.error("duplicate_node_id", f"duplicate node id: {node_id}", node_id)
            continue
        nodes[node_id] = node
        node_type = node.get("type")
        if not isinstance(node_type, str) or not node_type:
            result.error("missing_node_type", f"node {node_id} has no type", node_id)
            continue
        try:
            manifest = registry.get_manifest(node_type)
        except UnknownBlockError:
            result.error(
                "unknown_block",
                f"node {node_id}: unknown block type {node_type}",
                node_id,
            )
            continue
        params = node.get("params", {})
        if not isinstance(params, dict):
            result.error("invalid_params", f"node {node_id}: params must be an object", node_id)
            continue
        _validate_node_params(node_id, node_type, params, manifest, result)
        permissions = manifest.get("permissions", [])
        if bot_permissions is not None and isinstance(permissions, list):
            missing = sorted(str(item) for item in permissions if str(item) not in bot_permissions)
            if missing:
                result.warning(
                    "missing_permissions",
                    f"node {node_id}: bot lacks permissions: {', '.join(missing)}",
                    node_id,
                )

    edges_raw = flow.get("edges", [])
    if not isinstance(edges_raw, list):
        result.error("invalid_edges", "flow.edges must be a list")
        edges_raw = []
    edges: list[dict[str, Any]] = []
    for index, edge in enumerate(edges_raw):
        if not isinstance(edge, dict) or "from" not in edge or "to" not in edge:
            result.error("invalid_edge", f"edges[{index}] must have from and to")
            continue
        source = str(edge["from"])
        target = str(edge["to"])
        if source not in nodes:
            result.error("dangling_edge", f"edge source {source} does not exist")
            continue
        if target not in nodes:
            result.error("dangling_edge", f"edge target {target} does not exist")
            continue
        edges.append(edge)

    incoming = _collect_incoming(edges)
    start_id = flow.get("start")
    start_nodes = [start_id] if isinstance(start_id, str) and start_id in nodes else []
    if not start_nodes:
        trigger_nodes: list[str] = []
        for node_id, node in nodes.items():
            try:
                manifest = registry.get_manifest(str(node.get("type", "")))
            except UnknownBlockError:
                continue
            if manifest.get("category") == "trigger":
                trigger_nodes.append(node_id)
        start_nodes = trigger_nodes or [node_id for node_id in nodes if node_id not in incoming]
    if not start_nodes:
        result.error("no_start_node", "flow has no start node (all nodes are in a cycle)")

    reachable: set[str] = set()
    stack = list(start_nodes)
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    for edge in edges:
        adjacency[str(edge["from"])].append(str(edge["to"]))
    while stack:
        node_id = stack.pop()
        if node_id in reachable:
            continue
        reachable.add(node_id)
        stack.extend(adjacency.get(node_id, []))
    for node_id in nodes:
        if node_id not in reachable:
            result.warning("unreachable_node", f"node {node_id} is unreachable", node_id)

    cycles = _find_cycles(nodes, edges)
    if cycles:
        preview = " -> ".join(cycles[0])
        result.error("cycle_detected", f"flow contains a cycle: {preview}")

    for node_id, node in nodes.items():
        node_type = str(node.get("type", ""))
        outgoing = [edge for edge in edges if str(edge["from"]) == node_id]
        branches = {str(edge.get("branch")) for edge in outgoing if edge.get("branch") is not None}
        if node_type == "if":
            for branch in ("true", "false"):
                if branch not in branches:
                    result.error(
                        "unfinished_branch",
                        f"node {node_id}: no '{branch}' branch",
                        node_id,
                    )
        elif node_type == "switch":
            has_default = any(
                edge.get("branch") in (None, "default")
                for edge in outgoing
            )
            if not has_default:
                result.warning("unfinished_branch", f"node {node_id}: no default branch", node_id)
        elif node_type == "random_chance":
            for branch in ("true", "false"):
                if branch not in branches:
                    result.warning(
                        "unfinished_branch",
                        f"node {node_id}: no '{branch}' branch",
                        node_id,
                    )
        elif node_type in {"slash_command", "join_member", "message"} and not outgoing:
            result.error(
                "trigger_without_flow",
                f"node {node_id}: trigger has no next node",
                node_id,
            )

    return result


def validate_config(
    config: dict[str, Any],
    registry: BlockRegistry,
    *,
    bot_permissions: set[str] | None = None,
) -> ValidationResult:
    result = ValidationResult()
    if not isinstance(config, dict):
        result.error("invalid_config", "config must be an object")
        return result

    try:
        encoded = json.dumps(config, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        result.error("config_not_serializable", f"config is not JSON serializable: {exc}")
        return result
    if len(encoded) > MAX_CONFIG_BYTES:
        result.error("config_too_large", "config exceeds 2 MB")
    for finding in find_secrets(config):
        result.error("secret_in_config", finding)

    if config.get("schema_version") != 1:
        result.error("unsupported_schema", "schema_version must be 1")

    profile = config.get("profile", {})
    if not isinstance(profile, dict):
        result.error("invalid_profile", "profile must be an object")
    else:
        status = profile.get("status")
        if status is not None and status not in VALID_PROFILE_STATUSES:
            result.error("invalid_profile_status", f"unsupported profile.status: {status}")

    flows_raw = config.get("flows", [])
    if not isinstance(flows_raw, list):
        result.error("invalid_flows", "flows must be a list")
        flows_raw = []
    flows: dict[str, dict[str, Any]] = {}
    for flow in flows_raw:
        if not isinstance(flow, dict) or not isinstance(flow.get("id"), str):
            result.error("invalid_flow", "every flow must have an id")
            continue
        if flow["id"] in flows:
            result.error("duplicate_flow_id", f"duplicate flow id: {flow['id']}")
            continue
        flows[flow["id"]] = flow
        flow_result = validate_flow(flow, registry, bot_permissions=bot_permissions)
        result.errors.extend(flow_result.errors)
        result.warnings.extend(flow_result.warnings)

    commands_raw = config.get("commands", [])
    if not isinstance(commands_raw, list):
        result.error("invalid_commands", "commands must be a list")
        commands_raw = []
    command_names: set[str] = set()
    for command in commands_raw:
        if not isinstance(command, dict):
            result.error("invalid_command", "every command must be an object")
            continue
        name = command.get("name")
        if not isinstance(name, str) or not COMMAND_NAME_RE.fullmatch(name):
            result.error("invalid_command_name", f"invalid command name: {name}")
        elif name in command_names:
            result.error("duplicate_command_name", f"duplicate command name: {name}")
        else:
            command_names.add(name)
        flow_id = command.get("flow_id")
        if flow_id is not None and flow_id not in flows:
            result.error("missing_flow", f"command {name} references unknown flow {flow_id}")
        description = command.get("description", "")
        if isinstance(description, str) and len(description) > 100:
            result.error("command_description_too_long", f"command {name}: description exceeds 100")

    modules = config.get("modules", [])
    if not isinstance(modules, list):
        result.error("invalid_modules", "modules must be a list")
    else:
        module_ids: set[str] = set()
        for module in modules:
            if not isinstance(module, dict) or not isinstance(module.get("id"), str):
                result.error("invalid_module", "every module must have an id")
                continue
            if module["id"] in module_ids:
                result.error("duplicate_module", f"duplicate module id: {module['id']}")
            module_ids.add(module["id"])

    if "variables_schema" in config and not isinstance(config["variables_schema"], list):
        result.error("invalid_variables_schema", "variables_schema must be a list")

    return result
