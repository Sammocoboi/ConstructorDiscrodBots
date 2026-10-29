from unittest.mock import patch

from apps.notifications.services import NotificationService


def test_email_verification_delivery():
    with patch("apps.notifications.services.send_mail", return_value=1) as mock_send:
        res = NotificationService.send_email_verification(
            to_email="test@example.com", user_name="РРІР°РЅ", verification_token="token_abc_123"
        )
        assert res is True
        assert mock_send.called
        call_kwargs = mock_send.call_args[1]
        assert "token_abc_123" in call_kwargs["message"]
        assert "test@example.com" in call_kwargs["recipient_list"]


def test_password_reset_delivery():
    with patch("apps.notifications.services.send_mail", return_value=1) as mock_send:
        res = NotificationService.send_password_reset(
            to_email="user@domain.com", user_name="Петр", reset_token="pwd_token_xyz"
        )
        assert res is True
        assert mock_send.called
        call_kwargs = mock_send.call_args[1]
        assert "pwd_token_xyz" in call_kwargs["message"]


def test_bot_token_invalid_alert():
    with patch("apps.notifications.services.send_mail", return_value=1) as mock_send:
        res = NotificationService.send_bot_token_invalid_alert(
            to_email="owner@test.com",
            user_name="Владелец",
            bot_name="SuperBot",
            bot_id="11223344-5566-7788-9900-aabbccddeeff",
            error_details="Discord 401 Unauthorized",
        )
        assert res is True
        assert mock_send.called
        call_kwargs = mock_send.call_args[1]
        assert "SuperBot" in call_kwargs["subject"]
        assert "SuperBot" in call_kwargs["message"]
        assert "401 Unauthorized" in call_kwargs["message"]
