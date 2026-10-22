
import pytest
from unittest.mock import MagicMock, patch
import requests

from backend.integrations.discord.client import (
    DiscordRestClient,
    DiscordUnauthorizedError,
    DiscordRateLimitError,
    DiscordAPIError,
)

def test_get_current_bot_user_success():
    client = DiscordRestClient(bot_token="test_token")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "1234567890",
        "username": "MyCoolBot",
        "discriminator": "0000",
        "avatar": "abcdef123456",
        "bot": True,
        "flags": 0,
    }

    with patch.object(client.session, "request", return_value=mock_resp):
        user = client.get_current_bot_user()
        assert user["id"] == "1234567890"
        assert user["username"] == "MyCoolBot"
        assert user["bot"] is True

def test_client_handles_401_unauthorized_with_callback():
    callback_called = False

    def on_401():
        nonlocal callback_called
        callback_called = True

    client = DiscordRestClient(bot_token="invalid_token", on_unauthorized_callback=on_401)
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"message": "401: Unauthorized", "code": 0}

    with patch.object(client.session, "request", return_value=mock_resp):
        with pytest.raises(DiscordUnauthorizedError):
            client.get_current_bot_user()

    assert callback_called is True

def test_client_handles_429_rate_limit_and_retries():
    client = DiscordRestClient(bot_token="test_token", max_retries=2)

    mock_429 = MagicMock()
    mock_429.ok = False
    mock_429.status_code = 429
    mock_429.headers = {"Retry-After": "0.01"}
    mock_429.json.return_value = {"retry_after": 0.01, "message": "You are being rate limited."}

    mock_200 = MagicMock()
    mock_200.ok = True
    mock_200.status_code = 200
    mock_200.json.return_value = [{"id": "cmd1", "name": "ping"}]

    with patch.object(client.session, "request", side_effect=[mock_429, mock_200]) as mock_req:
        res = client.bulk_overwrite_global_commands(
            application_id="12345",
            commands=[{"name": "ping", "description": "ping command"}]
        )
        assert len(res) == 1
        assert res[0]["name"] == "ping"
        assert mock_req.call_count == 2
