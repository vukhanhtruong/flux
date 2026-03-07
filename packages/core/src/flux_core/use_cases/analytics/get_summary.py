"""GetSummary use case — spending report for a date range."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

    from flux_core.repositories.transaction_repo import TransactionRepository


class GetSummary:
    """Generate a spending summary for a date range (read-only)."""

    def __init__(self, txn_repo: TransactionRepository):
        self._txn_repo = txn_repo

    async def execute(
        self, user_id: str, start_date: date, end_date: date
    ) -> dict:
        summary = self._txn_repo.get_summary(user_id, start_date, end_date)

        total_income = summary.get("total_income") or Decimal("0")
        total_expenses = summary.get("total_expenses") or Decimal("0")
        net = total_income - total_expenses

        return {
            "total_income": str(total_income),
            "total_expenses": str(total_expenses),
            "net": str(net),
            "count": summary.get("count", 0),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
