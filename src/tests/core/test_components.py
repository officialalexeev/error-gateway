"""
Tests for Core Components.

Async: Async tests
"""

import pytest


class TestLogger:
    """Tests for logger."""

    def test_logger_import(self):
        """Test logger import."""
        from app.core.logger import log, setup_logger

        assert log is not None
        assert callable(setup_logger)

    def test_setup_logger(self):
        """Test logger setup."""
        from app.core.logger import setup_logger

        # Should not raise
        setup_logger()


class TestDatabase:
    """Tests for database."""

    @pytest.mark.asyncio
    async def test_get_db(self):
        """Test database session retrieval."""
        from app.core.database import get_db

        # Get generator
        gen = get_db()

        # Get session from generator
        session = await gen.__anext__()

        assert session is not None

        # Close generator
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass


class TestConfig:
    """Tests for configuration."""

    def test_settings_singleton(self):
        """Test settings singleton."""
        from app.core.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_use_postgres_property(self):
        """Test use_postgres property."""
        from app.core.config import Settings

        # PostgreSQL
        settings = Settings(POSTGRES_USER="postgres")
        assert settings.use_postgres is True

        # SQLite (default)
        settings = Settings(POSTGRES_USER="")
        assert settings.use_postgres is False

    def test_use_redis_property(self):
        """Test use_redis property."""
        from app.core.config import Settings

        # Redis
        settings = Settings(REDIS_HOST="localhost")
        assert settings.use_redis is True

        # Empty (In-Memory)
        settings = Settings(REDIS_HOST="")
        assert settings.use_redis is False

    def test_use_telegram_property(self):
        """Test use_telegram property."""
        from app.core.config import Settings

        # Telegram enabled
        settings = Settings(TG_BOT_TOKEN="123:ABC", TG_CHAT_ID="-1001234567")
        assert settings.use_telegram is True

        # Telegram disabled (no token)
        settings = Settings(TG_BOT_TOKEN="", TG_CHAT_ID="-1001234567")
        assert settings.use_telegram is False

        # Telegram disabled (no chat_id)
        settings = Settings(TG_BOT_TOKEN="123:ABC", TG_CHAT_ID="")
        assert settings.use_telegram is False

    def test_use_email_property(self):
        """Test use_email property."""
        from app.core.config import Settings

        # Email enabled
        settings = Settings(
            SMTP_HOST="smtp.gmail.com",
            SMTP_USER="user@gmail.com",
            SMTP_PASSWORD="pass",
            EMAIL_TO=["admin@example.com"],
        )
        assert settings.use_email is True

        # Email disabled (no host)
        settings = Settings(
            SMTP_HOST=None,
            SMTP_USER="user@gmail.com",
            SMTP_PASSWORD="pass",
            EMAIL_TO=["admin@example.com"],
        )
        assert settings.use_email is False
