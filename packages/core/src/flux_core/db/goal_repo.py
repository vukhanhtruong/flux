from decimal import Decimal
from typing import Optional
from uuid import UUID

from flux_core.db.connection import Database
from flux_core.models.goal import GoalCreate, GoalOut, GoalUpdate


class GoalRepository:
    def __init__(self, db: Database):
        self._db = db

    async def create(self, goal: GoalCreate) -> GoalOut:
        row = await self._db.fetchrow(
            """
            INSERT INTO savings_goals (user_id, name, target_amount, deadline, color)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, user_id, name, target_amount, current_amount, deadline, color
            """,
            goal.user_id, goal.name, goal.target_amount, goal.deadline, goal.color,
        )
        return GoalOut(**dict(row))

    async def get_by_id(self, goal_id: UUID, user_id: str) -> Optional[GoalOut]:
        row = await self._db.fetchrow(
            """
            SELECT id, user_id, name, target_amount, current_amount, deadline, color
            FROM savings_goals WHERE id = $1 AND user_id = $2
            """,
            goal_id, user_id,
        )
        return GoalOut(**dict(row)) if row else None

    async def list_by_user(self, user_id: str) -> list[GoalOut]:
        rows = await self._db.fetch(
            """
            SELECT id, user_id, name, target_amount, current_amount, deadline, color
            FROM savings_goals WHERE user_id = $1 ORDER BY name
            """,
            user_id,
        )
        return [GoalOut(**dict(r)) for r in rows]

    async def deposit(self, goal_id: UUID, user_id: str, amount: Decimal) -> Optional[GoalOut]:
        row = await self._db.fetchrow(
            """
            UPDATE savings_goals SET current_amount = current_amount + $3
            WHERE id = $1 AND user_id = $2
            RETURNING id, user_id, name, target_amount, current_amount, deadline, color
            """,
            goal_id, user_id, amount,
        )
        return GoalOut(**dict(row)) if row else None

    async def withdraw(self, goal_id: UUID, user_id: str, amount: Decimal) -> Optional[GoalOut]:
        row = await self._db.fetchrow(
            """
            UPDATE savings_goals SET current_amount = GREATEST(current_amount - $3, 0)
            WHERE id = $1 AND user_id = $2
            RETURNING id, user_id, name, target_amount, current_amount, deadline, color
            """,
            goal_id, user_id, amount,
        )
        return GoalOut(**dict(row)) if row else None

    async def delete(self, goal_id: UUID, user_id: str) -> bool:
        result = await self._db.execute(
            "DELETE FROM savings_goals WHERE id = $1 AND user_id = $2",
            goal_id, user_id,
        )
        return result == "DELETE 1"
