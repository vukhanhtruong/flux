from datetime import datetime
from decimal import Decimal
from typing import Callable
from uuid import UUID
from zoneinfo import ZoneInfo

from fastmcp import FastMCP
from flux_core.sqlite.asset_repo import SqliteAssetRepository
from flux_core.sqlite.database import Database
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.savings.create_savings import CreateSavings
from flux_core.use_cases.savings.process_interest import ProcessInterest
from flux_core.use_cases.savings.withdraw_savings import WithdrawSavings


def register_savings_tools(
    mcp: FastMCP,
    get_db: Callable[[], Database],
    get_uow: Callable[[], UnitOfWork],
    get_user_id: Callable[[], str],
    get_user_timezone: Callable[[], str],
):
    @mcp.tool()
    async def create_savings_deposit(
        name: str,
        amount: float,
        interest_rate: float,
        compound_frequency: str,
        maturity_date: str,
        category: str,
        start_date: str | None = None,
    ) -> dict:
        """Create a new savings deposit with compound interest.
        compound_frequency must be 'monthly', 'quarterly', 'yearly', or 'at_maturity'.
        Use 'at_maturity' for fixed deposits where interest is applied once at the end.
        Default compound_frequency to 'at_maturity' if the user does not specify.
        IMPORTANT: Before calling this tool, confirm all details with the user
        (name, amount, interest rate, compound frequency, maturity date).
        maturity_date is in YYYY-MM-DD format.
        start_date is optional — defaults to today in the user's timezone.
        interest_rate is annual percentage (e.g. 5.0 for 5%).
        Scheduling is handled automatically — do NOT call schedule_task separately.
        """
        from datetime import date
        tz = get_user_timezone()
        resolved_start = start_date or datetime.now(ZoneInfo(tz)).date().isoformat()
        uc = CreateSavings(get_uow())
        result = await uc.execute(
            get_user_id(), name, Decimal(str(amount)),
            Decimal(str(interest_rate)), compound_frequency,
            date.fromisoformat(resolved_start),
            date.fromisoformat(maturity_date), category,
        )
        return {
            "id": str(result.id),
            "name": result.name,
            "amount": str(result.amount),
            "interest_rate": str(result.interest_rate),
            "compound_frequency": result.compound_frequency,
            "next_date": str(result.next_date),
            "maturity_date": str(result.maturity_date) if result.maturity_date else None,
            "active": result.active,
        }

    @mcp.tool()
    async def list_savings(active_only: bool = True) -> list[dict]:
        """List all savings deposits with interest earned."""
        db = get_db()
        repo = SqliteAssetRepository(db.connection())
        results = repo.list_by_user(get_user_id(), active_only, asset_type="savings")
        return [
            {
                "id": str(a.id),
                "name": a.name,
                "amount": str(a.amount),
                "interest_rate": str(a.interest_rate),
                "compound_frequency": a.compound_frequency,
                "next_date": str(a.next_date),
                "maturity_date": str(a.maturity_date) if a.maturity_date else None,
                "active": a.active,
            }
            for a in results
        ]

    @mcp.tool()
    async def close_savings_early(asset_id: str) -> dict:
        """Close a savings deposit before maturity. Removes the scheduler."""
        from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository

        uow = get_uow()
        user_id = get_user_id()
        asset_uuid = UUID(asset_id)

        async with uow:
            asset_repo = SqliteAssetRepository(uow.conn)
            task_repo = SqliteBotScheduledTaskRepository(uow.conn)

            task_repo.delete_by_asset(asset_id)
            result = asset_repo.deactivate(asset_uuid, user_id)
            if result is None:
                await uow.commit()
                return {"error": f"Savings deposit {asset_id} not found"}
            await uow.commit()

        return {
            "id": str(result.id),
            "name": result.name,
            "active": result.active,
            "amount": str(result.amount),
            "status": "closed_early",
        }

    @mcp.tool()
    async def process_savings_interest(asset_id: str) -> dict:
        """Calculate and apply compound interest for a savings deposit.
        Called automatically by the scheduler on each compounding date.
        """
        uc = ProcessInterest(get_uow())
        return await uc.execute(UUID(asset_id), get_user_id())

    @mcp.tool()
    async def withdraw_savings(asset_id: str) -> dict:
        """Withdraw a matured (or early-closed) savings deposit.
        Creates an income transaction for the full balance and deactivates the asset.
        Money moves from 'asset balance' to 'cash (transactions)'.
        """
        tz = get_user_timezone()
        today = datetime.now(ZoneInfo(tz)).date()
        uc = WithdrawSavings(get_uow())
        return await uc.execute(UUID(asset_id), get_user_id(), today=today)

    @mcp.tool()
    async def delete_savings(asset_id: str) -> dict:
        """Delete a savings deposit permanently."""
        from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository

        uow = get_uow()
        user_id = get_user_id()
        asset_uuid = UUID(asset_id)

        async with uow:
            task_repo = SqliteBotScheduledTaskRepository(uow.conn)
            asset_repo = SqliteAssetRepository(uow.conn)

            task_repo.delete_by_asset(asset_id)
            success = asset_repo.delete(asset_uuid, user_id)
            await uow.commit()

        return {"deleted": success, "asset_id": asset_id}
