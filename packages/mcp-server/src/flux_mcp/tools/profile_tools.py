from typing import Callable, Awaitable

from fastmcp import FastMCP
from flux_core.db.connection import Database
from flux_core.db.user_profile_repo import UserProfileRepository


def register_profile_tools(
    mcp: FastMCP,
    get_db: Callable[[], Awaitable[Database]],
    get_user_id: Callable[[], str],
):
    @mcp.tool()
    async def update_preferences(
        currency: str | None = None,
        timezone: str | None = None,
        username: str | None = None,
    ) -> dict:
        """Update your preferences: currency, timezone, and/or username.
        Omit any field to leave it unchanged.
        If all fields are omitted, returns your current preferences without making any changes.
        Changing username assigns a new user_id; past records are unaffected.
        """
        db = await get_db()
        repo = UserProfileRepository(db)
        user_id = get_user_id()

        if currency is None and timezone is None and username is None:
            profile = await repo.get_by_user_id(user_id)
            if profile is None:
                return {"error": "profile not found"}
            return {
                "currency": profile.currency,
                "timezone": profile.timezone,
                "username": profile.username,
                "user_id": profile.user_id,
            }

        try:
            profile = await repo.update(
                user_id,
                currency=currency,
                timezone=timezone,
                username=username,
            )
        except ValueError as e:
            return {"error": str(e)}

        return {
            "currency": profile.currency,
            "timezone": profile.timezone,
            "username": profile.username,
            "user_id": profile.user_id,
        }
