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
from runtime.models import BotSpec, RuntimeCommand

log = logging.getLogger("runtime.db")

MIGRATION_PATH = PROJECT_ROOT / "infra" / "migrations" / "001_runtime.sql"


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
    def __init__(self, pool: asyncpg.Pool, dsn: str, cipher: TokenCipher | None = None) -> None:
        self._pool = pool
        self._dsn = dsn
        self._cipher = cipher or TokenCipher()

    @property
    def pool(self) -> asyncpg.Pool:
        return self._pool

    def _decode_token(self, encrypted: str | None) -> str:
        if not encrypted:
            return ""
        if self._cipher is None:
            return encrypted
        try:
            return self._cipher.decrypt(encrypted)
        except Exception:
            log.error("could not decrypt bot token — check TOKEN_ENCRYPTION_KEY")
            raise

    def _row_to_bot(self, row: asyncpg.Record) -> BotSpec:
        return BotSpec(
            id=str(row["id"]),
            name=str(row["name"]),
            token=self._decode_token(row["token_encrypted"]),
            config=_as_dict(row["config"]),
            desired_state=str(row["desired_state"]),
        )

    async def list_running_bots(self) -> list[BotSpec]:
        rows = await self._pool.fetch(
            """
            SELECT b.id, b.name, b.token_encrypted, b.desired_state,
                   COALESCE(v.config, b.config, '{}'::jsonb) AS config
            FROM bots b
            LEFT JOIN LATERAL (
                SELECT config FROM bot_versions
                WHERE bot_id = b.id AND status = 'published'
                ORDER BY number DESC LIMIT 1
            ) v ON TRUE
            WHERE b.desired_state = 'running' AND b.deleted_at IS NULL
            ORDER BY b.id
            """
        )
        return [self._row_to_bot(row) for row in rows]

    async def get_bot(self, bot_id: str) -> BotSpec | None:
        row = await self._pool.fetchrow(
            """
            SELECT b.id, b.name, b.token_encrypted, b.desired_state,
                   COALESCE(v.config, b.config, '{}'::jsonb) AS config
            FROM bots b
            LEFT JOIN LATERAL (
                SELECT config FROM bot_versions
                WHERE bot_id = b.id AND status = 'published'
                ORDER BY number DESC LIMIT 1
            ) v ON TRUE
            WHERE b.id = $1::uuid AND b.deleted_at IS NULL
            """,
            _uuid(bot_id),
        )
        return self._row_to_bot(row) if row else None

    async def set_bot_desired_state(self, bot_id: str, desired_state: str) -> None:
        await self._pool.execute(
            """
            UPDATE bots SET desired_state = $2, updated_at = now()
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
    ) -> None:
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    UPDATE bots
                    SET status = $2,
                        last_error = $3,
                        last_error_at = CASE WHEN $3::text IS NULL THEN NULL ELSE now() END,
                        updated_at = now()
                    WHERE id = $1::uuid
                    """,
                    _uuid(bot_id),
                    status,
                    error,
                )
                await connection.execute(
                    """
                    INSERT INTO bot_runtime_state (
                        bot_id, worker_id, status, latency_ms, uptime_seconds,
                        heartbeat_at, started_at, last_error
                    )
                    VALUES ($1::uuid, $2, $3, 0, 0, now(),
                            CASE WHEN $3 = 'starting' THEN now() ELSE NULL END, $4)
                    ON CONFLICT (bot_id) DO UPDATE
                    SET worker_id = EXCLUDED.worker_id,
                        status = EXCLUDED.status,
                        last_error = EXCLUDED.last_error,
                        heartbeat_at = now(),
                        started_at = CASE
                            WHEN EXCLUDED.status = 'starting' THEN now()
                            ELSE bot_runtime_state.started_at
                        END
                    """,
                    _uuid(bot_id),
                    worker_id,
                    status,
                    error,
                )

    async def write_heartbeat(
        self,
        bot_id: str,
        worker_id: str,
        status: str,
        latency_ms: int,
        uptime_seconds: int,
    ) -> None:
        await self._pool.execute(
            """
            INSERT INTO bot_runtime_state (
                bot_id, worker_id, status, latency_ms, uptime_seconds, heartbeat_at
            )
            VALUES ($1::uuid, $2, $3, $4, $5, now())
            ON CONFLICT (bot_id) DO UPDATE
            SET worker_id = EXCLUDED.worker_id,
                status = EXCLUDED.status,
                latency_ms = EXCLUDED.latency_ms,
                uptime_seconds = EXCLUDED.uptime_seconds,
                heartbeat_at = now()
            """,
            _uuid(bot_id),
            worker_id,
            status,
            latency_ms,
            uptime_seconds,
        )

    async def fetch_pending_commands(self, limit: int = 50) -> list[RuntimeCommand]:
        rows = await self._pool.fetch(
            """
            SELECT id, bot_id, command, payload, status, error
            FROM runtime_commands
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT $1
            """,
            limit,
        )
        return [
            RuntimeCommand(
                id=str(row["id"]),
                bot_id=str(row["bot_id"]),
                command=str(row["command"]),
                payload=_as_dict(row["payload"]),
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
        await self._pool.execute(
            """
            UPDATE runtime_commands
            SET status = $2,
                error = $3,
                acked_at = CASE WHEN $2 = 'acked' THEN now() ELSE acked_at END,
                finished_at = CASE WHEN $2 IN ('done', 'failed') THEN now() ELSE finished_at END
            WHERE id = $1::uuid
            """,
            _uuid(command_id),
            status,
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
        await self._pool.execute(
            """
            INSERT INTO runtime_commands (id, bot_id, command, payload, status, requested_by)
            VALUES ($1, $2::uuid, $3, $4::jsonb, 'pending', $5)
            """,
            command_id,
            _uuid(bot_id),
            command,
            json.dumps(payload or {}, ensure_ascii=False),
            requested_by,
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
            SELECT id, bot_id, number, status, config, comment, created_at
            FROM bot_versions
            WHERE bot_id = $1::uuid
            ORDER BY number DESC
            """,
            _uuid(bot_id),
        )
        return [
            BotVersion(
                id=str(row["id"]),
                bot_id=str(row["bot_id"]),
                number=int(row["number"]),
                status=VersionStatus(str(row["status"])),
                config=_as_dict(row["config"]),
                comment=str(row["comment"] or ""),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def get_version(self, version_id: str) -> Any | None:
        from runtime.versions import BotVersion, VersionStatus

        row = await self._pool.fetchrow(
            """
            SELECT id, bot_id, number, status, config, comment, created_at
            FROM bot_versions WHERE id = $1::uuid
            """,
            _uuid(version_id),
        )
        if row is None:
            return None
        return BotVersion(
            id=str(row["id"]),
            bot_id=str(row["bot_id"]),
            number=int(row["number"]),
            status=VersionStatus(str(row["status"])),
            config=_as_dict(row["config"]),
            comment=str(row["comment"] or ""),
            created_at=row["created_at"],
        )

    async def create_version(self, version: Any) -> Any:
        row = await self._pool.fetchrow(
            """
            INSERT INTO bot_versions (id, bot_id, number, status, config, comment)
            VALUES ($1, $2::uuid, $3, $4, $5::jsonb, $6)
            RETURNING created_at
            """,
            _uuid(version.id),
            _uuid(version.bot_id),
            version.number,
            str(version.status),
            json.dumps(version.config, ensure_ascii=False),
            version.comment,
        )
        if row:
            version.created_at = row["created_at"]
        return version

    async def update_version(self, version: Any) -> Any:
        await self._pool.execute(
            """
            UPDATE bot_versions
            SET status = $2, config = $3::jsonb, comment = $4
            WHERE id = $1::uuid
            """,
            _uuid(version.id),
            str(version.status),
            json.dumps(version.config, ensure_ascii=False),
            version.comment,
        )
        return version

    async def delete_version(self, version_id: str) -> None:
        await self._pool.execute(
            "DELETE FROM bot_versions WHERE id = $1::uuid",
            _uuid(version_id),
        )

    async def set_active_version(self, bot_id: str, version_id: str) -> None:
        await self._pool.execute(
            """
            UPDATE bots SET active_version_id = $2::uuid, updated_at = now()
            WHERE id = $1::uuid
            """,
            _uuid(bot_id),
            _uuid(version_id),
        )

    async def list_templates(self, owner_id: str | None = None) -> list[Any]:
        from runtime.templates import Template

        if owner_id is None:
            rows = await self._pool.fetch(
                "SELECT * FROM templates WHERE is_system = FALSE ORDER BY created_at DESC"
            )
        else:
            rows = await self._pool.fetch(
                """
                SELECT * FROM templates
                WHERE is_system = FALSE AND owner_id = $1
                ORDER BY created_at DESC
                """,
                owner_id,
            )
        return [
            Template(
                id=str(row["id"]),
                owner_id=row["owner_id"],
                slug=str(row["slug"]),
                title=str(row["title"]),
                description=str(row["description"] or ""),
                category=str(row["category"]),
                version=str(row["version"]),
                config=_as_dict(row["config"]),
                author=str(row["author"] or ""),
                is_system=bool(row["is_system"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def save_template(self, template: Any) -> Any:
        await self._pool.execute(
            """
            INSERT INTO templates (
                id, owner_id, slug, title, description, category, version,
                config, author, is_system, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, now(), now())
            ON CONFLICT (id) DO UPDATE
            SET slug = EXCLUDED.slug,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                category = EXCLUDED.category,
                version = EXCLUDED.version,
                config = EXCLUDED.config,
                author = EXCLUDED.author,
                updated_at = now()
            """,
            _uuid(template.id),
            template.owner_id,
            template.slug,
            template.title,
            template.description,
            template.category,
            template.version,
            json.dumps(template.config, ensure_ascii=False),
            template.author,
            template.is_system,
        )
        return template

    async def delete_template(self, template_id: str, owner_id: str) -> bool:
        row = await self._pool.fetchrow(
            """
            DELETE FROM templates
            WHERE id = $1::uuid AND owner_id = $2 AND is_system = FALSE
            RETURNING id
            """,
            _uuid(template_id),
            owner_id,
        )
        return row is not None

    async def list_due_jobs(self, now: datetime, limit: int = 20) -> list[Any]:
        from runtime.scheduler import ScheduledJob

        rows = await self._pool.fetch(
            """
            UPDATE scheduled_jobs
            SET status = 'running', last_started_at = now()
            WHERE id IN (
                SELECT id FROM scheduled_jobs
                WHERE enabled = TRUE AND next_run_at IS NOT NULL AND next_run_at <= $1
                ORDER BY next_run_at
                LIMIT $2
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id, name, cron, handler, payload, enabled, next_run_at, last_error
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
            UPDATE scheduled_jobs
            SET status = $2,
                last_run_at = now(),
                next_run_at = $3,
                last_error = $4
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
            DELETE FROM runtime_commands
            WHERE status IN ('done', 'failed') AND created_at < now() - ($1 || ' days')::interval
            """,
            str(days),
        )
        return _affected(result)

    async def cleanup_flow_traces(self, days: int = 30) -> int:
        result = await self._pool.execute(
            """
            DELETE FROM flow_traces
            WHERE created_at < now() - ($1 || ' days')::interval
            """,
            str(days),
        )
        return _affected(result)

    async def reset_usage_counters(self) -> int:
        exists = await self._pool.fetchval("SELECT to_regclass('public.usage_counters')")
        if exists is None:
            return 0
        result = await self._pool.execute("UPDATE usage_counters SET used = 0, updated_at = now()")
        return _affected(result)

    # --- Guild sync -------------------------------------------------------

    async def upsert_guild(
        self,
        bot_id: str,
        guild_id: str,
        guild_name: str,
    ) -> None:
        """Insert or update a guild for a bot (on_guild_join)."""
        await self._pool.execute(
            """
            INSERT INTO bot_guilds (id, bot_id, guild_id, guild_name, joined_at, created_at, updated_at)
            VALUES (gen_random_uuid(), $1::uuid, $2, $3, now(), now(), now())
            ON CONFLICT ON CONSTRAINT unique_bot_guild DO UPDATE
            SET guild_name = EXCLUDED.guild_name,
                left_at = NULL,
                deleted_at = NULL,
                updated_at = now()
            """,
            _uuid(bot_id),
            guild_id,
            guild_name,
        )

    async def remove_guild(
        self,
        bot_id: str,
        guild_id: str,
    ) -> None:
        """Mark a guild as left (on_guild_remove)."""
        await self._pool.execute(
            """
            UPDATE bot_guilds
            SET left_at = now(), updated_at = now()
            WHERE bot_id = $1::uuid AND guild_id = $2 AND left_at IS NULL
            """,
            _uuid(bot_id),
            guild_id,
        )

    async def count_guilds(self, bot_id: str) -> int:
        """Count active guilds for a bot."""
        count = await self._pool.fetchval(
            """
            SELECT COUNT(*) FROM bot_guilds
            WHERE bot_id = $1::uuid AND left_at IS NULL AND deleted_at IS NULL
            """,
            _uuid(bot_id),
        )
        return int(count or 0)


def _affected(result: str) -> int:
    try:
        return int(result.split()[-1])
    except (IndexError, ValueError):
        return 0

