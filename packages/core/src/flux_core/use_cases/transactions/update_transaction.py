"""UpdateTransaction use case — update transaction and re-embed in zvec."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from flux_core.events.events import TransactionUpdated
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository

if TYPE_CHECKING:
    from uuid import UUID

    from flux_core.embeddings.service import EmbeddingProvider
    from flux_core.models.transaction import TransactionOut, TransactionUpdate
    from flux_core.uow.unit_of_work import UnitOfWork


class UpdateTransaction:
    """Update a transaction and re-embed in zvec (dual-write)."""

    def __init__(self, uow: UnitOfWork, embedding_svc: EmbeddingProvider):
        self._uow = uow
        self._embedding_svc = embedding_svc

    async def execute(
        self,
        txn_id: UUID,
        user_id: str,
        updates: TransactionUpdate,
    ) -> TransactionOut:
        async with self._uow:
            repo = SqliteTransactionRepository(self._uow.conn)
            updated = repo.update(txn_id, user_id, updates)
            if updated is None:
                raise ValueError(f"Transaction {txn_id} not found")

            embedding = self._embedding_svc.embed(
                f"{updated.category} {updated.description}"
            )
            self._uow.add_vector(
                "transaction_embeddings",
                str(updated.id),
                embedding,
                {"user_id": user_id},
            )
            self._uow.add_event(
                TransactionUpdated(
                    timestamp=datetime.now(UTC),
                    transaction_id=str(updated.id),
                    user_id=user_id,
                )
            )
            await self._uow.commit()

        return updated
