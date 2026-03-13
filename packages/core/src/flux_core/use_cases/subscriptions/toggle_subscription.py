"""ToggleSubscription use case — toggle active + pause/resume scheduler."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository
from flux_core.sqlite.subscription_repo import SqliteSubscriptionRepository
from flux_core.utils import to_utc_midnight

if TYPE_CHECKING:
    from uuid import UUID

    from flux_core.models.subscription import SubscriptionOut
    from flux_core.uow.unit_of_work import UnitOfWork


class ToggleSubscription:
    """Toggle subscription active/inactive and pause/resume scheduler task."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(self, sub_id: UUID, user_id: str) -> SubscriptionOut:
        async with self._uow:
            sub_repo = SqliteSubscriptionRepository(self._uow.conn)
            result = sub_repo.toggle_active(sub_id, user_id)
            if result is None:
                raise ValueError(f"Subscription {sub_id} not found")

            task_repo = SqliteBotScheduledTaskRepository(self._uow.conn)
            if result.active:
                task_repo.resume_by_subscription(
                    str(sub_id), to_utc_midnight(result.next_date)
                )
            else:
                task_repo.pause_by_subscription(str(sub_id))

            await self._uow.commit()

        return result
