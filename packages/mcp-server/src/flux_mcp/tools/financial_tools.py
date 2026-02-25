from typing import Callable, Awaitable

from fastmcp import FastMCP
from flux_core.db.connection import Database
from flux_core.db.budget_repo import BudgetRepository
from flux_core.db.goal_repo import GoalRepository
from flux_core.db.subscription_repo import SubscriptionRepository
from flux_core.tools import financial_tools as biz


def register_financial_tools(
    mcp: FastMCP,
    get_db: Callable[[], Awaitable[Database]],
    get_user_id: Callable[[], str],
):
    @mcp.tool()
    async def set_budget(category: str, monthly_limit: float) -> dict:
        """Set or update a budget for a category."""
        db = await get_db()
        return await biz.set_budget(get_user_id(), category, monthly_limit, BudgetRepository(db))

    @mcp.tool()
    async def list_budgets() -> list[dict]:
        """List all budgets."""
        db = await get_db()
        return await biz.list_budgets(get_user_id(), BudgetRepository(db))

    @mcp.tool()
    async def create_goal(
        name: str, target_amount: float,
        deadline: str | None = None, color: str = "#3B82F6",
    ) -> dict:
        """Create a new savings goal."""
        db = await get_db()
        return await biz.create_goal(
            get_user_id(), name, target_amount, GoalRepository(db), deadline, color,
        )

    @mcp.tool()
    async def list_goals() -> list[dict]:
        """List all savings goals."""
        db = await get_db()
        return await biz.list_goals(get_user_id(), GoalRepository(db))

    @mcp.tool()
    async def create_subscription(
        name: str,
        amount: float,
        billing_cycle: str,
        next_date: str,
        category: str,
    ) -> dict:
        """Create a new recurring subscription (e.g. Netflix monthly, Google One yearly).
        billing_cycle must be 'monthly' or 'yearly'.
        next_date is the next billing date in YYYY-MM-DD format.
        """
        db = await get_db()
        return await biz.create_subscription(
            get_user_id(), name, amount, billing_cycle, next_date, category,
            SubscriptionRepository(db),
        )

    @mcp.tool()
    async def list_subscriptions(active_only: bool = True) -> list[dict]:
        """List all subscriptions."""
        db = await get_db()
        return await biz.list_subscriptions(get_user_id(), SubscriptionRepository(db), active_only)

    @mcp.tool()
    async def toggle_subscription(subscription_id: str) -> dict:
        """Toggle a subscription active/inactive."""
        db = await get_db()
        return await biz.toggle_subscription(subscription_id, get_user_id(), SubscriptionRepository(db))

    @mcp.tool()
    async def delete_subscription(subscription_id: str) -> dict:
        """Delete a subscription permanently."""
        db = await get_db()
        return await biz.delete_subscription(subscription_id, get_user_id(), SubscriptionRepository(db))
