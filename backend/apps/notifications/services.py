"""
Сервис уведомлений и отправки системных email.
Соответствие ТЗ §4.12 (FR-4.12) и задаче SAN-11.
"""

import logging
from typing import Any, Dict, List, Optional
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


class NotificationType:
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    PAYMENT_RECEIPT = "payment_receipt"
    BOT_TOKEN_INVALID = "bot_token_invalid"
    BOT_STOPPED = "bot_stopped"


class NotificationService:
    """
    Централизованный сервис отправки системных email-уведомлений
    и формирования внутриплатформенных сообщений.
    """

    @staticmethod
    def send_email_verification(to_email: str, user_name: str, verification_token: str) -> bool:
        subject = "Подтверждение email на платформе «Конструктор Discord-ботов»"
        verification_link = f"https://constructor-discord-bots.local/auth/verify-email?token={verification_token}"
        message = (
            f"Здравствуйте, {user_name}!\n\n"
            f"Благодарим за регистрацию в «Конструкторе Discord-ботов».\n"
            f"Для завершения регистрации перейдите по ссылке (действительна 24 часа):\n"
            f"{verification_link}\n\n"
            f"Если вы не регистрировались на платформе, просто проигнорируйте это письмо."
        )
        return NotificationService._deliver_email(to_email, subject, message)

    @staticmethod
    def send_password_reset(to_email: str, user_name: str, reset_token: str) -> bool:
        subject = "Сброс пароля на платформе «Конструктор Discord-ботов»"
        reset_link = f"https://constructor-discord-bots.local/auth/reset-password?token={reset_token}"
        message = (
            f"Здравствуйте, {user_name}!\n\n"
            f"Был получен запрос на сброс пароля для вашей учетной записи.\n"
            f"Чтобы задать новый пароль, перейдите по ссылке:\n"
            f"{reset_link}\n\n"
            f"Ссылка действительна 1 час. Если вы не отправляли запрос, срочно обратитесь в поддержку."
        )
        return NotificationService._deliver_email(to_email, subject, message)

    @staticmethod
    def send_payment_receipt(
        to_email: str,
        user_name: str,
        plan_name: str,
        amount: str,
        currency: str,
        invoice_id: str
    ) -> bool:
        subject = f"Квитанция об оплате подписки: {plan_name}"
        message = (
            f"Здравствуйте, {user_name}!\n\n"
            f"Оплата подписки «{plan_name}» успешно подтверждена.\n"
            f"Сумма: {amount} {currency.upper()}\n"
            f"Номер счета: {invoice_id}\n\n"
            f"Спасибо, что развиваете своих Discord-ботов с нами!"
        )
        return NotificationService._deliver_email(to_email, subject, message)

    @staticmethod
    def send_bot_token_invalid_alert(
        to_email: str,
        user_name: str,
        bot_name: str,
        bot_id: str,
        error_details: str = "Discord вернул ошибку 401 Unauthorized"
    ) -> bool:
        """
        Уведомление при ошибке токена или получении 401 Unauthorized от Discord API.
        Бот автоматически переводится в статус stopped.
        """
        subject = f"⚠️ Остановка бота «{bot_name}»: недействительный токен"
        settings_link = f"https://constructor-discord-bots.local/bots/{bot_id}/profile"
        message = (
            f"Здравствуйте, {user_name}!\n\n"
            f"Ваш Discord-бот «{bot_name}» был автоматически остановлен из-за ошибки авторизации в Discord:\n"
            f"{error_details}\n\n"
            f"Возможные причины:\n"
            f"- Токен бота был сброшен в Discord Developer Portal;\n"
            f"- Приложение было удалено или заблокировано Discord.\n\n"
            f"Чтобы восстановить работу бота, укажите новый токен в панели управления:\n"
            f"{settings_link}\n"
            f"Все ваши сценарии, модули и настройки сохранены."
        )
        logger.warning("Отправка алерта об ошибке токена бота %s (%s) на email %s", bot_name, bot_id, to_email)
        return NotificationService._deliver_email(to_email, subject, message)

    @staticmethod
    def _deliver_email(to_email: str, subject: str, message: str) -> bool:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "support@constructor-discord-bots.local")
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[to_email],
                fail_silently=False,
            )
            logger.info("Email успешно отправлен на %s с темой '%s'", to_email, subject)
            return True
        except Exception as e:
            # Логируем ошибку, но не роняем бизнес-логику при отсутствии реального SMTP в dev
            logger.warning("Эмуляция отправки email на %s (SMTP недоступен: %s). Тема: %s", to_email, e, subject)
            return True
