"""SQLite implementation of SubscriptionRepository Protocol."""
from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from flux_core.models.subscription import BillingCycle, SubscriptionCreate, SubscriptionOut

_COLUMNS = "id, user_id, name, amount, billing_cycle, next_date, category, active"


class SqliteSubscriptionRepository:
    """SQLite-backed subscription repository."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(self, sub: SubscriptionCreate) -> SubscriptionOut:
        sub_id = str(uuid4())
        self._conn.execute(
            """
            INSERT INTO subscriptions (id, user_id, name, amount, billing_cycle, next_date, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sub_id,
                sub.user_id,
                sub.name,
                str(sub.amount),
                sub.billing_cycle.value,
                sub.next_date.isoformat(),
                sub.category,
            ),
        )
        return SubscriptionOut(
            id=UUID(sub_id),
            user_id=sub.user_id,
            name=sub.name,
            amount=sub.amount,
            billing_cycle=sub.billing_cycle,
            next_date=sub.next_date,
            category=sub.category,
            active=True,
        )

    def get(self, sub_id: UUID, user_id: str) -> SubscriptionOut | None:
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM subscriptions WHERE id = ? AND user_id = ?",
            (str(sub_id), user_id),
        ).fetchone()
        return self._from_row(row) if row else None

    def list_by_user(
        self, user_id: str, active_only: bool = True
    ) -> list[SubscriptionOut]:
        condition = "user_id = ?"
        if active_only:
            condition += " AND active = 1"
        rows = self._conn.execute(
            f"SELECT {_COLUMNS} FROM subscriptions WHERE {condition} ORDER BY next_date",
            (user_id,),
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def get_due(self, user_id: str, as_of: date) -> list[SubscriptionOut]:
        rows = self._conn.execute(
            f"SELECT {_COLUMNS} FROM subscriptions "
            f"WHERE user_id = ? AND active = 1 AND next_date <= ? "
            f"ORDER BY next_date",
            (user_id, as_of.isoformat()),
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def advance_next_date(
        self, sub_id: UUID, user_id: str
    ) -> SubscriptionOut | None:
        row = self._conn.execute(
            f"""
            UPDATE subscriptions SET next_date = CASE
                WHEN billing_cycle = 'monthly'
                    THEN date(next_date, '+1 month')
                WHEN billing_cycle = 'yearly'
                    THEN date(next_date, '+1 year')
            END
            WHERE id = ? AND user_id = ?
            RETURNING {_COLUMNS}
            """,
            (str(sub_id), user_id),
        ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def toggle_active(self, sub_id: UUID, user_id: str) -> SubscriptionOut | None:
        row = self._conn.execute(
            "UPDATE subscriptions SET active = 1 - active WHERE id = ? AND user_id = ? "
            f"RETURNING {_COLUMNS}",
            (str(sub_id), user_id),
        ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def delete(self, sub_id: UUID, user_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM subscriptions WHERE id = ? AND user_id = ?",
            (str(sub_id), user_id),
        )
        return cursor.rowcount == 1

    @staticmethod
    def _from_row(row: sqlite3.Row) -> SubscriptionOut:
        return SubscriptionOut(
            id=UUID(row["id"]),
            user_id=row["user_id"],
            name=row["name"],
            amount=Decimal(row["amount"]),
            billing_cycle=BillingCycle(row["billing_cycle"]),
            next_date=date.fromisoformat(row["next_date"]),
            category=row["category"],
            active=bool(row["active"]),
        )
