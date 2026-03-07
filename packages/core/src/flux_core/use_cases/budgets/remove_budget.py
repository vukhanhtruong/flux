"""RemoveBudget use case — delete a budget for a category."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flux_core.sqlite.budget_repo import SqliteBudgetRepository

if TYPE_CHECKING:
    from flux_core.uow.unit_of_work import UnitOfWork


class RemoveBudget:
    """Remove a budget for a category (write via UoW)."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(self, user_id: str, category: str) -> bool:
        async with self._uow:
            repo = SqliteBudgetRepository(self._uow.conn)
            success = repo.remove(user_id, category)
            await self._uow.commit()
        return success
