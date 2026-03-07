"""Asset REST routes — thin adapters over SQLite repos."""
from uuid import UUID

from fastapi import APIRouter, status

from flux_api.deps import get_db, get_uow
from flux_core.models.asset import AssetOut
from flux_core.sqlite.asset_repo import SqliteAssetRepository

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/")
async def list_assets(
    user_id: str,
    active_only: bool = True,
    asset_type: str | None = None,
) -> list[AssetOut]:
    """List all assets for a user."""
    db = get_db()
    repo = SqliteAssetRepository(db.connection())
    return repo.list_by_user(user_id, active_only, asset_type=asset_type)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: str,
    user_id: str,
) -> None:
    """Delete an asset."""
    uow = get_uow()
    async with uow:
        repo = SqliteAssetRepository(uow.conn)
        repo.delete(UUID(asset_id), user_id)
        await uow.commit()
