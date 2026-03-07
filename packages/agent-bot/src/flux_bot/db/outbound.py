"""Async wrapper for bot_outbound_messages — delegates to core SQLite repo."""

from flux_core.sqlite.bot.outbound_repo import SqliteBotOutboundRepository
from flux_core.sqlite.database import Database


class OutboundRepository:
    def __init__(self, db: Database):
        self._db = db

    def _repo(self) -> SqliteBotOutboundRepository:
        return SqliteBotOutboundRepository(self._db.connection())

    async def insert(
        self,
        user_id: str,
        text: str,
        sender: str | None = None,
    ) -> int:
        """Insert a pending outbound message and return its ID."""
        msg_id = self._repo().insert(user_id, text, sender)
        self._db.connection().commit()
        return msg_id

    async def fetch_pending(self) -> list[dict]:
        """Fetch all pending outbound messages ordered by creation time."""
        return self._repo().fetch_pending()

    async def mark_sent(self, msg_id: int) -> None:
        """Mark an outbound message as sent."""
        self._repo().mark_sent(msg_id)
        self._db.connection().commit()

    async def mark_failed(self, msg_id: int, error: str) -> None:
        """Mark an outbound message as failed."""
        self._repo().mark_failed(msg_id, error)
        self._db.connection().commit()
