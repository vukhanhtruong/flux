"""CreateScheduledTask use case — create a scheduled task."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from flux_core.events.events import ScheduledTaskCreated
from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository

if TYPE_CHECKING:
    from flux_core.uow.unit_of_work import UnitOfWork


class CreateScheduledTask:
    """Create a new scheduled task (write via UoW). Emits ScheduledTaskCreated."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(
        self,
        user_id: str,
        prompt: str,
        schedule_type: str,
        schedule_value: str,
        next_run_at: datetime,
        *,
        subscription_id: str | None = None,
        asset_id: str | None = None,
    ) -> int:
        async with self._uow:
            repo = SqliteBotScheduledTaskRepository(self._uow.conn)
            task_id = repo.create(
                user_id=user_id,
                prompt=prompt,
                schedule_type=schedule_type,
                schedule_value=schedule_value,
                next_run_at=next_run_at,
                subscription_id=subscription_id,
                asset_id=asset_id,
            )
            self._uow.add_event(
                ScheduledTaskCreated(
                    timestamp=datetime.now(UTC),
                    task_id=task_id,
                    user_id=user_id,
                )
            )
            await self._uow.commit()

        return task_id
