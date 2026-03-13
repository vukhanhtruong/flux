"""Shared test fixtures for E2E tests across packages."""


class InMemoryVectorStore:
    """In-memory vector store substitute when zvec is not available."""

    def __init__(self):
        self._docs: dict[str, dict[str, tuple[list[float], dict]]] = {}

    def upsert(
        self, collection: str, doc_id: str, vector: list[float], metadata: dict
    ) -> None:
        if collection not in self._docs:
            self._docs[collection] = {}
        self._docs[collection][doc_id] = (vector, metadata)

    def delete(self, collection: str, doc_id: str) -> None:
        if collection in self._docs:
            self._docs[collection].pop(doc_id, None)

    def search(
        self,
        collection: str,
        vector: list[float],
        limit: int,
        filter: str | None = None,
    ) -> list[str]:
        if collection not in self._docs:
            return []
        return list(self._docs[collection].keys())[:limit]

    def optimize(self, collection: str) -> None:
        pass

    def has_docs(self, collection: str) -> bool:
        return bool(self._docs.get(collection))
