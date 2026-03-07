"""SQLite implementation of MemoryRepository Protocol."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import UUID, uuid4

from flux_core.models.memory import MemoryCreate, MemoryOut, MemoryType


class SqliteMemoryRepository:
    """SQLite-backed agent memory repository."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(self, memory: MemoryCreate) -> MemoryOut:
        mem_id = str(uuid4())
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        self._conn.execute(
            """
            INSERT INTO agent_memory (id, user_id, memory_type, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (mem_id, memory.user_id, memory.memory_type.value, memory.content, now),
        )
        return MemoryOut(
            id=UUID(mem_id),
            user_id=memory.user_id,
            memory_type=memory.memory_type,
            content=memory.content,
            created_at=datetime.fromisoformat(now),
        )

    def get_by_ids(self, ids: list[UUID]) -> list[MemoryOut]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"SELECT id, user_id, memory_type, content, created_at "
            f"FROM agent_memory WHERE id IN ({placeholders})",
            tuple(str(i) for i in ids),
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def list_by_user(
        self, user_id: str, *, memory_type: str | None = None, limit: int = 50
    ) -> list[MemoryOut]:
        if memory_type:
            rows = self._conn.execute(
                "SELECT id, user_id, memory_type, content, created_at "
                "FROM agent_memory WHERE user_id = ? AND memory_type = ? "
                "ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (user_id, memory_type, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, user_id, memory_type, content, created_at "
                "FROM agent_memory WHERE user_id = ? "
                "ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [self._from_row(r) for r in rows]

    @staticmethod
    def _from_row(row: sqlite3.Row) -> MemoryOut:
        return MemoryOut(
            id=UUID(row["id"]),
            user_id=row["user_id"],
            memory_type=MemoryType(row["memory_type"]),
            content=row["content"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
