import json
from pathlib import Path
from typing import Any

from rest_framework.exceptions import NotFound

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
COMMANDS_DIR = BASE_DIR / "content" / "commands"


class CommandLibraryRegistry:
    _cache: dict[str, dict[str, Any]] | None = None

    @classmethod
    def load_commands(cls, force_reload: bool = False) -> dict[str, dict[str, Any]]:
        if cls._cache is not None and not force_reload:
            return cls._cache

        commands_map: dict[str, dict[str, Any]] = {}
        if COMMANDS_DIR.exists():
            for json_file in COMMANDS_DIR.glob("*/*.json"):
                try:
                    with open(json_file, encoding="utf-8") as f:
                        data = json.load(f)
                        slug = data.get("slug")
                        if slug:
                            commands_map[slug] = data
                except Exception:
                    continue

        cls._cache = commands_map
        return cls._cache

    @classmethod
    def list_commands(
        cls, category: str | None = None, search: str | None = None
    ) -> list[dict[str, Any]]:
        all_cmds = list(cls.load_commands().values())
        filtered = all_cmds

        if category:
            filtered = [c for c in filtered if c.get("category") == category]

        if search:
            query = search.lower().strip()
            filtered = [
                c
                for c in filtered
                if query in c.get("name", "").lower()
                or query in c.get("title", "").lower()
                or query in c.get("description", "").lower()
            ]

        return filtered

    @classmethod
    def get_by_slug(cls, slug: str) -> dict[str, Any] | None:
        return cls.load_commands().get(slug)

    @classmethod
    def get_categories(cls) -> list[dict[str, Any]]:
        all_cmds = cls.load_commands().values()
        cat_counts: dict[str, int] = {}
        for c in all_cmds:
            cat = c.get("category", "other")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        result = []
        for cat, count in sorted(cat_counts.items()):
            result.append({"category": cat, "count": count})
        return result

    @classmethod
    def resolve_dependencies(cls, command_slug: str) -> dict[str, Any]:
        cmd = cls.get_by_slug(command_slug)
        if not cmd:
            raise NotFound(f"Команда '{command_slug}' не найдена в библиотеке")

        required_module = cmd.get("required_module")
        required_intents = cmd.get("required_intents", [])
        required_permissions = cmd.get("required_permissions", 0)

        return {
            "command_slug": command_slug,
            "required_module": required_module,
            "required_intents": required_intents,
            "required_permissions": required_permissions,
            "needs_module_activation": bool(required_module),
        }

    @classmethod
    def check_name_conflict(
        cls, existing_command_names: list[str], candidate_name: str
    ) -> dict[str, Any]:
        candidate_lower = candidate_name.lower().strip()
        has_conflict = candidate_lower in [n.lower().strip() for n in existing_command_names]

        suggested_name = candidate_name
        if has_conflict:
            counter = 2
            while f"{candidate_lower}_{counter}" in [
                n.lower().strip() for n in existing_command_names
            ]:
                counter += 1
            suggested_name = f"{candidate_name}_{counter}"

        return {
            "has_conflict": has_conflict,
            "original_name": candidate_name,
            "suggested_name": suggested_name,
            "action_choices": ["replace", "rename", "skip"] if has_conflict else ["add"],
        }
