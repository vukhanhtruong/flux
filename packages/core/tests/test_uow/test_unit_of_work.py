from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from flux_core.events.bus import EventBus
from flux_core.events.events import TransactionCreated
from flux_core.sqlite.database import Database
from flux_core.uow.unit_of_work import UnitOfWork

try:
    import zvec  # noqa: F401

    HAS_ZVEC = True
except ImportError:
    HAS_ZVEC = False


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


@pytest.mark.skipif(not HAS_ZVEC, reason="zvec not available")
async def test_commit_with_zvec(tmp_path):
    from flux_core.vector.store import ZvecStore

    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")
    vector_store = ZvecStore(str(tmp_path / "zvec"))
    event_bus = EventBus()

    uow = UnitOfWork(db, vector_store=vector_store, event_bus=event_bus)
    async with uow:
        uow.conn.execute("INSERT INTO test VALUES (?)", ("1",))
        uow.add_vector("test_coll", "1", [0.1, 0.2, 0.3, 0.4], {"user_id": "tg:123"})
        await uow.commit()

    rows = db.fetchall("SELECT * FROM test")
    assert len(rows) == 1
    vector_store.optimize("test_coll")
    results = vector_store.search("test_coll", [0.1, 0.2, 0.3, 0.4], limit=1)
    assert results == ["1"]
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


async def test_compensate_on_zvec_failure(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")
    event_bus = EventBus()

    broken_zvec = MagicMock()
    broken_zvec.upsert.side_effect = RuntimeError("zvec boom")

    uow = UnitOfWork(db, vector_store=broken_zvec, event_bus=event_bus)
    with pytest.raises(RuntimeError, match="zvec boom"):
        async with uow:
            uow.conn.execute("INSERT INTO test VALUES (?)", ("1",))
            uow.add_vector("test_coll", "1", [0.1, 0.2, 0.3, 0.4], {})
            await uow.commit()

    # SQLite should be rolled back (tx was never committed)
    rows = db.fetchall("SELECT * FROM test")
    assert len(rows) == 0
    db.disconnect()


async def test_events_not_emitted_on_failure(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")
    event_bus = EventBus()
    received = []

    async def handler(e):
        received.append(e)

    event_bus.subscribe(TransactionCreated, handler)

    broken_zvec = MagicMock()
    broken_zvec.upsert.side_effect = RuntimeError("zvec boom")

    uow = UnitOfWork(db, vector_store=broken_zvec, event_bus=event_bus)
    with pytest.raises(RuntimeError):
        async with uow:
            uow.conn.execute("INSERT INTO test VALUES (?)", ("1",))
            uow.add_vector("test_coll", "1", [0.1, 0.2, 0.3, 0.4], {})
            uow.add_event(
                TransactionCreated(
                    timestamp=datetime.now(timezone.utc),
                    transaction_id="1",
                    user_id="tg:123",
                )
            )
            await uow.commit()

    assert len(received) == 0
    db.disconnect()


async def test_compensate_zvec_on_sqlite_commit_failure(tmp_path):
    """When SQLite COMMIT fails after zvec writes succeed, zvec docs must be deleted."""
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")
    event_bus = EventBus()

    mock_zvec = MagicMock()
    uow = UnitOfWork(db, vector_store=mock_zvec, event_bus=event_bus)

    with pytest.raises(Exception):
        async with uow:
            uow.conn.execute("INSERT INTO test VALUES (?)", ("1",))
            uow.add_vector("coll", "doc1", [0.1, 0.2], {"k": "v"})
            # Force SQLite commit to fail by closing the connection
            uow.conn.close()
            await uow.commit()

    # zvec.upsert was called (write succeeded before commit)
    mock_zvec.upsert.assert_called_once_with("coll", "doc1", [0.1, 0.2], {"k": "v"})
    # Compensation: zvec.delete was called to undo the write
    mock_zvec.delete.assert_called_once_with("coll", "doc1")
    db.disconnect()


async def test_vector_delete_during_commit(tmp_path):
    """delete_vector() ops execute during commit."""
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")
    event_bus = EventBus()

    mock_zvec = MagicMock()
    uow = UnitOfWork(db, vector_store=mock_zvec, event_bus=event_bus)

    async with uow:
        uow.conn.execute("INSERT INTO test VALUES (?)", ("1",))
        uow.delete_vector("coll", "doc1")
        await uow.commit()

    mock_zvec.delete.assert_called_once_with("coll", "doc1")
    rows = db.fetchall("SELECT * FROM test")
    assert len(rows) == 1
    db.disconnect()


async def test_conn_before_aenter_raises():
    """Accessing .conn without entering context raises RuntimeError."""
    db = MagicMock()
    uow = UnitOfWork(db)
    with pytest.raises(RuntimeError, match="not entered"):
        _ = uow.conn
