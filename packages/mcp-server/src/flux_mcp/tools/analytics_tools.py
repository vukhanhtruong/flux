from datetime import date
from typing import Callable

from fastmcp import FastMCP
from flux_core.sqlite.database import Database
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository
from flux_core.use_cases.analytics.calculate_financial_health import CalculateFinancialHealth
from flux_core.use_cases.analytics.generate_spending_report import GenerateSpendingReport
from flux_core.use_cases.analytics.get_trends import GetTrends


def register_analytics_tools(
    mcp: FastMCP,
    get_db: Callable[[], Database],
    get_user_id: Callable[[], str],
):
    @mcp.tool()
    async def generate_spending_report(start_date: str, end_date: str) -> dict:
        """Generate a spending report for a date range."""
        db = get_db()
        repo = SqliteTransactionRepository(db.connection())
        sd = date.fromisoformat(start_date)
        ed = date.fromisoformat(end_date)
        uc = GenerateSpendingReport(repo)
        return await uc.execute(get_user_id(), sd, ed)

    @mcp.tool()
    async def calculate_financial_health(start_date: str, end_date: str) -> dict:
        """Calculate a financial health score based on multiple factors."""
        db = get_db()
        repo = SqliteTransactionRepository(db.connection())
        sd = date.fromisoformat(start_date)
        ed = date.fromisoformat(end_date)
        uc = CalculateFinancialHealth(repo)
        return await uc.execute(get_user_id(), sd, ed)

    @mcp.tool()
    async def get_trends(
        current_start: str,
        current_end: str,
        previous_start: str,
        previous_end: str,
    ) -> dict:
        """Compare spending and income between two periods to identify trends."""
        db = get_db()
        repo = SqliteTransactionRepository(db.connection())
        uc = GetTrends(repo)
        return await uc.execute(
            get_user_id(),
            date.fromisoformat(current_start),
            date.fromisoformat(current_end),
            date.fromisoformat(previous_start),
            date.fromisoformat(previous_end),
        )
