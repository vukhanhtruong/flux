"""ListGoals use case — read-only."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.models.goal import GoalOut
    from flux_core.repositories.goal_repo import GoalRepository


class ListGoals:
    """List all savings goals for a user (read-only)."""

    def __init__(self, goal_repo: GoalRepository):
        self._goal_repo = goal_repo

    async def execute(self, user_id: str) -> list[GoalOut]:
        return self._goal_repo.list_by_user(user_id)
