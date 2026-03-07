"""CancelTask use case — cancel and delete a scheduled task."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.uow.unit_of_work import UnitOfWork


class CancelTask:
    """Cancel and delete a scheduled task (write via UoW)."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(self, user_id: str, task_id: int) -> dict:
        async with self._uow:
            cursor = self._uow.conn.execute(
                "DELETE FROM bot_scheduled_tasks WHERE id = ? AND user_id = ?",
                (task_id, user_id),
            )
            if cursor.rowcount == 0:
                await self._uow.commit()
                return {
                    "status": "error",
                    "message": f"Task {task_id} not found.",
                }
            await self._uow.commit()

        return {"status": "cancelled", "task_id": task_id}
