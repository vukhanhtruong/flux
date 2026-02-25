"""Tests for MCP resource functions using mocked repositories."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from flux_core.models.transaction import TransactionOut, TransactionType
from flux_core.models.budget import BudgetOut
from flux_mcp.resources import get_recent_transactions, get_budget_summary


async def test_get_recent_transactions():
    transaction = TransactionOut(
        id=uuid4(),
        user_id="user1",
        date=date(2024, 1, 15),
        amount=Decimal("50.00"),
        category="Food",
        description="Lunch",
        type=TransactionType.expense,
        is_recurring=False,
        tags=[],
        created_at=datetime(2024, 1, 15, 12, 0, 0),
    )
    mock_repo = AsyncMock()
    mock_repo.list_by_user.return_value = [transaction]

    result = await get_recent_transactions("user1", mock_repo, limit=10)

    assert "recent_transactions" in result
    assert len(result["recent_transactions"]) == 1
    mock_repo.list_by_user.assert_awaited_once_with("user1", limit=10)


async def test_get_budget_summary():
    budget = BudgetOut(
        id=uuid4(),
        user_id="user1",
        category="Food",
        monthly_limit=Decimal("500.00"),
    )
    mock_repo = AsyncMock()
    mock_repo.list_by_user.return_value = [budget]

    result = await get_budget_summary("user1", mock_repo)

    assert "budgets" in result
    assert len(result["budgets"]) == 1
    mock_repo.list_by_user.assert_awaited_once_with("user1")
