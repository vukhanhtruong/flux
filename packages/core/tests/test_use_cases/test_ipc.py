"""Tests for IPC use cases (send_message, schedule_task, list_tasks, pause, resume, cancel)."""
from unittest.mock import AsyncMock, MagicMock, patch

from flux_core.use_cases.bot import (
    CancelTask,
    ListTasks,
    PauseTask,
    ResumeTask,
    ScheduleTask,
    SendMessage,
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


# ── SendMessage ─────────────────────────────────────────────────────────


@patch("flux_core.use_cases.bot.send_message.SqliteBotOutboundRepository")
async def test_send_message(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.insert.return_value = 10

    uc = SendMessage(uow)
    result = await uc.execute(USER_ID, "Hello!", sender="bot")

    assert result["status"] == "sent"
    assert result["message_id"] == 10
    mock_repo_cls.return_value.insert.assert_called_once_with(USER_ID, "Hello!", "bot")
    uow.add_event.assert_called_once()
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.bot.send_message.SqliteBotOutboundRepository")
async def test_send_message_no_sender(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.insert.return_value = 11

    uc = SendMessage(uow)
    result = await uc.execute(USER_ID, "Test")

    assert result["status"] == "sent"
    mock_repo_cls.return_value.insert.assert_called_once_with(USER_ID, "Test", None)


# ── ScheduleTask ────────────────────────────────────────────────────────


@patch(
    "flux_core.use_cases.bot.schedule_task.SqliteBotScheduledTaskRepository"
)
async def test_schedule_task_interval(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.create.return_value = 50

    uc = ScheduleTask(uow)
    result = await uc.execute(USER_ID, "Check", "interval", "300000")

    assert result["status"] == "scheduled"
    assert result["task_id"] == 50
    uow.commit.assert_called_once()


async def test_schedule_task_invalid_cron():
    uow = _mock_uow()

    uc = ScheduleTask(uow)
    result = await uc.execute(USER_ID, "Check", "cron", "not-a-cron")

    assert result["status"] == "error"
    assert "Invalid cron" in result["message"]


async def test_schedule_task_invalid_interval():
    uow = _mock_uow()

    uc = ScheduleTask(uow)
    result = await uc.execute(USER_ID, "Check", "interval", "abc")

    assert result["status"] == "error"
    assert "Invalid interval" in result["message"]


async def test_schedule_task_negative_interval():
    uow = _mock_uow()

    uc = ScheduleTask(uow)
    result = await uc.execute(USER_ID, "Check", "interval", "-100")

    assert result["status"] == "error"
    assert "positive" in result["message"]


async def test_schedule_task_unknown_type():
    uow = _mock_uow()

    uc = ScheduleTask(uow)
    result = await uc.execute(USER_ID, "Check", "banana", "123")

    assert result["status"] == "error"
    assert "Unknown" in result["message"]


@patch(
    "flux_core.use_cases.bot.schedule_task.SqliteBotScheduledTaskRepository"
)
async def test_schedule_task_once_delay(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.create.return_value = 51

    uc = ScheduleTask(uow)
    result = await uc.execute(USER_ID, "Remind", "once", "60000")

    assert result["status"] == "scheduled"


async def test_schedule_task_once_past_timestamp():
    uow = _mock_uow()

    uc = ScheduleTask(uow)
    result = await uc.execute(
        USER_ID, "Remind", "once", "2020-01-01T00:00:00"
    )

    assert result["status"] == "error"
    assert "past" in result["message"]


@patch(
    "flux_core.use_cases.bot.schedule_task.SqliteBotScheduledTaskRepository"
)
async def test_schedule_task_cron_valid(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.create.return_value = 52

    uc = ScheduleTask(uow)
    result = await uc.execute(USER_ID, "Daily", "cron", "0 9 * * *")

    assert result["status"] == "scheduled"
    assert result["task_id"] == 52


# ── ListTasks ───────────────────────────────────────────────────────────


async def test_list_tasks():
    repo = MagicMock()
    repo.list_by_user.return_value = [
        {"id": 1, "prompt": "Check", "schedule_type": "cron"},
        {"id": 2, "prompt": "Remind", "schedule_type": "once"},
    ]

    uc = ListTasks(repo)
    result = await uc.execute(USER_ID)

    assert len(result["tasks"]) == 2
    repo.list_by_user.assert_called_once_with(USER_ID)


async def test_list_tasks_empty():
    repo = MagicMock()
    repo.list_by_user.return_value = []

    uc = ListTasks(repo)
    result = await uc.execute(USER_ID)

    assert result["tasks"] == []


# ── PauseTask ───────────────────────────────────────────────────────────


async def test_pause_task():
    uow = _mock_uow()
    cursor = MagicMock()
    cursor.rowcount = 1
    uow.conn.execute.return_value = cursor

    uc = PauseTask(uow)
    result = await uc.execute(USER_ID, 5)

    assert result["status"] == "paused"
    assert result["task_id"] == 5
    uow.commit.assert_called_once()


async def test_pause_task_not_found():
    uow = _mock_uow()
    cursor = MagicMock()
    cursor.rowcount = 0
    uow.conn.execute.return_value = cursor

    uc = PauseTask(uow)
    result = await uc.execute(USER_ID, 99)

    assert result["status"] == "error"
    assert "not found" in result["message"]


# ── ResumeTask ──────────────────────────────────────────────────────────


async def test_resume_task():
    uow = _mock_uow()
    cursor = MagicMock()
    cursor.rowcount = 1
    uow.conn.execute.return_value = cursor

    uc = ResumeTask(uow)
    result = await uc.execute(USER_ID, 5)

    assert result["status"] == "resumed"
    assert result["task_id"] == 5
    uow.commit.assert_called_once()


async def test_resume_task_not_found():
    uow = _mock_uow()
    cursor = MagicMock()
    cursor.rowcount = 0
    uow.conn.execute.return_value = cursor

    uc = ResumeTask(uow)
    result = await uc.execute(USER_ID, 99)

    assert result["status"] == "error"
    assert "not found" in result["message"]


# ── CancelTask ──────────────────────────────────────────────────────────


async def test_cancel_task():
    uow = _mock_uow()
    cursor = MagicMock()
    cursor.rowcount = 1
    uow.conn.execute.return_value = cursor

    uc = CancelTask(uow)
    result = await uc.execute(USER_ID, 5)

    assert result["status"] == "cancelled"
    assert result["task_id"] == 5
    uow.commit.assert_called_once()


async def test_cancel_task_not_found():
    uow = _mock_uow()
    cursor = MagicMock()
    cursor.rowcount = 0
    uow.conn.execute.return_value = cursor

    uc = CancelTask(uow)
    result = await uc.execute(USER_ID, 99)

    assert result["status"] == "error"
    assert "not found" in result["message"]
