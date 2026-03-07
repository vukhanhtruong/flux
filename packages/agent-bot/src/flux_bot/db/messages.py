"""Async wrapper for bot_messages — delegates to core SQLite repo."""

from flux_core.sqlite.bot.message_repo import SqliteBotMessageRepository
from flux_core.sqlite.database import Database


class MessageRepository:
    def __init__(self, db: Database):
        self._db = db

    def _repo(self) -> SqliteBotMessageRepository:
        return SqliteBotMessageRepository(self._db.connection())

    async def insert(
        self,
        user_id: str,
        channel: str,
        platform_id: str,
        text: str | None = None,
        image_path: str | None = None,
    ) -> int:
        """Insert a new pending message and return its ID."""
        msg_id = self._repo().insert(user_id, channel, platform_id, text, image_path)
        self._db.connection().commit()
        return msg_id

    async def fetch_pending(self) -> list[dict]:
        """Fetch all pending messages ordered by creation time."""
        return self._repo().fetch_pending()

    async def mark_processing(self, msg_id: int) -> None:
        """Mark a message as being processed."""
        self._repo().mark_processing(msg_id)
        self._db.connection().commit()

    async def mark_processed(self, msg_id: int) -> None:
        """Mark a message as successfully processed."""
        self._repo().mark_processed(msg_id)
        self._db.connection().commit()

    async def mark_failed(self, msg_id: int, error: str) -> None:
        """Mark a message as failed with an error."""
        self._repo().mark_failed(msg_id, error)
        self._db.connection().commit()
