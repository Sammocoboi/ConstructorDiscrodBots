from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qs, urlparse

from runtime.secrets import find_secrets
from runtime.versions import validate_config

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CATEGORIES = {
    "community",
    "moderation",
    "support",
    "roles",
    "economy",
    "games",
    "giveaways",
    "utility",
    "custom",
}


class TemplateError(ValueError):
    pass


@dataclass(slots=True)
class Template:
    id: str
    slug: str
    title: str
    description: str
    category: str
    version: str
    config: dict[str, Any]
    author: str = ""
    owner_id: str | None = None
    is_system: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "config": self.config,
            "author": self.author,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Template:
        created_at = payload.get("created_at")
        if isinstance(created_at, str):
            try:
                parsed = datetime.fromisoformat(created_at)
            except ValueError:
                parsed = datetime.now(UTC)
        elif isinstance(created_at, datetime):
            parsed = created_at
        else:
            parsed = datetime.now(UTC)
        return cls(
            id=str(payload.get("id") or uuid.uuid4()),
            slug=str(payload["slug"]),
            title=str(payload["title"]),
            description=str(payload.get("description", "")),
            category=str(payload["category"]),
            version=str(payload["version"]),
            config=payload["config"],
            author=str(payload.get("author", "")),
            owner_id=payload.get("owner_id"),
            is_system=bool(payload.get("is_system", False)),
            created_at=parsed,
        )


class TemplateRepository(Protocol):
    async def list_templates(self, owner_id: str | None = None) -> list[Template]: ...

    async def save_template(self, template: Template) -> Template: ...

    async def delete_template(self, template_id: str, owner_id: str) -> bool: ...


def validate_template(template: Template) -> Template:
    errors: list[str] = []
    if not SLUG_RE.fullmatch(template.slug):
        errors.append("slug must match ^[a-z0-9]+(?:-[a-z0-9]+)*$")
    if not template.title.strip():
        errors.append("title is required")
    if template.category not in CATEGORIES:
        errors.append(f"unsupported category: {template.category}")
    if not SEMVER_RE.fullmatch(template.version):
        errors.append(f"invalid semver: {template.version}")
    try:
        validate_config(template.config)
    except ValueError as exc:
        errors.append(str(exc))
    errors.extend(find_secrets(template.config))
    if errors:
        raise TemplateError("; ".join(dict.fromkeys(errors)))
    return template


