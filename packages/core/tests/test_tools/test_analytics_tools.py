from decimal import Decimal
from unittest.mock import AsyncMock
import pytest

from flux_core.tools.analytics_tools import (
    generate_spending_report,
    forecast_budget,
    calculate_financial_health,
)


async def test_generate_spending_report():
    mock_txn_repo = AsyncMock()
    mock_txn_repo.get_summary.return_value = {
        "total_income": Decimal("5000.00"),
        "total_expenses": Decimal("3000.00"),
        "count": 25,
    }
    mock_txn_repo.get_category_breakdown.return_value = [
        {"category": "Food", "total": Decimal("800.00"), "count": 10},
        {"category": "Transport", "total": Decimal("400.00"), "count": 5},
    ]

    result = await generate_spending_report(
        user_id="test_user",
        start_date="2026-01-01",
        end_date="2026-01-31",
        txn_repo=mock_txn_repo,
    )

    assert result["total_income"] == "5000.00"
    assert result["total_expenses"] == "3000.00"
    assert result["net"] == "2000.00"
    assert result["count"] == 25
    assert len(result["category_breakdown"]) == 2
    assert result["category_breakdown"][0]["category"] == "Food"
    assert "subscriptions" not in result
    mock_txn_repo.get_summary.assert_called_once()
    mock_txn_repo.get_category_breakdown.assert_called_once()


@pytest.mark.asyncio
async def test_forecast_budget():
    mock_txn_repo = AsyncMock()
    mock_budget_repo = AsyncMock()

    # Mock transaction history
    mock_txn_repo.get_category_breakdown.return_value = [
        {"category": "Food", "total": Decimal("800.00"), "count": 10}
    ]

    # Mock budget
    mock_budget_repo.get_by_category.return_value = type('Budget', (), {
        'monthly_limit': Decimal("1000.00"),
        'category': "Food"
    })()

    result = await forecast_budget(
        user_id="test_user",
        category="Food",
        days_elapsed=10,
        days_in_month=30,
        txn_repo=mock_txn_repo,
        budget_repo=mock_budget_repo
    )

    assert result["category"] == "Food"
    assert result["budget_limit"] == "1000.00"
    assert result["spent_so_far"] == "800.00"
    assert "projected_total" in result
    assert "remaining_budget" in result
    assert "status" in result


@pytest.mark.asyncio
async def test_calculate_financial_health():
    mock_txn_repo = AsyncMock()
    mock_budget_repo = AsyncMock()
    mock_goal_repo = AsyncMock()

    # Mock summary data
    mock_txn_repo.get_summary.return_value = {
        "total_income": Decimal("5000.00"),
        "total_expenses": Decimal("3000.00"),
        "count": 25
    }
    mock_budget_repo.list_by_user.return_value = []
    mock_goal_repo.list_by_user.return_value = [
        type('Goal', (), {
            'target_amount': Decimal("5000.00"),
            'current_amount': Decimal("2000.00")
        })()
    ]

    result = await calculate_financial_health(
        user_id="test_user",
        start_date="2026-01-01",
        end_date="2026-01-31",
        txn_repo=mock_txn_repo,
        budget_repo=mock_budget_repo,
        goal_repo=mock_goal_repo
    )

    assert "score" in result
    assert "income" in result
    assert "expenses" in result
    assert "savings_rate" in result
    assert "budget_adherence" in result
    assert "goal_progress" in result
    assert result["income"] == "5000.00"
    assert result["expenses"] == "3000.00"
