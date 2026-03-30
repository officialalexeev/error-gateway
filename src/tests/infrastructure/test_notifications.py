"""
Tests for Notification Channels.

Test Isolation Principle:
- Mock external APIs
- Test only channel logic

Async: Async tests
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.domain.entities.notification import Notification
from app.infrastructure.notifications.email.channel import EmailNotificationChannel
from app.infrastructure.notifications.telegram.channel import TelegramNotificationChannel


class TestTelegramNotificationChannel:
    """Tests for Telegram channel."""

    def test_is_available_true(self):
        """Test channel availability."""
        channel = TelegramNotificationChannel(
            bot_token="123:ABC",
            chat_id="-1001234567",
        )

        assert channel.is_available is True

    def test_is_available_false_no_token(self):
        """Test channel unavailability without token."""
        channel = TelegramNotificationChannel(
            bot_token="",
            chat_id="-1001234567",
        )

        assert channel.is_available is False

    @pytest.mark.asyncio
    async def test_send_success(self, sample_error_group):
        """Test successful send."""
        channel = TelegramNotificationChannel(
            bot_token="123:ABC",
            chat_id="-1001234567",
        )
        notification = Notification(
            channel="telegram",
            recipient="-1001234567",
            subject="Error",
            body="Test error",
            error_group=sample_error_group,
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200
            result = await channel.send(notification)

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_failure(self, sample_error_group):
        """Test failed send."""
        channel = TelegramNotificationChannel(
            bot_token="123:ABC",
            chat_id="-1001234567",
        )
        notification = Notification(
            channel="telegram",
            recipient="-1001234567",
            subject="Error",
            body="Test error",
            error_group=sample_error_group,
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 400
            result = await channel.send(notification)

            assert result is False

    def test_ensure_telegram_limit_short_message(self, sample_error_group):
        """Test that short messages are not modified."""
        channel = TelegramNotificationChannel(
            bot_token="123:ABC",
            chat_id="-1001234567",
        )
        notification = Notification(error_group=sample_error_group)
        
        # Create a short message
        short_text = "🚨 *ERROR REPORT*\n\nTest message"
        result = channel._ensure_telegram_limit(short_text)
        
        assert result == short_text
        assert len(result) <= 4096

    def test_ensure_telegram_limit_long_message(self, sample_error_group):
        """Test that long messages are truncated."""
        channel = TelegramNotificationChannel(
            bot_token="123:ABC",
            chat_id="-1001234567",
        )
        
        # Create a message longer than 4096 characters
        long_text = "A" * 5000
        result = channel._ensure_telegram_limit(long_text)
        
        assert len(result) <= 4096
        assert "⚠️ _Message truncated due to Telegram limit_" in result
        assert result.startswith("A" * 100)  # Should start with original content


class TestEmailNotificationChannel:
    """Tests for Email channel."""

    def test_is_available_true(self):
        """Test channel availability."""
        channel = EmailNotificationChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=["admin@example.com"],
        )

        assert channel.is_available is True

    def test_is_available_false_no_recipients(self):
        """Test channel unavailability without recipients."""
        channel = EmailNotificationChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=[],
        )

        assert channel.is_available is False

    @pytest.mark.asyncio
    async def test_send_success(self, sample_error_group):
        """Test successful send."""
        channel = EmailNotificationChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=["admin@example.com"],
        )
        notification = Notification(
            channel="email",
            recipient="admin@example.com",
            subject="Error",
            body="Test error",
            error_group=sample_error_group,
        )

        # Mock SMTP connection and send_message
        with patch.object(channel, "_get_smtp", new_callable=AsyncMock) as mock_get_smtp:
            mock_smtp = AsyncMock()
            mock_smtp.send_message = AsyncMock()
            mock_get_smtp.return_value = mock_smtp

            result = await channel.send(notification)
            assert result is True
            mock_get_smtp.assert_called_once()
            mock_smtp.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_reconnect_on_disconnect(self, sample_error_group):
        """Test reconnect when connection is lost."""
        from aiosmtplib.errors import SMTPServerDisconnected

        channel = EmailNotificationChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=["admin@example.com"],
        )
        notification = Notification(
            channel="email",
            recipient="admin@example.com",
            subject="Error",
            body="Test error",
            error_group=sample_error_group,
        )

        # Mock SMTP connection with disconnect on first send
        with patch.object(channel, "_get_smtp", new_callable=AsyncMock) as mock_get_smtp:
            mock_smtp = AsyncMock()
            # First call raises disconnect, second succeeds
            mock_smtp.send_message = AsyncMock(
                side_effect=[SMTPServerDisconnected("Connection lost"), None]
            )
            mock_get_smtp.return_value = mock_smtp

            result = await channel.send(notification)
            assert result is True
            # Should call _get_smtp twice (initial + reconnect)
            assert mock_get_smtp.call_count == 2
            # Should call send_message twice (initial + retry)
            assert mock_smtp.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_close_smtp_connection(self):
        """Test SMTP connection close."""
        channel = EmailNotificationChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=["admin@example.com"],
        )

        # Mock SMTP connection - directly set internal state
        mock_smtp = AsyncMock()
        mock_smtp.quit = AsyncMock()
        channel._smtp = mock_smtp
        channel._connected = True

        # Close connection
        await channel.close()
        mock_smtp.quit.assert_called_once()
        assert channel._smtp is None
        assert channel._connected is False


class TestMultiChannelNotificationService:
    """Tests for multi-channel service."""

    def test_register_channel(self):
        """Test channel registration."""
        from unittest.mock import Mock

        from app.infrastructure.notifications.service import MultiChannelNotificationService

        channel = Mock()
        channel.is_available = True
        service = MultiChannelNotificationService(channels=[channel])

        assert len(service.channels) == 1

    @pytest.mark.asyncio
    async def test_should_notify_true(self, sample_error_group):
        """Test notification necessity."""
        from unittest.mock import Mock

        from app.infrastructure.notifications.service import MultiChannelNotificationService

        channel = Mock()
        channel.is_available = True
        service = MultiChannelNotificationService(channels=[channel])

        result = service.should_notify(sample_error_group, throttle_minutes=5)

        assert result is True

    @pytest.mark.asyncio
    async def test_should_notify_false_throttled(self, sample_error_group):
        """Test notification throttling with DB-based last_notified_at."""
        from datetime import datetime, timedelta, timezone
        from unittest.mock import Mock

        from app.infrastructure.notifications.service import MultiChannelNotificationService

        channel = Mock()
        channel.is_available = True
        service = MultiChannelNotificationService(channels=[channel])

        # Simulate group that was already notified recently
        sample_error_group.is_notified = True
        sample_error_group.last_notified_at = datetime.now(timezone.utc)

        # Should be throttled because last_notified_at is recent
        result = service.should_notify(sample_error_group, throttle_minutes=5)

        assert result is False

    @pytest.mark.asyncio
    async def test_should_notify_true_after_throttle(self, sample_error_group):
        """Test notification allowed after throttle period expires."""
        from datetime import datetime, timedelta, timezone
        from unittest.mock import Mock

        from app.infrastructure.notifications.service import MultiChannelNotificationService

        channel = Mock()
        channel.is_available = True
        service = MultiChannelNotificationService(channels=[channel])

        # Simulate group notified 10 minutes ago (throttle is 5 minutes)
        sample_error_group.is_notified = True
        sample_error_group.last_notified_at = datetime.now(timezone.utc) - timedelta(minutes=10)

        # Should allow notification because throttle period expired
        result = service.should_notify(sample_error_group, throttle_minutes=5)

        assert result is True
