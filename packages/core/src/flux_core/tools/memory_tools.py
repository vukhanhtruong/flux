from typing import Optional

from flux_core.db.memory_repo import MemoryRepository
from flux_core.embeddings.service import EmbeddingProvider
from flux_core.models.memory import MemoryCreate, MemoryType


async def remember(
    user_id: str,
    memory_type: str,
    content: str,
    repo: MemoryRepository,
    embedding_service: EmbeddingProvider
) -> dict:
    """Store a memory with semantic embedding."""
    memory = MemoryCreate(
        user_id=user_id,
        memory_type=MemoryType(memory_type),
        content=content
    )

    embedding = embedding_service.embed(content)
    result = await repo.create(memory, embedding)

    return {
        "id": str(result.id),
        "user_id": result.user_id,
        "memory_type": result.memory_type.value,
        "content": result.content,
        "created_at": result.created_at.isoformat()
    }


async def recall(
    user_id: str,
    query: str,
    repo: MemoryRepository,
    embedding_service: EmbeddingProvider,
    limit: int = 5
) -> list[dict]:
    """Recall memories semantically similar to a query."""
    embedding = embedding_service.embed(query)
    memories = await repo.search_by_embedding(user_id, embedding, limit)

    return [
        {
            "id": str(m.id),
            "user_id": m.user_id,
            "memory_type": m.memory_type.value,
            "content": m.content,
            "created_at": m.created_at.isoformat()
        }
        for m in memories
    ]


async def list_memories(
    user_id: str,
    repo: MemoryRepository,
    memory_type: Optional[str] = None
) -> list[dict]:
    """List all memories for a user, optionally filtered by type."""
    memories = await repo.list_by_user(user_id, memory_type)

    return [
        {
            "id": str(m.id),
            "user_id": m.user_id,
            "memory_type": m.memory_type.value,
            "content": m.content,
            "created_at": m.created_at.isoformat()
        }
        for m in memories
    ]
