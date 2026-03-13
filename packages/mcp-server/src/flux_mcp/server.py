import argparse
import os

from fastmcp import FastMCP

from flux_core.infrastructure import (  # noqa: F401
    get_db,
    get_embedding_service,
    get_event_bus,
    get_local_storage,
    get_s3_storage,
    get_uow,
    get_vector_store,
)
from flux_core.logging import configure_logging
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

_session_user_id: str = ""
_tunnel_manager = None
_user_timezone: str | None = None


def get_session_user_id() -> str:
    """Return the user_id for this MCP server session."""
    if not _session_user_id:
        raise RuntimeError("MCP server started without --user-id. Cannot identify user.")
    return _session_user_id


def get_tunnel_manager():
    global _tunnel_manager
    if _tunnel_manager is None:
        from flux_mcp.ngrok import TunnelManager
        port = int(os.getenv("NGROK_TUNNEL_PORT", "80"))
        timeout = int(os.getenv("NGROK_TUNNEL_TIMEOUT_MINUTES", "30"))
        _tunnel_manager = TunnelManager(port=port, timeout_minutes=timeout)
    return _tunnel_manager


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
    mcp, get_db, get_uow, get_vector_store, get_embedding_service, get_session_user_id,
)
register_analytics_tools(mcp, get_db, get_session_user_id)
register_profile_tools(mcp, get_db, get_uow, get_session_user_id)
register_ipc_tools(mcp, get_db, get_uow, get_session_user_id, get_user_timezone)
register_savings_tools(mcp, get_db, get_uow, get_session_user_id, get_user_timezone)
register_backup_tools(mcp, get_db, get_local_storage, get_s3_storage)
register_ngrok_tools(mcp, get_tunnel_manager, get_session_user_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", default="", help="Authenticated user_id for this session")
    args, _ = parser.parse_known_args()

    configure_logging()
    _session_user_id = args.user_id
    mcp.run()
