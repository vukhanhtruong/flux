import logging
from datetime import date
from typing import Callable, Awaitable

from fastmcp import FastMCP
from flux_core.db.connection import Database
from flux_core.db.budget_repo import BudgetRepository
from flux_core.db.goal_repo import GoalRepository
from flux_core.db.subscription_repo import SubscriptionRepository
from flux_core.db.transaction_repo import TransactionRepository
from flux_core.embeddings.service import EmbeddingProvider
from flux_core.models.subscription import BillingCycle
from flux_core.tools import financial_tools as biz
from flux_mcp.db.subscription_scheduler_repo import (
    SubscriptionSchedulerRepo, _derive_cron, _to_utc_midnight,
)


# ── testable helpers ────────────────────────────────────────────────────────

async def _create_subscription_with_scheduler(
    user_id: str,
    name: str,
    amount: float,
    billing_cycle: str,
    next_date: str,
    category: str,
    sub_repo: SubscriptionRepository,
    scheduler_repo: SubscriptionSchedulerRepo,
) -> dict:
    result = await biz.create_subscription(
        user_id, name, amount, billing_cycle, next_date, category, sub_repo,
    )
    nd = date.fromisoformat(result["next_date"])
    cycle = BillingCycle(result["billing_cycle"])
    prompt = f"Process subscription billing for {result['name']} (id: {result['id']})"
    try:
        await scheduler_repo.create(
            user_id=user_id,
            subscription_id=result["id"],
            prompt=prompt,
            cron=_derive_cron(cycle, nd),
            next_run_at=_to_utc_midnight(nd),
        )
    except Exception as exc:
        logging.getLogger(__name__).error(
            "Failed to create scheduler for subscription %s: %s", result["id"], exc
        )
    return result


async def _toggle_subscription_with_scheduler(
    subscription_id: str,
    user_id: str,
    sub_repo: SubscriptionRepository,
    scheduler_repo: SubscriptionSchedulerRepo,
) -> dict:
    result = await biz.toggle_subscription(subscription_id, user_id, sub_repo)
    if result["active"]:
        nd = date.fromisoformat(result["next_date"])
        await scheduler_repo.resume(subscription_id, _to_utc_midnight(nd))
    else:
        await scheduler_repo.pause(subscription_id)
    return result


async def _delete_subscription_with_scheduler(
    subscription_id: str,
    user_id: str,
    sub_repo: SubscriptionRepository,
    scheduler_repo: SubscriptionSchedulerRepo,
) -> dict:
    # Delete scheduler entry first. If no row exists (e.g., initial create failed silently),
    # the DELETE is a no-op and subscription deletion proceeds normally.
    # Any DB error from scheduler_repo.delete() propagates and blocks subscription deletion.
    await scheduler_repo.delete(subscription_id)
    return await biz.delete_subscription(subscription_id, user_id, sub_repo)


# ── MCP tool registration ────────────────────────────────────────────────────

def register_financial_tools(
    mcp: FastMCP,
    get_db: Callable[[], Awaitable[Database]],
    get_user_id: Callable[[], str],
    get_embedding_service: Callable[[], EmbeddingProvider],
    get_user_timezone: Callable[[], Awaitable[str]],
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
        return await _create_subscription_with_scheduler(
            get_user_id(), name, amount, billing_cycle, next_date, category,
            SubscriptionRepository(db),
            SubscriptionSchedulerRepo(db),
        )

    @mcp.tool()
    async def list_subscriptions(active_only: bool = True) -> list[dict]:
        """List all subscriptions."""
        db = await get_db()
        return await biz.list_subscriptions(get_user_id(), SubscriptionRepository(db), active_only)

    @mcp.tool()
    async def toggle_subscription(subscription_id: str) -> dict:
        """Toggle a subscription active/inactive (archive/restore)."""
        db = await get_db()
        return await _toggle_subscription_with_scheduler(
            subscription_id, get_user_id(),
            SubscriptionRepository(db),
            SubscriptionSchedulerRepo(db),
        )

    @mcp.tool()
    async def delete_subscription(subscription_id: str) -> dict:
        """Delete a subscription permanently."""
        db = await get_db()
        return await _delete_subscription_with_scheduler(
            subscription_id, get_user_id(),
            SubscriptionRepository(db),
            SubscriptionSchedulerRepo(db),
        )

    @mcp.tool()
    async def process_subscription_billing(subscription_id: str) -> dict:
        """Process a subscription billing cycle: create expense transaction and advance next_date.
        Called automatically by the scheduler on each billing date. Do not call manually.
        """
        db = await get_db()
        return await biz.process_subscription_billing(
            subscription_id,
            get_user_id(),
            SubscriptionRepository(db),
            TransactionRepository(db),
            get_embedding_service(),
            user_timezone=await get_user_timezone(),
        )
