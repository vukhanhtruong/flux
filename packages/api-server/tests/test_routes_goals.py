"""Test goal REST routes."""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app
from flux_core.models.goal import GoalOut


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    return uow


def test_create_goal(client, mock_uow):
    """Test POST /goals/ creates a goal and returns 201."""
    expected = GoalOut(
        id=UUID("11111111-aaaa-aaaa-aaaa-111111111111"),
        user_id="user-1",
        name="Emergency Fund",
        target_amount=Decimal("10000.00"),
        current_amount=Decimal("0.00"),
        deadline=date(2025, 12, 31),
        color="#3B82F6",
    )

    with (
        patch("flux_api.routes.goals.get_uow", return_value=mock_uow),
        patch("flux_api.routes.goals.CreateGoal") as MockUC,
    ):
        MockUC.return_value.execute = AsyncMock(return_value=expected)
        response = client.post(
            "/goals/",
            params={
                "user_id": "user-1",
                "name": "Emergency Fund",
                "target_amount": 10000.00,
                "deadline": "2025-12-31",
                "color": "#3B82F6",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "11111111-aaaa-aaaa-aaaa-111111111111"
    assert data["name"] == "Emergency Fund"
    assert data["target_amount"] == "10000.00"
    assert data["current_amount"] == "0.00"
    assert data["deadline"] == "2025-12-31"


def test_list_goals(client):
    """Test GET /goals/ returns list of goals for a user."""
    expected = [
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

    with (
        patch("flux_api.routes.goals.get_db") as mock_get_db,
        patch("flux_api.routes.goals.SqliteGoalRepository"),
        patch("flux_api.routes.goals.ListGoals") as MockUC,
    ):
        mock_get_db.return_value = MagicMock()
        MockUC.return_value.execute = AsyncMock(return_value=expected)
        response = client.get("/goals/?user_id=user-1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Vacation"
    assert data[1]["deadline"] is None


def test_deposit_to_goal(client, mock_uow):
    """Test POST /goals/{goal_id}/deposit deposits into a goal."""
    expected = GoalOut(
        id=UUID("22222222-aaaa-aaaa-aaaa-222222222222"),
        user_id="user-1",
        name="Vacation",
        target_amount=Decimal("3000.00"),
        current_amount=Decimal("600.00"),
        deadline=date(2024, 8, 1),
        color="#10B981",
    )

    with (
        patch("flux_api.routes.goals.get_uow", return_value=mock_uow),
        patch("flux_api.routes.goals.DepositToGoal") as MockUC,
    ):
        MockUC.return_value.execute = AsyncMock(return_value=expected)
        response = client.post(
            "/goals/22222222-aaaa-aaaa-aaaa-222222222222/deposit",
            params={"user_id": "user-1", "amount": 100.00},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["current_amount"] == "600.00"


def test_deposit_to_goal_not_found(client, mock_uow):
    """Test POST /goals/{goal_id}/deposit returns 404 when goal not found."""
    with (
        patch("flux_api.routes.goals.get_uow", return_value=mock_uow),
        patch("flux_api.routes.goals.DepositToGoal") as MockUC,
    ):
        MockUC.return_value.execute = AsyncMock(
            side_effect=ValueError("Goal not found")
        )
        response = client.post(
            "/goals/99999999-aaaa-aaaa-aaaa-999999999999/deposit",
            params={"user_id": "user-1", "amount": 100.00},
        )

    assert response.status_code == 404
    assert "Goal not found" in response.json()["detail"]


def test_delete_goal(client, mock_uow):
    """Test DELETE /goals/{goal_id} returns 204."""
    with (
        patch("flux_api.routes.goals.get_uow", return_value=mock_uow),
        patch("flux_api.routes.goals.DeleteGoal") as MockUC,
    ):
        MockUC.return_value.execute = AsyncMock(return_value=None)
        response = client.delete(
            "/goals/22222222-aaaa-aaaa-aaaa-222222222222?user_id=user-1"
        )

    assert response.status_code == 204
