from typing import Callable, Awaitable

from fastmcp import FastMCP
from flux_core.db.connection import Database
from flux_core.tools import ipc_tools as biz


def register_ipc_tools(
    mcp: FastMCP,
    get_db: Callable[[], Awaitable[Database]],
    get_user_id: Callable[[], str],
):
    @mcp.tool()
    async def send_message(text: str, sender: str | None = None) -> dict:
        """Send a message to the user immediately, without waiting until you finish.
        Use for progress updates on long tasks or to stream multiple messages.
        Your final response is always sent automatically — call this only when
        you need to deliver information before you finish, not as a substitute
        for your final reply."""
        db = await get_db()
        return await biz.send_message(get_user_id(), text, sender, db=db)

    @mcp.tool()
    async def schedule_task(
        prompt: str,
        schedule_type: str,
        schedule_value: str,
    ) -> dict:
        """Schedule a recurring or one-time task. The task runs as a full agent.

        schedule_type: "cron" | "interval" | "once"
        schedule_value:
          - cron: "0 9 * * *" (daily 9am), "*/5 * * * *" (every 5 min)
          - interval: milliseconds like "300000" (5 min), "3600000" (1 hour)
          - once: local timestamp like "2026-02-01T15:30:00" (no Z suffix).
                  For relative requests ("in 2 minutes"), add the offset to the
                  current date/time from your system context.
        """
        db = await get_db()
        return await biz.schedule_task(
            get_user_id(), prompt, schedule_type, schedule_value, db,
        )

    @mcp.tool()
    async def list_scheduled_tasks() -> dict:
        """List all your scheduled tasks."""
        db = await get_db()
        return await biz.list_tasks(get_user_id(), db)

    @mcp.tool()
    async def pause_scheduled_task(task_id: int) -> dict:
        """Pause a scheduled task. It will not run until resumed."""
        db = await get_db()
        return await biz.pause_task(get_user_id(), task_id, db)

    @mcp.tool()
    async def resume_scheduled_task(task_id: int) -> dict:
        """Resume a paused scheduled task."""
        db = await get_db()
        return await biz.resume_task(get_user_id(), task_id, db)

    @mcp.tool()
    async def cancel_scheduled_task(task_id: int) -> dict:
        """Cancel and delete a scheduled task."""
        db = await get_db()
        return await biz.cancel_task(get_user_id(), task_id, db)
