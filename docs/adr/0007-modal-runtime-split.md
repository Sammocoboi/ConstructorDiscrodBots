# 0007. Backend и Runtime — разные процессы

- Статус: принято
- Дата: 2026-10-21

## Контекст

Backend обслуживает HTTP и должен быстро рестартовать при деплое. Runtime держит
долгоживущие соединения с Discord и не должен зависеть от рестарта API.

## Решение

- `backend` — Django/DRF, stateless, масштабируется горизонтально.
- `runtime` — отдельный контейнер/сервис, состояние только в PostgreSQL.
- Контракт — таблицы `runtime_commands`, `bot_runtime_state` и `docs/runtime-protocol.md`.
- Runtime не импортирует Django-код; общие JSON-схемы лежат в `docs/`.

## Последствия

- Деплой backend не рвёт ботов.
- Нужны health-check, heartbeat и graceful drain Runtime.
- Дублирование части валидации между backend и Runtime компенсируется contract-тестами.
