from typing import Callable

from fastmcp import FastMCP
from flux_core.embeddings.service import EmbeddingProvider
from flux_core.models.memory import MemoryType
from flux_core.sqlite.memory_repo import SqliteMemoryRepository
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.memory.list_memories import ListMemories
from flux_core.use_cases.memory.recall import Recall
from flux_core.use_cases.memory.remember import Remember
from flux_core.vector.store import ZvecStore


def register_memory_tools(
    mcp: FastMCP,
    get_uow: Callable[[], UnitOfWork],
    get_vector_store: Callable[[], ZvecStore],
    get_embedding_service: Callable[[], EmbeddingProvider],
    get_user_id: Callable[[], str],
):
    @mcp.tool()
    async def remember(memory_type: str, content: str) -> dict:
        """Store a memory with semantic embedding."""
        uc = Remember(get_uow(), get_embedding_service())
        result = await uc.execute(
            get_user_id(), MemoryType(memory_type), content,
        )
        return {
            "id": str(result.id),
            "memory_type": result.memory_type.value,
            "content": result.content,
        }

    @mcp.tool()
    async def list_memories(
        memory_type: str | None = None, limit: int = 50
    ) -> list[dict]:
        """List all memories, optionally filtered by type."""
        from flux_mcp.server import get_db

        db = get_db()
        repo = SqliteMemoryRepository(db.connection())
        uc = ListMemories(repo)
        results = await uc.execute(
            get_user_id(), memory_type=memory_type, limit=limit
        )
        return [
            {
                "id": str(m.id),
                "memory_type": m.memory_type.value,
                "content": m.content,
                "created_at": str(m.created_at),
            }
            for m in results
        ]

    @mcp.tool()
    async def recall(query: str, limit: int = 5) -> list[dict]:
        """Recall memories semantically similar to a query."""
        # Read-only: use repo + vector store directly
        from flux_mcp.server import get_db
        db = get_db()
        repo = SqliteMemoryRepository(db.connection())
        uc = Recall(repo, get_vector_store(), get_embedding_service())
        results = await uc.execute(get_user_id(), query, limit=limit)
        return [
            {
                "id": str(m.id),
                "memory_type": m.memory_type.value,
                "content": m.content,
                "created_at": str(m.created_at),
            }
            for m in results
        ]
