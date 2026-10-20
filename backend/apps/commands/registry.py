"""
Реестр библиотеки готовых команд, разрешение зависимостей и конфликтов имён.
Соответствие ТЗ §4.4 (FR-4.1, FR-4.2, FR-4.3, FR-4.4) и задаче SAN-8.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from rest_framework.exceptions import NotFound, ValidationError

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
COMMANDS_DIR = BASE_DIR / "content" / "commands"


class CommandLibraryRegistry:
    """
    Загрузчик и поисковый сервис для библиотеки 70+ готовых команд.
    """
    _cache: Optional[Dict[str, Dict[str, Any]]] = None

    @classmethod
    def load_commands(cls, force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
        if cls._cache is not None and not force_reload:
            return cls._cache

        commands_map: Dict[str, Dict[str, Any]] = {}
        if COMMANDS_DIR.exists():
            for json_file in COMMANDS_DIR.glob("*/*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        slug = data.get("slug")
                        if slug:
                            commands_map[slug] = data
                except Exception as e:
                    continue

        cls._cache = commands_map
        return cls._cache

    @classmethod
    def list_commands(
        cls,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        all_cmds = list(cls.load_commands().values())
        filtered = all_cmds

        if category:
            filtered = [c for c in filtered if c.get("category") == category]

        if search:
            query = search.lower().strip()
            filtered = [
                c for c in filtered
                if query in c.get("name", "").lower()
                or query in c.get("title", "").lower()
                or query in c.get("description", "").lower()
            ]

        return filtered

    @classmethod
    def get_by_slug(cls, slug: str) -> Optional[Dict[str, Any]]:
        return cls.load_commands().get(slug)

    @classmethod
    def get_categories(cls) -> List[Dict[str, Any]]:
        """Возвращает категории с количеством команд в каждой."""
        all_cmds = cls.load_commands().values()
        cat_counts: Dict[str, int] = {}
        for c in all_cmds:
            cat = c.get("category", "other")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        result = []
        for cat, count in sorted(cat_counts.items()):
            result.append({"category": cat, "count": count})
        return result

    @classmethod
    def resolve_dependencies(cls, command_slug: str) -> Dict[str, Any]:
        """
        Проверяет и возвращает зависимости команды (FR-4.3):
        например, команда /warn требует модуль moderation.
        """
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
            "needs_module_activation": bool(required_module)
        }

    @classmethod
    def check_name_conflict(
        cls,
        existing_command_names: List[str],
        candidate_name: str
    ) -> Dict[str, Any]:
        """
        Проверка конфликтов имён команд при добавлении в проект (FR-4.3).
        Если имя уже занято, предлагает альтернативное имя и варианты действий.
        """
        candidate_lower = candidate_name.lower().strip()
        has_conflict = candidate_lower in [n.lower().strip() for n in existing_command_names]

        suggested_name = candidate_name
        if has_conflict:
            counter = 2
            while f"{candidate_lower}_{counter}" in [n.lower().strip() for n in existing_command_names]:
                counter += 1
            suggested_name = f"{candidate_name}_{counter}"

        return {
            "has_conflict": has_conflict,
            "original_name": candidate_name,
            "suggested_name": suggested_name,
            "action_choices": ["replace", "rename", "skip"] if has_conflict else ["add"]
        }
