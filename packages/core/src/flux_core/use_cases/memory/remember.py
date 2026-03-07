"""Remember use case — store a memory with embedding (dual-write)."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from flux_core.events.events import MemoryCreated
from flux_core.models.memory import MemoryCreate, MemoryType
from flux_core.sqlite.memory_repo import SqliteMemoryRepository

if TYPE_CHECKING:
    from flux_core.embeddings.service import EmbeddingProvider
    from flux_core.models.memory import MemoryOut
    from flux_core.uow.unit_of_work import UnitOfWork


class Remember:
    """Store a memory with semantic embedding (dual-write via UoW)."""

    def __init__(self, uow: UnitOfWork, embedding_svc: EmbeddingProvider):
        self._uow = uow
        self._embedding_svc = embedding_svc

    async def execute(
        self,
        user_id: str,
        memory_type: MemoryType,
        content: str,
    ) -> MemoryOut:
        memory = MemoryCreate(
            user_id=user_id,
            memory_type=memory_type,
            content=content,
        )

        embedding = self._embedding_svc.embed(content)

        async with self._uow:
            repo = SqliteMemoryRepository(self._uow.conn)
            created = repo.create(memory)
            self._uow.add_vector(
                "memory_embeddings",
                str(created.id),
                embedding,
                {"user_id": user_id},
            )
            self._uow.add_event(
                MemoryCreated(
                    timestamp=datetime.now(UTC),
                    memory_id=str(created.id),
                    user_id=user_id,
                )
            )
            await self._uow.commit()

        return created
