"""Notification factory for creating channel instances."""

from typing import List

from app.application.interfaces.interfaces import NotificationChannel, NotificationService
from app.core.config import Settings
from app.infrastructure.notifications.email.channel import EmailNotificationChannel
from app.infrastructure.notifications.service import MultiChannelNotificationService
from app.infrastructure.notifications.telegram.channel import TelegramNotificationChannel


class NotificationFactory:
    """Factory for creating notification service instances."""

    @staticmethod
    def create_notification_service(settings: Settings) -> NotificationService:
        """
        Create notification service with configured channels.

        Args:
            settings: Application settings with notification configuration.

        Returns:
            NotificationService instance with configured channels.
        """
        channels: List[NotificationChannel] = []

        # Add Telegram channel if configured
        if settings.use_telegram:
            if not (settings.TG_BOT_TOKEN and settings.TG_CHAT_ID):
                raise ValueError(
                    "TG_BOT_TOKEN and TG_CHAT_ID are required when Telegram is enabled"
                )
            telegram_channel = TelegramNotificationChannel(
                bot_token=settings.TG_BOT_TOKEN,
                chat_id=settings.TG_CHAT_ID,
                topic_id=settings.TG_TOPIC_ID,
            )
            channels.append(telegram_channel)

        # Add Email channel if configured
        if settings.use_email:
            if not (
                settings.SMTP_HOST
                and settings.SMTP_USER
                and settings.SMTP_PASSWORD
                and settings.EMAIL_TO
            ):
                raise ValueError(
                    "SMTP_HOST, SMTP_USER, SMTP_PASSWORD and EMAIL_TO are required when Email is enabled"
                )
            email_channel = EmailNotificationChannel(
                smtp_host=settings.SMTP_HOST,
                smtp_port=settings.SMTP_PORT or 587,
                smtp_user=settings.SMTP_USER,
                smtp_password=settings.SMTP_PASSWORD,
                email_from=settings.EMAIL_FROM or settings.SMTP_USER,
                email_to=settings.EMAIL_TO,
            )
            channels.append(email_channel)

        return MultiChannelNotificationService(channels)

    @staticmethod
    def create_telegram_channel(
        bot_token: str,
        chat_id: str,
        topic_id: str | None = None,
    ) -> TelegramNotificationChannel:
        """
        Create Telegram notification channel.

        Args:
            bot_token: Telegram bot token from @BotFather.
            chat_id: Telegram chat ID from @userinfobot.
            topic_id: Optional topic ID for forum chats.

        Returns:
            Configured TelegramNotificationChannel instance.
        """
        return TelegramNotificationChannel(
            bot_token=bot_token,
            chat_id=chat_id,
            topic_id=topic_id,
        )

    @staticmethod
    def create_email_channel(
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        email_from: str,
        email_to: List[str],
    ) -> EmailNotificationChannel:
        """
        Create Email notification channel.

        Args:
            smtp_host: SMTP server hostname.
            smtp_port: SMTP server port.
            smtp_user: SMTP username.
            smtp_password: SMTP password.
            email_from: Sender email address.
            email_to: List of recipient email addresses.

        Returns:
            Configured EmailNotificationChannel instance.
        """
        return EmailNotificationChannel(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            email_from=email_from,
            email_to=email_to,
        )
