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
from flux_core.models.goal import GoalCreate
from flux_core.models.subscription import SubscriptionCreate, BillingCycle
from flux_core.models.asset import AssetCreate, AssetFrequency, AssetOut, AssetType
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


def _asset_to_dict(a: AssetOut) -> dict:
    """Convert an AssetOut to a base response dict (all asset types)."""
    return {
        "id": str(a.id),
        "user_id": a.user_id,
        "name": a.name,
        "amount": str(a.amount),
        "interest_rate": str(a.interest_rate),
        "frequency": a.frequency.value,
        "next_date": str(a.next_date),
        "category": a.category,
        "active": a.active,
        "asset_type": a.asset_type.value,
    }


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
    return _asset_to_dict(result)


async def list_assets(
    user_id: str,
    repo: AssetRepository,
    active_only: bool = True
) -> list[dict]:
    """List assets for a user."""
    assets = await repo.list_by_user(user_id, active_only)
    return [_asset_to_dict(a) for a in assets]


async def advance_asset(
    asset_id: str,
    user_id: str,
    repo: AssetRepository
) -> dict:
    """Advance the next payment date for an asset."""
    result = await repo.advance_next_date(UUID(asset_id), user_id)
    if not result:
        raise ValueError(f"Asset {asset_id} not found")

    return _asset_to_dict(result)


async def delete_asset(
    asset_id: str,
    user_id: str,
    repo: AssetRepository
) -> dict:
    """Delete an asset."""
    success = await repo.delete(UUID(asset_id), user_id)
    return {"success": success}


# Savings tools

COMPOUND_PERIODS = {"monthly": 12, "quarterly": 4, "yearly": 1}

_NEXT_DATE_OFFSETS = {"monthly": (0, 1), "quarterly": (0, 3), "yearly": (1, 0)}


def _savings_to_dict(asset: AssetOut) -> dict:
    """Convert an AssetOut (savings type) to a response dict with savings-specific fields."""
    d = _asset_to_dict(asset)
    d.update({
        "principal_amount": str(asset.principal_amount) if asset.principal_amount else None,
        "compound_frequency": asset.compound_frequency,
        "maturity_date": str(asset.maturity_date) if asset.maturity_date else None,
        "start_date": str(asset.start_date) if asset.start_date else None,
    })
    return d


def _compute_next_date(start: _date, compound_frequency: str) -> _date:
    """Compute first interest application date (one period after start)."""
    years, months = _NEXT_DATE_OFFSETS[compound_frequency]
    new_month = start.month + months
    new_year = start.year + years + (new_month - 1) // 12
    new_month = (new_month - 1) % 12 + 1
    return start.replace(year=new_year, month=new_month)


async def create_savings_deposit(
    user_id: str,
    name: str,
    amount: float,
    interest_rate: float,
    compound_frequency: str,
    start_date: str,
    maturity_date: str,
    category: str,
    repo: AssetRepository,
) -> dict:
    """Create a new savings deposit with compound interest."""
    start = _date.fromisoformat(start_date)
    maturity = _date.fromisoformat(maturity_date)
    next_date = _compute_next_date(start, compound_frequency)

    if next_date > maturity:
        next_date = maturity

    asset = AssetCreate(
        user_id=user_id,
        name=name,
        amount=Decimal(str(amount)),
        interest_rate=Decimal(str(interest_rate)),
        frequency=AssetFrequency(compound_frequency),
        next_date=next_date,
        category=category,
        asset_type=AssetType.savings,
        principal_amount=Decimal(str(amount)),
        compound_frequency=compound_frequency,
        maturity_date=_date.fromisoformat(maturity_date),
        start_date=start,
    )
    result = await repo.create(asset)
    return _savings_to_dict(result)


async def process_savings_interest(
    asset_id: str,
    user_id: str,
    repo: AssetRepository,
) -> dict:
    """Calculate and apply compound interest for a savings deposit."""
    aid = UUID(asset_id)
    asset = await repo.get(aid, user_id)
    if asset is None:
        raise ValueError(f"Savings deposit {asset_id} not found")
    if not asset.active:
        raise ValueError(f"Savings deposit {asset_id} is not active")

    freq = asset.compound_frequency or asset.frequency.value
    periods = COMPOUND_PERIODS[freq]
    interest = (asset.amount * (asset.interest_rate / 100 / periods)).quantize(
        Decimal("0.01")
    )
    new_balance = asset.amount + interest

    await repo.update_amount(aid, user_id, new_balance)
    advanced = await repo.advance_next_date(aid, user_id)

    matured = False
    maturity_message = None
    if asset.maturity_date and advanced and advanced.next_date > asset.maturity_date:
        matured = True
        maturity_message = (
            f"Savings deposit '{asset.name}' has matured. "
            f"Final balance: {new_balance}"
        )
        await repo.deactivate(aid, user_id)

    result: dict = {
        "interest_applied": str(interest),
        "new_balance": str(new_balance),
        "matured": matured,
    }
    if maturity_message:
        result["maturity_message"] = maturity_message
    return result


async def list_savings(
    user_id: str,
    repo: AssetRepository,
    active_only: bool = True,
) -> list[dict]:
    """List savings deposits for a user, including interest earned."""
    assets = await repo.list_by_user(user_id, active_only, asset_type="savings")
    results = []
    for a in assets:
        d = _savings_to_dict(a)
        earned = a.amount - (a.principal_amount or a.amount)
        d["interest_earned"] = str(earned)
        results.append(d)
    return results


async def close_savings_early(
    asset_id: str,
    user_id: str,
    repo: AssetRepository,
) -> dict:
    """Close a savings deposit before maturity."""
    aid = UUID(asset_id)
    asset = await repo.get(aid, user_id)
    if asset is None:
        raise ValueError(f"Savings deposit {asset_id} not found")
    if not asset.active:
        raise ValueError(f"Savings deposit {asset_id} is not active")

    result = await repo.deactivate(aid, user_id)
    return _savings_to_dict(result)


async def withdraw_savings(
    asset_id: str,
    user_id: str,
    asset_repo: AssetRepository,
    txn_repo: TransactionRepository,
) -> dict:
    """Withdraw a savings deposit: create income transaction + deactivate asset."""
    aid = UUID(asset_id)
    asset = await asset_repo.get(aid, user_id)
    if asset is None:
        raise ValueError(f"Savings deposit {asset_id} not found")
    if not asset.active:
        raise ValueError(f"Savings deposit {asset_id} is not active")

    txn = TransactionCreate(
        user_id=user_id,
        date=_date.today(),
        amount=asset.amount,
        category=asset.category,
        description=f"Withdrawal from savings: {asset.name}",
        type=TransactionType.income,
        is_recurring=False,
    )
    # TODO: These two writes are not wrapped in a DB transaction. If deactivate
    # fails after create succeeds, the asset remains active while the income
    # transaction exists (double-count). Fix requires shared-connection support
    # in the Database abstraction.
    txn_out = await txn_repo.create(txn)
    await asset_repo.deactivate(aid, user_id)

    return {
        "withdrawn_amount": str(asset.amount),
        "transaction_id": str(txn_out.id),
        "asset_name": asset.name,
        "asset_id": asset_id,
    }
