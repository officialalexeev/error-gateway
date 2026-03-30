"""ProcessErrorUseCase — main business logic orchestrator."""

import time
from dataclasses import dataclass

from app.application.dto.dto import ErrorEventDTO
from app.application.interfaces.interfaces import LokiService, NotificationService
from app.core.logger import log
from app.core.metrics import ERROR_GROUPS_TOTAL, ERROR_PROCESSED, ERROR_PROCESSING_TIME, ERROR_TOTAL
from app.domain.entities.error_event import ErrorEvent
from app.domain.entities.error_group import ErrorGroup
from app.domain.repositories.interfaces import ErrorEventRepository, ErrorGroupRepository
from app.domain.services.services import FingerprintService, MaskingService


@dataclass
class ProcessErrorUseCase:
    """Use case for processing incoming errors."""

    event_repo: ErrorEventRepository
    group_repo: ErrorGroupRepository
    notification_service: NotificationService
    fingerprint_service: FingerprintService
    masking_service: MaskingService
    throttle_minutes: int = 5
    loki_client: LokiService | None = None

    async def execute(self, dto: ErrorEventDTO) -> ErrorGroup:
        """Execute use case and process error."""
        _start = time.perf_counter()

        # 1. Merge environment/release_version into context, then mask all fields
        raw_context = dict(dto.context)
        if dto.environment:
            raw_context.setdefault("environment", dto.environment)
        if dto.release_version:
            raw_context.setdefault("release_version", dto.release_version)

        masked_message = self.masking_service.mask_string(dto.message)
        masked_stack_trace = (
            self.masking_service.mask_string(dto.stack_trace)
            if dto.stack_trace is not None
            else None
        )
        masked_context = self.masking_service.mask(raw_context)

        # 2. Create domain entity
        event = ErrorEvent(
            message=masked_message,
            exception_type=dto.exception_type,
            stack_trace=masked_stack_trace,
            context=masked_context,
        )

        # 3. Generate fingerprint
        fingerprint = self.fingerprint_service.generate(
            exception_type=event.exception_type,
            message=event.message,
            stack_trace=event.stack_trace,
        )
        event.fingerprint = fingerprint

        # 4. Get or create group
        group = await self.group_repo.get_or_create_by_fingerprint(fingerprint, event)
        if group.count == 1:  # newly created group
            ERROR_GROUPS_TOTAL.inc()

        # 5. Save event
        await self.event_repo.save(event, group)

        # 6. Attach event so notification formatters can access context/environment/version
        group.events = [event]

        # 7. Send notification (if needed)
        # IMPORTANT: Сначала отправляем notification, потом обновляем БД для atomicity
        # Если notify() упадёт — is_notified останется False, следующая попытка через throttle_minutes
        if self.notification_service.should_notify(group, self.throttle_minutes):
            try:
                # Сначала отправить notification
                await self.notification_service.notify(group)

                # Если успешно — обновить БД
                group.mark_as_notified()
                await self.group_repo.update(group)

                log.info(
                    f"Notification sent for group {group.id}",
                    extra={"event": "notification_sent", "group_id": str(group.id)},
                )
            except Exception as e:
                # Если notification failed — НЕ обновляем is_notified
                # Следующая попытка будет через throttle_minutes
                log.error(
                    f"Failed to send notification for group {group.id}: {e}",
                    extra={
                        "event": "notification_failed",
                        "group_id": str(group.id),
                        "error": str(e),
                    },
                )

        # 8. Ship to Loki (fire-and-forget: LokiClient handles its own exceptions)
        if self.loki_client is not None:
            await self.loki_client.send_error(group)

        # 9. Record Prometheus metrics
        _elapsed = time.perf_counter() - _start
        ERROR_TOTAL.labels(
            exception_type=event.exception_type,
            environment=dto.environment or "unknown",
            release_version=dto.release_version or "unknown",
        ).inc()
        ERROR_PROCESSED.labels(exception_type=event.exception_type).inc()
        ERROR_PROCESSING_TIME.labels(exception_type=event.exception_type).observe(_elapsed)

        return group
