"""TransactionRepository Protocol — interface for transaction data access."""

from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from flux_core.models.transaction import TransactionCreate, TransactionOut, TransactionUpdate


class TransactionRepository(Protocol):
    """Repository interface for transactions."""

    def create(self, txn: TransactionCreate) -> TransactionOut: ...

    def get_by_id(self, txn_id: UUID, user_id: str) -> TransactionOut | None: ...

    def get_by_ids(self, ids: list[UUID]) -> list[TransactionOut]: ...

    def list_by_user(
        self,
        user_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        categories: list[str] | None = None,
        txn_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TransactionOut]: ...

    def update(
        self, txn_id: UUID, user_id: str, updates: TransactionUpdate
    ) -> TransactionOut | None: ...

    def delete(self, txn_id: UUID, user_id: str) -> bool: ...

    def get_summary(self, user_id: str, start_date: date, end_date: date) -> dict: ...

    def get_category_breakdown(
        self, user_id: str, start_date: date, end_date: date
    ) -> list[dict]: ...
