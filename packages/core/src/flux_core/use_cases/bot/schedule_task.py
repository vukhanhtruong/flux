"""ScheduleTask use case — schedule a recurring or one-time task.

This is the IPC version that validates schedule_type/schedule_value
and computes next_run_at, then delegates to CreateScheduledTask.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from croniter import croniter

from flux_core.events.events import ScheduledTaskCreated
from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo

    from flux_core.uow.unit_of_work import UnitOfWork


class ScheduleTask:
    """Schedule a recurring or one-time task with validation."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(
        self,
        user_id: str,
        prompt: str,
        schedule_type: str,
        schedule_value: str,
        *,
        user_tz: ZoneInfo | None = None,
    ) -> dict:
        from zoneinfo import ZoneInfo as ZI

        tz = user_tz or ZI("UTC")

        if schedule_type == "cron":
            if not croniter.is_valid(schedule_value):
                return {
                    "status": "error",
                    "message": (
                        f'Invalid cron: "{schedule_value}". '
                        'Use format like "0 9 * * *" (daily 9am).'
                    ),
                }
            now_local = datetime.now(tz)
            next_run = croniter(schedule_value, now_local).get_next(datetime)
            next_run = next_run.astimezone(UTC)

        elif schedule_type == "interval":
            try:
                ms = int(schedule_value)
            except ValueError:
                return {
                    "status": "error",
                    "message": (
                        f'Invalid interval: "{schedule_value}". '
                        "Must be a whole number of milliseconds."
                    ),
                }
            if ms <= 0:
                return {
                    "status": "error",
                    "message": f"Interval must be positive, got {ms}ms.",
                }
            next_run = datetime.now(UTC) + timedelta(milliseconds=ms)

        elif schedule_type == "once":
            if schedule_value.isdigit():
                ms = int(schedule_value)
                if ms <= 0:
                    return {"status": "error", "message": "Delay must be positive."}
                next_run = datetime.now(UTC) + timedelta(milliseconds=ms)
            else:
                try:
                    naive_dt = datetime.fromisoformat(schedule_value)
                    next_run = naive_dt.replace(tzinfo=tz).astimezone(UTC)
                except ValueError:
                    return {
                        "status": "error",
                        "message": (
                            f'Invalid timestamp: "{schedule_value}". '
                            "Use ISO 8601 format."
                        ),
                    }
                if next_run <= datetime.now(UTC):
                    return {
                        "status": "error",
                        "message": (
                            f'Scheduled time "{schedule_value}" is in the past.'
                        ),
                    }
        else:
            return {
                "status": "error",
                "message": f"Unknown schedule_type: {schedule_type}",
            }

        async with self._uow:
            repo = SqliteBotScheduledTaskRepository(self._uow.conn)
            task_id = repo.create(
                user_id=user_id,
                prompt=prompt,
                schedule_type=schedule_type,
                schedule_value=schedule_value,
                next_run_at=next_run,
            )
            self._uow.add_event(
                ScheduledTaskCreated(
                    timestamp=datetime.now(UTC),
                    task_id=task_id,
                    user_id=user_id,
                )
            )
            await self._uow.commit()

        return {"status": "scheduled", "task_id": task_id}
