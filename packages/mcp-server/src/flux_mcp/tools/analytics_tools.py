from typing import Callable, Awaitable

from fastmcp import FastMCP
from flux_core.db.connection import Database
from flux_core.db.transaction_repo import TransactionRepository
from flux_core.db.budget_repo import BudgetRepository
from flux_core.db.goal_repo import GoalRepository
from flux_core.tools import analytics_tools as biz


def register_analytics_tools(
    mcp: FastMCP,
    get_db: Callable[[], Awaitable[Database]],
    get_user_id: Callable[[], str],
):
    @mcp.tool()
    async def generate_spending_report(start_date: str, end_date: str) -> dict:
        """Generate a spending report for a date range."""
        db = await get_db()
        return await biz.generate_spending_report(
            get_user_id(), start_date, end_date, TransactionRepository(db),
        )

    @mcp.tool()
    async def calculate_financial_health(start_date: str, end_date: str) -> dict:
        """Calculate a financial health score based on multiple factors."""
        db = await get_db()
        return await biz.calculate_financial_health(
            get_user_id(), start_date, end_date,
            TransactionRepository(db), BudgetRepository(db), GoalRepository(db),
        )
