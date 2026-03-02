"""Manages bot_scheduled_tasks rows that are paired to savings deposits."""
from datetime import date, datetime, timezone
from uuid import UUID

from flux_core.db.connection import Database


def _to_utc_midnight(d: date) -> datetime:
    """Convert a date to UTC midnight datetime for next_run_at."""
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)


class SavingsSchedulerRepo:
    def __init__(self, db: Database):
        self._db = db

    async def create(
        self,
        user_id: str,
        asset_id: str,
        prompt: str,
        schedule_date: str,
        next_run_at: datetime,
    ) -> int:
        """Insert a one-shot scheduler row paired to a savings deposit. Returns task id."""
        row = await self._db.fetchrow(
            """
            INSERT INTO bot_scheduled_tasks
                (user_id, prompt, schedule_type, schedule_value, status, next_run_at, asset_id)
            VALUES ($1, $2, 'once', $3, 'active', $4, $5)
            RETURNING id
            """,
            user_id, prompt, schedule_date, next_run_at, UUID(asset_id),
        )
        return row["id"]

    async def pause(self, asset_id: str) -> None:
        """Pause the scheduler for a savings deposit."""
        await self._db.execute(
            "UPDATE bot_scheduled_tasks SET status = 'paused' WHERE asset_id = $1",
            UUID(asset_id),
        )

    async def resume(self, asset_id: str, next_run_at: datetime) -> None:
        """Re-activate the scheduler for a savings deposit."""
        await self._db.execute(
            """
            UPDATE bot_scheduled_tasks
            SET status = 'active', next_run_at = $2
            WHERE asset_id = $1
            """,
            UUID(asset_id), next_run_at,
        )

    async def delete(self, asset_id: str) -> None:
        """Remove the scheduler row when a savings deposit is deleted/closed."""
        await self._db.execute(
            "DELETE FROM bot_scheduled_tasks WHERE asset_id = $1",
            UUID(asset_id),
        )
