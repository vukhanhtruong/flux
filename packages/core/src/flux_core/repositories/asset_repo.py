"""AssetRepository Protocol — interface for asset data access."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from flux_core.models.asset import AssetCreate, AssetOut


class AssetRepository(Protocol):
    """Repository interface for assets."""

    def create(self, asset: AssetCreate) -> AssetOut: ...

    def get(self, asset_id: UUID, user_id: str) -> AssetOut | None: ...

    def list_by_user(
        self, user_id: str, active_only: bool = True, asset_type: str | None = None
    ) -> list[AssetOut]: ...

    def get_due(self, user_id: str, as_of: date) -> list[AssetOut]: ...

    def advance_next_date(self, asset_id: UUID, user_id: str) -> AssetOut | None: ...

    def update_amount(self, asset_id: UUID, user_id: str, new_amount: Decimal) -> AssetOut | None:
        ...

    def deactivate(self, asset_id: UUID, user_id: str) -> AssetOut | None: ...

    def delete(self, asset_id: UUID, user_id: str) -> bool: ...
