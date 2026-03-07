"""DeleteSubscription use case — delete subscription + scheduled task."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository
from flux_core.sqlite.subscription_repo import SqliteSubscriptionRepository

if TYPE_CHECKING:
    from uuid import UUID

    from flux_core.uow.unit_of_work import UnitOfWork


class DeleteSubscription:
    """Delete a subscription and its associated scheduled task (write via UoW)."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(self, sub_id: UUID, user_id: str) -> bool:
        async with self._uow:
            task_repo = SqliteBotScheduledTaskRepository(self._uow.conn)
            sub_repo = SqliteSubscriptionRepository(self._uow.conn)

            task_repo.delete_by_subscription(str(sub_id))
            success = sub_repo.delete(sub_id, user_id)

            await self._uow.commit()

        return success
