"""
Tests for Notification Factory.

Test Isolation Principle:
- Test only factory logic
- Verify correct channel creation

Async: Sync tests (factory is not async)
"""

from unittest.mock import Mock

from app.infrastructure.notifications.email.channel import EmailNotificationChannel
from app.infrastructure.notifications.factory import NotificationFactory
from app.infrastructure.notifications.service import MultiChannelNotificationService
from app.infrastructure.notifications.telegram.channel import TelegramNotificationChannel


class TestNotificationFactory:
    """Tests for NotificationFactory."""

    def test_create_notification_service_no_channels(self):
        """Test service creation without channels."""
        settings = Mock()
        settings.use_telegram = False
        settings.use_email = False
        settings.TG_BOT_TOKEN = ""
        settings.TG_CHAT_ID = ""
        settings.SMTP_HOST = ""
        settings.SMTP_USER = ""
        settings.SMTP_PASSWORD = ""
        settings.SMTP_PORT = None
        settings.EMAIL_FROM = ""
        settings.EMAIL_TO = []

        service = NotificationFactory.create_notification_service(settings)

        assert isinstance(service, MultiChannelNotificationService)
        assert len(service.channels) == 0

    def test_create_notification_service_telegram_only(self):
        """Test service creation with Telegram only."""
        settings = Mock()
        settings.use_telegram = True
        settings.TG_BOT_TOKEN = "123:ABC"
        settings.TG_CHAT_ID = "-1001234567"
        settings.use_email = False
        settings.SMTP_HOST = ""
        settings.SMTP_USER = ""
        settings.SMTP_PASSWORD = ""
        settings.EMAIL_TO = []

        service = NotificationFactory.create_notification_service(settings)

        assert isinstance(service, MultiChannelNotificationService)
        assert len(service.channels) == 1
        assert "TelegramNotificationChannel" in service.channels
        channel = service.channels["TelegramNotificationChannel"]
        assert isinstance(channel, TelegramNotificationChannel)
        assert channel.is_available is True

    def test_create_notification_service_email_only(self):
        """Test service creation with Email only."""
        settings = Mock()
        settings.use_telegram = False
        settings.TG_BOT_TOKEN = ""
        settings.TG_CHAT_ID = ""
        settings.use_email = True
        settings.SMTP_HOST = "smtp.gmail.com"
        settings.SMTP_USER = "user@gmail.com"
        settings.SMTP_PASSWORD = "password123"
        settings.SMTP_PORT = 587
        settings.EMAIL_FROM = "user@gmail.com"
        settings.EMAIL_TO = ["admin@example.com"]

        service = NotificationFactory.create_notification_service(settings)

        assert isinstance(service, MultiChannelNotificationService)
        assert len(service.channels) == 1
        assert "EmailNotificationChannel" in service.channels
        channel = service.channels["EmailNotificationChannel"]
        assert isinstance(channel, EmailNotificationChannel)
        assert channel.is_available is True

    def test_create_notification_service_both_channels(self):
        """Test service creation with both channels."""
        settings = Mock()
        settings.use_telegram = True
        settings.TG_BOT_TOKEN = "123:ABC"
        settings.TG_CHAT_ID = "-1001234567"
        settings.use_email = True
        settings.SMTP_HOST = "smtp.gmail.com"
        settings.SMTP_USER = "user@gmail.com"
        settings.SMTP_PASSWORD = "password123"
        settings.SMTP_PORT = 587
        settings.EMAIL_FROM = "user@gmail.com"
        settings.EMAIL_TO = ["admin@example.com"]

        service = NotificationFactory.create_notification_service(settings)

        assert isinstance(service, MultiChannelNotificationService)
        assert len(service.channels) == 2
        assert "TelegramNotificationChannel" in service.channels
        assert "EmailNotificationChannel" in service.channels
        assert isinstance(
            service.channels["TelegramNotificationChannel"], TelegramNotificationChannel
        )
        assert isinstance(service.channels["EmailNotificationChannel"], EmailNotificationChannel)

    def test_create_notification_service_telegram_no_token(self):
        """Test service creation without Telegram token."""
        settings = Mock()
        settings.use_telegram = False  # use_telegram=False if no token
        settings.TG_BOT_TOKEN = ""
        settings.TG_CHAT_ID = "-1001234567"
        settings.use_email = False

        service = NotificationFactory.create_notification_service(settings)

        assert isinstance(service, MultiChannelNotificationService)
        assert len(service.channels) == 0

    def test_create_notification_service_telegram_no_chat_id(self):
        """Test service creation without Telegram chat_id."""
        settings = Mock()
        settings.use_telegram = False  # use_telegram=False if no chat_id
        settings.TG_BOT_TOKEN = "123:ABC"
        settings.TG_CHAT_ID = ""  # Empty chat_id
        settings.use_email = False

        service = NotificationFactory.create_notification_service(settings)

        assert isinstance(service, MultiChannelNotificationService)
        assert len(service.channels) == 0

    def test_create_notification_service_email_incomplete_config(self):
        """Test service creation with incomplete Email configuration."""
        # Without SMTP_HOST
        settings = Mock()
        settings.use_email = False  # use_email=False if no config
        settings.SMTP_HOST = ""
        settings.SMTP_USER = "user@gmail.com"
        settings.SMTP_PASSWORD = "password"
        settings.use_telegram = False
        settings.EMAIL_TO = []

        service = NotificationFactory.create_notification_service(settings)
        assert len(service.channels) == 0

        # Without SMTP_USER
        settings.SMTP_HOST = "smtp.gmail.com"
        settings.SMTP_USER = ""
        service = NotificationFactory.create_notification_service(settings)
        assert len(service.channels) == 0

        # Without SMTP_PASSWORD
        settings.SMTP_USER = "user@gmail.com"
        settings.SMTP_PASSWORD = ""
        service = NotificationFactory.create_notification_service(settings)
        assert len(service.channels) == 0

    def test_create_notification_service_email_default_port(self):
        """Test service creation with default port."""
        settings = Mock()
        settings.use_telegram = False
        settings.use_email = True
        settings.SMTP_HOST = "smtp.gmail.com"
        settings.SMTP_USER = "user@gmail.com"
        settings.SMTP_PASSWORD = "password123"
        settings.SMTP_PORT = None  # Should use default 587
        settings.EMAIL_FROM = "user@gmail.com"
        settings.EMAIL_TO = ["admin@example.com"]

        service = NotificationFactory.create_notification_service(settings)

        assert len(service.channels) == 1
        channel = service.channels["EmailNotificationChannel"]
        assert channel.smtp_port == 587

    def test_create_notification_service_email_from_fallback(self):
        """Test EMAIL_FROM fallback to SMTP_USER."""
        settings = Mock()
        settings.use_telegram = False
        settings.use_email = True
        settings.SMTP_HOST = "smtp.gmail.com"
        settings.SMTP_USER = "user@gmail.com"
        settings.SMTP_PASSWORD = "password123"
        settings.SMTP_PORT = 587
        settings.EMAIL_FROM = ""  # Empty, should fallback to SMTP_USER
        settings.EMAIL_TO = ["admin@example.com"]

        service = NotificationFactory.create_notification_service(settings)

        assert len(service.channels) == 1
        channel = service.channels["EmailNotificationChannel"]
        assert channel.email_from == "user@gmail.com"

    def test_create_notification_service_multiple_email_recipients(self):
        """Test service creation with multiple Email recipients."""
        settings = Mock()
        settings.use_telegram = False
        settings.use_email = True
        settings.SMTP_HOST = "smtp.gmail.com"
        settings.SMTP_USER = "user@gmail.com"
        settings.SMTP_PASSWORD = "password123"
        settings.SMTP_PORT = 587
        settings.EMAIL_FROM = "user@gmail.com"
        settings.EMAIL_TO = ["admin1@example.com", "admin2@example.com", "admin3@example.com"]

        service = NotificationFactory.create_notification_service(settings)

        assert len(service.channels) == 1
        channel = service.channels["EmailNotificationChannel"]
        assert len(channel.email_to) == 3
        assert "admin1@example.com" in channel.email_to
        assert "admin2@example.com" in channel.email_to
        assert "admin3@example.com" in channel.email_to

    def test_create_notification_service_use_telegram_false(self):
        """Test service creation with use_telegram=False."""
        settings = Mock()
        settings.use_telegram = False  # Explicitly disabled
        settings.TG_BOT_TOKEN = "123:ABC"  # Token exists but use_telegram=False
        settings.TG_CHAT_ID = "-1001234567"
        settings.use_email = False

        service = NotificationFactory.create_notification_service(settings)

        assert len(service.channels) == 0

    def test_create_notification_service_use_email_false(self):
        """Test service creation with use_email=False."""
        settings = Mock()
        settings.use_telegram = False
        settings.use_email = False  # Explicitly disabled
        settings.SMTP_HOST = "smtp.gmail.com"  # Config exists but use_email=False
        settings.SMTP_USER = "user@gmail.com"
        settings.SMTP_PASSWORD = "password"
        settings.EMAIL_TO = []

        service = NotificationFactory.create_notification_service(settings)

        assert len(service.channels) == 0
