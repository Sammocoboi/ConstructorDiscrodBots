from __future__ import annotations

from runtime.interpreter.validation import validate_config, validate_flow


def make_flow(**overrides):
    flow = {
        "id": "flow_1",
        "nodes": [
            {"id": "n1", "type": "slash_command", "params": {"command_id": "c1"}},
            {"id": "n2", "type": "send_message", "params": {"content": "Hello"}},
        ],
        "edges": [{"from": "n1", "to": "n2"}],
    }
    flow.update(overrides)
    return flow


def test_valid_flow(registry):
    result = validate_flow(make_flow(), registry)
    assert result.ok
    assert result.warnings == []


def test_unknown_block(registry):
    flow = make_flow(
        nodes=[{"id": "n1", "type": "mystery", "params": {}}],
        edges=[],
    )
    result = validate_flow(flow, registry)
    assert not result.ok
    assert any(issue.code == "unknown_block" for issue in result.errors)


def test_missing_required_param(registry):
    flow = make_flow(
        nodes=[
            {"id": "n1", "type": "slash_command", "params": {}},
            {"id": "n2", "type": "send_message", "params": {"content": "x"}},
        ]
    )
    result = validate_flow(flow, registry)
    assert any(issue.code == "missing_param" for issue in result.errors)


def test_duplicate_and_dangling_edges(registry):
    flow = make_flow(
        nodes=[
            {"id": "n1", "type": "slash_command", "params": {"command_id": "c1"}},
            {"id": "n1", "type": "send_message", "params": {"content": "x"}},
        ],
        edges=[{"from": "n1", "to": "missing"}],
    )
    result = validate_flow(flow, registry)
    codes = {issue.code for issue in result.errors}
    assert "duplicate_node_id" in codes
    assert "dangling_edge" in codes


def test_cycle_detected(registry):
    flow = make_flow(
        nodes=[
            {"id": "n1", "type": "slash_command", "params": {"command_id": "c1"}},
            {"id": "n2", "type": "random_chance", "params": {"probability": 50}},
            {"id": "n3", "type": "send_message", "params": {"content": "x"}},
            {"id": "n4", "type": "send_message", "params": {"content": "y"}},
        ],
        edges=[
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n3", "branch": "true"},
            {"from": "n2", "to": "n4", "branch": "false"},
            {"from": "n3", "to": "n2"},
        ],
    )
    result = validate_flow(flow, registry)
    assert any(issue.code == "cycle_detected" for issue in result.errors)


def test_if_requires_both_branches(registry):
    flow = make_flow(
        nodes=[
            {"id": "n1", "type": "slash_command", "params": {"command_id": "c1"}},
            {"id": "n2", "type": "if", "params": {"condition": True}},
            {"id": "n3", "type": "send_message", "params": {"content": "x"}},
        ],
        edges=[
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n3", "branch": "true"},
        ],
    )
    result = validate_flow(flow, registry)
    assert any(issue.code == "unfinished_branch" for issue in result.errors)


def test_unreachable_node_warning(registry):
    flow = make_flow(
        nodes=[
            {"id": "n1", "type": "slash_command", "params": {"command_id": "c1"}},
            {"id": "n2", "type": "send_message", "params": {"content": "x"}},
            {"id": "n3", "type": "send_message", "params": {"content": "y"}},
        ],
        edges=[{"from": "n1", "to": "n2"}],
    )
    result = validate_flow(flow, registry)
    assert any(issue.code == "unreachable_node" for issue in result.warnings)


def test_message_and_embed_limits(registry):
    flow = make_flow(
        nodes=[
            {"id": "n1", "type": "slash_command", "params": {"command_id": "c1"}},
            {
                "id": "n2",
                "type": "send_message",
                "params": {"content": "x" * 2001, "embed": {"title": "t" * 300}},
            },
        ]
    )
    result = validate_flow(flow, registry)
    codes = {issue.code for issue in result.errors}
    assert "message_too_long" in codes
    assert "embed_title_too_long" in codes


def test_validate_config_with_secret(registry):
    config = {
        "schema_version": 1,
        "commands": [
            {"id": "c1", "name": "ping", "flow_id": "flow_1"},
        ],
        "flows": [make_flow()],
        "api_key": "super-secret-value",
    }
    result = validate_config(config, registry)
    assert not result.ok
    assert any(issue.code == "secret_in_config" for issue in result.errors)


def test_validate_config_command_reference(registry):
    config = {
        "schema_version": 1,
        "commands": [{"id": "c1", "name": "Bad Name", "flow_id": "missing"}],
        "flows": [make_flow()],
    }
    result = validate_config(config, registry)
    codes = {issue.code for issue in result.errors}
    assert "invalid_command_name" in codes
    assert "missing_flow" in codes
