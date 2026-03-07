"""ListTasks use case — list scheduled tasks (read-only)."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.repositories.bot.scheduled_task_repo import (
        BotScheduledTaskRepository,
    )


class ListTasks:
    """List all scheduled tasks for a user (read-only)."""

    def __init__(self, task_repo: BotScheduledTaskRepository):
        self._task_repo = task_repo

    async def execute(self, user_id: str) -> dict:
        tasks = self._task_repo.list_by_user(user_id)
        return {"tasks": tasks}
