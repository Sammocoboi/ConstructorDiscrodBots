import asyncpg


async def connect(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


async def fetch_running_bots(pool: asyncpg.Pool) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT id, token_encrypted, active_version_id, desired_state
        FROM bots
        WHERE desired_state = 'running'
        """
    )
    return [dict(r) for r in rows]


async def write_heartbeat(pool: asyncpg.Pool, bot_id: str, worker_id: str, latency_ms: int) -> None:
    await pool.execute(
        """
        INSERT INTO bot_runtime_state (bot_id, worker_id, status, latency_ms, heartbeat_at)
        VALUES ($1, $2, 'online', $3, now())
        ON CONFLICT (bot_id) DO UPDATE
        SET worker_id = EXCLUDED.worker_id,
            status = EXCLUDED.status,
            latency_ms = EXCLUDED.latency_ms,
            heartbeat_at = now()
        """,
        bot_id, worker_id, latency_ms,
    )