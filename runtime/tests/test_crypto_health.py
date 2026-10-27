from __future__ import annotations

import base64

import pytest
from cryptography.exceptions import InvalidTag

from runtime.crypto import TokenCipher, normalize_key
from runtime.health import render_metrics


def test_token_cipher_roundtrip():
    cipher = TokenCipher(b"k" * 32)
    encrypted = cipher.encrypt("MTAxMDEwMTAxMDEwMTAxMDEw.abc.def")
    assert encrypted.startswith("v1:")
    assert encrypted != "MTAxMDEwMTAxMDEwMTAxMDEw.abc.def"
    assert cipher.decrypt(encrypted) == "MTAxMDEwMTAxMDEwMTAxMDEw.abc.def"
    assert cipher.decrypt("") == ""


def test_token_cipher_rejects_bad_key_and_payload():
    with pytest.raises(ValueError):
        TokenCipher(b"short")
    cipher = TokenCipher(b"k" * 32)
    with pytest.raises(ValueError):
        cipher.decrypt("aGVsbG8=")
    with pytest.raises(InvalidTag):
        TokenCipher(b"x" * 32).decrypt(cipher.encrypt("token"))


def test_normalize_key_is_strict():
    key = base64.urlsafe_b64encode(b"k" * 32).decode()
    assert normalize_key(key) == b"k" * 32
    assert normalize_key(b"k" * 32) == b"k" * 32
    with pytest.raises(ValueError):
        normalize_key("secret")
    with pytest.raises(ValueError):
        normalize_key(None)
    with pytest.raises(ValueError):
        normalize_key(base64.urlsafe_b64encode(b"k" * 16).decode())



def test_mask_hides_most_of_token():
    assert TokenCipher.mask("") == ""
    assert TokenCipher.mask("short") == "********"
    assert TokenCipher.mask("abcdefghijklmnop").startswith("abcdef")
    assert TokenCipher.mask("abcdefghijklmnop").endswith("mnop")


def test_render_metrics():
    text = render_metrics(
        {
            "statuses": {"online": 2, "error": 1},
            "bots": [
                {"id": "b1", "name": "Alpha", "latency_ms": 30, "uptime_seconds": 100}
            ],
            "metrics": {
                "commands_total": 5,
                "commands_failed": 1,
                "restarts_total": 2,
                "uptime_seconds": 1000,
            },
        }
    )
    assert 'runtime_bots_total{status="online"} 2' in text
    assert "runtime_commands_total 5" in text
    assert 'runtime_bot_latency_ms{bot_id="b1",name="Alpha"} 30' in text


def test_render_metrics_escapes_label_values():
    text = render_metrics(
        {
            "statuses": {},
            "bots": [{"id": "b1", "name": 'Alpha "One"\\Two', "latency_ms": 1}],
            "metrics": {},
        }
    )
    assert 'name="Alpha \\"One\\"\\\\Two"' in text
