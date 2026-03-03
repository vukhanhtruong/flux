import logging
from datetime import date
from typing import Callable, Awaitable

from fastmcp import FastMCP
from flux_core.db.connection import Database
from flux_core.db.asset_repo import AssetRepository
from flux_core.tools import financial_tools as biz
from flux_mcp.db.savings_scheduler_repo import SavingsSchedulerRepo, _to_utc_midnight


def _build_savings_prompt(name: str, asset_id: str, is_maturity: bool) -> str:
    """Build the scheduler prompt, with maturity language if this is the final event."""
    base = f"Process savings interest for {name} (id: {asset_id})"
    if is_maturity:
        return (
            f"{base}. This deposit matures today. "
            "After processing, inform the user about the final balance "
            "and ask if they'd like to withdraw."
        )
    return base


# ── testable helpers ────────────────────────────────────────────────────────


async def _create_savings_with_scheduler(
    user_id: str,
    name: str,
    amount: float,
    interest_rate: float,
    compound_frequency: str,
    start_date: str,
    maturity_date: str,
    category: str,
    asset_repo: AssetRepository,
    scheduler_repo: SavingsSchedulerRepo,
) -> dict:
    result = await biz.create_savings_deposit(
        user_id, name, amount, interest_rate, compound_frequency,
        start_date, maturity_date, category, asset_repo,
    )
    nd = date.fromisoformat(result["next_date"])
    mat = date.fromisoformat(result["maturity_date"]) if result.get("maturity_date") else None
    is_maturity = mat is not None and nd >= mat
    prompt = _build_savings_prompt(result["name"], result["id"], is_maturity)
    try:
        await scheduler_repo.create(
            user_id=user_id,
            asset_id=result["id"],
            prompt=prompt,
            schedule_date=result["next_date"],
            next_run_at=_to_utc_midnight(nd),
        )
    except Exception as exc:
        logging.getLogger(__name__).error(
            "Failed to create scheduler for savings %s: %s", result["id"], exc
        )
    return result


async def _close_savings_with_scheduler(
    asset_id: str,
    user_id: str,
    asset_repo: AssetRepository,
    scheduler_repo: SavingsSchedulerRepo,
) -> dict:
    await scheduler_repo.delete(asset_id)
    return await biz.close_savings_early(asset_id, user_id, asset_repo)


async def _delete_savings_with_scheduler(
    asset_id: str,
    user_id: str,
    asset_repo: AssetRepository,
    scheduler_repo: SavingsSchedulerRepo,
) -> dict:
    await scheduler_repo.delete(asset_id)
    return await biz.delete_asset(asset_id, user_id, asset_repo)


# ── MCP tool registration ────────────────────────────────────────────────────

def register_savings_tools(
    mcp: FastMCP,
    get_db: Callable[[], Awaitable[Database]],
    get_user_id: Callable[[], str],
):
    @mcp.tool()
    async def create_savings_deposit(
        name: str,
        amount: float,
        interest_rate: float,
        compound_frequency: str,
        start_date: str,
        maturity_date: str,
        category: str,
    ) -> dict:
        """Create a new savings deposit with compound interest.
        compound_frequency must be 'monthly', 'quarterly', or 'yearly'.
        start_date and maturity_date are in YYYY-MM-DD format.
        interest_rate is annual percentage (e.g. 5.0 for 5%).
        """
        db = await get_db()
        return await _create_savings_with_scheduler(
            get_user_id(), name, amount, interest_rate, compound_frequency,
            start_date, maturity_date, category,
            AssetRepository(db),
            SavingsSchedulerRepo(db),
        )

    @mcp.tool()
    async def list_savings(active_only: bool = True) -> list[dict]:
        """List all savings deposits with interest earned."""
        db = await get_db()
        return await biz.list_savings(get_user_id(), AssetRepository(db), active_only)

    @mcp.tool()
    async def close_savings_early(asset_id: str) -> dict:
        """Close a savings deposit before maturity. Removes the scheduler."""
        db = await get_db()
        return await _close_savings_with_scheduler(
            asset_id, get_user_id(),
            AssetRepository(db),
            SavingsSchedulerRepo(db),
        )

    @mcp.tool()
    async def process_savings_interest(asset_id: str) -> dict:
        """Calculate and apply compound interest for a savings deposit.
        Called automatically by the scheduler on each compounding date.
        """
        db = await get_db()
        return await biz.process_savings_interest(
            asset_id, get_user_id(), AssetRepository(db),
        )
