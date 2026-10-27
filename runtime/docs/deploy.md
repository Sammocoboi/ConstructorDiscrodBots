# Deploy

## Топологии

В репозитории три compose-файла с разным назначением:

| Файл | Назначение | Сервисы |
|---|---|---|
| `docker-compose.prod.yml` (корень) | **production** | `postgres`, `migrate`, `backend`, `runtime`, `frontend`, `caddy`; профили `monitoring`, `backup` |
| `docker-compose.yml` (корень) | локальная разработка | `db`, `backend` (`runserver`) |
| `runtime/infra/docker-compose.yml` | только Runtime | `migrate`, `runtime`; PostgreSQL внешний |

Production-стек — единственный источник истины для реального запуска. В нём
backend и Runtime используют **одну** БД, а наружу открыт только Caddy (80/443).
PostgreSQL, backend, Runtime и frontend доступны только внутри Docker-сети.

## Требования

- Docker Engine 24+ и Compose v2;
- VPS минимум 2 vCPU / 4 ГБ RAM (для PostgreSQL + backend + Runtime + Caddy);
- DNS A/AAAA-записи `app.<домен>` и `api.<домен>` на VPS;
- открытые 80/tcp и 443/tcp (80 нужен Caddy для ACME HTTP-challenge и
  редиректа);
- исходящий HTTPS к Discord Gateway (443);
- секрет `TOKEN_ENCRYPTION_KEY` — URL-safe base64 ровно 32 байта.

## Подготовка `.env`

```bash
cp .env.production.example .env
# заполнить APP_DOMAIN, API_DOMAIN, пароли, ключи, Discord/Stripe/Email
```

Ключ шифрования:

```bash
python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

`TOKEN_ENCRYPTION_KEY` должен быть **одинаковым** для backend и Runtime. При его
потере/замене существующие `bots_bot.token_encrypted` перестанут
расшифровываться; Runtime переведёт таких ботов в `error` и `desired_state =
stopped`. Токены придётся заново сохранить через backend, имея их исходные
значения.

Обязательные переменные:

| переменная | назначение |
|---|---|
| `APP_DOMAIN` | домен SPA, например `app.example.com` |
| `API_DOMAIN` | домен API/admin, например `api.example.com` |
| `DJANGO_SECRET_KEY` | ≥32 случайных символов |
| `POSTGRES_PASSWORD` | пароль БД, не `constructor` |
| `TOKEN_ENCRYPTION_KEY` | общий ключ backend/Runtime |
| `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET` | Discord OAuth2 |
| `DISCORD_REDIRECT_URI` | `https://api.<домен>/api/v1/auth/discord/callback` |
| `STRIPE_*` | биллинг, если включён |
| `EMAIL_*` | SMTP, если включён |
| `WORKER_ID` | уникальный id Runtime-воркера |

`DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` и
`DATABASE_URL` вычисляются в `docker-compose.prod.yml` из `APP_DOMAIN`,
`API_DOMAIN` и `POSTGRES_*`; значения из `.env` для них не используются.
Пароль PostgreSQL должен быть URL-safe (или percent-encoded), потому что он
подставляется в `DATABASE_URL`.

## Первый деплой

```bash
docker compose -f docker-compose.prod.yml config >/dev/null
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps -a
docker compose -f docker-compose.prod.yml logs migrate
```

`migrate` — одноразовый сервис. Он выполняет строго по порядку:

1. `python manage.py migrate --noinput`;
2. `python manage.py collectstatic --noinput`;
3. `psql -f runtime/infra/migrations/001_runtime.sql`.

Успешный `migrate` остаётся в статусе `exited (0)` — это нормально. Backend и
Runtime стартуют только после `service_completed_successfully`. Runtime при
старте ещё раз идемпотентно применяет свой SQL, поэтому trigger на
`bots_runtimecommand` появится даже при ручном запуске.

Проверка:

```bash
curl -fsS https://api.example.com/api/v1/health
curl -fsS https://app.example.com/ >/dev/null
docker compose -f docker-compose.prod.yml exec runtime \
  python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8080/ready').read().decode())"
docker compose -f docker-compose.prod.yml logs --tail=100 caddy backend runtime
```

Caddy выпускает сертификаты Let's Encrypt автоматически. Если DNS ещё не
указал на VPS или закрыт 80/tcp, в `logs caddy` будут ошибки ACME.

Если изменился только Runtime SQL:

```bash
docker compose -f docker-compose.prod.yml run --rm migrate
```

## Маршрутизация и TLS

```text
https://app.<домен>/        -> frontend (nginx, SPA)
https://app.<домен>/api/*   -> frontend nginx -> backend:8000
https://app.<домен>/media/* -> общий volume backend_media через Caddy
https://api.<домен>/        -> backend:8000 (API, /admin/, /static/, /api/docs/)
https://api.<домен>/media/* -> общий volume backend_media через Caddy
```

- TLS завершается на Caddy; backend получает `X-Forwarded-Proto: https`.
- Django static/admin отдаёт WhiteNoise из Gunicorn-процесса; отдельный nginx
  для статики не нужен.
- Frontend-контейнер — nginx со сборкой Vite; он проксирует `/api/` на backend,
  поэтому SPA и API можно держать на одном origin.
- Наружу опубликованы только `80:80`, `443:443`, `443:443/udp` у Caddy.
  PostgreSQL (`5432`), backend (`8000`), Runtime (`8080`) и frontend (`80`) не
  имеют `ports:`.

## Переменные Runtime

