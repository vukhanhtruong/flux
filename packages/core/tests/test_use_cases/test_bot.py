"""Tests for bot use cases."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from flux_core.use_cases.bot import (
    CreateScheduledTask,
    FireScheduledTask,
    ProcessMessage,
    SendOutbound,
)

USER_ID = "tg:12345"


def _mock_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.conn = MagicMock()
    uow.add_event = MagicMock()
    return uow


# ── ProcessMessage ──────────────────────────────────────────────────────


@patch("flux_core.use_cases.bot.process_message.SqliteBotSessionRepository")
@patch("flux_core.use_cases.bot.process_message.SqliteBotOutboundRepository")
@patch("flux_core.use_cases.bot.process_message.SqliteBotMessageRepository")
async def test_process_message(mock_msg_cls, mock_out_cls, mock_sess_cls):
    uow = _mock_uow()
    mock_out_cls.return_value.insert.return_value = 42

    uc = ProcessMessage(uow)
    result = await uc.execute(
        msg_id=1,
        user_id=USER_ID,
        response_text="Hello!",
        session_id="sess-123",
        sender="bot",
    )

    assert result["msg_id"] == 1
    assert result["outbound_id"] == 42
    assert result["session_id"] == "sess-123"
    mock_msg_cls.return_value.mark_processed.assert_called_once_with(1)
    mock_out_cls.return_value.insert.assert_called_once_with(USER_ID, "Hello!", "bot")
    mock_sess_cls.return_value.upsert.assert_called_once_with(USER_ID, "sess-123")
    uow.add_event.assert_called_once()
    uow.commit.assert_called_once()


# ── SendOutbound ────────────────────────────────────────────────────────


@patch("flux_core.use_cases.bot.send_outbound.SqliteBotOutboundRepository")
async def test_send_outbound_mark_sent(mock_repo_cls):
    uow = _mock_uow()

    uc = SendOutbound(uow)
    await uc.mark_sent(42)

    mock_repo_cls.return_value.mark_sent.assert_called_once_with(42)
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.bot.send_outbound.SqliteBotOutboundRepository")
async def test_send_outbound_mark_failed(mock_repo_cls):
    uow = _mock_uow()

    uc = SendOutbound(uow)
    await uc.mark_failed(42, "timeout")

    mock_repo_cls.return_value.mark_failed.assert_called_once_with(42, "timeout")
    uow.commit.assert_called_once()


# ── CreateScheduledTask ─────────────────────────────────────────────────


@patch(
    "flux_core.use_cases.bot.create_scheduled_task"
    ".SqliteBotScheduledTaskRepository"
)
async def test_create_scheduled_task(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.create.return_value = 99
    next_run = datetime(2026, 4, 1, tzinfo=UTC)

    uc = CreateScheduledTask(uow)
    task_id = await uc.execute(
        USER_ID, "Do something", "cron", "0 9 * * *", next_run
    )

    assert task_id == 99
    mock_repo_cls.return_value.create.assert_called_once()
    uow.add_event.assert_called_once()
    uow.commit.assert_called_once()


@patch(
    "flux_core.use_cases.bot.create_scheduled_task"
    ".SqliteBotScheduledTaskRepository"
)
async def test_create_scheduled_task_with_asset(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.create.return_value = 100
    next_run = datetime(2026, 4, 1, tzinfo=UTC)

    uc = CreateScheduledTask(uow)
    task_id = await uc.execute(
        USER_ID, "Process interest", "once", "2026-04-01", next_run,
        asset_id="abc-123",
    )

    assert task_id == 100
    call_kwargs = mock_repo_cls.return_value.create.call_args
    assert call_kwargs.kwargs["asset_id"] == "abc-123"


# ── FireScheduledTask ───────────────────────────────────────────────────


@patch("flux_core.use_cases.bot.fire_scheduled_task.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.bot.fire_scheduled_task.SqliteBotMessageRepository")
async def test_fire_scheduled_task_once(mock_msg_cls, mock_task_cls):
    uow = _mock_uow()
    mock_msg_cls.return_value.insert.return_value = 77

    uc = FireScheduledTask(uow)
    msg_id = await uc.execute(
        task_id=5, user_id=USER_ID, prompt="Do it", schedule_type="once"
    )

    assert msg_id == 77
    mock_msg_cls.return_value.insert.assert_called_once_with(
        user_id=USER_ID, channel="scheduler", platform_id="task:5", text="Do it"
    )
    mock_task_cls.return_value.mark_completed.assert_called_once_with(5)
    uow.add_event.assert_called_once()
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.bot.fire_scheduled_task.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.bot.fire_scheduled_task.SqliteBotMessageRepository")
async def test_fire_scheduled_task_recurring(mock_msg_cls, mock_task_cls):
    uow = _mock_uow()
    mock_msg_cls.return_value.insert.return_value = 78
    next_run = datetime(2026, 5, 1, tzinfo=UTC)

    uc = FireScheduledTask(uow)
    msg_id = await uc.execute(
        task_id=6, user_id=USER_ID, prompt="Monthly check",
        schedule_type="cron", next_run_at=next_run,
    )

    assert msg_id == 78
    mock_task_cls.return_value.mark_completed.assert_not_called()
    mock_task_cls.return_value.advance_next_run.assert_called_once_with(6, next_run)
