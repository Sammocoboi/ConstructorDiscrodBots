# Backend ↔ Runtime contract v2

**Статус:** draft, зафиксирован Артёмом для Шухрата и Сани.
**Дата:** 26.10.2026.
**Источник истины:** Django-модели и миграции в `backend/apps/bots/models.py`.
**Связанные документы:** `docs/real-discord-launch.md`, `runtime/docs/runtime-protocol.md`.

Этот документ заменяет описание схемы из `runtime/docs/runtime-protocol.md` в
той части, где Runtime и backend используют одну PostgreSQL. Пока Шухрат не
подтвердит пункты ниже, полноценный запуск на реальном Discord заблокирован.

---

## 1. Главное решение

Одна PostgreSQL, одна схема. Django-модели — канонические. Runtime читает и
пишет те же таблицы, которые создают Django-миграции.

Из этого следуют три обязательных правила:

1. Runtime **не должен** выполнять `runtime/infra/migrations/001_runtime.sql` на
   базе backend: этот файл создаёт другие таблицы (`bots`, `bot_versions`,
   `runtime_commands`, ...), которые конфликтуют с Django.
2. Runtime использует Django-имена таблиц: `bots_bot`, `bots_botversion`,
   `bots_runtimecommand`, `bots_botruntimestate`, `bots_botguild`,
   `bots_botdraft`, `bots_scheduledjob`.
3. Если Runtime нужны свои служебные таблицы (`templates`, `flow_traces`,
   cron-задачи), они создаются отдельной миграцией Runtime с префиксом
   `runtime_` или в отдельной схеме, чтобы не пересекаться с Django.

---

## 2. Таблицы

### 2.1. `bots_bot` (Runtime: `bots`)

| Django-колонка | Runtime v1 | Комментарий |
|---|---|---|
| `id` uuid PK | `id` | совпадает |
| `owner_id` uuid | — | Runtime не нужен |
| `name` | `name` | совпадает |
| `token_encrypted` | `token_encrypted` | формат `v1:...`, см. раздел 4 |
| `desired_state` | `desired_state` | `running` / `stopped` |
| `status` | `status` | `stopped` / `starting` / `online` / `error` / `suspended` |
| `last_error` | `last_error` | совпадает |
| `last_error_at` | `last_error_at` | совпадает |
| `active_version_id` uuid | `active_version_id` | ссылка на `bots_botversion` |
| `profile` jsonb | `config` | **главное расхождение**: `config` больше нет |
| `intents` jsonb | `intents` | совпадает |
| `deleted_at` | `deleted_at` | soft delete |
| `created_at`, `updated_at` | `created_at`, `updated_at` | Runtime обновляет `updated_at` сам |

**Конфигурация для запуска** берётся так:

```sql
COALESCE(
    v.content,
    d.content,
    b.profile,
    '{}'::jsonb
)
```

где:

- `v` — `bots_botversion` по `b.active_version_id` (опубликованная версия);
- `d` — `bots_botdraft` по `d.bot_id = b.id` (черновик, если публикации ещё нет);
- `b.profile` — профиль бота (fallback).

`bots.config` из Runtime v1 удаляется из кода Runtime. Дублировать `config` в
Django не нужно.

### 2.2. `bots_botversion` (Runtime: `bot_versions`)

| Django-колонка | Runtime v1 | Комментарий |
|---|---|---|
| `id` uuid PK | `id` | совпадает |
| `bot_id` uuid | `bot_id` | совпадает |
| `version_number` integer | `number` | переименовать в runtime-запросах |
| `content` jsonb | `config` | переименовать |
| `comment` | `comment` | совпадает |
| `created_by_id` uuid nullable | `created_by` | Runtime обычно пишет `NULL` |
| `published_at` timestamptz | — | дата публикации |
| `created_at`, `updated_at` | `created_at` | Runtime должен передавать оба timestamp |

Отдельного `status` (`draft`/`published`/`archived`) в Django нет. Статус
версии выводится из `bots_bot.active_version_id`:

- `published` — версия, на которую указывает `active_version_id`;
- остальные — архивные/черновые.

Если Runtime нужен явный `status`, его нужно добавлять миграцией Django, а не
создавать параллельную таблицу.

### 2.3. `bots_botdraft`

Django-таблица `bots_botdraft`: `id`, `bot_id` (unique), `content`, `updated_by_id`,
`created_at`, `updated_at`. Runtime читает `content` как fallback.

### 2.4. `bots_runtimecommand` (Runtime: `runtime_commands`)

В Django уже добавлены поля, которых не хватало Runtime:

