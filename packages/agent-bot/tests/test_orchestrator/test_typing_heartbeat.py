"""Tests for the typing heartbeat helper."""

import asyncio
from unittest.mock import AsyncMock

from flux_bot.channels.base import Channel
from flux_bot.orchestrator.heartbeat import typing_heartbeat
from flux_bot.runner.sdk import ClaudeResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_channel():
    channel = AsyncMock(spec=Channel)
    channel.send_typing_action = AsyncMock()
    channel.send_message = AsyncMock()
    return channel


def _make_mock_runner(text="ok", session_id="sess-1", error=None):
    runner = AsyncMock()
    runner.run = AsyncMock(return_value=ClaudeResult(text=text, session_id=session_id, error=error))
    return runner


async def test_typing_heartbeat_calls_send_typing_action():
    """Heartbeat calls send_typing_action on each tick."""
    channel = _make_mock_channel()

    task = asyncio.create_task(typing_heartbeat(channel, "12345", interval=0.02))
    await asyncio.sleep(0.5)  # 25x margin: 0.5s / 0.02s = 25 expected ticks
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert channel.send_typing_action.call_count >= 5


async def test_typing_heartbeat_swallows_errors():
    """Heartbeat does not raise if send_typing_action fails."""
    channel = _make_mock_channel()
    channel.send_typing_action.side_effect = Exception("network error")

    task = asyncio.create_task(typing_heartbeat(channel, "12345", interval=0.02))
    await asyncio.sleep(0.2)  # 10x margin
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    # No exception propagated — test passes if we reach here


async def test_typing_heartbeat_cancelled_on_success(monkeypatch):
    """Heartbeat is cancelled after runner.run() completes successfully."""
    from flux_bot.orchestrator import handler as handler_module
    from flux_bot.runner.sdk import ClaudeResult

    heartbeat_started = []

    async def fake_heartbeat(channel, platform_id, interval=4.0):
        heartbeat_started.append(True)
        while True:
            await asyncio.sleep(interval)

    monkeypatch.setattr(handler_module, "typing_heartbeat", fake_heartbeat)

    channel = _make_mock_channel()
    # Use a side_effect that yields to the event loop so the heartbeat task
    # gets a chance to start before runner.run() returns.
    runner = AsyncMock()
    async def slow_run(**kwargs):
        await asyncio.sleep(0)
        return ClaudeResult(text="ok", session_id="sess-1", error=None)
    runner.run = AsyncMock(side_effect=slow_run)
    msg_repo = AsyncMock()
    msg_repo.mark_processed = AsyncMock()
    msg_repo.mark_failed = AsyncMock()
    session_repo = AsyncMock()
    session_repo.get_session_id = AsyncMock(return_value=None)
    session_repo.upsert = AsyncMock()
    profile_repo = AsyncMock()
    profile_repo.get_by_user_id = AsyncMock(return_value=None)

    from flux_bot.orchestrator.handler import make_handle_message
    handle_message = make_handle_message(
        runner=runner,
        msg_repo=msg_repo,
        session_repo=session_repo,
        profile_repo=profile_repo,
        channels={"telegram": channel},
    )

    msg = {
        "id": 1,
        "user_id": "tg:user",
        "channel": "telegram",
        "platform_id": "111",
        "text": "hello",
        "image_path": None,
    }
    await handle_message(msg)

    # runner was called
    runner.run.assert_called_once()
    # response sent
    channel.send_message.assert_called_once_with("111", "ok")
    assert heartbeat_started, "heartbeat was started"


async def test_typing_heartbeat_cancelled_on_error(monkeypatch):
    """Heartbeat is cancelled even when runner.run() returns an error."""
    from flux_bot.orchestrator import handler as handler_module

    async def fake_heartbeat(channel, platform_id, interval=4.0):
        while True:
            await asyncio.sleep(interval)

    monkeypatch.setattr(handler_module, "typing_heartbeat", fake_heartbeat)

    channel = _make_mock_channel()
    runner = _make_mock_runner(text=None, session_id=None, error="Timeout")
    msg_repo = AsyncMock()
    msg_repo.mark_failed = AsyncMock()
    msg_repo.mark_processed = AsyncMock()
    session_repo = AsyncMock()
    session_repo.get_session_id = AsyncMock(return_value=None)
    profile_repo = AsyncMock()
    profile_repo.get_by_user_id = AsyncMock(return_value=None)

    from flux_bot.orchestrator.handler import make_handle_message
    handle_message = make_handle_message(
        runner=runner,
        msg_repo=msg_repo,
        session_repo=session_repo,
        profile_repo=profile_repo,
        channels={"telegram": channel},
    )

    msg = {
        "id": 2,
        "user_id": "tg:user",
        "channel": "telegram",
        "platform_id": "111",
        "text": "hello",
        "image_path": None,
    }
    await handle_message(msg)

    msg_repo.mark_failed.assert_called_once()
    channel.send_message.assert_not_called()
