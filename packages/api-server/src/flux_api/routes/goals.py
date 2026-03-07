"""Goal REST routes — thin adapters over use cases."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from flux_api.deps import get_db, get_uow
from flux_core.models.goal import GoalOut
from flux_core.sqlite.goal_repo import SqliteGoalRepository
from flux_core.use_cases.goals.create_goal import CreateGoal
from flux_core.use_cases.goals.delete_goal import DeleteGoal
from flux_core.use_cases.goals.deposit_to_goal import DepositToGoal
from flux_core.use_cases.goals.list_goals import ListGoals

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_goal(
    user_id: str,
    name: str,
    target_amount: float,
    deadline: str | None = None,
    color: str = "#3B82F6",
) -> GoalOut:
    """Create a financial goal."""
    uc = CreateGoal(get_uow())
    dl = date.fromisoformat(deadline) if deadline else None
    return await uc.execute(user_id, name, Decimal(str(target_amount)), deadline=dl, color=color)


@router.get("/")
async def list_goals(
    user_id: str,
) -> list[GoalOut]:
    """List all goals for a user."""
    db = get_db()
    repo = SqliteGoalRepository(db.connection())
    uc = ListGoals(repo)
    return await uc.execute(user_id)


@router.post("/{goal_id}/deposit")
async def deposit_to_goal(
    goal_id: str,
    user_id: str,
    amount: float,
) -> GoalOut:
    """Deposit money into a goal."""
    uc = DepositToGoal(get_uow())
    try:
        return await uc.execute(UUID(goal_id), user_id, Decimal(str(amount)))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: str,
    user_id: str,
) -> None:
    """Delete a goal."""
    uc = DeleteGoal(get_uow())
    await uc.execute(UUID(goal_id), user_id)
