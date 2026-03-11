"""Scheduled task REST routes — thin adapter over use cases."""
from fastapi import APIRouter, HTTPException, status

from flux_api.deps import get_db, get_uow
from flux_core.sqlite.bot.scheduled_task_repo import SqliteBotScheduledTaskRepository
from flux_core.use_cases.bot.cancel_task import CancelTask
from flux_core.use_cases.bot.list_tasks import ListTasks

router = APIRouter(prefix="/scheduled-tasks", tags=["scheduled-tasks"])


@router.get("/")
async def list_scheduled_tasks(user_id: str) -> dict:
    """List all active scheduled tasks for a user."""
    db = get_db()
    repo = SqliteBotScheduledTaskRepository(db.connection())
    uc = ListTasks(repo)
    return await uc.execute(user_id)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_task(task_id: int, user_id: str) -> None:
    """Cancel and delete a scheduled task."""
    uc = CancelTask(get_uow())
    result = await uc.execute(user_id, task_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result["message"])
