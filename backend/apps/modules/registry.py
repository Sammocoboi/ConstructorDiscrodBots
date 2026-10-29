from typing import Any

import jsonschema
from rest_framework.exceptions import ValidationError

from integrations.discord.permissions import (
    MODULE_REQUIRED_INTENTS,
    MODULE_REQUIRED_PERMISSIONS,
    check_missing_permissions,
    check_role_hierarchy,
)

BUILTIN_MODULES: dict[str, dict[str, Any]] = {
    "welcomes": {
        "id": "welcomes",
        "slug": "welcomes",
        "title": "Приветствия и прощания",
        "description": "Автоматическая отправка приветствий, прощальных сообщений и выдача начальной роли (авто-роль).",
        "category": "Автоматизация",
        "is_premium": False,
        "min_plan": "free",
        "required_permissions": MODULE_REQUIRED_PERMISSIONS["welcomes"],
        "required_intents": MODULE_REQUIRED_INTENTS["welcomes"],
        "commands": ["welcome", "goodbye", "autorole"],
        "events": ["GUILD_MEMBER_ADD", "GUILD_MEMBER_REMOVE"],
        "dangerous_actions": False,
        "settings_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "welcome_channel_id": {"type": ["string", "null"], "title": "Канал приветствий"},
                "welcome_message": {
                    "type": "string",
                    "title": "Текст приветствия",
                    "default": "Добро пожаловать на сервер, {user.mention}!",
                },
                "welcome_embed": {
                    "type": "boolean",
                    "title": "Отправлять как Embed",
                    "default": True,
                },
                "autorole_id": {
                    "type": ["string", "null"],
                    "title": "Авто-роль для новых участников",
                },
                "dm_welcome": {
                    "type": "boolean",
                    "title": "Отправлять приветствие в ЛС",
                    "default": False,
                },
                "dm_message": {
                    "type": "string",
                    "title": "Текст в ЛС",
                    "default": "Приветствуем в нашем сообществе!",
                },
                "goodbye_channel_id": {"type": ["string", "null"], "title": "Канал прощаний"},
                "goodbye_message": {
                    "type": "string",
                    "title": "Текст прощания",
                    "default": "{user.name} покинул нас.",
                },
            },
        },
    },
    "moderation": {
        "id": "moderation",
        "slug": "moderation",
        "title": "Модерация",
        "description": "Бан, кик, тайм-аут, варны, журнал действий и автоматические наказания по порогам варнов.",
        "category": "Модерация",
        "is_premium": False,
        "min_plan": "free",
        "required_permissions": MODULE_REQUIRED_PERMISSIONS["moderation"],
        "required_intents": MODULE_REQUIRED_INTENTS["moderation"],
        "commands": [
            "ban",
            "unban",
            "kick",
            "timeout",
            "warn",
            "warnings",
            "clearwarns",
            "purge",
            "modlog",
        ],
        "events": ["MEMBER_BAN_ADD", "MEMBER_BAN_REMOVE"],
        "dangerous_actions": True,
        "settings_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "mod_log_channel_id": {
                    "type": ["string", "null"],
                    "title": "Канал журнала модерации",
                },
                "warn_action_3": {
                    "type": "string",
                    "title": "Действие при 3 варнах",
                    "enum": ["none", "timeout_1h", "kick", "ban"],
                    "default": "timeout_1h",
                },
                "warn_action_5": {
                    "type": "string",
                    "title": "Действие при 5 варнах",
                    "enum": ["none", "timeout_24h", "kick", "ban"],
                    "default": "ban",
                },
                "exempt_role_ids": {
                    "type": "array",
                    "title": "Иммунные роли (белый список)",
                    "items": {"type": "string"},
                    "default": [],
                },
                "default_reason": {"type": "string", "default": "Причина не указана"},
            },
        },
    },
    "antispam": {
        "id": "antispam",
        "slug": "antispam",
        "title": "Антиспам и антирейд",
        "description": "Блокировка флуда, повторяющихся сообщений, массовых упоминаний, ссылок-приглашений и капса.",
        "category": "Безопасность",
        "is_premium": False,
        "min_plan": "free",
        "required_permissions": MODULE_REQUIRED_PERMISSIONS["antispam"],
        "required_intents": MODULE_REQUIRED_INTENTS["antispam"],
        "commands": ["slowmode", "lock", "unlock"],
        "events": ["MESSAGE_CREATE"],
        "dangerous_actions": False,
        "settings_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "max_messages_per_5s": {
                    "type": "integer",
                    "minimum": 2,
                    "maximum": 20,
                    "default": 5,
                },
                "max_mentions_per_message": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5,
                },
                "block_discord_invites": {"type": "boolean", "default": True},
                "block_links": {"type": "boolean", "default": False},
                "max_caps_percentage": {
                    "type": "integer",
                    "minimum": 50,
                    "maximum": 100,
                    "default": 70,
                },
                "punishment": {
                    "type": "string",
                    "enum": ["delete", "warn", "timeout_10m"],
                    "default": "timeout_10m",
                },
                "whitelist_role_ids": {"type": "array", "items": {"type": "string"}, "default": []},
            },
        },
    },
    "tickets": {
        "id": "tickets",
        "slug": "tickets",
        "title": "Тикет-поддержка",
        "description": "Система обращений в приватных каналах с кнопками, транскриптами и назначением агентов поддержки.",
        "category": "Поддержка",
        "is_premium": False,
        "min_plan": "free",
        "required_permissions": MODULE_REQUIRED_PERMISSIONS["tickets"],
        "required_intents": [],
        "commands": [
            "ticket_panel",
            "ticket_close",
            "ticket_add",
            "ticket_remove",
            "ticket_transcript",
        ],
        "events": ["INTERACTION_CREATE"],
        "dangerous_actions": False,
        "settings_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "category_id": {"type": ["string", "null"], "title": "Категория каналов тикетов"},
                "support_role_ids": {"type": "array", "items": {"type": "string"}, "default": []},
                "max_open_tickets": {"type": "integer", "minimum": 1, "maximum": 10, "default": 1},
                "transcript_channel_id": {"type": ["string", "null"]},
                "welcome_text": {
                    "type": "string",
                    "default": "Спасибо за обращение! Опишите проблему, агент скоро подключится.",
                },
            },
        },
    },
    "levels": {
        "id": "levels",
        "slug": "levels",
        "title": "Уровни и опыт",
        "description": "Начисление XP за общение, карточки ранга (/rank), таблица лидеров (/top) и роли за уровни.",
        "category": "Социальное",
        "is_premium": False,
        "min_plan": "free",
        "required_permissions": MODULE_REQUIRED_PERMISSIONS["levels"],
        "required_intents": MODULE_REQUIRED_INTENTS["levels"],
        "commands": ["rank", "top", "setxp", "levelroles", "resetlevels", "xpboost"],
        "events": ["MESSAGE_CREATE"],
        "dangerous_actions": False,
        "settings_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "min_xp_per_msg": {"type": "integer", "default": 15},
                "max_xp_per_msg": {"type": "integer", "default": 25},
                "cooldown_seconds": {"type": "integer", "default": 60},
                "levelup_channel_mode": {
                    "type": "string",
                    "enum": ["current", "custom", "dm", "silent"],
                    "default": "current",
                },
                "levelup_channel_id": {"type": ["string", "null"]},
                "levelup_message": {
                    "type": "string",
                    "default": "Поздравляем, {user.mention}! Ты достиг уровня {level}!",
                },
                "reward_roles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["level", "role_id"],
                        "properties": {"level": {"type": "integer"}, "role_id": {"type": "string"}},
                    },
                    "default": [],
                },
            },
        },
    },
    "economy": {
        "id": "economy",
        "slug": "economy",
        "title": "Экономика и магазин",
        "description": "Виртуальная валюта, ежедневная награда (/daily), работа (/work), переводы и магазин ролей.",
        "category": "Экономика",
        "is_premium": False,
        "min_plan": "free",
        "required_permissions": MODULE_REQUIRED_PERMISSIONS["economy"],
        "required_intents": [],
        "commands": [
            "balance",
            "daily",
            "work",
            "pay",
            "shop",
            "buy",
            "inventory",
            "gamble",
            "baltop",
        ],
        "events": [],
        "dangerous_actions": False,
        "settings_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "currency_name": {"type": "string", "default": "Монет"},
                "currency_symbol": {"type": "string", "default": "🪙"},
                "daily_amount": {"type": "integer", "default": 100},
                "work_min": {"type": "integer", "default": 20},
                "work_max": {"type": "integer", "default": 80},
                "transfer_fee_percent": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "default": 5,
                },
            },
        },
    },
    "logging": {
        "id": "logging",
        "slug": "logging",
        "title": "Журнал аудита сервера",
        "description": "Логирование удаления/редактирования сообщений, входа/выхода участников, смены ролей и голосовых каналов.",
        "category": "Логирование",
        "is_premium": False,
        "min_plan": "free",
        "required_permissions": MODULE_REQUIRED_PERMISSIONS["logging"],
        "required_intents": MODULE_REQUIRED_INTENTS["logging"],
        "commands": [],
        "events": ["MESSAGE_DELETE", "MESSAGE_UPDATE", "GUILD_MEMBER_UPDATE", "VOICE_STATE_UPDATE"],
        "dangerous_actions": False,
        "settings_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "message_logs_channel_id": {"type": ["string", "null"]},
                "member_logs_channel_id": {"type": ["string", "null"]},
                "voice_logs_channel_id": {"type": ["string", "null"]},
                "log_message_deletes": {"type": "boolean", "default": True},
                "log_message_edits": {"type": "boolean", "default": True},
                "log_role_changes": {"type": "boolean", "default": True},
            },
        },
    },
    "roles": {
        "id": "roles",
        "slug": "roles",
        "title": "Реакции-роли и меню выбора",
        "description": "Интерактивное получение ролей участниками через кнопки, select-меню и реакции под сообщениями.",
        "category": "Роли",
        "is_premium": False,
        "min_plan": "free",
        "required_permissions": MODULE_REQUIRED_PERMISSIONS["roles"],
        "required_intents": MODULE_REQUIRED_INTENTS["roles"],
        "commands": [
            "role_add",
            "role_remove",
            "reactionroles",
            "selfroles",
            "rolemenu",
            "colorrole",
        ],
        "events": ["MESSAGE_REACTION_ADD", "MESSAGE_REACTION_REMOVE", "INTERACTION_CREATE"],
        "dangerous_actions": False,
        "settings_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "role_menus": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "channel_id": {"type": "string"},
                            "options": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "label": {"type": "string"},
                                        "role_id": {"type": "string"},
                                        "emoji": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "default": [],
                }
            },
        },
    },
    "fun": {
        "id": "fun",
        "slug": "fun",
        "title": "Мини-игры и развлечения",
        "description": "Монетка, кубик, шар предсказаний 8ball, викторина, камень-ножницы-бумага и казино.",
        "category": "Развлечения",
        "is_premium": False,
        "min_plan": "free",
        "required_permissions": MODULE_REQUIRED_PERMISSIONS["fun"],
        "required_intents": [],
        "commands": [
            "coinflip",
            "dice",
            "8ball",
            "rps",
            "trivia",
            "guessnumber",
            "slots",
            "hangman",
        ],
        "events": [],
        "dangerous_actions": False,
        "settings_schema": {"type": "object", "properties": {}},
    },
    "automation": {
        "id": "automation",
        "slug": "automation",
        "title": "Автоматизация и авто-ответы",
        "description": "Автоответчик по триггер-словам, автоудаление сообщений, таймеры сообщений и игра в счет.",
        "category": "Автоматизация",
        "is_premium": False,
        "min_plan": "free",
        "required_permissions": MODULE_REQUIRED_PERMISSIONS["automation"],
        "required_intents": ["MESSAGE_CONTENT", "GUILD_MESSAGES"],
        "commands": ["autoresponder", "autodelete", "schedule", "counting"],
        "events": ["MESSAGE_CREATE"],
        "dangerous_actions": False,
        "settings_schema": {
            "type": "object",
            "properties": {
                "autoresponders": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "trigger": {"type": "string"},
                            "response": {"type": "string"},
                            "exact_match": {"type": "boolean", "default": False},
                        },
                    },
                    "default": [],
                }
            },
        },
    },
    "giveaways": {
        "id": "giveaways",
        "slug": "giveaways",
        "title": "Розыгрыши призов",
        "description": "Проведение конкурсов и розыгрышей с таймером, реакциями и автоматическим выбором победителя.",
        "category": "Развлечения",
        "is_premium": False,
        "min_plan": "free",
        "required_permissions": MODULE_REQUIRED_PERMISSIONS["giveaways"],
        "required_intents": [],
        "commands": ["giveaway_start", "giveaway_end", "giveaway_reroll", "giveaway_list"],
        "events": ["INTERACTION_CREATE"],
        "dangerous_actions": False,
        "settings_schema": {
            "type": "object",
            "properties": {
                "default_channel_id": {"type": ["string", "null"]},
                "manager_role_id": {"type": ["string", "null"]},
            },
        },
    },
}


