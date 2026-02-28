"""Manages bot_scheduled_tasks rows that are paired to subscriptions."""
from datetime import date, datetime, timezone
from uuid import UUID

from flux_core.db.connection import Database
from flux_core.models.subscription import BillingCycle


def _derive_cron(billing_cycle: BillingCycle, next_date: date) -> str:
    """Derive a cron expression from a subscription's billing cycle and next_date day."""
    if billing_cycle == BillingCycle.monthly:
        return f"0 0 {next_date.day} * *"
    # yearly
    return f"0 0 {next_date.day} {next_date.month} *"


def _to_utc_midnight(d: date) -> datetime:
    """Convert a date to UTC midnight datetime for next_run_at."""
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)


class SubscriptionSchedulerRepo:
    def __init__(self, db: Database):
        self._db = db

    async def create(
        self,
        user_id: str,
        subscription_id: str,
        prompt: str,
        cron: str,
        next_run_at: datetime,
    ) -> int:
        """Insert a cron scheduler row paired to a subscription. Returns task id."""
        row = await self._db.fetchrow(
            """
            INSERT INTO bot_scheduled_tasks
                (user_id, prompt, schedule_type, schedule_value, status, next_run_at, subscription_id)
            VALUES ($1, $2, 'cron', $3, 'active', $4, $5)
            RETURNING id
            """,
            user_id, prompt, cron, next_run_at, UUID(subscription_id),
        )
        return row["id"]

    async def pause(self, subscription_id: str) -> None:
        """Pause the scheduler for an archived subscription."""
        await self._db.execute(
            "UPDATE bot_scheduled_tasks SET status = 'paused' WHERE subscription_id = $1",
            UUID(subscription_id),
        )

    async def resume(self, subscription_id: str, next_run_at: datetime) -> None:
        """Re-activate the scheduler when a subscription is re-enabled."""
        await self._db.execute(
            """
            UPDATE bot_scheduled_tasks
            SET status = 'active', next_run_at = $2
            WHERE subscription_id = $1
            """,
            UUID(subscription_id), next_run_at,
        )

    async def delete(self, subscription_id: str) -> None:
        """Remove the scheduler row when a subscription is deleted."""
        await self._db.execute(
            "DELETE FROM bot_scheduled_tasks WHERE subscription_id = $1",
            UUID(subscription_id),
        )
