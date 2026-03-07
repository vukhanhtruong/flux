"""Tests for the Poller — SQLite-based polling with notify() wakeup."""
import asyncio
from unittest.mock import AsyncMock

from flux_bot.orchestrator.poller import Poller


async def test_poller_fetches_pending_and_dispatches():
    """Poller fetches pending messages and dispatches each to the queue."""
    msg_repo = AsyncMock()
    msg_repo.fetch_pending.return_value = [
        {"id": 1, "user_id": "tg:123", "channel": "telegram", "text": "hello", "image_path": None},
        {"id": 2, "user_id": "tg:456", "channel": "telegram", "text": "hi", "image_path": None},
    ]
    msg_repo.mark_processing = AsyncMock()

    queue = AsyncMock()

    poller = Poller(message_repo=msg_repo, queue=queue, poll_interval=0.1)
    await poller._poll_once()

    assert msg_repo.mark_processing.call_count == 2
    assert queue.enqueue.call_count == 2


async def test_poller_skips_when_no_pending():
    """Poller does nothing when there are no pending messages."""
    msg_repo = AsyncMock()
    msg_repo.fetch_pending.return_value = []
    queue = AsyncMock()

    poller = Poller(message_repo=msg_repo, queue=queue, poll_interval=0.1)
    await poller._poll_once()

    queue.enqueue.assert_not_called()


async def test_notify_sets_event():
    """Calling notify() sets the internal event so the poll loop wakes."""
    msg_repo = AsyncMock()
    queue = AsyncMock()
    poller = Poller(message_repo=msg_repo, queue=queue)

    assert not poller._notify_event.is_set()
    poller.notify()
    assert poller._notify_event.is_set()


async def test_notify_event_wakes_poll_loop():
    """Setting the notify event wakes the poll loop before the fallback interval."""
    msg_repo = AsyncMock()
    msg_repo.fetch_pending.return_value = []
    queue = AsyncMock()

    poller = Poller(
        message_repo=msg_repo,
        queue=queue,
        poll_interval=30.0,
    )

    async def fire_event():
        await asyncio.sleep(0.05)
        poller.notify()
        await asyncio.sleep(0.05)
        poller.stop()

    asyncio.create_task(fire_event())
    await asyncio.wait_for(poller.start(), timeout=2.0)

    # _poll_once should have been called at least twice (initial + after notify wakeup)
    assert msg_repo.fetch_pending.call_count >= 2


async def test_close_is_noop():
    """close() is safe — no dedicated connections with SQLite."""
    msg_repo = AsyncMock()
    queue = AsyncMock()
    poller = Poller(message_repo=msg_repo, queue=queue)

    await poller.close()  # should not raise


async def test_stop_sets_event_to_wake_loop():
    """stop() sets the notify event so the loop exits promptly."""
    msg_repo = AsyncMock()
    queue = AsyncMock()
    poller = Poller(message_repo=msg_repo, queue=queue)

    poller.stop()
    assert poller._notify_event.is_set()
