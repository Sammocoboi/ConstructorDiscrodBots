"""
Расчет permissions integer Discord, генерация ссылок приглашения и проверка прав.
Соответствие ТЗ §4.2 (FR-2.1), §4.7 (FR-7.3), Приложению A и задаче SAN-4.
"""

from typing import Dict, List, Optional, Set
from urllib.parse import urlencode


class DiscordPermissions:
    # Базовые битовые флаги прав Discord API
    CREATE_INSTANT_INVITE = 1 << 0
    KICK_MEMBERS = 1 << 1
    BAN_MEMBERS = 1 << 2
    ADMINISTRATOR = 1 << 3
    MANAGE_CHANNELS = 1 << 4
    MANAGE_GUILD = 1 << 5
    ADD_REACTIONS = 1 << 6
    VIEW_AUDIT_LOG = 1 << 7
    PRIORITY_SPEAKER = 1 << 8
    STREAM = 1 << 9
    VIEW_CHANNEL = 1 << 10
    SEND_MESSAGES = 1 << 11
    SEND_TTS_MESSAGES = 1 << 12
    MANAGE_MESSAGES = 1 << 13
    EMBED_LINKS = 1 << 14
    ATTACH_FILES = 1 << 15
    READ_MESSAGE_HISTORY = 1 << 16
    MENTION_EVERYONE = 1 << 17
    USE_EXTERNAL_EMOJIS = 1 << 18
    VIEW_GUILD_INSIGHTS = 1 << 19
    CONNECT = 1 << 20
    SPEAK = 1 << 21
    MUTE_MEMBERS = 1 << 22
    DEAFEN_MEMBERS = 1 << 23
    MOVE_MEMBERS = 1 << 24
    USE_VAD = 1 << 25
    CHANGE_NICKNAME = 1 << 26
    MANAGE_NICKNAMES = 1 << 27
    MANAGE_ROLES = 1 << 28
    MANAGE_WEBHOOKS = 1 << 29
    MANAGE_GUILD_EXPRESSIONS = 1 << 30
    USE_APPLICATION_COMMANDS = 1 << 31
    REQUEST_TO_SPEAK = 1 << 32
    MANAGE_EVENTS = 1 << 33
    MANAGE_THREADS = 1 << 34
    CREATE_PUBLIC_THREADS = 1 << 35
    CREATE_PRIVATE_THREADS = 1 << 36
    USE_EXTERNAL_STICKERS = 1 << 37
    SEND_MESSAGES_IN_THREADS = 1 << 38
    USE_EMBEDDED_ACTIVITIES = 1 << 39
    MODERATE_MEMBERS = 1 << 40


# Названия прав в человекочитаемом виде
PERMISSION_NAMES: Dict[int, str] = {
    DiscordPermissions.CREATE_INSTANT_INVITE: "Создание приглашения (Create Instant Invite)",
    DiscordPermissions.KICK_MEMBERS: "Выгонять участников (Kick Members)",
    DiscordPermissions.BAN_MEMBERS: "Банить участников (Ban Members)",
    DiscordPermissions.ADMINISTRATOR: "Администратор (Administrator)",
    DiscordPermissions.MANAGE_CHANNELS: "Управление каналами (Manage Channels)",
    DiscordPermissions.MANAGE_GUILD: "Управление сервером (Manage Guild)",
    DiscordPermissions.ADD_REACTIONS: "Добавление реакций (Add Reactions)",
    DiscordPermissions.VIEW_AUDIT_LOG: "Просмотр журнала аудита (View Audit Log)",
    DiscordPermissions.VIEW_CHANNEL: "Просмотр каналов (View Channels)",
    DiscordPermissions.SEND_MESSAGES: "Отправка сообщений (Send Messages)",
    DiscordPermissions.MANAGE_MESSAGES: "Управление сообщениями (Manage Messages)",
    DiscordPermissions.EMBED_LINKS: "Встраивание ссылок (Embed Links)",
    DiscordPermissions.ATTACH_FILES: "Прикрепление файлов (Attach Files)",
    DiscordPermissions.READ_MESSAGE_HISTORY: "Чтение истории сообщений (Read Message History)",
    DiscordPermissions.MANAGE_ROLES: "Управление ролями (Manage Roles)",
    DiscordPermissions.USE_APPLICATION_COMMANDS: "Использование слэш-команд (Use Application Commands)",
    DiscordPermissions.MODERATE_MEMBERS: "Тайм-аут участников (Moderate Members)",
    DiscordPermissions.CHANGE_NICKNAME: "Изменение никнейма (Change Nickname)",
    DiscordPermissions.MANAGE_NICKNAMES: "Управление никнеймами (Manage Nicknames)",
}

# Базовые права для любого бота платформы (Ядро: slash-команды + сообщения)
BASE_BOT_PERMISSIONS: int = (
    DiscordPermissions.VIEW_CHANNEL
    | DiscordPermissions.SEND_MESSAGES
    | DiscordPermissions.EMBED_LINKS
    | DiscordPermissions.USE_APPLICATION_COMMANDS
    | DiscordPermissions.READ_MESSAGE_HISTORY
)

