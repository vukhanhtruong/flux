"""Shared fixtures for tool tests.

Tools wrap flux_core Use Cases, so the fixtures here mirror what a real
request-scope would provide: a migrated SQLite database, a per-request
user_id, and helpers for vector-store + embedding dependencies that would
otherwise be slow (fastembed model download) or filesystem-heavy (zvec).
"""
from __future__ import annotations

import pytest

from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate as run_core_migrations


@pytest.fixture
def core_db(tmp_path):
    """Real temp SQLite database with core migrations applied."""
    path = tmp_path / "flux.db"
    db = Database(str(path))
    db.connect()
    run_core_migrations(db)
    try:
        yield db
    finally:
        db.disconnect()


@pytest.fixture
def user_id(core_db) -> str:
    """Default test user id following the tg:<uid> convention.

    Seeds the ``users`` row up-front because every domain table has a
    foreign key on ``users(id)``.
    """
    uid = "tg:test-user"
    _seed_user(core_db, uid)
    return uid


def _seed_user(db: Database, uid: str) -> None:
    """Insert a minimal ``users`` row so foreign keys resolve.

    Idempotent via INSERT OR IGNORE so tests can seed additional users
    without tripping PK conflicts.
    """
    db.connection().execute(
        "INSERT OR IGNORE INTO users (id, platform, platform_id, display_name) "
        "VALUES (?, ?, ?, ?)",
        (uid, "test", uid.split(":", 1)[-1], "Test User"),
    )


@pytest.fixture
def seed_user(core_db):
    """Helper to seed arbitrary extra user rows inside a test."""

    def _seed(uid: str) -> str:
        _seed_user(core_db, uid)
        return uid

    return _seed


@pytest.fixture
def vector_store(core_db):
    """SqliteVecStore backed by the same SQLite DB as the relational data.

    Now that UoW writes vectors directly to sqlite-vec tables inside the same
    DB (no external zvec directory), tests must use SqliteVecStore for both
    writes (via UoW) and reads (via Recall/SearchTransactions) so they share
    the same data.
    """
    from flux_core.vector.store import SqliteVecStore

    return SqliteVecStore(core_db)


class _FakeEmbeddingService:
    """Deterministic 384-dim embedding service for tests.

    Avoids the ~100MB fastembed model download. Produces distinguishable
    vectors for different texts by hashing the input into the first few
    dimensions — enough for sqlite-vec to order results consistently in tests.
    """

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * 384
        if not text:
            return vec
        # Spread a hash across the first 8 dims so different texts get
        # different vectors; stable within a run.
        h = hash(text) & 0xFFFFFFFF
        for i in range(8):
            vec[i] = ((h >> (i * 4)) & 0xF) / 15.0
        return vec


@pytest.fixture
def embedding_svc() -> _FakeEmbeddingService:
    return _FakeEmbeddingService()
