"""SQLite implementation of AssetRepository Protocol."""
from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from flux_core.models.asset import AssetCreate, AssetFrequency, AssetOut, AssetType

_COLUMNS = (
    "id, user_id, name, amount, interest_rate, frequency, next_date, category, active,"
    " asset_type, principal_amount, compound_frequency, maturity_date, start_date"
)


class SqliteAssetRepository:
    """SQLite-backed asset repository."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(self, asset: AssetCreate) -> AssetOut:
        asset_id = str(uuid4())
        self._conn.execute(
            """
            INSERT INTO assets
                (id, user_id, name, amount, interest_rate, frequency, next_date, category,
                 asset_type, principal_amount, compound_frequency, maturity_date, start_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset_id,
                asset.user_id,
                asset.name,
                str(asset.amount),
                str(asset.interest_rate),
                asset.frequency.value,
                asset.next_date.isoformat(),
                asset.category,
                asset.asset_type.value,
                str(asset.principal_amount) if asset.principal_amount is not None else None,
                asset.compound_frequency,
                asset.maturity_date.isoformat() if asset.maturity_date else None,
                asset.start_date.isoformat() if asset.start_date else None,
            ),
        )
        return AssetOut(
            id=UUID(asset_id),
            user_id=asset.user_id,
            name=asset.name,
            amount=asset.amount,
            interest_rate=asset.interest_rate,
            frequency=asset.frequency,
            next_date=asset.next_date,
            category=asset.category,
            active=True,
            asset_type=asset.asset_type,
            principal_amount=asset.principal_amount,
            compound_frequency=asset.compound_frequency,
            maturity_date=asset.maturity_date,
            start_date=asset.start_date,
        )

    def get(self, asset_id: UUID, user_id: str) -> AssetOut | None:
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM assets WHERE id = ? AND user_id = ?",
            (str(asset_id), user_id),
        ).fetchone()
        return self._from_row(row) if row else None

    def list_by_user(
        self,
        user_id: str,
        active_only: bool = True,
        asset_type: str | None = None,
    ) -> list[AssetOut]:
        condition = "user_id = ?"
        params: list = [user_id]
        if active_only:
            condition += " AND active = 1"
        if asset_type is not None:
            condition += " AND asset_type = ?"
            params.append(asset_type)
        rows = self._conn.execute(
            f"SELECT {_COLUMNS} FROM assets WHERE {condition} ORDER BY next_date",
            tuple(params),
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def get_due(self, user_id: str, as_of: date) -> list[AssetOut]:
        rows = self._conn.execute(
            f"SELECT {_COLUMNS} FROM assets "
            f"WHERE user_id = ? AND active = 1 AND next_date <= ? "
            f"ORDER BY next_date",
            (user_id, as_of.isoformat()),
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def advance_next_date(self, asset_id: UUID, user_id: str) -> AssetOut | None:
        cursor = self._conn.execute(
            """
            UPDATE assets SET next_date = CASE
                WHEN frequency = 'monthly' THEN date(next_date, '+1 month')
                WHEN frequency = 'quarterly' THEN date(next_date, '+3 months')
                WHEN frequency = 'yearly' THEN date(next_date, '+1 year')
            END
            WHERE id = ? AND user_id = ?
            """,
            (str(asset_id), user_id),
        )
        if cursor.rowcount == 0:
            return None
        return self.get(asset_id, user_id)

    def update_amount(
        self, asset_id: UUID, user_id: str, new_amount: Decimal
    ) -> AssetOut | None:
        cursor = self._conn.execute(
            "UPDATE assets SET amount = ? WHERE id = ? AND user_id = ?",
            (str(new_amount), str(asset_id), user_id),
        )
        if cursor.rowcount == 0:
            return None
        return self.get(asset_id, user_id)

    def deactivate(self, asset_id: UUID, user_id: str) -> AssetOut | None:
        cursor = self._conn.execute(
            "UPDATE assets SET active = 0 WHERE id = ? AND user_id = ?",
            (str(asset_id), user_id),
        )
        if cursor.rowcount == 0:
            return None
        return self.get(asset_id, user_id)

    def delete(self, asset_id: UUID, user_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM assets WHERE id = ? AND user_id = ?",
            (str(asset_id), user_id),
        )
        return cursor.rowcount == 1

    @staticmethod
    def _from_row(row: sqlite3.Row) -> AssetOut:
        return AssetOut(
            id=UUID(row["id"]),
            user_id=row["user_id"],
            name=row["name"],
            amount=Decimal(row["amount"]),
            interest_rate=Decimal(row["interest_rate"]),
            frequency=AssetFrequency(row["frequency"]),
            next_date=date.fromisoformat(row["next_date"]),
            category=row["category"],
            active=bool(row["active"]),
            asset_type=AssetType(row["asset_type"]),
            principal_amount=(
                Decimal(row["principal_amount"]) if row["principal_amount"] else None
            ),
            compound_frequency=row["compound_frequency"],
            maturity_date=(
                date.fromisoformat(row["maturity_date"]) if row["maturity_date"] else None
            ),
            start_date=(
                date.fromisoformat(row["start_date"]) if row["start_date"] else None
            ),
        )
