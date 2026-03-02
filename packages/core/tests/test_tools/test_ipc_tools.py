from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
import pytest

from flux_core.tools.ipc_tools import (
    send_message,
    schedule_task,
    list_tasks,
    pause_task,
    resume_task,
    cancel_task,
)

_PROFILE_ROW = {
    "id": "tg:123", "username": "testuser", "platform": "telegram",
    "platform_id": "123", "currency": "USD", "timezone": "UTC", "locale": "en",
}


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.fetchrow.return_value = _PROFILE_ROW
    return db


async def test_send_message(mock_db):
    mock_db.fetchval.return_value = 42
    result = await send_message(
        user_id="tg:123", text="Hello!", sender="Bot", db=mock_db,
    )
    assert result == {"status": "sent", "message_id": 42}
    mock_db.fetchval.assert_called_once()


async def test_send_message_no_sender(mock_db):
    mock_db.fetchval.return_value = 43
    result = await send_message(
        user_id="tg:123", text="Hello!", sender=None, db=mock_db,
    )
    assert result == {"status": "sent", "message_id": 43}


async def test_schedule_task_cron(mock_db):
    mock_db.fetchval.return_value = 1
    result = await schedule_task(
        user_id="tg:123",
        prompt="Check weather",
        schedule_type="cron",
        schedule_value="0 9 * * *",
        db=mock_db,
    )
    assert result["status"] == "scheduled"
    assert result["task_id"] == 1


async def test_schedule_task_invalid_cron(mock_db):
    result = await schedule_task(
        user_id="tg:123",
        prompt="Bad",
        schedule_type="cron",
        schedule_value="not a cron",
        db=mock_db,
    )
    assert result["status"] == "error"
    assert "Invalid cron" in result["message"]


async def test_schedule_task_interval(mock_db):
    mock_db.fetchval.return_value = 2
    result = await schedule_task(
        user_id="tg:123",
        prompt="Poll API",
        schedule_type="interval",
        schedule_value="300000",
        db=mock_db,
    )
    assert result["status"] == "scheduled"
    assert result["task_id"] == 2


async def test_schedule_task_invalid_interval(mock_db):
    result = await schedule_task(
        user_id="tg:123",
        prompt="Bad",
        schedule_type="interval",
        schedule_value="-1",
        db=mock_db,
    )
    assert result["status"] == "error"


async def test_schedule_task_zero_interval(mock_db):
    result = await schedule_task(
        user_id="tg:123",
        prompt="Bad",
        schedule_type="interval",
        schedule_value="0",
        db=mock_db,
    )
    assert result["status"] == "error"
    assert "positive" in result["message"]


async def test_schedule_task_once(mock_db):
    mock_db.fetchval.return_value = 3
    result = await schedule_task(
        user_id="tg:123",
        prompt="Reminder",
        schedule_type="once",
        schedule_value="2099-03-01T15:30:00",
        db=mock_db,
    )
    assert result["status"] == "scheduled"


async def test_schedule_task_invalid_once(mock_db):
    result = await schedule_task(
        user_id="tg:123",
        prompt="Bad",
        schedule_type="once",
        schedule_value="not-a-date",
        db=mock_db,
    )
    assert result["status"] == "error"


async def test_list_tasks_empty(mock_db):
    mock_db.fetch.return_value = []
    result = await list_tasks(user_id="tg:123", db=mock_db)
    assert result == {"tasks": []}


async def test_list_tasks_with_results(mock_db):
    mock_db.fetch.return_value = [
        {"id": 1, "prompt": "Check weather", "schedule_type": "cron",
         "schedule_value": "0 9 * * *", "status": "active",
         "next_run_at": None, "created_at": "2026-02-25T10:00:00"},
    ]
    result = await list_tasks(user_id="tg:123", db=mock_db)
    assert len(result["tasks"]) == 1
    assert result["tasks"][0]["id"] == 1


async def test_pause_task(mock_db):
    mock_db.execute.return_value = "UPDATE 1"
    result = await pause_task(user_id="tg:123", task_id=1, db=mock_db)
    assert result["status"] == "paused"


async def test_pause_task_not_found(mock_db):
    mock_db.execute.return_value = "UPDATE 0"
    result = await pause_task(user_id="tg:123", task_id=999, db=mock_db)
    assert result["status"] == "error"


async def test_resume_task(mock_db):
    mock_db.execute.return_value = "UPDATE 1"
    result = await resume_task(user_id="tg:123", task_id=1, db=mock_db)
    assert result["status"] == "resumed"


async def test_cancel_task(mock_db):
    mock_db.execute.return_value = "DELETE 1"
    result = await cancel_task(user_id="tg:123", task_id=1, db=mock_db)
    assert result["status"] == "cancelled"


async def test_cancel_task_not_found(mock_db):
    mock_db.execute.return_value = "DELETE 0"
    result = await cancel_task(user_id="tg:123", task_id=999, db=mock_db)
    assert result["status"] == "error"


async def test_schedule_task_invalid_interval_string(mock_db):
    result = await schedule_task(
        user_id="tg:123",
        prompt="Bad",
        schedule_type="interval",
        schedule_value="abc",
        db=mock_db,
    )
    assert result["status"] == "error"


async def test_schedule_task_unknown_type(mock_db):
    result = await schedule_task(
        user_id="tg:123",
        prompt="Bad",
        schedule_type="weekly",
        schedule_value="whatever",
        db=mock_db,
    )
    assert result["status"] == "error"


async def test_resume_task_not_found(mock_db):
    mock_db.execute.return_value = "UPDATE 0"
    result = await resume_task(user_id="tg:123", task_id=999, db=mock_db)
    assert result["status"] == "error"


