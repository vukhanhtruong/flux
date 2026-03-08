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
_local_storage = None
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


def get_local_storage():
    """Get the shared LocalStorageProvider singleton."""
    from flux_core.services.storage.local import LocalStorageProvider

    global _local_storage
    if _local_storage is None:
        backup_dir = os.getenv("BACKUP_LOCAL_DIR", "/data/backups")
        _local_storage = LocalStorageProvider(backup_dir)
    return _local_storage


def get_s3_storage():
    """Get S3 provider if configured. Returns None if not configured."""
    try:
        from flux_core.services.encryption import EncryptionService
        from flux_core.sqlite.system_config_repo import SqliteSystemConfigRepository

        enc = EncryptionService.from_env()
        db = get_db()
        config_repo = SqliteSystemConfigRepository(db.connection(), enc)
        endpoint = config_repo.get("s3_endpoint")
        bucket = config_repo.get("s3_bucket")
        access_key = config_repo.get("s3_access_key")
        secret_key = config_repo.get("s3_secret_key")
        if all([endpoint, bucket, access_key, secret_key]):
            from flux_core.services.storage.s3 import S3StorageProvider

            region = config_repo.get("s3_region") or "auto"
            return S3StorageProvider(endpoint, access_key, secret_key, bucket, region)
    except (ValueError, ImportError):
        pass
    return None


def get_system_config_repo():
    """Get SystemConfigRepository, or None if FLUX_SECRET_KEY is not set."""
    try:
        from flux_core.services.encryption import EncryptionService
        from flux_core.sqlite.system_config_repo import SqliteSystemConfigRepository

        enc = EncryptionService.from_env()
        db = get_db()
        return SqliteSystemConfigRepository(db.connection(), enc)
    except (ValueError, ImportError):
        return None


def get_embedding_service() -> EmbeddingService:
    """Get the shared EmbeddingService singleton."""
    global _embedding_service
    if _embedding_service is None:
        model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        _embedding_service = EmbeddingService(model)
    return _embedding_service
