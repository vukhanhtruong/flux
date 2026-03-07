"""Test subscription REST routes."""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app
from flux_core.models.subscription import BillingCycle, SubscriptionOut


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


def test_create_subscription(client, mock_uow):
    """Test POST /subscriptions/ creates a subscription and returns 201."""
    expected = SubscriptionOut(
        id=UUID("44444444-aaaa-aaaa-aaaa-444444444444"),
        user_id="user-1",
        name="Netflix",
        amount=Decimal("15.99"),
        billing_cycle=BillingCycle.monthly,
        next_date=date(2024, 2, 15),
        category="entertainment",
        active=True,
    )

    with (
        patch("flux_api.routes.subscriptions.get_uow", return_value=mock_uow),
        patch("flux_api.routes.subscriptions.CreateSubscription") as MockUC,
    ):
        MockUC.return_value.execute = AsyncMock(return_value=expected)
        response = client.post(
            "/subscriptions/",
            params={
                "user_id": "user-1",
                "name": "Netflix",
                "amount": 15.99,
                "billing_cycle": "monthly",
                "next_date": "2024-02-15",
                "category": "entertainment",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "44444444-aaaa-aaaa-aaaa-444444444444"
    assert data["name"] == "Netflix"
    assert data["amount"] == "15.99"
    assert data["billing_cycle"] == "monthly"
    assert data["active"] is True


def test_list_subscriptions(client):
    """Test GET /subscriptions/ returns list of subscriptions for a user."""
    expected = [
        SubscriptionOut(
            id=UUID("55555555-aaaa-aaaa-aaaa-555555555555"),
            user_id="user-1",
            name="Netflix",
            amount=Decimal("15.99"),
            billing_cycle=BillingCycle.monthly,
            next_date=date(2024, 2, 15),
            category="entertainment",
            active=True,
        ),
        SubscriptionOut(
            id=UUID("66666666-aaaa-aaaa-aaaa-666666666666"),
            user_id="user-1",
            name="Spotify",
            amount=Decimal("9.99"),
            billing_cycle=BillingCycle.monthly,
            next_date=date(2024, 2, 20),
            category="entertainment",
            active=True,
        ),
    ]

    with (
        patch("flux_api.routes.subscriptions.get_db") as mock_get_db,
        patch("flux_api.routes.subscriptions.SqliteSubscriptionRepository"),
        patch("flux_api.routes.subscriptions.ListSubscriptions") as MockUC,
    ):
        mock_get_db.return_value = MagicMock()
        MockUC.return_value.execute = AsyncMock(return_value=expected)
        response = client.get("/subscriptions/?user_id=user-1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Netflix"
    assert data[1]["name"] == "Spotify"


def test_toggle_subscription(client, mock_uow):
    """Test POST /subscriptions/{id}/toggle toggles active state."""
    expected = SubscriptionOut(
        id=UUID("44444444-aaaa-aaaa-aaaa-444444444444"),
        user_id="user-1",
        name="Netflix",
        amount=Decimal("15.99"),
        billing_cycle=BillingCycle.monthly,
        next_date=date(2024, 2, 15),
        category="entertainment",
        active=False,
    )

    with (
        patch("flux_api.routes.subscriptions.get_uow", return_value=mock_uow),
        patch("flux_api.routes.subscriptions.ToggleSubscription") as MockUC,
    ):
        MockUC.return_value.execute = AsyncMock(return_value=expected)
        response = client.post(
            "/subscriptions/44444444-aaaa-aaaa-aaaa-444444444444/toggle"
            "?user_id=user-1"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["active"] is False


def test_delete_subscription(client, mock_uow):
    """Test DELETE /subscriptions/{sub_id} returns 204."""
    with (
        patch("flux_api.routes.subscriptions.get_uow", return_value=mock_uow),
        patch("flux_api.routes.subscriptions.DeleteSubscription") as MockUC,
    ):
        MockUC.return_value.execute = AsyncMock(return_value=None)
        response = client.delete(
            "/subscriptions/44444444-aaaa-aaaa-aaaa-444444444444?user_id=user-1"
        )

    assert response.status_code == 204
