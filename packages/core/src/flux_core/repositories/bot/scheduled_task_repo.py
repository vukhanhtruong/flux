"""BotScheduledTaskRepository Protocol — interface for bot scheduled task data access."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class BotScheduledTaskRepository(Protocol):
    """Repository interface for bot_scheduled_tasks table."""

    def create(
        self,
        user_id: str,
        prompt: str,
        schedule_type: str,
        schedule_value: str,
        next_run_at: datetime,
        subscription_id: str | None = None,
        asset_id: str | None = None,
    ) -> int: ...

    def fetch_due_tasks(self) -> list[dict]: ...

    def list_by_user(self, user_id: str) -> list[dict]: ...

    def advance_next_run(self, task_id: int, next_run_at: datetime) -> None: ...

    def mark_completed(self, task_id: int) -> None: ...

    def pause(self, task_id: int) -> None: ...

    def pause_by_asset(self, asset_id: str) -> None: ...

    def resume_by_asset(self, asset_id: str, next_run_at: datetime) -> None: ...

    def delete(self, task_id: int) -> None: ...

    def delete_by_asset(self, asset_id: str) -> None: ...

    def delete_by_subscription(self, subscription_id: str) -> None: ...
