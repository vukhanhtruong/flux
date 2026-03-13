"""SQLite implementation of BotMessageRepository Protocol."""
from __future__ import annotations

import sqlite3


class SqliteBotMessageRepository:
    """SQLite-backed bot message repository."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def insert(
        self,
        user_id: str,
        channel: str,
        platform_id: str,
        text: str | None = None,
        image_path: str | None = None,
    ) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO bot_messages (user_id, channel, platform_id, text, image_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, channel, platform_id, text, image_path),
        )
        return cursor.lastrowid

    def fetch_pending(self, limit: int = 100) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT id, user_id, channel, platform_id, text, image_path, created_at
            FROM bot_messages
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_processing(self, msg_id: int) -> None:
        self._conn.execute(
            "UPDATE bot_messages SET status = 'processing' WHERE id = ?",
            (msg_id,),
        )

    def mark_processed(self, msg_id: int) -> None:
        self._conn.execute(
            "UPDATE bot_messages SET status = 'processed', processed_at = datetime('now') "
            "WHERE id = ?",
            (msg_id,),
        )

    def mark_failed(self, msg_id: int, error: str) -> None:
        self._conn.execute(
            "UPDATE bot_messages SET status = 'failed', error = ?, "
            "processed_at = datetime('now') WHERE id = ?",
            (error, msg_id),
        )