class ModuleRegistry:
    @staticmethod
    def list_all() -> list[dict[str, Any]]:
        return list(BUILTIN_MODULES.values())

    @staticmethod
    def get_by_slug(slug: str) -> dict[str, Any] | None:
        return BUILTIN_MODULES.get(slug)

    @staticmethod
    def validate_settings(slug: str, settings_dict: dict[str, Any]) -> None:
        manifest = BUILTIN_MODULES.get(slug)
        if not manifest:
            raise ValidationError(f"Модуль '{slug}' не существует")

        schema = manifest.get("settings_schema")
        if not schema:
            return

        try:
            jsonschema.validate(instance=settings_dict, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            raise ValidationError(
                f"Настройки модуля '{slug}' не соответствуют JSON Schema: {e.message}"
            ) from e

    @staticmethod
    def check_permissions_and_hierarchy(
        slug: str,
        bot_permissions_int: int,
        bot_highest_role_pos: int = 100,
        target_role_pos: int | None = None,
    ) -> dict[str, Any]:
        manifest = BUILTIN_MODULES.get(slug)
        if not manifest:
            return {"valid": False, "error": f"Модуль {slug} не найден"}

        required_perms = manifest.get("required_permissions", 0)
        missing_perms = check_missing_permissions(bot_permissions_int, required_perms)

        hierarchy_check = None
        if target_role_pos is not None:
            hierarchy_check = check_role_hierarchy(bot_highest_role_pos, target_role_pos)

        warnings = []
        if manifest.get("dangerous_actions"):
            warnings.append(
                f"Внимание: модуль «{manifest['title']}» содержит потенциально опасные действия "
                f"(бан, кик, удаление сообщений). Убедитесь, что настроили белые списки ролей."
            )

        if missing_perms:
            warnings.append(
                f"Боту не хватает {len(missing_perms)} прав в Discord для полной работы модуля «{manifest['title']}»."
            )

        if hierarchy_check and not hierarchy_check.get("can_manage"):
            warnings.append(str(hierarchy_check["warning"]))

        return {
            "valid": len(missing_perms) == 0
            and (hierarchy_check is None or hierarchy_check.get("can_manage")),
            "missing_permissions": missing_perms,
            "hierarchy_check": hierarchy_check,
            "dangerous_actions": manifest.get("dangerous_actions", False),
            "warnings": warnings,
        }