async def test_schedule_task_once_converts_to_utc(mock_db):
    """'once' input in Asia/Ho_Chi_Minh (UTC+7) must be stored as UTC."""
    mock_db.fetchrow.return_value = {
        "id": "tg:123", "username": "testuser", "platform": "telegram",
        "platform_id": "123", "currency": "USD", "timezone": "Asia/Ho_Chi_Minh", "locale": "en",
    }
    mock_db.fetchval.return_value = 99
    result = await schedule_task(
        user_id="tg:123",
        prompt="Reminder",
        schedule_type="once",
        schedule_value="2099-03-01T10:00:00",
        db=mock_db,
    )
    assert result["status"] == "scheduled"
    # Extract next_run passed to DB (5th positional arg of fetchval INSERT call)
    call_args = mock_db.fetchval.call_args
    next_run = call_args.args[5]
    assert next_run.utcoffset() is not None, "next_run must be timezone-aware"
    assert next_run.astimezone(UTC).hour == 3
    assert next_run.astimezone(UTC).minute == 0
    assert next_run.astimezone(UTC).day == 1
    assert next_run.astimezone(UTC).month == 3


async def test_schedule_task_cron_uses_user_tz(mock_db):
    """Cron 'daily 9 AM' for Asia/Ho_Chi_Minh user must yield next_run_at at 2 AM UTC."""
    mock_db.fetchrow.return_value = {
        "id": "tg:123", "username": "testuser", "platform": "telegram",
        "platform_id": "123", "currency": "USD", "timezone": "Asia/Ho_Chi_Minh", "locale": "en",
    }
    mock_db.fetchval.return_value = 88
    result = await schedule_task(
        user_id="tg:123",
        prompt="Daily reminder",
        schedule_type="cron",
        schedule_value="0 9 * * *",
        db=mock_db,
    )
    assert result["status"] == "scheduled"
    call_args = mock_db.fetchval.call_args
    next_run = call_args.args[5]
    assert next_run.utcoffset() is not None, "next_run must be timezone-aware"
    next_run_utc = next_run.astimezone(UTC)
    # 9 AM Ho Chi Minh (UTC+7) = 2 AM UTC
    assert next_run_utc.hour == 2
    assert next_run_utc.minute == 0


async def test_schedule_task_once_rejects_past_time(mock_db):
    """'once' input that resolves to a past UTC time must return an error."""
    mock_db.fetchrow.return_value = _PROFILE_ROW  # timezone = "UTC"
    result = await schedule_task(
        user_id="tg:123",
        prompt="Stale",
        schedule_type="once",
        schedule_value="2000-01-01T00:00:00",   # definitely in the past
        db=mock_db,
    )
    assert result["status"] == "error"
    assert "past" in result["message"].lower()
    mock_db.fetchval.assert_not_called()   # must NOT insert


async def test_schedule_task_once_no_profile_falls_back_to_utc(mock_db):
    """When user profile not found, 'once' input is treated as UTC directly."""
    mock_db.fetchrow.return_value = None
    mock_db.fetchval.return_value = 77
    result = await schedule_task(
        user_id="tg:123",
        prompt="Reminder",
        schedule_type="once",
        schedule_value="2099-03-01T10:00:00",
        db=mock_db,
    )
    assert result["status"] == "scheduled"
    call_args = mock_db.fetchval.call_args
    next_run = call_args.args[5]
    assert next_run.utcoffset() is not None, "next_run must be timezone-aware"
    next_run_utc = next_run.astimezone(UTC)
    assert next_run_utc.hour == 10
    assert next_run_utc.minute == 0
    assert next_run_utc.day == 1


async def test_schedule_task_once_ms_delay(mock_db):
    """'once' with a pure integer value is treated as a ms delay from now."""
    mock_db.fetchval.return_value = 10
    before = datetime.now(UTC)
    result = await schedule_task(
        user_id="tg:123",
        prompt="Report in 2 min",
        schedule_type="once",
        schedule_value="120000",  # 2 minutes in ms
        db=mock_db,
    )
    after = datetime.now(UTC)

    assert result["status"] == "scheduled"
    assert result["task_id"] == 10

    call_args = mock_db.fetchval.call_args
    next_run_at = call_args.args[5]
    assert next_run_at.utcoffset() is not None, "next_run_at must be timezone-aware"
    expected = timedelta(milliseconds=120000)
    assert before + expected <= next_run_at <= after + expected


async def test_schedule_task_once_ms_delay_zero(mock_db):
    """'once' with ms delay of 0 must be rejected."""
    result = await schedule_task(
        user_id="tg:123",
        prompt="Bad",
        schedule_type="once",
        schedule_value="0",
        db=mock_db,
    )
    assert result["status"] == "error"
    assert "positive" in result["message"].lower()


async def test_schedule_task_interval_sets_next_run_at(mock_db):
    """Interval tasks must have next_run_at set to now+interval so the scheduler picks them up."""
    mock_db.fetchval.return_value = 5
    before = datetime.now(UTC)
    result = await schedule_task(
        user_id="tg:123",
        prompt="Poll API",
        schedule_type="interval",
        schedule_value="120000",   # 2 minutes
        db=mock_db,
    )
    after = datetime.now(UTC)

    assert result["status"] == "scheduled"

    # 5th positional arg to fetchval is next_run_at
    call_args = mock_db.fetchval.call_args
    next_run_at = call_args.args[5]  # (query, user_id, prompt, type, value, next_run_at)

    assert next_run_at is not None, "next_run_at must not be NULL for interval tasks"
    assert next_run_at.utcoffset() is not None, "next_run_at must be timezone-aware"
    expected = timedelta(milliseconds=120000)
    assert before + expected <= next_run_at <= after + expected
