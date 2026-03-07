"""SubscriptionRepository Protocol — interface for subscription data access."""

from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from flux_core.models.subscription import SubscriptionCreate, SubscriptionOut


class SubscriptionRepository(Protocol):
    """Repository interface for subscriptions."""

    def create(self, sub: SubscriptionCreate) -> SubscriptionOut: ...

    def get(self, sub_id: UUID, user_id: str) -> SubscriptionOut | None: ...

    def list_by_user(self, user_id: str, active_only: bool = True) -> list[SubscriptionOut]: ...

    def get_due(self, user_id: str, as_of: date) -> list[SubscriptionOut]: ...

    def advance_next_date(self, sub_id: UUID, user_id: str) -> SubscriptionOut | None: ...

    def toggle_active(self, sub_id: UUID, user_id: str) -> SubscriptionOut | None: ...

    def delete(self, sub_id: UUID, user_id: str) -> bool: ...
