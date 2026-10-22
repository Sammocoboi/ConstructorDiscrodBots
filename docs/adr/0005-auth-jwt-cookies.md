# 0005. JWT + refresh в httpOnly-cookie

- Статус: принято
- Дата: 2026-10-21

## Контекст

SPA обращается к API с другого origin. Нужны короткоживущие access-токены, отзыв сессий
и защита refresh-токена от XSS.

## Решение

- Access JWT — 15 минут в памяти frontend, заголовок `Authorization: Bearer`.
- Refresh JWT — 30 дней в httpOnly/SameSite=Lax cookie, путь `/api/v1/auth/`.
- Refresh-сессии хранятся в БД (`refresh_sessions`): jti, SHA-256 хеш, IP, user-agent, срок, отзыв.
- Ротация при каждом refresh, старый токен попадает в blacklist.
- Mutating-запросы с cookie защищены CSRF (`X-CSRFToken`).
- «Выйти на всех устройствах» отзывает все сессии пользователя.

## Способы входа (`AUTH_METHODS`)

Итерация 2 (CF-03): заказчик просил оставить только вход через Discord.

- Набор способов входа задаётся переменной окружения `AUTH_METHODS` (через запятую), по умолчанию — `email,discord`.
- При `AUTH_METHODS=discord` эндпоинты `/auth/register`, `/auth/login`, `/auth/password/*` возвращают `403 auth_method_disabled` и не создают сессий. Проверка выполняется после `super().initial()`, поэтому throttling продолжает работать.
- Код и модели email-аккаунтов сохраняются: по ТЗ FR-1.1 email-вход остаётся требованием, и заказчик может вернуть его без миграций.
- `/auth/email/verify` остаётся доступным, чтобы работали ссылки из уже отправленных писем.
- Django Admin, управление пользователями и сессиями от флага не зависят.

## Последствия

- Refresh-токен недоступен JavaScript.
- Нужна синхронизация cookie `Path`/`SameSite` и CORS `credentials`.
- Blacklist-таблица растёт; очистка — фоновая задача.
- Конфигурация `AUTH_METHODS` различается по окружениям; в production флаг задаётся вместе с остальными секретами.
