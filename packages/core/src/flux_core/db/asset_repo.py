from datetime import date
from typing import Optional
from uuid import UUID

from flux_core.db.connection import Database
from flux_core.models.asset import AssetCreate, AssetOut


class AssetRepository:
    def __init__(self, db: Database):
        self._db = db

    _COLUMNS = "id, user_id, name, amount, interest_rate, frequency, next_date, category, active"

    async def create(self, asset: AssetCreate) -> AssetOut:
        row = await self._db.fetchrow(
            f"""
            INSERT INTO assets (user_id, name, amount, interest_rate, frequency, next_date, category)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING {self._COLUMNS}
            """,
            asset.user_id, asset.name, asset.amount, asset.interest_rate,
            asset.frequency.value, asset.next_date, asset.category,
        )
        return AssetOut(**dict(row))

    async def list_by_user(self, user_id: str, active_only: bool = True) -> list[AssetOut]:
        condition = "user_id = $1"
        if active_only:
            condition += " AND active = TRUE"
        rows = await self._db.fetch(
            f"SELECT {self._COLUMNS} FROM assets WHERE {condition} ORDER BY next_date",
            user_id,
        )
        return [AssetOut(**dict(r)) for r in rows]

    async def get_due(self, user_id: str, as_of: date) -> list[AssetOut]:
        rows = await self._db.fetch(
            f"""
            SELECT {self._COLUMNS} FROM assets
            WHERE user_id = $1 AND active = TRUE AND next_date <= $2
            ORDER BY next_date
            """,
            user_id, as_of,
        )
        return [AssetOut(**dict(r)) for r in rows]

    async def advance_next_date(self, asset_id: UUID, user_id: str) -> Optional[AssetOut]:
        row = await self._db.fetchrow(
            f"""
            UPDATE assets SET next_date = CASE
                WHEN frequency = 'monthly' THEN next_date + INTERVAL '1 month'
                WHEN frequency = 'yearly' THEN next_date + INTERVAL '1 year'
            END
            WHERE id = $1 AND user_id = $2
            RETURNING {self._COLUMNS}
            """,
            asset_id, user_id,
        )
        return AssetOut(**dict(row)) if row else None

    async def delete(self, asset_id: UUID, user_id: str) -> bool:
        result = await self._db.execute(
            "DELETE FROM assets WHERE id = $1 AND user_id = $2", asset_id, user_id,
        )
        return result == "DELETE 1"
