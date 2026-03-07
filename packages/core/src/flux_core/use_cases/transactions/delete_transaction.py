"""DeleteTransaction use case — delete from SQLite and zvec."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from flux_core.events.events import TransactionDeleted
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository

if TYPE_CHECKING:
    from uuid import UUID

    from flux_core.uow.unit_of_work import UnitOfWork


class DeleteTransaction:
    """Delete a transaction from SQLite and zvec (dual-write)."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(self, txn_id: UUID, user_id: str) -> bool:
        async with self._uow:
            repo = SqliteTransactionRepository(self._uow.conn)
            success = repo.delete(txn_id, user_id)
            if success:
                self._uow.delete_vector("transaction_embeddings", str(txn_id))
                self._uow.add_event(
                    TransactionDeleted(
                        timestamp=datetime.now(UTC),
                        transaction_id=str(txn_id),
                        user_id=user_id,
                    )
                )
            await self._uow.commit()

        return success
