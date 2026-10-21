# Block Registry v1

Один JSON-манифест — источник правды для Runtime и палитры React Flow.
Файлы: `content/blocks/<type>.json`. Загрузка — `BlockRegistry.load_manifests()`,
обработчики регистрируются в `build_default_registry()`.

Изменения только через PR. Соавтор по UI — Данила.

## Формат манифеста

```json
{
  "type": "send_message",
  "category": "action",
  "title": "Отправить сообщение",
  "description": "Отправляет текст и/или embed в канал",
  "params": {
    "channel_id": {"type": "channel", "required": false},
    "content": {"type": "string", "required": false, "max_length": 2000},
    "embed": {"type": "embed", "required": false},
    "ephemeral": {"type": "boolean", "default": false}
  },
  "inputs": ["flow"],
  "outputs": ["flow"],
  "limits": {"max_per_flow": 200}
}
```

Обязательные поля: `type`, `category`, `title`. `params` по умолчанию `{}`,
`inputs`/`outputs` — `["flow"]`. Дубли `type` запрещены. Категории:
`trigger`, `condition`, `action`, `data`, `logic`. Категория `trigger`
определяет стартовые узлы flow.

Обработчик получает `(params, ctx)` и возвращает:

- `None` — продолжить по основному ребру;
- строку — имя ветки;
- `{"branch": "true", "output": {...}, "stop": true}` — ветка, данные для
  трассировки и остановка.

## Блоки

### Триггеры

| type | Параметры | Выход | Intents |
|---|---|---|---|
| `slash_command` | `command_id` (string, required, ≤64) | flow | — |
| `join_member` | — | flow | `members` |
| `message` | `prefix`, `contains`, `regex` (string, ≤200) | flow | `message_content` |

Триггеры сами ничего не делают в executor (`noop`) — они точка входа. В
Discord-адаптере `slash_command` привязывает flow к slash-команде,
`join_member` — к `on_member_join`, `message` — к `on_message`.

### Условия

| type | Параметры | Ветки |
|---|---|---|
| `if` | `condition` (condition, required) | `true`, `false` |
| `switch` | `value` (string, required), `cases` (array), `default_branch` (по умолчанию `default`) | ветки из `cases[].branch`, иначе default |
| `random_chance` | `probability` (number 0…100, по умолчанию 50) | `true`, `false` |

`switch.cases` — `[{"value": "a", "branch": "case_a"}]`. Сравнение строгое после
подстановки переменных. Для `if` обе ветки обязательны (error), для
`random_chance` отсутствие ветки — warning.

### Действия

| type | Параметры | Примечание |
|---|---|---|
| `send_message` | `channel_id` (channel), `content` (≤2000), `embed`, `ephemeral` (bool) | канал по умолчанию — текущий; в dry-run не отправляет |
| `send_dm` | `user_id` (user), `content` (≤2000), `embed` | пользователь по умолчанию — автор события; нужен `user_id` |
| `add_role` | `user_id`, `role_id` (role, required) | пользователь по умолчанию — автор события |
| `remove_role` | `user_id`, `role_id` (role, required) | то же |

### Данные и логика

| type | Параметры | Примечание |
|---|---|---|
| `set_variable` | `name` (string, required, ≤64), `value` (any), `operation`: `set`/`increment`/`append` | `increment` требует числа; `append` добавляет в список |
| `delay` | `seconds` (number 0…30, по умолчанию 1) | в dry-run не ждёт |
| `run_flow` | `flow_id` (string, required, ≤64) | общий `ctx.variables`, глубина ≤5 |
| `stop` | — | останавливает выполнение, `stopped=true` |
| `log` | `message` (string, required, ≤1000), `level`: `debug`/`info`/`warning`/`error` | пишет в лог Runtime, не в Discord |

## Пример flow

```json
{
  "id": "flow_hello",
  "nodes": [
    {"id": "t", "type": "join_member", "params": {}},
    {
      "id": "check",
      "type": "if",
      "params": {"condition": {"op": "exists", "left": "{user.id}"}}
    },
    {
      "id": "msg",
      "type": "send_message",
      "params": {"content": "Добро пожаловать, {user.name}!"}
    },
    {"id": "skip", "type": "stop", "params": {}}
  ],
  "edges": [
    {"from": "t", "to": "check"},
    {"from": "check", "to": "msg", "branch": "true"},
    {"from": "check", "to": "skip", "branch": "false"}
  ]
}
```

## Валидация блока

- `type` есть в реестре, `params` — объект;
- обязательные параметры присутствуют;
- `string`/`boolean`/`number`/`channel`/`role`/`user` имеют нужный тип;
- длина строк не превышает `max_length`;
- неизвестный параметр — warning;
- для `send_message`/`send_dm` проверяются лимиты текста и эмбедов.

## Добавление блока

1. Добавить `content/blocks/<type>.json`.
2. Добавить обработчик в `runtime/interpreter/handlers.py` и зарегистрировать.
3. Обновить тесты `tests/test_content.py` и, при необходимости, executor.
4. Обновить этот документ и UI-палитру (Данила).
