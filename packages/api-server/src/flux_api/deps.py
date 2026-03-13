"""FastAPI dependencies — re-exports shared infrastructure + api-server-specific deps."""

from flux_core.infrastructure import (  # noqa: F401
    get_db,
    get_embedding_service,
    get_event_bus,
    get_local_storage,
    get_s3_storage,
    get_uow,
    get_vector_store,
)


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
