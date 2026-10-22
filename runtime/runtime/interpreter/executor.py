from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from runtime.errors import FlowExecutionError, FlowLimitError, FlowTimeoutError
from runtime.interpreter.context import Context
from runtime.interpreter.registry import BlockRegistry

MAX_BLOCKS = 200
MAX_DURATION_SEC = 30.0
MAX_DEPTH = 5
MAX_NODE_VISITS = 50


@dataclass(slots=True)
class TraceEntry:
    node_id: str
    node_type: str
    status: str
    duration_ms: float
    branch: str | None = None
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "node_id": self.node_id,
            "type": self.node_type,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 3),
        }
        if self.branch is not None:
            payload["branch"] = self.branch
        if self.output:
            payload["output"] = self.output
        if self.error is not None:
            payload["error"] = self.error
        return payload


@dataclass(slots=True)
class ExecutionResult:
    trace: list[TraceEntry]
    steps: int
    variables: dict[str, Any]
    stopped: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace": [entry.as_dict() for entry in self.trace],
            "steps": self.steps,
            "variables": self.variables,
            "stopped": self.stopped,
        }


@dataclass(slots=True)
class _NodeResult:
    branch: str | None = None
    output: dict[str, Any] = field(default_factory=dict)
    stop: bool = False


def _normalize_result(result: dict[str, Any] | str | None) -> _NodeResult:
    if result is None:
        return _NodeResult()
    if isinstance(result, str):
        return _NodeResult(branch=result)
    output = result.get("output")
    return _NodeResult(
        branch=result.get("branch"),
        output=output if isinstance(output, dict) else {},
        stop=bool(result.get("stop", False)),
    )


def _edge_branch(edge: dict[str, Any]) -> str | None:
    branch = edge.get("branch")
    return str(branch) if branch is not None else None


def _select_next(
    edges_by_from: dict[str, list[dict[str, Any]]],
    node_id: str,
    branch: str | None,
) -> str | None:
    edges = edges_by_from.get(node_id, [])
    if branch is not None:
        for edge in edges:
            if _edge_branch(edge) == branch:
                return str(edge["to"])
        for edge in edges:
            if _edge_branch(edge) is None:
                return str(edge["to"])
        return None
    for edge in edges:
        if _edge_branch(edge) is None:
            return str(edge["to"])
    if len(edges) == 1:
        return str(edges[0]["to"])
    return None


def _find_start_nodes(
    flow: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    registry: BlockRegistry,
) -> list[str]:
    explicit = flow.get("start")
    if isinstance(explicit, str) and explicit in nodes:
        return [explicit]

    incoming: set[str] = set()
    for edge in flow.get("edges", []):
        if isinstance(edge, dict) and "to" in edge:
            incoming.add(str(edge["to"]))

    trigger_nodes: list[str] = []
    for node_id, node in nodes.items():
        try:
            manifest = registry.get_manifest(str(node.get("type", "")))
        except Exception:
            continue
        if manifest.get("category") == "trigger":
            trigger_nodes.append(node_id)
    if trigger_nodes:
        return trigger_nodes

    return [node_id for node_id in nodes if node_id not in incoming]


async def execute_flow(
    flow: dict[str, Any],
    ctx: Context,
    registry: BlockRegistry,
    *,
    depth: int = 0,
) -> ExecutionResult:
    if depth > MAX_DEPTH:
        raise FlowLimitError(f"max subflow depth {MAX_DEPTH} exceeded")

    nodes_list = flow.get("nodes")
    if not isinstance(nodes_list, list) or not nodes_list:
        raise FlowExecutionError("flow has no nodes")
    nodes: dict[str, dict[str, Any]] = {}
    for raw_node in nodes_list:
        if not isinstance(raw_node, dict) or not isinstance(raw_node.get("id"), str):
            raise FlowExecutionError("every node must have a string id")
        nodes[raw_node["id"]] = raw_node

    edges_by_from: dict[str, list[dict[str, Any]]] = {}
    for edge in flow.get("edges", []):
        if not isinstance(edge, dict) or "from" not in edge or "to" not in edge:
            raise FlowExecutionError("every edge must have from and to")
        edges_by_from.setdefault(str(edge["from"]), []).append(edge)

    start_nodes = _find_start_nodes(flow, nodes, registry)
    if not start_nodes:
        raise FlowExecutionError("flow has no start node")

    trace: list[TraceEntry] = []
    visits: dict[str, int] = {}
    steps = 0
    stopped = False
    deadline = time.monotonic() + MAX_DURATION_SEC

    for start_node in start_nodes:
        current: str | None = start_node
        while current is not None:
            if steps >= MAX_BLOCKS:
                raise FlowLimitError(f"flow exceeded {MAX_BLOCKS} blocks")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise FlowTimeoutError(f"flow exceeded {MAX_DURATION_SEC:.0f}s")

            node = nodes.get(current)
            if node is None:
                raise FlowExecutionError(f"edge points to unknown node {current}")

            visits[current] = visits.get(current, 0) + 1
            if visits[current] > MAX_NODE_VISITS:
                raise FlowLimitError(f"node {current} visited more than {MAX_NODE_VISITS} times")

            node_type = str(node.get("type", ""))
            handler = registry.get_handler(node_type)
            params = node.get("params")
            if not isinstance(params, dict):
                params = {}

            started = time.monotonic()
            try:
                raw_result = await asyncio.wait_for(handler(params, ctx), timeout=remaining)
            except TimeoutError as exc:
                trace.append(
                    TraceEntry(
                        node_id=current,
                        node_type=node_type,
                        status="error",
                        duration_ms=(time.monotonic() - started) * 1000,
                        error="timeout",
                    )
                )
                raise FlowTimeoutError(f"timeout in node {current}") from exc
            except Exception as exc:
                trace.append(
                    TraceEntry(
                        node_id=current,
                        node_type=node_type,
                        status="error",
                        duration_ms=(time.monotonic() - started) * 1000,
                        error=str(exc),
                    )
                )
                raise FlowExecutionError(f"node {current} failed: {exc}") from exc

            result = _normalize_result(raw_result)
            trace.append(
                TraceEntry(
                    node_id=current,
                    node_type=node_type,
                    status="ok",
                    duration_ms=(time.monotonic() - started) * 1000,
                    branch=result.branch,
                    output=result.output,
                )
            )
            steps += 1
            if result.stop:
                stopped = True
                break
            current = _select_next(edges_by_from, current, result.branch)
        if stopped:
            break

    return ExecutionResult(
        trace=trace,
        steps=steps,
        variables=dict(ctx.variables),
        stopped=stopped,
    )
