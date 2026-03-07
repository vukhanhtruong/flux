"""ListBudgets use case — read-only listing."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.models.budget import BudgetOut
    from flux_core.repositories.budget_repo import BudgetRepository


class ListBudgets:
    """List all budgets for a user (read-only)."""

    def __init__(self, budget_repo: BudgetRepository):
        self._budget_repo = budget_repo

    async def execute(self, user_id: str) -> list[BudgetOut]:
        return self._budget_repo.list_by_user(user_id)
