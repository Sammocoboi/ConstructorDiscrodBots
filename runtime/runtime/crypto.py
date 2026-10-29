from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PREFIX = "v1:"
KEY_BYTES = 32

# Backend uses "v1:" prefix with urlsafe base64
_V1_PREFIX = "v1:"


def _b64decode(value: str, *, what: str) -> bytes:
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except Exception as exc:
        raise ValueError(f"{what} must be url-safe base64") from exc
    return decoded


def normalize_key(raw_key: str | bytes | None) -> bytes:
    """Decode the shared TOKEN_ENCRYPTION_KEY.

    Backend and Runtime use the same format: URL-safe base64 of exactly 32
    bytes. There is deliberately no fallback key and no padding/truncation:
    a misconfigured deployment must fail loudly instead of silently writing
    tokens that the other service cannot read.
    """

    if raw_key is None or raw_key == "":
        raise ValueError("TOKEN_ENCRYPTION_KEY is required")
    if isinstance(raw_key, bytes):
        if len(raw_key) == KEY_BYTES:
            return raw_key
        raise ValueError("TOKEN_ENCRYPTION_KEY must be exactly 32 bytes")
    decoded = _b64decode(raw_key.strip(), what="TOKEN_ENCRYPTION_KEY")
    if len(decoded) != KEY_BYTES:
        raise ValueError("TOKEN_ENCRYPTION_KEY must decode to 32 bytes")
    return decoded


class TokenCipher:
    """AES-256-GCM token cipher compatible with backend ``apps.common.crypto``."""

    def __init__(self, key: bytes | str | None = None) -> None:
        normalized = normalize_key(key)
        self._aesgcm = AESGCM(normalized)

    def encrypt(self, plain_token: str) -> str:
        if not plain_token:
            return ""
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, plain_token.encode("utf-8"), None)
        payload = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
        return f"{PREFIX}{payload}"

    def decrypt(self, encrypted_token: str) -> str:
        if not encrypted_token:
            return ""
        if not encrypted_token.startswith(PREFIX):
            raise ValueError("unsupported token format: expected v1: prefix")
        combined = _b64decode(
            encrypted_token[len(PREFIX) :],
            what="encrypted token",
        )
        if len(combined) < 12 + 16:
            raise ValueError("encrypted token is too short")
        nonce, ciphertext = combined[:12], combined[12:]
        return self._aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")

    @staticmethod
    def mask(plain_token: str) -> str:
        if not plain_token:
            return ""
        if len(plain_token) <= 12:
            return "********"
        return f"{plain_token[:6]}{'*' * 20}{plain_token[-4:]}"
