"""Test profile REST routes."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app
from flux_api.deps import get_db
from flux_core.db.user_profile_repo import UserProfileRepository
from flux_core.models.user_profile import UserProfile


@pytest.fixture
def mock_repo():
    """Mock user profile repository."""
    return AsyncMock(spec=UserProfileRepository)


@pytest.fixture
def mock_db():
    """Mock database connection."""
    return MagicMock()


@pytest.fixture
def client(mock_db):
    """Test client with mocked DB dependency."""

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_profile_success(client, mock_repo):
    """Test GET /profile returns user profile."""
    mock_repo.get_by_user_id.return_value = UserProfile(
        user_id="tg:alice",
        username="alice",
        channel="telegram",
        platform_id="12345",
        currency="VND",
        timezone="Asia/Ho_Chi_Minh",
        locale="vi-VN",
    )

    with patch("flux_api.routes.profile.UserProfileRepository", return_value=mock_repo):
        response = client.get("/profile?user_id=tg:alice")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "tg:alice"
    assert data["currency"] == "VND"
    assert data["locale"] == "vi-VN"


def test_get_profile_not_found(client, mock_repo):
    """Test GET /profile returns 404 when user does not exist."""
    mock_repo.get_by_user_id.return_value = None

    with patch("flux_api.routes.profile.UserProfileRepository", return_value=mock_repo):
        response = client.get("/profile?user_id=tg:missing")

    assert response.status_code == 404


def test_patch_profile_success(client, mock_repo):
    """Test PATCH /profile updates profile fields."""
    mock_repo.update.return_value = UserProfile(
        user_id="tg:alice",
        username="alice",
        channel="telegram",
        platform_id="12345",
        currency="USD",
        timezone="America/New_York",
        locale="en-US",
    )

    with patch("flux_api.routes.profile.UserProfileRepository", return_value=mock_repo):
        response = client.patch(
            "/profile?user_id=tg:alice",
            json={"currency": "USD", "timezone": "America/New_York", "locale": "en-US"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["currency"] == "USD"
    assert data["timezone"] == "America/New_York"
    assert data["locale"] == "en-US"


def test_patch_profile_requires_payload_fields(client, mock_repo):
    """Test PATCH /profile rejects empty payload."""
    with patch("flux_api.routes.profile.UserProfileRepository", return_value=mock_repo):
        response = client.patch("/profile?user_id=tg:alice", json={})

    assert response.status_code == 400

