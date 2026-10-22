from __future__ import annotations

from pathlib import Path

from runtime.interpreter.handlers import build_default_registry
from runtime.interpreter.registry import BlockRegistry
from runtime.interpreter.validation import validate_config
from runtime.secrets import find_secrets
from runtime.templates import load_system_templates

ROOT = Path(__file__).resolve().parents[1]


def test_block_manifests_load():
    registry = build_default_registry(BlockRegistry(ROOT / "content" / "blocks"))
    assert len(registry.manifests) >= 15
    for block_type in (
        "slash_command",
        "join_member",
        "message",
        "if",
        "switch",
        "random_chance",
        "send_message",
        "send_dm",
        "add_role",
        "remove_role",
        "set_variable",
        "delay",
        "run_flow",
        "stop",
        "log",
    ):
        assert block_type in registry.manifests
        assert registry.has_handler(block_type)


def test_system_templates_validate_against_blocks():
    registry = build_default_registry(BlockRegistry(ROOT / "content" / "blocks"))
    templates = load_system_templates(ROOT / "content" / "templates")
    assert len(templates) == 8
    for template in templates:
        result = validate_config(template.config, registry)
        assert result.ok, (template.slug, [issue.message for issue in result.errors])
        assert find_secrets(template.config) == []
