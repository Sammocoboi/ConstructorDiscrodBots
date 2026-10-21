# 0002. Gateway-соединения в отдельном сервисе

- Статус: принято
- Дата: 2026-10-21

## Контекст

Django-воркеры (gunicorn) не подходят для долгоживущих WebSocket-соединений: несколько
воркеров создадут несколько Gateway-подключений одного бота, а рестарт API оборвёт ботов.

## Решение

Gateway-подключения держит отдельный Runtime-сервис:

- supervisor распределяет ботов по воркерам;
- на одного бота — не больше одного Gateway-соединения (advisory lock в PostgreSQL);
- API только пишет `runtime_commands` и читает `bot_runtime_state`;
- hot reload — PostgreSQL `LISTEN/NOTIFY`.

## Последствия

- API и Runtime масштабируются независимо.
- Появляется дополнительная операционная единица (supervisor + воркеры) и heartbeat-контроль.
- Требуется graceful drain при деплое Runtime.
