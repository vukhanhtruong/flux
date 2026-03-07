"""SQLite implementation of BotSessionRepository Protocol."""
from __future__ import annotations

import sqlite3


class SqliteBotSessionRepository:
    """SQLite-backed bot session repository."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_session_id(self, user_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT session_id FROM bot_sessions WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return row["session_id"] if row else None

    def upsert(self, user_id: str, session_id: str) -> None:
        self._conn.execute(
            """
            INSERT INTO bot_sessions (user_id, session_id, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT (user_id)
            DO UPDATE SET session_id = excluded.session_id, updated_at = datetime('now')
            """,
            (user_id, session_id),
        )

    def delete(self, user_id: str) -> None:
        self._conn.execute(
            "DELETE FROM bot_sessions WHERE user_id = ?",
            (user_id,),
        )
