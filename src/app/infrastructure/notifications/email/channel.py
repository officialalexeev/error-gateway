"""Email notification channel via SMTP."""

import html as html_lib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import aiosmtplib
from app.application.interfaces.interfaces import NotificationChannel
from app.core.logger import log
from app.domain.entities.notification import Notification
from app.infrastructure.notifications.utils import (
    format_context_summary,
    format_datetime_utc,
    format_stack_trace,
    truncate_text,
)


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel via SMTP with connection caching."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        email_from: str,
        email_to: List[str],
    ):
        """Initialize email channel with SMTP configuration."""
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port or 587
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.email_from = email_from or smtp_user
        self.email_to = email_to

        # SMTP connection cache (lazy initialization)
        self._smtp: aiosmtplib.SMTP | None = None
        self._connected: bool = False

    @property
    def is_available(self) -> bool:
        """Check if Email is configured."""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password and self.email_to)

    async def _get_smtp(self) -> aiosmtplib.SMTP:
        """
        Get or create SMTP connection with caching.

        Lazily initializes SMTP connection on first use.
        Reconnects if connection was lost.

        :return: Connected SMTP instance
        :raises: Exception if connection fails
        """
        # Create new SMTP instance if needed
        if self._smtp is None:
            self._smtp = aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                timeout=10,
            )

        # Connect if not connected
        if not self._connected:
            try:
                await self._smtp.connect()
                await self._smtp.starttls()
                await self._smtp.login(self.smtp_user, self.smtp_password)
                self._connected = True
                log.debug(
                    f"SMTP connection established: {self.smtp_host}:{self.smtp_port}",
                    extra={"event": "smtp_connected"},
                )
            except Exception as e:
                log.error(f"SMTP connection failed: {e}")
                self._smtp = None
                self._connected = False
                raise

        return self._smtp

    async def close(self) -> None:
        """Close SMTP connection."""
        if self._smtp is not None:
            try:
                await self._smtp.quit()
                log.debug(
                    f"SMTP connection closed: {self.smtp_host}:{self.smtp_port}",
                    extra={"event": "smtp_closed"},
                )
            except Exception:
                pass  # Ignore errors on close
            finally:
                self._smtp = None
                self._connected = False

    async def send(self, notification: Notification) -> bool:
        """Send notification via Email with connection caching."""
        if not self.is_available:
            return False

        try:
            message = self._create_message(notification)

            # Get cached SMTP connection
            smtp = await self._get_smtp()

            # Send with reconnect on failure
            try:
                await smtp.send_message(message)
                return True
            except aiosmtplib.errors.SMTPServerDisconnected:
                # Connection lost — reconnect and retry
                log.warning(
                    "SMTP connection lost, reconnecting...",
                    extra={"event": "smtp_reconnect"},
                )
                self._connected = False
                smtp = await self._get_smtp()
                await smtp.send_message(message)
                return True

        except aiosmtplib.errors.SMTPException as e:
            log.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            log.error(f"Email notification error: {e}")
            return False

    def _create_message(self, notification: Notification) -> MIMEMultipart:
        """Create email message."""
        group = notification.error_group

        message = MIMEMultipart("alternative")
        message["Subject"] = f"🚨 Error: {group.exception_type}"
        message["From"] = self.email_from
        message["To"] = ", ".join(self.email_to)

        text = self._format_text(group)
        message.attach(MIMEText(text, "plain"))

        html = self._format_html(group)
        message.attach(MIMEText(html, "html"))

        return message

    def _format_text(self, group) -> str:
        """Format email text."""
        text = "🚨 ERROR REPORT\n\n"
        text += f"📌 Type: {group.exception_type}\n"
        text += f"💬 Message: {truncate_text(group.message, 200)}\n\n"

        if group.events and group.events[0].context:
            event = group.events[0]
            if event.context.get("environment"):
                text += f"🌍 Environment: {event.context['environment']}\n"
            if event.context.get("release_version"):
                text += f"🏷 Version: {event.context['release_version']}\n"

        text += f"\n🔍 Count: {group.count} times\n"
        text += f"🕒 First seen: {format_datetime_utc(group.first_seen)}\n"
        text += f"🕒 Last seen: {format_datetime_utc(group.last_seen)}\n"

        if group.events and group.events[0].context:
            ctx = {
                k: v
                for k, v in group.events[0].context.items()
                if k not in ("environment", "release_version")
            }
            if ctx:
                text += "\n📄 Context:\n" + format_context_summary(ctx) + "\n"

        if group.events and group.events[0].stack_trace:
            trace = format_stack_trace(group.events[0].stack_trace, max_lines=15)
            text += f"\n📋 Stack Trace:\n{trace}\n"

        return text

    def _format_html(self, group) -> str:
        """Format email HTML."""
        e = html_lib.escape
        body = "<html><body>"
        body += "<h2>🚨 ERROR REPORT</h2>"
        body += f"<p><strong>📌 Type:</strong> <code>{e(group.exception_type)}</code></p>"
        body += f"<p><strong>💬 Message:</strong> {e(truncate_text(group.message, 200))}</p>"

        if group.events and group.events[0].context:
            event = group.events[0]
            if event.context.get("environment"):
                body += f"<p><strong>🌍 Environment:</strong> <code>{e(str(event.context['environment']))}</code></p>"
            if event.context.get("release_version"):
                body += f"<p><strong>🏷 Version:</strong> <code>{e(str(event.context['release_version']))}</code></p>"

        body += f"<p><strong>🔍 Count:</strong> {group.count} times</p>"
        body += f"<p><strong>🕒 First seen:</strong> {e(format_datetime_utc(group.first_seen))}</p>"
        body += f"<p><strong>🕒 Last seen:</strong> {e(format_datetime_utc(group.last_seen))}</p>"

        if group.events and group.events[0].context:
            ctx = {
                k: v
                for k, v in group.events[0].context.items()
                if k not in ("environment", "release_version")
            }
            if ctx:
                body += "<h3>📄 Context:</h3><ul>"
                for key, value in list(ctx.items())[:5]:
                    body += f"<li><strong>{e(key)}:</strong> <code>{e(truncate_text(str(value), 50))}</code></li>"
                body += "</ul>"

        if group.events and group.events[0].stack_trace:
            trace = format_stack_trace(group.events[0].stack_trace, max_lines=15)
            body += f"<h3>📋 Stack Trace:</h3><pre>{e(trace)}</pre>"

        body += "</body></html>"
        return body
