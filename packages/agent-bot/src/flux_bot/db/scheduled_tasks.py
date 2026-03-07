"""Async wrapper for bot_scheduled_tasks — delegates to core SQLite repo."""

from datetime import UTC, date, datetime

from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository
from flux_core.sqlite.database import Database


class ScheduledTaskRepository:
    def __init__(self, db: Database):
        self._db = db

    def _repo(self) -> SqliteBotScheduledTaskRepository:
        return SqliteBotScheduledTaskRepository(self._db.connection())

    async def fetch_due_tasks(self) -> list[dict]:
        """Fetch active tasks whose next_run_at is now or in the past."""
        return self._repo().fetch_due_tasks()

    async def get_subscription_next_run(self, task_id: int) -> datetime | None:
        """Return UTC midnight derived from the paired subscription.next_date."""
        conn = self._db.connection()
        row = conn.execute(
            """
            SELECT s.next_date
            FROM bot_scheduled_tasks t
            JOIN subscriptions s
              ON s.id = t.subscription_id
              AND s.user_id = t.user_id
            WHERE t.id = ?
            """,
            (task_id,),
        ).fetchone()
        if row is None:
            return None
        next_date: date = date.fromisoformat(row["next_date"])
        return datetime(next_date.year, next_date.month, next_date.day, tzinfo=UTC)

    async def mark_completed(self, task_id: int) -> None:
        """Mark a once task as completed after firing."""
        self._repo().mark_completed(task_id)
        self._db.connection().commit()

    async def advance_next_run(self, task_id: int, next_run_at: datetime) -> None:
        """Advance next_run_at for recurring tasks after firing."""
        self._repo().advance_next_run(task_id, next_run_at)
        self._db.connection().commit()

    async def list_by_user(self, user_id: str) -> list[dict]:
        """Return active scheduled tasks for a user, ordered by next_run_at."""
        return self._repo().list_by_user(user_id)