def load_system_templates(directory: Path) -> list[Template]:
    if not directory.exists():
        raise TemplateError(f"templates directory does not exist: {directory}")
    templates: list[Template] = []
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TemplateError(f"{path.name}: invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise TemplateError(f"{path.name}: template must be an object")
        try:
            template = Template.from_dict(payload)
        except KeyError as exc:
            raise TemplateError(f"{path.name}: missing field {exc}") from exc
        template.is_system = True
        template.owner_id = None
        validate_template(template)
        templates.append(template)
    return templates


def export_template(template: Template) -> str:
    validate_template(template)
    return json.dumps(template.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def import_template(raw: str | dict[str, Any], *, owner_id: str | None = None) -> Template:
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TemplateError(f"invalid template JSON: {exc}") from exc
    else:
        payload = raw
    if not isinstance(payload, dict):
        raise TemplateError("template must be an object")
    template = Template.from_dict(payload)
    template.id = str(uuid.uuid4())
    template.owner_id = owner_id
    template.is_system = False
    return validate_template(template)


def _b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_share_token(
    template: Template,
    secret: str,
    *,
    ttl: timedelta = timedelta(days=7),
    now: datetime | None = None,
) -> str:
    if not secret:
        raise TemplateError("share secret is required")
    validate_template(template)
    moment = now or datetime.now(UTC)
    payload = {
        "v": 1,
        "exp": int((moment + ttl).timestamp()),
        "template": template.to_dict(),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest()
    return f"{_b64encode(raw)}.{_b64encode(signature)}"


def create_share_link(base_url: str, template: Template, secret: str, **kwargs: Any) -> str:
    token = create_share_token(template, secret, **kwargs)
    return f"{base_url.rstrip('/')}/templates/shared?token={token}"


def parse_share_token(
    token: str,
    secret: str,
    *,
    now: datetime | None = None,
) -> Template:
    if not secret:
        raise TemplateError("share secret is required")
    try:
        encoded, signature = token.split(".", 1)
    except ValueError as exc:
        raise TemplateError("invalid share token") from exc
    raw = _b64decode(encoded)
    expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64decode(signature)):
        raise TemplateError("share token signature mismatch")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TemplateError("invalid share token payload") from exc
    if not isinstance(payload, dict) or payload.get("v") != 1:
        raise TemplateError("unsupported share token version")
    expires = payload.get("exp")
    moment = now or datetime.now(UTC)
    if not isinstance(expires, int) or datetime.fromtimestamp(expires, UTC) < moment:
        raise TemplateError("share token expired")
    template_payload = payload.get("template")
    if not isinstance(template_payload, dict):
        raise TemplateError("share token has no template")
    return validate_template(Template.from_dict(template_payload))


def parse_share_link(link: str, secret: str, *, now: datetime | None = None) -> Template:
    parsed = urlparse(link)
    token = parse_qs(parsed.query).get("token")
    if not token and parsed.fragment:
        token = parse_qs(parsed.fragment).get("token")
    if not token:
        raise TemplateError("share link has no token")
    return parse_share_token(token[0], secret, now=now)


class TemplateService:
    def __init__(
        self,
        repository: TemplateRepository | None,
        *,
        system_dir: Path,
        share_secret: str,
        share_base_url: str = "https://constructor.local",
        max_system_templates: int | None = None,
    ) -> None:
        self._repository = repository
        self._share_secret = share_secret
        self._share_base_url = share_base_url
        self._system = load_system_templates(system_dir)
        if max_system_templates is not None and len(self._system) > max_system_templates:
            raise TemplateError("too many system templates")
        slugs = [template.slug for template in self._system]
        if len(slugs) != len(set(slugs)):
            raise TemplateError("duplicate system template slug")

    @property
    def system_templates(self) -> list[Template]:
        return list(self._system)

    async def list_user_templates(self, owner_id: str) -> list[Template]:
        if self._repository is None:
            return []
        return await self._repository.list_templates(owner_id)

    async def list_all(self, owner_id: str | None = None) -> list[Template]:
        user_templates = await self.list_user_templates(owner_id) if owner_id else []
        return [*self._system, *user_templates]

    async def save_user_template(
        self,
        owner_id: str,
        payload: str | dict[str, Any],
        *,
        template_id: str | None = None,
    ) -> Template:
        if self._repository is None:
            raise TemplateError("template repository is not configured")
        template = import_template(payload, owner_id=owner_id)
        if template_id:
            template.id = template_id
        return await self._repository.save_template(template)

    async def delete_user_template(self, template_id: str, owner_id: str) -> bool:
        if self._repository is None:
            return False
        return await self._repository.delete_template(template_id, owner_id)

    def export(self, template: Template) -> str:
        return export_template(template)

    def import_payload(self, raw: str | dict[str, Any], owner_id: str) -> Template:
        return import_template(raw, owner_id=owner_id)

    def share_link(self, template: Template, **kwargs: Any) -> str:
        return create_share_link(self._share_base_url, template, self._share_secret, **kwargs)

    def resolve_share(self, link_or_token: str, **kwargs: Any) -> Template:
        if link_or_token.startswith("http://") or link_or_token.startswith("https://"):
            return parse_share_link(link_or_token, self._share_secret, **kwargs)
        return parse_share_token(link_or_token, self._share_secret, **kwargs)

    def find_by_slug(self, slug: str) -> Template | None:
        return next((template for template in self._system if template.slug == slug), None)

    def filter_system(
        self,
        *,
        category: str | None = None,
        query: str | None = None,
    ) -> list[Template]:
        result: Iterable[Template] = self._system
        if category:
            result = [template for template in result if template.category == category]
        if query:
            lowered = query.lower()
            result = [
                template
                for template in result
                if lowered in template.title.lower() or lowered in template.slug.lower()
            ]
        return list(result)
