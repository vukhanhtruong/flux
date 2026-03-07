"""Test asset REST routes."""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app
from flux_core.models.asset import AssetFrequency, AssetOut


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.conn = MagicMock()
    return uow


def test_list_assets(client):
    """Test GET /assets/ returns list of assets for a user."""
    expected = [
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
    ]
    mock_repo = MagicMock()
    mock_repo.list_by_user.return_value = expected

    with (
        patch("flux_api.routes.assets.get_db") as mock_get_db,
        patch("flux_api.routes.assets.SqliteAssetRepository", return_value=mock_repo),
    ):
        mock_get_db.return_value = MagicMock()
        response = client.get("/assets/?user_id=user-1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Checking Account"


def test_delete_asset(client, mock_uow):
    """Test DELETE /assets/{asset_id} returns 204."""
    mock_repo = MagicMock()
    mock_repo.delete.return_value = True

    with (
        patch("flux_api.routes.assets.get_uow", return_value=mock_uow),
        patch("flux_api.routes.assets.SqliteAssetRepository", return_value=mock_repo),
    ):
        response = client.delete(
            "/assets/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa?user_id=user-1"
        )

    assert response.status_code == 204
