"""Multi-channel notification service with DB-based throttling."""

import time
from typing import List

from app.application.interfaces.interfaces import NotificationChannel, NotificationService
from app.core.logger import log
from app.domain.entities.error_group import ErrorGroup
from app.domain.entities.notification import Notification


class MultiChannelNotificationService(NotificationService):
    """
    Multi-channel notification service with DB-based throttling.

    Uses ErrorGroup.last_notified_at from database for throttling decisions.
    This ensures consistent behavior across application restarts.
    """

    def __init__(self, channels: List[NotificationChannel]):
        """
        Initialize service with list of notification channels.

        Throttling state is stored in database (ErrorGroup.last_notified_at),
        so it persists across application restarts.
        """
        self.channels = {type(channel).__name__: channel for channel in channels}

    def should_notify(self, group: ErrorGroup, throttle_minutes: int = 5) -> bool:
        """
        Check if should send notification based on database state.

        Args:
            group: Error group to check
            throttle_minutes: Minimum minutes between notifications

        Returns:
            True if notification should be sent

        Logic:
            - Если is_notified=False → первое уведомление, отправляем
            - Если last_notified_at=None → нет данных, отправляем
            - Если прошло меньше throttle_minutes → ждём
            - Иначе → отправляем
        """
        # Первое уведомление для этой группы
        if not group.is_notified:
            return True

        # Нет данных о времени последнего уведомления
        if group.last_notified_at is None:
            return True

        now = time.time()
        last_notified = group.last_notified_at.timestamp()

        # Проверяем throttle
        if now - last_notified < throttle_minutes * 60:
            return False

        return True

    async def notify(self, group: ErrorGroup) -> None:
        """Send notification to all available channels."""
        notification = Notification(error_group=group)

        for channel_name, channel in self.channels.items():
            if channel.is_available:
                try:
                    success = await channel.send(notification)
                    if success:
                        notification.mark_as_sent()
                except Exception as e:
                    log.error(f"Notification channel {channel_name} failed: {e}")

    async def close(self):
        """Close all notification channels."""
        for channel_name, channel in self.channels.items():
            if hasattr(channel, "close"):
                try:
                    await channel.close()
                except Exception as e:
                    log.error(f"Error closing {channel_name}: {e}")
