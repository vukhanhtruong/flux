from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from flux_core.events.bus import EventBus
from flux_core.events.events import TransactionCreated
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.vector.store import SqliteVecStore


async def test_commit_sqlite_only(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")
    event_bus = EventBus()
    received = []

    async def handler(e):
        received.append(e)

    event_bus.subscribe(TransactionCreated, handler)

    uow = UnitOfWork(db, event_bus=event_bus)
    async with uow:
        uow.conn.execute("INSERT INTO test VALUES (?)", ("1",))
        uow.add_event(
            TransactionCreated(
                timestamp=datetime.now(timezone.utc),
                transaction_id="1",
                user_id="tg:123",
            )
        )
        await uow.commit()

    rows = db.fetchall("SELECT * FROM test")
    assert len(rows) == 1
    assert len(received) == 1
    db.disconnect()


async def test_rollback_on_sqlite_failure(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")
    db.execute("INSERT INTO test VALUES (?)", ("1",))
    db.connection().commit()
    event_bus = EventBus()
    received = []

    async def handler(e):
        received.append(e)

    event_bus.subscribe(TransactionCreated, handler)

    uow = UnitOfWork(db, event_bus=event_bus)
    with pytest.raises(Exception):
        async with uow:
            uow.conn.execute("INSERT INTO test VALUES (?)", ("1",))  # duplicate PK
            await uow.commit()

    assert len(received) == 0  # no events emitted
    db.disconnect()


async def test_conn_before_aenter_raises():
    """Accessing .conn without entering context raises RuntimeError."""
    db = MagicMock()
    uow = UnitOfWork(db)
    with pytest.raises(RuntimeError, match="not entered"):
        _ = uow.conn


async def test_commit_with_vectors_atomic(tmp_path):
    db = Database(str(tmp_path / "flux.db"))
    db.connect()
    migrate(db)

    event_bus = EventBus()
    vec = [1.0] + [0.0] * 383

    uow = UnitOfWork(db, event_bus=event_bus)
    async with uow:
        uow.add_vector(
            "transaction_embeddings",
            "txn1",
            vec,
            {"user_id": "tg:123"},
        )
        await uow.commit()

    store = SqliteVecStore(db)
    assert store.search("transaction_embeddings", vec, limit=1) == ["txn1"]
    db.disconnect()


async def test_rollback_discards_vectors(tmp_path):
    db = Database(str(tmp_path / "flux.db"))
    db.connect()
    migrate(db)

    vec = [1.0] + [0.0] * 383
    uow = UnitOfWork(db)
    try:
        async with uow:
            uow.add_vector(
                "transaction_embeddings",
                "txn1",
                vec,
                {"user_id": "tg:1"},
            )
            raise RuntimeError("oops")
    except RuntimeError:
        pass

    store = SqliteVecStore(db)
    assert store.search("transaction_embeddings", vec, limit=1) == []
    db.disconnect()


async def test_uow_no_longer_accepts_vector_store(tmp_path):
    import inspect
    sig = inspect.signature(UnitOfWork.__init__)
    assert "vector_store" not in sig.parameters
