"""BotOutboundRepository Protocol — interface for bot outbound message data access."""

from __future__ import annotations

from typing import Protocol


class BotOutboundRepository(Protocol):
    """Repository interface for bot_outbound_messages table."""

    def insert(self, user_id: str, text: str, sender: str | None = None) -> int: ...

    def fetch_pending(self) -> list[dict]: ...

    def mark_sent(self, msg_id: int) -> None: ...

    def mark_failed(self, msg_id: int, error: str) -> None: ...