# Приложение A ТЗ: Минимальные права по модулям
MODULE_REQUIRED_PERMISSIONS: Dict[str, int] = {
    "core": BASE_BOT_PERMISSIONS,
    "welcomes": DiscordPermissions.SEND_MESSAGES | DiscordPermissions.EMBED_LINKS | DiscordPermissions.MANAGE_ROLES,
    "moderation": (
        DiscordPermissions.BAN_MEMBERS
        | DiscordPermissions.KICK_MEMBERS
        | DiscordPermissions.MODERATE_MEMBERS
        | DiscordPermissions.MANAGE_MESSAGES
        | DiscordPermissions.VIEW_AUDIT_LOG
        | DiscordPermissions.SEND_MESSAGES
    ),
    "antispam": (
        DiscordPermissions.MANAGE_MESSAGES
        | DiscordPermissions.MODERATE_MEMBERS
        | DiscordPermissions.SEND_MESSAGES
    ),
    "roles": (
        DiscordPermissions.MANAGE_ROLES
        | DiscordPermissions.SEND_MESSAGES
        | DiscordPermissions.ADD_REACTIONS
    ),
    "tickets": (
        DiscordPermissions.MANAGE_CHANNELS
        | DiscordPermissions.MANAGE_ROLES
        | DiscordPermissions.READ_MESSAGE_HISTORY
        | DiscordPermissions.ATTACH_FILES
        | DiscordPermissions.SEND_MESSAGES
    ),
    "levels": DiscordPermissions.SEND_MESSAGES | DiscordPermissions.MANAGE_ROLES,
    "logging": (
        DiscordPermissions.VIEW_AUDIT_LOG
        | DiscordPermissions.SEND_MESSAGES
        | DiscordPermissions.EMBED_LINKS
    ),
    "economy": DiscordPermissions.SEND_MESSAGES | DiscordPermissions.EMBED_LINKS,
    "fun": DiscordPermissions.SEND_MESSAGES | DiscordPermissions.EMBED_LINKS,
    "automation": DiscordPermissions.SEND_MESSAGES | DiscordPermissions.MANAGE_MESSAGES,
    "giveaways": (
        DiscordPermissions.SEND_MESSAGES
        | DiscordPermissions.EMBED_LINKS
        | DiscordPermissions.ADD_REACTIONS
    ),
}

# Приложение A ТЗ: Privileged Gateway Intents по модулям
MODULE_REQUIRED_INTENTS: Dict[str, List[str]] = {
    "welcomes": ["GUILD_MEMBERS"],
    "moderation": ["GUILD_MEMBERS", "MESSAGE_CONTENT"],
    "antispam": ["GUILD_MESSAGES", "MESSAGE_CONTENT"],
    "levels": ["MESSAGE_CONTENT", "GUILD_MESSAGES"],
    "logging": ["GUILD_MEMBERS", "MESSAGE_CONTENT", "GUILD_MESSAGES"],
    "roles": ["GUILD_MEMBERS"],
}


def calculate_permissions_integer(
    enabled_module_ids: Optional[List[str]] = None,
    custom_permissions: int = 0
) -> int:
    """
    Рассчитывает суммарное permissions integer для бота
    на основе базовых прав и списка включенных модулей.
    """
    total = BASE_BOT_PERMISSIONS | custom_permissions
    if enabled_module_ids:
        for mod_id in enabled_module_ids:
            mod_perms = MODULE_REQUIRED_PERMISSIONS.get(mod_id, 0)
            total |= mod_perms
    return total


def calculate_required_intents(enabled_module_ids: Optional[List[str]] = None) -> List[str]:
    """
    Возвращает список уникальных Privileged Gateway Intents,
    необходимых для работы выбранных модулей.
    """
    intents: Set[str] = set()
    if enabled_module_ids:
        for mod_id in enabled_module_ids:
            for item in MODULE_REQUIRED_INTENTS.get(mod_id, []):
                intents.add(item)
    return sorted(list(intents))


def generate_invite_url(
    client_id: str,
    permissions_integer: int,
    guild_id: Optional[str] = None,
    disable_guild_select: bool = False
) -> str:
    """
    Генерирует официальную Discord OAuth2 URL-ссылку для добавления бота на сервер
    с рассчитанными правами permissions и scopes bot + applications.commands.
    """
    params = {
        "client_id": client_id,
        "permissions": str(permissions_integer),
        "scope": "bot applications.commands",
    }
    if guild_id:
        params["guild_id"] = str(guild_id)
        if disable_guild_select:
            params["disable_guild_select"] = "true"
    return f"https://discord.com/oauth2/authorize?{urlencode(params)}"


def check_missing_permissions(bot_permissions_int: int, required_permissions_int: int) -> List[Dict[str, object]]:
    """
    Проверяет, каких прав не хватает боту.
    Возвращает список недостающих прав с флагами и описаниями.
    """
    missing = []
    # Проверяем все известные права
    for perm_flag, perm_name in PERMISSION_NAMES.items():
        if (required_permissions_int & perm_flag) == perm_flag:
            if (bot_permissions_int & perm_flag) != perm_flag:
                missing.append({
                    "flag": perm_flag,
                    "name": perm_name,
                })
    return missing


def check_role_hierarchy(bot_highest_role_pos: int, target_role_pos: int) -> Dict[str, object]:
    """
    Проверяет Discord Role Hierarchy: бот может управлять ролью только если
    наивысшая роль бота находится строго ВЫШЕ целевой роли на сервере.
    """
    can_manage = bot_highest_role_pos > target_role_pos
    return {
        "can_manage": can_manage,
        "bot_role_position": bot_highest_role_pos,
        "target_role_position": target_role_pos,
        "warning": None if can_manage else (
            "Роль бота на сервере должна быть расположена выше роли, которой он управляет! "
            "Переместите роль бота выше в настройках сервера Discord."
        )
    }
