"""UserRepository Protocol — interface for user data access.

Merges UserRepository and UserProfileRepository from the old codebase.
"""

from __future__ import annotations

from typing import Protocol

from flux_core.models.user_profile import UserProfile, UserProfileCreate


class UserRepository(Protocol):
    """Repository interface for users (merged user + profile)."""

    def ensure_exists(self, user_id: str, display_name: str | None = None) -> None: ...

    def create_profile(self, create: UserProfileCreate) -> UserProfile: ...

    def get_by_user_id(self, user_id: str) -> UserProfile | None: ...

    def get_by_platform_id(self, channel: str, platform_id: str) -> UserProfile | None: ...

    def username_exists(self, channel: str, username: str) -> bool: ...

    def update(
        self,
        user_id: str,
        *,
        currency: str | None = None,
        timezone: str | None = None,
        locale: str | None = None,
        username: str | None = None,
    ) -> UserProfile: ...
