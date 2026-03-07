"""GoalRepository Protocol — interface for savings goal data access."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from flux_core.models.goal import GoalCreate, GoalOut, GoalUpdate


class GoalRepository(Protocol):
    """Repository interface for savings goals."""

    def create(self, goal: GoalCreate) -> GoalOut: ...

    def get_by_id(self, goal_id: UUID, user_id: str) -> GoalOut | None: ...

    def list_by_user(self, user_id: str) -> list[GoalOut]: ...

    def update(self, goal_id: UUID, user_id: str, updates: GoalUpdate) -> GoalOut | None: ...

    def deposit(self, goal_id: UUID, user_id: str, amount: Decimal) -> GoalOut | None: ...

    def withdraw(self, goal_id: UUID, user_id: str, amount: Decimal) -> GoalOut | None: ...

    def delete(self, goal_id: UUID, user_id: str) -> bool: ...
