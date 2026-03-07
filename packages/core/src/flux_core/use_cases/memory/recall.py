"""Recall use case — semantic search of memories via zvec."""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from flux_core.embeddings.service import EmbeddingProvider
    from flux_core.models.memory import MemoryOut
    from flux_core.repositories.memory_repo import MemoryRepository
    from flux_core.vector.store import ZvecStore


class Recall:
    """Recall memories semantically similar to a query (read-only)."""

    def __init__(
        self,
        memory_repo: MemoryRepository,
        vector_store: ZvecStore,
        embedding_svc: EmbeddingProvider,
    ):
        self._memory_repo = memory_repo
        self._vector_store = vector_store
        self._embedding_svc = embedding_svc

    async def execute(
        self,
        user_id: str,
        query: str,
        *,
        limit: int = 5,
    ) -> list[MemoryOut]:
        embedding = self._embedding_svc.embed(query)
        doc_ids = self._vector_store.search(
            "memory_embeddings",
            embedding,
            limit,
            filter=f'user_id = "{user_id}"',
        )
        if not doc_ids:
            return []
        uuids = [UUID(doc_id) for doc_id in doc_ids]
        return self._memory_repo.get_by_ids(uuids)
