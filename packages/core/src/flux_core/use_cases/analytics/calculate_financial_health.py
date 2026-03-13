"""CalculateFinancialHealth — compute financial health score from summary."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.repositories.transaction_repo import TransactionRepository


class CalculateFinancialHealth:
    """Calculate a financial health score based on income vs expenses."""

    def __init__(self, repo: TransactionRepository):
        self._repo = repo

    async def execute(self, user_id: str, start_date: date, end_date: date) -> dict:
        summary = self._repo.get_summary(user_id, start_date, end_date)
        total_income = Decimal(summary.get("total_income", "0"))
        total_expenses = Decimal(summary.get("total_expenses", "0"))
        savings_rate = (
            float((total_income - total_expenses) / total_income)
            if total_income > 0
            else 0.0
        )
        score = max(0, min(100, round(savings_rate * 100)))
        return {
            "score": score,
            "savings_rate": savings_rate,
            "budget_adherence": 0.0,
            "goal_progress": 0.0,
        }
