from __future__ import annotations

import asyncio
import logging
import signal
from typing import Any

from runtime.bot import DiscordBotClient, set_guild_repository
from runtime.config import Settings, load_settings
from runtime.crypto import TokenCipher
from runtime.db import PostgresRepository, connect, ensure_schema
from runtime.health import HealthServer
from runtime.interpreter.handlers import build_default_registry
from runtime.interpreter.registry import BlockRegistry
from runtime.listener import CommandListener
from runtime.models import BotSpec
from runtime.scheduler import SchedulerService
from runtime.supervisor import Supervisor

log = logging.getLogger("runtime")


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def init_sentry(dsn: str | None) -> None:
    if not dsn:
        return
    try:
        import sentry_sdk
    except ImportError:
        log.warning("SENTRY_DSN is set but sentry-sdk is not installed")
        return
    sentry_sdk.init(dsn=dsn, traces_sample_rate=0.1)


def build_factory(registry: BlockRegistry) -> Any:
    def factory(spec: BotSpec) -> DiscordBotClient:
        return DiscordBotClient(spec, registry)

    return factory


def install_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()

    def request_stop() -> None:
        stop_event.set()

    for signame in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, signame, None)
        if sig is None:
            continue
        try:
            loop.add_signal_handler(sig, request_stop)
        except (NotImplementedError, RuntimeError):
            signal.signal(sig, lambda *_: loop.call_soon_threadsafe(request_stop))


async def run(settings: Settings) -> None:
    configure_logging(settings.log_level)
    init_sentry(settings.sentry_dsn)
    log.info(
        "starting runtime worker %s (max %s bots)",
        settings.worker_id,
        settings.max_bots_per_worker,
    )

    pool = await connect(settings.database_url)
    try:
        await ensure_schema(pool)
        registry = build_default_registry(BlockRegistry(settings.blocks_dir))
        repository = PostgresRepository(
            pool,
            settings.database_url,
            TokenCipher(settings.token_key),
        )
        set_guild_repository(repository)
        supervisor = Supervisor(
            repository,
            build_factory(registry),
            worker_id=settings.worker_id,
            max_bots=settings.max_bots_per_worker,
            heartbeat_interval=settings.heartbeat_interval,
            reconcile_interval=settings.reconcile_interval,
            restart_limit=settings.restart_limit,
        )
        listener = CommandListener(
            repository,
            supervisor,
            poll_interval=settings.command_poll_interval,
        )
        scheduler = SchedulerService(repository)
        scheduler.register_default_handlers()
        health = HealthServer(
            supervisor,
            host=settings.health_host,
            port=settings.health_port,
        )

        await supervisor.start()
        await listener.start()
        await scheduler.start()
        try:
            await health.start()
        except OSError:
            log.exception(
                "health server could not bind to %s:%s",
                settings.health_host,
                settings.health_port,
            )

        stop_event = asyncio.Event()
        install_signal_handlers(stop_event)
        log.info("runtime is ready")
        await stop_event.wait()

        log.info("shutdown requested")
        await health.close()
        await scheduler.stop()
        await listener.stop()
        await supervisor.shutdown()
    finally:
        await pool.close()


def main() -> None:
    try:
        settings = load_settings()
    except Exception:
        configure_logging("INFO")
        log.exception("invalid runtime configuration")
        raise SystemExit(1) from None
    asyncio.run(run(settings))


if __name__ == "__main__":
    main()
