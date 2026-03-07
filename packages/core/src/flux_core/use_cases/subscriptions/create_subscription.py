"""CreateSubscription use case — create subscription + scheduled task."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from flux_core.events.events import SubscriptionCreated
from flux_core.models.subscription import BillingCycle, SubscriptionCreate
from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository
from flux_core.sqlite.subscription_repo import SqliteSubscriptionRepository

if TYPE_CHECKING:
    from datetime import date

    from flux_core.models.subscription import SubscriptionOut
    from flux_core.uow.unit_of_work import UnitOfWork


def _derive_cron(cycle: BillingCycle, next_date: date) -> str:
    """Derive a cron expression from billing cycle and next date."""
    if cycle == BillingCycle.monthly:
        return f"0 0 {next_date.day} * *"
    # yearly
    return f"0 0 {next_date.day} {next_date.month} *"


def _to_utc_midnight(d: date) -> datetime:
    """Convert a date to UTC midnight datetime."""
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


class CreateSubscription:
    """Create a subscription and its associated scheduled task (write via UoW)."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(
        self,
        user_id: str,
        name: str,
        amount: Decimal,
        billing_cycle: BillingCycle,
        next_date: date,
        category: str,
    ) -> SubscriptionOut:
        sub = SubscriptionCreate(
            user_id=user_id,
            name=name,
            amount=amount,
            billing_cycle=billing_cycle,
            next_date=next_date,
            category=category,
        )

        async with self._uow:
            sub_repo = SqliteSubscriptionRepository(self._uow.conn)
            task_repo = SqliteBotScheduledTaskRepository(self._uow.conn)

            result = sub_repo.create(sub)

            prompt = (
                f"Process subscription billing for {result.name} (id: {result.id})"
            )
            cron = _derive_cron(result.billing_cycle, result.next_date)
            task_repo.create(
                user_id=user_id,
                prompt=prompt,
                schedule_type="cron",
                schedule_value=cron,
                next_run_at=_to_utc_midnight(result.next_date),
                subscription_id=str(result.id),
            )

            self._uow.add_event(
                SubscriptionCreated(
                    timestamp=datetime.now(UTC),
                    subscription_id=str(result.id),
                    user_id=user_id,
                )
            )
            await self._uow.commit()

        return result
