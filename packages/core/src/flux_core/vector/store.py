from __future__ import annotations

import structlog
from pathlib import Path
from typing import Any

try:
    import zvec
    ZVEC_AVAILABLE = True
except ImportError:
    zvec = None  # type: ignore[assignment]
    ZVEC_AVAILABLE = False

logger = structlog.get_logger(__name__)


class ZvecStore:
    def __init__(self, path: str):
        self._path = Path(path)
        self._collections: dict[str, Any] = {}

    def upsert(
        self, collection: str, doc_id: str, vector: list[float], metadata: dict
    ) -> None:
        logger.debug("zvec upsert", collection=collection, doc_id=doc_id, dim=len(vector))
        coll = self._get_or_create(collection, len(vector), metadata)
        doc = zvec.Doc(
            id=doc_id,
            vectors={"embedding": vector},
            fields={k: v for k, v in metadata.items()},
        )
        coll.upsert(doc)

    def delete(self, collection: str, doc_id: str) -> None:
        logger.debug("zvec delete", collection=collection, doc_id=doc_id)
        coll = self._get(collection)
        if coll is not None:
            coll.delete(ids=doc_id)

    def search(
        self,
        collection: str,
        vector: list[float],
        limit: int,
        filter: str | None = None,
    ) -> list[str]:
        logger.debug("zvec search", collection=collection, limit=limit, has_filter=filter is not None)
        coll = self._get(collection)
        if coll is None:
            return []
        query = zvec.VectorQuery(field_name="embedding", vector=vector)
        try:
            if filter:
                results = coll.query(query, topk=limit, filter=filter)
            else:
                results = coll.query(query, topk=limit)
        except Exception:
            logger.debug("zvec query failed, returning empty", exc_info=True)
            return []
        return [doc.id for doc in results]

    def optimize(self, collection: str) -> None:
        coll = self._get(collection)
        if coll is not None:
            coll.optimize()

    def _get(self, name: str) -> Any | None:
        if name in self._collections:
            return self._collections[name]
        collection_path = self._path / name
        if not collection_path.exists():
            return None
        try:
            coll = zvec.open(path=str(collection_path))
            self._collections[name] = coll
            return coll
        except Exception:
            logger.debug("Failed to open zvec collection %s", name, exc_info=True)
            return None

    def _get_or_create(self, name: str, dimension: int, metadata: dict) -> Any:
        coll = self._get(name)
        if coll is not None:
            return coll

        collection_path = self._path / name
        collection_path.parent.mkdir(parents=True, exist_ok=True)

        fields = [
            zvec.FieldSchema(name=key, data_type=zvec.DataType.STRING, nullable=True)
            for key in metadata.keys()
        ]
        schema = zvec.CollectionSchema(
            name=name,
            fields=fields,
            vectors=[
                zvec.VectorSchema(
                    name="embedding",
                    data_type=zvec.DataType.VECTOR_FP32,
                    dimension=dimension,
                ),
            ],
        )
        coll = zvec.create_and_open(path=str(collection_path), schema=schema)
        self._collections[name] = coll
        logger.info("Created zvec collection: %s (dim=%d)", name, dimension)
        return coll
