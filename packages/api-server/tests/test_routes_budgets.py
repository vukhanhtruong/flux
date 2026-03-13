"""Test budget REST routes."""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from flux_core.models.budget import BudgetOut


def test_set_budget(client, mock_uow):
    """Test POST /budgets/ creates a budget and returns 201."""
    expected = BudgetOut(
        id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        user_id="user-1",
        category="groceries",
        monthly_limit=Decimal("400.00"),
    )

    with (
        patch("flux_api.routes.budgets.get_uow", return_value=mock_uow),
        patch("flux_api.routes.budgets.SetBudget") as MockUC,
    ):
        MockUC.return_value.execute = AsyncMock(return_value=expected)
        response = client.post(
            "/budgets/",
            params={
                "user_id": "user-1",
                "category": "groceries",
                "monthly_limit": 400.00,
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "dddddddd-dddd-dddd-dddd-dddddddddddd"
    assert data["category"] == "groceries"
    assert data["monthly_limit"] == "400.00"


def test_list_budgets(client):
    """Test GET /budgets/ returns list of budgets for a user."""
    expected = [
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

    with (
        patch("flux_api.routes.budgets.get_db") as mock_get_db,
        patch("flux_api.routes.budgets.SqliteBudgetRepository"),
        patch("flux_api.routes.budgets.ListBudgets") as MockUC,
    ):
        mock_get_db.return_value = MagicMock()
        MockUC.return_value.execute = AsyncMock(return_value=expected)
        response = client.get("/budgets/?user_id=user-1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["category"] == "groceries"
    assert data[1]["category"] == "entertainment"


def test_delete_budget(client, mock_uow):
    """Test DELETE /budgets/{category} returns 204."""
    with (
        patch("flux_api.routes.budgets.get_uow", return_value=mock_uow),
        patch("flux_api.routes.budgets.RemoveBudget") as MockUC,
    ):
        MockUC.return_value.execute = AsyncMock(return_value=None)
        response = client.delete("/budgets/groceries?user_id=user-1")

    assert response.status_code == 204
