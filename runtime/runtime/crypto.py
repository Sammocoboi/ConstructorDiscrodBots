from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DEFAULT_KEY = b"antigravity_discord_bot_aes256_k"

# Backend uses "v1:" prefix with urlsafe base64
_V1_PREFIX = "v1:"


def normalize_key(raw_key: str | None) -> bytes:
    if not raw_key:
        return DEFAULT_KEY
    # Try urlsafe base64 first (backend format), then standard base64
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            decoded = decoder(raw_key.encode("utf-8") if isinstance(raw_key, str) else raw_key)
            if len(decoded) == 32:
                return decoded
        except Exception:
            continue
    # Last resort: treat as raw bytes
    raw_bytes = raw_key.encode("utf-8") if isinstance(raw_key, str) else raw_key
    if len(raw_bytes) != 32:
        raw_bytes = raw_bytes.ljust(32, b"0")[:32]
    return raw_bytes


class TokenCipher:
    def __init__(self, key: bytes | str | None = None) -> None:
        if isinstance(key, str):
            key = normalize_key(key)
        elif key is None:
            key = DEFAULT_KEY
        if len(key) != 32:
            raise ValueError("AES-256-GCM requires a 32-byte key")
        self._aesgcm = AESGCM(key)

    def encrypt(self, plain_token: str) -> str:
        if not plain_token:
            return ""
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, plain_token.encode("utf-8"), None)
        # Produce v1: prefixed format compatible with backend
        return _V1_PREFIX + base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, encrypted_token: str) -> str:
        if not encrypted_token:
            return ""
        # Handle v1: prefix from backend
        if encrypted_token.startswith(_V1_PREFIX):
            payload = encrypted_token[len(_V1_PREFIX):]
            combined = base64.urlsafe_b64decode(payload.encode("ascii"))
        else:
            # Legacy format: standard base64 without prefix
            combined = base64.b64decode(encrypted_token.encode("ascii"))
        if len(combined) < 28:
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

