"""FireScheduledTask use case — insert synthetic message + advance/complete task."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from flux_core.events.events import MessageCreated
from flux_core.sqlite.bot.message_repo import SqliteBotMessageRepository
from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository

if TYPE_CHECKING:
    from flux_core.uow.unit_of_work import UnitOfWork


class FireScheduledTask:
    """Fire a scheduled task: insert a synthetic bot_message and advance or
    complete the task. Emits MessageCreated.
    """

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(
        self,
        task_id: int,
        user_id: str,
        prompt: str,
        schedule_type: str,
        *,
        next_run_at: datetime | None = None,
    ) -> int:
        """Returns the created message ID."""
        async with self._uow:
            msg_repo = SqliteBotMessageRepository(self._uow.conn)
            task_repo = SqliteBotScheduledTaskRepository(self._uow.conn)

            msg_id = msg_repo.insert(
                user_id=user_id,
                channel="scheduler",
                platform_id=f"task:{task_id}",
                text=prompt,
            )

            if schedule_type == "once":
                task_repo.mark_completed(task_id)
            elif next_run_at is not None:
                task_repo.advance_next_run(task_id, next_run_at)

            self._uow.add_event(
                MessageCreated(
                    timestamp=datetime.now(UTC),
                    message_id=msg_id,
                    user_id=user_id,
                )
            )
            await self._uow.commit()

        return msg_id
