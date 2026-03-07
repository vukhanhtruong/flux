from __future__ import annotations

import pytest

try:
    import zvec  # noqa: F401

    HAS_ZVEC = True
except ImportError:
    HAS_ZVEC = False

pytestmark = pytest.mark.skipif(not HAS_ZVEC, reason="zvec not installed")


@pytest.fixture()
def store(tmp_path):
    from flux_core.vector.store import ZvecStore

    return ZvecStore(str(tmp_path / "vectors"))


def test_upsert_and_search(store):
    """Upsert a doc, optimize, search — should find the doc."""
    store.upsert(
        "txns", "doc1", [1.0, 0.0, 0.0, 0.0], {"description": "groceries"}
    )
    store.optimize("txns")
    results = store.search("txns", [1.0, 0.0, 0.0, 0.0], limit=5)
    assert "doc1" in results


def test_upsert_overwrites(store):
    """Upserting same ID twice with different vector updates the doc."""
    store.upsert(
        "txns", "doc1", [1.0, 0.0, 0.0, 0.0], {"description": "old"}
    )
    store.upsert(
        "txns", "doc1", [0.0, 1.0, 0.0, 0.0], {"description": "new"}
    )
    store.optimize("txns")

    # Search with the new vector — doc1 should be found
    results = store.search("txns", [0.0, 1.0, 0.0, 0.0], limit=5)
    assert "doc1" in results


def test_delete(store):
    """Upsert then delete — search should not find the doc."""
    store.upsert(
        "txns", "doc1", [1.0, 0.0, 0.0, 0.0], {"description": "groceries"}
    )
    store.delete("txns", "doc1")
    store.optimize("txns")
    results = store.search("txns", [1.0, 0.0, 0.0, 0.0], limit=5)
    assert "doc1" not in results


def test_search_empty_collection(store):
    """Searching a non-existent collection returns empty list."""
    results = store.search("nonexistent", [1.0, 0.0, 0.0, 0.0], limit=5)
    assert results == []


def test_multiple_collections(store):
    """Each collection returns only its own docs."""
    store.upsert(
        "coll_a", "a1", [1.0, 0.0, 0.0, 0.0], {"label": "alpha"}
    )
    store.upsert(
        "coll_b", "b1", [0.0, 1.0, 0.0, 0.0], {"label": "beta"}
    )
    store.optimize("coll_a")
    store.optimize("coll_b")

    results_a = store.search("coll_a", [1.0, 0.0, 0.0, 0.0], limit=5)
    results_b = store.search("coll_b", [0.0, 1.0, 0.0, 0.0], limit=5)

    assert "a1" in results_a
    assert "b1" not in results_a
    assert "b1" in results_b
    assert "a1" not in results_b


def test_batch_upsert_and_rank(store):
    """Upsert 3 docs, search with query close to doc1 — doc1 should rank first."""
    store.upsert(
        "txns", "doc1", [1.0, 0.0, 0.0, 0.0], {"description": "target"}
    )
    store.upsert(
        "txns", "doc2", [0.0, 1.0, 0.0, 0.0], {"description": "other"}
    )
    store.upsert(
        "txns", "doc3", [0.0, 0.0, 1.0, 0.0], {"description": "another"}
    )
    store.optimize("txns")

    # Query very close to doc1's vector
    results = store.search("txns", [0.9, 0.1, 0.0, 0.0], limit=3)
    assert len(results) == 3
    assert results[0] == "doc1"
