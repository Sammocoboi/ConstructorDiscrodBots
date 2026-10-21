# Deploy

## Состав

В этой ветке Docker Compose поднимает Runtime-контур:

- `db` — PostgreSQL 16;
- `migrate` — одноразовое применение `infra/migrations/001_runtime.sql`;
- `runtime` — сервис `python -m runtime.main`.

Backend (Django) и frontend живут в своих ветках. Они подключаются к тому же
PostgreSQL; объединённый compose собирается после мержа зон. Runtime не
импортирует Django-модели и общается с backend только через таблицы.

## Требования

- Docker Engine 24+ и Compose v2;
- 1 ГБ RAM для Runtime + PostgreSQL;
- исходящий HTTPS к Discord Gateway;
- секрет `BOT_TOKEN_ENCRYPTION_KEY` (32 байта, base64), одинаковый с backend.

## Первый деплой

```bash
cd proect/infra
cp .env.example .env
# отредактировать .env: пароль PostgreSQL, ключ, worker id
docker compose up -d --build
docker compose ps
curl http://localhost:8080/health
curl http://localhost:8080/ready
```

`migrate` завершается успешно один раз и остаётся в статусе `exited (0)` — это
нормально. При изменении SQL перезапустите:

```bash
docker compose run --rm migrate
```

Для существующей БД миграция идемпотентна: `CREATE ... IF NOT EXISTS`,
`ALTER ... IF NOT EXISTS`, `DROP TRIGGER IF EXISTS`. Seed-задачи вставляются
через `ON CONFLICT (name) DO NOTHING`.

## Переменные

| переменная | по умолчанию | назначение |
|---|---|---|
| `POSTGRES_DB` | `constructor` | имя БД |
| `POSTGRES_USER` | `constructor` | пользователь БД |
| `POSTGRES_PASSWORD` | `constructor` | пароль БД (сменить) |
| `POSTGRES_PORT` | `5432` | порт на хосте |
| `DATABASE_URL` | `postgresql://constructor:constructor@db:5432/constructor` | DSN Runtime |
| `WORKER_ID` | `runtime-1` | id воркера, уникален |
| `MAX_BOTS_PER_WORKER` | `25` | capacity |
| `HEARTBEAT_INTERVAL` | `15` | секунды |
| `RECONCILE_INTERVAL` | `10` | секунды |
| `COMMAND_POLL_INTERVAL` | `30` | страховочный polling |
| `RESTART_LIMIT` | `5` | попытки авторестарта |
| `RUNTIME_PORT` | `8080` | health/metrics на хосте |
| `BOT_TOKEN_ENCRYPTION_KEY` | — | AES-256-GCM ключ |
| `SENTRY_DSN` | — | включает Sentry (extra `observability`) |

Сгенерировать ключ:

```bash
python -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())"
```

Ключ нельзя менять без перешифрования токенов: иначе Runtime не сможет
расшифровать `bots.token_encrypted` и упадёт в fallback «считать plaintext».

## Обновление

```bash
cd proect/infra
docker compose pull
docker compose build runtime
docker compose up -d
docker compose logs -f runtime
```

При SIGTERM Runtime останавливает listener, scheduler и всех ботов, освобождает
advisory locks. `stop_grace_period: 20s` даёт запас на drain.

## CI

`.github/workflows/ci.yml` запускается на изменения в `proect/`:

1. Python 3.12;
2. `pip install -e ".[dev]"`;
3. `ruff check .`;
4. `mypy runtime`;
5. `pytest -q`.

CI не поднимает PostgreSQL: unit-тесты используют in-memory репозитории.
Интеграционные тесты БД — отдельный этап (см. `docs/testing.md`).

## Бэкапы

```bash
cd proect/infra
./backup.sh
```

Скрипт делает `pg_dump --clean --if-exists`, сжимает gzip в `infra/backups/`
и удаляет файлы старше 14 дней. Восстановление:

```bash
./restore.sh backups/constructor-20261021T030000Z.sql.gz
```

Для production добавьте ежедневный cron/Task Scheduler и выгрузку в S3/внешнее
хранилище. Проверяйте restore на staging раз в месяц.

## Мониторинг

- `/metrics` — Prometheus scrape;
- `/health` — liveness, `/ready` — readiness;
- `bot_runtime_state.heartbeat_at` — свежесть ботов;
- `runtime_commands.status='failed'` — ошибки команд;
- `scheduled_jobs.status='error'` и `last_error` — планировщик;
- Sentry — исключения, если задан `SENTRY_DSN`.

## Production-чеклист

- [ ] Сменить `POSTGRES_PASSWORD`, не коммитить `.env`.
- [ ] Задать случайный `BOT_TOKEN_ENCRYPTION_KEY`, совпадающий с backend.
- [ ] Закрыть PostgreSQL от внешней сети, оставить только внутреннюю сеть.
- [ ] TLS-терминация перед `/metrics` (не публиковать наружу без auth).
- [ ] Ограничить `MAX_BOTS_PER_WORKER` по RAM/CPU.
- [ ] Настроить бэкапы и проверить restore.
- [ ] Проверить `curl /ready` и алерт на 503.
- [ ] Запустить staging на тестовом Discord-сервере.
