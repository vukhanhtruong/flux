"""Asset REST routes."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from flux_api.deps import get_db
from flux_core.db.connection import Database
from flux_core.db.asset_repo import AssetRepository
from flux_core.models.asset import AssetCreate, AssetOut

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset: AssetCreate,
    db: Annotated[Database, Depends(get_db)],
) -> AssetOut:
    """Create an asset entry."""
    repo = AssetRepository(db)
    created = await repo.create(asset)
    return created


@router.get("/")
async def list_assets(
    user_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> list[AssetOut]:
    """List all assets for a user."""
    repo = AssetRepository(db)
    assets = await repo.list_by_user(user_id)
    return assets


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: str,
    user_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> None:
    """Delete an asset."""
    repo = AssetRepository(db)
    await repo.delete(UUID(asset_id), user_id)
