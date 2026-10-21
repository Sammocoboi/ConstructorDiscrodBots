import pytest

from runtime.interpreter.context import Context
from runtime.interpreter.executor import execute_flow
from runtime.interpreter.registry import BlockRegistry


@pytest.fixture
def registry() -> BlockRegistry:
    reg = BlockRegistry()
    reg.load_manifests()

    async def send_message(params, ctx):
        ctx.variables["last_sent"] = ctx.resolve(params["content"])

    reg.register("send_message", send_message)
    return reg


@pytest.mark.asyncio
async def test_send_message_resolves_vars(registry):
    flow = {
        "id": "f1",
        "trigger": {"type": "slash_command", "command_id": "c1"},
        "nodes": [
            {"id": "n1", "type": "send_message",
             "params": {"channel_id": "1", "content": "Hi, {user.name}!"}}
        ],
        "edges": [],
    }
    ctx = Context(user={"name": "Шухрат"})
    await execute_flow(flow, ctx, registry)
    assert ctx.variables["last_sent"] == "Hi, Шухрат!"