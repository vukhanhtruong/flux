"""Repository for bot_scheduled_tasks table."""

from datetime import UTC, date, datetime
import asyncpg


class ScheduledTaskRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def fetch_due_tasks(self) -> list[dict]:
        """Fetch active tasks whose next_run_at is now or in the past."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.id, t.user_id, t.prompt, t.schedule_type, t.schedule_value,
                       t.subscription_id,
                       COALESCE(u.timezone, 'UTC') AS user_timezone
                FROM bot_scheduled_tasks t
                LEFT JOIN users u ON u.id = t.user_id
                WHERE t.status = 'active' AND t.next_run_at <= NOW()
                ORDER BY t.next_run_at
                """
            )
            return [dict(r) for r in rows]

    async def get_subscription_next_run(self, task_id: int) -> datetime | None:
        """Return UTC midnight derived from the paired subscription.next_date."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT s.next_date
                FROM bot_scheduled_tasks t
                JOIN subscriptions s
                  ON s.id = t.subscription_id
                 AND s.user_id = t.user_id
                WHERE t.id = $1
                """,
                task_id,
            )
            if row is None:
                return None
            next_date: date = row["next_date"]
            return datetime(next_date.year, next_date.month, next_date.day, tzinfo=UTC)

    async def mark_completed(self, task_id: int) -> None:
        """Mark a once task as completed after firing."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE bot_scheduled_tasks
                SET status = 'completed', last_run_at = NOW()
                WHERE id = $1
                """,
                task_id,
            )

    async def advance_next_run(self, task_id: int, next_run_at: datetime) -> None:
        """Advance next_run_at for recurring tasks after firing."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE bot_scheduled_tasks
                SET last_run_at = NOW(), next_run_at = $2
                WHERE id = $1
                """,
                task_id, next_run_at,
            )

    async def list_by_user(self, user_id: str) -> list[dict]:
        """Return active scheduled tasks for a user, ordered by next_run_at."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, prompt, schedule_type, schedule_value, next_run_at, created_at
                FROM bot_scheduled_tasks
                WHERE user_id = $1 AND status = 'active'
                ORDER BY next_run_at ASC NULLS LAST
                """,
                user_id,
            )
            return [dict(r) for r in rows]
