"""Typing heartbeat — re-sends typing action every N seconds."""

import asyncio
import structlog

logger = structlog.get_logger(__name__)


async def typing_heartbeat(channel, platform_id: str, interval: float = 4.0) -> None:
    """Send typing action repeatedly until cancelled."""
    while True:
        try:
            await channel.send_typing_action(platform_id)
        except Exception:
            logger.debug("typing action failed (non-critical)", exc_info=True)
        await asyncio.sleep(interval)
