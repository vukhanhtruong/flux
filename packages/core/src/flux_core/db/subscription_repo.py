from datetime import date
from typing import Optional
from uuid import UUID

from flux_core.db.connection import Database
from flux_core.models.subscription import SubscriptionCreate, SubscriptionOut


class SubscriptionRepository:
    def __init__(self, db: Database):
        self._db = db

    _COLUMNS = "id, user_id, name, amount, billing_cycle, next_date, category, active"

    async def create(self, sub: SubscriptionCreate) -> SubscriptionOut:
        row = await self._db.fetchrow(
            f"""
            INSERT INTO subscriptions (user_id, name, amount, billing_cycle, next_date, category)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING {self._COLUMNS}
            """,
            sub.user_id, sub.name, sub.amount, sub.billing_cycle.value,
            sub.next_date, sub.category,
        )
        return SubscriptionOut(**dict(row))

    async def list_by_user(self, user_id: str, active_only: bool = True) -> list[SubscriptionOut]:
        condition = "user_id = $1"
        if active_only:
            condition += " AND active = TRUE"
        rows = await self._db.fetch(
            f"SELECT {self._COLUMNS} FROM subscriptions WHERE {condition} ORDER BY next_date",
            user_id,
        )
        return [SubscriptionOut(**dict(r)) for r in rows]

    async def get_due(self, user_id: str, as_of: date) -> list[SubscriptionOut]:
        rows = await self._db.fetch(
            f"""
            SELECT {self._COLUMNS} FROM subscriptions
            WHERE user_id = $1 AND active = TRUE AND next_date <= $2
            ORDER BY next_date
            """,
            user_id, as_of,
        )
        return [SubscriptionOut(**dict(r)) for r in rows]

    async def advance_next_date(self, sub_id: UUID, user_id: str) -> Optional[SubscriptionOut]:
        row = await self._db.fetchrow(
            f"""
            UPDATE subscriptions SET next_date = CASE
                WHEN billing_cycle = 'monthly' THEN next_date + INTERVAL '1 month'
                WHEN billing_cycle = 'yearly' THEN next_date + INTERVAL '1 year'
            END
            WHERE id = $1 AND user_id = $2
            RETURNING {self._COLUMNS}
            """,
            sub_id, user_id,
        )
        return SubscriptionOut(**dict(row)) if row else None

    async def toggle_active(self, sub_id: UUID, user_id: str) -> Optional[SubscriptionOut]:
        row = await self._db.fetchrow(
            f"""
            UPDATE subscriptions SET active = NOT active
            WHERE id = $1 AND user_id = $2
            RETURNING {self._COLUMNS}
            """,
            sub_id, user_id,
        )
        return SubscriptionOut(**dict(row)) if row else None

    async def delete(self, sub_id: UUID, user_id: str) -> bool:
        result = await self._db.execute(
            "DELETE FROM subscriptions WHERE id = $1 AND user_id = $2",
            sub_id, user_id,
        )
        return result == "DELETE 1"
