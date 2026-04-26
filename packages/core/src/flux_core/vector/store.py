from __future__ import annotations

import struct
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from flux_core.sqlite.database import Database

logger = structlog.get_logger(__name__)

def _serialize(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


class SqliteVecStore:
    """EmbeddingRepository backed by sqlite-vec vec0 virtual tables.

    Collections map to tables named `vec_{collection}`. Writes normally run
    inside the UnitOfWork's open SQLite transaction; this class is used for
    read-only `search()` calls and for standalone writes.
    """

    def __init__(self, db: Database):
        self._db = db

    def upsert(
        self,
        collection: str,
        doc_id: str,
        vector: list[float],
        metadata: dict,
    ) -> None:
        logger.debug("sqlite-vec upsert", collection=collection, doc_id=doc_id)
        table = f"vec_{collection}"
        # sqlite-vec vec0 does not support INSERT OR REPLACE conflict resolution;
        # upsert is implemented as delete-then-insert.
        self._db.execute(f"DELETE FROM {table} WHERE id = ?", (doc_id,))
        self._db.execute(
            f"INSERT INTO {table}(id, embedding, user_id) VALUES (?, ?, ?)",
            (doc_id, _serialize(vector), metadata.get("user_id")),
        )

    def delete(self, collection: str, doc_id: str) -> None:
        logger.debug("sqlite-vec delete", collection=collection, doc_id=doc_id)
        table = f"vec_{collection}"
        self._db.execute(f"DELETE FROM {table} WHERE id = ?", (doc_id,))

    def search(
        self,
        collection: str,
        vector: list[float],
        limit: int,
        filter: dict[str, str] | None = None,
    ) -> list[str]:
        logger.debug(
            "sqlite-vec search", collection=collection, limit=limit,
            filter_keys=list(filter.keys()) if filter else [],
        )
        table = f"vec_{collection}"
        filter_sql = ""
        params: list = [_serialize(vector), limit]
        if filter:
            clauses = []
            for key, value in filter.items():
                clauses.append(f"{key} = ?")
                params.append(value)
            filter_sql = " AND " + " AND ".join(clauses)
        try:
            rows = self._db.fetchall(
                f"SELECT id FROM {table} WHERE embedding MATCH ? AND k = ?{filter_sql} ORDER BY distance",
                tuple(params),
            )
        except Exception:
            logger.debug("sqlite-vec query failed, returning empty", exc_info=True)
            return []
        return [r["id"] for r in rows]