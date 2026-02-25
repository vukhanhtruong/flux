from datetime import date
from decimal import Decimal

from flux_core.db.transaction_repo import TransactionRepository
from flux_core.db.budget_repo import BudgetRepository
from flux_core.db.goal_repo import GoalRepository
from flux_core.db.subscription_repo import SubscriptionRepository


async def generate_spending_report(
    user_id: str,
    start_date: str,
    end_date: str,
    txn_repo: TransactionRepository,
    sub_repo: SubscriptionRepository,
) -> dict:
    """Generate a spending report for a date range."""
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    summary = await txn_repo.get_summary(user_id, start, end)
    breakdown = await txn_repo.get_category_breakdown(user_id, start, end)
    subs = await sub_repo.list_by_user(user_id, active_only=True)

    total_income = summary["total_income"] or Decimal("0")
    total_expenses = summary["total_expenses"] or Decimal("0")
    net = total_income - total_expenses

    monthly_total = sum(
        (s.amount if s.billing_cycle == "monthly" else s.amount / 12)
        for s in subs
    )
    annual_total = monthly_total * 12

    return {
        "total_income": str(total_income),
        "total_expenses": str(total_expenses),
        "net": str(net),
        "count": summary["count"],
        "category_breakdown": [
            {"category": row["category"], "total": str(row["total"]), "count": row["count"]}
            for row in breakdown
        ],
        "start_date": start_date,
        "end_date": end_date,
        "subscriptions": {
            "active_count": len(subs),
            "monthly_total": str(round(monthly_total, 2)),
            "annual_total": str(round(annual_total, 2)),
            "items": [
                {
                    "name": s.name,
                    "amount": str(s.amount),
                    "billing_cycle": s.billing_cycle,
                    "category": s.category,
                    "next_date": str(s.next_date),
                }
                for s in subs
            ],
        },
    }


async def forecast_budget(
    user_id: str,
    category: str,
    days_elapsed: int,
    days_in_month: int,
    txn_repo: TransactionRepository,
    budget_repo: BudgetRepository,
) -> dict:
    """Forecast budget usage based on current spending rate."""
    from datetime import datetime

    # Get current month's spending
    today = datetime.now().date()
    start_of_month = today.replace(day=1)

    breakdown = await txn_repo.get_category_breakdown(user_id, start_of_month, today)
    spent_so_far = Decimal("0")
    for row in breakdown:
        if row["category"] == category:
            spent_so_far = row["total"]
            break

    # Get budget
    budget = await budget_repo.get_by_category(user_id, category)
    if not budget:
        return {"category": category, "error": "No budget set for this category"}

    # Calculate projection
    if days_elapsed > 0:
        daily_rate = spent_so_far / Decimal(str(days_elapsed))
        projected_total = daily_rate * Decimal(str(days_in_month))
    else:
        projected_total = Decimal("0")

    remaining_budget = budget.monthly_limit - spent_so_far
    status = "on_track"
    if projected_total > budget.monthly_limit:
        status = "over_budget"
    elif projected_total > budget.monthly_limit * Decimal("0.9"):
        status = "warning"

    return {
        "category": category,
        "budget_limit": str(budget.monthly_limit),
        "spent_so_far": str(spent_so_far),
        "projected_total": str(projected_total),
        "remaining_budget": str(remaining_budget),
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "status": status,
    }


async def calculate_financial_health(
    user_id: str,
    start_date: str,
    end_date: str,
    txn_repo: TransactionRepository,
    budget_repo: BudgetRepository,
    goal_repo: GoalRepository,
) -> dict:
    """Calculate a financial health score based on multiple factors."""
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    # Get summary data
    summary = await txn_repo.get_summary(user_id, start, end)
    total_income = summary["total_income"] or Decimal("0")
    total_expenses = summary["total_expenses"] or Decimal("0")

    # Calculate savings rate
    if total_income > 0:
        savings = total_income - total_expenses
        savings_rate = (savings / total_income) * 100
    else:
        savings_rate = Decimal("0")

    # Budget adherence (simplified - check if budgets exist)
    budgets = await budget_repo.list_by_user(user_id)
    budget_adherence = "good" if len(budgets) > 0 else "needs_budgets"

    # Goal progress
    goals = await goal_repo.list_by_user(user_id)
    if goals:
        total_target = sum(g.target_amount for g in goals)
        total_current = sum(g.current_amount for g in goals)
        goal_progress = (total_current / total_target * 100) if total_target > 0 else Decimal("0")
    else:
        goal_progress = Decimal("0")

    # Calculate overall score (0-100)
    score = Decimal("0")
    # Savings rate contributes 40%
    if savings_rate > 0:
        score += min(savings_rate, Decimal("40"))
    # Budget adherence contributes 30%
    if budget_adherence == "good":
        score += Decimal("30")
    # Goal progress contributes 30%
    score += min(goal_progress * Decimal("0.3"), Decimal("30"))

    return {
        "score": str(round(score, 2)),
        "income": str(total_income),
        "expenses": str(total_expenses),
        "savings_rate": str(round(savings_rate, 2)),
        "budget_adherence": budget_adherence,
        "goal_progress": str(round(goal_progress, 2)),
        "start_date": start_date,
        "end_date": end_date,
    }
