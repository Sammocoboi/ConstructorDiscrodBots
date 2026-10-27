# Runbook

Команды ниже рассчитаны на production-стек из корня репозитория. Для локального
Runtime-only стека замените `-f docker-compose.prod.yml` на
`-f runtime/infra/docker-compose.yml` и выполняйте команды из `runtime/infra`.

## Быстрая диагностика

```bash
docker compose -f docker-compose.prod.yml ps -a
docker compose -f docker-compose.prod.yml logs --tail=200 migrate backend runtime caddy
curl -fsS https://api.<домен>/api/v1/health
docker compose -f docker-compose.prod.yml exec runtime \
  python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8080/ready').read().decode())"
docker compose -f docker-compose.prod.yml exec runtime \
  python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8080/').read().decode())"
```

Логи ищутся по `runtime.supervisor`, `runtime.listener`, `runtime.bot`,
`runtime.scheduler`, `runtime.interpreter`, `runtime.db`.

## Стек не стартует

1. Проверить `.env` и подстановку:
   `docker compose -f docker-compose.prod.yml config`.
2. `docker compose ... logs migrate` — миграция должна завершиться с кодом 0.
3. `docker compose ... ps -a` — `migrate` должен быть `exited (0)`, а не
   `exited (1)`.
4. `invalid runtime configuration` — нет `DATABASE_URL`, `TOKEN_ENCRYPTION_KEY`
   или некорректное числовое значение интервала.
5. `TOKEN_ENCRYPTION_KEY is required` — переменная не задана или пустая.
6. `TOKEN_ENCRYPTION_KEY must decode to 32 bytes` — ключ не URL-safe base64 или
   не 32 байта. Перегенерировать и задать одинаково для backend/Runtime.
7. `FileNotFoundError: runtime migration not found` — в образ Runtime не
   скопирован `infra/migrations` (пересобрать `runtime`).
8. `blocks directory does not exist` — не скопирован `content/blocks`.

Если `migrate` упал на `psql`, проверьте, что Django-миграции прошли: Runtime SQL
создаёт trigger только при существующей `bots_runtimecommand`, но остальные
таблицы Runtime от Django не зависят.

## Бот не запускается

| Симптом | Проверка | Действие |
|---|---|---|
| `TokenDecryptionError` / `token decryption failed` | ключ backend = Runtime, формат `v1:` | задать правильный `TOKEN_ENCRYPTION_KEY`, перезапустить backend и Runtime, затем `start` через UI |
| `invalid_token` | токен в БД, Discord 401 | заменить токен через backend, проверить ключ |
| `missing_intents` | Privileged Intents в Discord Developer Portal | включить Members/Message Content или убрать блок |
| `bot is locked by another worker` | второй воркер держит бота | остановить лишний воркер, проверить `bots_botruntimestate.worker_id` |
| capacity | `MAX_BOTS_PER_WORKER` | поднять лимит или добавить воркер |
| вечный `starting` | Gateway/сеть, логи `runtime.bot` | проверить исходящий HTTPS, токен, статус Discord |
| `suspended` | 5 неудачных попыток | исправить причину, затем `start` |
| `desired_state = stopped` после ошибки | постоянная ошибка токена/intents | исправить причину и явно запустить бота заново |

SQL:

```sql
SELECT id, name, desired_state, status, last_error, last_error_at
FROM bots_bot
WHERE deleted_at IS NULL
ORDER BY updated_at DESC;

SELECT bot_id, worker_id, status, guild_count, version_number,
       latency_ms, uptime_seconds, heartbeat_at
FROM bots_botruntimestate
ORDER BY heartbeat_at DESC NULLS LAST;

SELECT id, bot_id, command, status, error, created_at, processed_at
FROM bots_runtimecommand
ORDER BY created_at DESC
LIMIT 20;
```

Запуск SQL в контейнере:

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### Проверка совпадения ключей

Отпечаток ключа (не сам ключ) можно сравнить в обоих контейнерах:

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -c "from apps.common.crypto import _key; import hashlib; print(hashlib.sha256(_key()).hexdigest())"
docker compose -f docker-compose.prod.yml exec runtime \
  python -c "from runtime.crypto import normalize_key; import os,hashlib; print(hashlib.sha256(normalize_key(os.environ['TOKEN_ENCRYPTION_KEY'])).hexdigest())"
```

Отпечатки должны совпадать. Если ключ менялся, старые токены нужно заново
сохранить через backend (потребуется исходный токен); смена ключа «на лету» не
восстановит их.

## Команды не доходят

1. Проверить `bots_runtimecommand` — есть ли `pending`.
2. Проверить trigger:

   ```sql
   SELECT tgname
   FROM pg_trigger
   WHERE tgrelid = 'bots_runtimecommand'::regclass;
   ```

   Должен быть `runtime_command_notify`. Если его нет — выполнить
   `docker compose -f docker-compose.prod.yml run --rm migrate` или
   перезапустить Runtime (он применяет `001_runtime.sql`).
3. Проверить, что Runtime слушает канал: в логах не должно быть
   `LISTEN/NOTIFY unavailable`; иначе работает polling раз в 30 секунд.
4. `pending` не уходит — listener/polling не работает или БД недоступна.
   Проверить `/ready` и `logs runtime`.
5. `acknowledged`, но бот не изменился — команда принята; смотреть логи
   `runtime.supervisor` и `bots_bot.status`. Помните: в Django-схеме
   `acknowledged` означает и «принята», и «выполнена».
6. `failed` — читать `error`; исправить причину и повторить команду из UI.

Зависшую команду можно вернуть в очередь **только после разбора**, иначе
действие выполнится дважды:

```sql
UPDATE bots_runtimecommand
SET status = 'pending', processed_at = NULL, error = '', updated_at = now()
WHERE id = '<uuid>';
```

## Дубли ответов бота

Причина — два воркера одновременно. Advisory lock должен предотвращать это.
Проверить:

```sql
SELECT bot_id, worker_id, status, heartbeat_at
FROM bots_botruntimestate
ORDER BY bot_id;

