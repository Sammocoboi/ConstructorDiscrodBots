from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from runtime.interpreter.validation import validate_config
from runtime.templates import (
    Template,
    TemplateError,
    TemplateService,
    create_share_link,
    create_share_token,
    export_template,
    import_template,
    load_system_templates,
    parse_share_link,
    parse_share_token,
    validate_template,
)

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "content" / "templates"
SECRET = "test-share-secret"


def system_templates() -> list[Template]:
    return load_system_templates(TEMPLATES_DIR)


def test_eight_system_templates_are_valid(registry):
    templates = system_templates()
    assert len(templates) == 8
    assert len({template.slug for template in templates}) == 8
    for template in templates:
        assert template.is_system
        assert validate_config(template.config, registry).ok


def test_export_import_roundtrip():
    template = system_templates()[0]
    exported = export_template(template)
    imported = import_template(exported, owner_id="user-1")
    assert imported.id != template.id
    assert imported.owner_id == "user-1"
    assert imported.slug == template.slug
    assert imported.config == template.config
    assert imported.is_system is False


def test_import_rejects_secrets():
    template = system_templates()[0].to_dict()
    template["config"]["discord_token"] = "M" + "a" * 24 + "." + "b" * 6 + "." + "c" * 27
    with pytest.raises(TemplateError):
        import_template(template, owner_id="user-1")


def test_validate_template_rejects_bad_semver():
    template = system_templates()[0]
    template.version = "1.0"
    with pytest.raises(TemplateError):
        validate_template(template)


def test_share_link_roundtrip():
    template = system_templates()[1]
    now = datetime(2026, 1, 1, tzinfo=UTC)
    link = create_share_link("https://example.test", template, SECRET, now=now)
    parsed = parse_share_link(link, SECRET, now=now + timedelta(days=1))
    assert parsed.slug == template.slug
    assert parsed.config == template.config


def test_share_token_tampering_and_expiry():
    template = system_templates()[2]
    now = datetime(2026, 1, 1, tzinfo=UTC)
    token = create_share_token(template, SECRET, now=now)
    with pytest.raises(TemplateError):
        parse_share_token(token + "x", SECRET, now=now)
    with pytest.raises(TemplateError):
        parse_share_token(token, "wrong-secret", now=now)
    with pytest.raises(TemplateError):
        parse_share_token(token, SECRET, now=now + timedelta(days=8))


def test_template_service_filters_system_catalog():
    service = TemplateService(
        None,
        system_dir=TEMPLATES_DIR,
        share_secret=SECRET,
    )
    assert len(service.system_templates) == 8
    assert len(service.filter_system(category="moderation")) == 1
    assert service.find_by_slug("utility") is not None
    assert service.find_by_slug("missing") is None
    assert service.filter_system(query="рол")
