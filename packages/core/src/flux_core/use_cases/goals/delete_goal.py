"""DeleteGoal use case."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flux_core.sqlite.goal_repo import SqliteGoalRepository

if TYPE_CHECKING:
    from uuid import UUID

    from flux_core.uow.unit_of_work import UnitOfWork


class DeleteGoal:
    """Delete a savings goal (write via UoW)."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(self, goal_id: UUID, user_id: str) -> bool:
        async with self._uow:
            repo = SqliteGoalRepository(self._uow.conn)
            success = repo.delete(goal_id, user_id)
            await self._uow.commit()
        return success
