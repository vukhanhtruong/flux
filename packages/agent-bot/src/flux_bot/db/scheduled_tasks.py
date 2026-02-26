"""Repository for bot_scheduled_tasks table."""

from datetime import datetime
import asyncpg


class ScheduledTaskRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def fetch_due_tasks(self) -> list[dict]:
        """Fetch active tasks whose next_run_at is now or in the past."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, prompt, schedule_type, schedule_value
                FROM bot_scheduled_tasks
                WHERE status = 'active' AND next_run_at <= NOW()
                ORDER BY next_run_at
                """
            )
            return [dict(r) for r in rows]

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
