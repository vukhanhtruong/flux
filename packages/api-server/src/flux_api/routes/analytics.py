"""Analytics REST routes — thin adapters over use cases."""
from datetime import date

from fastapi import APIRouter

from flux_api.deps import get_db
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository
from flux_core.use_cases.analytics.get_category_breakdown import GetCategoryBreakdown
from flux_core.use_cases.analytics.get_summary import GetSummary

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

    summary_uc = GetSummary(repo)
    summary = await summary_uc.execute(user_id, sd, ed)

    breakdown_uc = GetCategoryBreakdown(repo)
    breakdown = await breakdown_uc.execute(user_id, sd, ed)

    return {
        **summary,
        "category_breakdown": breakdown,
    }


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

    summary_uc = GetSummary(repo)
    summary = await summary_uc.execute(user_id, sd, ed)

    breakdown_uc = GetCategoryBreakdown(repo)
    breakdown = await breakdown_uc.execute(user_id, sd, ed)

    return {
        "summary": summary,
        "category_breakdown": breakdown,
        "period": {"start": start_date, "end": end_date},
    }
