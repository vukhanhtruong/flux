"""WithdrawSavings use case — create withdrawal transaction + deactivate + cleanup."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from flux_core.models.transaction import TransactionCreate, TransactionType
from flux_core.sqlite.asset_repo import SqliteAssetRepository
from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from flux_core.uow.unit_of_work import UnitOfWork


class WithdrawSavings:
    """Withdraw a savings deposit: create income transaction, deactivate asset,
    and delete the scheduled task. All within a single UoW transaction.
    """

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(
        self,
        asset_id: UUID,
        user_id: str,
        *,
        today: date | None = None,
    ) -> dict:
        async with self._uow:
            asset_repo = SqliteAssetRepository(self._uow.conn)
            txn_repo = SqliteTransactionRepository(self._uow.conn)
            task_repo = SqliteBotScheduledTaskRepository(self._uow.conn)

            asset = asset_repo.get(asset_id, user_id)
            if asset is None:
                raise ValueError(f"Savings deposit {asset_id} not found")
            if not asset.active:
                raise ValueError(f"Savings deposit {asset_id} is not active")

            withdrawal_date = today or datetime.now(UTC).date()
            txn = TransactionCreate(
                user_id=user_id,
                date=withdrawal_date,
                amount=asset.amount,
                category=asset.category,
                description=f"Withdrawal from savings: {asset.name}",
                type=TransactionType.income,
                is_recurring=False,
            )
            txn_out = txn_repo.create(txn)
            asset_repo.deactivate(asset_id, user_id)
            task_repo.delete_by_asset(str(asset_id))

            await self._uow.commit()

        return {
            "withdrawn_amount": str(asset.amount),
            "transaction_id": str(txn_out.id),
            "asset_name": asset.name,
            "asset_id": str(asset_id),
        }
