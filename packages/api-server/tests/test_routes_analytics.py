"""Test analytics REST routes."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_spending_report(client):
    """Test GET /analytics/spending-report returns report dict."""
    mock_summary = {
        "total_income": "5000.00",
        "total_expenses": "3000.00",
        "net": "2000.00",
        "count": 25,
    }
    mock_breakdown = [{"category": "food", "total": "1000.00"}]

    with (
        patch("flux_api.routes.analytics.get_db") as mock_get_db,
        patch("flux_api.routes.analytics.SqliteTransactionRepository"),
        patch("flux_api.routes.analytics.GetSummary") as MockSummary,
        patch("flux_api.routes.analytics.GetCategoryBreakdown") as MockBreakdown,
    ):
        mock_get_db.return_value = MagicMock()
        MockSummary.return_value.execute = AsyncMock(return_value=mock_summary)
        MockBreakdown.return_value.execute = AsyncMock(return_value=mock_breakdown)

        response = client.get(
            "/analytics/spending-report"
            "?user_id=user-1&start_date=2024-01-01&end_date=2024-01-31"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_income"] == "5000.00"
    assert "category_breakdown" in data


def test_financial_health(client):
    """Test GET /analytics/financial-health returns health score dict."""
    mock_summary = {"total_income": "5000.00", "total_expenses": "3000.00"}
    mock_breakdown = []

    with (
        patch("flux_api.routes.analytics.get_db") as mock_get_db,
        patch("flux_api.routes.analytics.SqliteTransactionRepository"),
        patch("flux_api.routes.analytics.GetSummary") as MockSummary,
        patch("flux_api.routes.analytics.GetCategoryBreakdown") as MockBreakdown,
    ):
        mock_get_db.return_value = MagicMock()
        MockSummary.return_value.execute = AsyncMock(return_value=mock_summary)
        MockBreakdown.return_value.execute = AsyncMock(return_value=mock_breakdown)

        response = client.get(
            "/analytics/financial-health"
            "?user_id=user-1&start_date=2024-01-01&end_date=2024-01-31"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 40
    assert data["savings_rate"] == pytest.approx(0.4)
    assert data["budget_adherence"] == 0.0
    assert data["goal_progress"] == 0.0
