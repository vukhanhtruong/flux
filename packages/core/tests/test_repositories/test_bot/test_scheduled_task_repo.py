"""Tests for SqliteBotScheduledTaskRepository."""
from datetime import datetime, timezone

import pytest
from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository


@pytest.fixture
def repo(conn):
    return SqliteBotScheduledTaskRepository(conn)


def _past():
    return datetime(2026, 1, 1, tzinfo=timezone.utc)


def _future():
    return datetime(2027, 1, 1, tzinfo=timezone.utc)


class TestCreate:
    def test_creates_task(self, repo):
        task_id = repo.create(
            user_id="tg:123",
            prompt="Pay rent",
            schedule_type="cron",
            schedule_value="0 0 1 * *",
            next_run_at=_future(),
        )
        assert isinstance(task_id, int)
        assert task_id > 0

    def test_with_subscription_id(self, repo):
        task_id = repo.create(
            user_id="tg:123",
            prompt="Pay Netflix",
            schedule_type="cron",
            schedule_value="0 0 1 * *",
            next_run_at=_future(),
            subscription_id="sub-123",
        )
        assert task_id > 0

    def test_with_asset_id(self, repo):
        task_id = repo.create(
            user_id="tg:123",
            prompt="Deposit savings",
            schedule_type="once",
            schedule_value="2026-06-01",
            next_run_at=_future(),
            asset_id="asset-456",
        )
        assert task_id > 0


class TestFetchDueTasks:
    def test_fetches_due(self, repo, user_id):
        repo.create(
            user_id=user_id,
            prompt="Due task",
            schedule_type="cron",
            schedule_value="0 0 1 * *",
            next_run_at=_past(),
        )
        repo.create(
            user_id=user_id,
            prompt="Future task",
            schedule_type="cron",
            schedule_value="0 0 1 * *",
            next_run_at=_future(),
        )
        results = repo.fetch_due_tasks()
        assert len(results) == 1
        assert results[0]["prompt"] == "Due task"
        assert "user_timezone" in results[0]

    def test_empty(self, repo):
        assert repo.fetch_due_tasks() == []


class TestListByUser:
    def test_lists_active_only(self, repo):
        repo.create(
            user_id="tg:123",
            prompt="Active task",
            schedule_type="cron",
            schedule_value="0 0 1 * *",
            next_run_at=_future(),
        )
        task2 = repo.create(
            user_id="tg:123",
            prompt="Paused task",
            schedule_type="cron",
            schedule_value="0 0 1 * *",
            next_run_at=_future(),
        )
        repo.pause(task2)
        results = repo.list_by_user("tg:123")
        assert len(results) == 1
        assert results[0]["prompt"] == "Active task"


class TestAdvanceNextRun:
    def test_advances(self, repo, conn):
        task_id = repo.create(
            user_id="tg:123",
            prompt="Recurring",
            schedule_type="cron",
            schedule_value="0 0 1 * *",
            next_run_at=_past(),
        )
        new_time = _future()
        repo.advance_next_run(task_id, new_time)
        row = conn.execute(
            "SELECT next_run_at, last_run_at FROM bot_scheduled_tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        assert row["next_run_at"] == new_time.isoformat()
        assert row["last_run_at"] is not None


class TestMarkCompleted:
    def test_marks_completed(self, repo, conn):
        task_id = repo.create(
            user_id="tg:123",
            prompt="One-shot",
            schedule_type="once",
            schedule_value="2026-06-01",
            next_run_at=_past(),
        )
        repo.mark_completed(task_id)
        row = conn.execute(
            "SELECT status FROM bot_scheduled_tasks WHERE id = ?", (task_id,)
        ).fetchone()
        assert row["status"] == "completed"


class TestPause:
    def test_pauses_task(self, repo, conn):
        task_id = repo.create(
            user_id="tg:123",
            prompt="Test",
            schedule_type="cron",
            schedule_value="0 0 1 * *",
            next_run_at=_future(),
        )
        repo.pause(task_id)
        row = conn.execute(
            "SELECT status FROM bot_scheduled_tasks WHERE id = ?", (task_id,)
        ).fetchone()
        assert row["status"] == "paused"


class TestPauseByAsset:
    def test_pauses_by_asset(self, repo, conn):
        repo.create(
            user_id="tg:123",
            prompt="Savings",
            schedule_type="once",
            schedule_value="2026-06-01",
            next_run_at=_future(),
            asset_id="asset-1",
        )
        repo.pause_by_asset("asset-1")
        row = conn.execute(
            "SELECT status FROM bot_scheduled_tasks WHERE asset_id = ?", ("asset-1",)
        ).fetchone()
        assert row["status"] == "paused"


class TestResumeByAsset:
    def test_resumes_by_asset(self, repo, conn):
        repo.create(
            user_id="tg:123",
            prompt="Savings",
            schedule_type="once",
            schedule_value="2026-06-01",
            next_run_at=_past(),
            asset_id="asset-1",
        )
        repo.pause_by_asset("asset-1")
        new_time = _future()
        repo.resume_by_asset("asset-1", new_time)
        row = conn.execute(
            "SELECT status, next_run_at FROM bot_scheduled_tasks WHERE asset_id = ?",
            ("asset-1",),
        ).fetchone()
        assert row["status"] == "active"
        assert row["next_run_at"] == new_time.isoformat()


class TestDelete:
    def test_deletes_task(self, repo, conn):
        task_id = repo.create(
            user_id="tg:123",
            prompt="Test",
            schedule_type="cron",
            schedule_value="0 0 1 * *",
            next_run_at=_future(),
        )
        repo.delete(task_id)
        row = conn.execute(
            "SELECT id FROM bot_scheduled_tasks WHERE id = ?", (task_id,)
        ).fetchone()
        assert row is None


class TestDeleteByAsset:
    def test_deletes_by_asset(self, repo, conn):
        repo.create(
            user_id="tg:123",
            prompt="Savings",
            schedule_type="once",
            schedule_value="2026-06-01",
            next_run_at=_future(),
            asset_id="asset-1",
        )
        repo.delete_by_asset("asset-1")
        row = conn.execute(
            "SELECT id FROM bot_scheduled_tasks WHERE asset_id = ?", ("asset-1",)
        ).fetchone()
        assert row is None


class TestDeleteBySubscription:
    def test_deletes_by_subscription(self, repo, conn):
        repo.create(
            user_id="tg:123",
            prompt="Pay sub",
            schedule_type="cron",
            schedule_value="0 0 1 * *",
            next_run_at=_future(),
            subscription_id="sub-1",
        )
        repo.delete_by_subscription("sub-1")
        row = conn.execute(
            "SELECT id FROM bot_scheduled_tasks WHERE subscription_id = ?", ("sub-1",)
        ).fetchone()
        assert row is None
