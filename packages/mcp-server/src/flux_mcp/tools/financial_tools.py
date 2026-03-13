from datetime import date
from decimal import Decimal
from typing import Callable
from uuid import UUID

from fastmcp import FastMCP
from flux_core.embeddings.service import EmbeddingProvider
from flux_core.models.subscription import BillingCycle
from flux_core.sqlite.database import Database
from flux_core.sqlite.budget_repo import SqliteBudgetRepository
from flux_core.sqlite.goal_repo import SqliteGoalRepository
from flux_core.sqlite.subscription_repo import SqliteSubscriptionRepository
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.budgets.list_budgets import ListBudgets
from flux_core.use_cases.budgets.remove_budget import RemoveBudget
from flux_core.use_cases.budgets.set_budget import SetBudget
from flux_core.use_cases.goals.create_goal import CreateGoal
from flux_core.use_cases.goals.delete_goal import DeleteGoal
from flux_core.use_cases.goals.deposit_to_goal import DepositToGoal
from flux_core.use_cases.goals.list_goals import ListGoals
from flux_core.use_cases.goals.withdraw_from_goal import WithdrawFromGoal
from flux_core.use_cases.subscriptions.create_subscription import CreateSubscription
from flux_core.use_cases.subscriptions.delete_subscription import DeleteSubscription
from flux_core.use_cases.subscriptions.list_subscriptions import ListSubscriptions
from flux_core.use_cases.subscriptions.toggle_subscription import ToggleSubscription


def register_financial_tools(
    mcp: FastMCP,
    get_db: Callable[[], Database],
    get_uow: Callable[[], UnitOfWork],
    get_embedding_service: Callable[[], EmbeddingProvider],
    get_user_id: Callable[[], str],
    get_user_timezone: Callable[[], str],
):
    @mcp.tool()
    async def set_budget(category: str, monthly_limit: float) -> dict:
        """Set or update a budget for a category."""
        uc = SetBudget(get_uow())
        result = await uc.execute(get_user_id(), category, Decimal(str(monthly_limit)))
        return {
            "id": str(result.id),
            "category": result.category,
            "monthly_limit": str(result.monthly_limit),
        }

    @mcp.tool()
    async def list_budgets() -> list[dict]:
        """List all budgets."""
        db = get_db()
        repo = SqliteBudgetRepository(db.connection())
        uc = ListBudgets(repo)
        results = await uc.execute(get_user_id())
        return [
            {
                "id": str(b.id),
                "category": b.category,
                "monthly_limit": str(b.monthly_limit),
            }
            for b in results
        ]

    @mcp.tool()
    async def create_goal(
        name: str, target_amount: float,
        deadline: str | None = None, color: str = "#3B82F6",
    ) -> dict:
        """Create a new savings goal."""
        uc = CreateGoal(get_uow())
        dl = date.fromisoformat(deadline) if deadline else None
        result = await uc.execute(
            get_user_id(), name, Decimal(str(target_amount)),
            deadline=dl, color=color,
        )
        return {
            "id": str(result.id),
            "name": result.name,
            "target_amount": str(result.target_amount),
            "current_amount": str(result.current_amount),
            "deadline": str(result.deadline) if result.deadline else None,
            "color": result.color,
        }

    @mcp.tool()
    async def list_goals() -> list[dict]:
        """List all savings goals."""
        db = get_db()
        repo = SqliteGoalRepository(db.connection())
        uc = ListGoals(repo)
        results = await uc.execute(get_user_id())
        return [
            {
                "id": str(g.id),
                "name": g.name,
                "target_amount": str(g.target_amount),
                "current_amount": str(g.current_amount),
                "deadline": str(g.deadline) if g.deadline else None,
                "color": g.color,
            }
            for g in results
        ]

    @mcp.tool()
    async def delete_goal(goal_id: str) -> dict:
        """Delete a savings goal permanently."""
        uc = DeleteGoal(get_uow())
        success = await uc.execute(UUID(goal_id), get_user_id())
        return {"deleted": success, "goal_id": goal_id}

    @mcp.tool()
    async def deposit_to_goal(goal_id: str, amount: float) -> dict:
        """Deposit money into a savings goal."""
        uc = DepositToGoal(get_uow())
        try:
            result = await uc.execute(UUID(goal_id), get_user_id(), Decimal(str(amount)))
        except ValueError as e:
            return {"error": str(e)}
        return {
            "id": str(result.id),
            "name": result.name,
            "target_amount": str(result.target_amount),
            "current_amount": str(result.current_amount),
            "deadline": str(result.deadline) if result.deadline else None,
            "color": result.color,
        }

    @mcp.tool()
    async def withdraw_from_goal(goal_id: str, amount: float) -> dict:
        """Withdraw money from a savings goal."""
        uc = WithdrawFromGoal(get_uow())
        try:
            result = await uc.execute(UUID(goal_id), get_user_id(), Decimal(str(amount)))
        except ValueError as e:
            return {"error": str(e)}
        return {
            "id": str(result.id),
            "name": result.name,
            "target_amount": str(result.target_amount),
            "current_amount": str(result.current_amount),
            "deadline": str(result.deadline) if result.deadline else None,
            "color": result.color,
        }

    @mcp.tool()
    async def remove_budget(category: str) -> dict:
        """Remove a budget for a category."""
        uc = RemoveBudget(get_uow())
        success = await uc.execute(get_user_id(), category)
        return {"deleted": success, "category": category}

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
        uc = CreateSubscription(get_uow())
        result = await uc.execute(
            get_user_id(), name, Decimal(str(amount)),
            BillingCycle(billing_cycle), date.fromisoformat(next_date), category,
        )
        return {
            "id": str(result.id),
            "name": result.name,
            "amount": str(result.amount),
            "billing_cycle": result.billing_cycle.value,
            "next_date": str(result.next_date),
            "category": result.category,
            "active": result.active,
        }

    @mcp.tool()
    async def list_subscriptions(active_only: bool = True) -> list[dict]:
        """List all subscriptions."""
        db = get_db()
        repo = SqliteSubscriptionRepository(db.connection())
        uc = ListSubscriptions(repo)
        results = await uc.execute(get_user_id(), active_only=active_only)
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "amount": str(s.amount),
                "billing_cycle": s.billing_cycle.value,
                "next_date": str(s.next_date),
                "category": s.category,
                "active": s.active,
            }
            for s in results
        ]

    @mcp.tool()
    async def toggle_subscription(subscription_id: str) -> dict:
        """Toggle a subscription active/inactive (archive/restore)."""
        uc = ToggleSubscription(get_uow())
        result = await uc.execute(UUID(subscription_id), get_user_id())
        return {
            "id": str(result.id),
            "name": result.name,
            "active": result.active,
            "next_date": str(result.next_date),
        }

    @mcp.tool()
    async def delete_subscription(subscription_id: str) -> dict:
        """Delete a subscription permanently."""
        uc = DeleteSubscription(get_uow())
        success = await uc.execute(UUID(subscription_id), get_user_id())
        return {"deleted": success, "subscription_id": subscription_id}

    @mcp.tool()
    async def process_subscription_billing(subscription_id: str) -> dict:
        """Process a subscription billing cycle: create expense transaction and advance next_date.
        Called automatically by the scheduler on each billing date. Do not call manually.
        """
        from flux_core.use_cases.subscriptions.process_billing import (
            ProcessSubscriptionBilling,
        )

        uc = ProcessSubscriptionBilling(get_uow(), get_embedding_service())
        return await uc.execute(get_user_id(), subscription_id, get_user_timezone())
