"""Test that the Poller notify mechanism wakes the poll loop promptly.

With SQLite, there is no LISTEN/NOTIFY. Instead, external callers (e.g. EventBus
subscribers) call poller.notify() to wake the loop immediately.
"""
import asyncio
from unittest.mock import AsyncMock

from flux_bot.orchestrator.poller import Poller


async def test_notify_wakes_poller_immediately():
    """Calling poller.notify() wakes the poll loop before the fallback interval."""
    msg_repo = AsyncMock()
    msg_repo.fetch_pending.return_value = []
    queue = AsyncMock()

    poller = Poller(message_repo=msg_repo, queue=queue, poll_interval=30.0)

    async def fire_notify():
        await asyncio.sleep(0.05)
        poller.notify()
        await asyncio.sleep(0.05)
        poller.stop()

    asyncio.create_task(fire_notify())
    await asyncio.wait_for(poller.start(), timeout=2.0)

    # _poll_once should have been called at least twice (initial + after notify wakeup)
    assert msg_repo.fetch_pending.call_count >= 2
