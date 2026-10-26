# Запуск проекта на реальном Discord

План вывода объединённого проекта из `main` на настоящий Discord: от тестового
сервера до production-стенда.

**Статус:** план согласования и работ, не инструкция «нажать одну кнопку».
**Участники:** Артём (Samoilov, backend-core), Саня (Discord integrations),
Шухрат (Runtime и инфраструктура), Данила (frontend).
**Ориентир по срокам:** 3–5 рабочих дней на команду.

---

## 1. Главное

После слияния веток в `main` весь код находится в одном месте, но проект **ещё
не готов к запуску на реальном Discord**. Причина — не в деплое, а в
рассинхроне контрактов между зонами:

- backend и Runtime по-разному видят схему PostgreSQL;
- backend и Runtime шифруют токены по-разному;
- frontend ожидает API, которых backend пока не отдаёт;
- OAuth-пути frontend и backend не совпадают;
- нет единого production-стека (backend, frontend, Runtime, PostgreSQL);
- нет синхронизации гильдий.

Поэтому сначала — короткий интеграционный этап, затем сборка стенда и только
потом — реальные токены и пользователи.

---

## 2. Что мешает прямо сейчас

| Блокер | Где проявляется | Кто закрывает |
|---|---|---|
| Рассинхрон схемы БД | `runtime/runtime/db.py` vs `backend/apps/bots/models.py` | Артём + Шухрат |
| Рассинхрон шифрования токенов | `backend/apps/common/crypto.py`, `runtime/runtime/crypto.py` | Артём + Шухрат |
| OAuth-пути не совпадают | `frontend/src/...`, `backend/apps/accounts/` | Артём + Саня + Данила |
| Frontend ждёт несуществующие API | `frontend/src/shared/api/httpApi.ts` | Артём + Данила |
| Нет синхронизации гильдий | backend + Runtime | Саня + Артём |
| Нет единого production-стека | `docker-compose.yml`, `runtime/infra/docker-compose.yml` | Шухрат |
| Включён mock-режим frontend | `frontend/.env.example` | Данила |

### 2.1. Схема БД

Runtime ожидает колонки и таблицы, которых нет в Django-схеме:

- `bots.config` — в Django-модели `Bot` такого поля нет;
- `bot_versions.number`, `bot_versions.status`, `bot_versions.config` — в Django
  используются `version_number`, `published_at`, `content`;
- `runtime_commands.payload`, `acked_at`, `finished_at`, статусы `acked`/`done` —
  в Django есть `processed_at`, `error`, статусы `pending`/`acknowledged`/`failed`;
- `bot_runtime_state` — Runtime вставляет строку без `id`, а Django требует
  непустой UUID PK; также расходятся `started_at`, `last_error`, `guild_count`,
  `version_number`;
- `scheduled_jobs` — у Runtime и Django разные наборы полей и назначение.

Пока это не сведено, Runtime не сможет прочитать бота из Django-БД, а значит не
запустит ни одного реального бота.

### 2.2. Шифрование токенов

- Backend: `TOKEN_ENCRYPTION_KEY` (urlsafe base64, 32 байта), формат
  `v1:<base64(nonce + ciphertext)>`; если ключ не задан — ключ выводится из
  `SECRET_KEY`.
- Runtime: `BOT_TOKEN_ENCRYPTION_KEY`, ожидает обычный base64 **без** префикса
  `v1:`; при ошибке расшифровки молча считает строку plaintext-токеном.

Даже если положить один и тот же ключ, префикс `v1:` сломает расшифровку.
Нужен единый формат и единое имя переменной.

### 2.3. OAuth

- Frontend открывает `/api/v1/auth/discord`, backend отдаёт только
  `/api/v1/auth/discord/login`.
- Backend редиректит на `${FRONTEND_URL}/auth/callback`, а frontend-роут —
  `/auth/callback/discord`.
- Страница callback не обменивает `code` через `/auth/discord/exchange`, а
  сразу вызывает `/auth/me`.

### 2.4. Недостающие API frontend

`frontend/src/shared/api/httpApi.ts` ожидает, среди прочего:

- `POST /bots/validate-token`;
- `POST /bots/{id}/token`;
- `GET/POST/PUT/DELETE /bots/{id}/flows`, publish/rollback/validate/test;
- `GET /bots/{id}/events`;
- `GET/PUT/POST /messages`;
- `POST /bots/{id}/save-as-template`.

