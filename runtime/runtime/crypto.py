from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DEFAULT_KEY = b"antigravity_discord_bot_aes256_k"


def normalize_key(raw_key: str | None) -> bytes:
    if not raw_key:
        return DEFAULT_KEY
    try:
        decoded = base64.b64decode(raw_key, validate=True)
    except Exception:
        decoded = raw_key.encode("utf-8")
    if len(decoded) != 32:
        decoded = decoded.ljust(32, b"0")[:32]
    return decoded


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
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, encrypted_token: str) -> str:
        if not encrypted_token:
            return ""
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
