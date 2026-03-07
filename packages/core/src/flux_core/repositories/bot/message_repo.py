"""BotMessageRepository Protocol — interface for bot message data access."""

from __future__ import annotations

from typing import Protocol


class BotMessageRepository(Protocol):
    """Repository interface for bot_messages table."""

    def insert(
        self,
        user_id: str,
        channel: str,
        platform_id: str,
        text: str | None = None,
        image_path: str | None = None,
    ) -> int: ...

    def fetch_pending(self) -> list[dict]: ...

    def mark_processing(self, msg_id: int) -> None: ...

    def mark_processed(self, msg_id: int) -> None: ...

    def mark_failed(self, msg_id: int, error: str) -> None: ...
