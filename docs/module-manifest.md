# Контракт манифеста модулей (`docs/module-manifest.md`)

Версия: 1.0  
Владелец контракта: Саня (backend-integrations)  
Согласовано: Данила (frontend), Шухратжон (runtime)

---

## 1. Назначение

Манифест модуля определяет метаданные функционального модуля бота:
- Идентификатор и локализованные заголовки/описания;
- Необходимые права бота в Discord (битовая маска Permissions);
- Необходимые Privileged Gateway Intents (Server Members, Message Content, Presence);
- Команды и события, регистрируемые модулем;
- JSON Schema для автоматической генерации формы настроек на фронтенде и серверной валидации настроек по каждой гильдии (`bot_guilds.settings[module_id]`).

---

## 2. Спецификация схемы манифеста (JSON)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "id",
    "title",
    "description",
    "category",
    "required_permissions",
    "required_intents",
    "commands",
    "events",
    "settings_schema"
  ],
  "properties": {
    "id": { "type": "string", "pattern": "^[a-z0-9_-]+$" },
    "title": { "type": "string" },
    "description": { "type": "string" },
    "category": { "type": "string" },
    "is_premium": { "type": "boolean", "default": false },
    "min_plan": { "type": "string", "enum": ["free", "pro", "business"], "default": "free" },
    "required_permissions": { "type": "integer", "description": "Битовая маска Discord Permissions" },
    "required_intents": {
      "type": "array",
      "items": { "type": "string", "enum": ["GUILDS", "GUILD_MEMBERS", "GUILD_MESSAGES", "MESSAGE_CONTENT", "GUILD_PRESENCES"] }
    },
    "commands": {
      "type": "array",
      "items": { "type": "string" }
    },
    "events": {
      "type": "array",
      "items": { "type": "string" }
    },
    "settings_schema": {
      "type": "object",
      "description": "Валидная JSON Schema (Draft 7) для настроек модуля в гильдии"
    }
  }
}
```

---

## 3. Манифесты базовых модулей платформы

### 3.1. Модуль «Приветствия» (`welcomes`)
- **ID:** `welcomes`
- **Заголовок:** Приветствия и прощания
- **Описание:** Отправка приветственных сообщений новым участникам, выдача автороли и сообщения при выходе.
- **Требуемые права:**
  - `SEND_MESSAGES` (0x00000800)
  - `EMBED_LINKS` (0x00004000)
  - `MANAGE_ROLES` (0x10000000)
  - **Итого Permissions:** `0x10004800` (268453888)
- **Intents:** `["GUILD_MEMBERS"]` (Privileged Intent)
- **События:** `["GUILD_MEMBER_ADD", "GUILD_MEMBER_REMOVE"]`
- **JSON Schema настроек:**
```json
{
  "type": "object",
  "properties": {
    "welcome_channel_id": { "type": ["string", "null"], "title": "Канал приветствий" },
    "welcome_message": { "type": "string", "title": "Текст приветствия", "default": "Добро пожаловать на сервер, {user.mention}!" },
    "welcome_embed": { "type": "boolean", "title": "Отправлять как Embed", "default": true },
    "autorole_id": { "type": ["string", "null"], "title": "Авто-роль для новичков" },
    "dm_welcome": { "type": "boolean", "title": "Отправлять приветствие в ЛС", "default": false },
    "dm_message": { "type": "string", "title": "Текст сообщения в ЛС" },
    "goodbye_channel_id": { "type": ["string", "null"], "title": "Канал прощаний" },
    "goodbye_message": { "type": "string", "title": "Текст прощания", "default": "{user.name} покинул нас." }
  }
}
```

### 3.2. Модуль «Модерация» (`moderation`)
- **ID:** `moderation`
- **Заголовок:** Модерация
- **Описание:** Система наказаний (бан, кик, тайм-аут, варны), лог-канал и причины действий.
- **Требуемые права:**
  - `BAN_MEMBERS` (0x00000004)
  - `KICK_MEMBERS` (0x00000002)
  - `MODERATE_MEMBERS` (0x0000010000000000, 1099511627776)
  - `MANAGE_MESSAGES` (0x00002000)
  - `VIEW_AUDIT_LOG` (0x00000080)
  - `SEND_MESSAGES` (0x00000800)
  - **Итого Permissions:** `1099511638150`
- **Intents:** `["GUILD_MEMBERS"]`
- **События:** `["MEMBER_BAN_ADD", "MEMBER_BAN_REMOVE"]`
- **JSON Schema настроек:**
```json
{
  "type": "object",
  "properties": {
    "mod_log_channel_id": { "type": ["string", "null"], "title": "Канал журнала модерации" },
    "warn_action_3": { "type": "string", "enum": ["none", "timeout_1h", "kick", "ban"], "default": "timeout_1h" },
    "warn_action_5": { "type": "string", "enum": ["none", "timeout_24h", "kick", "ban"], "default": "ban" },
    "exempt_role_ids": { "type": "array", "items": { "type": "string" }, "default": [] },
    "default_reason": { "type": "string", "default": "Причина не указана" }
  }
}
```

### 3.3. Модуль «Антиспам» (`antispam`)
- **ID:** `antispam`
- **Заголовок:** Антиспам и антирейд
- **Описание:** Автоматическая фильтрация флуда, массовых упоминаний, ссылок и капса.
- **Требуемые права:**
  - `MANAGE_MESSAGES` (0x00002000)
  - `MODERATE_MEMBERS` (1099511627776)
  - `SEND_MESSAGES` (0x00000800)
- **Intents:** `["MESSAGE_CONTENT", "GUILD_MESSAGES"]`
- **JSON Schema настроек:**
```json
{
  "type": "object",
  "properties": {
    "max_messages_per_5s": { "type": "integer", "minimum": 2, "maximum": 20, "default": 5 },
    "max_mentions_per_message": { "type": "integer", "minimum": 1, "maximum": 20, "default": 5 },
    "block_discord_invites": { "type": "boolean", "default": true },
    "block_links": { "type": "boolean", "default": false },
    "max_caps_percentage": { "type": "integer", "minimum": 50, "maximum": 100, "default": 70 },
    "punishment": { "type": "string", "enum": ["delete", "warn", "timeout_10m"], "default": "timeout_10m" },
    "whitelist_role_ids": { "type": "array", "items": { "type": "string" }, "default": [] }
  }
}
```

### 3.4. Модуль «Тикет-поддержка» (`tickets`)
- **ID:** `tickets`
- **Заголовок:** Тикет-поддержка
- **Описание:** Создание приватных каналов обращений с кнопками и транскриптами.
- **Требуемые права:**
  - `MANAGE_CHANNELS` (0x00000010)
  - `MANAGE_ROLES` (0x10000000)
  - `READ_MESSAGE_HISTORY` (0x00010000)
  - `ATTACH_FILES` (0x00008000)
  - `SEND_MESSAGES` (0x00000800)
- **Intents:** `[]`
- **JSON Schema настроек:**
```json
{
  "type": "object",
  "properties": {
    "category_id": { "type": ["string", "null"], "title": "Категория для тикетов" },
    "support_role_ids": { "type": "array", "items": { "type": "string" }, "title": "Роли поддержки" },
    "max_open_tickets": { "type": "integer", "minimum": 1, "maximum": 10, "default": 1 },
    "transcript_channel_id": { "type": ["string", "null"], "title": "Канал для архива транскриптов" },
    "welcome_text": { "type": "string", "default": "Спасибо за обращение! Опишите проблему, агент поддержки скоро ответит." }
  }
}
```

### 3.5. Модуль «Уровни и опыт» (`levels`)
- **ID:** `levels`
- **Заголовок:** Уровни и опыт
- **Описание:** Начисление опыта за сообщения, уровни, таблицы лидеров и авто-выдача ролей.
- **Требуемые права:**
  - `SEND_MESSAGES` (0x00000800)
  - `MANAGE_ROLES` (0x10000000)
- **Intents:** `["MESSAGE_CONTENT", "GUILD_MESSAGES"]`
- **JSON Schema настроек:**
```json
{
  "type": "object",
  "properties": {
    "min_xp_per_msg": { "type": "integer", "default": 15 },
    "max_xp_per_msg": { "type": "integer", "default": 25 },
    "cooldown_seconds": { "type": "integer", "default": 60 },
    "levelup_channel_mode": { "type": "string", "enum": ["current", "custom", "dm", "silent"], "default": "current" },
    "levelup_channel_id": { "type": ["string", "null"] },
    "levelup_message": { "type": "string", "default": "Поздравляем, {user.mention}! Ты достиг уровня {level}!" },
    "reward_roles": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["level", "role_id"],
        "properties": {
          "level": { "type": "integer" },
          "role_id": { "type": "string" }
        }
      },
      "default": []
    }
  }
}
```

### 3.6. Модуль «Экономика» (`economy`)
- **ID:** `economy`
- **Заголовок:** Экономика и магазин
- **Описание:** Виртуальная валюта, ежедневные награды, магазин товаров и ролей.
- **Требуемые права:**
  - `SEND_MESSAGES` (0x00000800)
  - `EMBED_LINKS` (0x00004000)
  - `MANAGE_ROLES` (0x10000000)
- **Intents:** `[]`
- **JSON Schema настроек:**
```json
{
  "type": "object",
  "properties": {
    "currency_name": { "type": "string", "default": "Монет" },
    "currency_symbol": { "type": "string", "default": "🪙" },
    "daily_amount": { "type": "integer", "default": 100 },
    "work_min": { "type": "integer", "default": 20 },
    "work_max": { "type": "integer", "default": 80 },
    "transfer_fee_percent": { "type": "integer", "minimum": 0, "maximum": 50, "default": 5 }
  }
}
```

### 3.7. Модуль «Логирование событий» (`logging`)
- **ID:** `logging`
- **Заголовок:** Журнал аудита сервера
- **Описание:** Запись изменений каналов, ролей, удалений сообщений и голосовых событий.
- **Требуемые права:**
  - `VIEW_AUDIT_LOG` (0x00000080)
  - `SEND_MESSAGES` (0x00000800)
  - `EMBED_LINKS` (0x00004000)
- **Intents:** `["GUILD_MEMBERS", "GUILD_MESSAGES", "MESSAGE_CONTENT"]`
- **JSON Schema настроек:**
```json
{
  "type": "object",
  "properties": {
    "message_logs_channel_id": { "type": ["string", "null"] },
    "member_logs_channel_id": { "type": ["string", "null"] },
    "voice_logs_channel_id": { "type": ["string", "null"] },
    "log_message_deletes": { "type": "boolean", "default": true },
    "log_message_edits": { "type": "boolean", "default": true },
    "log_role_changes": { "type": "boolean", "default": true }
  }
}
```

### 3.8. Модуль «Роли по реакциям и меню» (`roles`)
- **ID:** `roles`
- **Заголовок:** Реакции-роли и выбор ролей
- **Описание:** Выдача ролей при клике на кнопки, select-меню или реакции.
- **Требуемые права:**
  - `MANAGE_ROLES` (0x10000000)
  - `SEND_MESSAGES` (0x00000800)
  - `ADD_REACTIONS` (0x00000040)
- **Intents:** `["GUILD_MEMBERS"]`
- **JSON Schema настроек:**
```json
{
  "type": "object",
  "properties": {
    "role_menus": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "title": { "type": "string" },
          "channel_id": { "type": "string" },
          "options": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "label": { "type": "string" },
                "role_id": { "type": "string" },
                "emoji": { "type": "string" }
              }
            }
          }
        }
      },
      "default": []
    }
  }
}
```
