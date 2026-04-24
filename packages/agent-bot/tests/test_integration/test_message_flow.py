"""Integration test: full message flow with SQLite database."""
import asyncio
from unittest.mock import AsyncMock

from flux_bot.db.messages import MessageRepository
from flux_bot.db.sessions import SessionRepository
from flux_bot.orchestrator.poller import Poller
from flux_bot.orchestrator.queue import UserQueue
from flux_bot.orchestrator.handler import make_handle_message
from flux_bot.runner.result import AgentResult
from flux_bot.db.llm_config import UserLlmConfig


def _make_llm_config():
    return UserLlmConfig(
        user_id="tg:truong-vu",
        provider="anthropic",
        model="claude-sonnet-4-6",
        base_url=None,
        api_key="sk-test-key",
    )


async def test_full_message_flow(sqlite_db):
    """Full flow: message inserted -> polled -> processed -> marked done."""
    msg_repo = MessageRepository(sqlite_db)
    session_repo = SessionRepository(sqlite_db)

    mock_channel = AsyncMock()
    mock_runner = AsyncMock()
    mock_runner.run.return_value = AgentResult(
        text="Recorded 50k lunch expense!", thread_id=None
    )
    from unittest.mock import MagicMock as _MM
    _profile = _MM()
    _profile.user_id = "tg:truong-vu"
    _profile.username = "testuser"
    _profile.currency = "USD"
    _profile.timezone = "UTC"
    profile_repo = AsyncMock()
    profile_repo.get_by_user_id = AsyncMock(return_value=_profile)

    llm_config_repo = AsyncMock()
    llm_config_repo.get = AsyncMock(return_value=_make_llm_config())

    channels = {"telegram": mock_channel}
    handle_message = make_handle_message(
        runner=mock_runner,
        msg_repo=msg_repo,
        session_repo=session_repo,
        profile_repo=profile_repo,
        channels=channels,
        llm_config_repo=llm_config_repo,
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

    pending = await msg_repo.fetch_pending()
    assert len(pending) == 0

    queue.stop()
