"""WithdrawFromGoal use case."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from flux_core.sqlite.goal_repo import SqliteGoalRepository

if TYPE_CHECKING:
    from uuid import UUID

    from flux_core.models.goal import GoalOut
    from flux_core.uow.unit_of_work import UnitOfWork


class WithdrawFromGoal:
    """Withdraw money from a savings goal (write via UoW)."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(
        self, goal_id: UUID, user_id: str, amount: Decimal
    ) -> GoalOut:
        async with self._uow:
            repo = SqliteGoalRepository(self._uow.conn)
            result = repo.withdraw(goal_id, user_id, amount)
            if result is None:
                raise ValueError(f"Goal {goal_id} not found")
            await self._uow.commit()
        return result
