"""Budget tools for the deepagents runner.

Each tool wraps an existing ``flux_core`` Use Case with ``user_id`` closed
over. The model sees these tools and never sees ``user_id`` as an argument,
so cross-user queries are structurally impossible.

Mirrors the MCP-side surface in
``packages/mcp-server/src/flux_mcp/tools/financial_tools.py`` — the shape
of tool inputs/outputs is intentionally identical so the model experiences
the same contract regardless of host.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool, StructuredTool

from flux_core.sqlite.budget_repo import SqliteBudgetRepository
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.budgets.check_budgets import CheckBudgets
from flux_core.use_cases.budgets.list_budgets import ListBudgets
from flux_core.use_cases.budgets.set_budget import SetBudget

if TYPE_CHECKING:
    from flux_core.sqlite.database import Database


def build_budget_tools(*, user_id: str, db: Database) -> list[BaseTool]:
    """Return the budget tool set bound to a specific user.

    Args:
        user_id: The user identity closed over by every tool. Never
            exposed as a tool argument — guarantees isolation.
        db: Connected core ``Database`` (SQLite, WAL mode).
    """

    async def set_budget(category: str, monthly_limit: str) -> dict:
        """Set or update a budget limit for a spending category.

        Args:
            category: Short category name (e.g. "food", "transport").
            monthly_limit: Decimal string for the monthly spend cap, e.g.
                "500.00". Must be > 0.

        Returns:
            Dict with id, category, monthly_limit.
        """
        uow = UnitOfWork(db)
        uc = SetBudget(uow)
        result = await uc.execute(user_id, category, Decimal(monthly_limit))
        return {
            "id": str(result.id),
            "category": result.category,
            "monthly_limit": str(result.monthly_limit),
        }

    async def list_budgets() -> list[dict]:
        """List all budgets for the current user.

        Returns:
            List of dicts, each with id, category, monthly_limit.
        """
        repo = SqliteBudgetRepository(db.connection())
        uc = ListBudgets(repo)
        results = await uc.execute(user_id)
        return [
            {
                "id": str(b.id),
                "category": b.category,
                "monthly_limit": str(b.monthly_limit),
            }
            for b in results
        ]

    async def check_budgets() -> list[dict]:
        """Check all budgets with current-month spending status.

        Returns each budget with: category, monthly_limit, spent_this_month,
        percent_used, remaining, and is_over_budget. Automatically scopes
        spending to the current calendar month.

        Returns:
            List of dicts with budget status for each category.
        """
        conn = db.connection()
        budget_repo = SqliteBudgetRepository(conn)
        txn_repo = SqliteTransactionRepository(conn)
        uc = CheckBudgets(budget_repo, txn_repo)
        return await uc.execute(user_id)

    return [
        StructuredTool.from_function(
            coroutine=set_budget,
            name="set_budget",
            description=set_budget.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=list_budgets,
            name="list_budgets",
            description=list_budgets.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=check_budgets,
            name="check_budgets",
            description=check_budgets.__doc__ or "",
        ),
    ]
