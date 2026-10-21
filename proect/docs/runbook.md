# Runbook

## Быстрая диагностика

```bash
cd proect/infra
docker compose ps
docker compose logs --tail=200 runtime
curl -s localhost:8080/health
curl -s localhost:8080/ready
curl -s localhost:8080/ | python -m json.tool
```

Логи ищутся по `runtime.supervisor`, `runtime.listener`, `runtime.bot`,
`runtime.scheduler`, `runtime.interpreter`.

## Runtime не стартует

1. `docker compose logs migrate` — миграция должна завершиться с кодом 0.
2. Проверить `DATABASE_URL`, доступность `db`, пароль.
3. `invalid runtime configuration` — отсутствует `DATABASE_URL` или
   нечисловое значение интервала.
4. `FileNotFoundError: runtime migration not found` — в образ не скопирован
   `infra/migrations` (пересобрать `runtime`).
5. `blocks directory does not exist` — не скопирован `content/blocks`.

## Бот не запускается

| Симптом | Проверка | Действие |
|---|---|---|
| `invalid_token` | токен в БД, ключ шифрования | заменить токен через backend, проверить `BOT_TOKEN_ENCRYPTION_KEY` |
| `missing_intents` | Privileged Intents в Discord Developer Portal | включить Members/Message Content или убрать блок |
| `bot is locked by another worker` | второй воркер держит бота | остановить лишний воркер, проверить `bot_runtime_state.worker_id` |
| capacity | `MAX_BOTS_PER_WORKER` | поднять лимит или добавить воркер |
| вечный `starting` | Gateway/сеть, логи `runtime.bot` | проверить исходящий HTTPS, токен, Discord status |
| `suspended` | 5 неудачных попыток | исправить причину, затем `start` |

SQL:

```sql
SELECT id, name, desired_state, status, last_error, last_error_at
FROM bots WHERE deleted_at IS NULL ORDER BY updated_at DESC;

SELECT * FROM bot_runtime_state ORDER BY heartbeat_at DESC;

SELECT id, bot_id, command, status, error, created_at
FROM runtime_commands ORDER BY created_at DESC LIMIT 20;
```

## Команды не доходят

1. Проверить `runtime_commands` — есть ли `pending`.
2. Проверить триггер:
   `SELECT tgname FROM pg_trigger WHERE tgrelid = 'runtime_commands'::regclass;`
   Должен быть `runtime_commands_notify`.
3. Проверить, что Runtime слушает канал: в логах не должно быть
   `LISTEN/NOTIFY unavailable`; иначе работает polling раз в 30 секунд.
4. `acked`, но не `done/failed` — воркер упал во время выполнения; смотреть
   логи и снять зависшую команду вручную после разбора.

## Дубли ответов бота

Причина — два воркера одновременно. Advisory lock должен предотвращать это.
Проверить:

```sql
SELECT bot_id, worker_id, status, heartbeat_at FROM bot_runtime_state;
```

Остановить лишний воркер, дождаться закрытия его соединений. Не удалять lock
вручную при живом воркере.

## Heartbeat устарел

`heartbeat_at` старше 60 секунд означает: воркер завис/упал или бот не в
`starting/online`. Runtime не меняет статус автоматически. Действия:

1. `docker compose restart runtime` (или scale);
2. проверить `docker stats`, OOM, сеть;
3. после рестарта reconcile поднимет ботов с `desired_state='running'`.

## Планировщик

```sql
SELECT name, cron, status, next_run_at, last_run_at, last_error
FROM scheduled_jobs ORDER BY name;
```

- `status='running'` и `last_started_at` давно — задача зависла; сбросить
  `status='idle'`, `next_run_at=now()` после разбора.
- `unknown job handler` — handler не зарегистрирован в Runtime; обновить код.
- `could not find next run` — некорректный cron; исправить `cron`.

Cron — 5 полей: минута, час, день месяца, месяц, день недели. Поддерживаются
`*`, числа, диапазоны, шаги и имена месяцев/дней (`jan`, `mon`).

## Шаблоны и share-link

- `invalid share token` — ссылка повреждена/подписана другим секретом.
- `share token expired` — TTL 7 дней; выпустить новую ссылку.
- `secret-like key` / `Discord token detected` — шаблон содержит секрет;
  удалить поле, секреты хранятся только в `bots.token_encrypted`.
- `config exceeds 2 MB` — уменьшить шаблон.

## PostgreSQL

```bash
docker compose exec db pg_isready -U constructor -d constructor
docker compose exec db psql -U constructor -d constructor -c "SELECT version();"
```

При потере диска/БД — восстановить последний дамп (`restore.sh`), затем
`docker compose up -d`. Runtime при старте применит идемпотентную миграцию.

## Graceful shutdown и деплой

1. `docker compose stop runtime` — SIGTERM, drain до 20 секунд.
2. Убедиться, что боты `stopped`, locks освобождены.
3. Обновить образ/код, `docker compose up -d`.
4. Проверить `/ready` и статусы ботов.

## Эскалация

- токены/ключи — к владельцу backend (Артём/Саня), не логировать;
- Discord API/intents — Саня;
- ошибки интерпретатора/шаблонов — Шухратжон;
- инфраструктура/CI — Шухратжон, ревью Артём.
