"""MCP Resources for flux.

Resources are data endpoints that can be queried by MCP clients.
"""

from flux_core.db.transaction_repo import TransactionRepository
from flux_core.db.budget_repo import BudgetRepository


async def get_recent_transactions(
    user_id: str,
    repo: TransactionRepository,
    limit: int = 10
) -> dict:
    """Get recent transactions for a user.

    This resource provides a snapshot of recent financial activity.
    """
    transactions = await repo.list_by_user(user_id, limit=limit)

    return {
        "recent_transactions": [
            {
                "id": str(t.id),
                "date": str(t.date),
                "amount": str(t.amount),
                "category": t.category,
                "description": t.description,
                "type": t.type.value,
                "is_recurring": t.is_recurring,
                "tags": t.tags
            }
            for t in transactions
        ]
    }


async def get_budget_summary(
    user_id: str,
    repo: BudgetRepository
) -> dict:
    """Get budget summary for a user.

    This resource provides an overview of all budget limits.
    """
    budgets = await repo.list_by_user(user_id)

    return {
        "budgets": [
            {
                "id": str(b.id),
                "category": b.category,
                "monthly_limit": str(b.monthly_limit)
            }
            for b in budgets
        ]
    }
