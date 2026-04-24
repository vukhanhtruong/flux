"""Bot IPC tools for the deepagents runner.

Each tool wraps an existing ``flux_core`` Use Case with ``user_id`` closed
over. The model sees these tools and never sees ``user_id`` as an argument,
so cross-user queries are structurally impossible.

Mirrors the IPC subset of the MCP-side surface in
``packages/mcp-server/src/flux_mcp/tools/ipc_tools.py`` — the shape
of tool inputs/outputs is intentionally identical so the model experiences
the same contract regardless of host.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool, StructuredTool

from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.bot.cancel_task import CancelTask
from flux_core.use_cases.bot.list_tasks import ListTasks
from flux_core.use_cases.bot.schedule_task import ScheduleTask
from flux_core.use_cases.bot.send_message import SendMessage

if TYPE_CHECKING:
    from flux_core.sqlite.database import Database


def build_bot_tools(*, user_id: str, db: Database) -> list[BaseTool]:
    """Return the bot IPC tool set bound to a specific user.

    Args:
        user_id: The user identity closed over by every tool. Never
            exposed as a tool argument — guarantees isolation.
        db: Connected core ``Database`` (SQLite, WAL mode).
    """

    async def send_outbound_message(
        text: str, sender: str | None = None
    ) -> dict:
        """Send a message to the user immediately, without waiting until you finish.

        Use for progress updates on long tasks or to stream multiple messages.
        Your final response is always sent automatically — call this only when
        you need to deliver information before you finish, not as a substitute
        for your final reply.

        Args:
            text: The message text to send to the user.
            sender: Optional label identifying the message source (e.g.
                "scheduler"). Usually omitted.

        Returns:
            Dict with status ("sent") and message_id.
        """
        uow = UnitOfWork(db)
        uc = SendMessage(uow)
        return await uc.execute(user_id, text, sender=sender)

    async def schedule_task(
        prompt: str,
        schedule_type: str,
        schedule_value: str,
    ) -> dict:
        """Schedule a recurring or one-time task. The task runs as a full agent.

        schedule_type must be one of "cron", "interval", or "once".

        schedule_value format:
          - cron: standard cron expression, e.g. "0 9 * * *" (daily 9am)
          - interval: milliseconds as a whole number, e.g. "3600000" (1 hour)
          - once: milliseconds for a relative delay, e.g. "300000" (5 min),
              or a local ISO timestamp like "2026-02-01T15:30:00" (no Z suffix)

        Args:
            prompt: Task description the agent will run, max 2000 characters.
            schedule_type: "cron", "interval", or "once".
            schedule_value: Schedule expression (see format above).

        Returns:
            Dict with status ("scheduled" or "error") and task_id on success.
        """
        uow = UnitOfWork(db)
        uc = ScheduleTask(uow)
        return await uc.execute(user_id, prompt, schedule_type, schedule_value)

    async def list_tasks() -> dict:
        """List all scheduled tasks for the current user.

        Returns:
            Dict with a "tasks" list, each entry containing id, prompt,
            schedule_type, schedule_value, next_run_at, last_run_at,
            created_at, and status.
        """
        repo = SqliteBotScheduledTaskRepository(db.connection())
        uc = ListTasks(repo)
        return await uc.execute(user_id)

    async def cancel_task(task_id: int) -> dict:
        """Cancel and delete a scheduled task.

        Args:
            task_id: Integer ID of the task to cancel (from list_tasks).

        Returns:
            Dict with status ("cancelled" or "error") and task_id.
        """
        uow = UnitOfWork(db)
        uc = CancelTask(uow)
        return await uc.execute(user_id, task_id)

    return [
        StructuredTool.from_function(
            coroutine=send_outbound_message,
            name="send_outbound_message",
            description=send_outbound_message.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=schedule_task,
            name="schedule_task",
            description=schedule_task.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=list_tasks,
            name="list_tasks",
            description=list_tasks.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=cancel_task,
            name="cancel_task",
            description=cancel_task.__doc__ or "",
        ),
    ]
