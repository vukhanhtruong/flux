"""CreateGoal use case."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from flux_core.models.goal import GoalCreate
from flux_core.sqlite.goal_repo import SqliteGoalRepository

if TYPE_CHECKING:
    from flux_core.models.goal import GoalOut
    from flux_core.uow.unit_of_work import UnitOfWork


class CreateGoal:
    """Create a new savings goal (write via UoW)."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(
        self,
        user_id: str,
        name: str,
        target_amount: Decimal,
        *,
        deadline: date | None = None,
        color: str = "#3B82F6",
    ) -> GoalOut:
        goal = GoalCreate(
            user_id=user_id,
            name=name,
            target_amount=target_amount,
            deadline=deadline,
            color=color,
        )
        async with self._uow:
            repo = SqliteGoalRepository(self._uow.conn)
            result = repo.create(goal)
            await self._uow.commit()
        return result
