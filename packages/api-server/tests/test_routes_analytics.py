"""Test analytics REST routes."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app
from flux_api.deps import get_db, get_embedding_service
from flux_core.db.transaction_repo import TransactionRepository
from flux_core.db.budget_repo import BudgetRepository
from flux_core.db.goal_repo import GoalRepository


@pytest.fixture
def mock_txn_repo():
    """Mock transaction repository."""
    return AsyncMock(spec=TransactionRepository)


@pytest.fixture
def mock_budget_repo():
    """Mock budget repository."""
    return AsyncMock(spec=BudgetRepository)


@pytest.fixture
def mock_goal_repo():
    """Mock goal repository."""
    return AsyncMock(spec=GoalRepository)


@pytest.fixture
def mock_db():
    """Mock database connection."""
    return MagicMock()


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    service = MagicMock()
    service.embed_text.return_value = [0.1] * 384
    return service


@pytest.fixture
def client(mock_db, mock_embedding_service):
    """Test client with mocked dependencies."""

    async def override_get_db():
        yield mock_db

    def override_get_embedding_service():
        return mock_embedding_service

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_embedding_service] = override_get_embedding_service

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_spending_report(client, mock_txn_repo):
    """Test GET /analytics/spending-report returns report dict."""
    expected = {
        "period": {"start": "2024-01-01", "end": "2024-01-31"},
        "total_expenses": "500.00",
        "by_category": {"groceries": "200.00", "transport": "300.00"},
    }

    with patch(
        "flux_api.routes.analytics.TransactionRepository",
        return_value=mock_txn_repo,
    ), patch(
        "flux_api.routes.analytics.analytics_tools.generate_spending_report",
        new=AsyncMock(return_value=expected),
    ):
        response = client.get(
            "/analytics/spending-report?user_id=user-1&start_date=2024-01-01&end_date=2024-01-31"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["period"]["start"] == "2024-01-01"
    assert data["total_expenses"] == "500.00"
    assert "groceries" in data["by_category"]


def test_financial_health(client, mock_txn_repo, mock_budget_repo, mock_goal_repo):
    """Test GET /analytics/financial-health returns health score dict."""
    expected = {
        "score": 78,
        "grade": "B+",
        "factors": {
            "savings_rate": 0.2,
            "budget_adherence": 0.85,
        },
    }

    with patch(
        "flux_api.routes.analytics.TransactionRepository",
        return_value=mock_txn_repo,
    ), patch(
        "flux_api.routes.analytics.BudgetRepository",
        return_value=mock_budget_repo,
    ), patch(
        "flux_api.routes.analytics.GoalRepository",
        return_value=mock_goal_repo,
    ), patch(
        "flux_api.routes.analytics.analytics_tools.calculate_financial_health",
        new=AsyncMock(return_value=expected),
    ):
        response = client.get(
            "/analytics/financial-health?user_id=user-1&start_date=2024-01-01&end_date=2024-01-31"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 78
    assert data["grade"] == "B+"
    assert "savings_rate" in data["factors"]
