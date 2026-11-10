# Локальный показ с Discord без Docker

VPS и Docker не нужны. Нужны Python 3.12+, Node.js/npm и запущенный PostgreSQL
16+. Backend умеет работать с SQLite для обычной разработки, но Discord Runtime
использует PostgreSQL — без него живой бот не запустится.

## Установка зависимостей

Из корня репозитория в PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements/dev.txt
python -m pip install -e .\runtime
cd frontend
npm ci
Copy-Item .env.example .env
cd ..
```

Установите PostgreSQL и запустите его службу. Создайте базу `constructor` и
пользователя для локального показа. Например, через `psql` от пользователя
`postgres`:

```powershell
psql -h 127.0.0.1 -U postgres -c "CREATE USER constructor WITH PASSWORD 'constructor';"
psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE constructor OWNER constructor;"
```

Если роль или база уже существуют, повторно создавать их не нужно. Поменяйте
пароль в командах и URL ниже, если используете другой.

## Настройка `.env`

Скопируйте `.env.example` в корне репозитория в `.env` и задайте параметры базы:

```dotenv
DATABASE_URL=postgresql://constructor:constructor@127.0.0.1:5432/constructor
FRONTEND_URL=http://localhost:5173
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
DISCORD_REDIRECT_URI=http://localhost:8000/api/v1/auth/discord/callback
TOKEN_ENCRYPTION_KEY=
```

Для входа через Discord заполните OAuth Client ID/Secret и добавьте в Discord
Developer Portal точный redirect URI из `.env`. Без OAuth-ключей войдите по
email и паролю. Сгенерируйте `TOKEN_ENCRYPTION_KEY` командой из комментария в
`.env.example`, затем внесите одно и то же значение в корневой `.env` и
`runtime/.env`.

Создайте `runtime/.env` на основе `runtime/infra/.env.example`. В нём задайте
тот же `DATABASE_URL` и `TOKEN_ENCRYPTION_KEY`, что в корневом `.env`; для
локального запуска используйте `127.0.0.1`, а не `host.docker.internal`.

## Подготовка базы и запуск

Один раз выполните из корня репозитория:

```powershell
cd backend
python manage.py migrate
python manage.py seed_plans
python manage.py seed_modules
python manage.py seed_commands
python manage.py seed_templates
psql -h 127.0.0.1 -U constructor -d constructor -v ON_ERROR_STOP=1 -f ..\runtime\infra\migrations\001_runtime.sql
cd ..
```

Запустите компоненты в трёх отдельных терминалах из корня репозитория:

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

```powershell
cd runtime
..\.venv\Scripts\python.exe -m runtime.main
```

```powershell
cd frontend
npm run dev -- --host 127.0.0.1
```

Откройте <http://localhost:5173>. Оставьте все три терминала и PostgreSQL
запущенными на время показа.

## Проверка в Discord

Создайте тестовое Application и Bot в Discord Developer Portal, скопируйте
токен и вставьте его только в форму приложения. Добавьте бота на тестовый
сервер, создайте сценарий со slash-командой `/hello`, опубликуйте сценарий и
запустите бота. Токен бота — отдельный от OAuth Client ID/Secret; не коммитьте
его и не отправляйте в чат.
