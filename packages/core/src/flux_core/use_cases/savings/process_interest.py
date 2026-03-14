"""ProcessInterest use case — compound interest on savings + reschedule."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from flux_core.sqlite.asset_repo import SqliteAssetRepository
from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository
from flux_core.utils import build_savings_prompt, to_utc_midnight

if TYPE_CHECKING:
    from uuid import UUID

    from flux_core.uow.unit_of_work import UnitOfWork

COMPOUND_PERIODS = {"monthly": 12, "quarterly": 4, "yearly": 1}


class ProcessInterest:
    """Calculate and apply compound interest for a savings deposit.

    After applying interest, either reschedules the next interest task
    or deactivates the asset if it has matured.
    """

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(self, asset_id: UUID, user_id: str) -> dict:
        async with self._uow:
            asset_repo = SqliteAssetRepository(self._uow.conn)
            task_repo = SqliteBotScheduledTaskRepository(self._uow.conn)

            asset = asset_repo.get(asset_id, user_id)
            if asset is None:
                raise ValueError(f"Savings deposit {asset_id} not found")
            if not asset.active:
                raise ValueError(f"Savings deposit {asset_id} is not active")

            freq = asset.compound_frequency or asset.frequency.value
            if freq == "at_maturity" and asset.start_date and asset.maturity_date:
                months = (
                    (asset.maturity_date.year - asset.start_date.year) * 12
                    + asset.maturity_date.month
                    - asset.start_date.month
                )
                interest = (
                    asset.amount * asset.interest_rate / 100 / 12 * months
                ).quantize(Decimal("0.01"))
            else:
                periods = COMPOUND_PERIODS[freq]
                interest = (asset.amount * (asset.interest_rate / 100 / periods)).quantize(
                    Decimal("0.01")
                )
            new_balance = asset.amount + interest

            asset_repo.update_amount(asset_id, user_id, new_balance)
            advanced = asset_repo.advance_next_date(asset_id, user_id)

            matured = False
            maturity_message = None
            if (
                asset.maturity_date
                and advanced
                and advanced.next_date > asset.maturity_date
            ):
                matured = True
                maturity_message = (
                    f"Savings deposit '{asset.name}' has matured. "
                    f"Final balance: {new_balance}"
                )
                asset_repo.deactivate(asset_id, user_id)
            elif advanced and advanced.active:
                # Schedule next interest processing
                nd = advanced.next_date
                is_maturity = (
                    asset.maturity_date is not None and nd >= asset.maturity_date
                )
                prompt = build_savings_prompt(
                    asset.name, str(asset_id), is_maturity
                )
                task_repo.create(
                    user_id=user_id,
                    prompt=prompt,
                    schedule_type="once",
                    schedule_value=str(nd),
                    next_run_at=to_utc_midnight(nd),
                    asset_id=str(asset_id),
                )

            await self._uow.commit()

        result: dict = {
            "interest_applied": str(interest),
            "new_balance": str(new_balance),
            "matured": matured,
        }
        if maturity_message:
            result["maturity_message"] = maturity_message
        return result
