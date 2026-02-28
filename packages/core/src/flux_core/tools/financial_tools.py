from datetime import date as _date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from flux_core.db.budget_repo import BudgetRepository
from flux_core.db.goal_repo import GoalRepository
from flux_core.db.subscription_repo import SubscriptionRepository
from flux_core.db.asset_repo import AssetRepository
from flux_core.db.transaction_repo import TransactionRepository
from flux_core.embeddings.service import EmbeddingProvider
from flux_core.models.budget import BudgetSet
from flux_core.models.goal import GoalCreate, GoalUpdate
from flux_core.models.subscription import SubscriptionCreate, BillingCycle
from flux_core.models.asset import AssetCreate, AssetFrequency
from flux_core.models.transaction import TransactionCreate, TransactionType


# Budget tools
async def set_budget(
    user_id: str,
    category: str,
    monthly_limit: float,
    repo: BudgetRepository
) -> dict:
    """Set or update a budget for a category."""
    budget = BudgetSet(
        user_id=user_id,
        category=category,
        monthly_limit=Decimal(str(monthly_limit))
    )
    result = await repo.set(budget)
    return {
        "id": str(result.id),
        "user_id": result.user_id,
        "category": result.category,
        "monthly_limit": str(result.monthly_limit)
    }


async def list_budgets(
    user_id: str,
    repo: BudgetRepository
) -> list[dict]:
    """List all budgets for a user."""
    budgets = await repo.list_by_user(user_id)
    return [
        {
            "id": str(b.id),
            "user_id": b.user_id,
            "category": b.category,
            "monthly_limit": str(b.monthly_limit)
        }
        for b in budgets
    ]


async def remove_budget(
    user_id: str,
    category: str,
    repo: BudgetRepository
) -> dict:
    """Remove a budget for a category."""
    success = await repo.remove(user_id, category)
    return {"success": success}


# Goal tools
async def create_goal(
    user_id: str,
    name: str,
    target_amount: float,
    repo: GoalRepository,
    deadline: Optional[str] = None,
    color: str = "#3B82F6"
) -> dict:
    """Create a new savings goal."""
    goal = GoalCreate(
        user_id=user_id,
        name=name,
        target_amount=Decimal(str(target_amount)),
        deadline=deadline,
        color=color
    )
    result = await repo.create(goal)
    return {
        "id": str(result.id),
        "user_id": result.user_id,
        "name": result.name,
        "target_amount": str(result.target_amount),
        "current_amount": str(result.current_amount),
        "deadline": str(result.deadline) if result.deadline else None,
        "color": result.color
    }


async def list_goals(
    user_id: str,
    repo: GoalRepository
) -> list[dict]:
    """List all savings goals for a user."""
    goals = await repo.list_by_user(user_id)
    return [
        {
            "id": str(g.id),
            "user_id": g.user_id,
            "name": g.name,
            "target_amount": str(g.target_amount),
            "current_amount": str(g.current_amount),
            "deadline": str(g.deadline) if g.deadline else None,
            "color": g.color
        }
        for g in goals
    ]


async def deposit_to_goal(
    goal_id: str,
    user_id: str,
    amount: float,
    repo: GoalRepository
) -> dict:
    """Deposit money to a savings goal."""
    result = await repo.deposit(UUID(goal_id), user_id, Decimal(str(amount)))
    if not result:
        raise ValueError(f"Goal {goal_id} not found")

    return {
        "id": str(result.id),
        "user_id": result.user_id,
        "name": result.name,
        "target_amount": str(result.target_amount),
        "current_amount": str(result.current_amount),
        "deadline": str(result.deadline) if result.deadline else None,
        "color": result.color
    }


async def withdraw_from_goal(
    goal_id: str,
    user_id: str,
    amount: float,
    repo: GoalRepository
) -> dict:
    """Withdraw money from a savings goal."""
    result = await repo.withdraw(UUID(goal_id), user_id, Decimal(str(amount)))
    if not result:
        raise ValueError(f"Goal {goal_id} not found")

    return {
        "id": str(result.id),
        "user_id": result.user_id,
        "name": result.name,
        "target_amount": str(result.target_amount),
        "current_amount": str(result.current_amount),
        "deadline": str(result.deadline) if result.deadline else None,
        "color": result.color
    }


async def delete_goal(
    goal_id: str,
    user_id: str,
    repo: GoalRepository
) -> dict:
    """Delete a savings goal."""
    success = await repo.delete(UUID(goal_id), user_id)
    return {"success": success}


# Subscription tools
async def create_subscription(
    user_id: str,
    name: str,
    amount: float,
    billing_cycle: str,
    next_date: str,
    category: str,
    repo: SubscriptionRepository
) -> dict:
    """Create a new subscription."""
    subscription = SubscriptionCreate(
        user_id=user_id,
        name=name,
        amount=Decimal(str(amount)),
        billing_cycle=BillingCycle(billing_cycle),
        next_date=next_date,
        category=category
    )
    result = await repo.create(subscription)
    return {
        "id": str(result.id),
        "user_id": result.user_id,
        "name": result.name,
        "amount": str(result.amount),
        "billing_cycle": result.billing_cycle.value,
        "next_date": str(result.next_date),
        "category": result.category,
        "active": result.active
    }


async def list_subscriptions(
    user_id: str,
    repo: SubscriptionRepository,
    active_only: bool = True
) -> list[dict]:
    """List subscriptions for a user."""
    subscriptions = await repo.list_by_user(user_id, active_only)
    return [
        {
            "id": str(s.id),
            "user_id": s.user_id,
            "name": s.name,
            "amount": str(s.amount),
            "billing_cycle": s.billing_cycle.value,
            "next_date": str(s.next_date),
            "category": s.category,
            "active": s.active
        }
        for s in subscriptions
    ]


