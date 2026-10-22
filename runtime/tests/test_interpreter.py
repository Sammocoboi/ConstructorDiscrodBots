from __future__ import annotations

import pytest

from runtime.errors import FlowExecutionError, FlowLimitError
from runtime.interpreter.context import Context
from runtime.interpreter.executor import execute_flow
from runtime.interpreter.registry import BlockRegistry


def flow_with(nodes, edges, flow_id="f1"):
    return {"id": flow_id, "nodes": nodes, "edges": edges}


async def test_send_message_resolves_vars(registry, actions):
    flow = flow_with(
        [
            {"id": "n1", "type": "slash_command", "params": {"command_id": "c1"}},
            {
                "id": "n2",
                "type": "send_message",
                "params": {"content": "Hi, {user.name}! id={user.id}"},
            },
        ],
        [{"from": "n1", "to": "n2"}],
    )
    ctx = Context(user={"id": "42", "name": "Шухрат"}, channel={"id": "7"}, actions=actions)
    result = await execute_flow(flow, ctx, registry)
    assert result.steps == 2
    assert actions.messages[0]["content"] == "Hi, Шухрат! id=42"
    assert actions.messages[0]["channel_id"] == "7"
    assert [entry.node_id for entry in result.trace] == ["n1", "n2"]


async def test_dry_run_does_not_call_actions(registry, actions):
    flow = flow_with(
        [
            {"id": "n1", "type": "slash_command", "params": {"command_id": "c1"}},
            {"id": "n2", "type": "send_message", "params": {"content": "test"}},
            {"id": "n3", "type": "delay", "params": {"seconds": 30}},
        ],
        [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}],
    )
    ctx = Context(actions=actions, dry_run=True)
    result = await execute_flow(flow, ctx, registry)
    assert actions.messages == []
    assert result.trace[1].output["dry_run"] is True
    assert result.trace[2].output["seconds"] == 30


async def test_if_branches(registry, actions):
    flow = flow_with(
        [
            {"id": "n1", "type": "slash_command", "params": {"command_id": "c1"}},
            {
                "id": "n2",
                "type": "if",
                "params": {"condition": {"op": "eq", "left": "{args.mode}", "right": "yes"}},
            },
            {"id": "n3", "type": "send_message", "params": {"content": "TRUE"}},
            {"id": "n4", "type": "send_message", "params": {"content": "FALSE"}},
        ],
        [
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n3", "branch": "true"},
            {"from": "n2", "to": "n4", "branch": "false"},
        ],
    )
    await execute_flow(flow, Context(args={"mode": "yes"}, actions=actions), registry)
    assert actions.messages[0]["content"] == "TRUE"
    await execute_flow(flow, Context(args={"mode": "no"}, actions=actions), registry)
    assert actions.messages[-1]["content"] == "FALSE"


@pytest.mark.parametrize(("probability", "expected"), [(100, "TRUE"), (0, "FALSE")])
async def test_random_chance(registry, actions, probability, expected):
    flow = flow_with(
        [
            {"id": "n1", "type": "slash_command", "params": {"command_id": "c1"}},
            {"id": "n2", "type": "random_chance", "params": {"probability": probability}},
            {"id": "n3", "type": "send_message", "params": {"content": "TRUE"}},
            {"id": "n4", "type": "send_message", "params": {"content": "FALSE"}},
        ],
        [
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n3", "branch": "true"},
            {"from": "n2", "to": "n4", "branch": "false"},
        ],
    )
    await execute_flow(flow, Context(actions=actions), registry)
    assert actions.messages[0]["content"] == expected


async def test_set_variable_operations(registry, actions):
    flow = flow_with(
        [
            {"id": "n1", "type": "slash_command", "params": {"command_id": "c1"}},
            {
                "id": "n2",
                "type": "set_variable",
                "params": {"name": "counter", "value": 2},
            },
            {
                "id": "n3",
                "type": "set_variable",
                "params": {"name": "counter", "value": 3, "operation": "increment"},
            },
            {
                "id": "n4",
                "type": "send_message",
                "params": {"content": "counter={variables.counter}"},
            },
        ],
        [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}],
    )
    ctx = Context(actions=actions)
    result = await execute_flow(flow, ctx, registry)
    assert ctx.variables["counter"] == 5
    assert actions.messages[0]["content"] == "counter=5"
    assert result.variables["counter"] == 5


async def test_cycle_is_stopped_by_visit_limit(registry):
    flow = flow_with(
        [
            {"id": "n1", "type": "slash_command", "params": {"command_id": "c1"}},
            {
                "id": "n2",
                "type": "random_chance",
                "params": {"probability": 100},
            },
        ],
        [
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n2", "branch": "true"},
        ],
    )
    with pytest.raises(FlowLimitError):
        await execute_flow(flow, Context(dry_run=True), registry)


async def test_step_limit(registry):
    nodes = [{"id": "n0", "type": "slash_command", "params": {"command_id": "c1"}}]
    edges = []
    for index in range(1, 202):
        nodes.append({"id": f"n{index}", "type": "log", "params": {"message": "x"}})
        edges.append({"from": f"n{index - 1}", "to": f"n{index}"})
    with pytest.raises(FlowLimitError):
        await execute_flow(flow_with(nodes, edges), Context(dry_run=True), registry)


async def test_run_flow_depth_limit(registry):
    flows = {}
    for index in range(7):
        flows[f"f{index}"] = flow_with(
            [
                {"id": "n1", "type": "run_flow", "params": {"flow_id": f"f{index + 1}"}},
            ],
            [],
            flow_id=f"f{index}",
        )
    flows["f7"] = flow_with([{"id": "n1", "type": "stop", "params": {}}], [], flow_id="f7")
    ctx = Context(dry_run=True, flows=flows)
    with pytest.raises(FlowExecutionError):
        await execute_flow(flows["f0"], ctx, registry)


async def test_unknown_block_raises(registry):
    flow = flow_with([{"id": "n1", "type": "does_not_exist", "params": {}}], [])
    with pytest.raises(ValueError):
        await execute_flow(flow, Context(dry_run=True), registry)


def test_registry_rejects_duplicate_manifest(tmp_path):
    (tmp_path / "a.json").write_text('{"type": "x"}', encoding="utf-8")
    (tmp_path / "b.json").write_text('{"type": "x"}', encoding="utf-8")
    registry = BlockRegistry(tmp_path)
    with pytest.raises(ValueError):
        registry.load_manifests()
