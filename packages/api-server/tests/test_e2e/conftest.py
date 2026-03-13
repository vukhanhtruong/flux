"""Shared fixtures for API server E2E tests — seeded SQLite + mock zvec."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import flux_api.deps as deps_module
from flux_core.events.bus import EventBus
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
from flux_core.vector.store import ZVEC_AVAILABLE, ZvecStore

TEST_USER_ID = "test:e2e-user"


class InMemoryVectorStore:
    """In-memory vector store for E2E tests when zvec is not installed."""

    def __init__(self):
        self._docs: dict[str, dict[str, tuple[list[float], dict]]] = {}

    def upsert(
        self, collection: str, doc_id: str, vector: list[float], metadata: dict
    ) -> None:
        if collection not in self._docs:
            self._docs[collection] = {}
        self._docs[collection][doc_id] = (vector, metadata)

    def delete(self, collection: str, doc_id: str) -> None:
        if collection in self._docs:
            self._docs[collection].pop(doc_id, None)

    def search(
        self, collection: str, vector: list[float], limit: int,
        filter: str | None = None,
    ) -> list[str]:
        if collection not in self._docs:
            return []
        return list(self._docs[collection].keys())[:limit]

    def optimize(self, collection: str) -> None:
        pass


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
    """Patch API deps singletons to use seeded SQLite + zvec, return TestClient.

    We patch the module-level singletons (_db, _vector_store, etc.) so that
    the original get_*() functions return our test instances (they check
    ``if _xxx is None`` and skip lazy init when already set).
    """
    monkeypatch.setattr(deps_module, "_db", seeded_db)
    monkeypatch.setattr(deps_module, "_vector_store", vector_store)
    monkeypatch.setattr(deps_module, "_event_bus", event_bus)
    monkeypatch.setattr(deps_module, "_embedding_service", mock_embedding_service)

    from flux_api.app import app
    return TestClient(app, raise_server_exceptions=True)
