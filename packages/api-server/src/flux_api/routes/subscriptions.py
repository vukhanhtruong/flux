"""Subscription REST routes — thin adapters over use cases."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, status

from flux_api.deps import get_db, get_uow
from flux_core.models.subscription import BillingCycle, SubscriptionOut
from flux_core.sqlite.subscription_repo import SqliteSubscriptionRepository
from flux_core.use_cases.subscriptions.create_subscription import CreateSubscription
from flux_core.use_cases.subscriptions.delete_subscription import DeleteSubscription
from flux_core.use_cases.subscriptions.list_subscriptions import ListSubscriptions
from flux_core.use_cases.subscriptions.toggle_subscription import ToggleSubscription

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    user_id: str,
    name: str,
    amount: float,
    billing_cycle: str,
    next_date: str,
    category: str,
) -> SubscriptionOut:
    """Create a recurring subscription."""
    uc = CreateSubscription(get_uow())
    return await uc.execute(
        user_id, name, Decimal(str(amount)),
        BillingCycle(billing_cycle), date.fromisoformat(next_date), category,
    )


@router.get("/")
async def list_subscriptions(
    user_id: str,
    active_only: bool = True,
) -> list[SubscriptionOut]:
    """List all subscriptions for a user."""
    db = get_db()
    repo = SqliteSubscriptionRepository(db.connection())
    uc = ListSubscriptions(repo)
    return await uc.execute(user_id, active_only=active_only)


@router.post("/{subscription_id}/toggle")
async def toggle_subscription(
    subscription_id: str,
    user_id: str,
) -> SubscriptionOut:
    """Toggle a subscription active/inactive."""
    uc = ToggleSubscription(get_uow())
    return await uc.execute(UUID(subscription_id), user_id)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: str,
    user_id: str,
) -> None:
    """Delete a subscription."""
    uc = DeleteSubscription(get_uow())
    await uc.execute(UUID(subscription_id), user_id)
