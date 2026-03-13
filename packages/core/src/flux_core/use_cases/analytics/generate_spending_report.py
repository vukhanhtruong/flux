"""GenerateSpendingReport — combines summary + category breakdown."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.repositories.transaction_repo import TransactionRepository


class GenerateSpendingReport:
    """Generate a spending report combining summary and category breakdown."""

    def __init__(self, repo: TransactionRepository):
        self._repo = repo

    async def execute(self, user_id: str, start_date: date, end_date: date) -> dict:
        summary = self._repo.get_summary(user_id, start_date, end_date)
        breakdown = self._repo.get_category_breakdown(user_id, start_date, end_date)
        return {**summary, "category_breakdown": breakdown}
