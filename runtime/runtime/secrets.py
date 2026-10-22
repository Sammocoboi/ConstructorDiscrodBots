from __future__ import annotations

import re
from typing import Any

_SECRET_KEY_RE = re.compile(
    r"(?:^|_)(?:token|secret|password|passwd|api[_-]?key|private[_-]?key|authorization|cookie)$",
    re.IGNORECASE,
)
_DISCORD_TOKEN_RE = re.compile(r"[MN][A-Za-z\d]{23,}\.[\w-]{6}\.[\w-]{27,}")
_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{16,}", re.IGNORECASE)


def find_secrets(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            current = f"{path}.{key_text}" if path else key_text
            if _SECRET_KEY_RE.search(key_text) and item not in (None, "", {}, []):
                findings.append(f"{current}: secret-like key")
            findings.extend(find_secrets(item, current))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(find_secrets(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        if _DISCORD_TOKEN_RE.search(value):
            findings.append(f"{path or '<root>'}: Discord token detected")
        if _BEARER_RE.search(value):
            findings.append(f"{path or '<root>'}: bearer token detected")
    return findings
