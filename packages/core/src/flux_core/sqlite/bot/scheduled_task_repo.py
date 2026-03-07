"""SQLite implementation of BotScheduledTaskRepository Protocol."""
from __future__ import annotations

import sqlite3
from datetime import datetime


class SqliteBotScheduledTaskRepository:
    """SQLite-backed bot scheduled task repository."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(
        self,
        user_id: str,
        prompt: str,
        schedule_type: str,
        schedule_value: str,
        next_run_at: datetime,
        subscription_id: str | None = None,
        asset_id: str | None = None,
    ) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO bot_scheduled_tasks
                (user_id, prompt, schedule_type, schedule_value, next_run_at,
                 subscription_id, asset_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                prompt,
                schedule_type,
                schedule_value,
                next_run_at.isoformat(),
                subscription_id,
                asset_id,
            ),
        )
        return cursor.lastrowid

    def fetch_due_tasks(self) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT t.id, t.user_id, t.prompt, t.schedule_type, t.schedule_value,
                   t.subscription_id, t.asset_id,
                   COALESCE(u.timezone, 'UTC') AS user_timezone
            FROM bot_scheduled_tasks t
            LEFT JOIN users u ON u.id = t.user_id
            WHERE t.status = 'active' AND t.next_run_at <= datetime('now')
            ORDER BY t.next_run_at
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def list_by_user(self, user_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT id, user_id, prompt, schedule_type, schedule_value,
                   status, next_run_at, last_run_at,
                   subscription_id, asset_id, created_at
            FROM bot_scheduled_tasks
            WHERE user_id = ? AND status = 'active'
            ORDER BY next_run_at ASC
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def advance_next_run(self, task_id: int, next_run_at: datetime) -> None:
        self._conn.execute(
            """
            UPDATE bot_scheduled_tasks
            SET last_run_at = datetime('now'), next_run_at = ?
            WHERE id = ?
            """,
            (next_run_at.isoformat(), task_id),
        )

    def mark_completed(self, task_id: int) -> None:
        self._conn.execute(
            """
            UPDATE bot_scheduled_tasks
            SET status = 'completed', last_run_at = datetime('now')
            WHERE id = ?
            """,
            (task_id,),
        )

    def pause(self, task_id: int) -> None:
        self._conn.execute(
            "UPDATE bot_scheduled_tasks SET status = 'paused' WHERE id = ?",
            (task_id,),
        )

    def pause_by_asset(self, asset_id: str) -> None:
        self._conn.execute(
            "UPDATE bot_scheduled_tasks SET status = 'paused' WHERE asset_id = ?",
            (asset_id,),
        )

    def resume_by_asset(self, asset_id: str, next_run_at: datetime) -> None:
        self._conn.execute(
            """
            UPDATE bot_scheduled_tasks
            SET status = 'active', next_run_at = ?
            WHERE asset_id = ?
            """,
            (next_run_at.isoformat(), asset_id),
        )

    def delete(self, task_id: int) -> None:
        self._conn.execute(
            "DELETE FROM bot_scheduled_tasks WHERE id = ?",
            (task_id,),
        )

    def delete_by_asset(self, asset_id: str) -> None:
        self._conn.execute(
            "DELETE FROM bot_scheduled_tasks WHERE asset_id = ?",
            (asset_id,),
        )

    def delete_by_subscription(self, subscription_id: str) -> None:
        self._conn.execute(
            "DELETE FROM bot_scheduled_tasks WHERE subscription_id = ?",
            (subscription_id,),
        )
