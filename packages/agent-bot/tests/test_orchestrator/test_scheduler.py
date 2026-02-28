from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
import pytest

from flux_bot.orchestrator.scheduler import SchedulerWorker


_ONCE_TASK = {
    "id": 1, "user_id": "tg:12345",
    "prompt": "Send me a report",
    "schedule_type": "once", "schedule_value": "2026-03-01T10:00:00",
}
_CRON_TASK = {
    "id": 2, "user_id": "tg:12345",
    "prompt": "Daily summary",
    "schedule_type": "cron", "schedule_value": "0 9 * * *",
}
_INTERVAL_TASK = {
    "id": 3, "user_id": "tg:12345",
    "prompt": "Poll status",
    "schedule_type": "interval", "schedule_value": "300000",
}


@pytest.fixture
def mock_task_repo():
    return AsyncMock()


@pytest.fixture
def mock_msg_repo():
    return AsyncMock()


@pytest.fixture
def worker(mock_task_repo, mock_msg_repo):
    return SchedulerWorker(
        task_repo=mock_task_repo,
        message_repo=mock_msg_repo,
        poll_interval=30.0,
    )


async def test_once_task_injects_message_and_completes(worker, mock_task_repo, mock_msg_repo):
    mock_task_repo.fetch_due_tasks.return_value = [_ONCE_TASK]
    mock_msg_repo.insert.return_value = 10
    await worker._fire_once()
    mock_msg_repo.insert.assert_called_once_with(
        user_id="tg:12345", channel="telegram", platform_id="12345",
        text="Send me a report",
    )
    mock_task_repo.mark_completed.assert_called_once_with(1)
    mock_task_repo.advance_next_run.assert_not_called()


async def test_cron_task_injects_message_and_advances(worker, mock_task_repo, mock_msg_repo):
    mock_task_repo.fetch_due_tasks.return_value = [_CRON_TASK]
    mock_msg_repo.insert.return_value = 11
    await worker._fire_once()
    mock_msg_repo.insert.assert_called_once()
    mock_task_repo.advance_next_run.assert_called_once()
    task_id, next_run = mock_task_repo.advance_next_run.call_args.args
    assert task_id == 2
    assert next_run > datetime.now(UTC)


async def test_interval_task_injects_message_and_advances(worker, mock_task_repo, mock_msg_repo):
    mock_task_repo.fetch_due_tasks.return_value = [_INTERVAL_TASK]
    mock_msg_repo.insert.return_value = 12
    await worker._fire_once()
    mock_msg_repo.insert.assert_called_once()
    mock_task_repo.advance_next_run.assert_called_once()
    task_id, next_run = mock_task_repo.advance_next_run.call_args.args
    assert task_id == 3
    assert next_run.tzinfo is not None, "advanced next_run must be timezone-aware"
    # interval = 300000ms = 5min from now (roughly)
    assert next_run > datetime.now(UTC) + timedelta(minutes=4)


async def test_no_due_tasks_is_noop(worker, mock_task_repo, mock_msg_repo):
    mock_task_repo.fetch_due_tasks.return_value = []
    await worker._fire_once()
    mock_msg_repo.insert.assert_not_called()


async def test_unknown_channel_prefix_skips_task(worker, mock_task_repo, mock_msg_repo):
    task = {**_ONCE_TASK, "user_id": "discord:99999"}
    mock_task_repo.fetch_due_tasks.return_value = [task]
    await worker._fire_once()  # must not raise
    mock_msg_repo.insert.assert_not_called()
    mock_task_repo.mark_completed.assert_not_called()


def test_compute_next_run_cron_respects_user_timezone(worker):
    """_compute_next_run with user_timezone yields next_run in user local time, converted to UTC."""
    next_run = worker._compute_next_run("cron", "0 20 * * *", "Asia/Bangkok")
    next_run_utc = next_run.astimezone(UTC)
    # 8 PM Bangkok (UTC+7) = 1 PM UTC
    assert next_run_utc.hour == 13
    assert next_run_utc.minute == 0
    assert next_run_utc.tzinfo is not None


async def test_cron_task_uses_user_timezone(worker, mock_task_repo, mock_msg_repo):
    """Cron advance must use user_timezone from the task dict, not UTC."""
    task = {
        "id": 4, "user_id": "tg:12345",
        "prompt": "Evening reminder",
        "schedule_type": "cron", "schedule_value": "0 20 * * *",
        "user_timezone": "Asia/Bangkok",  # ICT = UTC+7
    }
    mock_task_repo.fetch_due_tasks.return_value = [task]
    mock_msg_repo.insert.return_value = 14
    await worker._fire_once()
    _, next_run = mock_task_repo.advance_next_run.call_args.args
    next_run_utc = next_run.astimezone(UTC)
    # 8 PM Bangkok (UTC+7) = 1 PM UTC
    assert next_run_utc.hour == 13
    assert next_run_utc.minute == 0
