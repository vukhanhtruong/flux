"""User profile REST routes — thin adapters over SQLite repos."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from flux_api.deps import get_db, get_uow
from flux_core.sqlite.user_repo import SqliteUserRepository

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
) -> ProfileOut:
    """Fetch profile by user_id."""
    if not user_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")

    db = get_db()
    repo = SqliteUserRepository(db.connection())
    profile = repo.get_by_user_id(user_id)
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
) -> ProfileOut:
    """Update mutable profile preferences."""
    if not user_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")

    if payload.currency is None and payload.timezone is None and payload.locale is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="no fields to update"
        )
    if payload.currency is not None and not payload.currency.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="currency cannot be empty"
        )
    if payload.timezone is not None and not payload.timezone.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="timezone cannot be empty"
        )
    if payload.locale is not None and not payload.locale.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="locale cannot be empty"
        )

    uow = get_uow()
    async with uow:
        repo = SqliteUserRepository(uow.conn)
        try:
            profile = repo.update(
                user_id,
                currency=payload.currency,
                timezone=payload.timezone,
                locale=payload.locale,
            )
        except ValueError as exc:
            msg = str(exc)
            if "already taken" in msg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail=msg
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=msg
            ) from exc
        await uow.commit()

    return ProfileOut(
        user_id=profile.user_id,
        username=profile.username,
        channel=profile.channel,
        platform_id=profile.platform_id,
        currency=profile.currency,
        timezone=profile.timezone,
        locale=profile.locale,
    )
