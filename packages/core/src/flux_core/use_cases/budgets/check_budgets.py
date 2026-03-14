"""CheckBudgets use case — budget limits with current-month spending."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.repositories.budget_repo import BudgetRepository
    from flux_core.repositories.transaction_repo import TransactionRepository


class CheckBudgets:
    """Return all budgets with current-month spending, percentage, and over-budget status."""

    def __init__(
        self, budget_repo: BudgetRepository, txn_repo: TransactionRepository
    ):
        self._budget_repo = budget_repo
        self._txn_repo = txn_repo

    async def execute(self, user_id: str) -> list[dict]:
        budgets = self._budget_repo.list_by_user(user_id)
        if not budgets:
            return []

        today = datetime.now(timezone.utc).date()
        start_of_month = today.replace(day=1)

        breakdown = self._txn_repo.get_category_breakdown(
            user_id, start_of_month, today
        )
        spending_by_cat = {
            row["category"].lower(): Decimal(str(row["total"])) for row in breakdown
        }

        results = []
        for b in budgets:
            spent = spending_by_cat.get(b.category.lower(), Decimal("0"))
            limit = b.monthly_limit
            percent = float((spent / limit) * 100) if limit > 0 else 0.0
            remaining = limit - spent

            results.append({
                "category": b.category,
                "monthly_limit": str(limit),
                "spent_this_month": f"{spent:.2f}",
                "percent_used": round(percent, 1),
                "remaining": f"{remaining:.2f}",
                "is_over_budget": spent > limit,
            })

        return results
