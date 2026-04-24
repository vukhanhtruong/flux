"""Analytics tools for the deepagents runner.

Each tool wraps an existing ``flux_core`` Use Case with ``user_id`` closed
over. The model sees these tools and never sees ``user_id`` as an argument,
so cross-user queries are structurally impossible.

Mirrors the MCP-side surface in
``packages/mcp-server/src/flux_mcp/tools/analytics_tools.py`` — the shape
of tool inputs/outputs is intentionally identical so the model experiences
the same contract regardless of host.
"""
from __future__ import annotations

from datetime import date as date_cls
from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool, StructuredTool

from flux_core.sqlite.transaction_repo import SqliteTransactionRepository
from flux_core.use_cases.analytics.get_category_breakdown import GetCategoryBreakdown
from flux_core.use_cases.analytics.get_summary import GetSummary
from flux_core.use_cases.analytics.get_trends import GetTrends

if TYPE_CHECKING:
    from flux_core.sqlite.database import Database


def build_analytics_tools(*, user_id: str, db: Database) -> list[BaseTool]:
    """Return the analytics tool set bound to a specific user.

    Args:
        user_id: The user identity closed over by every tool. Never
            exposed as a tool argument — guarantees isolation.
        db: Connected core ``Database`` (SQLite, WAL mode).
    """

    async def get_spending_summary(start_date: str, end_date: str) -> dict:
        """Generate a spending summary for a date range.

        Returns total income, total expenses, net balance, and transaction
        count for the specified period.

        Args:
            start_date: ISO date (YYYY-MM-DD) for the start of the range
                (inclusive).
            end_date: ISO date (YYYY-MM-DD) for the end of the range
                (inclusive).

        Returns:
            Dict with total_income, total_expenses, net, count, start_date,
            end_date.
        """
        repo = SqliteTransactionRepository(db.connection())
        uc = GetSummary(repo)
        return await uc.execute(
            user_id,
            date_cls.fromisoformat(start_date),
            date_cls.fromisoformat(end_date),
        )

    async def get_category_breakdown(start_date: str, end_date: str) -> list[dict]:
        """Get category-level spending breakdown for a date range.

        Aggregates expenses by category for the specified period.

        Args:
            start_date: ISO date (YYYY-MM-DD) for the start of the range
                (inclusive).
            end_date: ISO date (YYYY-MM-DD) for the end of the range
                (inclusive).

        Returns:
            List of dicts, each with category, total (decimal string),
            and count. Only expense categories are included.
        """
        repo = SqliteTransactionRepository(db.connection())
        uc = GetCategoryBreakdown(repo)
        return await uc.execute(
            user_id,
            date_cls.fromisoformat(start_date),
            date_cls.fromisoformat(end_date),
        )

    async def get_trends(
        current_start: str,
        current_end: str,
        previous_start: str,
        previous_end: str,
    ) -> dict:
        """Compare spending and income between two periods to identify trends.

        Calculates absolute and percentage changes for expenses and income.

        Args:
            current_start: ISO date (YYYY-MM-DD) for the current period start.
            current_end: ISO date (YYYY-MM-DD) for the current period end.
            previous_start: ISO date (YYYY-MM-DD) for the prior period start.
            previous_end: ISO date (YYYY-MM-DD) for the prior period end.

        Returns:
            Dict with current_expenses, previous_expenses, expense_change,
            expense_change_pct, current_income, previous_income, income_change,
            income_change_pct.
        """
        repo = SqliteTransactionRepository(db.connection())
        uc = GetTrends(repo)
        return await uc.execute(
            user_id,
            date_cls.fromisoformat(current_start),
            date_cls.fromisoformat(current_end),
            date_cls.fromisoformat(previous_start),
            date_cls.fromisoformat(previous_end),
        )

    return [
        StructuredTool.from_function(
            coroutine=get_spending_summary,
            name="get_spending_summary",
            description=get_spending_summary.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=get_category_breakdown,
            name="get_category_breakdown",
            description=get_category_breakdown.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=get_trends,
            name="get_trends",
            description=get_trends.__doc__ or "",
        ),
    ]
