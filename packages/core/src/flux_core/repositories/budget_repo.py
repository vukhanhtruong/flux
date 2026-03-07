"""BudgetRepository Protocol — interface for budget data access."""

from __future__ import annotations

from typing import Protocol

from flux_core.models.budget import BudgetOut, BudgetSet


class BudgetRepository(Protocol):
    """Repository interface for budgets."""

    def set(self, budget: BudgetSet) -> BudgetOut: ...

    def list_by_user(self, user_id: str) -> list[BudgetOut]: ...

    def get_by_category(self, user_id: str, category: str) -> BudgetOut | None: ...

    def remove(self, user_id: str, category: str) -> bool: ...
