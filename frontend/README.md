# BotForge Frontend

Веб-интерфейс конструктора Discord-ботов: дашборд, управление ботами и гильдиями, модули, команды, визуальный редактор сценариев, сообщения, шаблоны, биллинг, аккаунт и справка.

## Стек

- React 18 + TypeScript, Vite
- React Router 6
- TanStack Query
- Zustand
- react-hook-form + zod
- i18next (RU/EN)
- Mantine 7 + Tabler Icons
- `@xyflow/react` для редактора сценариев
- Vitest + Testing Library, Playwright

## Быстрый старт

```bash
npm install
cp .env.example .env
npm run dev
```

Приложение откроется на `http://localhost:5173`.

Демо-доступ (mock-режим): `danila@example.com` / `password123`. На странице входа поля уже заполнены.

## Скрипты

| Команда | Назначение |
| --- | --- |
| `npm run dev` | Dev-сервер Vite |
| `npm run build` | Проверка типов и production-сборка |
| `npm run preview` | Просмотр сборки |
| `npm run typecheck` | `tsc -b --noEmit` |
| `npm run lint` | ESLint |
| `npm run test` | Unit-тесты Vitest |
| `npm run test:watch` | Vitest в watch-режиме |
| `npm run test:e2e` | Playwright smoke-тесты |
| `npm run api:types` | Генерация типов из OpenAPI |

## Режимы API

По умолчанию включён mock-бэкенд (`VITE_USE_MOCKS=true`). Данные хранятся в `localStorage` под ключом `botforge.mock.database.v1`; сессия — `botforge.auth`.

Для работы с Django API:

```env
VITE_USE_MOCKS=false
VITE_API_URL=/api/v1
```

Vite проксирует `/api` на `VITE_PROXY_TARGET` (по умолчанию `http://localhost:8000`).

## Структура

```
src/
  features/        экраны по доменам (auth, bots, modules, commands, flows, messages,
                   templates, billing, account, notifications, help, dashboard, landing)
  layouts/         AppLayout, AuthLayout, BotLayout, CommandPalette
  shared/
    api/           типы, mockApi, httpApi, query hooks, ошибки
    components/    общие компоненты и состояния
    i18n/          переводы RU/EN
    lib/           валидация, форматирование, граф сценариев
    mocks/         seed и хранилище mock-базы
    stores/        auth/ui/theme
  theme/           токены Mantine, глобальные стили
e2e/               Playwright smoke-тесты
```

## Основные маршруты

- `/` — лендинг
- `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`, `/auth/callback/discord`
- `/app` — дашборд
- `/app/bots/new` — мастер создания бота (`?templateId=...` подставляет шаблон)
- `/app/bots/:botId/{overview,status,profile,guilds,modules,commands,flows,messages}`
- `/app/templates`, `/app/templates/mine`
- `/app/billing`, `/app/account`, `/app/notifications`, `/app/help`

## Тесты

```bash
npm run test
npx playwright install chromium
npm run test:e2e
```

E2E поднимает dev-сервер автоматически. Если приложение уже запущено, задайте `PLAYWRIGHT_BASE_URL=http://localhost:5173`, чтобы использовать его.
