"""SchedulerWorker — polls bot_scheduled_tasks and fires due tasks.

Due tasks are injected as synthetic bot_messages so the existing
Poller → UserQueue → ClaudeRunner pipeline handles them normally.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from croniter import croniter

from flux_bot.db.messages import MessageRepository
from flux_bot.db.scheduled_tasks import ScheduledTaskRepository
from flux_bot.orchestrator.outbound import parse_channel_prefix

logger = logging.getLogger(__name__)


class SchedulerWorker:
    def __init__(
        self,
        task_repo: ScheduledTaskRepository,
        message_repo: MessageRepository,
        poll_interval: float = 30.0,
    ):
        self.task_repo = task_repo
        self.message_repo = message_repo
        self.poll_interval = poll_interval
        self._running = False

    async def start(self) -> None:
        """Start the scheduler loop."""
        self._running = True
        logger.info(f"SchedulerWorker started (poll_interval={self.poll_interval}s)")
        while self._running:
            try:
                await self._fire_once()
            except Exception:
                logger.exception("Error in scheduler cycle")
            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        self._running = False

    async def _fire_once(self) -> None:
        """Fetch due tasks and inject each as a synthetic bot_message."""
        tasks = await self.task_repo.fetch_due_tasks()
        for task in tasks:
            await self._fire_task(task)

    async def _fire_task(self, task: dict) -> None:
        channel_name, platform_id = parse_channel_prefix(task["user_id"])
        if channel_name is None:
            logger.warning(
                f"Skipping task {task['id']}: unrecognized user_id prefix '{task['user_id']}'"
            )
            return

        try:
            await self.message_repo.insert(
                user_id=task["user_id"],
                channel=channel_name,
                platform_id=platform_id,
                text=task["prompt"],
            )
        except Exception:
            logger.exception(f"Failed to inject message for task {task['id']}")
            return

        if task["schedule_type"] == "once":
            await self.task_repo.mark_completed(task["id"])
        else:
            next_run = None
            if task.get("subscription_id"):
                # Keep subscription schedule in sync with subscriptions.next_date.
                next_run = await self.task_repo.get_subscription_next_run(task["id"])
            if next_run is None:
                next_run = self._compute_next_run(
                    task["schedule_type"], task["schedule_value"], task.get("user_timezone", "UTC")
                )
            await self.task_repo.advance_next_run(task["id"], next_run)
        logger.info(f"Fired task {task['id']} ({task['schedule_type']}) for {task['user_id']}")

    def _compute_next_run(
        self, schedule_type: str, schedule_value: str, user_timezone: str = "UTC"
    ) -> datetime:
        if schedule_type == "cron":
            now_local = datetime.now(ZoneInfo(user_timezone))
            return croniter(schedule_value, now_local).get_next(datetime).astimezone(UTC)
        # interval: schedule_value is milliseconds
        ms = int(schedule_value)
        return datetime.now(UTC) + timedelta(milliseconds=ms)
