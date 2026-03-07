"""Polls bot_messages table for pending messages and dispatches to queue.

With SQLite, uses simple polling (no LISTEN/NOTIFY).
"""

import asyncio
import structlog

from flux_bot.db.messages import MessageRepository

logger = structlog.get_logger(__name__)


class Poller:
    def __init__(
        self,
        message_repo: MessageRepository,
        queue,  # UserQueue
        poll_interval: float = 2.0,
    ):
        self.message_repo = message_repo
        self.queue = queue
        self.poll_interval = poll_interval
        self._running = False
        self._notify_event = asyncio.Event()

    async def start(self) -> None:
        """Start the polling loop."""
        self._running = True
        logger.info(f"Poller started (interval={self.poll_interval}s)")
        while self._running:
            try:
                await self._poll_once()
            except Exception:
                logger.exception("Error in poll cycle")
            self._notify_event.clear()
            try:
                await asyncio.wait_for(
                    self._notify_event.wait(), timeout=self.poll_interval
                )
            except asyncio.TimeoutError:
                pass

    def stop(self) -> None:
        self._running = False
        self._notify_event.set()

    def notify(self) -> None:
        """Wake the poller immediately (called by EventBus subscriber)."""
        self._notify_event.set()

    async def close(self) -> None:
        """No-op — no dedicated connections to close with SQLite."""
        pass

    async def _poll_once(self) -> None:
        """Fetch pending messages and dispatch to queue."""
        messages = await self.message_repo.fetch_pending()
        for msg in messages:
            await self.message_repo.mark_processing(msg["id"])
            await self.queue.enqueue(msg)
