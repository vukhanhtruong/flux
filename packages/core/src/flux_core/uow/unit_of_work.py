from __future__ import annotations

import struct
import sqlite3
import structlog
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.events.bus import EventBus
    from flux_core.events.events import Event
    from flux_core.sqlite.database import Database

logger = structlog.get_logger(__name__)


@dataclass
class _VectorOp:
    collection: str
    doc_id: str
    vector: list[float]
    metadata: dict


@dataclass
class _VectorDeleteOp:
    collection: str
    doc_id: str


def _serialize(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


class UnitOfWork:
    """Coordinates SQLite writes (relational + sqlite-vec) and event emission.

    Write sequence:
      1. BEGIN SQLite transaction (in __aenter__)
      2. User performs SQL writes via uow.conn, registers vector ops via
         add_vector() / delete_vector(), and events via add_event()
      3. On commit(): flush buffered vector SQL on the open connection,
         COMMIT, then emit events

    Since vectors and relational rows share one transaction, ROLLBACK
    naturally discards both — no compensation logic needed.
    """

    def __init__(
        self,
        db: Database,
        event_bus: EventBus | None = None,
    ):
        self._db = db
        self._event_bus = event_bus
        self._pending_vectors: list[_VectorOp] = []
        self._pending_deletes: list[_VectorDeleteOp] = []
        self._pending_events: list[Event] = []
        self._conn: sqlite3.Connection | None = None
        self._committed = False

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("UnitOfWork not entered. Use 'async with uow:'")
        return self._conn

    def add_vector(
        self, collection: str, doc_id: str, vector: list[float], metadata: dict
    ) -> None:
        self._pending_vectors.append(_VectorOp(collection, doc_id, vector, metadata))

    def delete_vector(self, collection: str, doc_id: str) -> None:
        self._pending_deletes.append(_VectorDeleteOp(collection, doc_id))

    def add_event(self, event: Event) -> None:
        self._pending_events.append(event)

    async def commit(self) -> None:
        conn = self.conn
        logger.debug(
            "UoW commit",
            vectors=len(self._pending_vectors),
            deletes=len(self._pending_deletes),
            events=len(self._pending_events),
        )

        # Delete-then-insert pattern — sqlite-vec vec0 doesn't support
        # INSERT OR REPLACE conflict resolution.
        for op in self._pending_vectors:
            table = f"vec_{op.collection}"
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (op.doc_id,))
            conn.execute(
                f"INSERT INTO {table}(id, embedding, user_id) VALUES (?, ?, ?)",
                (op.doc_id, _serialize(op.vector), op.metadata.get("user_id")),
            )
        for op in self._pending_deletes:
            table = f"vec_{op.collection}"
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (op.doc_id,))

        conn.commit()
        self._committed = True

        if self._event_bus:
            for event in self._pending_events:
                await self._event_bus.emit(event)

    async def __aenter__(self) -> UnitOfWork:
        self._conn = self._db.connection()
        self._conn.execute("BEGIN")
        logger.debug("UoW begin")
        self._pending_vectors.clear()
        self._pending_deletes.clear()
        self._pending_events.clear()
        self._committed = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self._committed:
            logger.debug("UoW rollback")
            try:
                self.conn.rollback()
            except Exception:
                pass
        self._conn = None
        return False
