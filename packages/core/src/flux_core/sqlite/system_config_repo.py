"""SQLite implementation of SystemConfig repository."""
from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.services.encryption import EncryptionService


class SqliteSystemConfigRepository:
    def __init__(self, conn: sqlite3.Connection, encryption: EncryptionService):
        self._conn = conn
        self._enc = encryption

    def get(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value, encrypted FROM system_config WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        if row["encrypted"]:
            return self._enc.decrypt(row["value"])
        return row["value"]

    def set(self, key: str, value: str, *, encrypted: bool = False) -> None:
        stored_value = self._enc.encrypt(value) if encrypted else value
        self._conn.execute(
            "INSERT INTO system_config (key, value, encrypted, updated_at) "
            "VALUES (?, ?, ?, datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "encrypted = excluded.encrypted, updated_at = datetime('now')",
            (key, stored_value, int(encrypted)),
        )
        self._conn.commit()

    def delete(self, key: str) -> None:
        self._conn.execute("DELETE FROM system_config WHERE key = ?", (key,))
        self._conn.commit()

    def get_all(self) -> dict[str, str]:
        rows = self._conn.execute(
            "SELECT key, value, encrypted FROM system_config"
        ).fetchall()
        result = {}
        for row in rows:
            if row["encrypted"]:
                result[row["key"]] = self._enc.decrypt(row["value"])
            else:
                result[row["key"]] = row["value"]
        return result

    def get_by_prefix(self, prefix: str) -> dict[str, str]:
        rows = self._conn.execute(
            "SELECT key, value, encrypted FROM system_config WHERE key LIKE ?",
            (prefix + "%",),
        ).fetchall()
        result = {}
        for row in rows:
            if row["encrypted"]:
                result[row["key"]] = self._enc.decrypt(row["value"])
            else:
                result[row["key"]] = row["value"]
        return result
