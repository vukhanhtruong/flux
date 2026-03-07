from __future__ import annotations

import structlog
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.events.bus import EventBus
    from flux_core.events.events import Event
    from flux_core.sqlite.database import Database
    from flux_core.vector.store import ZvecStore

logger = structlog.get_logger(__name__)


@dataclass
class VectorOp:
    collection: str
    doc_id: str
    vector: list[float]
    metadata: dict


@dataclass
class VectorDeleteOp:
    collection: str
    doc_id: str


class UnitOfWork:
    """Coordinates dual-writes between SQLite and zvec, plus event emission.

    Write sequence:
      1. BEGIN SQLite transaction (in __aenter__)
      2. User performs SQL writes via uow.conn
      3. User registers vector ops via add_vector() and events via add_event()
      4. On commit(): write zvec first (SQLite tx still open), then COMMIT SQLite,
         then emit events
      5. If zvec fails: ROLLBACK the still-uncommitted SQLite transaction
      6. If SQLite COMMIT fails after zvec succeeds: compensate by deleting zvec docs
    """

    def __init__(
        self,
        db: Database,
        vector_store: ZvecStore | None = None,
        event_bus: EventBus | None = None,
    ):
        self._db = db
        self._vector_store = vector_store
        self._event_bus = event_bus
        self._pending_vectors: list[VectorOp] = []
        self._pending_deletes: list[VectorDeleteOp] = []
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
        self._pending_vectors.append(VectorOp(collection, doc_id, vector, metadata))

    def delete_vector(self, collection: str, doc_id: str) -> None:
        self._pending_deletes.append(VectorDeleteOp(collection, doc_id))

    def add_event(self, event: Event) -> None:
        self._pending_events.append(event)

    async def commit(self) -> None:
        conn = self.conn
        logger.debug("UoW commit", vectors=len(self._pending_vectors), deletes=len(self._pending_deletes), events=len(self._pending_events))

        # Step 1: Write/delete zvec FIRST (SQLite tx still open)
        written_vectors: list[VectorOp] = []
        if self._pending_vectors and self._vector_store:
            try:
                for op in self._pending_vectors:
                    self._vector_store.upsert(
                        op.collection, op.doc_id, op.vector, op.metadata
                    )
                    written_vectors.append(op)
            except Exception:
                logger.error("zvec write failed, rolling back SQLite")
                conn.rollback()
                raise

        deleted_vectors: list[VectorDeleteOp] = []
        if self._pending_deletes and self._vector_store:
            try:
                for op in self._pending_deletes:
                    self._vector_store.delete(op.collection, op.doc_id)
                    deleted_vectors.append(op)
            except Exception:
                logger.error("zvec delete failed, rolling back SQLite")
                conn.rollback()
                raise

        # Step 2: COMMIT SQLite (zvec already written)
        try:
            conn.commit()
        except Exception:
            # SQLite commit failed — compensate zvec
            self._compensate_zvec(written_vectors)
            raise

        # Step 3: Emit events (both stores succeeded)
        self._committed = True
        if self._event_bus:
            for event in self._pending_events:
                await self._event_bus.emit(event)

    def _compensate_zvec(self, written: list[VectorOp]) -> None:
        if not self._vector_store:
            return
        for op in written:
            try:
                self._vector_store.delete(op.collection, op.doc_id)
            except Exception:
                logger.error(
                    "Failed to compensate zvec delete for %s/%s",
                    op.collection,
                    op.doc_id,
                )

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