SELECT pid, objid, classid
FROM pg_locks
WHERE locktype = 'advisory';
```

Остановить лишний воркер, дождаться закрытия его соединений. Не удалять lock
вручную при живом воркере.

## Heartbeat устарел

`heartbeat_at` старше 60 секунд означает: воркер завис/упал или бот не в
`starting`/`online`. Runtime не меняет статус автоматически. Действия:

1. `docker compose -f docker-compose.prod.yml restart runtime`;
2. проверить `docker stats`, OOM, сеть;
3. после рестарта reconcile поднимет ботов с `desired_state='running'`;
4. если бот остался `stopped`, проверить `last_error` и запустить вручную.

## Планировщик Runtime

```sql
SELECT name, cron, status, next_run_at, last_run_at, last_started_at, last_error
FROM runtime_scheduled_jobs
ORDER BY name;
```

- `status='running'` и `last_started_at` давно — задача зависла; сбросить
  `status='idle'`, `next_run_at=now()` после разбора.
- `unknown job handler` — handler не зарегистрирован в Runtime; обновить код.
- `could not find next run` — некорректный cron; исправить `cron`.
- Штатные задачи: `cleanup-runtime-commands` и `cleanup-flow-traces`.

Cron — 5 полей: минута, час, день месяца, месяц, день недели. Поддерживаются
`*`, числа, диапазоны, шаги и имена месяцев/дней (`jan`, `mon`).

`bots_scheduledjob` — пользовательские отложенные flow-задачи Django. Runtime
их не читает и не изменяет; не путать с `runtime_scheduled_jobs`.

## Шаблоны и share-link

- `invalid share token` — ссылка повреждена/подписана другим секретом.
- `share token expired` — TTL 7 дней; выпустить новую ссылку.
- `secret-like key` / `Discord token detected` — шаблон содержит секрет;
  удалить поле, секреты хранятся только в `bots_bot.token_encrypted`.
- `config exceeds 2 MB` — уменьшить шаблон.
- Пользовательские шаблоны: `templates_catalog_template` и
  `templates_catalog_templateversion`; системные — файлы в `content/templates`.

## PostgreSQL

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose -f docker-compose.prod.yml exec postgres \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version();"'
docker compose -f docker-compose.prod.yml exec postgres \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT pg_size_pretty(pg_database_size(current_database()));"'
```

PostgreSQL не опубликован на хост; подключаться снаружи через `exec` или
временный контейнер в сети стека.

При потере диска/БД — восстановить последний дамп:

```bash
docker compose -f docker-compose.prod.yml stop backend runtime frontend caddy
docker compose -f docker-compose.prod.yml run --rm --entrypoint sh backup \
  /usr/local/bin/restore.sh /backups/constructor-<UTC>.dump
docker compose -f docker-compose.prod.yml up -d
```

`restore.sh` заменяет содержимое БД. После восстановления проверьте
`migrate`/`/ready` и статусы ботов.

## Caddy, TLS и 502

```bash
docker compose -f docker-compose.prod.yml logs --tail=200 caddy
curl -I https://app.<домен>/
curl -I https://api.<домен>/api/v1/health
```

- ACME-ошибки — DNS не указывает на VPS или закрыт 80/tcp.
- `502` на app — frontend не прошёл healthcheck или backend недоступен;
  проверить `ps`, `logs frontend backend`.
- `502` на api — backend упал/не прошёл healthcheck; смотреть `logs backend`.
- 404 на `/static/admin/...` — `collectstatic` не выполнился; перезапустить
  `migrate`.
- 404 на `/media/...` — файл не создан или volume `backend_media` не смонтирован.

## Graceful shutdown и деплой

1. `docker compose -f docker-compose.prod.yml stop runtime` — SIGTERM, drain до
   20 секунд.
2. Убедиться, что боты `stopped`, locks освобождены.
3. Обновить образ/код, выполнить `run --rm migrate`, затем `up -d`.
4. Проверить `/ready`, `bots_botruntimestate` и статусы ботов.

При штатном shutdown `desired_state` остаётся `running`, поэтому после старта
Runtime поднимет ботов автоматически. Если нужно, чтобы бот не поднялся,
сначала переведите его в `stopped` через UI/API.

## Rollback

См. `docs/deploy.md`: откат кода через предыдущий commit/тег и пересборку.
Django-миграции автоматически назад не откатываются; при несовместимой схеме
восстанавливайте БД из backup.

## Эскалация

- токены/ключи — к владельцу backend (Артём/Саня), не логировать;
- Discord API/intents — Саня;
- ошибки интерпретатора/шаблонов — Шухратжон;
- инфраструктура/CI — Шухратжон, ревью Артём.
