"""Tests for server.py module-level functions."""
import pytest
from unittest.mock import MagicMock

import flux_mcp.server as server_module
from flux_mcp.server import get_session_user_id, get_db, get_embedding_service, get_user_timezone


def test_get_session_user_id_raises_when_empty(monkeypatch):
    monkeypatch.setattr(server_module, "_session_user_id", "")
    with pytest.raises(RuntimeError, match="--user-id"):
        get_session_user_id()


def test_get_db_creates_database_when_none(monkeypatch, tmp_path):
    mock_db_instance = MagicMock()
    mock_db_class = MagicMock(return_value=mock_db_instance)
    mock_migrate = MagicMock()

    monkeypatch.setattr(server_module, "_db", None)
    monkeypatch.setattr(server_module, "Database", mock_db_class)
    monkeypatch.setattr(server_module, "migrate", mock_migrate)

    result = get_db()

    mock_db_class.assert_called_once()
    mock_db_instance.connect.assert_called_once()
    mock_migrate.assert_called_once_with(mock_db_instance)
    assert result is mock_db_instance

    # restore _db to None so other tests start clean
    monkeypatch.setattr(server_module, "_db", None)


def test_get_embedding_service_creates_service_when_none(monkeypatch):
    mock_svc_instance = MagicMock()
    mock_svc_class = MagicMock(return_value=mock_svc_instance)

    monkeypatch.setattr(server_module, "_embedding_service", None)
    monkeypatch.setattr(server_module, "EmbeddingService", mock_svc_class)

    result = get_embedding_service()

    mock_svc_class.assert_called_once()
    assert result is mock_svc_instance

    # restore so other tests start clean
    monkeypatch.setattr(server_module, "_embedding_service", None)


def test_get_user_timezone_falls_back_to_utc(monkeypatch, seeded_db):
    """get_user_timezone returns 'UTC' when profile has no timezone."""
    monkeypatch.setattr(server_module, "_user_timezone", None)
    monkeypatch.setattr(server_module, "_db", seeded_db)
    monkeypatch.setattr(server_module, "_session_user_id", "nonexistent:user")
    monkeypatch.setattr(server_module, "get_db", lambda: seeded_db)
    monkeypatch.setattr(server_module, "get_session_user_id", lambda: "nonexistent:user")

    result = get_user_timezone()
    assert result == "UTC"

    monkeypatch.setattr(server_module, "_user_timezone", None)
