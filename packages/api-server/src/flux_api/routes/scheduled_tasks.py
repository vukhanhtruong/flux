"""Scheduled task REST routes — thin adapter over ListTasks use case."""
from fastapi import APIRouter

from flux_api.deps import get_db
from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository
from flux_core.use_cases.bot.list_tasks import ListTasks

router = APIRouter(prefix="/scheduled-tasks", tags=["scheduled-tasks"])


@router.get("/")
async def list_scheduled_tasks(user_id: str) -> dict:
    """List all active scheduled tasks for a user."""
    db = get_db()
    repo = SqliteBotScheduledTaskRepository(db.connection())
    uc = ListTasks(repo)
    return await uc.execute(user_id)
