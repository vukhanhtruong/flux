from datetime import UTC, datetime, timedelta
import asyncpg
import pytest

from flux_bot.db.scheduled_tasks import ScheduledTaskRepository
from flux_bot.db.migrate import run_migrations
from flux_core.migrations.migrate import migrate as run_core_migrations


async def _setup(pg_url: str) -> tuple[asyncpg.Pool, ScheduledTaskRepository]:
    await run_core_migrations(pg_url)
    await run_migrations(pg_url)
    pool = await asyncpg.create_pool(pg_url, min_size=1, max_size=3)
    return pool, ScheduledTaskRepository(pool)


async def _insert_task(pool, *, next_run_at, status="active"):
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO bot_scheduled_tasks
                (user_id, prompt, schedule_type, schedule_value, status, next_run_at)
            VALUES ('tg:99', 'test prompt', 'once', '2000-01-01T00:00:00', $1, $2)
            RETURNING id
            """,
            status, next_run_at,
        )


async def test_fetch_due_returns_past_active_tasks(pg_url):
    pool, repo = await _setup(pg_url)
    try:
        past = datetime.now(UTC) - timedelta(minutes=5)
        task_id = await _insert_task(pool, next_run_at=past)
        due = await repo.fetch_due_tasks()
        ids = [t["id"] for t in due]
        assert task_id in ids
        task = next(t for t in due if t["id"] == task_id)
        assert "user_timezone" in task, "fetch_due_tasks must include user_timezone"
        assert task["user_timezone"] == "UTC", "default user_timezone must be UTC"
    finally:
        await pool.close()


async def test_fetch_due_ignores_future_tasks(pg_url):
    pool, repo = await _setup(pg_url)
    try:
        future = datetime.now(UTC) + timedelta(hours=1)
        task_id = await _insert_task(pool, next_run_at=future)
        due = await repo.fetch_due_tasks()
        ids = [t["id"] for t in due]
        assert task_id not in ids
    finally:
        await pool.close()


async def test_fetch_due_ignores_non_active(pg_url):
    pool, repo = await _setup(pg_url)
    try:
        past = datetime.now(UTC) - timedelta(minutes=1)
        task_id = await _insert_task(pool, next_run_at=past, status="paused")
        due = await repo.fetch_due_tasks()
        ids = [t["id"] for t in due]
        assert task_id not in ids
    finally:
        await pool.close()


async def test_mark_completed(pg_url):
    pool, repo = await _setup(pg_url)
    try:
        past = datetime.now(UTC) - timedelta(minutes=1)
        task_id = await _insert_task(pool, next_run_at=past)
        await repo.mark_completed(task_id)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status, last_run_at FROM bot_scheduled_tasks WHERE id=$1", task_id
            )
        assert row["status"] == "completed"
        assert row["last_run_at"] is not None
    finally:
        await pool.close()


async def test_advance_next_run(pg_url):
    pool, repo = await _setup(pg_url)
    try:
        past = datetime.now(UTC) - timedelta(minutes=1)
        task_id = await _insert_task(pool, next_run_at=past)
        new_next = datetime.now(UTC) + timedelta(hours=1)
        await repo.advance_next_run(task_id, new_next)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT next_run_at, last_run_at FROM bot_scheduled_tasks WHERE id=$1", task_id
            )
        assert row["next_run_at"].replace(tzinfo=UTC) > datetime.now(UTC)
        assert row["last_run_at"] is not None
    finally:
        await pool.close()


async def test_list_by_user_returns_active_tasks(pg_url):
    pool, repo = await _setup(pg_url)
    try:
        future = datetime.now(UTC) + timedelta(hours=1)
        task_id = await _insert_task(pool, next_run_at=future)
        tasks = await repo.list_by_user("tg:99")
        ids = [t["id"] for t in tasks]
        assert task_id in ids
    finally:
        await pool.close()


async def test_list_by_user_excludes_other_users(pg_url):
    pool, repo = await _setup(pg_url)
    try:
        future = datetime.now(UTC) + timedelta(hours=1)
        async with pool.acquire() as conn:
            task_id = await conn.fetchval(
                """
                INSERT INTO bot_scheduled_tasks
                    (user_id, prompt, schedule_type, schedule_value, status, next_run_at)
                VALUES ('tg:other', 'other prompt', 'once', '2000-01-01T00:00:00', 'active', $1)
                RETURNING id
                """,
                future,
            )
        tasks = await repo.list_by_user("tg:99")
        ids = [t["id"] for t in tasks]
        assert task_id not in ids
    finally:
        await pool.close()


async def test_list_by_user_excludes_completed(pg_url):
    pool, repo = await _setup(pg_url)
    try:
        future = datetime.now(UTC) + timedelta(hours=1)
        task_id = await _insert_task(pool, next_run_at=future, status="completed")
        tasks = await repo.list_by_user("tg:99")
        ids = [t["id"] for t in tasks]
        assert task_id not in ids
    finally:
        await pool.close()
