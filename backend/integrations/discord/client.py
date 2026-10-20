
import time
import json
import logging
from typing import Any, Dict, List, Optional, Union
import requests
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class DiscordAPIError(Exception):
    def __init__(self, status_code: int, message: str, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(f"Discord API error {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.response_data = response_data or {}

class DiscordUnauthorizedError(DiscordAPIError):
    pass

class DiscordForbiddenError(DiscordAPIError):
    pass

class DiscordNotFoundError(DiscordAPIError):
    pass

class DiscordRateLimitError(DiscordAPIError):
    pass

class DiscordRestClient:

    BASE_URL = "https://discord.com/api/v10/"

    def __init__(
        self,
        bot_token: Optional[str] = None,
        max_retries: int = 3,
        session: Optional[requests.Session] = None,
        on_unauthorized_callback: Optional[Any] = None
    ):
        self.bot_token = bot_token
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.on_unauthorized_callback = on_unauthorized_callback
        self._route_reset_times: Dict[str, float] = {}

    def _get_headers(self, custom_token: Optional[str] = None, is_bearer: bool = False) -> Dict[str, str]:
        token = custom_token or self.bot_token
        if not token:
            raise ValueError("Токен авторизации Discord не указан")
        auth_prefix = "Bearer" if is_bearer else "Bot"
        return {
            "Authorization": f"{auth_prefix} {token}",
            "Content-Type": "application/json",
            "User-Agent": "ConstructorDiscordBots/1.0 (https://constructor-discord-bots.local, 1.0)",
        }

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        custom_token: Optional[str] = None,
        is_bearer: bool = False
    ) -> Any:
        url = urljoin(self.BASE_URL, endpoint.lstrip("/"))
        headers = self._get_headers(custom_token, is_bearer)

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 429:
                    retry_after = 1.0
                    try:
                        err_json = response.json()
                        retry_after = float(err_json.get("retry_after", 1.0))
                    except Exception:
                        header_val = response.headers.get("Retry-After")
                        if header_val:
                            retry_after = float(header_val)

                    logger.warning(
                        "Discord 429 Rate Limit на %s %s. Пауза %s сек. Попытка %d/%d",
                        method, endpoint, retry_after, attempt + 1, self.max_retries
                    )

                    if attempt < self.max_retries:
                        time.sleep(retry_after)
                        continue
                    else:
                        raise DiscordRateLimitError(429, f"Превышен лимит запросов Discord, retry_after={retry_after}")

                if response.status_code == 401:
                    logger.error("Discord 401 Unauthorized для токена на эндпоинте %s", endpoint)
                    if self.on_unauthorized_callback:
                        try:
                            self.on_unauthorized_callback()
                        except Exception as cb_err:
                            logger.exception("Ошибка в callback on_unauthorized: %s", cb_err)
                    raise DiscordUnauthorizedError(401, "Неверный или отозванный токен бота (Discord 401)")

                if response.status_code == 403:
                    data = response.json() if response.content else {}
                    raise DiscordForbiddenError(403, data.get("message", "Доступ запрещен (Discord 403)"), data)

                if response.status_code == 404:
                    data = response.json() if response.content else {}
                    raise DiscordNotFoundError(404, data.get("message", "Ресурс не найден (Discord 404)"), data)

                if not response.ok:
                    data = {}
                    try:
                        data = response.json()
                    except Exception:
                        pass
                    raise DiscordAPIError(response.status_code, data.get("message", response.text), data)

                if response.status_code == 204 or not response.content:
                    return None
                return response.json()

            except requests.RequestException as e:
                if attempt < self.max_retries:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                raise DiscordAPIError(0, f"Сетевая ошибка при запросе к Discord API: {str(e)}")

        raise DiscordAPIError(0, "Не удалось выполнить запрос к Discord API после всех попыток")

    def get_current_bot_user(self) -> Dict[str, Any]:
        data = self.request("GET", "users/@me")
        if not data.get("bot", False):
            raise DiscordAPIError(400, "Указанный токен принадлежит обычному пользователю, а не Discord-боту!")
        return data

    def modify_current_bot_user(self, username: Optional[str] = None, avatar_base64: Optional[str] = None) -> Dict[str, Any]:
        payload = {}
        if username:
            payload["username"] = username
        if avatar_base64:
            payload["avatar"] = avatar_base64
        return self.request("PATCH", "users/@me", json_data=payload)

    def get_guild(self, guild_id: str, with_counts: bool = True) -> Dict[str, Any]:
        return self.request("GET", f"guilds/{guild_id}", params={"with_counts": with_counts})

    def get_guild_channels(self, guild_id: str) -> List[Dict[str, Any]]:
        return self.request("GET", f"guilds/{guild_id}/channels")

    def get_guild_roles(self, guild_id: str) -> List[Dict[str, Any]]:
        return self.request("GET", f"guilds/{guild_id}/roles")

    def get_guild_emojis(self, guild_id: str) -> List[Dict[str, Any]]:
        return self.request("GET", f"guilds/{guild_id}/emojis")

    def get_guild_member(self, guild_id: str, user_id: str) -> Dict[str, Any]:
        return self.request("GET", f"guilds/{guild_id}/members/{user_id}")

    def get_user_guilds(self, user_oauth_token: str) -> List[Dict[str, Any]]:
        return self.request(
            "GET",
            "users/@me/guilds",
            custom_token=user_oauth_token,
            is_bearer=True
        )

    def bulk_overwrite_global_commands(self, application_id: str, commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.request(
            "PUT",
            f"applications/{application_id}/commands",
            json_data=commands
        )

    def bulk_overwrite_guild_commands(
        self, application_id: str, guild_id: str, commands: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        return self.request(
            "PUT",
            f"applications/{application_id}/guilds/{guild_id}/commands",
            json_data=commands
        )
