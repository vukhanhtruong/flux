"""BotSessionRepository Protocol — interface for bot session data access."""

from __future__ import annotations

from typing import Protocol


class BotSessionRepository(Protocol):
    """Repository interface for bot_sessions table."""

    def get_session_id(self, user_id: str) -> str | None: ...

    def upsert(self, user_id: str, session_id: str) -> None: ...

    def delete(self, user_id: str) -> None: ...
