# Деплой и эксплуатация

Документ описывает минимальный рабочий процесс для local/staging/production.
Инфраструктурный владелец — Шухратжон, контракты и переменные окружения — Артём.

## 1. Окружения

| Окружение | `DJANGO_SETTINGS_MODULE` | Особенности |
|---|---|---|
| local | `config.settings.dev` | SQLite по умолчанию, console email, Stripe mock |
| staging | `config.settings.prod` | PostgreSQL, тестовый Discord-сервер, Stripe test mode |
| production | `config.settings.prod` | PostgreSQL, реальные секреты, HTTPS, бэкапы |

Секреты хранятся только в переменных окружения (`.env` локально, secret store на staging/prod).
`.env.example` содержит полный список переменных без значений.

## 2. Локальный запуск

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r backend/requirements/dev.txt
copy .env.example .env
cd backend
python manage.py migrate
python manage.py seed_plans
python manage.py createsuperuser
python manage.py runserver
```

Docker:

```bash
copy .env.example .env
docker compose up --build
```

Compose поднимает PostgreSQL и backend, миграции применяются при старте контейнера.

## 3. Обязательные проверки перед PR

```bash
cd backend
ruff check .
ruff format --check .
python manage.py makemigrations --check --dry-run
python manage.py check
pytest
```

Те же шаги выполняет CI (`.github/workflows/ci.yml`).

## 4. Миграции

- Только через PR, ревью Артёма.
- В CI проверяется отсутствие несозданных миграций.
- На staging/prod: `python manage.py migrate --noinput` перед стартом новой версии.
- Откат — обратная миграция или восстановление из бэкапа; деструктивные миграции
  выполняются в два этапа (сначала код, затем удаление поля).

## 5. Переменные окружения

Критичные:

| Переменная | Назначение |
|---|---|
| `DJANGO_SECRET_KEY` | подпись JWT и Django; ≥32 символов |
| `DATABASE_URL` | PostgreSQL на staging/prod |
| `DISCORD_CLIENT_ID/SECRET` | OAuth2 |
| `DISCORD_REDIRECT_URI` | должен совпадать с Discord Developer Portal |
| `STRIPE_SECRET_KEY/WEBHOOK_SECRET` | биллинг; без них работает mock |
| `EMAIL_*` | SMTP; в dev — console backend |
| `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | домены frontend/backend |

## 6. Бэкапы

- PostgreSQL: ежедневный `pg_dump` + WAL-архив (если доступно), хранение ≥7 дней.
- Проверка восстановления — раз в спринт на staging.
- Секреты и `.env` не попадают в бэкап репозитория.
- Медиа (аватары) — отдельный bucket/volume.

## 7. Мониторинг и логи

- `GET /api/v1/health` — liveness; Runtime heartbeat — в `bot_runtime_state`.
- Логи — JSON/структурированные, с `request_id`; секреты маскируются.
- Sentry — ошибки backend и Runtime.
- Prometheus-метрики: latency, 5xx, размер очереди, количество online-ботов.
- Алерты: 5xx > 1%, heartbeat-просрочки, падение webhook Stripe, ошибки 401 от Discord.

## 8. Деплой

1. PR в `main`, CI зелёный, 1 approve.
2. Тег версии и запись в changelog.
3. Staging: миграции → деплой backend → smoke-тесты → деплой Runtime.
4. Production: миграции → backend → Runtime (graceful drain).
5. Проверка: health, вход, создание бота, запуск, тестовая команда.

## 9. Runtime

- Supervisor запускается отдельным контейнером.
- При деплое — `SIGTERM`, drain активных ботов, затем остановка.
- На одного бота — advisory lock; второй воркер не подхватит того же бота.
- Hot reload конфигурации — через `runtime_commands` + `LISTEN/NOTIFY`.

## 10. Инциденты

- Ошибка токена Discord (401) — бот останавливается, пользователь получает уведомление.
- Массовые 429 — backoff по `Retry-After`, алерт при устойчивом превышении.
- Недоступен Stripe — checkout возвращает mock/ошибку, подписки не меняются.
- Потеря Runtime — backend продолжает работать, статусы ботов становятся `error` по heartbeat.
