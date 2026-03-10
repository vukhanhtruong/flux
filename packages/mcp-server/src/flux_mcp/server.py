import argparse
import os

from fastmcp import FastMCP

from flux_core.embeddings.service import EmbeddingService
from flux_core.events.bus import EventBus
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.logging import configure_logging
from flux_core.vector.store import ZvecStore
from flux_mcp.tools.analytics_tools import register_analytics_tools
from flux_mcp.tools.backup_tools import register_backup_tools
from flux_mcp.tools.financial_tools import register_financial_tools
from flux_mcp.tools.ipc_tools import register_ipc_tools
from flux_mcp.tools.memory_tools import register_memory_tools
from flux_mcp.tools.profile_tools import register_profile_tools
from flux_mcp.tools.savings_tools import register_savings_tools
from flux_mcp.tools.ngrok_tools import register_ngrok_tools
from flux_mcp.tools.transaction_tools import register_transaction_tools

mcp = FastMCP("flux")

_db: Database | None = None
_vector_store: ZvecStore | None = None
_event_bus: EventBus | None = None
_embedding_service: EmbeddingService | None = None
_session_user_id: str = ""
_tunnel_manager = None


def get_session_user_id() -> str:
    """Return the user_id for this MCP server session."""
    if not _session_user_id:
        raise RuntimeError("MCP server started without --user-id. Cannot identify user.")
    return _session_user_id


def get_db() -> Database:
    global _db
    if _db is None:
        db_path = os.getenv("DATABASE_PATH", "/data/sqlite/flux.db")
        _db = Database(db_path)
        _db.connect()
        migrate(_db)
    return _db


def get_vector_store() -> ZvecStore:
    global _vector_store
    if _vector_store is None:
        zvec_path = os.getenv("ZVEC_PATH", "/data/zvec")
        _vector_store = ZvecStore(zvec_path)
    return _vector_store


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def get_uow() -> UnitOfWork:
    return UnitOfWork(get_db(), get_vector_store(), get_event_bus())


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        _embedding_service = EmbeddingService(model)
    return _embedding_service


def get_local_storage():
    from flux_core.services.storage.local import LocalStorageProvider
    backup_dir = os.getenv("BACKUP_LOCAL_DIR", "/data/backups")
    return LocalStorageProvider(backup_dir)


def get_s3_storage():
    try:
        from flux_core.services.encryption import EncryptionService
        from flux_core.sqlite.system_config_repo import SqliteSystemConfigRepository
        enc = EncryptionService.from_env()
        config_repo = SqliteSystemConfigRepository(get_db().connection(), enc)
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


def get_tunnel_manager():
    global _tunnel_manager
    if _tunnel_manager is None:
        from flux_mcp.ngrok import TunnelManager
        port = int(os.getenv("NGROK_TUNNEL_PORT", "80"))
        timeout = int(os.getenv("NGROK_TUNNEL_TIMEOUT_MINUTES", "30"))
        _tunnel_manager = TunnelManager(port=port, timeout_minutes=timeout)
    return _tunnel_manager


_user_timezone: str | None = None


def get_user_timezone() -> str:
    global _user_timezone
    if _user_timezone is None:
        db = get_db()
        user_id = get_session_user_id()
        from flux_core.sqlite.user_repo import SqliteUserRepository
        repo = SqliteUserRepository(db.connection())
        profile = repo.get_by_user_id(user_id)
        _user_timezone = profile.timezone if profile and profile.timezone else "UTC"
    return _user_timezone


# Register all tools
register_transaction_tools(
    mcp, get_db, get_uow, get_vector_store, get_embedding_service, get_session_user_id,
    get_user_timezone,
)
register_financial_tools(
    mcp, get_db, get_uow, get_embedding_service, get_session_user_id, get_user_timezone,
)
register_memory_tools(
    mcp, get_uow, get_vector_store, get_embedding_service, get_session_user_id,
)
register_analytics_tools(mcp, get_db, get_session_user_id)
register_profile_tools(mcp, get_db, get_uow, get_session_user_id)
register_ipc_tools(mcp, get_uow, get_session_user_id, get_user_timezone)
register_savings_tools(mcp, get_uow, get_session_user_id, get_user_timezone)
register_backup_tools(mcp, get_db, get_local_storage, get_s3_storage)
register_ngrok_tools(mcp, get_tunnel_manager, get_session_user_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", default="", help="Authenticated user_id for this session")
    args, _ = parser.parse_known_args()

    configure_logging()
    _session_user_id = args.user_id
    mcp.run()
