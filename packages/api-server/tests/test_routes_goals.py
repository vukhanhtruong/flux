"""Test goal REST routes."""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app
from flux_api.deps import get_db, get_embedding_service
from flux_core.db.goal_repo import GoalRepository
from flux_core.models.goal import GoalOut


@pytest.fixture
def mock_repo():
    """Mock goal repository (no spec — route calls update which is not on the repo directly)."""
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


def test_create_goal(client, mock_repo):
    """Test POST /goals/ creates a goal and returns 201."""
    mock_goal = GoalOut(
        id=UUID("11111111-aaaa-aaaa-aaaa-111111111111"),
        user_id="user-1",
        name="Emergency Fund",
        target_amount=Decimal("10000.00"),
        current_amount=Decimal("0.00"),
        deadline=date(2025, 12, 31),
        color="#3B82F6",
    )
    mock_repo.create.return_value = mock_goal

    with patch(
        "flux_api.routes.goals.GoalRepository",
        return_value=mock_repo,
    ):
        response = client.post(
            "/goals/",
            json={
                "user_id": "user-1",
                "name": "Emergency Fund",
                "target_amount": "10000.00",
                "deadline": "2025-12-31",
                "color": "#3B82F6",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "11111111-aaaa-aaaa-aaaa-111111111111"
    assert data["user_id"] == "user-1"
    assert data["name"] == "Emergency Fund"
    assert data["target_amount"] == "10000.00"
    assert data["current_amount"] == "0.00"
    assert data["deadline"] == "2025-12-31"
    assert data["color"] == "#3B82F6"


def test_list_goals(client, mock_repo):
    """Test GET /goals/ returns list of goals for a user."""
    mock_goals = [
        GoalOut(
            id=UUID("22222222-aaaa-aaaa-aaaa-222222222222"),
            user_id="user-1",
            name="Vacation",
            target_amount=Decimal("3000.00"),
            current_amount=Decimal("500.00"),
            deadline=date(2024, 8, 1),
            color="#10B981",
        ),
        GoalOut(
            id=UUID("33333333-aaaa-aaaa-aaaa-333333333333"),
            user_id="user-1",
            name="New Car",
            target_amount=Decimal("20000.00"),
            current_amount=Decimal("2000.00"),
            deadline=None,
            color="#F59E0B",
        ),
    ]
    mock_repo.list_by_user.return_value = mock_goals

    with patch(
        "flux_api.routes.goals.GoalRepository",
        return_value=mock_repo,
    ):
        response = client.get("/goals/?user_id=user-1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == "22222222-aaaa-aaaa-aaaa-222222222222"
    assert data[1]["id"] == "33333333-aaaa-aaaa-aaaa-333333333333"
    assert data[0]["name"] == "Vacation"
    assert data[1]["deadline"] is None


def test_update_goal(client, mock_repo):
    """Test PATCH /goals/{goal_id} updates a goal and returns 200."""
    mock_goal = GoalOut(
        id=UUID("22222222-aaaa-aaaa-aaaa-222222222222"),
        user_id="user-1",
        name="Beach Vacation",
        target_amount=Decimal("4000.00"),
        current_amount=Decimal("500.00"),
        deadline=date(2024, 9, 1),
        color="#10B981",
    )
    mock_repo.update.return_value = mock_goal

    with patch(
        "flux_api.routes.goals.GoalRepository",
        return_value=mock_repo,
    ):
        response = client.patch(
            "/goals/22222222-aaaa-aaaa-aaaa-222222222222?user_id=user-1",
            json={
                "name": "Beach Vacation",
                "target_amount": "4000.00",
                "deadline": "2024-09-01",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "22222222-aaaa-aaaa-aaaa-222222222222"
    assert data["name"] == "Beach Vacation"
    assert data["target_amount"] == "4000.00"
    assert data["deadline"] == "2024-09-01"


def test_delete_goal(client, mock_repo):
    """Test DELETE /goals/{goal_id} returns 204."""
    mock_repo.delete.return_value = True

    with patch(
        "flux_api.routes.goals.GoalRepository",
        return_value=mock_repo,
    ):
        response = client.delete(
            "/goals/22222222-aaaa-aaaa-aaaa-222222222222?user_id=user-1"
        )

    assert response.status_code == 204
    mock_repo.delete.assert_called_once_with(
        UUID("22222222-aaaa-aaaa-aaaa-222222222222"), "user-1"
    )
