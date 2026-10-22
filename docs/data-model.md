# Модель данных

Схема соответствует `backend/apps/*/models.py` и миграциям. Все основные таблицы
имеют UUIDv7-первичный ключ, `created_at` и `updated_at`; пользователи, боты, гильдии,
шаблоны, модули и команды поддерживают мягкое удаление (`deleted_at`).

> Имена таблиц ниже — логические. Django добавляет префикс приложения
> (`accounts_user`, `bots_bot`, `billing_plan`, `common_idempotencykey` и т.д.).

## 1. Аккаунты (`accounts`)

| Таблица | Поля (ключевые) | Связи |
|---|---|---|
| `users` | email (unique), display_name, avatar_url, locale, timezone, is_active, is_staff, email_verified_at, deleted_at | — |
| `oauth_accounts` | provider, provider_user_id, access_token_encrypted, refresh_token_encrypted, scopes, expires_at | user → users, unique(provider, provider_user_id) |
| `refresh_sessions` | jti (unique), token_hash, device_info, ip, expires_at, revoked_at | user → users |

Пароли — Argon2. OAuth-токены и токены ботов шифруются AES-256-GCM.
Refresh-сессии хранят только SHA-256 хеш токена.

## 2. Боты (`bots`)

| Таблица | Поля | Связи |
|---|---|---|
| `bots` | name, discord_application_id, discord_bot_user_id, token_encrypted, status, desired_state, profile, intents, last_error, last_error_at, deleted_at | owner → users, active_version → bot_versions |
| `bot_members` | role (owner/editor/viewer) | bot, user (unique) |
| `bot_guilds` | guild_id, guild_name, joined_at, left_at, settings, enabled_modules | bot (unique bot+guild_id) |
| `bot_drafts` | content (JSONB) | bot (one-to-one), updated_by |
| `bot_versions` | version_number, content, comment, published_at | bot (unique bot+version_number), created_by |
| `bot_variables` | scope, guild_id, user_discord_id, key, value | bot (unique по области и ключу) |
| `runtime_commands` | command (start/stop/restart/reload), status, processed_at, error | bot, requested_by |
| `bot_runtime_state` | worker_id, status, latency_ms, guild_count, uptime_seconds, version_number, heartbeat_at | bot (one-to-one) |
| `scheduled_jobs` | guild_id, flow_id, run_at, cron, payload, status | bot |

Конфигурация бота — JSONB с `schema_version` (см. `docs/architecture.md`, ADR-0004).
Лимит документа — 2 МБ.

## 3. Контент

| Таблица | Поля | Примечание |
|---|---|---|
| `templates` | title, description, category, visibility, is_system, author, popularity, deleted_at | системные и пользовательские |
| `template_versions` | version (semver), content | история шаблона |
| `modules` | slug, title, description, permissions, intents, settings_schema, is_premium, min_plan, deleted_at | манифест модуля |
| `commands_library` | slug, title, category, type, description, parameters, permissions, dependencies, popularity | карточки библиотеки |

## 4. Биллинг (`billing`)

| Таблица | Поля | Примечание |
|---|---|---|
| `plans` | code (free/pro/business, unique), name, price_monthly, currency, stripe_price_id, limits (JSONB), is_active | лимиты: `bots`, `guilds_per_bot`, `executions_per_month`, `api_calls_per_month` |
| `subscriptions` | status (trialing/active/past_due/canceled/expired), external_id, current_period_start/end, cancel_at_period_end, trial_end | user → users, plan → plans |
| `payments` | amount, currency, status, external_id (unique), payload, paid_at | user, subscription |
| `invoices` | number (unique), amount, currency, status, external_id, issued_at, paid_at, pdf_url | user, subscription |
| `usage_counters` | period_start, period_end, executions, api_calls | user, bot (nullable) |

Идемпотентность Stripe — уникальные `external_id` + `get_or_create`; клиентская
идемпотентность — таблица `idempotency_keys` (TTL 24 часа).

## 5. Служебные

| Таблица | Поля | Примечание |
|---|---|---|
| `notifications` | type, payload, read_at | user |
| `audit_logs` | action, object_type, object_id, ip, user_agent, diff | actor (nullable) |
| `idempotency_keys` | key, request_method, request_path, request_hash, response_status, response_body, expires_at | user; unique(user, key) |
| `platform_settings` | singleton_id=1, site_name, support_email, maintenance_mode, registration_enabled, trial_days | singleton для Django Admin |

## 6. Инварианты

- Один пользователь не видит чужих ботов, гильдий, версий, сессий, счетов и уведомлений.
- Один бот — один активный Gateway-воркер (advisory lock в Runtime).
- До 30 версий конфигурации на бота (проверка в сервисе версий).
- `bots.desired_state` — намерение пользователя; `bot_runtime_state.status` — факт.
- `heartbeat_at` старше 60 секунд считается потерей соединения.
- Лимиты тарифа проверяются до создания бота и перед исполнением сценария.
