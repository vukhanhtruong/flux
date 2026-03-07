from __future__ import annotations

import asyncio
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, path: str):
        self._path = path
        self._conn: sqlite3.Connection | None = None
        self._executor = ThreadPoolExecutor(max_workers=1)

    def connect(self) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            self._path, check_same_thread=False, isolation_level=None
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.execute("PRAGMA cache_size = -8000")
        self._conn.execute("PRAGMA wal_autocheckpoint = 1000")
        logger.info("Connected to SQLite: %s (WAL mode)", self._path)

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
        self._executor.shutdown(wait=False)

    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.connection().execute(sql, params)

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self.connection().execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.connection().execute(sql, params).fetchall()

    async def execute_async(self, sql: str, params: tuple = ()) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self.execute, sql, params)

    async def fetchone_async(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.fetchone, sql, params)

    async def fetchall_async(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.fetchall, sql, params)
