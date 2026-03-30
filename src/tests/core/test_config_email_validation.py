"""Tests for email validation in Settings."""

import os
import pytest
from app.core.config import Settings


class TestEmailValidation:
    """Tests for email address validation."""

    def test_valid_email_to_list(self):
        """Test valid email list."""
        settings = Settings(
            EMAIL_TO=["admin@example.com", "dev@example.org"]
        )
        assert settings.EMAIL_TO == ["admin@example.com", "dev@example.org"]

    def test_valid_email_to_string(self):
        """Test valid comma-separated email string."""
        settings = Settings(
            EMAIL_TO="admin@example.com,dev@example.org"
        )
        assert settings.EMAIL_TO == ["admin@example.com", "dev@example.org"]

    def test_empty_email_to(self):
        """Test empty EMAIL_TO."""
        settings = Settings(EMAIL_TO="")
        assert settings.EMAIL_TO == []

    def test_none_email_to(self):
        """Test None EMAIL_TO."""
        settings = Settings(EMAIL_TO=None)
        assert settings.EMAIL_TO == []

    def test_invalid_email_to(self):
        """Test invalid email raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email address format"):
            Settings(EMAIL_TO="invalid-email")

    def test_invalid_email_in_list(self):
        """Test invalid email in list raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email address format"):
            Settings(EMAIL_TO="admin@example.com,invalid")

    def test_valid_email_from(self):
        """Test valid EMAIL_FROM."""
        settings = Settings(EMAIL_FROM="noreply@example.com")
        assert settings.EMAIL_FROM == "noreply@example.com"

    def test_invalid_email_from(self):
        """Test invalid EMAIL_FROM raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email address format"):
            Settings(EMAIL_FROM="not-an-email")

    def test_none_email_from(self):
        """Test None EMAIL_FROM."""
        settings = Settings(EMAIL_FROM=None)
        assert settings.EMAIL_FROM is None

    def test_whitespace_trimming(self):
        """Test email addresses are trimmed."""
        settings = Settings(EMAIL_TO="  admin@example.com  ,  dev@example.org  ")
        assert settings.EMAIL_TO == ["admin@example.com", "dev@example.org"]

    def test_skip_empty_emails(self):
        """Test empty emails in list are skipped."""
        settings = Settings(EMAIL_TO="admin@example.com,,dev@example.org")
        assert settings.EMAIL_TO == ["admin@example.com", "dev@example.org"]

    def test_common_email_patterns(self):
        """Test common valid email patterns."""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user_name@example.co.uk",
            "user123@test.org",
        ]
        
        for email in valid_emails:
            settings = Settings(EMAIL_TO=[email])
            assert settings.EMAIL_TO == [email]

    def test_invalid_email_patterns(self):
        """Test common invalid email patterns."""
        invalid_emails = [
            "plainaddress",
            "@missinglocal.com",
            "missing@.com",
            "missing@domain",
            "spaces @example.com",
            "double@@example.com",
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValueError):
                Settings(EMAIL_TO=[email])
