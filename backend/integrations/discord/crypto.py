"""
Шифрование токенов ботов и OAuth-токенов методом AES-256-GCM.
Соответствие ТЗ §4.2 (FR-2.2), §10.1 и задаче SAN-3.
"""

import os
import base64
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class TokenCipher:
    """
    Класс для симметричного шифрования и дешифрования токенов ботов
    с использованием стандарта AES-256-GCM (длина ключа 32 байта).
    """

    def __init__(self, key: Optional[bytes] = None):
        if key is None:
            # Извлекаем ключ из переменной окружения BOT_TOKEN_ENCRYPTION_KEY
            # или используем дефолтный ключ для окружения разработки.
            env_key = os.environ.get("BOT_TOKEN_ENCRYPTION_KEY")
            if env_key:
                # Если передан base64-ключ
                try:
                    self.key = base64.b64decode(env_key)
                except Exception:
                    self.key = env_key.encode("utf-8").ljust(32, b"0")[:32]
            else:
                # 32-байтный статический ключ по умолчанию для dev/test
                self.key = b"antigravity_discord_bot_aes256_k"
        else:
            self.key = key

        if len(self.key) != 32:
            raise ValueError(f"Длина ключа AES-256 должна составлять ровно 32 байта, получено {len(self.key)}")

        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plain_token: str) -> str:
        """
        Шифрует токен бота.
        Возвращает строку формата base64(nonce + ciphertext + tag).
        """
        if not plain_token:
            return ""
        # 12 байт nonce для стандарта AES-GCM
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plain_token.encode("utf-8"), None)
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode("utf-8")

    def decrypt(self, encrypted_token: str) -> str:
        """
        Расшифровывает токен бота.
        """
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
        """
        Маскирует токен бота для безопасного отображения в UI и API.
        Пример: "MTIwOTg...****...xyz"
        Никогда не выдает открытый токен.
        """
        if not plain_or_encrypted:
            return ""
        clean = plain_or_encrypted.strip()
        if len(clean) <= 12:
            return "********"
        prefix = clean[:6]
        suffix = clean[-4:]
        return f"{prefix}••••••••••••••••••••{suffix}"


# Singleton экземпляр для приложения
default_cipher = TokenCipher()
