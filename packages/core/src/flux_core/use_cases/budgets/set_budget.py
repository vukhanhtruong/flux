"""SetBudget use case — upsert a budget for a category."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from flux_core.models.budget import BudgetSet
from flux_core.sqlite.budget_repo import SqliteBudgetRepository

if TYPE_CHECKING:
    from flux_core.models.budget import BudgetOut
    from flux_core.uow.unit_of_work import UnitOfWork


class SetBudget:
    """Set or update a budget for a category (write via UoW)."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(
        self, user_id: str, category: str, monthly_limit: Decimal
    ) -> BudgetOut:
        budget = BudgetSet(
            user_id=user_id,
            category=category,
            monthly_limit=monthly_limit,
        )
        async with self._uow:
            repo = SqliteBudgetRepository(self._uow.conn)
            result = repo.set(budget)
            await self._uow.commit()
        return result
