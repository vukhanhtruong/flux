"""Shared test fixtures for E2E tests across packages."""

from __future__ import annotations


class InMemoryVectorStore:
    """In-memory vector store substitute matching EmbeddingRepository."""

    def __init__(self):
        self._docs: dict[str, dict[str, tuple[list[float], dict]]] = {}

    def upsert(
        self, collection: str, doc_id: str, vector: list[float], metadata: dict
    ) -> None:
        self._docs.setdefault(collection, {})[doc_id] = (vector, metadata)

    def delete(self, collection: str, doc_id: str) -> None:
        self._docs.get(collection, {}).pop(doc_id, None)

    def search(
        self,
        collection: str,
        vector: list[float],
        limit: int,
        filter: dict[str, str] | None = None,
    ) -> list[str]:
        docs = self._docs.get(collection, {})
        if not filter:
            return list(docs.keys())[:limit]
        filtered = [
            doc_id
            for doc_id, (_, meta) in docs.items()
            if all(meta.get(k) == v for k, v in filter.items())
        ]
        return filtered[:limit]

    def has_docs(self, collection: str) -> bool:
        return bool(self._docs.get(collection))
