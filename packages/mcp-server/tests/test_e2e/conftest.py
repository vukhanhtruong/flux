"""Shared fixtures for MCP server E2E tests — seeded SQLite + mock zvec."""
import json
from unittest.mock import MagicMock

import pytest

import flux_core.infrastructure as infra
import flux_mcp.server as server_module
from flux_core.events.bus import EventBus
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
from flux_core.testing.fixtures import InMemoryVectorStore
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.vector.store import ZVEC_AVAILABLE, ZvecStore

TEST_USER_ID = "test:e2e-user"


def extract_json(tool_result):
    """Extract JSON from MCP tool result."""
    if hasattr(tool_result, "content") and tool_result.content:
        for block in tool_result.content:
            if hasattr(block, "text"):
                return json.loads(block.text)
    if hasattr(tool_result, "structured_content") and tool_result.structured_content is not None:
        sc = tool_result.structured_content
        if isinstance(sc, dict) and "result" in sc:
            return sc["result"]
        return sc
    return tool_result


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
    """Create a vector store — real zvec if available, in-memory mock otherwise."""
    if ZVEC_AVAILABLE:
        return ZvecStore(str(tmp_path / "zvec"))
    return InMemoryVectorStore()


@pytest.fixture
def event_bus():
    """Create a fresh EventBus."""
    return EventBus()


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service returning 384-dim vectors."""
    svc = MagicMock()
    svc.embed.return_value = [0.1] * 384
    return svc


@pytest.fixture
def seeded_server(
    seeded_db, vector_store, event_bus, mock_embedding_service, monkeypatch
):
    """Patch MCP server globals to use seeded SQLite + zvec,
    then return the FastMCP server instance for E2E testing."""
    # Patch infrastructure singletons
    monkeypatch.setattr(infra, "_db", seeded_db)
    monkeypatch.setattr(infra, "_vector_store", vector_store)
    monkeypatch.setattr(infra, "_event_bus", event_bus)
    monkeypatch.setattr(infra, "_embedding_service", mock_embedding_service)

    # Patch MCP-server-specific globals
    monkeypatch.setattr(server_module, "_session_user_id", TEST_USER_ID)
    monkeypatch.setattr(server_module, "_user_timezone", "UTC")

    # Patch get_* functions on the server module so tools that import from it get test instances
    monkeypatch.setattr(server_module, "get_db", lambda: seeded_db)
    monkeypatch.setattr(server_module, "get_vector_store", lambda: vector_store)
    monkeypatch.setattr(server_module, "get_event_bus", lambda: event_bus)
    monkeypatch.setattr(
        server_module, "get_embedding_service", lambda: mock_embedding_service
    )
    monkeypatch.setattr(server_module, "get_session_user_id", lambda: TEST_USER_ID)
    monkeypatch.setattr(server_module, "get_user_timezone", lambda: "UTC")

    def patched_get_uow():
        return UnitOfWork(seeded_db, vector_store, event_bus)

    monkeypatch.setattr(server_module, "get_uow", patched_get_uow)

    from flux_mcp.server import mcp

    return mcp
