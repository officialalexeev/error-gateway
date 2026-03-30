"""Telegram notification channel with retry logic."""

import httpx
from app.application.interfaces.interfaces import NotificationChannel
from app.core.logger import log
from app.domain.entities.notification import Notification
from app.infrastructure.notifications.utils import (
    format_datetime_utc,
    format_stack_trace,
    truncate_text,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Telegram message length limit
TELEGRAM_MESSAGE_LIMIT = 4096


class TelegramNotificationChannel(NotificationChannel):
    """Telegram notification channel with retry logic."""

    def __init__(self, bot_token: str, chat_id: str, topic_id: str | None = None):
        """Initialize Telegram channel with bot credentials."""
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.topic_id = topic_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def is_available(self) -> bool:
        """Check if Telegram is configured."""
        return bool(self.bot_token and self.chat_id)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def _send_with_retry(self, notification: Notification) -> bool:
        """Send notification with retry logic."""
        payload = {
            "chat_id": self._get_chat_id(),
            "text": self._format_message(notification),
            "parse_mode": "Markdown",
        }

        if self.topic_id:
            payload["message_thread_id"] = int(self.topic_id)  # type: ignore[assignment]

        response = await self._client.post(
            f"{self.base_url}/sendMessage",
            json=payload,
        )
        return response.status_code == 200

    def _get_chat_id(self) -> str:
        """Get chat ID."""
        return self.chat_id

    async def send(self, notification: Notification) -> bool:
        """Send notification to Telegram."""
        if not self.is_available:
            return False

        try:
            return await self._send_with_retry(notification)
        except Exception as e:
            log.error(f"Telegram notification error (after retries): {e}")
            return False

    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()

    def _format_message(self, notification: Notification) -> str:
        """Format message for Telegram."""
        group = notification.error_group

        text = "🚨 *ERROR REPORT*\n\n"
        text += f"📌 *Type:* `{group.exception_type}`\n"
        text += f"💬 *Message:* {truncate_text(group.message, 200)}\n\n"

        if group.events and group.events[0].context:
            event = group.events[0]
            if event.context.get("environment"):
                text += f"🌍 *Environment:* `{event.context['environment']}`\n"
            if event.context.get("release_version"):
                text += f"🏷 *Version:* `{event.context['release_version']}`\n"

        text += f"\n🔍 *Count:* {group.count} times\n"
        text += f"🕒 *First seen:* `{format_datetime_utc(group.first_seen)}`\n"
        text += f"🕒 *Last seen:* `{format_datetime_utc(group.last_seen)}`\n"

        if group.events and group.events[0].context:
            text += "\n📄 *Context:*\n"
            for key, value in list(group.events[0].context.items())[:5]:
                if key not in ("environment", "release_version"):
                    text += f"• {key}: `{truncate_text(str(value), 50)}`\n"

        if group.events and group.events[0].stack_trace:
            trace = format_stack_trace(group.events[0].stack_trace, max_lines=10)
            text += f"\n📋 *Stack Trace:*\n```\n{trace}\n```\n"

        # Ensure message fits within Telegram limit
        return self._ensure_telegram_limit(text)

    def _ensure_telegram_limit(self, text: str, max_length: int = TELEGRAM_MESSAGE_LIMIT) -> str:
        """
        Ensure message fits within Telegram's 4096 character limit.
        
        Args:
            text: Message text to check
            max_length: Maximum allowed length (default: 4096)
            
        Returns:
            Text truncated to fit within limit with notification suffix
        """
        if len(text) <= max_length:
            return text
        
        # Truncate and add notification
        suffix = "\n\n⚠️ _Message truncated due to Telegram limit_"
        available_length = max_length - len(suffix)
        
        return text[:available_length] + suffix
