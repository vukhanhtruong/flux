"""User profile REST routes."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from flux_api.deps import get_db
from flux_core.db.connection import Database
from flux_core.db.user_profile_repo import UserProfileRepository

router = APIRouter(tags=["profile"])


class ProfileOut(BaseModel):
    user_id: str
    username: str
    channel: str
    platform_id: str
    currency: str
    timezone: str
    locale: str


class ProfileUpdate(BaseModel):
    currency: str | None = None
    timezone: str | None = None
    locale: str | None = None


@router.get("/profile")
async def get_profile(
    user_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> ProfileOut:
    """Fetch profile by user_id."""
    if not user_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")

    repo = UserProfileRepository(db)
    profile = await repo.get_by_user_id(user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not found")

    return ProfileOut(
        user_id=profile.user_id,
        username=profile.username,
        channel=profile.channel,
        platform_id=profile.platform_id,
        currency=profile.currency,
        timezone=profile.timezone,
        locale=profile.locale,
    )


@router.patch("/profile")
async def update_profile(
    user_id: str,
    payload: ProfileUpdate,
    db: Annotated[Database, Depends(get_db)],
) -> ProfileOut:
    """Update mutable profile preferences."""
    if not user_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")

    if payload.currency is None and payload.timezone is None and payload.locale is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no fields to update")
    if payload.currency is not None and not payload.currency.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="currency cannot be empty")
    if payload.timezone is not None and not payload.timezone.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="timezone cannot be empty")
    if payload.locale is not None and not payload.locale.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="locale cannot be empty")

    repo = UserProfileRepository(db)
    try:
        profile = await repo.update(
            user_id,
            currency=payload.currency,
            timezone=payload.timezone,
            locale=payload.locale,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ProfileOut(
        user_id=profile.user_id,
        username=profile.username,
        channel=profile.channel,
        platform_id=profile.platform_id,
        currency=profile.currency,
        timezone=profile.timezone,
        locale=profile.locale,
    )
