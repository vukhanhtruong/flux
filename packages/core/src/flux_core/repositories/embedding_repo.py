"""EmbeddingRepository Protocol — interface for vector embedding storage (sqlite-vec)."""

from __future__ import annotations

from typing import Protocol


class EmbeddingRepository(Protocol):
    """Repository interface for vector embeddings.

    Backed by sqlite-vec vec0 virtual tables inside the same SQLite database.
    The use case layer coordinates between relational repos and this repo.
    """

    def upsert(
        self, collection: str, doc_id: str, vector: list[float], metadata: dict
    ) -> None: ...

    def delete(self, collection: str, doc_id: str) -> None: ...

    def search(
        self,
        collection: str,
        vector: list[float],
        limit: int,
        filter: dict[str, str] | None = None,
    ) -> list[str]: ...
