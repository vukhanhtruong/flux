"""Async wrapper for bot_sessions — delegates to core SQLite repo."""

from flux_core.sqlite.bot.session_repo import SqliteBotSessionRepository
from flux_core.sqlite.database import Database


class SessionRepository:
    def __init__(self, db: Database):
        self._db = db

    def _repo(self) -> SqliteBotSessionRepository:
        return SqliteBotSessionRepository(self._db.connection())

    async def get_session_id(self, user_id: str) -> str | None:
        """Get the Claude CLI session ID for a user, or None if no session."""
        return self._repo().get_session_id(user_id)

    async def upsert(self, user_id: str, session_id: str) -> None:
        """Insert or update the session ID for a user."""
        self._repo().upsert(user_id, session_id)
        self._db.connection().commit()

    async def delete(self, user_id: str) -> None:
        """Delete the session for a user, forcing a fresh session on next run."""
        self._repo().delete(user_id)
        self._db.connection().commit()
