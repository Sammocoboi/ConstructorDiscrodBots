# Runtime Protocol v1

Контракт между backend (API) и Runtime. Источник SQL-схемы:
`infra/migrations/001_runtime.sql`. Runtime и backend используют один PostgreSQL.

## Таблицы

### `bots`

Ключевые для Runtime колонки:

| колонка | тип | описание |
|---|---|---|
| `id` | uuid | PK |
| `name` | text | имя бота |
| `token_encrypted` | text | AES-256-GCM токен (base64 nonce+ciphertext) |
| `desired_state` | text | `running` / `stopped` |
| `status` | text | `stopped` / `starting` / `online` / `error` / `suspended` |
| `last_error` | text | последняя ошибка |
| `last_error_at` | timestamptz | когда произошла ошибка |
| `config` | jsonb | fallback-конфигурация |
| `active_version_id` | uuid | опубликованная версия |
| `deleted_at` | timestamptz | soft delete |
| `intents` | jsonb | заявленные intents |

Runtime выбирает последнюю `bot_versions` со `status='published'`; если её нет —
`bots.config`.

### `runtime_commands`

| колонка | тип | описание |
|---|---|---|
| `id` | uuid | PK |
| `bot_id` | uuid | FK `bots` |
| `command` | text | `start` / `stop` / `restart` / `reload` |
| `payload` | jsonb | дополнительные данные |
| `status` | text | `pending` / `acked` / `done` / `failed` |
| `error` | text | текст ошибки |
| `requested_by` | text | кто запросил |
| `created_at` | timestamptz | |
| `acked_at` | timestamptz | |
| `finished_at` | timestamptz | |

### `bot_runtime_state`

| колонка | тип | описание |
|---|---|---|
| `bot_id` | uuid | PK, FK `bots` |
| `worker_id` | text | воркер, владеющий ботом |
| `status` | text | статус бота |
| `latency_ms` | integer | ping |
| `uptime_seconds` | bigint | uptime |
| `heartbeat_at` | timestamptz | обновляется каждые 15 секунд |
| `started_at` | timestamptz | старт текущей попытки |
| `last_error` | text | ошибка |

### `bot_versions`

`id`, `bot_id`, `number`, `status` (`draft`/`published`/`archived`), `config`,
`comment`, `created_by`, `created_at`, `UNIQUE(bot_id, number)`.

### `templates`, `flow_traces`, `scheduled_jobs`

- `templates` — системные (`is_system=true`, `owner_id=NULL`) и пользовательские
  шаблоны; `UNIQUE(owner_id, slug)` для пользовательских.
- `flow_traces` — трассировки запусков (сейчас пишутся вызывающей стороной;
  таблица готова для API/тестов).
- `scheduled_jobs` — cron-задачи Runtime: `name`, `cron`, `handler`, `payload`,
  `enabled`, `status`, `next_run_at`, `last_error`.

## Доставка команд

1. Backend вставляет строку в `runtime_commands` со `status='pending'`.
2. Триггер `runtime_commands_notify` выполняет
   `pg_notify('runtime_commands_channel', NEW.id::text)`.
   Payload — **id команды**, не bot_id.
3. `CommandListener` держит отдельное соединение `LISTEN runtime_commands_channel`.
   NOTIFY только будит воркер; сами команды читаются из таблицы.
4. Runtime выбирает `pending` пачками, выполняет и ставит:
   `acked` → `done` или `failed` (+ `error`, `finished_at`).
5. Страховка: polling раз в `COMMAND_POLL_INTERVAL` (по умолчанию 30 секунд).
   Если LISTEN/NOTIFY недоступен, polling продолжает работать.

Команды:

| команда | действие |
|---|---|
| `start` | запустить бота, если он не запущен |
| `stop` | остановить и снять advisory lock |
| `restart` | stop + start |
| `reload` | перечитать `bots`/published-версию и применить конфиг без рестарта |

`reload` обновляет имя, токен и конфигурацию; для применения slash-команд
адаптер пересобирает их. Если бот не запущен, reload — no-op.

