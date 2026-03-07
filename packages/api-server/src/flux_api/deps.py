"""FastAPI dependencies for SQLite database, vector store, and embedding service."""
import os

from flux_core.embeddings.service import EmbeddingService
from flux_core.events.bus import EventBus
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.vector.store import ZvecStore

# Global singletons (lazy-loaded)
_db: Database | None = None
_vector_store: ZvecStore | None = None
_event_bus: EventBus | None = None
_embedding_service: EmbeddingService | None = None


def get_db() -> Database:
    """Get the shared Database singleton (lazy init + migration)."""
    global _db
    if _db is None:
        db_path = os.getenv("DATABASE_PATH", "/data/sqlite/flux.db")
        _db = Database(db_path)
        _db.connect()
        migrate(_db)
    return _db


def get_vector_store() -> ZvecStore:
    """Get the shared ZvecStore singleton."""
    global _vector_store
    if _vector_store is None:
        zvec_path = os.getenv("ZVEC_PATH", "/data/zvec")
        _vector_store = ZvecStore(zvec_path)
    return _vector_store


def get_event_bus() -> EventBus:
    """Get the shared EventBus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def get_uow() -> UnitOfWork:
    """Create a new UnitOfWork instance."""
    return UnitOfWork(get_db(), get_vector_store(), get_event_bus())


def get_embedding_service() -> EmbeddingService:
    """Get the shared EmbeddingService singleton."""
    global _embedding_service
    if _embedding_service is None:
        model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        _embedding_service = EmbeddingService(model)
    return _embedding_service
