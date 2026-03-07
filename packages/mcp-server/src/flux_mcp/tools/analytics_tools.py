from datetime import date
from typing import Callable

from fastmcp import FastMCP
from flux_core.sqlite.database import Database
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository
from flux_core.use_cases.analytics.get_category_breakdown import GetCategoryBreakdown
from flux_core.use_cases.analytics.get_summary import GetSummary


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

        summary_uc = GetSummary(repo)
        summary = await summary_uc.execute(get_user_id(), sd, ed)

        breakdown_uc = GetCategoryBreakdown(repo)
        breakdown = await breakdown_uc.execute(get_user_id(), sd, ed)

        return {
            **summary,
            "category_breakdown": breakdown,
        }

    @mcp.tool()
    async def calculate_financial_health(start_date: str, end_date: str) -> dict:
        """Calculate a financial health score based on multiple factors."""
        db = get_db()
        repo = SqliteTransactionRepository(db.connection())
        sd = date.fromisoformat(start_date)
        ed = date.fromisoformat(end_date)

        summary_uc = GetSummary(repo)
        summary = await summary_uc.execute(get_user_id(), sd, ed)

        breakdown_uc = GetCategoryBreakdown(repo)
        breakdown = await breakdown_uc.execute(get_user_id(), sd, ed)

        return {
            "summary": summary,
            "category_breakdown": breakdown,
            "period": {"start": start_date, "end": end_date},
        }
