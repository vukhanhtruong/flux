"""Manages bot_scheduled_tasks rows that are paired to savings deposits."""
from datetime import date, datetime, timezone
from uuid import UUID

from flux_core.db.connection import Database


def _derive_savings_cron(compound_frequency: str, next_date: date) -> str:
    """Derive a cron expression from a savings deposit's compound frequency and next_date."""
    day = next_date.day
    if compound_frequency == "monthly":
        return f"0 0 {day} * *"
    if compound_frequency == "quarterly":
        start_month = next_date.month
        months = ",".join(
            str((start_month - 1 + i * 3) % 12 + 1) for i in range(4)
        )
        return f"0 0 {day} {months} *"
    # yearly
    return f"0 0 {day} {next_date.month} *"


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
        cron: str,
        next_run_at: datetime,
    ) -> int:
        """Insert a cron scheduler row paired to a savings deposit. Returns task id."""
        row = await self._db.fetchrow(
            """
            INSERT INTO bot_scheduled_tasks
                (user_id, prompt, schedule_type, schedule_value, status, next_run_at, asset_id)
            VALUES ($1, $2, 'cron', $3, 'active', $4, $5)
            RETURNING id
            """,
            user_id, prompt, cron, next_run_at, UUID(asset_id),
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
