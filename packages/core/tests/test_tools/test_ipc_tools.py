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


@pytest.fixture
def mock_db():
    return AsyncMock()


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


async def test_schedule_task_once(mock_db):
    mock_db.fetchval.return_value = 3
    result = await schedule_task(
        user_id="tg:123",
        prompt="Reminder",
        schedule_type="once",
        schedule_value="2026-03-01T15:30:00",
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