async def advance_subscription(
    subscription_id: str,
    user_id: str,
    repo: SubscriptionRepository
) -> dict:
    """Advance the next billing date for a subscription."""
    result = await repo.advance_next_date(UUID(subscription_id), user_id)
    if not result:
        raise ValueError(f"Subscription {subscription_id} not found")

    return {
        "id": str(result.id),
        "user_id": result.user_id,
        "name": result.name,
        "amount": str(result.amount),
        "billing_cycle": result.billing_cycle.value,
        "next_date": str(result.next_date),
        "category": result.category,
        "active": result.active
    }


async def toggle_subscription(
    subscription_id: str,
    user_id: str,
    repo: SubscriptionRepository
) -> dict:
    """Toggle subscription active status."""
    result = await repo.toggle_active(UUID(subscription_id), user_id)
    if not result:
        raise ValueError(f"Subscription {subscription_id} not found")

    return {
        "id": str(result.id),
        "user_id": result.user_id,
        "name": result.name,
        "amount": str(result.amount),
        "billing_cycle": result.billing_cycle.value,
        "next_date": str(result.next_date),
        "category": result.category,
        "active": result.active
    }


async def delete_subscription(
    subscription_id: str,
    user_id: str,
    repo: SubscriptionRepository
) -> dict:
    """Delete a subscription."""
    success = await repo.delete(UUID(subscription_id), user_id)
    return {"success": success}


async def process_subscription_billing(
    subscription_id: str,
    user_id: str,
    sub_repo: SubscriptionRepository,
    txn_repo: TransactionRepository,
    embedding_service: EmbeddingProvider,
) -> dict:
    """Create the expense transaction for a due subscription and advance next_date.

    Called by the scheduler on each billing date. Raises ValueError if the
    subscription is not found or is inactive.
    """
    sub = await sub_repo.get(UUID(subscription_id), user_id)
    if sub is None:
        raise ValueError(f"Subscription {subscription_id} not found")
    if not sub.active:
        raise ValueError(f"Subscription {subscription_id} is not active")

    transaction = TransactionCreate(
        user_id=user_id,
        date=_date.today(),
        amount=sub.amount,
        category=sub.category,
        description=f"{sub.name} subscription",
        type=TransactionType.expense,
        is_recurring=True,
        tags=[],
    )
    embedding = embedding_service.embed(f"{sub.category} {sub.name} subscription")
    txn_result = await txn_repo.create(transaction, embedding)

    updated_sub = await sub_repo.advance_next_date(UUID(subscription_id), user_id)

    return {
        "transaction": {
            "id": str(txn_result.id),
            "user_id": txn_result.user_id,
            "date": str(txn_result.date),
            "amount": str(txn_result.amount),
            "category": txn_result.category,
            "description": txn_result.description,
            "type": txn_result.type.value,
            "is_recurring": txn_result.is_recurring,
        },
        "subscription": {
            "id": str(updated_sub.id),
            "name": updated_sub.name,
            "next_date": str(updated_sub.next_date),
            "billing_cycle": updated_sub.billing_cycle.value,
        },
    }


# Asset tools
async def create_asset(
    user_id: str,
    name: str,
    amount: float,
    interest_rate: float,
    frequency: str,
    next_date: str,
    category: str,
    repo: AssetRepository
) -> dict:
    """Create a new asset (recurring income)."""
    asset = AssetCreate(
        user_id=user_id,
        name=name,
        amount=Decimal(str(amount)),
        interest_rate=Decimal(str(interest_rate)),
        frequency=AssetFrequency(frequency),
        next_date=next_date,
        category=category
    )
    result = await repo.create(asset)
    return {
        "id": str(result.id),
        "user_id": result.user_id,
        "name": result.name,
        "amount": str(result.amount),
        "interest_rate": str(result.interest_rate),
        "frequency": result.frequency.value,
        "next_date": str(result.next_date),
        "category": result.category,
        "active": result.active
    }


async def list_assets(
    user_id: str,
    repo: AssetRepository,
    active_only: bool = True
) -> list[dict]:
    """List assets for a user."""
    assets = await repo.list_by_user(user_id, active_only)
    return [
        {
            "id": str(a.id),
            "user_id": a.user_id,
            "name": a.name,
            "amount": str(a.amount),
            "interest_rate": str(a.interest_rate),
            "frequency": a.frequency.value,
            "next_date": str(a.next_date),
            "category": a.category,
            "active": a.active
        }
        for a in assets
    ]


async def advance_asset(
    asset_id: str,
    user_id: str,
    repo: AssetRepository
) -> dict:
    """Advance the next payment date for an asset."""
    result = await repo.advance_next_date(UUID(asset_id), user_id)
    if not result:
        raise ValueError(f"Asset {asset_id} not found")

    return {
        "id": str(result.id),
        "user_id": result.user_id,
        "name": result.name,
        "amount": str(result.amount),
        "interest_rate": str(result.interest_rate),
        "frequency": result.frequency.value,
        "next_date": str(result.next_date),
        "category": result.category,
        "active": result.active
    }


async def delete_asset(
    asset_id: str,
    user_id: str,
    repo: AssetRepository
) -> dict:
    """Delete an asset."""
    success = await repo.delete(UUID(asset_id), user_id)
    return {"success": success}