| Колонка | Тип | Комментарий |
|---|---|---|
| `id` uuid PK | uuid | Runtime генерирует UUID при вставке |
| `bot_id` uuid FK | uuid | ссылка на `bots_bot` |
| `command` | text | `start` / `stop` / `restart` / `reload` |
| `payload` jsonb | jsonb | дополнительные данные команды |
| `status` | text | `pending` / `acked` / `acknowledged` / `done` / `failed` |
| `requested_by_id` uuid nullable | — | FK на пользователя; Runtime пишет `NULL` или UUID |
| `acked_at` | timestamptz | когда Runtime принял команду |
| `finished_at` | timestamptz | когда завершил |
| `processed_at` | timestamptz | legacy-поле backend; можно не использовать |
| `error` | text | текст ошибки |
| `created_at`, `updated_at` | timestamptz | **Runtime должен передавать при INSERT** |

Что сделать в Runtime:

- заменить таблицу `runtime_commands` на `bots_runtimecommand`;
- при INSERT передавать `id`, `created_at`, `updated_at` (в Django нет
  DB-default для этих колонок);
- `mark_command` писать `status='acked'`/`'done'`/`'failed'` и обновлять
  `acked_at`/`finished_at`;
- `requested_by` заменить на `requested_by_id` и передавать `NULL`, если это
  системная команда;
- либо добавить в Django-миграцию trigger `pg_notify` на
  `bots_runtimecommand`, либо оставить polling Runtime (30 секунд). Сейчас
  Django-таблица триггера не имеет.

### 2.5. `bots_botruntimestate` (Runtime: `bot_runtime_state`)

В Django уже добавлены `started_at` и `last_error`. Осталось:

| Django-колонка | Комментарий |
|---|---|
| `id` uuid PK | **Runtime должен генерировать UUID при INSERT** |
| `bot_id` uuid unique | один state на бота |
| `worker_id` | совпадает |
| `status` | совпадает |
| `latency_ms` | в Django nullable, Runtime пишет 0 |
| `guild_count` | Runtime должен обновлять |
| `uptime_seconds` | совпадает |
| `version_number` | Runtime должен обновлять |
| `heartbeat_at` | совпадает |
| `started_at` | добавлено в Django |
| `last_error` | добавлено в Django |
| `created_at`, `updated_at` | **Runtime должен передавать при INSERT** |

`ON CONFLICT (bot_id)` в Runtime сохраняется. При вставке нужен `id`:
`gen_random_uuid()` на стороне PostgreSQL или UUID, сгенерированный в Runtime.

### 2.6. `bots_scheduledjob`

Это **не** cron-таблица Runtime. Django-модель `ScheduledJob` — пользовательские
отложенные задачи конкретного бота: `bot_id`, `guild_id`, `flow_id`, `run_at`,
`cron`, `payload`, `status`.

Cron-задачи Runtime (`cleanup-runtime-commands`, `cleanup-flow-traces`,
`reset-usage-counters`) должны жить в отдельной таблице, например
`runtime_scheduled_jobs`, или в отдельной схеме. Нельзя использовать
`bots_scheduledjob` для глобальных задач Runtime.

### 2.7. Runtime-only таблицы

`templates`, `flow_traces` в Django-схеме отсутствуют. Их можно оставить
Runtime-only, но:

- имена не должны конфликтовать с будущими Django-таблицами;
- миграция Runtime не должна повторно создавать `bots*`/`scheduled_jobs`;
- лучше вынести их в `runtime_`-префикс или отдельную schema.

---

## 3. API-контракт, который уже готов в backend

Все пути ниже — от `/api/v1`.

### 3.1. OAuth

- `GET /auth/discord` и `GET /auth/discord/login` — редирект на Discord.
  Параметр `next` принимается только как относительный путь (`/app/...`).
- Discord redirect URI остаётся backend-callback:
  `DISCORD_REDIRECT_URI=http://localhost:8000/api/v1/auth/discord/callback`.
- Backend callback редиректит на frontend:
  `${FRONTEND_URL}/auth/callback/discord?code=<one-time-code>&next=<safe-next>`.
- `POST /auth/discord/exchange` с `{"code": "..."}` возвращает
  `{"access": "...", "access_token": "...", "user": {...}}` и ставит
  refresh-cookie.
- `POST /auth/login`, `POST /auth/register`, `POST /auth/refresh` также
  возвращают и `access`, и `access_token`. Регистрация сразу создаёт сессию.
- Frontend должен вызвать exchange на странице callback; `next` использовать
  для возврата пользователя.

### 3.2. Токен бота

`POST /bots/validate-token/` (нужен trailing slash):

```json
{"token": "<discord bot token>"}
```

Успех `200`:

```json
{
  "valid": true,
  "username": "My Bot",
  "applicationId": "123456789012345678",
  "avatarColor": "#5865f2",
  "guildsCount": 3
}
```

Ошибка `400`:

```json
{"valid": false, "detail": "Discord rejected the bot token"}
```

`POST /bots/{id}/token/` — только владелец бота. Тело то же. Возвращает
`BotSerializer` без plaintext-токена; при запущенном боте ставит в очередь
`reload`.

### 3.3. Синхронизация гильдий

`POST /bots/{id}/guilds/sync` — внутренний endpoint для Runtime.

Заголовок:

```text
X-Runtime-Token: <RUNTIME_SERVICE_TOKEN>
```

