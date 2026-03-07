"""ListSubscriptions use case — read-only."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.models.subscription import SubscriptionOut
    from flux_core.repositories.subscription_repo import SubscriptionRepository


class ListSubscriptions:
    """List subscriptions for a user (read-only)."""

    def __init__(self, sub_repo: SubscriptionRepository):
        self._sub_repo = sub_repo

    async def execute(
        self, user_id: str, *, active_only: bool = True
    ) -> list[SubscriptionOut]:
        return self._sub_repo.list_by_user(user_id, active_only)
