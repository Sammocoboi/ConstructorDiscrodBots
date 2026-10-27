# Config Schema v1

Конфигурация бота — единый JSON-документ, который хранится в
`bots_botversion.content` (активная версия) и `bots_botdraft.content` (fallback,
если активной версии нет). Runtime также объединяет с конфигом
`bots_bot.intents`. Отдельного `bots_bot.config` нет.

Ограничения: не более **2 МБ**, `schema_version` обязателен, секреты запрещены.
Владелец контракта: Шухратжон. Изменения — через PR.

## Полная структура

```json
{
  "schema_version": 1,
  "profile": {
    "status": "online",
    "activity": {"type": "playing", "text": "/help"}
  },
  "modules": [
    {"id": "moderation", "enabled": true, "settings": {}}
  ],
  "commands": [
    {
      "id": "cmd_ping",
      "name": "ping",
      "description": "Проверить задержку",
      "type": "slash",
      "options": [],
      "flow_id": "flow_ping"
    }
  ],
  "flows": [
    {
      "id": "flow_ping",
      "trigger": {"type": "slash_command", "command_id": "cmd_ping"},
      "nodes": [
        {"id": "n1", "type": "slash_command", "params": {"command_id": "cmd_ping"}},
        {
          "id": "n2",
          "type": "send_message",
          "params": {"content": "Pong! {bot.latency} ms", "ephemeral": true}
        }
      ],
      "edges": [{"from": "n1", "to": "n2"}]
    }
  ],
  "messages": [],
  "variables_schema": []
}
```

## Секции

### `profile`

- `status`: `online` | `idle` | `dnd` | `invisible`.
- `activity.type`: `playing` | `watching` | `listening` | `competing`.
- `activity.text`: до 128 символов.

### `modules`

Список включённых модулей: `{id, enabled, settings}`. Настройки модуля
валидируются по манифесту модуля (зона backend-integrations). Runtime учитывает
`id` при проверке дублей; неизвестные модули не исполняет.

### `commands`

Slash-команды проекта:

- `id` — уникальный идентификатор в документе;
- `name` — `^[a-z0-9_-]{1,32}$`, уникален;
- `description` — до 100 символов;
- `type` — пока `slash`;
- `options` — параметры Discord (передаются в адаптер);
- `flow_id` — ссылка на flow; должен существовать.

### `flows`

Один flow — граф выполнения:

- `id` — уникальный;
- `start` — необязательный id стартового узла;
- `trigger` — необязательное описание триггера для UI;
- `nodes` — непустой список узлов;
- `edges` — список связей `{from, to, branch?}`.

Стартовые узлы определяются так:

1. `flow.start`, если он существует;
2. все узлы блоков категории `trigger`;
3. все узлы без входящих рёбер.

Узел: `{id, type, params}`. `type` обязан быть в реестре блоков, `params` —
объект. Неизвестные параметры дают warning.

`branch` используется блоками `if`, `switch`, `random_chance`. Ребро без
`branch` — основной поток. Если ветка не найдена, executor пробует ребро без
ветки; если и его нет — выполнение завершается.

### `messages`, `variables_schema`

Зарезервированы под библиотеку сообщений и описание переменных. Runtime
проверяет только тип `variables_schema` (список). Секреты в этих секциях
запрещены так же, как во всём документе.

## Переменные и выражения

Строки в параметрах блоков разрешают подстановки:

- `{user.id}`, `{user.name}`, `{guild.id}`, `{channel.id}`;
- `{args.<name>}` — аргументы slash-команды;
- `{bot.latency}`;
- `{variables.counter}` или `{counter}`;
- в строке можно смешивать текст и подстановки: `Привет, {user.name}!`.

Контекст: `user`, `guild`, `channel`, `message`, `args`, `bot`, `variables`.
Если строка целиком является подстановкой, возвращается исходное значение
(число, список, объект), иначе — строка. `None` превращается в пустую строку.

Условия:

```json
{"op": "eq", "left": "{args.mode}", "right": "fast"}
```

```json
{"jsonlogic": {"and": [{"var": "user.id"}, {"==": [{"var": "args.n"}, "1"]}]}}
```

Поддерживаются операторы `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `contains`,
`starts_with`, `ends_with`, `in`, `is_empty`, `exists`, `matches`, `not`, а также
JSONLogic: `var`, `missing`, `missing_some`, `if`, `and`, `or`, `not`, `cat`,
`in`, `contains`, `==`, `===`, `!=`, `!==`, `>`, `>=`, `<`, `<=`, `+`, `-`, `*`,
`/`, `%`, `min`, `max`, `merge`. `eval` и сетевые вызовы запрещены.

## Лимиты исполнения

| Лимит | Значение |
|---|---|
| Размер конфигурации | 2 МБ |
| Блоков на запуск | 200 |
| Длительность запуска | 30 секунд |
| Глубина `run_flow` | 5 |
| Посещений одного узла | 50 |
| `delay.seconds` | 0…30 |
| `content` сообщения | 2000 символов |
| Эмбедов | 10 |
| Полей эмбеда | 25 |

Лимиты Discord: title 256, description 4096, footer 2048, author 256,
field name 256, field value 1024.

## Валидация

`runtime.interpreter.validation.validate_config(config, registry)` возвращает
`{ok, errors, warnings}`. Проверяется:

- `schema_version == 1`, размер, отсутствие секретов;
- профиль, дубли flow/command/module, ссылки `flow_id`;
- неизвестные блоки, обязательные параметры, типы и длины;
- висячие рёбра, циклы, недостижимые узлы, незавершённые ветки;
- триггер без следующего узла;
- лимиты сообщений и эмбедов.

`errors` блокируют публикацию, `warnings` — нет. Пример ответа:

```json
{
  "ok": false,
  "errors": [
    {"code": "missing_param", "message": "node n2: missing required param 'content'", "severity": "error", "node_id": "n2"}
  ],
  "warnings": [
    {"code": "unreachable_node", "message": "node n9 is unreachable", "severity": "warning", "node_id": "n9"}
  ]
}
```

## Секреты

Запрещены ключи вида `token`, `secret`, `password`, `api_key`, `private_key`,
`authorization`, `cookie` с непустым значением. Дополнительно ищутся Discord
token-паттерны и `Bearer ...`. Токен бота хранится только в
`bots.token_encrypted` (AES-256-GCM).
