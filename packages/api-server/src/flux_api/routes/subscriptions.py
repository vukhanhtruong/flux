"""Subscription REST routes."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from flux_api.deps import get_db
from flux_core.db.connection import Database
from flux_core.db.subscription_repo import SubscriptionRepository
from flux_core.models.subscription import SubscriptionCreate, SubscriptionOut

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription: SubscriptionCreate,
    db: Annotated[Database, Depends(get_db)],
) -> SubscriptionOut:
    """Create a recurring subscription."""
    repo = SubscriptionRepository(db)
    created = await repo.create(subscription)
    return created


@router.get("/")
async def list_subscriptions(
    user_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> list[SubscriptionOut]:
    """List all subscriptions for a user."""
    repo = SubscriptionRepository(db)
    subscriptions = await repo.list_by_user(user_id)
    return subscriptions


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: str,
    user_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> None:
    """Delete a subscription."""
    repo = SubscriptionRepository(db)
    await repo.delete(UUID(subscription_id), user_id)
