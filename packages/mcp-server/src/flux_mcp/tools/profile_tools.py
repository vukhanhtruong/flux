from typing import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastmcp import FastMCP
from flux_core.sqlite.database import Database
from flux_core.sqlite.user_repo import SqliteUserRepository
from flux_core.uow.unit_of_work import UnitOfWork


def register_profile_tools(
    mcp: FastMCP,
    get_db: Callable[[], Database],
    get_uow: Callable[[], UnitOfWork],
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
        db = get_db()
        user_id = get_user_id()
        repo = SqliteUserRepository(db.connection())

        if currency is None and timezone is None and username is None:
            profile = repo.get_by_user_id(user_id)
            if profile is None:
                return {"error": "profile not found"}
            return {
                "currency": profile.currency,
                "timezone": profile.timezone,
                "username": profile.username,
                "user_id": profile.user_id,
            }

        # Validate timezone before writing
        if timezone is not None:
            try:
                ZoneInfo(timezone)
            except (ZoneInfoNotFoundError, KeyError):
                return {"error": f"Invalid timezone: {timezone}"}

        # Write operation — use UoW for transactional safety
        uow = get_uow()
        async with uow:
            uw_repo = SqliteUserRepository(uow.conn)
            try:
                profile = uw_repo.update(
                    user_id,
                    currency=currency,
                    timezone=timezone,
                    username=username,
                )
            except ValueError as e:
                return {"error": str(e)}
            await uow.commit()

        # Invalidate cached timezone if it was updated
        if timezone is not None:
            import flux_mcp.server as _server
            _server._user_timezone = None

        return {
            "currency": profile.currency,
            "timezone": profile.timezone,
            "username": profile.username,
            "user_id": profile.user_id,
        }
