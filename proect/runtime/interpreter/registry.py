import json
from pathlib import Path
from typing import Any, Callable, Awaitable

BLOCKS_DIR = Path(__file__).resolve().parents[2] / "content" / "blocks"

Handler = Callable[[dict[str, Any], "Context"], Awaitable[dict[str, Any]]]


class BlockRegistry:
    def __init__(self) -> None:
        self._manifests: dict[str, dict[str, Any]] = {}
        self._handlers: dict[str, Handler] = {}

    def load_manifests(self) -> None:
        for path in BLOCKS_DIR.glob("*.json"):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            self._manifests[manifest["type"]] = manifest

    def register(self, block_type: str, handler: Handler) -> None:
        if block_type not in self._manifests:
            raise ValueError(f"Block {block_type} has no manifest")
        self._handlers[block_type] = handler

    def get_handler(self, block_type: str) -> Handler:
        if block_type not in self._handlers:
            raise ValueError(f"No handler for {block_type}")
        return self._handlers[block_type]

    def manifest(self, block_type: str) -> dict[str, Any]:
        return self._manifests[block_type]