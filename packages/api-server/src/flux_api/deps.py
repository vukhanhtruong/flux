"""FastAPI dependencies for database and embedding service."""
import os
from collections.abc import AsyncIterator

from flux_core.db.connection import Database
from flux_core.embeddings.service import EmbeddingService

# Global singletons (lazy-loaded)
_db: Database | None = None
_embedding_service: EmbeddingService | None = None


async def get_db() -> AsyncIterator[Database]:
    """FastAPI dependency for database connection."""
    global _db
    if _db is None:
        database_url = os.getenv("DATABASE_URL", "postgresql://localhost/flux")
        db = Database(database_url)
        await db.connect()
        _db = db
    yield _db


def get_embedding_service() -> EmbeddingService:
    """FastAPI dependency for embedding service."""
    global _embedding_service
    if _embedding_service is None:
        model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        _embedding_service = EmbeddingService(model)
    return _embedding_service
