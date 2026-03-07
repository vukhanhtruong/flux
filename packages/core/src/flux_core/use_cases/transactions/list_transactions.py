"""ListTransactions use case — read-only listing with filters."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.models.transaction import TransactionOut
    from flux_core.repositories.transaction_repo import TransactionRepository


class ListTransactions:
    """List transactions for a user with optional filters (read-only)."""

    def __init__(self, txn_repo: TransactionRepository):
        self._txn_repo = txn_repo

    async def execute(
        self,
        user_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        categories: list[str] | None = None,
        txn_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TransactionOut]:
        return self._txn_repo.list_by_user(
            user_id,
            start_date=start_date,
            end_date=end_date,
            categories=categories,
            txn_type=txn_type,
            limit=limit,
            offset=offset,
        )
