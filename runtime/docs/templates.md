# Шаблоны

Системные шаблоны лежат в `content/templates/*.json`, загружаются
`TemplateService` и валидируются тем же конфигом, что и боты. Пользовательские
шаблоны хранятся в таблице `templates`.

## Системные шаблоны (8)

| Файл | slug | Категория | Flows |
|---|---|---|---|
| `community.json` | `community-server` | community | 3 |
| `moderation.json` | `moderation` | moderation | 2 |
| `support.json` | `support-tickets` | support | 2 |
| `roles.json` | `roles-and-selfroles` | roles | 2 |
| `economy.json` | `economy` | economy | 2 |
| `games.json` | `mini-games` | games | 2 |
| `giveaways.json` | `giveaways` | giveaways | 2 |
| `utility.json` | `utility` | utility | 3 |

Каждый шаблон — валидный `config` с `schema_version: 1`, профилем, командами и
flows. Секреты запрещены.

## Формат

```json
{
  "id": "uuid",
  "slug": "community-server",
  "title": "Сервер сообщества",
  "description": "Приветствия, роли, правила",
  "category": "community",
  "version": "1.0.0",
  "author": "Constructor",
  "is_system": true,
  "config": {"schema_version": 1, "profile": {}, "flows": [], "commands": []}
}
```

Правила:

- `slug`: `^[a-z0-9]+(?:-[a-z0-9]+)*$`, уникален среди системных;
- `title` не пустой;
- `category`: `community`, `moderation`, `support`, `roles`, `economy`, `games`,
  `giveaways`, `utility`, `custom`;
- `version`: semver;
- `config`: проходит `validate_config` (2 МБ, блоки, лимиты, без секретов).

## Импорт и экспорт

- `export_template(template)` — JSON с сортировкой ключей.
- `import_template(raw, owner_id=...)` — новый `id`, `owner_id`, `is_system=false`,
  повторная валидация.
- `TemplateService.save_user_template(owner_id, payload, template_id=...)` —
  сохраняет в репозиторий.
- `load_system_templates(directory)` — при старте; дубли slug и ошибки JSON
  останавливают загрузку.

## Share-link

```python
link = service.share_link(template)
resolved = service.resolve_share(link)
```

Токен: `base64url(payload).base64url(HMAC-SHA256(payload, secret))`, payload —
`{v:1, exp, template}`. TTL по умолчанию 7 дней. Ссылка:
`<base_url>/templates/shared?token=...` (поддерживается и fragment).

- Подпись проверяется `hmac.compare_digest`;
- просроченный/битый токен → `TemplateError`;
- при импорте создаётся новый `id`, системность снимается;
- `secret` обязателен, пустой запрещён.

## API (зона backend)

Предлагаемые эндпоинты:

- `GET /api/v1/templates?category=&q=` — системные + свои;
- `GET /api/v1/templates/{id}`;
- `POST /api/v1/templates` — создать из конфига;
- `POST /api/v1/templates/import` — JSON;
- `GET /api/v1/templates/{id}/export`;
- `POST /api/v1/templates/{id}/share`;
- `POST /api/v1/templates/shared/resolve` — токен/ссылка;
- `DELETE /api/v1/templates/{id}` — только свой.

## Ограничения

- 2 МБ на конфиг;
- секреты и Discord-токены запрещены;
- нельзя перезаписать системный шаблон;
- `slug` уникален в пределах владельца;
- версии шаблона — semver, история версий пока на уровне поля `version`.
