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
from flux_core.vector.store import ZvecStore


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
def user_id() -> str:
    """Default test user id following the tg:<uid> convention."""
    return "tg:test-user"


@pytest.fixture
def vector_store(tmp_path) -> ZvecStore:
    """Real ZvecStore rooted at tmp_path/zvec — collections are created lazily."""
    return ZvecStore(str(tmp_path / "zvec"))


class _FakeEmbeddingService:
    """Deterministic 384-dim embedding service for tests.

    Avoids the ~100MB fastembed model download. Produces distinguishable
    vectors for different texts by hashing the input into the first few
    dimensions — enough for zvec to order results consistently in tests.
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
