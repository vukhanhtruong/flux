"""Analytics REST routes."""
from typing import Annotated

from fastapi import APIRouter, Depends

from flux_api.deps import get_db
from flux_core.db.connection import Database
from flux_core.db.transaction_repo import TransactionRepository
from flux_core.db.budget_repo import BudgetRepository
from flux_core.db.goal_repo import GoalRepository
from flux_core.db.subscription_repo import SubscriptionRepository
from flux_core.tools import analytics_tools

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/spending-report")
async def generate_spending_report(
    user_id: str,
    start_date: str,
    end_date: str,
    db: Annotated[Database, Depends(get_db)],
) -> dict:
    """Generate a spending report for a date range."""
    return await analytics_tools.generate_spending_report(
        user_id, start_date, end_date,
        TransactionRepository(db),
        SubscriptionRepository(db),
    )


@router.get("/financial-health")
async def calculate_financial_health(
    user_id: str,
    start_date: str,
    end_date: str,
    db: Annotated[Database, Depends(get_db)],
) -> dict:
    """Calculate a financial health score based on multiple factors."""
    return await analytics_tools.calculate_financial_health(
        user_id, start_date, end_date,
        TransactionRepository(db), BudgetRepository(db), GoalRepository(db),
    )
