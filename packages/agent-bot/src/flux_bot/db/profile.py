"""Async wrapper for user profile — delegates to core SQLite UserRepository.

Drop-in replacement for the old asyncpg-based flux_core.db.user_profile_repo.UserProfileRepository.
"""

from flux_core.models.user_profile import UserProfile, UserProfileCreate
from flux_core.sqlite.database import Database
from flux_core.sqlite.user_repo import SqliteUserRepository


class ProfileRepository:
    """Async-compatible profile repository backed by SQLite."""

    def __init__(self, db: Database):
        self._db = db

    def _repo(self) -> SqliteUserRepository:
        return SqliteUserRepository(self._db.connection())

    async def create(self, create: UserProfileCreate) -> UserProfile:
        result = self._repo().create_profile(create)
        self._db.connection().commit()
        return result

    async def get_by_user_id(self, user_id: str) -> UserProfile | None:
        return self._repo().get_by_user_id(user_id)

    async def get_by_platform_id(self, channel: str, platform_id: str) -> UserProfile | None:
        return self._repo().get_by_platform_id(channel, platform_id)

    async def username_exists(self, channel: str, username: str) -> bool:
        return self._repo().username_exists(channel, username)

    async def update(
        self,
        user_id: str,
        *,
        currency: str | None = None,
        timezone: str | None = None,
        locale: str | None = None,
        username: str | None = None,
    ) -> UserProfile:
        result = self._repo().update(
            user_id,
            currency=currency,
            timezone=timezone,
            locale=locale,
            username=username,
        )
        self._db.connection().commit()
        return result
