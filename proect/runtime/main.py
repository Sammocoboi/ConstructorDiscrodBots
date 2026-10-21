import asyncio
import logging
import os

import discord

from runtime.config import load_settings
from runtime.db import connect, fetch_running_bots, write_heartbeat

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("runtime")


class PingBot(discord.Client):
    def __init__(self, pool, bot_id: str, worker_id: str):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.pool = pool
        self.bot_id = bot_id
        self.worker_id = worker_id

    async def setup_hook(self) -> None:
        @self.tree.command(name="ping", description="Проверка")
        async def ping(interaction: discord.Interaction):
            await interaction.response.send_message(
                f"Pong! {round(self.latency * 1000)} ms", ephemeral=True
            )
        await self.tree.sync()

    async def on_ready(self) -> None:
        log.info("Bot online as %s", self.user)
        asyncio.create_task(self._heartbeat())

    async def _heartbeat(self) -> None:
        while not self.is_closed():
            await write_heartbeat(
                self.pool, self.bot_id, self.worker_id, int(self.latency * 1000)
            )
            await asyncio.sleep(15)


async def main() -> None:
    settings = load_settings()
    pool = await connect(settings.database_url)

    token = os.environ.get("DISCORD_TEST_BOT_TOKEN")
    if not token:
        log.error("DISCORD_TEST_BOT_TOKEN не задан — прототип не запустится")
        return

    bots = await fetch_running_bots(pool)
    if not bots:
        log.info("Нет ботов с desired_state=running. Добавь тестовую строку в bots.")
        return

    bot_row = bots[0]
    client = PingBot(pool, str(bot_row["id"]), settings.worker_id)
    await client.start(token)


if __name__ == "__main__":
    asyncio.run(main())