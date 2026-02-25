"""Goal REST routes."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from flux_api.deps import get_db
from flux_core.db.connection import Database
from flux_core.db.goal_repo import GoalRepository
from flux_core.models.goal import GoalCreate, GoalOut, GoalUpdate

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_goal(
    goal: GoalCreate,
    db: Annotated[Database, Depends(get_db)],
) -> GoalOut:
    """Create a financial goal."""
    repo = GoalRepository(db)
    created = await repo.create(goal)
    return created


@router.get("/")
async def list_goals(
    user_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> list[GoalOut]:
    """List all goals for a user."""
    repo = GoalRepository(db)
    goals = await repo.list_by_user(user_id)
    return goals


@router.patch("/{goal_id}")
async def update_goal(
    goal_id: str,
    user_id: str,
    updates: GoalUpdate,
    db: Annotated[Database, Depends(get_db)],
) -> GoalOut:
    """Update a goal's progress or details."""
    repo = GoalRepository(db)
    updated = await repo.update(UUID(goal_id), user_id, updates)
    return updated


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: str,
    user_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> None:
    """Delete a goal."""
    repo = GoalRepository(db)
    await repo.delete(UUID(goal_id), user_id)
