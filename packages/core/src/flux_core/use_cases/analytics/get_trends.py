"""GetTrends use case — month-over-month spending trends."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

    from flux_core.repositories.transaction_repo import TransactionRepository


class GetTrends:
    """Calculate month-over-month spending trends (read-only).

    Compares two consecutive periods: the current period (start_date to end_date)
    and the prior period of the same length.
    """

    def __init__(self, txn_repo: TransactionRepository):
        self._txn_repo = txn_repo

    async def execute(
        self,
        user_id: str,
        current_start: date,
        current_end: date,
        previous_start: date,
        previous_end: date,
    ) -> dict:
        current = self._txn_repo.get_summary(user_id, current_start, current_end)
        previous = self._txn_repo.get_summary(user_id, previous_start, previous_end)

        curr_expenses = current.get("total_expenses") or Decimal("0")
        prev_expenses = previous.get("total_expenses") or Decimal("0")
        curr_income = current.get("total_income") or Decimal("0")
        prev_income = previous.get("total_income") or Decimal("0")

        expense_change = curr_expenses - prev_expenses
        income_change = curr_income - prev_income

        if prev_expenses > 0:
            expense_pct = (expense_change / prev_expenses * 100).quantize(
                Decimal("0.01")
            )
        else:
            expense_pct = Decimal("0")

        if prev_income > 0:
            income_pct = (income_change / prev_income * 100).quantize(Decimal("0.01"))
        else:
            income_pct = Decimal("0")

        return {
            "current_expenses": str(curr_expenses),
            "previous_expenses": str(prev_expenses),
            "expense_change": str(expense_change),
            "expense_change_pct": str(expense_pct),
            "current_income": str(curr_income),
            "previous_income": str(prev_income),
            "income_change": str(income_change),
            "income_change_pct": str(income_pct),
        }
