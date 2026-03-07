"""SQLite implementation of BudgetRepository Protocol."""
from __future__ import annotations

import sqlite3
from decimal import Decimal
from uuid import UUID, uuid4

from flux_core.models.budget import BudgetOut, BudgetSet


class SqliteBudgetRepository:
    """SQLite-backed budget repository."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def set(self, budget: BudgetSet) -> BudgetOut:
        budget_id = str(uuid4())
        self._conn.execute(
            """
            INSERT INTO budgets (id, user_id, category, monthly_limit)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (user_id, category)
            DO UPDATE SET monthly_limit = excluded.monthly_limit
            """,
            (budget_id, budget.user_id, budget.category, str(budget.monthly_limit)),
        )
        row = self._conn.execute(
            "SELECT id, user_id, category, monthly_limit FROM budgets "
            "WHERE user_id = ? AND category = ?",
            (budget.user_id, budget.category),
        ).fetchone()
        return self._from_row(row)

    def list_by_user(self, user_id: str) -> list[BudgetOut]:
        rows = self._conn.execute(
            "SELECT id, user_id, category, monthly_limit FROM budgets "
            "WHERE user_id = ? ORDER BY category",
            (user_id,),
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def get_by_category(self, user_id: str, category: str) -> BudgetOut | None:
        row = self._conn.execute(
            "SELECT id, user_id, category, monthly_limit FROM budgets "
            "WHERE user_id = ? AND category = ?",
            (user_id, category),
        ).fetchone()
        return self._from_row(row) if row else None

    def remove(self, user_id: str, category: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM budgets WHERE user_id = ? AND category = ?",
            (user_id, category),
        )
        return cursor.rowcount == 1

    @staticmethod
    def _from_row(row: sqlite3.Row) -> BudgetOut:
        return BudgetOut(
            id=UUID(row["id"]),
            user_id=row["user_id"],
            category=row["category"],
            monthly_limit=Decimal(row["monthly_limit"]),
        )
