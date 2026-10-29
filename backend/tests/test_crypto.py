import pytest

from integrations.discord.crypto import TokenCipher, default_cipher


def test_token_encryption_and_decryption():
    cipher = TokenCipher()
    raw_token = "MTIxMjM0NTY3ODkwMTIzNDU2Nw.Gxyz12.SampleDiscordBotSecretToken12345"

    encrypted = cipher.encrypt(raw_token)
    assert encrypted != raw_token
    assert len(encrypted) > 20

    decrypted = cipher.decrypt(encrypted)
    assert decrypted == raw_token


def test_token_masking():
    raw_token = "MTIxMjM0NTY3ODkwMTIzNDU2Nw.Gxyz12.SampleDiscordBotSecretToken12345"
    masked = default_cipher.mask_token(raw_token)

    assert "MTIxMj" in masked
    assert "2345" in masked
    assert "SampleDiscordBotSecretToken" not in masked
    assert "••••" in masked


def test_empty_token():
    assert default_cipher.encrypt("") == ""
    assert default_cipher.decrypt("") == ""
    assert default_cipher.mask_token("") == ""


def test_invalid_key_length():
    with pytest.raises(ValueError):
        TokenCipher(key=b"too_short_key")
