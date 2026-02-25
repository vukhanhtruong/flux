"""Test subscription REST routes."""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app
from flux_api.deps import get_db, get_embedding_service
from flux_core.db.subscription_repo import SubscriptionRepository
from flux_core.models.subscription import SubscriptionOut, BillingCycle


@pytest.fixture
def mock_repo():
    """Mock subscription repository."""
    return AsyncMock(spec=SubscriptionRepository)


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


def test_create_subscription(client, mock_repo):
    """Test POST /subscriptions/ creates a subscription and returns 201."""
    mock_subscription = SubscriptionOut(
        id=UUID("44444444-aaaa-aaaa-aaaa-444444444444"),
        user_id="user-1",
        name="Netflix",
        amount=Decimal("15.99"),
        billing_cycle=BillingCycle.monthly,
        next_date=date(2024, 2, 15),
        category="entertainment",
        active=True,
    )
    mock_repo.create.return_value = mock_subscription

    with patch(
        "flux_api.routes.subscriptions.SubscriptionRepository",
        return_value=mock_repo,
    ):
        response = client.post(
            "/subscriptions/",
            json={
                "user_id": "user-1",
                "name": "Netflix",
                "amount": "15.99",
                "billing_cycle": "monthly",
                "next_date": "2024-02-15",
                "category": "entertainment",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "44444444-aaaa-aaaa-aaaa-444444444444"
    assert data["user_id"] == "user-1"
    assert data["name"] == "Netflix"
    assert data["amount"] == "15.99"
    assert data["billing_cycle"] == "monthly"
    assert data["active"] is True


def test_list_subscriptions(client, mock_repo):
    """Test GET /subscriptions/ returns list of subscriptions for a user."""
    mock_subscriptions = [
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
    mock_repo.list_by_user.return_value = mock_subscriptions

    with patch(
        "flux_api.routes.subscriptions.SubscriptionRepository",
        return_value=mock_repo,
    ):
        response = client.get("/subscriptions/?user_id=user-1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == "55555555-aaaa-aaaa-aaaa-555555555555"
    assert data[1]["id"] == "66666666-aaaa-aaaa-aaaa-666666666666"
    assert data[0]["name"] == "Netflix"
    assert data[1]["name"] == "Spotify"


def test_delete_subscription(client, mock_repo):
    """Test DELETE /subscriptions/{sub_id} returns 204."""
    mock_repo.delete.return_value = True

    with patch(
        "flux_api.routes.subscriptions.SubscriptionRepository",
        return_value=mock_repo,
    ):
        response = client.delete(
            "/subscriptions/44444444-aaaa-aaaa-aaaa-444444444444?user_id=user-1"
        )

    assert response.status_code == 204
    mock_repo.delete.assert_called_once_with(
        UUID("44444444-aaaa-aaaa-aaaa-444444444444"), "user-1"
    )
