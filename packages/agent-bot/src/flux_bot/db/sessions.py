"""Repository for bot_sessions table."""

import asyncpg


class SessionRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_session_id(self, user_id: str) -> str | None:
        """Get the Claude CLI session ID for a user, or None if no session."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT session_id FROM bot_sessions WHERE user_id = $1",
                user_id,
            )

    async def upsert(self, user_id: str, session_id: str) -> None:
        """Insert or update the session ID for a user."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO bot_sessions (user_id, session_id, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id) DO UPDATE SET session_id = $2, updated_at = NOW()
                """,
                user_id, session_id,
            )

    async def delete(self, user_id: str) -> None:
        """Delete the session for a user, forcing a fresh session on next run."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM bot_sessions WHERE user_id = $1",
                user_id,
            )
