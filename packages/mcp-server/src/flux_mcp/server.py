import argparse
import os
from fastmcp import FastMCP

from flux_core.db.connection import Database
from flux_core.embeddings.service import EmbeddingService

mcp = FastMCP("flux")

_db: Database | None = None
_embedding_service: EmbeddingService | None = None
_session_user_id: str = ""


def get_session_user_id() -> str:
    """Return the user_id for this MCP server session."""
    if not _session_user_id:
        raise RuntimeError("MCP server started without --user-id. Cannot identify user.")
    return _session_user_id


async def get_db() -> Database:
    global _db
    if _db is None:
        database_url = os.getenv("DATABASE_URL", "postgresql://localhost/flux")
        _db = Database(database_url)
        await _db.connect()
    return _db


_user_timezone: str | None = None


async def get_user_timezone() -> str:
    global _user_timezone
    if _user_timezone is None:
        db = await get_db()
        user_id = get_session_user_id()
        row = await db.fetchrow("SELECT timezone FROM users WHERE id = $1", user_id)
        _user_timezone = (row["timezone"] if row and row["timezone"] else "UTC")
    return _user_timezone


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        _embedding_service = EmbeddingService(model)
    return _embedding_service


# Register all tools
from flux_mcp.tools.transaction_tools import register_transaction_tools
from flux_mcp.tools.financial_tools import register_financial_tools
from flux_mcp.tools.memory_tools import register_memory_tools
from flux_mcp.tools.analytics_tools import register_analytics_tools
from flux_mcp.tools.profile_tools import register_profile_tools
from flux_mcp.tools.ipc_tools import register_ipc_tools
from flux_mcp.tools.savings_tools import register_savings_tools

register_transaction_tools(mcp, get_db, get_embedding_service, get_session_user_id, get_user_timezone)
register_financial_tools(mcp, get_db, get_session_user_id, get_embedding_service, get_user_timezone)
register_memory_tools(mcp, get_db, get_embedding_service, get_session_user_id)
register_analytics_tools(mcp, get_db, get_session_user_id)
register_profile_tools(mcp, get_db, get_session_user_id)
register_ipc_tools(mcp, get_db, get_session_user_id)
register_savings_tools(mcp, get_db, get_session_user_id, get_user_timezone)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", default="", help="Authenticated user_id for this session")
    args, _ = parser.parse_known_args()

    _session_user_id = args.user_id
    mcp.run()
