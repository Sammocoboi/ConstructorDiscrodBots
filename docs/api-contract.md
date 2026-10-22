# API-контракт Constructor Discord Bots

Версия: 1.0. Контракт действует для всех клиентов: frontend, Runtime, интеграции.
Изменения — только через PR с ревью владельца подсистемы (Артём, `docs/api-contract.md`).

## 1. Базовые правила

- Префикс: `/api/v1/`.
- Формат: JSON (`application/json`), если не указано иное.
- Кодировка: UTF-8.
- Время: ISO 8601 UTC (`2026-01-31T12:00:00Z`).
- Идентификаторы: UUIDv7 (кроме Discord snowflake — строки).
- Версионирование: префикс `/v1/`; ломающие изменения — только `/v2/`.
- OpenAPI: `GET /api/schema/`, Swagger UI: `/api/docs/`, актуальный экспорт — `docs/openapi.yaml`.

## 2. Аутентификация

- Access-токен: JWT, 15 минут, передаётся `Authorization: Bearer <access>`.
- Refresh-токен: JWT, 30 дней, httpOnly-cookie `refresh_token` с `Path=/api/v1/auth/`, ротация при каждом обновлении.
- Для refresh/logout обязателен CSRF: frontend получает cookie через `GET /api/v1/auth/csrf` и отправляет `X-CSRFToken`.
- Discord OAuth2: `GET /api/v1/auth/discord/login` → redirect → callback → одноразовый `code` → `POST /api/v1/auth/discord/exchange`.
- Публичные эндпоинты: регистрация, вход, сброс пароля, подтверждение email, тарифы, webhook Stripe, health.

## 3. Ошибки

Единый формат для всех 4xx/5xx:

```json
{
  "code": "validation_error",
  "message": "Validation error",
  "details": {"email": ["Enter a valid email address."]},
  "request_id": "9f1c1f0e-8f7a-4f1c-9c5e-6b7f0f5e2a11"
}
```

- `code` — машиночитаемый код (`not_authenticated`, `permission_denied`, `not_found`, `validation_error`, `throttled`, `idempotency_conflict`, ...).
- `details` — объект или список; для не-полевых ошибок `{}`.
- `request_id` — совпадает с заголовком `X-Request-ID`; клиент передаёт свой `X-Request-ID`, иначе сервер генерирует UUID.

## 4. Пагинация

Курсорная, по всем спискам:

```
GET /api/v1/bots?limit=20&cursor=<opaque>
```

```json
{
  "next": "http://.../api/v1/bots?cursor=...",
  "previous": null,
  "results": []
}
```

- `limit` — 1..100, по умолчанию 20.
- Сортировка по умолчанию `-created_at`; для списков с фильтрами — `ordering`.
- Фильтры: `django-filter`, поиск — `search`, сортировка — `ordering`.

## 5. Throttling

| Scope | Лимит | Где |
|---|---|---|
| `anon` | 60/мин | по умолчанию |
| `user` | 600/мин | по умолчанию |
| `auth` | 10/мин | register/login |
| `token` | 30/мин | refresh/exchange/verify |
| `password_reset` | 5/мин | reset request/confirm |

Ответ 429 содержит `Retry-After` и стандартный формат ошибки.

## 6. Идемпотентность

Для небезопасных запросов (`POST/PUT/PATCH/DELETE`) клиент может передать:

```
Idempotency-Key: <uuid или строка до 255 символов>
```

- Ключ уникален в рамках пользователя; TTL — 24 часа.
- Повтор с тем же телом возвращает сохранённый ответ и заголовок `Idempotent-Replayed: true`.
- Повтор с другим телом — `409 idempotency_conflict`.
- Запросы без ключа обрабатываются как обычно.
- Не применяется к неаутентифицированным запросам (webhooks Stripe защищены подписью).

## 7. Лимиты тарифов

- `GET /api/v1/me/usage` — план, лимиты, использование, проценты и признак блокировки.
- Создание бота сверх лимита — `403 limit_exceeded` с `details.limit = "bots"`.
- Исполнения сценариев учитываются в `usage_counters`; Runtime вызывает `billing.services.check_execution_limit()` перед запуском.
- При 80% лимита создаётся уведомление `limit_warning`.
- При 100% исполнения блокируются; при истечении подписки пользователь деградирует до Free.

## 8. Основные группы эндпоинтов

| Группа | Префикс | Владелец |
|---|---|---|
| Auth, профиль, сессии | `/auth/*`, `/me`, `/me/sessions` | Артём |
| Боты, запуск, гильдии, версии | `/bots/*` | Саня |
| Модули | `/modules/*`, `/bots/{id}/modules/*` | Саня |
| Библиотека команд | `/commands-library/*` | Саня |
| Шаблоны | `/templates/*` | Шухратжон |
| Биллинг, лимиты | `/plans`, `/billing/*`, `/me/usage`, `/me/subscription`, `/me/invoices` | Артём |
| Уведомления | `/notifications/*` | Саня / Артём |
| Служебные | `/health`, `/api/schema/`, `/api/docs/` | Артём |

Точные пути, схемы запросов и ответов — в `docs/openapi.yaml`.

## 9. Health и наблюдаемость

- `GET /api/v1/health` → `200 {"status": "ok"}`; не требует авторизации.
- Все ответы содержат `X-Request-ID`.
- Ошибки логируются с `request_id`; секреты и токены в логи не попадают.

## 10. Правило изменения контракта

1. PR в `docs/api-contract.md` и `docs/openapi.yaml`.
2. Согласование с владельцем (Артём) и владельцем затронутой подсистемы.
3. Обновление типов frontend из OpenAPI.
4. Только после этого — код.
