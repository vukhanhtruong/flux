from __future__ import annotations

import structlog
from collections import defaultdict
from typing import Callable

from flux_core.events.events import Event

logger = structlog.get_logger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[type[Event], list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type[Event], handler: Callable) -> None:
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: type[Event], handler: Callable) -> None:
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def emit(self, event: Event) -> None:
        handlers = self._subscribers.get(type(event), [])
        logger.debug("Event emitted", event_type=type(event).__name__, subscribers=len(handlers))
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Event handler %s failed for %s",
                    handler.__name__,
                    type(event).__name__,
                )
