import asyncio
from typing import Any

from runtime.interpreter.context import Context
from runtime.interpreter.registry import BlockRegistry

MAX_BLOCKS = 200
MAX_DURATION_SEC = 30
MAX_DEPTH = 5


async def execute_flow(
    flow: dict[str, Any],
    ctx: Context,
    registry: BlockRegistry,
    *,
    depth: int = 0,
) -> None:
    if depth > MAX_DEPTH:
        raise RuntimeError("max subflow depth exceeded")

    nodes = {n["id"]: n for n in flow["nodes"]}
    edges = flow.get("edges", [])
    next_map = {e["from"]: e["to"] for e in edges}

    current = flow["nodes"][0]["id"]
    steps = 0
    started = asyncio.get_event_loop().time()

    while current and steps < MAX_BLOCKS:
        elapsed = asyncio.get_event_loop().time() - started
        if elapsed > MAX_DURATION_SEC:
            raise TimeoutError("flow exceeded 30s")

        node = nodes[current]
        handler = registry.get_handler(node["type"])
        await handler(node.get("params", {}), ctx)

        steps += 1
        current = next_map.get(current)