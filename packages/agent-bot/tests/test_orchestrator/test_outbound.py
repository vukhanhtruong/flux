import asyncio
from unittest.mock import AsyncMock
import pytest

from flux_bot.orchestrator.outbound import OutboundWorker, parse_channel_prefix


@pytest.fixture
def mock_outbound_repo():
    return AsyncMock()


@pytest.fixture
def channels():
    telegram = AsyncMock()
    return {"telegram": telegram}


@pytest.fixture
def worker(mock_outbound_repo, channels):
    return OutboundWorker(
        outbound_repo=mock_outbound_repo,
        channels=channels,
        poll_interval=0.1,
    )


async def test_deliver_telegram_message(worker, mock_outbound_repo, channels):
    mock_outbound_repo.fetch_pending.return_value = [
        {"id": 1, "user_id": "tg:12345", "text": "Hello!", "sender": None},
    ]
    await worker._deliver_once()
    channels["telegram"].send_outbound.assert_called_once_with("12345", "Hello!", None)
    mock_outbound_repo.mark_sent.assert_called_once_with(1)


async def test_deliver_unknown_channel(worker, mock_outbound_repo):
    mock_outbound_repo.fetch_pending.return_value = [
        {"id": 2, "user_id": "slack:999", "text": "Oops", "sender": None},
    ]
    await worker._deliver_once()
    mock_outbound_repo.mark_failed.assert_called_once()
    args = mock_outbound_repo.mark_failed.call_args
    assert args[0][0] == 2  # msg_id


async def test_deliver_empty(worker, mock_outbound_repo):
    mock_outbound_repo.fetch_pending.return_value = []
    await worker._deliver_once()
    mock_outbound_repo.mark_sent.assert_not_called()
    mock_outbound_repo.mark_failed.assert_not_called()


async def test_parse_channel_prefix_telegram():
    assert parse_channel_prefix("tg:12345") == ("telegram", "12345")


async def test_parse_channel_prefix_whatsapp():
    assert parse_channel_prefix("wa:555") == ("whatsapp", "555")


async def test_parse_channel_prefix_unknown():
    assert parse_channel_prefix("unknown:1") == (None, "1")


async def test_parse_channel_prefix_no_colon():
    assert parse_channel_prefix("nocolon") == (None, "nocolon")


async def test_deliver_send_failure(worker, mock_outbound_repo, channels):
    """If send_outbound raises, message is marked failed."""
    channels["telegram"].send_outbound.side_effect = RuntimeError("Timeout")
    mock_outbound_repo.fetch_pending.return_value = [
        {"id": 3, "user_id": "tg:99", "text": "Fail me", "sender": "Bot"},
    ]
    await worker._deliver_once()
    mock_outbound_repo.mark_sent.assert_not_called()
    mock_outbound_repo.mark_failed.assert_called_once_with(3, "Timeout")
