"""GetCategoryBreakdown use case — category spending breakdown."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

    from flux_core.repositories.transaction_repo import TransactionRepository


class GetCategoryBreakdown:
    """Get category-level spending breakdown for a date range (read-only)."""

    def __init__(self, txn_repo: TransactionRepository):
        self._txn_repo = txn_repo

    async def execute(
        self, user_id: str, start_date: date, end_date: date
    ) -> list[dict]:
        breakdown = self._txn_repo.get_category_breakdown(
            user_id, start_date, end_date
        )
        return [
            {
                "category": row["category"],
                "total": str(row["total"]),
                "count": row["count"],
            }
            for row in breakdown
        ]
