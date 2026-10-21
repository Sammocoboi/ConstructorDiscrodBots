# ADR 0001: Планировщик Runtime

**Статус:** принято для Runtime; Procrastinate — рекомендация для backend.
**Дата:** 2026-10-21.

## Контекст

Нужны фоновые задачи: очистка `runtime_commands`, `flow_traces`, сброс
`usage_counters`, синхронизация slash-команд, email. Backend — Django на
PostgreSQL; Runtime — отдельный Python-сервис без Django. Кандидаты:
Procrastinate, Django-Q2, собственный cron на `scheduled_jobs`.

## Решение

1. **Runtime** использует таблицу `scheduled_jobs` + cron-парсер и
   `SELECT ... FOR UPDATE SKIP LOCKED` для захвата задач. Это уже реализовано
   в `runtime/scheduler.py` и `runtime/db.py`.
2. **Backend** для своих задач (email, синхронизация команд, платежи)
   использует **Procrastinate**: PostgreSQL-native, без Redis, транзакционная
   постановка задач, знакомый стек.
3. Не добавляем второй брокер/очередь в Runtime. Runtime-задачи остаются
   локальными и идемпотентными.

## Почему

- Runtime не должен тянуть Django/Q2 или Redis.
- `SKIP LOCKED` даёт безопасную работу нескольких воркеров без отдельного
  сервиса.
- Procrastinate разделяет очередь backend и runtime-циклы, но использует ту же
  PostgreSQL.
- Простая эксплуатация: меньше контейнеров, меньше точек отказа.

## Последствия

- Cron — только 5 полей, без секунд; сложные расписания выражаются несколькими
  задачами.
- Нет встроенного retry/backoff у `scheduled_jobs`: ошибка пишется в
  `last_error`, `next_run_at` остаётся; повтор — по расписанию.
- Для email/тяжёлых задач backend обязан использовать Procrastinate, а не
  Runtime.
- При росте нагрузки `scheduled_jobs` можно заменить на Procrastinate без
  изменения таблиц Runtime.

## Альтернативы

- **Django-Q2** — требует Django ORM в Runtime, отклонено.
- **Celery + Redis** — лишний брокер, отклонено для MVP.
- **Только Procrastinate в Runtime** — возможно позже, но сейчас Runtime не
  Django; накладные расходы выше выгоды.
