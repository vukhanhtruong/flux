from typing import Optional

from flux_core.db.connection import Database
from flux_core.models.budget import BudgetSet, BudgetOut


class BudgetRepository:
    def __init__(self, db: Database):
        self._db = db

    async def set(self, budget: BudgetSet) -> BudgetOut:
        row = await self._db.fetchrow(
            """
            INSERT INTO budgets (user_id, category, monthly_limit)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, category)
            DO UPDATE SET monthly_limit = EXCLUDED.monthly_limit
            RETURNING id, user_id, category, monthly_limit
            """,
            budget.user_id, budget.category, budget.monthly_limit,
        )
        return BudgetOut(**dict(row))

    async def list_by_user(self, user_id: str) -> list[BudgetOut]:
        rows = await self._db.fetch(
            "SELECT id, user_id, category, monthly_limit FROM budgets WHERE user_id = $1 ORDER BY category",
            user_id,
        )
        return [BudgetOut(**dict(r)) for r in rows]

    async def get_by_category(self, user_id: str, category: str) -> Optional[BudgetOut]:
        row = await self._db.fetchrow(
            "SELECT id, user_id, category, monthly_limit FROM budgets WHERE user_id = $1 AND category = $2",
            user_id, category,
        )
        return BudgetOut(**dict(row)) if row else None

    async def remove(self, user_id: str, category: str) -> bool:
        result = await self._db.execute(
            "DELETE FROM budgets WHERE user_id = $1 AND category = $2",
            user_id, category,
        )
        return result == "DELETE 1"
