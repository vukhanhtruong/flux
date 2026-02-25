"""Polls bot_messages table for pending messages and dispatches to queue.

Supports hybrid LISTEN/NOTIFY + fallback polling for near-instant wakeups.
"""

import asyncio
import logging

import asyncpg

from flux_bot.db.messages import MessageRepository

logger = logging.getLogger(__name__)


class Poller:
    def __init__(
        self,
        message_repo: MessageRepository,
        queue,  # UserQueue
        poll_interval: float = 2.0,
        database_url: str | None = None,
        fallback_poll_interval: float = 30.0,
    ):
        self.message_repo = message_repo
        self.queue = queue
        self.poll_interval = poll_interval
        self.database_url = database_url
        self.fallback_poll_interval = fallback_poll_interval
        self._running = False
        self._listener_conn: asyncpg.Connection | None = None
        self._notify_event = asyncio.Event()

    async def start(self) -> None:
        """Start the polling loop."""
        self._running = True
        listener_active = await self._setup_listener()
        interval = self.fallback_poll_interval if listener_active else self.poll_interval
        logger.info(
            f"Poller started (interval={interval}s, listener={'active' if listener_active else 'inactive'})"
        )
        while self._running:
            try:
                await self._poll_once()
            except Exception:
                logger.exception("Error in poll cycle")
            self._notify_event.clear()
            try:
                await asyncio.wait_for(self._notify_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    def stop(self) -> None:
        self._running = False
        self._notify_event.set()

    async def close(self) -> None:
        """Close the dedicated listener connection."""
        if self._listener_conn is not None:
            try:
                await self._listener_conn.remove_listener(
                    "new_bot_message", self._on_notify
                )
                await self._listener_conn.close()
            except Exception:
                logger.exception("Error closing listener connection")
            finally:
                self._listener_conn = None

    async def _setup_listener(self) -> bool:
        """Open a dedicated connection for LISTEN/NOTIFY. Returns True on success."""
        if not self.database_url:
            return False
        try:
            conn = await asyncpg.connect(self.database_url)
            await conn.add_listener("new_bot_message", self._on_notify)
            self._listener_conn = conn
            logger.info("LISTEN/NOTIFY listener active on 'new_bot_message'")
            return True
        except Exception:
            logger.exception("Failed to set up LISTEN/NOTIFY, falling back to polling")
            self._listener_conn = None
            return False

    def _on_notify(self, connection, pid, channel, payload) -> None:
        """Synchronous callback invoked by asyncpg on NOTIFY."""
        self._notify_event.set()

    async def _poll_once(self) -> None:
        """Fetch pending messages and dispatch to queue."""
        messages = await self.message_repo.fetch_pending()
        for msg in messages:
            await self.message_repo.mark_processing(msg["id"])
            await self.queue.enqueue(msg)
