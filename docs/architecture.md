# Архитектура

## 1. Компоненты

```
┌──────────────┐     HTTPS/JSON      ┌─────────────────────┐
│  React SPA   │ ──────────────────► │  Django + DRF API   │
│  (Vite, TS)  │ ◄────────────────── │  /api/v1/           │
└──────────────┘   access/refresh    └──────┬──────────────┘
                                             │ ORM
                                      ┌──────▼──────────────┐
                                      │    PostgreSQL       │
                                      │  + LISTEN/NOTIFY    │
                                      └──────┬──────────────┘
                                             │ runtime_commands
                                      ┌──────▼──────────────┐
                                      │  Runtime service    │
                                      │ supervisor + workers│
                                      └──────┬──────────────┘
                                             │ Gateway/HTTP
                                      ┌──────▼──────────────┐
                                      │    Discord API      │
                                      └─────────────────────┘
```

- **Backend** (`backend/`) — Django 5 + DRF: аккаунты, боты, модули, команды, шаблоны, биллинг, уведомления, аудит. Владелец контрактов и модели данных.
- **Runtime** (`runtime/`, отдельный сервис) — supervisor, пул воркеров, Gateway-соединения, интерпретатор сценариев. Не импортирует Django-модели, общается через PostgreSQL (`runtime_commands`, `bot_runtime_state`) и LISTEN/NOTIFY.
- **Frontend** (`frontend/`) — React 18 + TypeScript: дашборд, мастер бота, редактор графа и эмбедов, кабинеты.
- **PostgreSQL** — единственный источник правды для конфигурации, состояния и очереди задач.

## 2. Backend-приложения

| Приложение | Ответственность |
|---|---|
| `common` | базовые модели (UUIDv7, soft delete), ошибки, пагинация, middleware, права, идемпотентность |
| `accounts` | пользователи, Discord OAuth, JWT, сессии, профиль, email-токены |
| `bots` | проекты ботов, токены, гильдии, версии, runtime-команды и состояние |
| `templates_catalog` | системные и пользовательские шаблоны, версии |
| `modules` | манифесты модулей |
| `commands` | библиотека Discord-команд |
| `billing` | тарифы, подписки, платежи, счета, usage-счётчики, Stripe |
| `notifications` | in-app уведомления |
| `audit` | журнал действий |

## 3. Поток запуска бота

1. Пользователь создаёт бота, передаёт токен → backend проверяет `GET /users/@me`, шифрует AES-256-GCM.
2. `POST /bots/{id}/start` → `desired_state=running`, `status=starting`, запись в `runtime_commands`.
3. Runtime получает команду (poll/LISTEN), подключается к Gateway, обновляет `bot_runtime_state` (heartbeat каждые 15 секунд).
4. Frontend опрашивает `GET /bots/{id}/status`; при `heartbeat_at` старше 60 секунд бот считается не живым.

## 4. Конфигурация бота

- Черновик (`bot_drafts`) → публикация (`bot_versions`, до 30 версий) → активная версия.
- Формат — JSONB, версия схемы фиксируется в `docs/config-schema.md`.
- Секреты в конфигурации запрещены: токены хранятся только в зашифрованном поле `bots.token_encrypted`.
- Runtime получает конфигурацию через `runtime_commands` с командой `reload` и читает активную версию.

## 5. Аутентификация и безопасность

- JWT access 15 минут, refresh 30 дней с ротацией и хешем в БД, refresh — httpOnly-cookie.
- Discord OAuth state — одноразовый, в кеше, TTL 10 минут; обмен кода на JWT — через одноразовый login-code.
- Object-level доступ: все выборки фильтруются по владельцу; IDOR закрыт на уровне queryset и `IsOwner`.
- Токены ботов и OAuth шифруются (`apps/common/crypto.py`), в API маскируются.
- Stripe webhook — проверка подписи `Stripe-Signature`.
- Ошибки не раскрывают наличие аккаунта (reset/verify).
- Секреты — только через переменные окружения, pre-commit secret scan.

## 6. Очереди и фоновые задачи

- Выбран Procrastinate (PostgreSQL-native, см. ADR-0003).
- Через очередь: email, синхронизация slash-команд, очистка usage/idempotency, шаблонные регрессии.
- Runtime-команды — отдельная таблица, не очередь: нужна строгая последовательность на бота и hot reload через NOTIFY.

## 7. Окружения

| Окружение | Настройки | БД | Назначение |
|---|---|---|---|
| local | `config.settings.dev` | SQLite или PostgreSQL | разработка, тесты |
| staging | `config.settings.prod` | PostgreSQL | приёмка, тестовый Discord-сервер |
| production | `config.settings.prod` | PostgreSQL | демо/защита |

Подробнее — `docs/deployment.md`.