В backend этих маршрутов нет. Нужно либо реализовать их, либо явно урезать MVP
и скрыть соответствующие экраны.

### 2.5. Инфраструктура

- Корневой `docker-compose.yml` поднимает только `db` + `backend`, причём с
  `DJANGO_SETTINGS_MODULE=config.settings.dev` и `runserver`.
- `runtime/infra/docker-compose.yml` поднимает **свою** PostgreSQL и Runtime,
  то есть backend и Runtime не используют одну БД.
- У frontend нет Dockerfile/nginx-конфига для production.
- Наружу нельзя публиковать PostgreSQL и Runtime health-порт без защиты.

---

## 3. Целевая архитектура

```text
Браузер
  │ HTTPS
  ▼
nginx / Caddy (frontend + reverse proxy)
  ├── /              → статика React (dist)
  └── /api           → backend (gunicorn, Django)
                          │
                          ▼
                     PostgreSQL
                          ▲
                          │
                     Runtime (Discord Gateway)
                          │
                          ▼
                       Discord
```

Требования:

- один PostgreSQL для backend и Runtime;
- один `docker-compose.prod.yml` на весь стек;
- наружу открыты только 80/443;
- PostgreSQL и Runtime-порт 8080 — только во внутренней сети;
- HTTPS-сертификаты (Let's Encrypt);
- бэкапы БД и мониторинг;
- отдельные Discord-приложения для staging и production.

---

## 4. Этап 0. Общее: Discord-приложение и тестовый сервер

Выполняется один раз, лучше всей командой. Занимает 30–60 минут.

### 4.1. Приложение платформы (для входа через Discord)

1. Открыть [Discord Developer Portal](https://discord.com/developers/applications).
2. Создать приложение `Constructor / BotForge`.
3. `OAuth2 → Redirects`:
   - `http://localhost:8000/api/v1/auth/discord/callback`
   - `https://api.<домен>/api/v1/auth/discord/callback`
4. `OAuth2 → Scopes`: `identify`, `email`, `guilds`.
5. Сохранить `Application ID` и `Client Secret`.

### 4.2. Тестовый бот

1. В приложении: `Bot → Add Bot`.
2. `Reset Token` и сохранить токен в менеджер паролей.
3. Включить **Privileged Gateway Intents**:
   - `Server Members Intent` — welcome, роли, уровни;
   - `Message Content Intent` — prefix-команды, antispam, уровни.
4. Создать тестовый Discord-сервер.
5. Пригласить бота со scopes `bot applications.commands` и правами:
   - базовые: View Channels, Send Messages, Embed Links,
     Read Message History, Use Application Commands;
   - по модулям: Manage Roles, Manage Channels, Manage Messages,
     Moderate Members, Ban/Kick Members.

### 4.3. Правила работы с секретами

- Секреты — только в менеджере паролей и в `.env` на сервере.
- Не коммитить `.env`, токены, `Client Secret`.
- Не переиспользовать production-токены на staging.
- `DISCORD_BOT_TOKEN` из `.env.example` сейчас не используется: платформа
  работает с токенами пользовательских ботов. Переменную можно удалить.

### 4.4. Быстрая проверка токена

```bash
curl -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  https://discord.com/api/v10/users/@me
```

Ожидается JSON с `id`, `username`, `bot: true`.

---

## 5. План по участникам

### 5.1. Артём (Samoilov) — backend-core и контракт

**Задача:** сделать backend источником истины по БД и API, чтобы Runtime и
frontend могли с ним работать.

#### Задачи

**Статус на 26.10.2026 (Артём):** backend-slice готов и покрыт тестами:
OAuth-алиас/callback/exchange, `access_token`, `validate-token`, замена токена,
внутренний guild-sync, поля `runtime_commands`/`bot_runtime_state`, env и
`docs/runtime-protocol.md`. Полный запуск всё ещё ждёт правок Runtime
(Шухрат) и frontend (Данила).

- [ ] Провести созвон с Шухратом и Саней, зафиксировать контракт БД v2 и
      записать его в `docs/runtime-protocol.md`.
      > Черновик контракта уже создан: `docs/runtime-protocol.md`. Нужно
      > подтверждение Шухрата по таблицам/колонкам.
- [ ] Свести схему БД к одному виду. Рекомендуемый вариант: Django-схема —
      главная, Runtime подстраивается.
      > В backend добавлены `runtime_commands.payload`, `acked_at`,
      > `finished_at`, статусы `acked`/`done`, а также
      > `bot_runtime_state.started_at`/`last_error`. Остальное (имена таблиц,
      > `bot_versions`, `bots.config`, timestamps) — за Runtime.
      - `bot_versions`: использовать `version_number`, `content`,
        `published_at` (либо добавить `status`/`config` миграцией, но без дублей).
      - `bots`: убрать зависимость Runtime от несуществующего `bots.config`;
        fallback — `BotDraft.content` или `active_version.content`.
      - `runtime_commands`: согласовать `payload`, `acked_at`, `finished_at` и
        статусы `acked`/`done` vs `acknowledged`/`processed_at`.
      - `bot_runtime_state`: согласовать PK, `started_at`, `last_error`,
        `guild_count`, `version_number`.
      - `scheduled_jobs`: развести runtime-джобы и пользовательские задачи либо
        привести к одной таблице.
- [ ] Унифицировать шифрование токенов:
      > Backend-сторона готова: `TOKEN_ENCRYPTION_KEY` добавлен в
      > `.env.example`, формат `v1:` описан в `docs/runtime-protocol.md`.
      > Осталось переименовать env и поддержать `v1:` в Runtime.
      - один env `TOKEN_ENCRYPTION_KEY` (urlsafe base64, 32 байта) для backend
        и Runtime;
      - Runtime должен понимать префикс `v1:`;
      - убрать fallback «считать токен plaintext»;
      - добавить тест: backend зашифровал → Runtime расшифровал → Discord принял.
- [x] Починить OAuth-контракт:
      - `GET /api/v1/auth/discord/login` (или алиас `/auth/discord`);
      - callback → `FRONTEND_URL/auth/callback/discord?code=...`;
      - frontend обменивает `code` через `/auth/discord/exchange`;
      - `next`-параметр либо поддержать, либо убрать.
      > Backend готов; страницу callback и обмен `code` должен доделать
      > frontend (Данила).
- [ ] Добавить недостающие эндпоинты:
      - `POST /bots/validate-token`;
      - `POST /bots/{id}/token` — обновление токена;
      - `POST /bots/{id}/flows`, `PUT/DELETE`, `POST /flows/{id}/publish`,
        `rollback`;
      - `GET /bots/{id}/events`;
      - `/messages`;
      - `POST /bots/{id}/save-as-template`.
      > `validate-token` и `token` готовы. Flows/events/messages/templates —
      > следующий этап, требуют моделей и согласования с frontend.
- [ ] Добавить синхронизацию гильдий: Runtime или backend делает upsert в
      `bot_guilds` при join/leave; отдавать это в `/bots/{id}/guilds`.
      > Backend endpoint готов: `POST /bots/{id}/guilds/sync` с
      > `X-Runtime-Token`. Runtime должен его вызывать.
- [ ] Проверить production-настройки: `config.settings.prod`, `ALLOWED_HOSTS`,
      CORS/CSRF, cookies, статика, миграции.
- [x] Обновить `.env.example`, API-контракт и тесты.

#### Готово, когда

Backend поднимается с `config.settings.prod`, реальный Discord-токен
сохраняется, Runtime его расшифровывает, бот стартует и получает статус
`online`.

---

### 5.2. Саня — Discord integrations

**Задача:** чтобы реальный Discord API работал без сюрпризов.

#### Задачи

- [ ] Настроить приложение в Discord Developer Portal по этапу 0; передать
      Артёму и Шухрату ID/secret по защищённому каналу.
- [ ] Проверить OAuth на реальном Discord: вход → список серверов пользователя
      (`/me/discord-guilds`) → выход.
- [ ] Проверить `POST /bots` с реальным токеном: backend вызывает
      `GET /users/@me`, сохраняет `discord_bot_user_id`, отдаёт `has_token`.
- [ ] Реализовать/проверить invite-URL:
      - scopes `bot applications.commands`;
      - permissions integer по включённым модулям;
      - `guild_id` и `disable_guild_select` при необходимости.
- [ ] Проверить intents и права:
      - join-событие, welcome;
      - slash-команды;
      - Manage Roles, Manage Channels;
      - ошибки `MissingIntentsError` и `401` должны доходить до UI.
- [ ] Добавить обработку:
      - `429` с `Retry-After`;
      - `401` — остановка бота и уведомление;
      - `403` — понятный текст пользователю.
- [ ] Синхронизация гильдий: по gateway-событиям `on_guild_join` /
      `on_guild_remove` писать в `bot_guilds` (или отдавать события в backend).
- [ ] Прогнать ручной smoke-тест на тестовом сервере и записать результаты в
      `docs/`.
- [ ] Учесть ограничения Discord:
      - верификация бота при >100 серверах;
      - Message Content Intent;
      - rate limits.

#### Готово, когда

Пользователь входит через реальный Discord, создаёт бота с реальным токеном,
приглашает на тестовый сервер, и бот отвечает на `/ping`.

---

### 5.3. Шухрат — Runtime и инфраструктура

**Задача:** один воспроизводимый production-стек, а не набор разрозненных
compose-файлов.

#### Задачи

- [ ] Адаптировать SQL-запросы Runtime под финальную схему БД (решение
      зафиксировать с Артёмом).
- [ ] Исправить расшифровку токенов: общий ключ, поддержка `v1:`, убрать
      plaintext-fallback.
- [ ] Сделать единый `docker-compose.prod.yml`:
      - `postgres`;
      - `backend` (gunicorn + `config.settings.prod`);
      - `runtime`;
      - `frontend` (nginx);
      - `migrate` (Django migrate + runtime SQL строго до старта);
      - опционально Sentry/Prometheus.
- [ ] Убрать отдельную БД у Runtime; один PostgreSQL для backend и Runtime.
- [ ] Закрыть наружу лишнее:
      - только 80/443;
      - PostgreSQL и 8080 Runtime — только внутренняя сеть.
- [ ] TLS: Caddy/Nginx + Let's Encrypt; домены `app.<домен>` и `api.<домен>`.
- [ ] Healthchecks, `restart: unless-stopped`, `stop_grace_period`, логи,
      Sentry, `/health`, `/ready`, `/metrics`.
- [ ] Бэкапы PostgreSQL (`pg_dump`, cron, проверка restore), обновление и
      rollback.
- [ ] Provision VPS (минимум 2 vCPU / 4 ГБ RAM), DNS, firewall, отдельный
      пользователь деплоя.
- [ ] Проверить lifecycle:
      - start → online;
      - restart → stop;
      - падение токена;
      - missing intents;
      - перезагрузка сервера.

#### Готово, когда

`docker compose -f docker-compose.prod.yml up -d` на чистой машине поднимает
весь стек, а тестовый бот стабильно онлайн после перезапуска контейнеров и
сервера.

---

### 5.4. Данила — Frontend

**Задача:** убрать mock-режим и довести UI до реального API.

#### Задачи

- [ ] Production-конфиг:
      - `VITE_USE_MOCKS=false`;
      - `VITE_API_URL=/api/v1`;
      - `VITE_ADMIN_URL=https://api.<домен>/admin/`.
- [ ] Убрать демо-доступ и mock-only заглушки из production-сборки.
- [ ] Свести пути API с backend (или попросить Артёма добавить алиасы):
      - OAuth callback: принять `code`, вызвать `/auth/discord/exchange`,
        сохранить сессию, обработать `error`;
      - `/auth/discord` vs `/auth/discord/login`;
      - `/bots/validate-token`, `/token`, `/flows`, `/messages`, `/events`.
- [ ] Проверить реальные сценарии:
      - вход через Discord;
      - создание бота с токеном;
      - список гильдий;
      - invite;
      - модули и команды;
      - редактор flow;
      - публикация;
      - start/stop/status.
- [ ] Сделать Dockerfile (multi-stage build) + nginx-конфиг с SPA-fallback и
      проксированием `/api`.
- [ ] Настроить корректную работу с refresh-cookie и ошибками 401/403/429.
- [ ] Прогнать E2E против реального backend и тестового Discord-сервера;
      проверить production-сборку.
- [ ] Скрыть или пометить функции, которых ещё нет в backend, чтобы не
      обещать пользователю нерабочий UI.

#### Готово, когда

Production-сборка открывается по HTTPS, входит через реальный Discord и
полностью проводит сценарий «создать бота → пригласить → опубликовать →
запустить → увидеть online».

---

## 6. Порядок работ

| День | Что делаем |
|---|---|
| 1 | Этап 0: Discord-приложение, тестовый сервер, секреты. Созвон по контракту БД. Артём + Шухрат начинают схему и шифрование. |
| 2 | Артём: OAuth + недостающие эндпоинты. Шухрат: единый compose и Runtime SQL. Саня: реальный OAuth/токен/гильдии. |
| 3 | Данила: реальный API + Docker/nginx. Совместная сборка стека на VPS/staging. |
| 4 | Smoke-тест на реальном Discord, исправление ошибок, бэкапы/мониторинг. |
| 5 | Финальный прогон, документация, передача доступов, запуск. |

### Зависимости

1. Сначала фиксируется контракт БД и шифрования (Артём + Шухрат).
2. Параллельно Саня настраивает реальное Discord-приложение и проверяет API.
3. После контракта Данила переводит frontend на реальные эндпоинты.
4. Шухрат собирает единый стек, когда готовы backend и Runtime.
5. Финальный smoke-тест — только после сборки всех четырёх зон.

---

## 7. Финальный smoke-тест «настоящий Discord»

1. Новый пользователь входит через Discord OAuth.
2. Создаёт бота, вставляет реальный токен — backend подтверждает его через
   Discord.
3. Получает invite-ссылку и приглашает бота на тестовый сервер.
4. В UI появляется гильдия.
5. Публикует конфигурацию и нажимает «Запустить».
6. В течение ~15 секунд статус `online`, в Runtime-логах — подключение к
   Gateway.
7. `/ping` отвечает, welcome-flow срабатывает на входе участника.
8. Restart и stop работают, heartbeat не просрочен.
9. В логах и репозитории нет токенов; `401`/`429` обрабатываются.
10. После перезагрузки сервера стек и бот поднимаются автоматически.

---

## 8. Безопасность и подводные камни

- Не публиковать наружу PostgreSQL (`5432`) и Runtime (`8080`).
- Не использовать `DJANGO_DEBUG=true`, `runserver` и дефолтные секреты в
  production.
- Один и тот же `TOKEN_ENCRYPTION_KEY` на backend и Runtime, иначе токены не
  расшифруются.
- Токены ботов — только в зашифрованном виде; ротация токена = замена в UI.
- Message Content Intent для верифицированных ботов требует одобрения Discord.
- Для >100 серверов бот должен пройти верификацию Discord — это отдельный
  процесс, не технический деплой.
- Сделать отдельные приложения Discord для staging и production, чтобы не
  смешивать токены и данные.
- Не хранить `.env` и дампы БД в git и в публичных бэкапах.

---

## Приложение A. Пример production-переменных

Корневой `.env`:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=<случайная строка ≥32 символов>
DJANGO_ALLOWED_HOSTS=api.example.com
DATABASE_URL=postgres://constructor:<пароль>@db:5432/constructor

FRONTEND_URL=https://app.example.com
CORS_ALLOWED_ORIGINS=https://app.example.com
CSRF_TRUSTED_ORIGINS=https://app.example.com

DISCORD_CLIENT_ID=<application id>
DISCORD_CLIENT_SECRET=<client secret>
DISCORD_REDIRECT_URI=https://api.example.com/api/v1/auth/discord/callback

TOKEN_ENCRYPTION_KEY=<urlsafe base64, 32 байта>
```

Runtime `.env`:

```dotenv
DATABASE_URL=postgres://constructor:<пароль>@db:5432/constructor
WORKER_ID=runtime-1
MAX_BOTS_PER_WORKER=25
HEARTBEAT_INTERVAL=15
RECONCILE_INTERVAL=10
COMMAND_POLL_INTERVAL=30
RESTART_LIMIT=5
BOT_TOKEN_ENCRYPTION_KEY=<тот же ключ, что TOKEN_ENCRYPTION_KEY>
SENTRY_DSN=
```

Frontend `.env.production`:

```dotenv
VITE_USE_MOCKS=false
VITE_API_URL=/api/v1
VITE_ADMIN_URL=https://api.example.com/admin/
```

Сгенерировать ключ:

```bash
python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

---

## Приложение B. Быстрые проверки

Проверка токена Discord:

```bash
curl -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  https://discord.com/api/v10/users/@me
```

Проверка backend:

```bash
curl -f https://api.example.com/api/v1/health
```

Проверка Runtime:

```bash
curl -f http://127.0.0.1:8080/health
curl -f http://127.0.0.1:8080/ready
```

Проверка миграций:

```bash
docker compose -f docker-compose.prod.yml run --rm backend \
  python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml run --rm backend \
  python manage.py check --deploy
```
