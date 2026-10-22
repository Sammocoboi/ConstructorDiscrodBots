from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from runtime.interpreter.context import Context

log = logging.getLogger("runtime.interpreter.registry")

DEFAULT_BLOCKS_DIR = Path(__file__).resolve().parents[2] / "content" / "blocks"

Handler = Callable[[dict[str, Any], "Context"], Awaitable[dict[str, Any] | str | None]]


class BlockRegistryError(ValueError):
    pass


class UnknownBlockError(BlockRegistryError):
    pass


class BlockRegistry:
    def __init__(self, blocks_dir: Path | None = None) -> None:
        self._blocks_dir = blocks_dir or DEFAULT_BLOCKS_DIR
        self._manifests: dict[str, dict[str, Any]] = {}
        self._handlers: dict[str, Handler] = {}

    @property
    def blocks_dir(self) -> Path:
        return self._blocks_dir

    @property
    def manifests(self) -> Mapping[str, dict[str, Any]]:
        return dict(self._manifests)

    def load_manifests(self) -> int:
        if not self._blocks_dir.exists():
            raise BlockRegistryError(f"blocks directory does not exist: {self._blocks_dir}")

        loaded = 0
        for path in sorted(self._blocks_dir.glob("*.json")):
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise BlockRegistryError(f"invalid JSON in {path.name}: {exc}") from exc
            if not isinstance(manifest, dict):
                raise BlockRegistryError(f"{path.name}: manifest must be an object")
            block_type = manifest.get("type")
            if not isinstance(block_type, str) or not block_type:
                raise BlockRegistryError(f"{path.name}: type is required")
            if block_type in self._manifests:
                raise BlockRegistryError(f"duplicate block type: {block_type}")
            manifest.setdefault("params", {})
            manifest.setdefault("category", "action")
            manifest.setdefault("inputs", ["flow"])
            manifest.setdefault("outputs", ["flow"])
            self._manifests[block_type] = manifest
            loaded += 1
        log.info("Loaded %s block manifests from %s", loaded, self._blocks_dir)
        return loaded

    def register(self, block_type: str, handler: Handler) -> None:
        if block_type not in self._manifests:
            raise UnknownBlockError(f"block {block_type} has no manifest")
        self._handlers[block_type] = handler

    def get_handler(self, block_type: str) -> Handler:
        try:
            return self._handlers[block_type]
        except KeyError as exc:
            raise UnknownBlockError(f"no handler registered for block {block_type}") from exc

    def get_manifest(self, block_type: str) -> dict[str, Any]:
        try:
            return self._manifests[block_type]
        except KeyError as exc:
            raise UnknownBlockError(f"unknown block type: {block_type}") from exc

    def has_handler(self, block_type: str) -> bool:
        return block_type in self._handlers
