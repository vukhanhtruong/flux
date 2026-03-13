"""SQLite implementation of BotMessageRepository Protocol."""
from __future__ import annotations

import sqlite3

from flux_core.models.bot_enums import MessageStatus


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
            WHERE status = ?
            ORDER BY created_at
            LIMIT ?
            """,
            (MessageStatus.pending, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_processing(self, msg_id: int) -> None:
        self._conn.execute(
            "UPDATE bot_messages SET status = ? WHERE id = ?",
            (MessageStatus.processing, msg_id),
        )

    def mark_processed(self, msg_id: int) -> None:
        self._conn.execute(
            "UPDATE bot_messages SET status = ?, processed_at = datetime('now') "
            "WHERE id = ?",
            (MessageStatus.processed, msg_id),
        )

    def mark_failed(self, msg_id: int, error: str) -> None:
        self._conn.execute(
            "UPDATE bot_messages SET status = ?, error = ?, "
            "processed_at = datetime('now') WHERE id = ?",
            (MessageStatus.failed, error, msg_id),
        )
