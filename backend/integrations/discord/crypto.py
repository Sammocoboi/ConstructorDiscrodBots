"""Deprecated token cipher kept for older integration imports.

New code must use :mod:`apps.common.crypto`, which shares
``TOKEN_ENCRYPTION_KEY`` and the ``v1:`` payload format with Runtime. This
wrapper delegates to it when no explicit key is supplied; the old static
fallback key has been removed.
"""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from apps.common.crypto import decrypt_secret, encrypt_secret


def _normalize_key(key: bytes | str) -> bytes:
    if isinstance(key, str):
        try:
            decoded = base64.urlsafe_b64decode(key + "=" * (-len(key) % 4))
        except Exception as exc:
            raise ValueError("key must be url-safe base64") from exc
    else:
        decoded = key
    if len(decoded) != 32:
        raise ValueError(f"AES-256 key must be exactly 32 bytes, got {len(decoded)}")
    return decoded


class TokenCipher:
    def __init__(self, key: bytes | str | None = None):
        self.key = _normalize_key(key) if key is not None else None

    def encrypt(self, plain_token: str) -> str:
        if not plain_token:
            return ""
        if self.key is None:
            return encrypt_secret(plain_token)
        nonce = os.urandom(12)
        ciphertext = AESGCM(self.key).encrypt(nonce, plain_token.encode("utf-8"), None)
        return "v1:" + base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, encrypted_token: str) -> str:
        if not encrypted_token:
            return ""
        if self.key is None:
            return decrypt_secret(encrypted_token)
        if not encrypted_token.startswith("v1:"):
            raise ValueError("unsupported token format")
        combined = base64.urlsafe_b64decode(encrypted_token[3:])
        nonce, ciphertext = combined[:12], combined[12:]
        return AESGCM(self.key).decrypt(nonce, ciphertext, None).decode("utf-8")

    @staticmethod
    def mask_token(plain_or_encrypted: str) -> str:
        if not plain_or_encrypted:
            return ""
        clean = plain_or_encrypted.strip()
        if len(clean) <= 12:
            return "********"
        prefix = clean[:6]
        suffix = clean[-4:]
        return f"{prefix}••••••••••••••••••••{suffix}"


default_cipher = TokenCipher()
