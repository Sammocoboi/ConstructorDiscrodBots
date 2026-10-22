from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from runtime.interpreter.context import Context, stringify
from runtime.interpreter.expressions import evaluate
from runtime.interpreter.registry import BlockRegistry

log = logging.getLogger("runtime.interpreter.handlers")

TRIGGER_TYPES = {"slash_command", "join_member", "message"}


async def _noop(params: dict[str, Any], ctx: Context) -> dict[str, Any] | None:
    return None


async def _send_message(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
    content = ctx.resolve_deep(params.get("content"))
    if content is not None:
        content = stringify(content)[:2000]
    embed = ctx.resolve_deep(params.get("embed"))
    if embed is not None and not isinstance(embed, dict):
        embed = None
    channel_id = ctx.resolve_deep(params.get("channel_id")) or ctx.channel.get("id")
    ephemeral = bool(ctx.resolve_deep(params.get("ephemeral", False)))
    target = str(channel_id) if channel_id else None
    payload = {"channel_id": target, "content": content, "embed": embed, "ephemeral": ephemeral}

    if ctx.dry_run or ctx.actions is None:
        return {"output": {"dry_run": True, **payload}}
    await ctx.actions.send_message(
        channel_id=target,
        content=content,
        embed=embed,
        ephemeral=ephemeral,
    )
    return {"output": {"sent": True, **payload}}


async def _send_dm(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
    content = ctx.resolve_deep(params.get("content"))
    if content is not None:
        content = stringify(content)[:2000]
    embed = ctx.resolve_deep(params.get("embed"))
    if embed is not None and not isinstance(embed, dict):
        embed = None
    user_id = ctx.resolve_deep(params.get("user_id")) or ctx.user.get("id")
    if not user_id:
        raise ValueError("send_dm requires user_id")
    target = str(user_id)
    payload = {"user_id": target, "content": content, "embed": embed}
    if ctx.dry_run or ctx.actions is None:
        return {"output": {"dry_run": True, **payload}}
    await ctx.actions.send_dm(user_id=target, content=content, embed=embed)
    return {"output": {"sent": True, **payload}}


async def _add_role(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
    role_id = ctx.resolve_deep(params.get("role_id"))
    user_id = ctx.resolve_deep(params.get("user_id")) or ctx.user.get("id")
    if not role_id or not user_id:
        raise ValueError("add_role requires role_id and user_id")
    payload = {"user_id": str(user_id), "role_id": str(role_id)}
    if ctx.dry_run or ctx.actions is None:
        return {"output": {"dry_run": True, **payload}}
    await ctx.actions.add_role(user_id=str(user_id), role_id=str(role_id))
    return {"output": {"added": True, **payload}}


async def _remove_role(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
    role_id = ctx.resolve_deep(params.get("role_id"))
    user_id = ctx.resolve_deep(params.get("user_id")) or ctx.user.get("id")
    if not role_id or not user_id:
        raise ValueError("remove_role requires role_id and user_id")
    payload = {"user_id": str(user_id), "role_id": str(role_id)}
    if ctx.dry_run or ctx.actions is None:
        return {"output": {"dry_run": True, **payload}}
    await ctx.actions.remove_role(user_id=str(user_id), role_id=str(role_id))
    return {"output": {"removed": True, **payload}}


async def _set_variable(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
    name = ctx.resolve_deep(params.get("name"))
    if not isinstance(name, str) or not name:
        raise ValueError("set_variable requires name")
    if name.startswith("variables."):
        name = name.removeprefix("variables.")
    value = ctx.resolve_deep(params.get("value"))
    operation = params.get("operation", "set")
    if operation == "increment":
        current = ctx.get(f"variables.{name}", 0)
        try:
            value = float(current) + float(value)
            if value.is_integer():
                value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("increment requires numeric value") from exc
    elif operation == "append":
        current_value = ctx.get(f"variables.{name}", [])
        if not isinstance(current_value, list):
            current_value = [current_value]
        value = [*current_value, value]
    ctx.set(name, value)
    return {"output": {"name": name, "value": value}}


async def _if(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
    result = evaluate(params.get("condition"), ctx)
    return {"branch": "true" if result else "false", "output": {"result": result}}


async def _switch(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
    value = ctx.resolve_deep(params.get("value"))
    cases = params.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("switch cases must be a list")
    for case in cases:
        if not isinstance(case, dict):
            continue
        if case.get("value") == value:
            return {"branch": str(case.get("branch", "default")), "output": {"value": value}}
    return {"branch": str(params.get("default_branch", "default")), "output": {"value": value}}


async def _random_chance(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
    raw = ctx.resolve_deep(params.get("probability", 50))
    probability = float(raw)
    probability = max(0.0, min(100.0, probability))
    result = random.random() * 100 < probability
    return {"branch": "true" if result else "false", "output": {"probability": probability}}


async def _delay(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
    raw = ctx.resolve_deep(params.get("seconds", 1))
    seconds = max(0.0, min(MAX_DELAY_SEC, float(raw)))
    if not ctx.dry_run:
        await asyncio.sleep(seconds)
    return {"output": {"seconds": seconds}}


async def _stop(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
    return {"stop": True}


async def _log(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
    message = stringify(ctx.resolve_deep(params.get("message", "")))
    level = str(params.get("level", "info")).lower()
    log_method = getattr(log, level, log.info)
    log_method("flow log: %s", message)
    return {"output": {"message": message, "level": level}}


MAX_DELAY_SEC = 30.0


def build_default_registry(registry: BlockRegistry) -> BlockRegistry:
    registry.load_manifests()
    basic_handlers = {
        "send_message": _send_message,
        "send_dm": _send_dm,
        "add_role": _add_role,
        "remove_role": _remove_role,
        "set_variable": _set_variable,
        "if": _if,
        "switch": _switch,
        "random_chance": _random_chance,
        "delay": _delay,
        "stop": _stop,
        "log": _log,
    }
    for block_type, handler in basic_handlers.items():
        registry.register(block_type, handler)

    async def _run_flow(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
        from runtime.interpreter.executor import execute_flow

        flow_id = ctx.resolve_deep(params.get("flow_id"))
        if not isinstance(flow_id, str) or flow_id not in ctx.flows:
            raise ValueError(f"unknown subflow: {flow_id}")
        previous_depth = ctx.depth
        ctx.depth += 1
        try:
            result = await execute_flow(ctx.flows[flow_id], ctx, registry, depth=ctx.depth)
        finally:
            ctx.depth = previous_depth
        return {"output": {"subflow": flow_id, "trace": result.as_dict()}}

    registry.register("run_flow", _run_flow)

    for block_type, manifest in registry.manifests.items():
        if manifest.get("category") == "trigger" or block_type in TRIGGER_TYPES:
            if not registry.has_handler(block_type):
                registry.register(block_type, _noop)
    return registry
