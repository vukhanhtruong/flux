from typing import Callable

from fastmcp import FastMCP

_MAX_PROMPT_LENGTH = 2000

_BLOCKED_PHRASES = [
    "ignore instructions",
    "ignore previous",
    "ignore your",
    "override",
    "system prompt",
    "forget rules",
    "forget your",
    "disregard",
    "new instructions",
    "change your behavior",
    "act as",
    "pretend you",
    "you are now",
]
from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.bot.cancel_task import CancelTask
from flux_core.use_cases.bot.list_tasks import ListTasks
from flux_core.use_cases.bot.pause_task import PauseTask
from flux_core.use_cases.bot.resume_task import ResumeTask
from flux_core.use_cases.bot.schedule_task import ScheduleTask
from flux_core.use_cases.bot.send_message import SendMessage


def register_ipc_tools(
    mcp: FastMCP,
    get_uow: Callable[[], UnitOfWork],
    get_user_id: Callable[[], str],
    get_user_timezone: Callable[[], str],
):
    @mcp.tool()
    async def send_message(text: str, sender: str | None = None) -> dict:
        """Send a message to the user immediately, without waiting until you finish.
        Use for progress updates on long tasks or to stream multiple messages.
        Your final response is always sent automatically — call this only when
        you need to deliver information before you finish, not as a substitute
        for your final reply."""
        uc = SendMessage(get_uow())
        return await uc.execute(get_user_id(), text, sender=sender)

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
          - once: for relative delays ("in 5 min"), use milliseconds like "300000".
                  For absolute times, use local timestamp like "2026-02-01T15:30:00" (no Z suffix).
        """
        # Validate prompt length
        if len(prompt) > _MAX_PROMPT_LENGTH:
            return {
                "status": "error",
                "error": f"Prompt too long ({len(prompt)} chars). Maximum is {_MAX_PROMPT_LENGTH} characters.",
            }

        # Check for injection keywords
        prompt_lower = prompt.lower()
        for phrase in _BLOCKED_PHRASES:
            if phrase in prompt_lower:
                return {
                    "status": "error",
                    "error": "Prompt contains prohibited phrase. Scheduled task prompts must describe financial operations only.",
                }

        from zoneinfo import ZoneInfo
        tz = ZoneInfo(get_user_timezone())
        uc = ScheduleTask(get_uow())
        return await uc.execute(
            get_user_id(), prompt, schedule_type, schedule_value, user_tz=tz,
        )

    @mcp.tool()
    async def list_scheduled_tasks() -> dict:
        """List all your scheduled tasks."""
        from datetime import UTC, datetime
        from zoneinfo import ZoneInfo

        from flux_mcp.server import get_db

        db = get_db()
        repo = SqliteBotScheduledTaskRepository(db.connection())
        uc = ListTasks(repo)
        result = await uc.execute(get_user_id())

        tz = ZoneInfo(get_user_timezone())
        _DT_FIELDS = ("next_run_at", "last_run_at", "created_at")
        for task in result.get("tasks", []):
            for field in _DT_FIELDS:
                val = task.get(field)
                if not val:
                    continue
                utc_dt = datetime.strptime(val, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
                task[field] = utc_dt.astimezone(tz).strftime("%Y-%m-%dT%H:%M:%S%z")

        return result

    @mcp.tool()
    async def pause_scheduled_task(task_id: int) -> dict:
        """Pause a scheduled task. It will not run until resumed."""
        uc = PauseTask(get_uow())
        return await uc.execute(get_user_id(), task_id)

    @mcp.tool()
    async def resume_scheduled_task(task_id: int) -> dict:
        """Resume a paused scheduled task."""
        uc = ResumeTask(get_uow())
        return await uc.execute(get_user_id(), task_id)

    @mcp.tool()
    async def cancel_scheduled_task(task_id: int) -> dict:
        """Cancel and delete a scheduled task."""
        uc = CancelTask(get_uow())
        return await uc.execute(get_user_id(), task_id)
