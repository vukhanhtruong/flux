"""Tests for LLM config API routes."""
from unittest.mock import MagicMock, patch


def test_get_llm_config_not_found(client):
    """Test GET /llm-config returns 404 when config does not exist."""
    with patch("flux_api.routes.llm_config.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        mock_get_db.return_value = mock_db

        response = client.get("/llm-config?user_id=tg:12345")

    assert response.status_code == 404
    assert response.json()["detail"] == "LLM config not found"


def test_get_llm_config_success(client):
    """Test GET /llm-config returns config with masked API key."""
    with (
        patch("flux_api.routes.llm_config.get_db") as mock_get_db,
        patch("flux_api.routes.llm_config.EncryptionService") as mock_enc,
    ):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = [
            {
                "user_id": "tg:12345",
                "provider": "anthropic",
                "model": "claude-sonnet-4-6",
                "base_url": None,
                "api_key_encrypted": "encrypted-value",
            }
        ]
        mock_get_db.return_value = mock_db
        mock_enc.from_env.return_value.decrypt.return_value = "sk-secret-key"

        response = client.get("/llm-config?user_id=tg:12345")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "tg:12345"
    assert data["provider"] == "anthropic"
    assert data["model"] == "claude-sonnet-4-6"
    assert data["api_key_masked"] == "sk-s...key"


def test_get_llm_config_missing_user_id(client):
    """Test GET /llm-config rejects empty user_id."""
    response = client.get("/llm-config?user_id=")
    assert response.status_code == 400


def test_put_llm_config_success(client):
    """Test PUT /llm-config creates/updates config."""
    with (
        patch("flux_api.routes.llm_config.get_db") as mock_get_db,
        patch("flux_api.routes.llm_config.EncryptionService") as mock_enc,
    ):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_enc.from_env.return_value.encrypt.return_value = "encrypted"
        mock_enc.from_env.return_value.decrypt.return_value = "sk-new-key"

        response = client.put(
            "/llm-config?user_id=tg:12345",
            json={
                "provider": "openai",
                "model": "gpt-4o",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-new-key",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "openai"
    assert data["model"] == "gpt-4o"
    assert data["base_url"] == "https://api.openai.com/v1"
    assert data["api_key_masked"] == "sk-n...key"


def test_put_llm_config_update_without_api_key(client):
    """When api_key is omitted, keep the existing key."""
    with (
        patch("flux_api.routes.llm_config.get_db") as mock_get_db,
        patch("flux_api.routes.llm_config.EncryptionService") as mock_enc,
    ):
        mock_db = MagicMock()
        # First call: check for existing key
        mock_db.fetchall.return_value = [
            {
                "user_id": "tg:12345",
                "provider": "anthropic",
                "model": "claude-sonnet-4-6",
                "base_url": None,
                "api_key_encrypted": "old-encrypted",
            }
        ]
        mock_get_db.return_value = mock_db
        mock_enc.from_env.return_value.decrypt.return_value = "existing-key"
        mock_enc.from_env.return_value.encrypt.return_value = "encrypted"

        response = client.put(
            "/llm-config?user_id=tg:12345",
            json={
                "provider": "anthropic",
                "model": "claude-opus-4",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "claude-opus-4"


def test_put_llm_config_new_without_api_key_fails(client):
    """When creating new config, api_key is required."""
    with (
        patch("flux_api.routes.llm_config.get_db") as mock_get_db,
        patch("flux_api.routes.llm_config.EncryptionService"),
    ):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []  # No existing config
        mock_get_db.return_value = mock_db

        response = client.put(
            "/llm-config?user_id=tg:12345",
            json={
                "provider": "anthropic",
                "model": "claude-opus-4",
            },
        )

    assert response.status_code == 400
    assert "api_key is required" in response.json()["detail"]


def test_delete_llm_config(client):
    """Test DELETE /llm-config removes config."""
    with patch("flux_api.routes.llm_config.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        response = client.delete("/llm-config?user_id=tg:12345")

    assert response.status_code == 204
    mock_db.execute.assert_called_once()


def test_delete_llm_config_missing_user_id(client):
    """Test DELETE /llm-config rejects empty user_id."""
    response = client.delete("/llm-config?user_id=")
    assert response.status_code == 400
