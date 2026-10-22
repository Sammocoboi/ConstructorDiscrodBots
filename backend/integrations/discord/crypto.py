
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class TokenCipher:

    def __init__(self, key: bytes | None = None):
        if key is None:
            env_key = os.environ.get("BOT_TOKEN_ENCRYPTION_KEY")
            if env_key:
                try:
                    self.key = base64.b64decode(env_key)
                except Exception:
                    self.key = env_key.encode("utf-8").ljust(32, b"0")[:32]
            else:
                self.key = b"antigravity_discord_bot_aes256_k"
        else:
            self.key = key

        if len(self.key) != 32:
            raise ValueError(f"Длина ключа AES-256 должна составлять ровно 32 байта, получено {len(self.key)}")

        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plain_token: str) -> str:
        if not plain_token:
            return ""
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plain_token.encode("utf-8"), None)
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode("utf-8")

    def decrypt(self, encrypted_token: str) -> str:
        if not encrypted_token:
            return ""
        combined = base64.b64decode(encrypted_token.encode("utf-8"))
        if len(combined) < 28:
            raise ValueError("Некорректная длина зашифрованного токена")
        nonce = combined[:12]
        ciphertext = combined[12:]
        decrypted_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted_bytes.decode("utf-8")

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
