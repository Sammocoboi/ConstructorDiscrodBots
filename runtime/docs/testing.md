# Testing / QA

## Команды

```bash
cd runtime
.venv/Scripts/python -m pytest -q     # Windows
python -m pytest -q                    # Linux/macOS
ruff check .
mypy runtime
```

Текущее состояние: **64 теста, все проходят**; `ruff` и `mypy --strict`
зелёные.

## Что покрыто

| Файл | Проверяет |
|---|---|
| `tests/test_interpreter.py` | send_message, dry-run, if, random_chance, set_variable, циклы, лимиты, run_flow depth, unknown block, registry |
| `tests/test_expressions.py` | операторы, JSONLogic, переменные, вложенные значения |
| `tests/test_validation.py` | обязательные параметры, типы, ветки, циклы, недостижимые узлы, секреты, embed-лимиты |
| `tests/test_content.py` | 15 манифестов и 8 шаблонов: JSON, поля, уникальность, валидация |
| `tests/test_templates.py` | системный каталог, импорт/экспорт, share-link, TTL, подпись, фильтры |
| `tests/test_versions.py` | черновик/публикация/архив, diff, откат, лимит 30 |
| `tests/test_scheduler.py` | cron-парсинг, next_after, due jobs, ошибки handler |
| `tests/test_supervisor.py` | старт/stop, авторестарт, suspended, capacity, commands, heartbeat |
| `tests/test_crypto_health.py` | AES-GCM, маска, health endpoints, metrics |

## Ручной smoke на Discord

1. Создать тестовое приложение и бота, включить нужные intents.
2. Пригласить бота на тестовый сервер.
3. Записать токен и `guild_id` в безопасное хранилище (не в git).
4. Создать бота в БД с `desired_state='running'` и конфигом из
   `content/templates/utility.json`.
5. Запустить Runtime, проверить `/health`, `/`, статус `online`.
6. Выполнить `/ping` (или команду из шаблона), проверить ответ.
7. Изменить конфиг, опубликовать версию, отправить `reload`, проверить без
   рестарта.
8. Отправить `stop`, проверить `stopped`; `start` — снова `online`.
9. Проверить `join_member`: новый участник получает приветствие.
10. Проверить `bots_runtimecommand` и `bots_botruntimestate`.

## Регрессия шаблонов

`tests/test_content.py` автоматически валидирует все 8 шаблонов. При изменении
шаблона:

```bash
pytest tests/test_content.py -q
```

Дополнительно вручную: создать бота из шаблона, пройти flow в dry-run и на
тестовом сервере, проверить отсутствие секретов.

## Не покрыто (следующий этап)

- Интеграционные тесты с реальным PostgreSQL (миграция, LISTEN/NOTIFY,
  advisory lock, SKIP LOCKED).
- Живой Discord Gateway (нужен тестовый токен/сервер).
- E2E Playwright (зона Данилы) — сценарии «бот за 5 минут», публикация flow.
- Нагрузка k6/Locust: 100–1000 ботов, 200 блоков, 30 секунд.
- Contract-тесты backend ↔ Runtime (схема `bots_runtimecommand` и
  `bots_botruntimestate`).

## Definition of Done для Runtime-задачи

- [ ] `ruff`, `mypy`, `pytest` зелёные.
- [ ] Новый блок/поведение покрыты unit-тестом.
- [ ] Обновлён `docs/` при изменении контракта.
- [ ] Нет секретов в коде/логах/шаблонах.
- [ ] Проверено на тестовом Discord-сервере (для gateway-фич).
- [ ] Учтены лимиты Discord и таймауты.
- [ ] Обработаны пустое/ошибочное состояние и graceful shutdown.
