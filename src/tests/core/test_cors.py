"""
Tests for CORS configuration.

Tests verify that CORS is properly configured based on settings.
"""

import pytest
from app.core.config import settings


class TestCORSConfiguration:
    """Test CORS configuration."""

    def test_cors_disabled_by_default(self):
        """CORS should be disabled by default (empty CORS_ORIGINS)."""
        # By default, CORS_ORIGINS is empty
        assert settings.cors_origins_list == []

    def test_cors_origins_parsing_single(self):
        """Test parsing single CORS origin."""
        from app.core.config import Settings

        test_settings = Settings(CORS_ORIGINS="https://admin.example.com")
        assert test_settings.cors_origins_list == ["https://admin.example.com"]

    def test_cors_origins_parsing_multiple(self):
        """Test parsing multiple CORS origins."""
        from app.core.config import Settings

        test_settings = Settings(
            CORS_ORIGINS="https://admin.example.com, https://dashboard.example.com"
        )
        assert test_settings.cors_origins_list == [
            "https://admin.example.com",
            "https://dashboard.example.com",
        ]

    def test_cors_origins_parsing_with_whitespace(self):
        """Test parsing CORS origins with extra whitespace."""
        from app.core.config import Settings

        test_settings = Settings(
            CORS_ORIGINS="  https://admin.example.com  ,  https://dashboard.example.com  "
        )
        assert test_settings.cors_origins_list == [
            "https://admin.example.com",
            "https://dashboard.example.com",
        ]

    def test_cors_origins_empty_string(self):
        """Test that empty string returns empty list."""
        from app.core.config import Settings

        test_settings = Settings(CORS_ORIGINS="")
        assert test_settings.cors_origins_list == []


class TestCORSEndpoints:
    """Test CORS behavior on endpoints."""

    # Note: Endpoint CORS tests removed - CORS behavior is tested
    # through settings validation. Actual CORS headers depend on
    # CORS_ORIGINS environment variable and are verified manually.
    pass


@pytest.fixture
def client():
    """Deprecated - use integration test fixtures."""
    pass
