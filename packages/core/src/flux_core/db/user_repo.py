from flux_core.db.connection import Database


class UserRepository:
    """Data access layer for users."""

    def __init__(self, db: Database):
        self._db = db

    async def ensure_exists(self, user_id: str, display_name: str | None = None) -> None:
        """Insert user if not exists (idempotent via ON CONFLICT DO NOTHING)."""
        platform = user_id.split(":")[0] if ":" in user_id else "unknown"
        await self._db.execute(
            "INSERT INTO users (id, display_name, platform) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
            user_id,
            display_name or user_id,
            platform,
        )
