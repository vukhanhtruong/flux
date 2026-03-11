"""Test profile REST routes."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app
from flux_core.models.user_profile import UserProfile


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


def _make_profile(**overrides) -> UserProfile:
    defaults = dict(
        user_id="tg:alice",
        username="alice",
        channel="telegram",
        platform_id="12345",
        currency="VND",
        timezone="Asia/Ho_Chi_Minh",
        locale="vi-VN",
    )
    defaults.update(overrides)
    return UserProfile(**defaults)


def test_get_profile_success(client):
    """Test GET /profile returns user profile."""
    profile = _make_profile()
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.return_value = profile

    with (
        patch("flux_api.routes.profile.get_db") as mock_get_db,
        patch("flux_api.routes.profile.SqliteUserRepository", return_value=mock_repo),
    ):
        mock_get_db.return_value = MagicMock()
        response = client.get("/profile?user_id=tg:alice")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "tg:alice"
    assert data["currency"] == "VND"
    assert data["locale"] == "vi-VN"


def test_get_profile_not_found(client):
    """Test GET /profile returns 404 when user does not exist."""
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.return_value = None

    with (
        patch("flux_api.routes.profile.get_db") as mock_get_db,
        patch("flux_api.routes.profile.SqliteUserRepository", return_value=mock_repo),
    ):
        mock_get_db.return_value = MagicMock()
        response = client.get("/profile?user_id=tg:missing")

    assert response.status_code == 404


def test_patch_profile_success(client, mock_uow):
    """Test PATCH /profile updates profile fields."""
    updated = _make_profile(currency="USD", timezone="America/New_York", locale="en-US")
    mock_repo = MagicMock()
    mock_repo.update.return_value = updated

    with (
        patch("flux_api.routes.profile.get_uow", return_value=mock_uow),
        patch("flux_api.routes.profile.SqliteUserRepository", return_value=mock_repo),
    ):
        response = client.patch(
            "/profile?user_id=tg:alice",
            json={"currency": "USD", "timezone": "America/New_York", "locale": "en-US"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["currency"] == "USD"
    assert data["timezone"] == "America/New_York"


def test_patch_profile_requires_payload_fields(client):
    """Test PATCH /profile rejects empty payload."""
    response = client.patch("/profile?user_id=tg:alice", json={})
    assert response.status_code == 400


def test_get_profile_empty_user_id(client):
    """Test GET /profile rejects empty user_id."""
    response = client.get("/profile?user_id=%20")
    assert response.status_code == 400
    assert "user_id is required" in response.json()["detail"]


def test_patch_profile_empty_user_id(client):
    """Test PATCH /profile rejects empty user_id."""
    response = client.patch("/profile?user_id=%20", json={"currency": "USD"})
    assert response.status_code == 400
    assert "user_id is required" in response.json()["detail"]


def test_patch_profile_empty_currency(client):
    """Test PATCH /profile rejects empty currency string."""
    response = client.patch("/profile?user_id=tg:alice", json={"currency": "  "})
    assert response.status_code == 400
    assert "currency cannot be empty" in response.json()["detail"]


def test_patch_profile_empty_timezone(client):
    """Test PATCH /profile rejects empty timezone string."""
    response = client.patch("/profile?user_id=tg:alice", json={"timezone": "  "})
    assert response.status_code == 400
    assert "timezone cannot be empty" in response.json()["detail"]


def test_patch_profile_empty_locale(client):
    """Test PATCH /profile rejects empty locale string."""
    response = client.patch("/profile?user_id=tg:alice", json={"locale": "  "})
    assert response.status_code == 400
    assert "locale cannot be empty" in response.json()["detail"]


def test_patch_profile_user_not_found(client, mock_uow):
    """Test PATCH /profile returns 404 when user does not exist."""
    mock_repo = MagicMock()
    mock_repo.update.side_effect = ValueError("user not found")

    with (
        patch("flux_api.routes.profile.get_uow", return_value=mock_uow),
        patch("flux_api.routes.profile.SqliteUserRepository", return_value=mock_repo),
    ):
        response = client.patch(
            "/profile?user_id=tg:missing",
            json={"currency": "USD"},
        )

    assert response.status_code == 404
    assert "user not found" in response.json()["detail"]
