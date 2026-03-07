"""SearchTransactions use case — semantic search via zvec then fetch from SQLite."""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from flux_core.embeddings.service import EmbeddingProvider
    from flux_core.models.transaction import TransactionOut
    from flux_core.repositories.transaction_repo import TransactionRepository
    from flux_core.vector.store import ZvecStore


class SearchTransactions:
    """Search transactions semantically (read-only)."""

    def __init__(
        self,
        txn_repo: TransactionRepository,
        vector_store: ZvecStore,
        embedding_svc: EmbeddingProvider,
    ):
        self._txn_repo = txn_repo
        self._vector_store = vector_store
        self._embedding_svc = embedding_svc

    async def execute(
        self,
        user_id: str,
        query: str,
        *,
        limit: int = 10,
    ) -> list[TransactionOut]:
        embedding = self._embedding_svc.embed(query)
        doc_ids = self._vector_store.search(
            "transaction_embeddings",
            embedding,
            limit,
            filter=f'user_id = "{user_id}"',
        )
        if not doc_ids:
            return []
        uuids = [UUID(doc_id) for doc_id in doc_ids]
        return self._txn_repo.get_by_ids(uuids)
