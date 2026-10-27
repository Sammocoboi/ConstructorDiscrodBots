# Discord Bot Constructor — Runtime

Сервис исполнения Discord-ботов: supervisor, Discord Gateway, интерпретатор
сценариев, версии, шаблоны, планировщик и health/metrics.

## Схема БД

Django — источник истины для `bots_bot`, `bots_botdraft`, `bots_botversion`,
`bots_runtimecommand`, `bots_botruntimestate` и `templates_catalog_*`. Runtime не
создаёт и не изменяет эти таблицы.

Runtime владеет только:

- `runtime_scheduled_jobs` — cron-задачи Runtime;
- `runtime_flow_traces` — трассировки flow.

Плюс создаёт индекс и trigger `runtime_command_notify` на Django-таблице
`bots_runtimecommand` (только если она уже существует). SQL:
`infra/migrations/001_runtime.sql`; порядок применения — после
`manage.py migrate`.

Токены расшифровываются общим `TOKEN_ENCRYPTION_KEY` (URL-safe base64, 32
байта) в формате `v1:<nonce+ciphertext>`. Plaintext-fallback отсутствует.

## Структура

```text
runtime/runtime/          # пакет сервиса
  bot.py                  # Discord-адаптер
  supervisor.py           # жизненный цикл ботов, heartbeat, advisory locks
  listener.py             # bots_runtimecommand через LISTEN/NOTIFY + polling
  db.py                   # PostgreSQL-адаптер Django-схемы
  versions.py             # черновики, публикация, откат, diff
  templates.py            # системные/пользовательские шаблоны, share-link
  scheduler.py            # cron и runtime_scheduled_jobs
  health.py               # /health, /ready, /metrics
runtime/content/
  blocks/                 # 15 JSON-манифестов блоков
  templates/              # 8 системных шаблонов
runtime/infra/
  migrations/             # runtime-owned SQL
  docker-compose.yml      # Runtime-only стек против внешней PostgreSQL
  Dockerfile.runtime
runtime/tests/
```

## Локальный запуск

Требования: Python 3.12+, PostgreSQL 16 с уже применёнными Django-миграциями.

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -e ".[dev]"

cp infra/.env.example .env
# заполнить DATABASE_URL и TOKEN_ENCRYPTION_KEY
python -m runtime.main
```

Схема Runtime применяется автоматически при старте (`ensure_schema`), либо
вручную:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/migrations/001_runtime.sql
```

## Docker

Production использует единый стек из корня репозитория:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Локально только Runtime против внешней PostgreSQL:

```bash
cd runtime/infra
cp .env.example .env
# DATABASE_URL по умолчанию использует host.docker.internal:5432
docker compose up -d --build
curl http://localhost:8080/health
curl http://localhost:8080/ready
docker compose logs -f runtime
```

Подробности: [docs/deploy.md](docs/deploy.md). Диагностика:
[docs/runbook.md](docs/runbook.md).

## Проверки

```bash
ruff check .
mypy runtime
pytest -q
```

## Контракты

- [docs/config-schema.md](docs/config-schema.md) — формат конфигурации бота.
- [docs/block-registry.md](docs/block-registry.md) — блоки сценариев и выражения.
- [docs/runtime-protocol.md](docs/runtime-protocol.md) — таблицы, команды,
  heartbeat, токены.
- [docs/templates.md](docs/templates.md) — шаблоны и share-link.
- [docs/testing.md](docs/testing.md) — QA-план.
- [docs/adr/0001-scheduler.md](docs/adr/0001-scheduler.md) — планировщик.
