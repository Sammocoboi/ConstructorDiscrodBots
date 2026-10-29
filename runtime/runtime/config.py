from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "infra" / ".env")


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    worker_id: str = "worker-1"
    log_level: str = "INFO"
    max_bots_per_worker: int = 25
    heartbeat_interval: float = 15.0
    reconcile_interval: float = 10.0
    command_poll_interval: float = 30.0
    restart_limit: int = 5
    health_host: str = "0.0.0.0"
    health_port: int = 8080
    token_key: str | None = None
    blocks_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "content" / "blocks")
    templates_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "content" / "templates")
    sentry_dsn: str | None = None


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    value = float(raw)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    value = int(raw)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _token_key() -> str:
    """Return the key shared with Django.

    ``TOKEN_ENCRYPTION_KEY`` is the canonical name. The legacy
    ``BOT_TOKEN_ENCRYPTION_KEY`` is accepted only to make the migration of
    existing deployments less painful; new installations must use the canonical
    name.
    """

    canonical = os.environ.get("TOKEN_ENCRYPTION_KEY", "").strip()
    if canonical:
        return canonical
    legacy = os.environ.get("BOT_TOKEN_ENCRYPTION_KEY", "").strip()
    if legacy:
        return legacy
    raise ValueError(
        "TOKEN_ENCRYPTION_KEY is required (same url-safe base64 key as Django)"
    )


def load_settings() -> Settings:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is required")
    return Settings(
        database_url=database_url,
        worker_id=os.environ.get("WORKER_ID", "worker-1"),
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        max_bots_per_worker=_int_env("MAX_BOTS_PER_WORKER", 25),
        heartbeat_interval=_float_env("HEARTBEAT_INTERVAL", 15.0),
        reconcile_interval=_float_env("RECONCILE_INTERVAL", 10.0),
        command_poll_interval=_float_env("COMMAND_POLL_INTERVAL", 30.0),
        restart_limit=_int_env("RESTART_LIMIT", 5),
        health_host=os.environ.get("HEALTH_HOST", "0.0.0.0"),
        health_port=_int_env("HEALTH_PORT", 8080),
        token_key=_token_key(),
        blocks_dir=Path(os.environ.get("BLOCKS_DIR", PROJECT_ROOT / "content" / "blocks")),
        templates_dir=Path(
            os.environ.get("TEMPLATES_DIR", PROJECT_ROOT / "content" / "templates")
        ),
        sentry_dsn=os.environ.get("SENTRY_DSN") or None,
    )
