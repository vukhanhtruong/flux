"""Test ScheduledTaskRepository — async wrapper around SQLite bot scheduled task repo."""
from datetime import UTC, datetime, timedelta

from flux_bot.db.scheduled_tasks import ScheduledTaskRepository


def _insert_task(sqlite_db, *, next_run_at, status="active"):
    """Insert a task directly via SQL and return its ID.

    Stores next_run_at in SQLite-compatible format (YYYY-MM-DD HH:MM:SS UTC).
    """
    conn = sqlite_db.connection()
    # Convert to UTC and format without timezone for SQLite datetime() compatibility
    utc_str = next_run_at.strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute(
        """
        INSERT INTO bot_scheduled_tasks
            (user_id, prompt, schedule_type, schedule_value, status, next_run_at)
        VALUES ('tg:99', 'test prompt', 'once', '2000-01-01T00:00:00', ?, ?)
        """,
        (status, utc_str),
    )
    conn.commit()
    return cursor.lastrowid


async def test_fetch_due_returns_past_active_tasks(sqlite_db):
    repo = ScheduledTaskRepository(sqlite_db)
    past = datetime.now(UTC) - timedelta(minutes=5)
    task_id = _insert_task(sqlite_db, next_run_at=past)
    due = await repo.fetch_due_tasks()
    ids = [t["id"] for t in due]
    assert task_id in ids


async def test_fetch_due_ignores_future_tasks(sqlite_db):
    repo = ScheduledTaskRepository(sqlite_db)
    future = datetime.now(UTC) + timedelta(hours=1)
    task_id = _insert_task(sqlite_db, next_run_at=future)
    due = await repo.fetch_due_tasks()
    ids = [t["id"] for t in due]
    assert task_id not in ids


async def test_fetch_due_ignores_non_active(sqlite_db):
    repo = ScheduledTaskRepository(sqlite_db)
    past = datetime.now(UTC) - timedelta(minutes=1)
    task_id = _insert_task(sqlite_db, next_run_at=past, status="paused")
    due = await repo.fetch_due_tasks()
    ids = [t["id"] for t in due]
    assert task_id not in ids


async def test_mark_completed(sqlite_db):
    repo = ScheduledTaskRepository(sqlite_db)
    past = datetime.now(UTC) - timedelta(minutes=1)
    task_id = _insert_task(sqlite_db, next_run_at=past)
    await repo.mark_completed(task_id)
    conn = sqlite_db.connection()
    row = conn.execute(
        "SELECT status, last_run_at FROM bot_scheduled_tasks WHERE id = ?", (task_id,)
    ).fetchone()
    assert row["status"] == "completed"
    assert row["last_run_at"] is not None


async def test_advance_next_run(sqlite_db):
    repo = ScheduledTaskRepository(sqlite_db)
    past = datetime.now(UTC) - timedelta(minutes=1)
    task_id = _insert_task(sqlite_db, next_run_at=past)
    new_next = datetime.now(UTC) + timedelta(hours=1)
    await repo.advance_next_run(task_id, new_next)
    conn = sqlite_db.connection()
    row = conn.execute(
        "SELECT next_run_at, last_run_at FROM bot_scheduled_tasks WHERE id = ?", (task_id,)
    ).fetchone()
    assert row["last_run_at"] is not None


async def test_list_by_user_returns_active_tasks(sqlite_db):
    repo = ScheduledTaskRepository(sqlite_db)
    future = datetime.now(UTC) + timedelta(hours=1)
    task_id = _insert_task(sqlite_db, next_run_at=future)
    tasks = await repo.list_by_user("tg:99")
    ids = [t["id"] for t in tasks]
    assert task_id in ids


async def test_list_by_user_excludes_completed(sqlite_db):
    repo = ScheduledTaskRepository(sqlite_db)
    future = datetime.now(UTC) + timedelta(hours=1)
    task_id = _insert_task(sqlite_db, next_run_at=future, status="completed")
    tasks = await repo.list_by_user("tg:99")
    ids = [t["id"] for t in tasks]
    assert task_id not in ids
