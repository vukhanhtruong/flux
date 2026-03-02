"""Integration tests for SavingsSchedulerRepo against a real DB."""
from datetime import datetime, timezone
from uuid import UUID
import pytest

from flux_core.migrations.migrate import migrate as run_core_migrations
from flux_bot.db.migrate import run_migrations as run_bot_migrations
from flux_core.db.connection import Database
from flux_mcp.db.savings_scheduler_repo import SavingsSchedulerRepo


ASSET_UUID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_ID = "tg:999"


@pytest.fixture
async def db(pg_url):
    await run_core_migrations(pg_url)
    await run_bot_migrations(pg_url)
    database = Database(pg_url)
    await database.connect()
    await database.execute(
        "INSERT INTO users (id, display_name, platform) VALUES ($1, $2, $3)"
        " ON CONFLICT DO NOTHING",
        USER_ID, "Test", "tg",
    )
    yield database
    await database.disconnect()


@pytest.fixture
def repo(db):
    return SavingsSchedulerRepo(db)


async def test_create_scheduler(repo, db):
    next_run = datetime(2026, 3, 1, tzinfo=timezone.utc)
    task_id = await repo.create(
        user_id=USER_ID,
        asset_id=str(ASSET_UUID),
        prompt="Process savings interest for Bank Deposit"
        f" (id: {ASSET_UUID})",
        schedule_date="2026-03-01",
        next_run_at=next_run,
    )
    assert task_id is not None

    rows = await db.fetch(
        "SELECT * FROM bot_scheduled_tasks WHERE id = $1", task_id
    )
    assert len(rows) == 1
    row = dict(rows[0])
    assert row["asset_id"] == ASSET_UUID
    assert row["schedule_type"] == "once"
    assert row["schedule_value"] == "2026-03-01"
    assert row["status"] == "active"


async def test_pause_and_resume(repo, db):
    next_run = datetime(2026, 3, 1, tzinfo=timezone.utc)
    await repo.create(USER_ID, str(ASSET_UUID), "prompt", "2026-03-01", next_run)

    await repo.pause(str(ASSET_UUID))
    rows = await db.fetch(
        "SELECT status FROM bot_scheduled_tasks WHERE asset_id = $1", ASSET_UUID
    )
    assert rows[0]["status"] == "paused"

    new_next_run = datetime(2027, 3, 1, tzinfo=timezone.utc)
    await repo.resume(str(ASSET_UUID), new_next_run)
    rows = await db.fetch(
        "SELECT status, next_run_at FROM bot_scheduled_tasks WHERE asset_id = $1",
        ASSET_UUID,
    )
    assert rows[0]["status"] == "active"
    assert rows[0]["next_run_at"].replace(tzinfo=timezone.utc) == new_next_run


async def test_delete(repo, db):
    next_run = datetime(2026, 3, 1, tzinfo=timezone.utc)
    await repo.create(USER_ID, str(ASSET_UUID), "prompt", "2026-03-01", next_run)

    await repo.delete(str(ASSET_UUID))
    rows = await db.fetch(
        "SELECT id FROM bot_scheduled_tasks WHERE asset_id = $1", ASSET_UUID
    )
    assert len(rows) == 0
