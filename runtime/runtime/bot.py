from __future__ import annotations

import asyncio
import inspect
import logging
import math
import re
import time
from typing import Any

import discord
from discord import app_commands

from runtime.errors import InvalidTokenError, MissingIntentsError
from runtime.interpreter.context import Context
from runtime.interpreter.executor import execute_flow
from runtime.interpreter.registry import BlockRegistry
from runtime.models import BotSpec

log = logging.getLogger("runtime.bot")

# Import db types for guild sync — optional, set at runtime
_guild_repo = None


def set_guild_repository(repo):
    """Set the repository instance used for guild sync."""
    global _guild_repo
    _guild_repo = repo


OPTION_TYPES: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "user": discord.Member,
    "channel": discord.abc.GuildChannel,
    "role": discord.Role,
}
OPTION_NAME_RE = re.compile(r"[^a-z0-9_-]+")


def _option_name(raw: str, fallback: str) -> str:
    name = OPTION_NAME_RE.sub("-", str(raw).lower()).strip("-_")
    return (name or fallback)[:32]


def _embed(payload: dict[str, Any] | None) -> discord.Embed | None:
    if payload is None:
        return None
    return discord.Embed.from_dict(payload)


class DiscordActions:
    def __init__(
        self,
        client: DiscordBotClient,
        interaction: discord.Interaction | None = None,
        guild_id: str | None = None,
    ) -> None:
        self._client = client
        self._interaction = interaction
        self._guild_id = guild_id

    async def send_message(
        self,
        *,
        channel_id: str | None,
        content: str | None,
        embed: dict[str, Any] | None,
        ephemeral: bool,
    ) -> Any:
        if content is None and embed is None:
            raise ValueError("send_message requires content or embed")
        send_kwargs: dict[str, Any] = {}
        if content is not None:
            send_kwargs["content"] = content
        embed_object = _embed(embed)
        if embed_object is not None:
            send_kwargs["embed"] = embed_object
        interaction = self._interaction
        if (
            interaction is not None
            and channel_id is not None
            and interaction.channel_id is not None
            and str(interaction.channel_id) == channel_id
        ):
            if not interaction.response.is_done():
                return await interaction.response.send_message(
                    ephemeral=ephemeral,
                    **send_kwargs,
                )
            return await interaction.followup.send(ephemeral=ephemeral, **send_kwargs)
        channel = await self._client.resolve_channel(channel_id)
        return await channel.send(**send_kwargs)

    async def send_dm(
        self,
        *,
        user_id: str,
        content: str | None,
        embed: dict[str, Any] | None,
    ) -> Any:
        user = self._client.get_user(int(user_id))
        if user is None:
            user = await self._client.fetch_user(int(user_id))
        dm_kwargs: dict[str, Any] = {}
        if content is not None:
            dm_kwargs["content"] = content
        embed_object = _embed(embed)
        if embed_object is not None:
            dm_kwargs["embed"] = embed_object
        return await user.send(**dm_kwargs)

    async def add_role(self, *, user_id: str, role_id: str) -> None:
        member, role = await self._resolve_member_role(user_id, role_id)
        await member.add_roles(role, reason="Constructor Discord Bots flow")

    async def remove_role(self, *, user_id: str, role_id: str) -> None:
        member, role = await self._resolve_member_role(user_id, role_id)
        await member.remove_roles(role, reason="Constructor Discord Bots flow")

    async def _resolve_member_role(
        self,
        user_id: str,
        role_id: str,
    ) -> tuple[discord.Member, discord.Role]:
        if self._guild_id is None:
            raise ValueError("role operations require a guild context")
        guild = self._client.get_guild(int(self._guild_id))
        if guild is None:
            raise ValueError(f"guild {self._guild_id} is not available")
        member = guild.get_member(int(user_id))
        if member is None:
            member = await guild.fetch_member(int(user_id))
        role = guild.get_role(int(role_id))
        if role is None:
            raise ValueError(f"role {role_id} not found")
        return member, role


