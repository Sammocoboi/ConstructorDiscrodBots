"""PostgreSQL adapter for the Django-owned schema.

Django is the source of truth for ``bots_bot``, ``bots_botversion``,
``bots_runtimecommand`` and related tables. Runtime owns only
``runtime_scheduled_jobs`` and ``runtime_flow_traces`` (see
``infra/migrations/001_runtime.sql``).
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg

from runtime.config import PROJECT_ROOT
from runtime.crypto import TokenCipher
from runtime.errors import TokenDecryptionError
from runtime.models import BotSpec, RuntimeCommand

log = logging.getLogger("runtime.db")

MIGRATION_PATH = PROJECT_ROOT / "infra" / "migrations" / "001_runtime.sql"

_BOT_SELECT = """
    SELECT b.id, b.name, b.token_encrypted, b.desired_state, b.intents,
           COALESCE(v.content, d.content, '{}'::jsonb) AS config,
           v.version_number
      FROM bots_bot b
      LEFT JOIN bots_botversion v ON v.id = b.active_version_id
      LEFT JOIN bots_botdraft d ON d.bot_id = b.id
"""


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


async def connect(dsn: str, *, min_size: int = 1, max_size: int = 10) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)


async def ensure_schema(pool: asyncpg.Pool, path: Path | None = None) -> None:
    migration = path or MIGRATION_PATH
    if not migration.exists():
        raise FileNotFoundError(f"runtime migration not found: {migration}")
    script = migration.read_text(encoding="utf-8")
    async with pool.acquire() as connection:
        await connection.execute(script)
    log.info("Runtime schema is up to date")


class ListenerHandle:
    def __init__(
        self,
        connection: asyncpg.Connection,
        callback: Callable[[str], Awaitable[None]],
    ) -> None:
        self._connection = connection
        self._callback = callback

    async def _on_notify(
        self,
        connection: asyncpg.Connection,
        process_id: int,
        channel: str,
        payload: str,
    ) -> None:
        try:
            await self._callback(payload)
        except Exception:
            log.exception("runtime command listener failed")

    def start(self) -> None:
        self._connection.add_listener("runtime_commands_channel", self._on_notify)

    async def close(self) -> None:
        try:
            self._connection.remove_listener("runtime_commands_channel", self._on_notify)
        finally:
            await self._connection.close()


class BotLock:
    def __init__(self, connection: asyncpg.Connection, bot_id: str) -> None:
        self._connection = connection
        self._bot_id = bot_id

    async def release(self) -> None:
        try:
            await self._connection.execute("SELECT pg_advisory_unlock(hashtext($1))", self._bot_id)
        finally:
            await self._connection.close()


class PostgresRepository:
    def __init__(
        self,
        pool: asyncpg.Pool,
        dsn: str,
        cipher: TokenCipher | None = None,
    ) -> None:
        self._pool = pool
        self._dsn = dsn
        self._cipher = cipher

    @property
    def pool(self) -> asyncpg.Pool:
        return self._pool

    def _decode_token(self, encrypted: str | None) -> str:
        if not encrypted:
            raise TokenDecryptionError("bot token is not set")
        if self._cipher is None:
            raise TokenDecryptionError("token cipher is not configured")
        try:
            return self._cipher.decrypt(encrypted)
        except Exception as exc:
            # Never fall back to plaintext: a ciphertext sent to Discord would
            # produce a misleading 401, and a plaintext fallback would hide a
            # broken shared key.
            raise TokenDecryptionError(
                "token decryption failed; TOKEN_ENCRYPTION_KEY does not match backend"
            ) from exc

    def _row_to_bot(self, row: asyncpg.Record) -> BotSpec:
        token_error: str | None = None
        try:
            token = self._decode_token(row["token_encrypted"])
        except TokenDecryptionError as exc:
            token = ""
            token_error = str(exc)
            log.error("bot %s cannot be started: %s", row["id"], exc)

        config = _as_dict(row["config"])
        intents = row["intents"]
        if isinstance(intents, list) and intents:
            configured = config.get("intents")
            merged = list(configured) if isinstance(configured, list) else []
            for intent in intents:
                if intent not in merged:
                    merged.append(intent)
            config["intents"] = merged

        version_number = row["version_number"]
        return BotSpec(
            id=str(row["id"]),
            name=str(row["name"]),
            token=token,
            config=config,
            desired_state=str(row["desired_state"]),
            version_number=int(version_number) if version_number is not None else None,
            token_error=token_error,
        )

    async def list_running_bots(self) -> list[BotSpec]:
        rows = await self._pool.fetch(
            _BOT_SELECT
            + """
            WHERE b.desired_state = 'running' AND b.deleted_at IS NULL
            ORDER BY b.id
            """
        )
        return [self._row_to_bot(row) for row in rows]

    async def get_bot(self, bot_id: str) -> BotSpec | None:
        row = await self._pool.fetchrow(
            _BOT_SELECT
            + """
            WHERE b.id = $1::uuid AND b.deleted_at IS NULL
            """,
            _uuid(bot_id),
        )
        return self._row_to_bot(row) if row else None

    async def ping(self) -> bool:
        try:
            return bool(await self._pool.fetchval("SELECT 1") == 1)
        except Exception:
            log.exception("database readiness check failed")
            return False

    async def set_bot_desired_state(self, bot_id: str, desired_state: str) -> None:
        await self._pool.execute(
            """
            UPDATE bots_bot SET desired_state = $2, updated_at = now()
            WHERE id = $1::uuid
            """,
            _uuid(bot_id),
            desired_state,
        )

    async def set_bot_status(
        self,
        bot_id: str,
        status: str,
        *,
        error: str | None = None,
        worker_id: str = "",
        guild_count: int = 0,
        version_number: int | None = None,
    ) -> None:
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    UPDATE bots_bot
                    SET status = $2,
                        last_error = COALESCE($3::text, ''),
                        last_error_at = CASE
                            WHEN NULLIF($3::text, '') IS NULL THEN NULL
                            ELSE now()
                        END,
                        updated_at = now()
                    WHERE id = $1::uuid
                    """,
                    _uuid(bot_id),
                    status,
                    error,
                )
                await connection.execute(
                    """
                    INSERT INTO bots_botruntimestate (
                        id, bot_id, created_at, updated_at, worker_id, status,
                        latency_ms, guild_count, uptime_seconds, version_number,
                        heartbeat_at
                    )
                    VALUES (
                        $1, $2::uuid, now(), now(), $3, $4,
                        0, $5, 0, $6, now()
                    )
                    ON CONFLICT (bot_id) DO UPDATE
                    SET worker_id = EXCLUDED.worker_id,
                        status = EXCLUDED.status,
                        guild_count = EXCLUDED.guild_count,
                        version_number = EXCLUDED.version_number,
                        latency_ms = CASE
                            WHEN EXCLUDED.status = 'starting' THEN 0
                            ELSE bots_botruntimestate.latency_ms
                        END,
                        uptime_seconds = CASE
                            WHEN EXCLUDED.status = 'starting' THEN 0
                            ELSE bots_botruntimestate.uptime_seconds
                        END,
                        heartbeat_at = now(),
                        updated_at = now()
                    """,
                    uuid.uuid4(),
                    _uuid(bot_id),
                    worker_id,
                    status,
                    guild_count,
                    version_number,
                )

    async def write_heartbeat(
        self,
        bot_id: str,
        worker_id: str,
        status: str,
        latency_ms: int,
        uptime_seconds: int,
        *,
        guild_count: int = 0,
        version_number: int | None = None,
    ) -> None:
        await self._pool.execute(
            """
            INSERT INTO bots_botruntimestate (
                id, bot_id, created_at, updated_at, worker_id, status,
                latency_ms, guild_count, uptime_seconds, version_number,
                heartbeat_at
            )
            VALUES (
                $1, $2::uuid, now(), now(), $3, $4,
                $5, $6, $7, $8, now()
            )
            ON CONFLICT (bot_id) DO UPDATE
            SET worker_id = EXCLUDED.worker_id,
                status = EXCLUDED.status,
                latency_ms = EXCLUDED.latency_ms,
                guild_count = EXCLUDED.guild_count,
                uptime_seconds = EXCLUDED.uptime_seconds,
                version_number = EXCLUDED.version_number,
                heartbeat_at = now(),
                updated_at = now()
            """,
            uuid.uuid4(),
            _uuid(bot_id),
            worker_id,
            status,
            latency_ms,
            guild_count,
            uptime_seconds,
            version_number,
        )

    async def fetch_pending_commands(self, limit: int = 50) -> list[RuntimeCommand]:
        rows = await self._pool.fetch(
            """
            WITH pending AS (
                SELECT id
                FROM bots_runtimecommand
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT $1
                FOR UPDATE SKIP LOCKED
            )
            UPDATE bots_runtimecommand AS command
            SET status = 'acknowledged',
                processed_at = now(),
                updated_at = now()
            FROM pending
            WHERE command.id = pending.id
            RETURNING command.id, command.bot_id, command.command,
                      command.status, command.error
            """,
            limit,
        )
        return [
            RuntimeCommand(
                id=str(row["id"]),
                bot_id=str(row["bot_id"]),
                command=str(row["command"]),
                payload={},
                status=str(row["status"]),
                error=row["error"],
            )
            for row in rows
        ]

    async def mark_command(
        self,
        command_id: str,
        status: str,
        *,
        error: str | None = None,
    ) -> None:
        # Django uses pending/acknowledged/failed and processed_at. Runtime's
        # internal acked/done states are folded into acknowledged.
        db_status = {
            "acked": "acknowledged",
            "done": "acknowledged",
            "failed": "failed",
        }.get(status, status)
        await self._pool.execute(
            """
            UPDATE bots_runtimecommand
            SET status = $2,
                error = COALESCE($3::text, ''),
                processed_at = CASE
                    WHEN $2 IN ('acknowledged', 'failed') THEN now()
                    ELSE processed_at
                END,
                updated_at = now()
            WHERE id = $1::uuid
            """,
            _uuid(command_id),
            db_status,
            error,
        )

    async def create_runtime_command(
        self,
        bot_id: str,
        command: str,
        *,
        payload: dict[str, Any] | None = None,
        requested_by: str | None = None,
    ) -> str:
        command_id = uuid.uuid4()
        requested_by_id: uuid.UUID | None = None
        if requested_by:
            try:
                requested_by_id = _uuid(requested_by)
            except ValueError:
                requested_by_id = None
        if payload:
            log.warning("runtime command payload is not stored by the Django schema")
        await self._pool.execute(
            """
            INSERT INTO bots_runtimecommand (
                id, created_at, updated_at, command, status, error,
                bot_id, requested_by_id
            )
            VALUES ($1, now(), now(), $2, 'pending', '', $3::uuid, $4::uuid)
            """,
            command_id,
            command,
            _uuid(bot_id),
            requested_by_id,
        )
        return str(command_id)

    async def listen_commands(
        self,
        callback: Callable[[str], Awaitable[None]],
    ) -> ListenerHandle:
        connection = await asyncpg.connect(self._dsn)
        handle = ListenerHandle(connection, callback)
        handle.start()
        return handle

    async def acquire_bot_lock(self, bot_id: str) -> BotLock | None:
        connection = await asyncpg.connect(self._dsn)
        try:
            acquired = await connection.fetchval(
                "SELECT pg_try_advisory_lock(hashtext($1))",
                bot_id,
            )
        except Exception:
            await connection.close()
            raise
        if not acquired:
            await connection.close()
            return None
        return BotLock(connection, bot_id)

    async def list_versions(self, bot_id: str) -> list[Any]:
        from runtime.versions import BotVersion, VersionStatus

        rows = await self._pool.fetch(
            """
            SELECT version.id, version.bot_id, version.version_number,
                   version.content, version.comment, version.created_at,
                   (bot.active_version_id = version.id) AS is_active
            FROM bots_botversion AS version
            JOIN bots_bot AS bot ON bot.id = version.bot_id
            WHERE version.bot_id = $1::uuid
            ORDER BY version.version_number DESC
            """,
            _uuid(bot_id),
        )
        return [
            BotVersion(
                id=str(row["id"]),
                bot_id=str(row["bot_id"]),
                number=int(row["version_number"]),
                status=VersionStatus.PUBLISHED
                if bool(row["is_active"])
                else VersionStatus.ARCHIVED,
                config=_as_dict(row["content"]),
                comment=str(row["comment"] or ""),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def get_version(self, version_id: str) -> Any | None:
        from runtime.versions import BotVersion, VersionStatus

        row = await self._pool.fetchrow(
            """
            SELECT version.id, version.bot_id, version.version_number,
                   version.content, version.comment, version.created_at,
                   (bot.active_version_id = version.id) AS is_active
            FROM bots_botversion AS version
            JOIN bots_bot AS bot ON bot.id = version.bot_id
            WHERE version.id = $1::uuid
            """,
            _uuid(version_id),
        )
        if row is None:
            return None
        return BotVersion(
            id=str(row["id"]),
            bot_id=str(row["bot_id"]),
            number=int(row["version_number"]),
            status=VersionStatus.PUBLISHED
            if bool(row["is_active"])
            else VersionStatus.ARCHIVED,
            config=_as_dict(row["content"]),
            comment=str(row["comment"] or ""),
            created_at=row["created_at"],
        )

    async def create_version(self, version: Any) -> Any:
        row = await self._pool.fetchrow(
            """
            INSERT INTO bots_botversion (
                id, created_at, updated_at, version_number, content,
                comment, published_at, bot_id
            )
            VALUES ($1, now(), now(), $2, $3::jsonb, $4, now(), $5::uuid)
            RETURNING created_at
            """,
            _uuid(version.id),
            version.number,
            json.dumps(version.config, ensure_ascii=False),
            version.comment,
            _uuid(version.bot_id),
        )
        if row:
            version.created_at = row["created_at"]
        return version

    async def update_version(self, version: Any) -> Any:
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    UPDATE bots_botversion
                    SET content = $2::jsonb,
                        comment = $3,
                        updated_at = now()
                    WHERE id = $1::uuid
                    """,
                    _uuid(version.id),
                    json.dumps(version.config, ensure_ascii=False),
                    version.comment,
                )
                if str(version.status) == "published":
                    await connection.execute(
                        """
                        UPDATE bots_bot
                        SET active_version_id = $2::uuid, updated_at = now()
                        WHERE id = $1::uuid
                        """,
                        _uuid(version.bot_id),
                        _uuid(version.id),
                    )
                elif str(version.status) == "archived":
                    await connection.execute(
                        """
                        UPDATE bots_bot
                        SET active_version_id = NULL, updated_at = now()
                        WHERE active_version_id = $1::uuid
                        """,
                        _uuid(version.id),
                    )
        return version

    async def delete_version(self, version_id: str) -> None:
        await self._pool.execute(
            "DELETE FROM bots_botversion WHERE id = $1::uuid",
            _uuid(version_id),
        )

    async def set_active_version(self, bot_id: str, version_id: str) -> None:
        await self._pool.execute(
            """
            UPDATE bots_bot
            SET active_version_id = $2::uuid, updated_at = now()
            WHERE id = $1::uuid
            """,
            _uuid(bot_id),
            _uuid(version_id),
        )

    async def list_templates(self, owner_id: str | None = None) -> list[Any]:
        from runtime.templates import Template

        owner_uuid = _uuid(owner_id) if owner_id else None
        rows = await self._pool.fetch(
            """
            SELECT template.id, template.author_id, template.title,
                   template.description, template.category, template.is_system,
                   template.created_at, version.version AS version_name,
                   version.content
            FROM templates_catalog_template AS template
            LEFT JOIN LATERAL (
                SELECT version, content
                FROM templates_catalog_templateversion
                WHERE template_id = template.id
                ORDER BY created_at DESC
                LIMIT 1
            ) AS version ON TRUE
            WHERE template.deleted_at IS NULL
              AND template.is_system = FALSE
              AND ($1::uuid IS NULL OR template.author_id = $1::uuid)
            ORDER BY template.created_at DESC
            """,
            owner_uuid,
        )
        templates: list[Template] = []
        for row in rows:
            config = _as_dict(row["content"])
            slug = str(config.get("slug") or row["id"])
            templates.append(
                Template(
                    id=str(row["id"]),
                    owner_id=str(row["author_id"]) if row["author_id"] else None,
                    slug=slug,
                    title=str(row["title"]),
                    description=str(row["description"] or ""),
                    category=str(row["category"] or "custom"),
                    version=str(row["version_name"] or "1.0.0"),
                    config=config,
                    author=str(row["author_id"] or ""),
                    is_system=bool(row["is_system"]),
                    created_at=row["created_at"],
                )
            )
        return templates

    async def save_template(self, template: Any) -> Any:
        owner_uuid = _uuid(template.owner_id) if template.owner_id else None
        version_id = uuid.uuid4()
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO templates_catalog_template (
                        id, created_at, updated_at, title, description,
                        category, visibility, tags, is_system, popularity,
                        author_id
                    )
                    VALUES (
                        $1, now(), now(), $2, $3, $4, 'private',
                        '[]'::jsonb, FALSE, 0, $5::uuid
                    )
                    ON CONFLICT (id) DO UPDATE
                    SET title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        category = EXCLUDED.category,
                        author_id = EXCLUDED.author_id,
                        updated_at = now()
                    """,
                    _uuid(template.id),
                    template.title,
                    template.description,
                    template.category,
                    owner_uuid,
                )
                await connection.execute(
                    """
                    INSERT INTO templates_catalog_templateversion (
                        id, created_at, updated_at, template_id, version,
                        changelog, content
                    )
                    VALUES ($1, now(), now(), $2::uuid, $3, '', $4::jsonb)
                    ON CONFLICT (template_id, version) DO UPDATE
                    SET content = EXCLUDED.content,
                        updated_at = now()
                    """,
                    version_id,
                    _uuid(template.id),
                    template.version,
                    json.dumps(template.config, ensure_ascii=False),
                )
        return template

    async def delete_template(self, template_id: str, owner_id: str) -> bool:
        row = await self._pool.fetchrow(
            """
            UPDATE templates_catalog_template
            SET deleted_at = now(), updated_at = now()
            WHERE id = $1::uuid
              AND author_id = $2::uuid
              AND is_system = FALSE
              AND deleted_at IS NULL
            RETURNING id
            """,
            _uuid(template_id),
            _uuid(owner_id),
        )
        return row is not None

    async def list_due_jobs(self, now: datetime, limit: int = 20) -> list[Any]:
        from runtime.scheduler import ScheduledJob

        rows = await self._pool.fetch(
            """
            UPDATE runtime_scheduled_jobs
            SET status = 'running',
                last_started_at = now(),
                updated_at = now()
            WHERE id IN (
                SELECT id FROM runtime_scheduled_jobs
                WHERE enabled = TRUE
                  AND next_run_at IS NOT NULL
                  AND next_run_at <= $1
                ORDER BY next_run_at
                LIMIT $2
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id, name, cron, handler, payload, enabled,
                      next_run_at, last_error
            """,
            now,
            limit,
        )
        return [
            ScheduledJob(
                id=str(row["id"]),
                name=str(row["name"]),
                cron=str(row["cron"]),
                handler=str(row["handler"]),
                payload=_as_dict(row["payload"]),
                enabled=bool(row["enabled"]),
                next_run_at=row["next_run_at"],
                last_error=row["last_error"],
            )
            for row in rows
        ]

    async def mark_job_finished(
        self,
        job_id: str,
        status: str,
        *,
        next_run_at: datetime | None,
        error: str | None = None,
    ) -> None:
        await self._pool.execute(
            """
            UPDATE runtime_scheduled_jobs
            SET status = $2,
                last_run_at = now(),
                next_run_at = $3,
                last_error = $4,
                updated_at = now()
            WHERE id = $1::uuid
            """,
            _uuid(job_id),
            status,
            next_run_at,
            error,
        )

    async def cleanup_runtime_commands(self, days: int = 14) -> int:
        result = await self._pool.execute(
            """
            DELETE FROM bots_runtimecommand
            WHERE status IN ('acknowledged', 'failed')
              AND created_at < now() - ($1 || ' days')::interval
            """,
            str(days),
        )
        return _affected(result)

    async def cleanup_flow_traces(self, days: int = 30) -> int:
        result = await self._pool.execute(
            """
            DELETE FROM runtime_flow_traces
            WHERE created_at < now() - ($1 || ' days')::interval
            """,
            str(days),
        )
        return _affected(result)

    async def reset_usage_counters(self) -> int:
        # Django's UsageCounter is period-based; resetting all rows would erase
        # historical billing data. The runtime scheduler must not touch it.
        log.info("usage counters are period-based in Django; reset skipped")
        return 0


def _affected(result: str) -> int:
    try:
        return int(result.split()[-1])
    except (IndexError, ValueError):
        return 0
