"""Analytics REST routes — thin adapters over use cases."""
from datetime import date

from fastapi import APIRouter

from flux_api.deps import get_db
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository
from flux_core.use_cases.analytics.calculate_financial_health import CalculateFinancialHealth
from flux_core.use_cases.analytics.generate_spending_report import GenerateSpendingReport

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/spending-report")
async def generate_spending_report(
    user_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Generate a spending report for a date range."""
    db = get_db()
    repo = SqliteTransactionRepository(db.connection())
    sd = date.fromisoformat(start_date)
    ed = date.fromisoformat(end_date)
    uc = GenerateSpendingReport(repo)
    return await uc.execute(user_id, sd, ed)


@router.get("/financial-health")
async def calculate_financial_health(
    user_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Calculate a financial health score based on multiple factors."""
    db = get_db()
    repo = SqliteTransactionRepository(db.connection())
    sd = date.fromisoformat(start_date)
    ed = date.fromisoformat(end_date)
    uc = CalculateFinancialHealth(repo)
    return await uc.execute(user_id, sd, ed)
