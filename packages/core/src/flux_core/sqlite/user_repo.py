"""SQLite implementation of UserRepository Protocol."""
from __future__ import annotations

import sqlite3

from flux_core.models.user_profile import UserProfile, UserProfileCreate, _CHANNEL_PREFIXES


class SqliteUserRepository:
    """SQLite-backed user repository (merged user + profile)."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def ensure_exists(self, user_id: str, display_name: str | None = None) -> None:
        """Insert user if not exists (idempotent via ON CONFLICT DO NOTHING)."""
        platform = user_id.split(":")[0] if ":" in user_id else "unknown"
        self._conn.execute(
            "INSERT OR IGNORE INTO users (id, display_name, platform) VALUES (?, ?, ?)",
            (user_id, display_name or user_id, platform),
        )

    def create_profile(self, create: UserProfileCreate) -> UserProfile:
        """Create a full user profile."""
        prefix = _CHANNEL_PREFIXES.get(create.channel, create.channel)
        user_id = f"{prefix}:{create.platform_id}"
        self._conn.execute(
            """
            INSERT INTO users
                (id, display_name, platform, username, currency, timezone, locale, platform_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                create.username,
                create.channel,
                create.username,
                create.currency,
                create.timezone,
                create.locale,
                create.platform_id,
            ),
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

    def get_by_user_id(self, user_id: str) -> UserProfile | None:
        row = self._conn.execute(
            "SELECT id, username, platform, platform_id, currency, timezone, locale "
            "FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return self._from_row(row)

    def get_by_platform_id(self, channel: str, platform_id: str) -> UserProfile | None:
        row = self._conn.execute(
            "SELECT id, username, platform, platform_id, currency, timezone, locale "
            "FROM users WHERE platform = ? AND platform_id = ?",
            (channel, platform_id),
        ).fetchone()
        if not row:
            return None
        return self._from_row(row)

    def username_exists(self, channel: str, username: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM users WHERE platform = ? AND username = ?",
            (channel, username),
        ).fetchone()
        return row is not None

    def update(
        self,
        user_id: str,
        *,
        currency: str | None = None,
        timezone: str | None = None,
        locale: str | None = None,
        username: str | None = None,
    ) -> UserProfile:
        sets: list[str] = ["updated_at = datetime('now')"]
        params: list = []

        if currency is not None:
            sets.append("currency = ?")
            params.append(currency)
        if timezone is not None:
            sets.append("timezone = ?")
            params.append(timezone)
        if locale is not None:
            sets.append("locale = ?")
            params.append(locale)
        if username is not None:
            sets.append("username = ?")
            params.append(username)
            sets.append("display_name = ?")
            params.append(username)

        params.append(user_id)
        set_clause = ", ".join(sets)

        try:
            row = self._conn.execute(
                f"UPDATE users SET {set_clause} WHERE id = ? "
                "RETURNING id, username, platform, platform_id, currency, timezone, locale",
                tuple(params),
            ).fetchone()
        except sqlite3.IntegrityError:
            raise ValueError("username already taken")

        if row is None:
            raise ValueError(f"user {user_id!r} not found")

        return self._from_row(row)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> UserProfile:
        return UserProfile(
            user_id=row["id"],
            username=row["username"],
            channel=row["platform"],
            platform_id=row["platform_id"],
            currency=row["currency"],
            timezone=row["timezone"],
            locale=row["locale"],
        )
