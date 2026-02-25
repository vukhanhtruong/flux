from datetime import date
from typing import Optional
from uuid import UUID

from flux_core.db.connection import Database
from flux_core.models.transaction import TransactionCreate, TransactionOut, TransactionUpdate


class TransactionRepository:
    """Data access layer for transactions."""

    def __init__(self, db: Database):
        self._db = db

    async def create(self, txn: TransactionCreate, embedding: Optional[list[float]] = None) -> TransactionOut:
        row = await self._db.fetchrow(
            """
            INSERT INTO transactions (user_id, date, amount, category, description, type, is_recurring, tags, embedding)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::vector)
            RETURNING id, user_id, date, amount, category, description, type, is_recurring, tags, created_at
            """,
            txn.user_id, txn.date, txn.amount, txn.category, txn.description,
            txn.type.value, txn.is_recurring, txn.tags,
            str(embedding) if embedding is not None else None,
        )
        return TransactionOut(**dict(row))

    async def get_by_id(self, txn_id: UUID, user_id: str) -> Optional[TransactionOut]:
        row = await self._db.fetchrow(
            """
            SELECT id, user_id, date, amount, category, description, type, is_recurring, tags, created_at
            FROM transactions WHERE id = $1 AND user_id = $2
            """,
            txn_id, user_id,
        )
        return TransactionOut(**dict(row)) if row else None

    async def list_by_user(
        self,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        categories: Optional[list[str]] = None,
        txn_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TransactionOut]:
        conditions = ["user_id = $1"]
        params: list = [user_id]
        idx = 2

        if start_date:
            conditions.append(f"date >= ${idx}")
            params.append(start_date)
            idx += 1
        if end_date:
            conditions.append(f"date <= ${idx}")
            params.append(end_date)
            idx += 1
        if categories:
            conditions.append(f"category = ANY(${idx})")
            params.append(categories)
            idx += 1
        if txn_type:
            conditions.append(f"type = ${idx}")
            params.append(txn_type)
            idx += 1

        where = " AND ".join(conditions)
        params.extend([limit, offset])
        rows = await self._db.fetch(
            f"""
            SELECT id, user_id, date, amount, category, description, type, is_recurring, tags, created_at
            FROM transactions WHERE {where}
            ORDER BY date DESC, created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params,
        )
        return [TransactionOut(**dict(r)) for r in rows]

    async def update(self, txn_id: UUID, user_id: str, updates: TransactionUpdate) -> Optional[TransactionOut]:
        fields = updates.model_dump(exclude_none=True)
        if not fields:
            return await self.get_by_id(txn_id, user_id)

        set_clauses = []
        params = []
        idx = 1
        for key, value in fields.items():
            if key == "type":
                value = value.value
            set_clauses.append(f"{key} = ${idx}")
            params.append(value)
            idx += 1

        set_clauses.append(f"updated_at = NOW()")
        params.extend([txn_id, user_id])

        row = await self._db.fetchrow(
            f"""
            UPDATE transactions SET {', '.join(set_clauses)}
            WHERE id = ${idx} AND user_id = ${idx + 1}
            RETURNING id, user_id, date, amount, category, description, type, is_recurring, tags, created_at
            """,
            *params,
        )
        return TransactionOut(**dict(row)) if row else None

    async def delete(self, txn_id: UUID, user_id: str) -> bool:
        result = await self._db.execute(
            "DELETE FROM transactions WHERE id = $1 AND user_id = $2",
            txn_id, user_id,
        )
        return result == "DELETE 1"

    async def search_by_embedding(
        self, user_id: str, embedding: list[float], limit: int = 10
    ) -> list[TransactionOut]:
        rows = await self._db.fetch(
            """
            SELECT id, user_id, date, amount, category, description, type, is_recurring, tags, created_at
            FROM transactions
            WHERE user_id = $1 AND embedding IS NOT NULL
            ORDER BY embedding <=> $2::vector
            LIMIT $3
            """,
            user_id, str(embedding), limit,
        )
        return [TransactionOut(**dict(r)) for r in rows]

    async def get_summary(
        self, user_id: str, start_date: date, end_date: date
    ) -> dict:
        row = await self._db.fetchrow(
            """
            SELECT
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS total_expenses,
                COUNT(*) AS count
            FROM transactions
            WHERE user_id = $1 AND date >= $2 AND date <= $3
            """,
            user_id, start_date, end_date,
        )
        return dict(row)

    async def get_category_breakdown(
        self, user_id: str, start_date: date, end_date: date
    ) -> list[dict]:
        rows = await self._db.fetch(
            """
            SELECT category, SUM(amount) AS total, COUNT(*) AS count
            FROM transactions
            WHERE user_id = $1 AND date >= $2 AND date <= $3 AND type = 'expense'
            GROUP BY category
            ORDER BY total DESC
            """,
            user_id, start_date, end_date,
        )
        return [dict(r) for r in rows]
