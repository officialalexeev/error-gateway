"""Application settings from environment variables with auto-detection."""

import re
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Email validation regex (RFC 5322 simplified)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email_address(email: str) -> str:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        The same email if valid

    Raises:
        ValueError: If email format is invalid
    """
    if not EMAIL_REGEX.match(email):
        raise ValueError(f"Invalid email address format: {email}")
    return email


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    BACKEND_PORT: int = 8000

    # Database (auto-detection: SQLite if POSTGRES_USER is None)
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        """Get database URL based on configuration."""
        if self.POSTGRES_USER:
            if not self.POSTGRES_PASSWORD or not self.POSTGRES_DB:
                raise ValueError(
                    "POSTGRES_PASSWORD and POSTGRES_DB are required when POSTGRES_USER is set"
                )
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return "sqlite+aiosqlite:///./data/error-gateway.db"

    @property
    def use_postgres(self) -> bool:
        """Check if PostgreSQL is used."""
        return bool(self.POSTGRES_USER)

    @property
    def use_sqlite(self) -> bool:
        """Check if SQLite is used."""
        return not self.POSTGRES_USER

    # Redis (auto-detection: In-Memory if REDIS_HOST is None)
    REDIS_HOST: str | None = None
    REDIS_PORT: int = 6379
    REDIS_DB: int = 1
    REDIS_PASSWORD: str | None = None

    @property
    def REDIS_URL(self) -> str | None:
        """Get Redis URL based on configuration."""
        if self.REDIS_HOST:
            password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            return f"redis://{password_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return None

    @property
    def use_redis(self) -> bool:
        """Check if Redis is used."""
        return bool(self.REDIS_HOST)

    # Grafana Loki
    LOKI_URL: str | None = None

    @property
    def use_loki(self) -> bool:
        """Check if Loki logging is enabled."""
        return bool(self.LOKI_URL)

    # Telegram
    TG_BOT_TOKEN: str | None = None
    TG_CHAT_ID: str | None = None
    TG_TOPIC_ID: str | None = None

    @property
    def use_telegram(self) -> bool:
        """Check if Telegram is enabled."""
        return bool(self.TG_BOT_TOKEN and self.TG_CHAT_ID)

    # Email (SMTP)
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAIL_FROM: str | None = None
    EMAIL_TO: list[str] = []

    @field_validator("EMAIL_TO", mode="before")
    @classmethod
    def parse_email_to(cls, v: str | list[str] | None) -> list[str]:
        """
        Parse EMAIL_TO from comma-separated string to list.

        Handles both string from environment variables and list from tests.
        Validates each email address format.

        Raises:
            ValueError: If any email address has invalid format
        """
        if v is None:
            return []
        if isinstance(v, list):
            emails = v
        elif not v:
            return []
        else:
            emails = [email.strip() for email in v.split(",")]

        # Validate each email address
        validated_emails = []
        for email in emails:
            if email:  # Skip empty strings
                validated_emails.append(validate_email_address(email))

        return validated_emails

    @field_validator("EMAIL_FROM", mode="before")
    @classmethod
    def validate_email_from(cls, v: str | None) -> str | None:
        """Validate EMAIL_FROM format if provided."""
        if v is None:
            return None
        if not v:
            return None
        return validate_email_address(v)

    @property
    def use_email(self) -> bool:
        """Check if Email is enabled."""
        return bool(self.SMTP_HOST and self.SMTP_USER and self.SMTP_PASSWORD and self.EMAIL_TO)

    # Application
    LOG_LEVEL: str = "INFO"
    ERROR_RETENTION_DAYS: int = 30
    RATE_LIMIT_PER_MINUTE: int = 100
    NOTIFICATION_THROTTLE_MINUTES: int = 5
    MAX_PAGINATION_LIMIT: int = 100

    # Data Masking
    MASK_EMAIL: bool = True
    MASK_PHONE: bool = True
    MASK_CREDIT_CARD: bool = True
    MASK_TOKENS: bool = True

    # Logging
    LOG_FORMAT: str = "json"
    LOG_FORMAT_TEXT: str = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )

    # CORS
    CORS_ORIGINS: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
