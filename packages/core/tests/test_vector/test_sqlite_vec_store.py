from __future__ import annotations

import pytest

from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate


@pytest.fixture()
def store(tmp_path):
    from flux_core.vector.store import SqliteVecStore

    db = Database(str(tmp_path / "flux.db"))
    db.connect()
    migrate(db)
    yield SqliteVecStore(db)
    db.disconnect()


def _vec(*components: float, dim: int = 384) -> list[float]:
    """Build a dim-length vector with given leading components, zeros elsewhere."""
    v = list(components) + [0.0] * (dim - len(components))
    return v[:dim]


def test_upsert_and_search_roundtrip(store):
    store.upsert(
        "transaction_embeddings",
        "doc1",
        _vec(1.0),
        {"user_id": "tg:1"},
    )
    results = store.search("transaction_embeddings", _vec(1.0), limit=5)
    assert results == ["doc1"]


def test_upsert_overwrites(store):
    store.upsert("transaction_embeddings", "doc1", _vec(1.0), {"user_id": "tg:1"})
    store.upsert("transaction_embeddings", "doc1", _vec(0.0, 1.0), {"user_id": "tg:1"})

    results = store.search("transaction_embeddings", _vec(0.0, 1.0), limit=5)
    assert "doc1" in results


def test_delete(store):
    store.upsert("transaction_embeddings", "doc1", _vec(1.0), {"user_id": "tg:1"})
    store.delete("transaction_embeddings", "doc1")

    results = store.search("transaction_embeddings", _vec(1.0), limit=5)
    assert "doc1" not in results


def test_search_filters_by_user_id(store):
    store.upsert("transaction_embeddings", "a", _vec(1.0), {"user_id": "tg:1"})
    store.upsert("transaction_embeddings", "b", _vec(1.0), {"user_id": "tg:2"})

    results = store.search(
        "transaction_embeddings",
        _vec(1.0),
        limit=10,
        filter={"user_id": "tg:1"},
    )
    assert results == ["a"]


def test_search_empty_collection_returns_empty_list(store):
    # Searching before any inserts — vec0 table exists but is empty
    results = store.search("transaction_embeddings", _vec(1.0), limit=5)
    assert results == []
