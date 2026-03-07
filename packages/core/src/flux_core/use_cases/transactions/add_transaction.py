"""AddTransaction use case — create a transaction with embedding."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from flux_core.events.events import TransactionCreated
from flux_core.models.transaction import TransactionCreate, TransactionType
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository

if TYPE_CHECKING:
    from datetime import date

    from flux_core.embeddings.service import EmbeddingProvider
    from flux_core.models.transaction import TransactionOut
    from flux_core.uow.unit_of_work import UnitOfWork


class AddTransaction:
    """Create a new transaction with semantic embedding (dual-write)."""

    def __init__(self, uow: UnitOfWork, embedding_svc: EmbeddingProvider):
        self._uow = uow
        self._embedding_svc = embedding_svc

    async def execute(
        self,
        user_id: str,
        date: date,
        amount: Decimal,
        category: str,
        description: str,
        transaction_type: TransactionType,
        *,
        is_recurring: bool = False,
        tags: list[str] | None = None,
    ) -> TransactionOut:
        txn = TransactionCreate(
            user_id=user_id,
            date=date,
            amount=amount,
            category=category,
            description=description,
            type=transaction_type,
            is_recurring=is_recurring,
            tags=tags or [],
        )

        embedding = self._embedding_svc.embed(f"{category} {description}")

        async with self._uow:
            repo = SqliteTransactionRepository(self._uow.conn)
            created = repo.create(txn)
            self._uow.add_vector(
                "transaction_embeddings",
                str(created.id),
                embedding,
                {"user_id": user_id},
            )
            self._uow.add_event(
                TransactionCreated(
                    timestamp=datetime.now(UTC),
                    transaction_id=str(created.id),
                    user_id=user_id,
                )
            )
            await self._uow.commit()

        return created
