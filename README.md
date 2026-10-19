# Constructor Discord Bots

Веб-платформа для визуального создания, настройки и хостинга Discord-ботов.

Репозиторий содержит учебный MVP по ТЗ «Конструктор Discord-ботов». Работы распределены по веткам участников:

| Ветка | Участник | Зона |
|---|---|---|
| `Samoilov` | Артём | Тимлид, backend-core: архитектура, auth, БД, API-контракты, биллинг, админка, CI |
| `sanya` | Саня | Backend-integrations: боты, Discord API, модули, библиотека команд |
| `shuhrat` | Шухратжон | Runtime, интерпретатор сценариев, шаблоны, инфраструктура, QA |
| `danil` | Данила | Frontend: React, редактор графа, редактор эмбедов, экраны |

Подробный план — [`docs/team-plan.md`](docs/team-plan.md).

## Что уже реализовано в backend-core (ветка `Samoilov`)

- каркас Django 5 + DRF + PostgreSQL/SQLite;
- кастомная модель пользователя с UUIDv7 и мягким удалением;
- регистрация по email, подтверждение почты, сброс пароля;
- вход по email/паролю и Discord OAuth2;
- JWT (access 15 минут, refresh 30 дней) с ротацией и httpOnly-cookie;
- список активных сессий и принудительный logout;
- профиль пользователя;
- базовые модели данных: боты, версии, гильдии, шаблоны, модули, библиотека команд, биллинг, уведомления, аудит;
- базовый CRUD ботов и управление запуском (создание `runtime_commands`);
- тарифы, лимиты и тестовый Stripe-сценарий;
- Django Admin;
- единый формат ошибок, `request_id`, курсорная пагинация, throttling;
- OpenAPI-документация;
- Docker Compose, CI, pre-commit, тесты.

## Быстрый старт (локально)

```bash
# из корня репозитория
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -r backend/requirements/dev.txt
copy .env.example .env           # Windows
# cp .env.example .env           # Linux/macOS

cd backend
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Приложение: http://localhost:8000

- Swagger UI: http://localhost:8000/api/docs/
- OpenAPI schema: http://localhost:8000/api/schema/
- Django Admin: http://localhost:8000/admin/

Без `DATABASE_URL` используется SQLite — этого достаточно для локальной разработки и тестов. Для PostgreSQL задайте `DATABASE_URL` в `.env`.

## Docker Compose

```bash
copy .env.example .env
docker compose up --build
```

Поднимаются PostgreSQL и backend. Миграции применяются автоматически при старте контейнера.

## Тесты и линтеры

```bash
cd backend
pytest
ruff check .
ruff format --check .
python manage.py makemigrations --check --dry-run
```

## Переменные окружения

Основные переменные — в [`.env.example`](.env.example). Секреты (Discord client secret, Stripe keys, JWT secret) в репозиторий не коммитятся.

## Структура

```
backend/
  config/            # настройки, urls, wsgi/asgi
  apps/
    common/          # базовые модели, middleware, ошибки, пагинация
    accounts/        # пользователи, OAuth, JWT, сессии, профиль
    bots/            # боты, гильдии, версии, runtime-команды, состояние
    templates_catalog/ # шаблоны и их версии
    modules/         # манифесты модулей
    commands/        # библиотека команд
    billing/         # тарифы, подписки, платежи, лимиты
    notifications/   # уведомления
    audit/           # журнал действий
docs/
  team-plan.md       # распределение задач
  api-contract.md    # контракт API
  adr/               # архитектурные решения
```

## Ветки и PR

- `main` защищена, изменения — только через PR.
- Ветки участников: `Samoilov`, `sanya`, `shuhrat`, `danil`.
- Перед PR: `pytest`, `ruff check .`, `makemigrations --check`.
- Миграции БД ревьюит Артём.
