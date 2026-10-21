# Block Registry v1

Один JSON-манифест — источник правды для Runtime и палитры React Flow.
Файлы: `content/blocks/<type>.json`.

## Формат манифеста

{
  "type": "send_message",
  "category": "action",
  "title": "Отправить сообщение",
  "description": "Отправляет сообщение в канал",
  "params": {
    "channel_id": {"type": "channel", "required": true},
    "content": {"type": "string", "required": true, "max_length": 2000},
    "ephemeral": {"type": "boolean", "default": false}
  },
  "inputs": ["flow"],
  "outputs": ["flow"],
  "limits": {"max_per_flow": 200}
}

## Первые 10 блоков (этап 0)

| type | category | назначение |
|---|---|---|
| slash_command | trigger | триггер slash-команды |
| join_member | trigger | вход участника |
| message | trigger | сообщение по ключевому слову |
| if | condition | ветвление |
| switch | condition | переключатель |
| random_chance | condition | случайный шанс % |
| send_message | action | отправить сообщение |
| add_role | action | выдать роль |
| set_variable | data | установить переменную |
| delay | logic | задержка |

Правило: изменения только через PR. Соавтор — Данила (UI).