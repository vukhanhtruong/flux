"""Integration test: full message flow with SQLite database."""
import asyncio
from unittest.mock import AsyncMock

from flux_bot.db.messages import MessageRepository
from flux_bot.db.sessions import SessionRepository
from flux_bot.orchestrator.poller import Poller
from flux_bot.orchestrator.queue import UserQueue
from flux_bot.orchestrator.handler import make_handle_message
from flux_bot.runner.sdk import ClaudeResult


async def test_full_message_flow(sqlite_db):
    """Full flow: message inserted -> polled -> processed -> marked done."""
    msg_repo = MessageRepository(sqlite_db)
    session_repo = SessionRepository(sqlite_db)

    mock_channel = AsyncMock()
    mock_runner = AsyncMock()
    mock_runner.run.return_value = ClaudeResult(
        text="Recorded 50k lunch expense!", session_id="sess-new-123"
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
    poller = Poller(message_repo=msg_repo, queue=queue, poll_interval=0.1)

    await msg_repo.insert(
        user_id="tg:truong-vu", channel="telegram", platform_id="123", text="spent 50k lunch"
    )

    await poller._poll_once()
    await asyncio.sleep(0.3)

    mock_channel.send_message.assert_called_once_with("123", "Recorded 50k lunch expense!")

    session_id = await session_repo.get_session_id("tg:truong-vu")
    assert session_id == "sess-new-123"

    pending = await msg_repo.fetch_pending()
    assert len(pending) == 0

    queue.stop()
