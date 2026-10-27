# Runtime Protocol v1

Контракт между Django backend и Runtime. Оба сервиса используют **один
PostgreSQL**. Источник истины по схеме — Django migrations; Runtime не создаёт и
не изменяет структуру Django-таблиц (только пишет данные и добавляет служебный
индекс/триггер на таблице команд). Runtime владеет только двумя таблицами.

Порядок применения схемы в production:

```text
python manage.py migrate          # Django: bots_*, templates_catalog_*
psql -f infra/migrations/001_runtime.sql   # Runtime: scheduler/traces + trigger
python -m runtime.main            # Runtime повторно применяет свой SQL (идемпотентно)
```

`001_runtime.sql` можно запускать на свежей БД до Django migrate: создание
триггера и индекса на `bots_runtimecommand` пропускается, если таблицы ещё нет.
После Django migrate скрипт нужно выполнить повторно либо перезапустить Runtime.

## Владение таблицами

| Таблица | Владелец | Назначение |
|---|---|---|
| `bots_bot` | Django | боты, токен, desired/current status, active version |
| `bots_botdraft` | Django | черновик конфигурации (one-to-one с ботом) |
| `bots_botversion` | Django | опубликованные/архивные версии конфигурации |
| `bots_runtimecommand` | Django | очередь команд `start`/`stop`/`restart`/`reload` |
| `bots_botruntimestate` | Django | heartbeat и метрики бота |
| `templates_catalog_template`, `templates_catalog_templateversion` | Django | пользовательские шаблоны |
| `bots_scheduledjob` | Django | пользовательские отложенные flow-задачи |
| `runtime_scheduled_jobs` | Runtime | cron-задачи самого Runtime |
| `runtime_flow_traces` | Runtime | трассировки выполнения flow |

`bots_scheduledjob` и `runtime_scheduled_jobs` — разные сущности. Runtime не
читает и не изменяет пользовательские задачи Django.

## Чтение бота

Runtime читает только ботов с `desired_state = 'running'` и
`deleted_at IS NULL`:

```sql
SELECT b.id, b.name, b.token_encrypted, b.desired_state, b.intents,
       COALESCE(v.content, d.content, '{}'::jsonb) AS config,
       v.version_number
  FROM bots_bot b
  LEFT JOIN bots_botversion v ON v.id = b.active_version_id
  LEFT JOIN bots_botdraft  d ON d.bot_id = b.id;
```

Приоритет конфигурации:

1. `bots_botversion.content` активной версии (`bots_bot.active_version_id`);
2. `bots_botdraft.content`, если активной версии нет;
3. `{}`.

`bots_bot.intents` (JSON-массив) объединяется с `config["intents"]`; значения из
`bots_bot.intents` добавляются без дублей. Отдельного `bots_bot.config` и
отдельного `status` у версии нет: опубликованная версия — та, на которую
указывает `active_version_id`, остальные версии считаются архивными.

### `bots_bot` — используемые поля

| колонка | назначение |
|---|---|
| `id` (uuid) | PK |
| `name` | имя бота |
| `token_encrypted` | токен в формате `v1:...` |
| `desired_state` | `running` / `stopped` |
| `status` | `stopped` / `starting` / `online` / `error` / `suspended` |
| `active_version_id` | активная `bots_botversion` |
| `intents` | JSON-массив intents |
| `last_error`, `last_error_at` | последняя ошибка |
| `deleted_at` | soft delete |

### `bots_runtimecommand` — очередь команд

| колонка | назначение |
|---|---|
| `id` (uuid) | PK |
| `bot_id` | FK на `bots_bot` |
| `command` | `start` / `stop` / `restart` / `reload` |
| `status` | `pending` / `acknowledged` / `failed` |
| `processed_at` | когда команда подтверждена/завершена |
| `error` | текст ошибки (пустая строка при успехе) |
| `requested_by_id` | пользователь, инициировавший команду |
| `created_at`, `updated_at` | служебные |

В Django-схеме нет `payload`, `acked_at` и `finished_at`. Runtime не хранит
payload команды: при необходимости параметры должны передаваться через
отдельные поля/таблицы backend. Внутренние состояния Runtime `acked`/`done`
отображаются в `acknowledged`, `failed` остаётся `failed`:

| Runtime | PostgreSQL |
|---|---|
| `acked` | `acknowledged`, `processed_at = now()` |
| `done` | `acknowledged`, `processed_at = now()` |
| `failed` | `failed`, `processed_at = now()`, `error` |

