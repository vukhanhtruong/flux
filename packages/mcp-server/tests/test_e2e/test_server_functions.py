"""Tests for server.py module-level functions."""
import pytest
from unittest.mock import AsyncMock, MagicMock

import flux_mcp.server as server_module
from flux_mcp.server import get_session_user_id, get_db, get_embedding_service


def test_get_session_user_id_raises_when_empty(monkeypatch):
    monkeypatch.setattr(server_module, "_session_user_id", "")
    with pytest.raises(RuntimeError, match="--user-id"):
        get_session_user_id()


async def test_get_db_creates_database_when_none(monkeypatch):
    mock_db_instance = AsyncMock()
    mock_db_class = MagicMock(return_value=mock_db_instance)

    monkeypatch.setattr(server_module, "_db", None)
    monkeypatch.setattr(server_module, "Database", mock_db_class)

    result = await get_db()

    mock_db_class.assert_called_once()
    mock_db_instance.connect.assert_awaited_once()
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
