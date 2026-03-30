"""Loguru logger setup with JSON/text formatting and secret masking."""

import re
import sys

from app.core.config import settings
from loguru import logger


class SafeLogger:
    """Safe logger wrapper with secret masking."""

    def __init__(self):
        """Initialize safe logger."""
        self._logger = logger

    def _mask_secrets(self, message: str) -> str:
        """Mask sensitive data in message."""
        masked = message

        masked = re.sub(
            r"bot\d+:[A-Za-z0-9_-]+",
            "***BOT_TOKEN***",
            masked,
        )

        masked = re.sub(
            r"password[\"']?\s*[:=]\s*[\"'][^\"']+[\"']",
            "password=***",
            masked,
            flags=re.IGNORECASE,
        )

        return masked

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._logger.info(self._mask_secrets(message), **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self._logger.error(self._mask_secrets(message), **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._logger.debug(self._mask_secrets(message), **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._logger.warning(self._mask_secrets(message), **kwargs)


def setup_logger() -> SafeLogger:
    """Setup logger with custom format and secret masking."""
    logger.remove()

    if settings.LOG_FORMAT == "json":
        logger.add(
            sys.stdout,
            format="{message}",
            level=settings.LOG_LEVEL,
            serialize=True,
        )
    else:
        logger.add(
            sys.stdout,
            format=settings.LOG_FORMAT_TEXT,
            level=settings.LOG_LEVEL,
        )

    return SafeLogger()


log = setup_logger()
