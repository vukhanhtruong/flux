"""IPC tools — send messages and manage scheduled tasks via PostgreSQL."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from croniter import croniter

from flux_core.db.connection import Database
from flux_core.db.user_profile_repo import UserProfileRepository


async def send_message(
    user_id: str,
    text: str,
    sender: str | None = None,
    *,
    db: Database,
) -> dict:
    """Queue an outbound message for delivery to the user's channel."""
    msg_id = await db.fetchval(
        """
        INSERT INTO bot_outbound_messages (user_id, text, sender)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        user_id, text, sender,
    )
    return {"status": "sent", "message_id": msg_id}


async def schedule_task(
    user_id: str,
    prompt: str,
    schedule_type: str,
    schedule_value: str,
    db: Database,
) -> dict:
    """Schedule a recurring or one-time task."""
    profile = await UserProfileRepository(db).get_by_user_id(user_id)
    user_tz = ZoneInfo(profile.timezone) if profile else ZoneInfo("UTC")

    if schedule_type == "cron":
        if not croniter.is_valid(schedule_value):
            return {
                "status": "error",
                "message": f'Invalid cron: "{schedule_value}". '
                'Use format like "0 9 * * *" (daily 9am) or "*/5 * * * *" (every 5 min).',
            }
        now_local = datetime.now(user_tz)
        next_run = croniter(schedule_value, now_local).get_next(datetime).astimezone(UTC)
    elif schedule_type == "interval":
        try:
            ms = int(schedule_value)
        except ValueError:
            return {
                "status": "error",
                "message": f'Invalid interval: "{schedule_value}". '
                'Must be a whole number of milliseconds (e.g., "300000" for 5 min).',
            }
        if ms <= 0:
            return {
                "status": "error",
                "message": f'Interval must be positive, got {ms}ms. '
                'Use a value like "300000" for 5 minutes.',
            }
        next_run = None
    elif schedule_type == "once":
        try:
            naive_dt = datetime.fromisoformat(schedule_value)
            next_run = naive_dt.replace(tzinfo=user_tz).astimezone(UTC)
        except ValueError:
            return {
                "status": "error",
                "message": f'Invalid timestamp: "{schedule_value}". '
                'Use ISO 8601 format like "2026-02-01T15:30:00".',
            }
    else:
        return {"status": "error", "message": f"Unknown schedule_type: {schedule_type}"}

    task_id = await db.fetchval(
        """
        INSERT INTO bot_scheduled_tasks (user_id, prompt, schedule_type, schedule_value, next_run_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        user_id, prompt, schedule_type, schedule_value, next_run,
    )
    return {"status": "scheduled", "task_id": task_id}


async def list_tasks(user_id: str, db: Database) -> dict:
    """List all scheduled tasks for the user."""
    rows = await db.fetch(
        """
        SELECT id, prompt, schedule_type, schedule_value, status, next_run_at, created_at
        FROM bot_scheduled_tasks
        WHERE user_id = $1
        ORDER BY created_at
        """,
        user_id,
    )
    return {"tasks": [dict(r) for r in rows]}


async def pause_task(user_id: str, task_id: int, db: Database) -> dict:
    """Pause a scheduled task."""
    result = await db.execute(
        """
        UPDATE bot_scheduled_tasks SET status = 'paused'
        WHERE id = $1 AND user_id = $2 AND status = 'active'
        """,
        task_id, user_id,
    )
    if result == "UPDATE 0":
        return {"status": "error", "message": f"Task {task_id} not found or not active."}
    return {"status": "paused", "task_id": task_id}


async def resume_task(user_id: str, task_id: int, db: Database) -> dict:
    """Resume a paused task."""
    result = await db.execute(
        """
        UPDATE bot_scheduled_tasks SET status = 'active'
        WHERE id = $1 AND user_id = $2 AND status = 'paused'
        """,
        task_id, user_id,
    )
    if result == "UPDATE 0":
        return {"status": "error", "message": f"Task {task_id} not found or not paused."}
    return {"status": "resumed", "task_id": task_id}


async def cancel_task(user_id: str, task_id: int, db: Database) -> dict:
    """Cancel and delete a scheduled task."""
    result = await db.execute(
        "DELETE FROM bot_scheduled_tasks WHERE id = $1 AND user_id = $2",
        task_id, user_id,
    )
    if result == "DELETE 0":
        return {"status": "error", "message": f"Task {task_id} not found."}
    return {"status": "cancelled", "task_id": task_id}
