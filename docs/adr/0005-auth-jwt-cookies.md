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

## Последствия

- Refresh-токен недоступен JavaScript.
- Нужна синхронизация cookie `Path`/`SameSite` и CORS `credentials`.
- Blacklist-таблица растёт; очистка — фоновая задача.
