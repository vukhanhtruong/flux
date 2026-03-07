"""ListMemories use case — read-only listing."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.models.memory import MemoryOut
    from flux_core.repositories.memory_repo import MemoryRepository


class ListMemories:
    """List all memories for a user, optionally filtered by type (read-only)."""

    def __init__(self, memory_repo: MemoryRepository):
        self._memory_repo = memory_repo

    async def execute(
        self,
        user_id: str,
        *,
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[MemoryOut]:
        return self._memory_repo.list_by_user(
            user_id, memory_type=memory_type, limit=limit
        )
