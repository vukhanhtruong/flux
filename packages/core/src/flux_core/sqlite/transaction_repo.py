"""SQLite implementation of TransactionRepository Protocol."""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from flux_core.models.transaction import (
    TransactionCreate,
    TransactionOut,
    TransactionType,
    TransactionUpdate,
)


class SqliteTransactionRepository:
    """SQLite-backed transaction repository."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(self, txn: TransactionCreate) -> TransactionOut:
        txn_id = str(uuid4())
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        self._conn.execute(
            """
            INSERT INTO transactions
                (id, user_id, date, amount, category, description, type,
                 is_recurring, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                txn_id,
                txn.user_id,
                txn.date.isoformat(),
                str(txn.amount),
                txn.category,
                txn.description,
                txn.type.value,
                1 if txn.is_recurring else 0,
                json.dumps(txn.tags),
                now,
                now,
            ),
        )
        return TransactionOut(
            id=UUID(txn_id),
            user_id=txn.user_id,
            date=txn.date,
            amount=txn.amount,
            category=txn.category,
            description=txn.description,
            type=txn.type,
            is_recurring=txn.is_recurring,
            tags=txn.tags,
            created_at=datetime.fromisoformat(now),
        )

    def get_by_id(self, txn_id: UUID, user_id: str) -> TransactionOut | None:
        row = self._conn.execute(
            "SELECT id, user_id, date, amount, category, description, type, "
            "is_recurring, tags, created_at "
            "FROM transactions WHERE id = ? AND user_id = ?",
            (str(txn_id), user_id),
        ).fetchone()
        return self._from_row(row) if row else None

    def get_by_ids(self, ids: list[UUID]) -> list[TransactionOut]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"SELECT id, user_id, date, amount, category, description, type, "
            f"is_recurring, tags, created_at "
            f"FROM transactions WHERE id IN ({placeholders})",
            tuple(str(i) for i in ids),
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def list_by_user(
        self,
        user_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        categories: list[str] | None = None,
        txn_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TransactionOut]:
        conditions = ["user_id = ?"]
        params: list = [user_id]

        if start_date:
            conditions.append("date >= ?")
            params.append(start_date.isoformat())
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date.isoformat())
        if categories:
            placeholders = ",".join("?" for _ in categories)
            conditions.append(f"category IN ({placeholders})")
            params.extend(categories)
        if txn_type:
            conditions.append("type = ?")
            params.append(txn_type)

        where = " AND ".join(conditions)
        params.extend([limit, offset])
        rows = self._conn.execute(
            f"SELECT id, user_id, date, amount, category, description, type, "
            f"is_recurring, tags, created_at "
            f"FROM transactions WHERE {where} "
            f"ORDER BY date DESC, created_at DESC "
            f"LIMIT ? OFFSET ?",
            tuple(params),
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def update(
        self, txn_id: UUID, user_id: str, updates: TransactionUpdate
    ) -> TransactionOut | None:
        fields = updates.model_dump(exclude_none=True)
        if not fields:
            return self.get_by_id(txn_id, user_id)

        set_clauses = []
        params: list = []
        for key, value in fields.items():
            if key == "type":
                value = value.value
            elif key == "tags":
                value = json.dumps(value)
            elif key == "date":
                value = value.isoformat()
            elif key == "amount":
                value = str(value)
            set_clauses.append(f"{key} = ?")
            params.append(value)

        set_clauses.append("updated_at = datetime('now')")
        params.extend([str(txn_id), user_id])

        row = self._conn.execute(
            f"UPDATE transactions SET {', '.join(set_clauses)} "
            f"WHERE id = ? AND user_id = ? "
            f"RETURNING id, user_id, date, amount, category, description, type, "
            f"is_recurring, tags, created_at",
            tuple(params),
        ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def delete(self, txn_id: UUID, user_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM transactions WHERE id = ? AND user_id = ?",
            (str(txn_id), user_id),
        )
        return cursor.rowcount == 1

    def get_summary(self, user_id: str, start_date: date, end_date: date) -> dict:
        row = self._conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN type = 'income' THEN CAST(amount AS REAL) ELSE 0 END), 0)
                    AS total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN CAST(amount AS REAL) ELSE 0 END), 0)
                    AS total_expenses,
                COUNT(*) AS count
            FROM transactions
            WHERE user_id = ? AND date >= ? AND date <= ?
            """,
            (user_id, start_date.isoformat(), end_date.isoformat()),
        ).fetchone()
        d = dict(row)
        d["total_income"] = Decimal(str(d["total_income"]))
        d["total_expenses"] = Decimal(str(d["total_expenses"]))
        return d

    def get_category_breakdown(
        self, user_id: str, start_date: date, end_date: date
    ) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT category,
                   SUM(CAST(amount AS REAL)) AS total,
                   COUNT(*) AS count
            FROM transactions
            WHERE user_id = ? AND date >= ? AND date <= ? AND type = 'expense'
            GROUP BY category
            ORDER BY total DESC
            """,
            (user_id, start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["total"] = Decimal(str(d["total"]))
            result.append(d)
        return result

    @staticmethod
    def _from_row(row: sqlite3.Row) -> TransactionOut:
        return TransactionOut(
            id=UUID(row["id"]),
            user_id=row["user_id"],
            date=date.fromisoformat(row["date"]),
            amount=Decimal(row["amount"]),
            category=row["category"],
            description=row["description"],
            type=TransactionType(row["type"]),
            is_recurring=bool(row["is_recurring"]),
            tags=json.loads(row["tags"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
