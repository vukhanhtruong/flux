import asyncpg

from flux_core.db.connection import Database
from flux_core.models.user_profile import UserProfile, UserProfileCreate

_CHANNEL_PREFIXES = {"telegram": "tg", "whatsapp": "wa"}


class UserProfileRepository:
    def __init__(self, db: Database):
        self._db = db

    async def create(self, create: UserProfileCreate) -> UserProfile:
        prefix = _CHANNEL_PREFIXES.get(create.channel, create.channel)
        user_id = f"{prefix}:{create.platform_id}"
        await self._db.execute(
            """
            INSERT INTO users (id, display_name, platform, username, currency, timezone, locale, platform_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            user_id, create.username, create.channel,
            create.username, create.currency, create.timezone, create.locale, create.platform_id,
        )
        return UserProfile(
            user_id=user_id,
            username=create.username,
            channel=create.channel,
            platform_id=create.platform_id,
            currency=create.currency,
            timezone=create.timezone,
            locale=create.locale,
        )

    async def get_by_user_id(self, user_id: str) -> UserProfile | None:
        row = await self._db.fetchrow(
            "SELECT id, username, platform, platform_id, currency, timezone, locale FROM users WHERE id = $1",
            user_id,
        )
        if not row:
            return None
        return UserProfile(
            user_id=row["id"],
            username=row["username"],
            channel=row["platform"],
            platform_id=row["platform_id"],
            currency=row["currency"],
            timezone=row["timezone"],
            locale=row["locale"],
        )

    async def get_by_platform_id(self, channel: str, platform_id: str) -> UserProfile | None:
        row = await self._db.fetchrow(
            """
            SELECT id, username, platform, platform_id, currency, timezone, locale
            FROM users WHERE platform = $1 AND platform_id = $2
            """,
            channel, platform_id,
        )
        if not row:
            return None
        return UserProfile(
            user_id=row["id"],
            username=row["username"],
            channel=row["platform"],
            platform_id=row["platform_id"],
            currency=row["currency"],
            timezone=row["timezone"],
            locale=row["locale"],
        )

    async def username_exists(self, channel: str, username: str) -> bool:
        result = await self._db.fetchval(
            "SELECT EXISTS(SELECT 1 FROM users WHERE platform = $1 AND username = $2)",
            channel, username,
        )
        return bool(result)

    async def update(
        self,
        user_id: str,
        *,
        currency: str | None = None,
        timezone: str | None = None,
        locale: str | None = None,
        username: str | None = None,
    ) -> UserProfile:
        """Update mutable profile fields. Renames id when username changes."""

        sets: list[str] = ["updated_at = NOW()"]
        params: list = [user_id]

        if currency is not None:
            params.append(currency)
            sets.append(f"currency = ${len(params)}")
        if timezone is not None:
            params.append(timezone)
            sets.append(f"timezone = ${len(params)}")
        if locale is not None:
            params.append(locale)
            sets.append(f"locale = ${len(params)}")
        if username is not None:
            params.append(username)
            sets.append(f"username = ${len(params)}")
            params.append(username)
            sets.append(f"display_name = ${len(params)}")

        set_clause = ", ".join(sets)
        try:
            row = await self._db.fetchrow(
                f"""
                UPDATE users SET {set_clause}
                WHERE id = $1
                RETURNING id, username, platform, platform_id, currency, timezone, locale
                """,
                *params,
            )
        except asyncpg.UniqueViolationError:
            raise ValueError("username already taken")

        if row is None:
            raise ValueError(f"user {user_id!r} not found")

        return UserProfile(
            user_id=row["id"],
            username=row["username"],
            channel=row["platform"],
            platform_id=row["platform_id"],
            currency=row["currency"],
            timezone=row["timezone"],
            locale=row["locale"],
        )