Тело:

```json
{"guilds": [{"id": "123", "name": "My Server"}]}
```

Поведение: upsert в `bots_botguild`; гильдии, которых нет в новом списке,
получают `left_at`. Ответ: `{"synced": 1}`. Если `RUNTIME_SERVICE_TOKEN` не
задан или не совпал — `403`.

Альтернатива: Runtime пишет `bots_botguild` напрямую. HTTP-вариант предпочтительнее,
потому что backend остаётся владельцем инвариантов.

### 3.4. Trailing slash

Все DRF-router endpoints (`/bots/...`) требуют завершающий `/`. Frontend сейчас
вызывает `/bots`, `/bots/{id}/validate-token` и т.п. без слэша. Это нужно
исправить в `frontend/src/shared/api/httpApi.ts` (зона Данилы), иначе POST
получает 301 и теряет тело. Auth endpoints (`/auth/login` и т.д.) слэш не
требуют.

---

## 4. Шифрование токенов

Единый формат:

```text
v1:<urlsafe-base64(nonce[12] + AES-256-GCM ciphertext + tag)>
```

- Ключ: `TOKEN_ENCRYPTION_KEY`, urlsafe base64, ровно 32 байта.
- Backend: `backend/apps/common/crypto.py`.
- Runtime: `runtime/runtime/crypto.py`.

Что должен сделать Runtime:

1. Читать `TOKEN_ENCRYPTION_KEY` (переименовать `BOT_TOKEN_ENCRYPTION_KEY`).
2. Использовать `base64.urlsafe_b64decode`, а не `base64.b64decode`.
3. Обязательно снимать префикс `v1:` перед base64-decode.
4. Не делать fallback «считать строку plaintext-токеном». При ошибке
   расшифровки — ошибка `invalid_token`/статус `error`, без отправки мусора в
   Discord.
5. Использовать тот же ключ, что backend. Если ключ не задан в production —
   backend падает с `ValueError`, Runtime должен вести себя так же.

Проверка: backend шифрует токен → Runtime расшифровывает → Discord
`GET /users/@me` отвечает `200`.

---

## 5. Environment

Backend (`.env`):

```dotenv
TOKEN_ENCRYPTION_KEY=<urlsafe base64, 32 bytes>
RUNTIME_SERVICE_TOKEN=<random shared secret>
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
DISCORD_REDIRECT_URI=http://localhost:8000/api/v1/auth/discord/callback
FRONTEND_URL=http://localhost:5173
```

Runtime (`.env`):

```dotenv
DATABASE_URL=postgresql://.../one_database_for_backend_and_runtime
TOKEN_ENCRYPTION_KEY=<same value as backend>
RUNTIME_SERVICE_TOKEN=<same value as backend>
BACKEND_URL=http://backend:8000
```

`RUNTIME_SERVICE_TOKEN` и `TOKEN_ENCRYPTION_KEY` — секреты, не коммитить.

---

## 6. Что осталось за Шухратом

- [ ] Перевести SQL Runtime на Django-имена таблиц (см. раздел 2).
- [ ] Убрать `bots.config`, `bot_versions.number/status/config` из запросов.
- [ ] Добавить `id`/`created_at`/`updated_at` при INSERT в
      `bots_runtimecommand` и `bots_botruntimestate`.
- [ ] Перевести `mark_command` на `acked`/`done`/`failed` и
      `acked_at`/`finished_at`.
- [ ] Заменить `requested_by` на `requested_by_id`.
- [ ] Обновлять `guild_count`/`version_number` в `bots_botruntimestate`.
- [ ] Вынести cron Runtime из `scheduled_jobs` в отдельную таблицу.
- [ ] Отключить/переписать `ensure_schema` и `001_runtime.sql` для общей БД.
- [ ] Перейти на `TOKEN_ENCRYPTION_KEY` + `v1:` + urlsafe base64.
- [ ] Добавить `X-Runtime-Token` при вызове `/bots/{id}/guilds/sync`.
- [ ] Добавить тест: старт реального бота → статус `online`.

## 7. Что осталось за Данилой

- [ ] Trailing slash во всех `/bots/...` запросах.
- [ ] Callback-страница: вызвать `/auth/discord/exchange`, сохранить
      `access_token`, обработать `next`/`error`.
- [ ] Адаптер snake_case ↔ camelCase для `Bot`, `Guild`, `Flow`, `Message`,
      `Event`.
- [ ] Либо скрыть экраны `/flows`, `/messages`, `/events`, либо дождаться
      backend-эндпоинтов (это следующий этап, не входит в текущий backend-slice).

## 8. Что уже проверено

- `python -m pytest -q` в `backend` — все тесты зелёные.
- `python manage.py check` — ошибок нет.
- `python manage.py makemigrations --check --dry-run` — изменений нет.
- `ruff check .` — чисто.
- Покрыты тестами: OAuth state/next/callback, exchange, register auto-login,
  validate-token, token replacement, IDOR, guild sync + shared secret.
