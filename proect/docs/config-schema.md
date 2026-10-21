# Config Schema v1

Конфигурация бота — единый JSONB-документ. Лимит: 2 МБ. Секреты запрещены.

## Структура

{
  "schema_version": 1,
  "profile": {
    "status": "online",          // online | idle | dnd
    "activity": {"type": "playing", "text": "/help"}
  },
  "modules": [
    {"id": "moderation", "enabled": true, "settings": {}}
  ],
  "commands": [
    {"id": "cmd_1", "name": "ping", "type": "slash", "options": [], "flow_id": "flow_1"}
  ],
  "flows": [
    {
      "id": "flow_1",
      "trigger": {"type": "slash_command", "command_id": "cmd_1"},
      "nodes": [
        {"id": "n1", "type": "send_message",
         "params": {"content": "Pong! {bot.latency} ms", "ephemeral": true}}
      ],
      "edges": []
    }
  ],
  "messages": [],
  "variables_schema": []
}

## Правила

- `schema_version` обязателен; миграции между версиями — отдельный модуль.
- Неизвестный `type` блока → документ невалиден.
- Токены, пароли, ключи — только вне документа (в `bots.token_encrypted`).
- Владелец схемы: Шухратжон. Изменения — через PR.