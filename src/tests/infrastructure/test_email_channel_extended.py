"""Extended tests for Email notification channel - connection management."""

import pytest
from app.domain.entities.notification import Notification
from app.infrastructure.notifications.email.channel import EmailNotificationChannel
from unittest.mock import AsyncMock, patch


class TestEmailNotificationChannelConnection:
    """Tests for SMTP connection management."""

    @pytest.mark.asyncio
    async def test_get_smtp_creates_new_connection(self):
        """Test that _get_smtp creates new SMTP connection."""
        channel = EmailNotificationChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=["admin@example.com"],
        )

        # Mock SMTP class
        with patch("app.infrastructure.notifications.email.channel.aiosmtplib.SMTP") as MockSMTP:
            mock_smtp_instance = AsyncMock()
            MockSMTP.return_value = mock_smtp_instance

            # Call _get_smtp
            result = await channel._get_smtp()

            # Verify SMTP was created and connected
            MockSMTP.assert_called_once_with(hostname="smtp.gmail.com", port=587, timeout=10)
            mock_smtp_instance.connect.assert_called_once()
            mock_smtp_instance.starttls.assert_called_once()
            mock_smtp_instance.login.assert_called_once_with("user@gmail.com", "pass")
            assert result is mock_smtp_instance
            assert channel._connected is True

    @pytest.mark.asyncio
    async def test_get_smtp_returns_cached_connection(self):
        """Test that _get_smtp returns cached connection if already connected."""
        channel = EmailNotificationChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=["admin@example.com"],
        )

        # Set up cached connection
        mock_cached_smtp = AsyncMock()
        channel._smtp = mock_cached_smtp
        channel._connected = True

        with patch("app.infrastructure.notifications.email.channel.aiosmtplib.SMTP") as MockSMTP:
            result = await channel._get_smtp()

            # Verify cached connection was returned (no new SMTP created)
            MockSMTP.assert_not_called()
            mock_cached_smtp.connect.assert_not_called()
            assert result is mock_cached_smtp

    @pytest.mark.asyncio
    async def test_get_smtp_connection_fails(self):
        """Test that _get_smtp handles connection failure."""
        channel = EmailNotificationChannel(
            smtp_host="smtp.invalid.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=["admin@example.com"],
        )

        with patch("app.infrastructure.notifications.email.channel.aiosmtplib.SMTP") as MockSMTP:
            mock_smtp = AsyncMock()
            mock_smtp.connect.side_effect = Exception("Connection refused")
            MockSMTP.return_value = mock_smtp

            # Should raise exception
            with pytest.raises(Exception, match="Connection refused"):
                await channel._get_smtp()

            # Verify state was reset
            assert channel._smtp is None
            assert channel._connected is False

    @pytest.mark.asyncio
    async def test_close_smtp_connection(self):
        """Test that close() properly closes SMTP connection."""
        channel = EmailNotificationChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=["admin@example.com"],
        )

        # Set up SMTP connection
        mock_smtp = AsyncMock()
        channel._smtp = mock_smtp
        channel._connected = True

        # Close connection
        await channel.close()

        # Verify quit was called
        mock_smtp.quit.assert_called_once()
        assert channel._smtp is None
        assert channel._connected is False

    @pytest.mark.asyncio
    async def test_close_no_connection(self):
        """Test that close() handles no connection gracefully."""
        channel = EmailNotificationChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=["admin@example.com"],
        )

        # No connection set up
        assert channel._smtp is None

        # Should not raise
        await channel.close()

        assert channel._smtp is None
        assert channel._connected is False

    @pytest.mark.asyncio
    async def test_close_quit_raises_exception(self):
        """Test that close() handles quit() exception gracefully."""
        channel = EmailNotificationChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=["admin@example.com"],
        )

        # Set up SMTP connection that raises on quit
        mock_smtp = AsyncMock()
        mock_smtp.quit.side_effect = Exception("Already closed")
        channel._smtp = mock_smtp
        channel._connected = True

        # Should not raise, exception is logged and ignored
        await channel.close()

        # Verify state was reset despite exception
        assert channel._smtp is None
        assert channel._connected is False

    @pytest.mark.asyncio
    async def test_is_available_when_configured(self):
        """Test is_available returns True when properly configured."""
        channel = EmailNotificationChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=["admin@example.com"],
        )

        assert channel.is_available is True

    @pytest.mark.asyncio
    async def test_is_available_when_not_configured(self):
        """Test is_available returns False when not configured."""
        # Missing smtp_host
        channel = EmailNotificationChannel(
            smtp_host="",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=["admin@example.com"],
        )

        assert channel.is_available is False

        # Missing email_to
        channel2 = EmailNotificationChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            email_from="user@gmail.com",
            email_to=[],
        )

        assert channel2.is_available is False

    @pytest.mark.asyncio
    async def test_send_not_available(self, sample_error_group):
        """Test that send returns False when channel is not available."""
        channel = EmailNotificationChannel(
            smtp_host="",  # Not configured
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

        result = await channel.send(notification)
        assert result is False
