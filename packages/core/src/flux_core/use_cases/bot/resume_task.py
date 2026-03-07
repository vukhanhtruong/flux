"""ResumeTask use case — resume a paused scheduled task."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.uow.unit_of_work import UnitOfWork


class ResumeTask:
    """Resume a paused scheduled task (write via UoW)."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(self, user_id: str, task_id: int) -> dict:
        async with self._uow:
            cursor = self._uow.conn.execute(
                "UPDATE bot_scheduled_tasks SET status = 'active'"
                " WHERE id = ? AND user_id = ? AND status = 'paused'",
                (task_id, user_id),
            )
            if cursor.rowcount == 0:
                await self._uow.commit()
                return {
                    "status": "error",
                    "message": f"Task {task_id} not found or not paused.",
                }
            await self._uow.commit()

        return {"status": "resumed", "task_id": task_id}
