"""Budget REST routes — thin adapters over use cases."""
from decimal import Decimal

from fastapi import APIRouter, status

from flux_api.deps import get_db, get_uow
from flux_core.models.budget import BudgetOut
from flux_core.sqlite.budget_repo import SqliteBudgetRepository
from flux_core.use_cases.budgets.list_budgets import ListBudgets
from flux_core.use_cases.budgets.remove_budget import RemoveBudget
from flux_core.use_cases.budgets.set_budget import SetBudget

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def set_budget(
    user_id: str,
    category: str,
    monthly_limit: float,
) -> BudgetOut:
    """Set a budget limit for a category."""
    uc = SetBudget(get_uow())
    return await uc.execute(user_id, category, Decimal(str(monthly_limit)))


@router.get("/")
async def list_budgets(
    user_id: str,
) -> list[BudgetOut]:
    """List all budgets for a user."""
    db = get_db()
    repo = SqliteBudgetRepository(db.connection())
    uc = ListBudgets(repo)
    return await uc.execute(user_id)


@router.delete("/{category}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    category: str,
    user_id: str,
) -> None:
    """Delete a budget."""
    uc = RemoveBudget(get_uow())
    await uc.execute(user_id, category)