| переменная | по умолчанию | назначение |
|---|---|---|
| `WORKER_ID` | `runtime-1` | уникальный id воркера |
| `LOG_LEVEL` | `INFO` | уровень логов |
| `MAX_BOTS_PER_WORKER` | `25` | capacity |
| `HEARTBEAT_INTERVAL` | `15` | секунды |
| `RECONCILE_INTERVAL` | `10` | секунды |
| `COMMAND_POLL_INTERVAL` | `30` | страховочный polling |
| `RESTART_LIMIT` | `5` | попытки авторестарта |
| `SENTRY_DSN` | — | Sentry, если задан |
| `TOKEN_ENCRYPTION_KEY` | — | общий AES-256-GCM ключ |

Устаревшее `BOT_TOKEN_ENCRYPTION_KEY` Runtime принимает как fallback, но в
новом стеке используйте только `TOKEN_ENCRYPTION_KEY`.

## Обновление

```bash
git pull --ff-only
docker compose -f docker-compose.prod.yml build backend runtime frontend
docker compose -f docker-compose.prod.yml run --rm migrate
docker compose -f docker-compose.prod.yml up -d --no-deps backend runtime frontend caddy
docker compose -f docker-compose.prod.yml ps
```

- Перед обновлением с потенциально несовместимой миграцией сделайте backup.
- Django-миграции выполняются вперёд; автоматического rollback схемы нет.
- При SIGTERM Runtime останавливает listener, scheduler и ботов, освобождает
  advisory locks. `stop_grace_period` — 20 секунд, у backend — 30 секунд.

## Rollback

Код:

```bash
git checkout <предыдущий-коммит-или-тег>
docker compose -f docker-compose.prod.yml build backend runtime frontend
docker compose -f docker-compose.prod.yml up -d --no-deps backend runtime frontend caddy
```

Если новая версия уже применила несовместимую миграцию, откат кода не вернёт
схему. В этом случае остановите сервисы и восстановите БД из backup (ниже).
Перед destructive-миграцией всегда делайте дамп.

## Бэкапы

Включить ежедневный backup-контейнер:

```bash
docker compose -f docker-compose.prod.yml --profile backup up -d backup
```

- дампы: `${BACKUP_DIR:-./backups}/constructor-<UTC>.dump`;
- формат: `pg_dump --format=custom --no-owner --no-privileges`;
- рядом пишется `.sha256`;
- retention: `BACKUP_RETENTION_DAYS` (14 дней);
- интервал: `BACKUP_INTERVAL` секунд (86400);
- контейнер работает в цикле и делает первый дамп сразу при старте.

Немедленный внеочередной дамп:

```bash
docker compose -f docker-compose.prod.yml restart backup
```

Восстановление (остановить сервисы, которые пишут в БД):

```bash
docker compose -f docker-compose.prod.yml stop backend runtime frontend caddy
docker compose -f docker-compose.prod.yml run --rm --entrypoint sh backup \
  /usr/local/bin/restore.sh /backups/constructor-20261027T030000Z.dump
docker compose -f docker-compose.prod.yml up -d
```

`restore.sh` использует `pg_restore --clean --if-exists` и **заменяет**
содержимое БД. Скопируйте дампы в S3/внешнее хранилище: локальный volume не
защищает от потери VPS. Раз в месяц проверяйте restore на staging.

## Мониторинг

```bash
docker compose -f docker-compose.prod.yml --profile monitoring up -d prometheus
```

- Prometheus: `http://127.0.0.1:9090` (порт привязан к loopback);
- scrape target: `runtime:8080/metrics`;
- `/health` — liveness контейнера Runtime;
- `/ready` — БД + остановка воркера, `503` при проблемах;
- Sentry — задайте `SENTRY_DSN`;
- алерты: `runtime_commands_failed_total`, `runtime_bots_total{status="error"}`,
  устаревший `bots_botruntimestate.heartbeat_at`, `503` от `/ready`.

## Локальная разработка

`docker-compose.yml` в корне — только PostgreSQL и Django `runserver`. Runtime и
frontend запускаются отдельно:

```bash
# БД + backend
cp .env.example .env
docker compose up --build

# Runtime против той же БД (после Django migrate)
cd runtime/infra
cp .env.example .env
docker compose up --build

# frontend
cd frontend
npm ci
npm run dev
```

`runtime/infra/docker-compose.yml` не создаёт PostgreSQL и не применяет
Django-миграции: он подключается к БД, где схема Django уже создана. В
`.env.example` используется `host.docker.internal`, потому что корневой dev
compose публикует PostgreSQL на хосте; compose добавляет `host-gateway` для
Linux.

## Ограничения проверки

В текущем локальном окружении нет Docker, PostgreSQL и реального Discord-
токена. Compose-файлы, миграции и lifecycle проверены статически и unit-тестами,
но не запускались на реальном VPS. Перед production-запуском обязательны:

- `docker compose -f docker-compose.prod.yml config`;
- первый `up` на staging с реальными доменами;
- проверка backup/restore;
- smoke-тест Discord-бота (start/stop/reload/токен/intents).

## Production-чеклист

- [ ] DNS `app.*` и `api.*` указывает на VPS, 80/443 открыты.
- [ ] `POSTGRES_PASSWORD` и `DJANGO_SECRET_KEY` заменены на случайные.
- [ ] `TOKEN_ENCRYPTION_KEY` задан и совпадает у backend/Runtime.
- [ ] `migrate` завершился с кодом 0, trigger `runtime_command_notify` создан.
- [ ] `curl https://api.*/api/v1/health` и `/ready` отвечают `200`.
- [ ] Caddy выпустил сертификаты для обоих доменов.
- [ ] PostgreSQL/Runtime/backend/frontend не опубликованы наружу.
- [ ] Backup-профиль включён, restore проверен.
- [ ] Настроены Sentry/Prometheus и алерты.
- [ ] `MAX_BOTS_PER_WORKER` соответствует RAM/CPU.
- [ ] Пройден smoke-тест Discord на тестовом сервере.
