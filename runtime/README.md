# Discord Bot Constructor — Runtime

Сервис исполнения Discord-ботов: supervisor, Discord Gateway, интерпретатор
сценариев, версии, шаблоны, планировщик и health/metrics.

## Структура

```text
runtime/                # сервис Runtime
  interpreter/          # реестр блоков, выражения, executor, валидация
  bot.py                # Discord-адаптер
  supervisor.py         # жизненный цикл ботов и heartbeat
  listener.py           # runtime_commands через LISTEN/NOTIFY + polling
  versions.py           # черновики, публикация, откат, diff
  templates.py          # системные/пользовательские шаблоны, share-link
  scheduler.py          # cron и scheduled_jobs
  health.py             # /health, /ready, /metrics
content/
  blocks/               # 15 JSON-манифестов блоков
  templates/            # 8 системных шаблонов
infra/
  migrations/           # SQL-схема Runtime
  docker-compose.yml    # PostgreSQL + migrate + runtime
tests/
```

## Локальный запуск

Требования: Python 3.12+, PostgreSQL 16.

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -e ".[dev]"

cp infra/.env.example .env
# заполнить DATABASE_URL и BOT_TOKEN_ENCRYPTION_KEY
python -m runtime.main
```

Схема БД применяется автоматически при старте (`ensure_schema`), либо вручную:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/migrations/001_runtime.sql
```

## Docker

```bash
cd infra
cp .env.example .env
docker compose up -d --build
curl http://localhost:8080/health
docker compose logs -f runtime
```

Подробности: [docs/deploy.md](docs/deploy.md). Диагностика: [docs/runbook.md](docs/runbook.md).

## Проверки

```bash
ruff check .
mypy runtime
pytest -q
```

## Контракты

- [docs/config-schema.md](docs/config-schema.md) — формат конфигурации бота.
- [docs/block-registry.md](docs/block-registry.md) — блоки сценариев и выражения.
- [docs/runtime-protocol.md](docs/runtime-protocol.md) — таблицы, команды, heartbeat.
- [docs/templates.md](docs/templates.md) — шаблоны и share-link.
- [docs/testing.md](docs/testing.md) — QA-план.
- [docs/adr/0001-scheduler.md](docs/adr/0001-scheduler.md) — выбор планировщика.
