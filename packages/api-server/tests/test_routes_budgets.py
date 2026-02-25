"""Test budget REST routes."""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app
from flux_api.deps import get_db, get_embedding_service
from flux_core.db.budget_repo import BudgetRepository
from flux_core.models.budget import BudgetOut


@pytest.fixture
def mock_repo():
    """Mock budget repository (no spec — route calls set_budget/delete which differ from repo internals)."""
    return AsyncMock()


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


def test_set_budget(client, mock_repo):
    """Test POST /budgets/ creates a budget and returns 201."""
    mock_budget = BudgetOut(
        id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        user_id="user-1",
        category="groceries",
        monthly_limit=Decimal("400.00"),
    )
    mock_repo.set_budget.return_value = mock_budget

    with patch(
        "flux_api.routes.budgets.BudgetRepository",
        return_value=mock_repo,
    ):
        response = client.post(
            "/budgets/",
            json={
                "user_id": "user-1",
                "category": "groceries",
                "monthly_limit": "400.00",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "dddddddd-dddd-dddd-dddd-dddddddddddd"
    assert data["user_id"] == "user-1"
    assert data["category"] == "groceries"
    assert data["monthly_limit"] == "400.00"


def test_list_budgets(client, mock_repo):
    """Test GET /budgets/ returns list of budgets for a user."""
    mock_budgets = [
        BudgetOut(
            id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            user_id="user-1",
            category="groceries",
            monthly_limit=Decimal("400.00"),
        ),
        BudgetOut(
            id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
            user_id="user-1",
            category="entertainment",
            monthly_limit=Decimal("100.00"),
        ),
    ]
    mock_repo.list_by_user.return_value = mock_budgets

    with patch(
        "flux_api.routes.budgets.BudgetRepository",
        return_value=mock_repo,
    ):
        response = client.get("/budgets/?user_id=user-1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    assert data[1]["id"] == "ffffffff-ffff-ffff-ffff-ffffffffffff"
    assert data[0]["category"] == "groceries"
    assert data[1]["category"] == "entertainment"


def test_delete_budget(client, mock_repo):
    """Test DELETE /budgets/{budget_id} returns 204."""
    mock_repo.delete.return_value = True

    with patch(
        "flux_api.routes.budgets.BudgetRepository",
        return_value=mock_repo,
    ):
        response = client.delete(
            "/budgets/dddddddd-dddd-dddd-dddd-dddddddddddd?user_id=user-1"
        )

    assert response.status_code == 204
    mock_repo.delete.assert_called_once_with(
        UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"), "user-1"
    )