class DiscordBotClient(discord.Client):
    def __init__(
        self,
        spec: BotSpec,
        registry: BlockRegistry,
        *,
        connect_timeout: float = 60.0,
    ) -> None:
        self.spec = spec
        self.registry = registry
        self.connect_timeout = connect_timeout
        self._ready_event = asyncio.Event()
        self._stopped = asyncio.Event()
        self._start_error: BaseException | None = None
        self._task: asyncio.Task[None] | None = None
        self._started_at: float | None = None
        self._flows_by_id: dict[str, dict[str, Any]] = {}
        self._command_flows: dict[str, dict[str, Any]] = {}
        self._command_defs: dict[str, dict[str, Any]] = {}
        self._join_flows: list[dict[str, Any]] = []
        self._message_flows: list[dict[str, Any]] = []
        super().__init__(intents=self._build_intents(spec.config))
        self.tree: app_commands.CommandTree[Any] = app_commands.CommandTree(self)

    @staticmethod
    def _build_intents(config: dict[str, Any]) -> discord.Intents:
        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True
        intents.dm_messages = True
        configured = {str(item) for item in config.get("intents", [])}
        flows = config.get("flows", [])
        uses_members = any(
            isinstance(flow, dict)
            and isinstance(flow.get("trigger"), dict)
            and flow["trigger"].get("type") == "join_member"
            for flow in flows
        )
        uses_messages = any(
            isinstance(flow, dict)
            and isinstance(flow.get("trigger"), dict)
            and flow["trigger"].get("type") == "message"
            for flow in flows
        )
        if "members" in configured or "member_events" in configured or uses_members:
            intents.members = True
        if "message_content" in configured or uses_messages:
            intents.message_content = True
        return intents

    async def setup_hook(self) -> None:
        self._apply_config(self.spec.config)
        await self._sync_commands()

    async def on_ready(self) -> None:
        self._started_at = time.monotonic()
        self._ready_event.set()
        log.info("bot %s connected as %s", self.spec.id, self.user)

    async def on_member_join(self, member: discord.Member) -> None:
        if not self._join_flows:
            return
        context = self._build_context(user=member, guild=member.guild)
        for flow in self._join_flows:
            await self._execute_flow(flow, context)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not self._message_flows:
            return
        context = self._build_context(
            user=message.author,
            guild=message.guild,
            channel=message.channel,
            message=message,
        )
        for flow in self._message_flows:
            trigger = flow.get("trigger", {})
            if not self._message_matches(trigger, message.content):
                continue
            await self._execute_flow(flow, context)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Sync guild to DB when the bot is added to a server."""
        log.info("bot %s joined guild %s (%s)", self.spec.id, guild.id, guild.name)
        if _guild_repo is not None:
            try:
                await _guild_repo.upsert_guild(
                    self.spec.id,
                    str(guild.id),
                    guild.name,
                )
            except Exception:
                log.exception("failed to upsert guild %s for bot %s", guild.id, self.spec.id)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Mark guild as left in DB when the bot is removed from a server."""
        log.info("bot %s removed from guild %s (%s)", self.spec.id, guild.id, guild.name)
        if _guild_repo is not None:
            try:
                await _guild_repo.remove_guild(
                    self.spec.id,
                    str(guild.id),
                )
            except Exception:
                log.exception("failed to remove guild %s for bot %s", guild.id, self.spec.id)

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """Handle Discord gateway errors with specific messages."""
        import sys

        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_value is None:
            return

        error_msg = str(exc_value)

        if isinstance(exc_value, discord.HTTPException):
            if exc_value.status == 429:
                retry_after = getattr(exc_value, "retry_after", 5.0)
                log.warning(
                    "bot %s: rate limited (429) in %s, retry after %.1fs",
                    self.spec.id,
                    event_method,
                    retry_after,
                )
                await asyncio.sleep(retry_after)
                return
            elif exc_value.status == 401:
                log.error(
                    "bot %s: unauthorized (401) in %s — token may be invalid",
                    self.spec.id,
                    event_method,
                )
                return
            elif exc_value.status == 403:
                log.warning(
                    "bot %s: forbidden (403) in %s — missing permissions: %s",
                    self.spec.id,
                    event_method,
                    error_msg,
                )
                return

        log.exception(
            "bot %s: unhandled error in %s: %s",
            self.spec.id,
            event_method,
            error_msg,
        )

    @staticmethod
    def _message_matches(trigger: dict[str, Any], content: str) -> bool:
        prefix = trigger.get("prefix")
        if isinstance(prefix, str) and prefix and not content.startswith(prefix):
            return False
        contains = trigger.get("contains")
        if isinstance(contains, str) and contains and contains not in content:
            return False
        pattern = trigger.get("regex")
        if isinstance(pattern, str) and pattern:
            try:
                return re.search(pattern, content) is not None
            except re.error:
                return False
        return True

    async def _execute_flow(
        self,
        flow: dict[str, Any],
        context: Context,
        interaction: discord.Interaction | None = None,
    ) -> None:
        try:
            result = await execute_flow(flow, context, self.registry)
            log.info(
                "flow %s executed by bot %s (%s steps)",
                flow.get("id"),
                self.spec.id,
                result.steps,
            )
            if interaction is not None and not interaction.response.is_done():
                await interaction.response.send_message("Готово.", ephemeral=True)
        except Exception as exc:
            log.exception("flow %s failed for bot %s", flow.get("id"), self.spec.id)
            if interaction is not None and not interaction.response.is_done():
                await interaction.response.send_message(
                    f"Ошибка сценария: {exc}",
                    ephemeral=True,
                )

    def _build_context(
        self,
        *,
        user: Any,
        guild: Any = None,
        channel: Any = None,
        message: Any = None,
        interaction: discord.Interaction | None = None,
        args: dict[str, Any] | None = None,
    ) -> Context:
        user_payload: dict[str, Any] = {
            "id": str(getattr(user, "id", "")),
            "name": str(getattr(user, "name", "")),
            "display_name": str(getattr(user, "display_name", getattr(user, "name", ""))),
            "mention": str(getattr(user, "mention", "")),
        }
        guild_payload: dict[str, Any] = {
            "id": str(getattr(guild, "id", "")),
            "name": str(getattr(guild, "name", "")),
            "member_count": int(getattr(guild, "member_count", 0) or 0),
        }
        channel_payload: dict[str, Any] = {
            "id": str(getattr(channel, "id", "")),
            "name": str(getattr(channel, "name", "")),
        }
        message_payload: dict[str, Any] = {}
        if message is not None:
            message_payload = {
                "id": str(getattr(message, "id", "")),
                "content": str(getattr(message, "content", "")),
                "author_id": str(getattr(getattr(message, "author", None), "id", "")),
            }
        bot_payload = {
            "id": str(self.user.id) if self.user else "",
            "name": str(self.user.name) if self.user else "",
            "latency": self.latency_ms,
            "uptime_seconds": int(time.monotonic() - self._started_at) if self._started_at else 0,
        }
        return Context(
            user=user_payload,
            guild=guild_payload,
            channel=channel_payload,
            message=message_payload,
            args=args or {},
            bot=bot_payload,
            flows=self._flows_by_id,
            actions=DiscordActions(
                self,
                interaction=interaction,
                guild_id=str(guild_payload["id"]) or None,
            ),
        )

    def _apply_config(self, config: dict[str, Any]) -> None:
        self._flows_by_id = {
            str(flow["id"]): flow
            for flow in config.get("flows", [])
            if isinstance(flow, dict) and isinstance(flow.get("id"), str)
        }
        self._command_defs = {
            str(command["name"]): command
            for command in config.get("commands", [])
            if isinstance(command, dict) and isinstance(command.get("name"), str)
        }
        self._command_flows = {}
        for name, command in self._command_defs.items():
            flow = self._flows_by_id.get(str(command.get("flow_id")))
            if flow is not None:
                self._command_flows[name] = flow
        for flow in self._flows_by_id.values():
            trigger = flow.get("trigger")
            if not isinstance(trigger, dict):
                continue
            trigger_type = trigger.get("type")
            if trigger_type == "slash_command":
                command_id = trigger.get("command_id")
                matched_command: dict[str, Any] | None = next(
                    (item for item in self._command_defs.values() if item.get("id") == command_id),
                    None,
                )
                if (
                    matched_command is not None
                    and str(matched_command["name"]) not in self._command_flows
                ):
                    self._command_flows[str(matched_command["name"])] = flow
            elif trigger_type == "join_member":
                self._join_flows.append(flow)
            elif trigger_type == "message":
                self._message_flows.append(flow)

    async def _sync_commands(self) -> None:
        self.tree.clear_commands(guild=None)
        for name, flow in self._command_flows.items():
            command_def = self._command_defs.get(name, {})
            callback = self._make_command_callback(name, flow)
            app_command: Any = app_commands.Command(
                name=name,
                description=str(command_def.get("description", "Команда конструктора"))[:100],
                callback=callback,
            )
            self.tree.add_command(app_command)
        try:
            await self.tree.sync()
        except discord.HTTPException:
            log.exception("failed to sync slash commands for bot %s", self.spec.id)

    def _make_command_callback(self, name: str, flow: dict[str, Any]) -> Any:
        command_def = self._command_defs.get(name, {})
        options = command_def.get("options", [])
        if not isinstance(options, list):
            options = []

        async def callback(interaction: discord.Interaction, **kwargs: Any) -> None:
            args = {key: _serialize_option(value) for key, value in kwargs.items()}
            context = self._build_context(
                user=interaction.user,
                guild=interaction.guild,
                channel=interaction.channel,
                interaction=interaction,
                args=args,
            )
            await self._execute_flow(flow, context, interaction=interaction)

        parameters = [
            inspect.Parameter(
                "interaction",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=discord.Interaction,
            )
        ]
        used_names: set[str] = set()
        for index, option in enumerate(options):
            if not isinstance(option, dict):
                continue
            option_name = _option_name(str(option.get("name", f"arg{index}")), f"arg{index}")
            if option_name in used_names:
                option_name = f"{option_name}-{index}"
            used_names.add(option_name)
            annotation = OPTION_TYPES.get(str(option.get("type", "string")), str)
            required = bool(option.get("required", False))
            default = inspect.Parameter.empty if required else None
            parameters.append(
                inspect.Parameter(
                    option_name,
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation=annotation,
                    default=default,
                )
            )
        callback.__signature__ = inspect.Signature(parameters)  # type: ignore[attr-defined]
        callback.__name__ = f"command_{name.replace('-', '_')}"
        return callback

    async def resolve_channel(self, channel_id: str | None) -> Any:
        if channel_id is None:
            raise ValueError("channel_id is required")
        channel = self.get_channel(int(channel_id))
        if channel is None:
            channel = await self.fetch_channel(int(channel_id))
        return channel

    @property
    def latency_ms(self) -> int:
        latency = self.latency
        if latency is None or math.isnan(latency):
            return 0
        return int(latency * 1000)

    @property
    def guild_count(self) -> int:
        return len(self.guilds)

    async def start(self, token: str | None = None, *, reconnect: bool = True) -> None:
        if self._task is not None and not self._task.done():
            return
        self._ready_event.clear()
        self._stopped.clear()
        self._start_error = None
        self._task = asyncio.create_task(self._run_client(), name=f"discord-{self.spec.id}")
        try:
            await asyncio.wait_for(self._ready_event.wait(), timeout=self.connect_timeout)
        except TimeoutError as exc:
            await self.stop()
            raise ConnectionError("gateway connection timed out") from exc
        if self._start_error is not None:
            error = self._start_error
            await self.stop()
            raise error

    async def _run_client(self) -> None:
        try:
            await super().start(self.spec.token)
        except discord.LoginFailure:
            self._start_error = InvalidTokenError("Discord 401 Unauthorized: invalid bot token")
            self._ready_event.set()
        except discord.PrivilegedIntentsRequired:
            self._start_error = MissingIntentsError(
                "Discord requires privileged intents that are disabled in the developer portal"
            )
            self._ready_event.set()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._start_error = exc
            self._ready_event.set()
        finally:
            self._started_at = None
            self._stopped.set()

    async def wait_closed(self) -> None:
        await self._stopped.wait()

    async def stop(self) -> None:
        if not self.is_closed():
            await self.close()
        task = self._task
        if task is not None and not task.done():
            try:
                await asyncio.wait_for(task, timeout=10)
            except TimeoutError:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._task = None

    async def reload(self, config: dict[str, Any]) -> None:
        self.spec.config = config
        self._join_flows = []
        self._message_flows = []
        self._apply_config(config)
        await self._sync_commands()
        log.info("bot %s configuration reloaded", self.spec.id)


def _serialize_option(value: Any) -> Any:
    if isinstance(value, (discord.Member, discord.User)):
        return {
            "id": str(value.id),
            "name": value.name,
            "display_name": getattr(value, "display_name", value.name),
            "mention": value.mention,
        }
    if isinstance(value, discord.Role):
        return {"id": str(value.id), "name": value.name}
    if isinstance(value, discord.abc.GuildChannel):
        return {"id": str(value.id), "name": value.name}
    return value
