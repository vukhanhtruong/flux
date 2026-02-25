"""Outbound message worker — delivers bot_outbound_messages to channels.

Uses LISTEN/NOTIFY for near-instant delivery + fallback polling.
"""

import asyncio
import logging

import asyncpg

from flux_bot.db.outbound import OutboundRepository

logger = logging.getLogger(__name__)

CHANNEL_PREFIXES = {
    "tg": "telegram",
    "wa": "whatsapp",
}


def parse_channel_prefix(user_id: str) -> tuple[str | None, str]:
    """Parse 'tg:12345' into ('telegram', '12345'). Returns (None, user_id) if unrecognized."""
    if ":" in user_id:
        prefix, platform_id = user_id.split(":", 1)
        return CHANNEL_PREFIXES.get(prefix), platform_id
    return None, user_id


class OutboundWorker:
    def __init__(
        self,
        outbound_repo: OutboundRepository,
        channels: dict,
        poll_interval: float = 2.0,
        database_url: str | None = None,
        fallback_poll_interval: float = 30.0,
    ):
        self.outbound_repo = outbound_repo
        self.channels = channels
        self.poll_interval = poll_interval
        self.database_url = database_url
        self.fallback_poll_interval = fallback_poll_interval
        self._running = False
        self._listener_conn: asyncpg.Connection | None = None
        self._notify_event = asyncio.Event()

    async def start(self) -> None:
        """Start the outbound delivery loop."""
        self._running = True
        listener_active = await self._setup_listener()
        interval = self.fallback_poll_interval if listener_active else self.poll_interval
        logger.info(
            f"OutboundWorker started (interval={interval}s, "
            f"listener={'active' if listener_active else 'inactive'})"
        )
        while self._running:
            try:
                await self._deliver_once()
            except Exception:
                logger.exception("Error in outbound delivery cycle")
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
                    "new_outbound_message", self._on_notify
                )
                await self._listener_conn.close()
            except Exception:
                logger.exception("Error closing outbound listener connection")
            finally:
                self._listener_conn = None

    async def _setup_listener(self) -> bool:
        """Open a dedicated connection for LISTEN/NOTIFY. Returns True on success."""
        if not self.database_url:
            return False
        try:
            conn = await asyncpg.connect(self.database_url)
            await conn.add_listener("new_outbound_message", self._on_notify)
            self._listener_conn = conn
            logger.info("LISTEN/NOTIFY listener active on 'new_outbound_message'")
            return True
        except Exception:
            logger.exception("Failed to set up outbound LISTEN/NOTIFY")
            self._listener_conn = None
            return False

    def _on_notify(self, connection, pid, channel, payload) -> None:
        self._notify_event.set()

    async def _deliver_once(self) -> None:
        """Fetch pending outbound messages and deliver them."""
        messages = await self.outbound_repo.fetch_pending()
        for msg in messages:
            channel_name, platform_id = parse_channel_prefix(msg["user_id"])
            channel = self.channels.get(channel_name) if channel_name else None

            if channel is None:
                logger.warning(
                    f"No channel handler for user_id={msg['user_id']} "
                    f"(resolved prefix: {channel_name!r})"
                )
                await self.outbound_repo.mark_failed(
                    msg["id"], "No channel handler for prefix"
                )
                continue

            try:
                await channel.send_outbound(platform_id, msg["text"], msg.get("sender"))
                await self.outbound_repo.mark_sent(msg["id"])
            except Exception as e:
                logger.exception(f"Failed to deliver outbound message {msg['id']}")
                await self.outbound_repo.mark_failed(msg["id"], str(e))
