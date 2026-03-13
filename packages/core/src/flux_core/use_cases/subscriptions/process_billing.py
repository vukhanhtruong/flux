"""ProcessSubscriptionBilling — create expense transaction for subscription billing."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID
from zoneinfo import ZoneInfo

from flux_core.models.transaction import TransactionCreate, TransactionType
from flux_core.sqlite.subscription_repo import SqliteSubscriptionRepository
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository

if TYPE_CHECKING:
    from flux_core.embeddings.service import EmbeddingProvider
    from flux_core.uow.unit_of_work import UnitOfWork


class ProcessSubscriptionBilling:
    """Process a subscription billing cycle: create expense transaction and advance next_date."""

    def __init__(self, uow: UnitOfWork, embedding_svc: EmbeddingProvider):
        self._uow = uow
        self._embedding_svc = embedding_svc

    async def execute(self, user_id: str, subscription_id: str, timezone: str) -> dict:
        sub_uuid = UUID(subscription_id)

        async with self._uow:
            sub_repo = SqliteSubscriptionRepository(self._uow.conn)
            txn_repo = SqliteTransactionRepository(self._uow.conn)

            sub = sub_repo.get(sub_uuid, user_id)
            if sub is None:
                return {"error": f"Subscription {subscription_id} not found"}
            if not sub.active:
                return {"error": f"Subscription {subscription_id} is not active"}

            today = datetime.now(ZoneInfo(timezone)).date()
            txn = TransactionCreate(
                user_id=user_id,
                date=today,
                amount=sub.amount,
                category=sub.category,
                description=f"Subscription: {sub.name}",
                type=TransactionType.expense,
                is_recurring=True,
            )
            txn_out = txn_repo.create(txn)
            sub_repo.advance_next_date(sub_uuid, user_id)

            embedding = self._embedding_svc.embed(
                f"{sub.category} Subscription: {sub.name}"
            )
            self._uow.add_vector(
                "transaction_embeddings", str(txn_out.id),
                embedding, {"user_id": user_id},
            )

            await self._uow.commit()

        return {
            "transaction_id": str(txn_out.id),
            "subscription_name": sub.name,
            "amount": str(sub.amount),
            "billing_date": str(today),
        }