Из-за этого по таблице нельзя отличить «команда принята» от «команда выполнена».
Для диагностики используйте логи Runtime и `bots_bot.status`.

### `bots_botruntimestate` — heartbeat

| колонка | назначение |
|---|---|
| `id` (uuid) | PK, Runtime генерирует UUID |
| `bot_id` | UNIQUE, one-to-one с ботом |
| `worker_id` | воркер, владеющий ботом |
| `status` | текущий статус бота |
| `latency_ms` | задержка Gateway |
| `guild_count` | число гильдий |
| `uptime_seconds` | uptime текущего подключения |
| `version_number` | версия конфигурации |
| `heartbeat_at` | время последнего heartbeat |
| `created_at`, `updated_at` | служебные |

Полей `started_at` и `last_error` нет: ошибка хранится в `bots_bot.last_error`,
время старта вычисляется по `heartbeat_at`/`uptime_seconds`.

### Шаблоны

Пользовательские шаблоны: `templates_catalog_template` +
`templates_catalog_templateversion` (последняя версия по `created_at`).
Системные шаблоны загружаются из `content/templates/*.json`; в БД они не
дублируются. `slug` хранится внутри `content`, отдельной колонки нет.

### Runtime-owned таблицы

- `runtime_scheduled_jobs` — `id`, `name`, `cron`, `handler`, `payload`,
  `enabled`, `status`, `last_run_at`, `last_started_at`, `next_run_at`,
  `last_error`;
- `runtime_flow_traces` — `id`, `bot_id`, `flow_id`, `status`, `trace`,
  `created_at`.

## Шифрование токенов

Единый контракт backend и Runtime:

- ключ: `TOKEN_ENCRYPTION_KEY`, URL-safe base64 ровно **32 байта** (AES-256);
- формат: `v1:` + URL-safe base64 от `nonce (12 байт) + ciphertext + tag`;
- plaintext-fallback отсутствует;
- неверный формат, неверный ключ или повреждённый ciphertext — постоянная
  ошибка, а не повод отправить строку в Discord.

`TOKEN_ENCRYPTION_KEY` — каноническое имя для обоих сервисов. Runtime также
принимает устаревшее `BOT_TOKEN_ENCRYPTION_KEY` как fallback, чтобы упростить
миграцию существующих установок; backend читает только каноническое имя.
Новые deployment-ы должны задавать `TOKEN_ENCRYPTION_KEY`.

При ошибке расшифровки Runtime:

1. ставит боту `status = 'error'` и `last_error`;
2. переводит `desired_state` в `stopped`;
3. не запускает клиент и не делает авторестарт.

Проверить, что ключи совпадают, можно тестом backend-шифрование → Runtime-
дешифрование; в production ключ должен быть одинаковым в `.env` unified-стека.

## Доставка команд

1. Backend вставляет строку в `bots_runtimecommand` со `status = 'pending'`.
2. Триггер `runtime_command_notify` (функция `runtime_notify_command`)
   выполняет `pg_notify('runtime_commands_channel', NEW.id::text)`. Payload —
   **id команды**, не bot_id.
3. `CommandListener` держит отдельное соединение
   `LISTEN runtime_commands_channel`. NOTIFY только будит воркер; команды
   читаются из таблицы.
4. Runtime захватывает пачку через `FOR UPDATE SKIP LOCKED`, сразу переводит в
   `acknowledged`/`processed_at` и выполняет.
5. Результат: `acknowledged` (успех) или `failed` + `error`.
6. Страховка: polling раз в `COMMAND_POLL_INTERVAL` (по умолчанию 30 секунд).
   Если LISTEN/NOTIFY недоступен, polling продолжает работать.

Триггер и индекс создаются только если `bots_runtimecommand` уже существует.
Проверка:

```sql
SELECT tgname FROM pg_trigger
WHERE tgrelid = 'bots_runtimecommand'::regclass;
```

Ожидается `runtime_command_notify`.

| команда | действие |
|---|---|
| `start` | запустить бота, если `desired_state = 'running'` и он не запущен |
| `stop` | остановить, снять advisory lock, поставить `stopped` |
| `restart` | stop + start |
| `reload` | перечитать бота/активную версию и применить конфиг без рестарта |

`reload` обновляет имя, токен и конфигурацию; если бот не запущен — no-op.
Backend перед `start`/`restart` сам выставляет `desired_state = 'running'`,
перед `stop` — `stopped`.

## Блокировка

