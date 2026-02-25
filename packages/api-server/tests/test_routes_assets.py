"""Test asset REST routes."""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app
from flux_api.deps import get_db, get_embedding_service
from flux_core.db.asset_repo import AssetRepository
from flux_core.models.asset import AssetOut, AssetFrequency


@pytest.fixture
def mock_repo():
    """Mock asset repository."""
    return AsyncMock(spec=AssetRepository)


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


def test_create_asset(client, mock_repo):
    """Test POST /assets/ creates an asset and returns 201."""
    mock_asset = AssetOut(
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        user_id="user-1",
        name="Savings Account",
        amount=Decimal("10000.00"),
        interest_rate=Decimal("0.05"),
        frequency=AssetFrequency.monthly,
        next_date=date(2024, 2, 1),
        category="savings",
        active=True,
    )
    mock_repo.create.return_value = mock_asset

    with patch(
        "flux_api.routes.assets.AssetRepository",
        return_value=mock_repo,
    ):
        response = client.post(
            "/assets/",
            json={
                "user_id": "user-1",
                "name": "Savings Account",
                "amount": "10000.00",
                "interest_rate": "0.05",
                "frequency": "monthly",
                "next_date": "2024-02-01",
                "category": "savings",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert data["user_id"] == "user-1"
    assert data["name"] == "Savings Account"
    assert data["amount"] == "10000.00"
    assert data["frequency"] == "monthly"
    assert data["active"] is True


def test_list_assets(client, mock_repo):
    """Test GET /assets/ returns list of assets for a user."""
    mock_assets = [
        AssetOut(
            id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            user_id="user-1",
            name="Checking Account",
            amount=Decimal("5000.00"),
            interest_rate=Decimal("0.01"),
            frequency=AssetFrequency.monthly,
            next_date=date(2024, 2, 1),
            category="checking",
            active=True,
        ),
        AssetOut(
            id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            user_id="user-1",
            name="Investment Portfolio",
            amount=Decimal("25000.00"),
            interest_rate=Decimal("0.07"),
            frequency=AssetFrequency.yearly,
            next_date=date(2025, 1, 1),
            category="investments",
            active=True,
        ),
    ]
    mock_repo.list_by_user.return_value = mock_assets

    with patch(
        "flux_api.routes.assets.AssetRepository",
        return_value=mock_repo,
    ):
        response = client.get("/assets/?user_id=user-1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    assert data[1]["id"] == "cccccccc-cccc-cccc-cccc-cccccccccccc"
    assert data[0]["name"] == "Checking Account"
    assert data[1]["name"] == "Investment Portfolio"


def test_delete_asset(client, mock_repo):
    """Test DELETE /assets/{asset_id} returns 204."""
    mock_repo.delete.return_value = True

    with patch(
        "flux_api.routes.assets.AssetRepository",
        return_value=mock_repo,
    ):
        response = client.delete(
            "/assets/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa?user_id=user-1"
        )

    assert response.status_code == 204
    mock_repo.delete.assert_called_once_with(
        UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), "user-1"
    )
