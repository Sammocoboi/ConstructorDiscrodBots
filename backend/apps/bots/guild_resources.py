from cryptography.exceptions import InvalidTag
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import OAuthAccount
from apps.common.crypto import decrypt_secret
from integrations.discord.client import DiscordAPIError as DiscordRestError
from integrations.discord.client import DiscordRestClient
from integrations.discord.permissions import DiscordPermissions

from .models import Bot
from .services import DiscordAPIError, get_bot_token

CHANNEL_TYPES = {
    0: "text",
    2: "voice",
    4: "category",
    5: "text",
    13: "voice",
    15: "forum",
    16: "forum",
}
CREATE_CHANNEL_TYPES = {"text": 0, "category": 4}


class ResourceInput(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("channel", "role"))
    name = serializers.CharField(max_length=100)
    channel_type = serializers.ChoiceField(choices=tuple(CREATE_CHANNEL_TYPES), default="text")


def _has_discord_permission(user, guild_id: str, permission: int) -> bool:
    account = user.oauth_accounts.filter(provider=OAuthAccount.Provider.DISCORD).first()
    if not account or not account.access_token_encrypted:
        return False
    try:
        token = decrypt_secret(account.access_token_encrypted)
    except (ValueError, InvalidTag):
        return False
    guilds = DiscordRestClient(max_retries=0).get_user_guilds(token)
    guild = next((item for item in guilds if str(item.get("id")) == guild_id), None)
    if guild is None:
        return False
    permissions = int(guild.get("permissions") or 0)
    return bool(guild.get("owner") or permissions & (DiscordPermissions.ADMINISTRATOR | permission))


def _discord_error(error: DiscordRestError) -> Response:
    if error.status_code in (403, 404):
        return Response(
            {
                "detail": "Discord отказал в доступе. Проверьте, что бот на сервере "
                "и у него есть нужные права."
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    if error.status_code == 429:
        return Response(
            {"detail": "Discord ограничил частоту запросов. Попробуйте чуть позже."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    if error.status_code == 400:
        return Response(
            {"detail": "Discord отклонил запрос. Проверьте название и лимиты сервера."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {"detail": "Не удалось связаться с Discord. Проверьте подключение и токен бота."},
        status=status.HTTP_502_BAD_GATEWAY,
    )


class BotGuildResourcesView(APIView):
    permission_classes = [IsAuthenticated]

    def get_client(self, request, bot_id, guild_id):
        bot = get_object_or_404(Bot, id=bot_id, owner=request.user)
        if not guild_id.isascii() or not guild_id.isdecimal() or len(guild_id) > 20:
            raise serializers.ValidationError({"detail": "Некорректный ID сервера."})
        try:
            token = get_bot_token(bot)
        except DiscordAPIError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc
        return DiscordRestClient(bot_token=token, max_retries=0)

    def get(self, request, bot_id, guild_id):
        client = self.get_client(request, bot_id, guild_id)
        try:
            channels = client.get_guild_channels(guild_id)
            roles = client.get_guild_roles(guild_id)
        except DiscordRestError as exc:
            return _discord_error(exc)
        return Response(
            {
                "channels": [
                    {
                        "id": channel["id"],
                        "name": channel["name"],
                        "type": CHANNEL_TYPES[channel["type"]],
                    }
                    for channel in channels
                    if channel["type"] in CHANNEL_TYPES
                ],
                "roles": [
                    {
                        "id": role["id"],
                        "name": role["name"],
                        "position": role["position"],
                        "color": f"#{role.get('color') or 0:06x}",
                        "managed": role.get("managed", False),
                    }
                    for role in roles
                    if str(role["id"]) != guild_id
                ],
            }
        )

    def post(self, request, bot_id, guild_id):
        client = self.get_client(request, bot_id, guild_id)
        serializer = ResourceInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        is_role = data["kind"] == "role"
        permission = DiscordPermissions.MANAGE_ROLES if is_role else DiscordPermissions.MANAGE_CHANNELS
        permission_name = "Управлять ролями" if is_role else "Управлять каналами"
        try:
            allowed = _has_discord_permission(request.user, guild_id, permission)
        except DiscordRestError as exc:
            if exc.status_code == 401:
                return Response(
                    {"detail": "Войдите через Discord заново, чтобы подтвердить права на сервере."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return _discord_error(exc)
        if not allowed:
            return Response(
                {"detail": f"Войдите через Discord с правом «{permission_name}» на этом сервере."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            if is_role:
                created = client.request(
                    "POST",
                    f"guilds/{guild_id}/roles",
                    json_data={"name": data["name"], "permissions": "0"},
                )
            else:
                created = client.request(
                    "POST",
                    f"guilds/{guild_id}/channels",
                    json_data={
                        "name": data["name"],
                        "type": CREATE_CHANNEL_TYPES[data["channel_type"]],
                    },
                )
        except DiscordRestError as exc:
            if exc.status_code == 403:
                return Response(
                    {"detail": f"Выдайте боту право «{permission_name}» в Discord и повторите попытку."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return _discord_error(exc)
        return Response({"id": created["id"]}, status=status.HTTP_201_CREATED)
