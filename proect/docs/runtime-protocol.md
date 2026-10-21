# Runtime Protocol v1

## Таблицы

### runtime_commands
| колонка | тип | описание |
|---|---|---|
| id | uuid | PK |
| bot_id | uuid | FK bots |
| command | text | start / stop / restart / reload |
| status | text | pending / acked / done / failed |
| requested_by | uuid | FK users |
| created_at | timestamptz | |
| acked_at | timestamptz | |

### bot_runtime_state
| колонка | тип | описание |
|---|---|---|
| bot_id | uuid | PK |
| worker_id | text | |
| status | text | stopped / starting / online / error / suspended |
| latency_ms | int | ping |
| heartbeat_at | timestamptz | обновляется каждые 15 сек |

## Доставка команд

1. API пишет строку в `runtime_commands` (status=pending).
2. `NOTIFY runtime_commands_channel, '<bot_id>'`.
3. Runtime слушает `LISTEN runtime_commands_channel`, забирает команду,
   ставит status=acked, выполняет, ставит status=done/failed.
4. Страховка: polling `runtime_commands` раз в 30 сек.

## Блокировка

`pg_advisory_lock(hashtext(bot_id))` с lease; продление каждые 10 сек.
Один бот — ровно на одном воркере. Защита от двойных ответов.

## Heartbeat

Каждые 15 сек воркер обновляет `bot_runtime_state.heartbeat_at`.
Бот без heartbeat > 60 сек считается недоступным (API).

## Коды ошибок Runtime

- `invalid_token` — Discord 401
- `missing_intents` — не включены Privileged Intents
- `missing_permissions` — не хватает прав в гильдии
- `overloaded` — очередь событий переполнена