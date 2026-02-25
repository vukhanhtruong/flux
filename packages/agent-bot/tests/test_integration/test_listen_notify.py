import asyncio
from unittest.mock import AsyncMock

import asyncpg

from flux_bot.db.messages import MessageRepository
from flux_bot.db.migrate import run_migrations
from flux_bot.orchestrator.poller import Poller
from flux_bot.orchestrator.queue import UserQueue
from flux_bot.orchestrator.handler import make_handle_message
from flux_bot.runner.sdk import ClaudeResult


async def test_notify_trigger_fires_on_insert(pg_url):
    """Inserting a bot_message fires the NOTIFY trigger."""
    await run_migrations(pg_url)

    conn = await asyncpg.connect(pg_url)
    received = asyncio.Event()
    payloads: list[str] = []

    def listener(connection, pid, channel, payload):
        payloads.append(payload)
        received.set()

    await conn.add_listener("new_bot_message", listener)

    pool = await asyncpg.create_pool(pg_url)
    msg_repo = MessageRepository(pool)
    await msg_repo.insert(
        user_id="tg:notify-test", channel="telegram", platform_id="999", text="trigger test"
    )

    await asyncio.wait_for(received.wait(), timeout=2.0)
    assert len(payloads) == 1

    await conn.remove_listener("new_bot_message", listener)
    await conn.close()
    await pool.close()


async def test_full_flow_with_listen_notify(pg_url):
    """Full pipeline: insert -> NOTIFY -> Poller wakes -> handler called promptly."""
    await run_migrations(pg_url)
    pool = await asyncpg.create_pool(pg_url)

    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM bot_messages")
        await conn.execute("DELETE FROM bot_sessions")

    msg_repo = MessageRepository(pool)
    session_repo = AsyncMock()
    session_repo.get_session_id = AsyncMock(return_value=None)
    session_repo.upsert_session_id = AsyncMock()

    mock_channel = AsyncMock()
    mock_runner = AsyncMock()
    mock_runner.run.return_value = ClaudeResult(
        text="Got it!", session_id="sess-ln-1"
    )
    profile_repo = AsyncMock()
    profile_repo.get_by_user_id = AsyncMock(return_value=None)

    channels = {"telegram": mock_channel}
    handle_message = make_handle_message(
        runner=mock_runner,
        msg_repo=msg_repo,
        session_repo=session_repo,
        profile_repo=profile_repo,
        channels=channels,
    )

    queue = UserQueue(handler=handle_message)
    await queue.start()

    poller = Poller(
        message_repo=msg_repo,
        queue=queue,
        poll_interval=2.0,
        database_url=pg_url,
        fallback_poll_interval=30.0,
    )

    poller_task = asyncio.create_task(poller.start())

    # Give listener time to set up
    await asyncio.sleep(0.1)

    await msg_repo.insert(
        user_id="tg:ln-user", channel="telegram", platform_id="ln-42", text="hello notify"
    )

    # Should be processed within ~0.5s (not 30s fallback)
    for _ in range(20):
        await asyncio.sleep(0.1)
        if mock_channel.send_message.called:
            break

    mock_channel.send_message.assert_called_once_with("ln-42", "Got it!")

    poller.stop()
    await poller.close()
    poller_task.cancel()
    try:
        await poller_task
    except asyncio.CancelledError:
        pass

    queue.stop()
    await pool.close()
