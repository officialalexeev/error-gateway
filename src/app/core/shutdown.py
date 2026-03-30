"""Graceful shutdown manager for async application lifecycle."""

import asyncio
from typing import Any, Callable, Coroutine


class ShutdownManager:
    """
    Manager for graceful application shutdown.

    Handles cleanup of resources (database connections, HTTP clients, etc.)
    when the application receives a shutdown signal.
    """

    def __init__(self):
        """Initialize shutdown manager."""
        self._shutdown_handlers: list[Callable[[], Coroutine[Any, Any, None]]] = []
        self._is_shutting_down = False
        self._lock = asyncio.Lock()

    def register(self, handler: Callable[[], Coroutine[Any, Any, None]]) -> None:
        """
        Register a shutdown handler.

        Args:
            handler: Async callable to be executed on shutdown.
        """
        self._shutdown_handlers.append(handler)

    async def shutdown(self) -> None:
        """
        Execute all registered shutdown handlers.

        Handlers are executed sequentially. If one fails, the rest still run.
        """
        async with self._lock:
            if self._is_shutting_down:
                return
            self._is_shutting_down = True

        for handler in self._shutdown_handlers:
            try:
                await handler()
            except Exception as e:
                # Log but continue with other handlers
                from app.core.logger import log

                log.error(f"Shutdown handler error: {e}")

    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self._is_shutting_down
