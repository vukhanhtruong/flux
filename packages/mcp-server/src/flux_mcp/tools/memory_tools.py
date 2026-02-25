from typing import Callable, Awaitable

from fastmcp import FastMCP
from flux_core.db.connection import Database
from flux_core.db.memory_repo import MemoryRepository
from flux_core.embeddings.service import EmbeddingProvider
from flux_core.tools import memory_tools as biz


def register_memory_tools(
    mcp: FastMCP,
    get_db: Callable[[], Awaitable[Database]],
    get_embedding_service: Callable[[], EmbeddingProvider],
    get_user_id: Callable[[], str],
):
    @mcp.tool()
    async def remember(memory_type: str, content: str) -> dict:
        """Store a memory with semantic embedding."""
        db = await get_db()
        return await biz.remember(
            get_user_id(), memory_type, content, MemoryRepository(db), get_embedding_service(),
        )

    @mcp.tool()
    async def recall(query: str, limit: int = 5) -> list[dict]:
        """Recall memories semantically similar to a query."""
        db = await get_db()
        return await biz.recall(
            get_user_id(), query, MemoryRepository(db), get_embedding_service(), limit,
        )
