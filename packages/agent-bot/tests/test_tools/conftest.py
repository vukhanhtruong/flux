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


class _InMemoryVectorStore:
    """Minimal in-memory stand-in for ``ZvecStore``.

    Duck-types the methods UoW + SearchTransactions rely on (``upsert``,
    ``delete``, ``search``) so we don't need the optional ``zvec``
    native dependency installed to run tool tests.

    Supports the single filter form the Use Cases emit today:
    ``user_id = "<uid>"``. Search ranks by cosine similarity.
    """

    def __init__(self) -> None:
        # collection -> doc_id -> (vector, metadata)
        self._docs: dict[str, dict[str, tuple[list[float], dict]]] = {}

    def upsert(
        self, collection: str, doc_id: str, vector: list[float], metadata: dict
    ) -> None:
        self._docs.setdefault(collection, {})[doc_id] = (list(vector), dict(metadata))

    def delete(self, collection: str, doc_id: str) -> None:
        coll = self._docs.get(collection)
        if coll is not None:
            coll.pop(doc_id, None)

    def search(
        self,
        collection: str,
        vector: list[float],
        limit: int,
        filter: dict[str, str] | None = None,
    ) -> list[str]:
        coll = self._docs.get(collection, {})
        required_user: str | None = None
        if filter:
            required_user = filter.get("user_id")
        scored: list[tuple[float, str]] = []
        for doc_id, (vec, meta) in coll.items():
            if required_user is not None and meta.get("user_id") != required_user:
                continue
            scored.append((_cosine(vector, vec), doc_id))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [doc_id for _, doc_id in scored[:limit]]

    def optimize(self, collection: str) -> None:  # pragma: no cover - noop
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    import math

    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


@pytest.fixture
def vector_store() -> _InMemoryVectorStore:
    """In-memory vector store that duck-types ZvecStore.

    Avoids the optional ``zvec`` native dependency in unit tests while
    exercising the real Use Case / UoW dual-write codepath.
    """
    return _InMemoryVectorStore()


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
