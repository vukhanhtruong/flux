from typing import Optional

from flux_core.db.connection import Database
from flux_core.models.memory import MemoryCreate, MemoryOut


class MemoryRepository:
    def __init__(self, db: Database):
        self._db = db

    async def create(self, memory: MemoryCreate, embedding: Optional[list[float]] = None) -> MemoryOut:
        row = await self._db.fetchrow(
            """
            INSERT INTO agent_memory (user_id, memory_type, content, embedding)
            VALUES ($1, $2, $3, $4)
            RETURNING id, user_id, memory_type, content, created_at
            """,
            memory.user_id, memory.memory_type.value, memory.content, embedding,
        )
        return MemoryOut(**dict(row))

    async def search_by_embedding(
        self, user_id: str, embedding: list[float], limit: int = 5
    ) -> list[MemoryOut]:
        rows = await self._db.fetch(
            """
            SELECT id, user_id, memory_type, content, created_at
            FROM agent_memory
            WHERE user_id = $1 AND embedding IS NOT NULL
            ORDER BY embedding <=> $2::vector
            LIMIT $3
            """,
            user_id, str(embedding), limit,
        )
        return [MemoryOut(**dict(r)) for r in rows]

    async def list_by_user(self, user_id: str, memory_type: Optional[str] = None) -> list[MemoryOut]:
        if memory_type:
            rows = await self._db.fetch(
                """
                SELECT id, user_id, memory_type, content, created_at
                FROM agent_memory WHERE user_id = $1 AND memory_type = $2
                ORDER BY created_at DESC
                """,
                user_id, memory_type,
            )
        else:
            rows = await self._db.fetch(
                """
                SELECT id, user_id, memory_type, content, created_at
                FROM agent_memory WHERE user_id = $1
                ORDER BY created_at DESC
                """,
                user_id,
            )
        return [MemoryOut(**dict(r)) for r in rows]
