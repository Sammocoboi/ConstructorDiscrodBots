"""Symmetric encryption for secrets that must be stored in the database.

Bot tokens and OAuth tokens are never returned by the API and never written to
logs. The key is derived from ``SECRET_KEY`` for local development; in
production set a dedicated ``TOKEN_ENCRYPTION_KEY`` (base64, 32 bytes).
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

_PREFIX = "v1:"


def _key() -> bytes:
    raw = os.getenv("TOKEN_ENCRYPTION_KEY", "").strip()
    if raw:
        try:
            padded = raw + "=" * (-len(raw) % 4)
            key = base64.urlsafe_b64decode(padded)
        except Exception as exc:  # pragma: no cover - configuration error
            raise ValueError("TOKEN_ENCRYPTION_KEY must be url-safe base64") from exc
        if len(key) != 32:
            raise ValueError("TOKEN_ENCRYPTION_KEY must decode to 32 bytes")
        return key
    if settings.DEBUG or settings.SETTINGS_MODULE.endswith(".dev"):
        # Local development convenience only. Production must share an explicit
        # key with Runtime; deriving from SECRET_KEY would silently create
        # tokens Runtime cannot decrypt.
        return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    raise ValueError("TOKEN_ENCRYPTION_KEY is required in production")


def encrypt_secret(value: str) -> str:
    if not value:
        return ""
    nonce = os.urandom(12)
    ciphertext = AESGCM(_key()).encrypt(nonce, value.encode("utf-8"), None)
    return _PREFIX + base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    if not value.startswith(_PREFIX):
        raise ValueError("Unsupported secret format")
    payload_b64 = value[len(_PREFIX) :]
    payload = base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4))
    nonce, ciphertext = payload[:12], payload[12:]
    return AESGCM(_key()).decrypt(nonce, ciphertext, None).decode("utf-8")


def mask_secret(value: str) -> str:
    if not value:
        return ""
    tail = value[-4:] if len(value) >= 4 else ""
    return f"••••••••{tail}"