`pg_try_advisory_lock(hashtext(bot_id))` на отдельном соединении, которое живёт
всё время работы бота. Один бот — ровно один воркер. Соединение закрывается при
stop/shutdown, lock снимается автоматически. TTL/lease не нужен: сессия
PostgreSQL и есть lease. Второй воркер получает `None` и пропускает бота.

## Heartbeat

- Каждые `HEARTBEAT_INTERVAL` (15 секунд) воркер обновляет
  `bots_botruntimestate`: `heartbeat_at`, `latency_ms`, `uptime_seconds`,
  `guild_count`, `version_number`, `worker_id`.
- Heartbeat пишется для ботов в статусах `starting` и `online`.
- Backend считает состояние живым, если `heartbeat_at` не старше 60 секунд
  (`BotRuntimeState.is_alive`). Runtime сам не меняет статус по таймауту — это
  делает API/оператор.

## Жизненный цикл

```text
stopped -> starting -> online
                 \-> error -> starting (backoff) ... -> suspended
online -> error (gateway lost) -> starting ... -> suspended
```

- Авторестарт: до `RESTART_LIMIT` (5) попыток, backoff `1, 2, 4, 8, 16...`
  секунд, максимум 30.
- Если бот проработал ≥ 60 секунд, счётчик попыток сбрасывается.
- `InvalidTokenError` / `MissingIntentsError` / ошибка расшифровки токена —
  постоянные ошибки: статус `error`, `desired_state = stopped`, рестартов нет.
- При превышении лимита — `suspended` с ошибкой.
- При capacity (`MAX_BOTS_PER_WORKER`) бот получает `suspended` и ждёт
  освобождения места/другого воркера.
- При graceful shutdown боты получают `stopped`, но `desired_state` остаётся
  `running`; после рестарта reconcile поднимает их снова.

## Ошибки

| код/исключение | причина |
|---|---|
| `TokenDecryptionError` | токен не задан, ключ не совпадает, формат не `v1:` |
| `invalid_token` / `InvalidTokenError` | Discord 401 |
| `missing_intents` / `MissingIntentsError` | не включены Privileged Intents |
| `SupervisorCapacityError` | воркер заполнен |
| `FlowExecutionError` | ошибка блока/графа |
| `FlowTimeoutError` | превышены 30 секунд |
| `FlowLimitError` | блоки, глубина или посещения |
| `ValidationError` | невалидный конфиг/шаблон |

## Health и метрики

HTTP-сервер Runtime (по умолчанию `0.0.0.0:8080`, наружу не публикуется):

- `GET /health` — liveness, всегда `200` при живом процессе:
  `{"status":"ok","worker_id":"..."}`;
- `GET /ready` — readiness: `200`, если БД доступна и воркер не остановлен;
  иначе `503` с `{"ready":false,"database":...}`;
- `GET /metrics` — Prometheus-текст:
  `runtime_bots_total{status}`, `runtime_commands_total`,
  `runtime_commands_failed_total`, `runtime_restarts_total`,
  `runtime_uptime_seconds`, `runtime_bot_latency_ms`, `runtime_bot_uptime_seconds`;
- `GET /` — полный snapshot (боты, статусы, capacity, metrics).

Docker healthcheck использует `/health`; readiness проверяется отдельно, чтобы
падение БД не вызывало бесконечный рестарт контейнера.

## Переменные окружения

См. `infra/.env.example` и корневой `.env.production.example`. Ключевые:
`DATABASE_URL`, `WORKER_ID`, `MAX_BOTS_PER_WORKER`, `HEARTBEAT_INTERVAL`,
`RECONCILE_INTERVAL`, `COMMAND_POLL_INTERVAL`, `RESTART_LIMIT`, `HEALTH_HOST`,
`HEALTH_PORT`, `TOKEN_ENCRYPTION_KEY` (legacy: `BOT_TOKEN_ENCRYPTION_KEY`),
`SENTRY_DSN`.

## Масштабирование

- Несколько воркеров запускаются с разными `WORKER_ID`; боты распределяются
  advisory lock'ами и `desired_state`.
- `list_running_bots` возвращает всех, capacity ограничивает локально.
- Для 1000+ ботов планируется шардирование Gateway (P2); текущая схема
  допускает несколько процессов, но не гарантирует равномерность.
- Graceful shutdown: SIGTERM → listener/scheduler останавливаются → все боты
  останавливаются, locks освобождаются. `stop_grace_period` в compose — 20
  секунд.
