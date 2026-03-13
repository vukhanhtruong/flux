"""Shared fixtures for API server E2E tests — seeded SQLite + mock zvec."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import flux_core.infrastructure as infra
from flux_core.events.bus import EventBus
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
from flux_core.testing.fixtures import InMemoryVectorStore
from flux_core.vector.store import ZVEC_AVAILABLE, ZvecStore

TEST_USER_ID = "test:e2e-user"


@pytest.fixture
def seeded_db(tmp_path):
    """Create a temp SQLite database with migrations and seed data."""
    db = Database(str(tmp_path / "e2e_test.db"))
    db.connect()
    migrate(db)

    conn = db.connection()
    conn.execute(
        "INSERT INTO users (id, platform, platform_id, display_name) VALUES (?, ?, ?, ?)",
        (TEST_USER_ID, "test", "e2e-user", "E2E Test User"),
    )
    conn.commit()

    yield db
    db.disconnect()


@pytest.fixture
def vector_store(tmp_path):
    """Create a vector store -- real zvec if available, in-memory mock otherwise."""
    if ZVEC_AVAILABLE:
        return ZvecStore(str(tmp_path / "zvec"))
    return InMemoryVectorStore()


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def mock_embedding_service():
    svc = MagicMock()
    svc.embed.return_value = [0.1] * 384
    return svc


@pytest.fixture
def seeded_app(seeded_db, vector_store, event_bus, mock_embedding_service, monkeypatch):
    """Patch infrastructure singletons to use seeded SQLite + zvec, return TestClient.

    We patch the module-level singletons in flux_core.infrastructure so that
    the get_*() functions return our test instances (they check
    ``if _xxx is None`` and skip lazy init when already set).
    """
    monkeypatch.setattr(infra, "_db", seeded_db)
    monkeypatch.setattr(infra, "_vector_store", vector_store)
    monkeypatch.setattr(infra, "_event_bus", event_bus)
    monkeypatch.setattr(infra, "_embedding_service", mock_embedding_service)

    from flux_api.app import app
    return TestClient(app, raise_server_exceptions=True)
