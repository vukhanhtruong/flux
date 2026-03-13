"""SQLite implementation of BotOutboundRepository Protocol."""
from __future__ import annotations

import sqlite3


class SqliteBotOutboundRepository:
    """SQLite-backed bot outbound message repository."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def insert(self, user_id: str, text: str, sender: str | None = None) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO bot_outbound_messages (user_id, text, sender)
            VALUES (?, ?, ?)
            """,
            (user_id, text, sender),
        )
        return cursor.lastrowid

    def fetch_pending(self, limit: int = 100) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT id, user_id, text, sender, status, created_at
            FROM bot_outbound_messages
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_sent(self, msg_id: int) -> None:
        self._conn.execute(
            "UPDATE bot_outbound_messages "
            "SET status = 'sent', completed_at = datetime('now') "
            "WHERE id = ?",
            (msg_id,),
        )

    def mark_failed(self, msg_id: int, error: str) -> None:
        self._conn.execute(
            "UPDATE bot_outbound_messages "
            "SET status = 'failed', completed_at = datetime('now'), error = ? "
            "WHERE id = ?",
            (error, msg_id),
        )
