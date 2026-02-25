"""Budget REST routes."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from flux_api.deps import get_db
from flux_core.db.connection import Database
from flux_core.db.budget_repo import BudgetRepository
from flux_core.models.budget import BudgetSet, BudgetOut

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def set_budget(
    budget: BudgetSet,
    db: Annotated[Database, Depends(get_db)],
) -> BudgetOut:
    """Set a budget limit for a category."""
    repo = BudgetRepository(db)
    created = await repo.set_budget(budget)
    return created


@router.get("/")
async def list_budgets(
    user_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> list[BudgetOut]:
    """List all budgets for a user."""
    repo = BudgetRepository(db)
    budgets = await repo.list_by_user(user_id)
    return budgets


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: str,
    user_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> None:
    """Delete a budget."""
    repo = BudgetRepository(db)
    await repo.delete(UUID(budget_id), user_id)
