# Архитектурные решения (ADR)

Короткие записи о значимых решениях. Новый ADR — отдельный файл `NNNN-краткое-имя.md`,
изменение принятого решения — новый ADR со ссылкой на предыдущий.

| № | Решение | Статус |
|---|---|---|
| [0001](0001-python-runtime.md) | Runtime на Python | принято |
| [0002](0002-discord-gateway.md) | Gateway-соединения в отдельном сервисе | принято |
| [0003](0003-procrastinate-queue.md) | Очередь Procrastinate на PostgreSQL | принято |
| [0004](0004-config-format-jsonb.md) | Конфигурация бота — JSONB с версией схемы | принято |
| [0005](0005-auth-jwt-cookies.md) | JWT + refresh в httpOnly-cookie | принято |
| [0006](0006-billing-idempotency.md) | Идемпотентность API и Stripe webhook | принято |
| [0007](0007-modal-runtime-split.md) | Backend и Runtime — разные процессы | принято |

Шаблон:

```markdown
# NNNN. Название

- Статус: предложено / принято / заменено
- Дата: YYYY-MM-DD
- Контекст
- Решение
- Последствия
```