## Блокировка

`pg_try_advisory_lock(hashtext(bot_id))` на отдельном соединении, которое живёт
всё время работы бота. Один бот — ровно один воркер. Соединение закрывается
при stop/shutdown, lock снимается автоматически. TTL/lease не нужен: сессия
PostgreSQL и есть lease. Второй воркер получает `None` и пропускает бота.

## Heartbeat

- Каждые `HEARTBEAT_INTERVAL` (15 секунд) воркер обновляет
  `bot_runtime_state.heartbeat_at`, `latency_ms`, `uptime_seconds`.
- Heartbeat пишется для ботов в статусах `starting` и `online`.
- Backend считает бота недоступным, если `heartbeat_at` старше 60 секунд.
  Runtime сам не меняет статус по таймауту — это делает API/оператор.

## Жизненный цикл

```text
stopped -> starting -> online
                 \-> error -> starting (backoff) ... -> suspended
online -> error (gateway lost) -> starting ... -> suspended
```

- Авторестарт: до `RESTART_LIMIT` (5) попыток, backoff `1, 2, 4, 8, 16...`
  секунд, максимум 30.
- Если бот проработал ≥60 секунд, счётчик попыток сбрасывается.
- `InvalidTokenError` / `MissingIntentsError` — постоянные ошибки: статус
  `error`, `desired_state` переводится в `stopped`, рестартов нет.
- При превышении лимита — `suspended` с ошибкой.
- При capacity (`MAX_BOTS_PER_WORKER`) бот получает `suspended` и ждёт
  освобождения места/другого воркера.

## Ошибки

| код/исключение | причина |
|---|---|
| `invalid_token` / `InvalidTokenError` | Discord 401 |
| `missing_intents` / `MissingIntentsError` | не включены Privileged Intents |
| `SupervisorCapacityError` | воркер заполнен |
| `FlowExecutionError` | ошибка блока/графа |
| `FlowTimeoutError` | превышены 30 секунд |
| `FlowLimitError` | блоки, глубина или посещения |
| `ValidationError` | невалидный конфиг/шаблон |

## Health и метрики

HTTP-сервер Runtime (по умолчанию `0.0.0.0:8080`):

- `GET /health` — `{"status":"ok","worker_id":"..."}`;
- `GET /ready` — `200`, пока воркер не остановлен, иначе `503`;
- `GET /metrics` — Prometheus-текст:
  `runtime_bots_total{status}`, `runtime_commands_total`,
  `runtime_commands_failed_total`, `runtime_restarts_total`,
  `runtime_uptime_seconds`, `runtime_bot_latency_ms`, `runtime_bot_uptime_seconds`;
- `GET /` — полный snapshot (боты, статусы, capacity, metrics).

## Переменные окружения

См. `infra/.env.example`. Ключевые: `DATABASE_URL`, `WORKER_ID`,
`MAX_BOTS_PER_WORKER`, `HEARTBEAT_INTERVAL`, `RECONCILE_INTERVAL`,
`COMMAND_POLL_INTERVAL`, `RESTART_LIMIT`, `HEALTH_HOST`, `HEALTH_PORT`,
`BOT_TOKEN_ENCRYPTION_KEY`, `SENTRY_DSN`.

`BOT_TOKEN_ENCRYPTION_KEY` должен совпадать с ключом backend: Runtime
расшифровывает `bots.token_encrypted`. Пустой ключ означает встроенный
dev-ключ — **не использовать в production**.

## Масштабирование

- Несколько воркеров запускаются с разными `WORKER_ID`; боты распределяются
  advisory lock'ами и `desired_state`.
- `list_running_bots` возвращает всех, capacity ограничивает локально.
- Для 1000+ ботов планируется шардирование Gateway (P2); текущая схема
  допускает несколько процессов, но не гарантирует равномерность.
- Graceful shutdown: SIGTERM → listener/scheduler останавливаются → все боты
  останавливаются, locks освобождаются. `stop_grace_period` в compose — 20 секунд.
