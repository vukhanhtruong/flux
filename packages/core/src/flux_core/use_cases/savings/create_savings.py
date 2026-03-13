"""CreateSavings use case — create savings asset + scheduled task for interest."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from flux_core.events.events import SavingsCreated
from flux_core.models.asset import AssetCreate, AssetFrequency, AssetType
from flux_core.sqlite.asset_repo import SqliteAssetRepository
from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository
from flux_core.utils import build_savings_prompt, to_utc_midnight

if TYPE_CHECKING:
    from datetime import date

    from flux_core.models.asset import AssetOut
    from flux_core.uow.unit_of_work import UnitOfWork

_NEXT_DATE_OFFSETS = {"monthly": (0, 1), "quarterly": (0, 3), "yearly": (1, 0)}


def _compute_next_date(start: date, compound_frequency: str) -> date:
    """Compute first interest application date (one period after start)."""
    years, months = _NEXT_DATE_OFFSETS[compound_frequency]
    new_month = start.month + months
    new_year = start.year + years + (new_month - 1) // 12
    new_month = (new_month - 1) % 12 + 1
    return start.replace(year=new_year, month=new_month)


class CreateSavings:
    """Create a savings deposit with compound interest and schedule interest tasks."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(
        self,
        user_id: str,
        name: str,
        amount: Decimal,
        interest_rate: Decimal,
        compound_frequency: str,
        start_date: date,
        maturity_date: date,
        category: str,
    ) -> AssetOut:
        next_date = _compute_next_date(start_date, compound_frequency)
        if next_date > maturity_date:
            next_date = maturity_date

        asset = AssetCreate(
            user_id=user_id,
            name=name,
            amount=amount,
            interest_rate=interest_rate,
            frequency=AssetFrequency(compound_frequency),
            next_date=next_date,
            category=category,
            asset_type=AssetType.savings,
            principal_amount=amount,
            compound_frequency=compound_frequency,
            maturity_date=maturity_date,
            start_date=start_date,
        )

        async with self._uow:
            asset_repo = SqliteAssetRepository(self._uow.conn)
            task_repo = SqliteBotScheduledTaskRepository(self._uow.conn)

            result = asset_repo.create(asset)

            is_maturity = next_date >= maturity_date
            prompt = build_savings_prompt(result.name, str(result.id), is_maturity)
            task_repo.create(
                user_id=user_id,
                prompt=prompt,
                schedule_type="once",
                schedule_value=next_date.isoformat(),
                next_run_at=to_utc_midnight(next_date),
                asset_id=str(result.id),
            )

            self._uow.add_event(
                SavingsCreated(
                    timestamp=datetime.now(UTC),
                    savings_id=str(result.id),
                    user_id=user_id,
                )
            )
            await self._uow.commit()

        return result
