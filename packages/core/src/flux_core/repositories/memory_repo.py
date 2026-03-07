"""MemoryRepository Protocol — interface for agent memory data access."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from flux_core.models.memory import MemoryCreate, MemoryOut


class MemoryRepository(Protocol):
    """Repository interface for agent memory."""

    def create(self, memory: MemoryCreate) -> MemoryOut: ...

    def get_by_ids(self, ids: list[UUID]) -> list[MemoryOut]: ...

    def list_by_user(
        self, user_id: str, *, memory_type: str | None = None, limit: int = 50
    ) -> list[MemoryOut]: ...
