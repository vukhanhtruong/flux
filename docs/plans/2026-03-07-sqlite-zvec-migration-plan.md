# SQLite + zvec Migration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace PostgreSQL + pgvector with SQLite + zvec for local-first, single-container deployment.

**Architecture:** Use Case pattern with Unit of Work coordinating strict dual-writes to SQLite (relational) and zvec (embeddings). In-process EventBus replaces PostgreSQL LISTEN/NOTIFY. Repository Protocol interfaces decouple business logic from storage.

**Tech Stack:** Python 3.12, sqlite3, zvec==0.2.1b0, fastembed, FastAPI, FastMCP 3.0, pytest, uv

**Design doc:** `docs/plans/2026-03-07-sqlite-zvec-migration-design.md`

**Worktree:** `/home/ces-truongvu/WIP/mine/FluxFinance/.worktrees/sqlite-zvec-migration`

**Branch:** `feature/sqlite-zvec-migration`

---

## Phase 1: Core Infrastructure

Foundation layers with no business logic dependencies. All tested in isolation.

---

### Task 1: Update core pyproject.toml dependencies

**Files:**
- Modify: `packages/core/pyproject.toml`

**Step 1: Update dependencies**

Remove `asyncpg`, `pgvector`. Add `zvec`. Keep `fastembed` optional. Remove `testcontainers`.

```toml
[project]
dependencies = [
    "pydantic>=2.0",
    "croniter>=3.0",
    "zvec>=0.2.1b0",
]

[project.optional-dependencies]
embeddings = ["fastembed>=0.4"]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-benchmark>=4.0",
    "ruff>=0.8",
]
```

**Step 2: Verify install**

Run: `cd packages/core && pip install -e ".[dev]"`
Expected: Installs without errors

**Step 3: Commit**

```bash
git add packages/core/pyproject.toml
git commit -m "chore: update core deps — remove asyncpg/pgvector, add zvec"
```

---

### Task 2: Event Bus

**Files:**
- Create: `packages/core/src/flux_core/events/__init__.py`
- Create: `packages/core/src/flux_core/events/events.py`
- Create: `packages/core/src/flux_core/events/bus.py`
- Test: `packages/core/tests/test_events/__init__.py`
- Test: `packages/core/tests/test_events/test_bus.py`

**Step 1: Write failing tests**

```python
# test_events/test_bus.py
import asyncio
from flux_core.events.bus import EventBus
from flux_core.events.events import Event, TransactionCreated
from datetime import datetime, timezone


async def test_subscribe_and_emit():
    bus = EventBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(TransactionCreated, handler)
    event = TransactionCreated(
        timestamp=datetime.now(timezone.utc),
        transaction_id="txn-1",
        user_id="tg:123",
    )
    await bus.emit(event)
    assert len(received) == 1
    assert received[0].transaction_id == "txn-1"


async def test_emit_no_subscribers():
    bus = EventBus()
    event = TransactionCreated(
        timestamp=datetime.now(timezone.utc),
        transaction_id="txn-1",
        user_id="tg:123",
    )
    await bus.emit(event)  # should not raise


async def test_subscriber_error_does_not_block_others():
    bus = EventBus()
    received = []

    async def bad_handler(event):
        raise RuntimeError("boom")

    async def good_handler(event):
        received.append(event)

    bus.subscribe(TransactionCreated, bad_handler)
    bus.subscribe(TransactionCreated, good_handler)
    event = TransactionCreated(
        timestamp=datetime.now(timezone.utc),
        transaction_id="txn-1",
        user_id="tg:123",
    )
    await bus.emit(event)
    assert len(received) == 1


async def test_unsubscribe():
    bus = EventBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(TransactionCreated, handler)
    bus.unsubscribe(TransactionCreated, handler)
    event = TransactionCreated(
        timestamp=datetime.now(timezone.utc),
        transaction_id="txn-1",
        user_id="tg:123",
    )
    await bus.emit(event)
    assert len(received) == 0


async def test_multiple_event_types():
    bus = EventBus()
    txn_received = []
    mem_received = []

    async def txn_handler(event):
        txn_received.append(event)

    async def mem_handler(event):
        mem_received.append(event)

    from flux_core.events.events import MemoryCreated

    bus.subscribe(TransactionCreated, txn_handler)
    bus.subscribe(MemoryCreated, mem_handler)

    await bus.emit(TransactionCreated(
        timestamp=datetime.now(timezone.utc),
        transaction_id="txn-1", user_id="tg:123",
    ))
    assert len(txn_received) == 1
    assert len(mem_received) == 0
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && pytest tests/test_events/test_bus.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'flux_core.events'`

**Step 3: Implement events module**

```python
# events/events.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Event:
    timestamp: datetime


@dataclass(frozen=True)
class MessageCreated(Event):
    message_id: int
    user_id: str


@dataclass(frozen=True)
class OutboundCreated(Event):
    outbound_id: int
    user_id: str


@dataclass(frozen=True)
class TransactionCreated(Event):
    transaction_id: str
    user_id: str


@dataclass(frozen=True)
class TransactionUpdated(Event):
    transaction_id: str
    user_id: str


@dataclass(frozen=True)
class TransactionDeleted(Event):
    transaction_id: str
    user_id: str


@dataclass(frozen=True)
class MemoryCreated(Event):
    memory_id: str
    user_id: str


@dataclass(frozen=True)
class SubscriptionCreated(Event):
    subscription_id: str
    user_id: str


@dataclass(frozen=True)
class SavingsCreated(Event):
    savings_id: str
    user_id: str


@dataclass(frozen=True)
class ScheduledTaskCreated(Event):
    task_id: int
    user_id: str


@dataclass(frozen=True)
class ScheduledTaskDue(Event):
    task_id: int
    user_id: str
```

```python
# events/bus.py
from __future__ import annotations
import logging
from collections import defaultdict
from typing import Callable

from flux_core.events.events import Event

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._subscribers: dict[type[Event], list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type[Event], handler: Callable) -> None:
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: type[Event], handler: Callable) -> None:
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def emit(self, event: Event) -> None:
        handlers = self._subscribers.get(type(event), [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Event handler %s failed for %s", handler.__name__, type(event).__name__
                )
```

```python
# events/__init__.py
from flux_core.events.bus import EventBus
from flux_core.events.events import (
    Event,
    MessageCreated,
    MemoryCreated,
    OutboundCreated,
    ScheduledTaskCreated,
    ScheduledTaskDue,
    SavingsCreated,
    SubscriptionCreated,
    TransactionCreated,
    TransactionDeleted,
    TransactionUpdated,
)

__all__ = [
    "Event",
    "EventBus",
    "MemoryCreated",
    "MessageCreated",
    "OutboundCreated",
    "SavingsCreated",
    "ScheduledTaskCreated",
    "ScheduledTaskDue",
    "SubscriptionCreated",
    "TransactionCreated",
    "TransactionDeleted",
    "TransactionUpdated",
]
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/core && pytest tests/test_events/test_bus.py -v`
Expected: All 5 tests PASS

**Step 5: Lint**

Run: `cd packages/core && ruff check src/flux_core/events/ tests/test_events/`
Expected: No errors

**Step 6: Commit**

```bash
git add packages/core/src/flux_core/events/ packages/core/tests/test_events/
git commit -m "feat: add in-process EventBus with pub/sub and error isolation"
```

---

### Task 3: SQLite Database class

**Files:**
- Create: `packages/core/src/flux_core/sqlite/__init__.py`
- Create: `packages/core/src/flux_core/sqlite/database.py`
- Test: `packages/core/tests/test_sqlite/__init__.py`
- Test: `packages/core/tests/test_sqlite/test_database.py`

**Step 1: Write failing tests**

```python
# test_sqlite/test_database.py
import sqlite3
from flux_core.sqlite.database import Database


async def test_connect_sets_wal_mode(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    result = db.fetchone("PRAGMA journal_mode")
    assert result[0] == "wal"
    db.disconnect()


async def test_foreign_keys_enabled(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    result = db.fetchone("PRAGMA foreign_keys")
    assert result[0] == 1
    db.disconnect()


async def test_execute_and_fetch(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.execute("CREATE TABLE test (id TEXT PRIMARY KEY, val TEXT)")
    db.execute("INSERT INTO test VALUES (?, ?)", ("1", "hello"))
    rows = db.fetchall("SELECT * FROM test")
    assert len(rows) == 1
    assert rows[0]["id"] == "1"
    assert rows[0]["val"] == "hello"
    db.disconnect()


async def test_fetchone_returns_none_when_empty(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")
    result = db.fetchone("SELECT * FROM test WHERE id = ?", ("nope",))
    assert result is None
    db.disconnect()


async def test_execute_in_thread(tmp_path):
    """Verify async wrapper runs SQL in ThreadPoolExecutor."""
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")
    await db.execute_async("INSERT INTO test VALUES (?)", ("1",))
    rows = await db.fetchall_async("SELECT * FROM test")
    assert len(rows) == 1
    db.disconnect()


async def test_transaction_commit(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")
    conn = db.connection()
    conn.execute("BEGIN")
    conn.execute("INSERT INTO test VALUES (?)", ("1",))
    conn.execute("COMMIT")
    rows = db.fetchall("SELECT * FROM test")
    assert len(rows) == 1
    db.disconnect()


async def test_transaction_rollback(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")
    conn = db.connection()
    conn.execute("BEGIN")
    conn.execute("INSERT INTO test VALUES (?)", ("1",))
    conn.execute("ROLLBACK")
    rows = db.fetchall("SELECT * FROM test")
    assert len(rows) == 0
    db.disconnect()
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && pytest tests/test_sqlite/test_database.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement Database class**

```python
# sqlite/database.py
from __future__ import annotations

import asyncio
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, path: str):
        self._path = path
        self._conn: sqlite3.Connection | None = None
        self._executor = ThreadPoolExecutor(max_workers=1)

    def connect(self) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.execute("PRAGMA cache_size = -8000")
        self._conn.execute("PRAGMA wal_autocheckpoint = 1000")
        logger.info("Connected to SQLite: %s (WAL mode)", self._path)

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
        self._executor.shutdown(wait=False)

    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.connection().execute(sql, params)

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self.connection().execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.connection().execute(sql, params).fetchall()

    async def execute_async(self, sql: str, params: tuple = ()) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self.execute, sql, params)

    async def fetchone_async(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.fetchone, sql, params)

    async def fetchall_async(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.fetchall, sql, params)
```

```python
# sqlite/__init__.py
from flux_core.sqlite.database import Database

__all__ = ["Database"]
```

**Step 4: Run tests**

Run: `cd packages/core && pytest tests/test_sqlite/test_database.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/sqlite/ packages/core/tests/test_sqlite/
git commit -m "feat: add SQLite Database class with WAL mode and ThreadPoolExecutor"
```

---

### Task 4: SQLite migrations

**Files:**
- Create: `packages/core/src/flux_core/sqlite/migrations/__init__.py`
- Create: `packages/core/src/flux_core/sqlite/migrations/001_initial.sql`
- Create: `packages/core/src/flux_core/sqlite/migrations/migrate.py`
- Test: `packages/core/tests/test_sqlite/test_migrations.py`

**Step 1: Write failing test**

```python
# test_sqlite/test_migrations.py
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate


async def test_migrate_creates_all_tables(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    migrate(db)
    tables = db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    table_names = {row["name"] for row in tables}
    expected = {
        "users", "transactions", "budgets", "savings_goals",
        "subscriptions", "assets", "agent_memory",
        "bot_messages", "bot_sessions", "bot_scheduled_tasks",
        "bot_outbound_messages", "schema_migrations",
    }
    assert expected.issubset(table_names)
    db.disconnect()


async def test_migrate_is_idempotent(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    migrate(db)
    migrate(db)  # should not raise
    version = db.fetchone("SELECT MAX(version) as v FROM schema_migrations")
    assert version["v"] == 1
    db.disconnect()


async def test_schema_migrations_tracked(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    migrate(db)
    row = db.fetchone("SELECT version, applied_at FROM schema_migrations WHERE version = 1")
    assert row is not None
    assert row["version"] == 1
    db.disconnect()
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && pytest tests/test_sqlite/test_migrations.py -v`
Expected: FAIL

**Step 3: Create 001_initial.sql**

Use the full DDL from the design doc (Section 5: SQLite Schema). This is the complete fresh schema — all core tables + bot tables + indexes.

Reference: `docs/plans/2026-03-07-sqlite-zvec-migration-design.md` → "SQLite Schema" section for the full DDL. Include all tables: `users`, `transactions`, `budgets`, `savings_goals`, `subscriptions`, `assets`, `agent_memory`, `bot_messages`, `bot_sessions`, `bot_scheduled_tasks`, `bot_outbound_messages`, `schema_migrations`.

**Step 4: Implement migrate.py**

```python
# sqlite/migrations/migrate.py
from __future__ import annotations

import logging
from pathlib import Path

from flux_core.sqlite.database import Database

logger = logging.getLogger(__name__)
MIGRATIONS_DIR = Path(__file__).parent


def migrate(db: Database) -> None:
    conn = db.connection()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    row = conn.execute("SELECT MAX(version) as v FROM schema_migrations").fetchone()
    current_version = row["v"] if row["v"] is not None else 0

    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for sql_file in sql_files:
        version = int(sql_file.name.split("_")[0])
        if version <= current_version:
            continue
        logger.info("Applying migration %s", sql_file.name)
        sql = sql_file.read_text()
        conn.executescript(sql)
        conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
        conn.commit()
        logger.info("Applied migration %s (version %d)", sql_file.name, version)
```

**Step 5: Run tests**

Run: `cd packages/core && pytest tests/test_sqlite/test_migrations.py -v`
Expected: All 3 tests PASS

**Step 6: Commit**

```bash
git add packages/core/src/flux_core/sqlite/migrations/
git add packages/core/tests/test_sqlite/test_migrations.py
git commit -m "feat: add SQLite migration system with fresh 001_initial.sql schema"
```

---

### Task 5: ZvecStore wrapper

**Files:**
- Create: `packages/core/src/flux_core/vector/__init__.py`
- Create: `packages/core/src/flux_core/vector/store.py`
- Test: `packages/core/tests/test_vector/__init__.py`
- Test: `packages/core/tests/test_vector/test_store.py`

**Step 1: Write failing tests**

```python
# test_vector/test_store.py
import pytest
from flux_core.vector.store import ZvecStore

DIMENSION = 4  # small for tests


def test_upsert_and_search(tmp_path):
    store = ZvecStore(str(tmp_path / "zvec"))
    store.upsert(
        collection="test_coll",
        doc_id="doc1",
        vector=[0.1, 0.2, 0.3, 0.4],
        metadata={"user_id": "tg:123", "category": "Food"},
    )
    store.optimize("test_coll")
    results = store.search("test_coll", [0.15, 0.25, 0.35, 0.45], limit=1)
    assert results == ["doc1"]


def test_upsert_overwrites(tmp_path):
    store = ZvecStore(str(tmp_path / "zvec"))
    store.upsert("test_coll", "doc1", [0.1, 0.2, 0.3, 0.4], {"user_id": "tg:123"})
    store.upsert("test_coll", "doc1", [0.9, 0.8, 0.7, 0.6], {"user_id": "tg:123"})
    store.optimize("test_coll")
    results = store.search("test_coll", [0.9, 0.8, 0.7, 0.6], limit=1)
    assert results == ["doc1"]


def test_delete(tmp_path):
    store = ZvecStore(str(tmp_path / "zvec"))
    store.upsert("test_coll", "doc1", [0.1, 0.2, 0.3, 0.4], {"user_id": "tg:123"})
    store.delete("test_coll", "doc1")
    store.optimize("test_coll")
    results = store.search("test_coll", [0.1, 0.2, 0.3, 0.4], limit=1)
    assert "doc1" not in results


def test_search_empty_collection(tmp_path):
    store = ZvecStore(str(tmp_path / "zvec"))
    results = store.search("nonexistent", [0.1, 0.2, 0.3, 0.4], limit=5)
    assert results == []


def test_multiple_collections(tmp_path):
    store = ZvecStore(str(tmp_path / "zvec"))
    store.upsert("coll_a", "doc1", [0.1, 0.2, 0.3, 0.4], {"user_id": "tg:123"})
    store.upsert("coll_b", "doc2", [0.5, 0.6, 0.7, 0.8], {"user_id": "tg:456"})
    store.optimize("coll_a")
    store.optimize("coll_b")
    assert store.search("coll_a", [0.1, 0.2, 0.3, 0.4], limit=5) == ["doc1"]
    assert store.search("coll_b", [0.5, 0.6, 0.7, 0.8], limit=5) == ["doc2"]


def test_batch_upsert_and_rank(tmp_path):
    store = ZvecStore(str(tmp_path / "zvec"))
    store.upsert("coll", "doc1", [1.0, 0.0, 0.0, 0.0], {"user_id": "tg:123"})
    store.upsert("coll", "doc2", [0.0, 1.0, 0.0, 0.0], {"user_id": "tg:123"})
    store.upsert("coll", "doc3", [0.9, 0.1, 0.0, 0.0], {"user_id": "tg:123"})
    store.optimize("coll")
    results = store.search("coll", [1.0, 0.0, 0.0, 0.0], limit=3)
    assert results[0] == "doc1"  # most similar
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && pytest tests/test_vector/test_store.py -v`
Expected: FAIL

**Step 3: Implement ZvecStore**

```python
# vector/store.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import zvec

logger = logging.getLogger(__name__)


class ZvecStore:
    def __init__(self, path: str):
        self._path = Path(path)
        self._collections: dict[str, Any] = {}

    def upsert(
        self, collection: str, doc_id: str, vector: list[float], metadata: dict
    ) -> None:
        coll = self._get_or_create(collection, len(vector), metadata)
        doc = zvec.Doc(
            id=doc_id,
            vectors={"embedding": vector},
            fields={k: v for k, v in metadata.items()},
        )
        coll.upsert(doc)

    def delete(self, collection: str, doc_id: str) -> None:
        coll = self._get(collection)
        if coll is not None:
            coll.delete(ids=doc_id)

    def search(
        self,
        collection: str,
        vector: list[float],
        limit: int,
        filter: str | None = None,
    ) -> list[str]:
        coll = self._get(collection)
        if coll is None:
            return []
        query = zvec.VectorQuery(field_name="embedding", vector=vector, limit=limit)
        try:
            if filter:
                results = coll.query(query, filter=filter)
            else:
                results = coll.query(query)
        except Exception:
            logger.debug("zvec query failed, returning empty", exc_info=True)
            return []
        return [doc.id for doc in results]

    def optimize(self, collection: str) -> None:
        coll = self._get(collection)
        if coll is not None:
            coll.optimize()

    def _get(self, name: str) -> Any | None:
        if name in self._collections:
            return self._collections[name]
        collection_path = self._path / name
        if not collection_path.exists():
            return None
        try:
            coll = zvec.open(path=str(collection_path))
            self._collections[name] = coll
            return coll
        except Exception:
            logger.debug("Failed to open zvec collection %s", name, exc_info=True)
            return None

    def _get_or_create(self, name: str, dimension: int, metadata: dict) -> Any:
        coll = self._get(name)
        if coll is not None:
            return coll

        collection_path = self._path / name
        collection_path.parent.mkdir(parents=True, exist_ok=True)

        fields = [
            zvec.FieldSchema(name=key, data_type=zvec.DataType.STRING, nullable=True)
            for key in metadata.keys()
        ]
        schema = zvec.CollectionSchema(
            name=name,
            fields=fields,
            vectors=[
                zvec.VectorSchema(
                    name="embedding",
                    data_type=zvec.DataType.VECTOR_FP32,
                    dimension=dimension,
                ),
            ],
        )
        coll = zvec.create_and_open(path=str(collection_path), schema=schema)
        self._collections[name] = coll
        logger.info("Created zvec collection: %s (dim=%d)", name, dimension)
        return coll
```

```python
# vector/__init__.py
from flux_core.vector.store import ZvecStore

__all__ = ["ZvecStore"]
```

**Step 4: Run tests**

Run: `cd packages/core && pytest tests/test_vector/test_store.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/vector/ packages/core/tests/test_vector/
git commit -m "feat: add ZvecStore wrapper for zvec 0.2.1b0 vector operations"
```

---

### Task 6: Unit of Work

**Files:**
- Create: `packages/core/src/flux_core/uow/__init__.py`
- Create: `packages/core/src/flux_core/uow/unit_of_work.py`
- Test: `packages/core/tests/test_uow/__init__.py`
- Test: `packages/core/tests/test_uow/test_unit_of_work.py`

**Step 1: Write failing tests**

```python
# test_uow/test_unit_of_work.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from flux_core.sqlite.database import Database
from flux_core.vector.store import ZvecStore
from flux_core.events.bus import EventBus
from flux_core.events.events import TransactionCreated
from flux_core.uow.unit_of_work import UnitOfWork
from datetime import datetime, timezone


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
        uow.add_event(TransactionCreated(
            timestamp=datetime.now(timezone.utc),
            transaction_id="1", user_id="tg:123",
        ))
        await uow.commit()

    rows = db.fetchall("SELECT * FROM test")
    assert len(rows) == 1
    assert len(received) == 1
    db.disconnect()


async def test_commit_with_zvec(tmp_path):
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

    broken_zvec = MagicMock(spec=ZvecStore)
    broken_zvec.upsert.side_effect = RuntimeError("zvec boom")

    uow = UnitOfWork(db, vector_store=broken_zvec, event_bus=event_bus)
    with pytest.raises(RuntimeError, match="zvec boom"):
        async with uow:
            uow.conn.execute("INSERT INTO test VALUES (?)", ("1",))
            uow.add_vector("test_coll", "1", [0.1, 0.2, 0.3, 0.4], {})
            await uow.commit()

    # SQLite should be rolled back
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

    broken_zvec = MagicMock(spec=ZvecStore)
    broken_zvec.upsert.side_effect = RuntimeError("zvec boom")

    uow = UnitOfWork(db, vector_store=broken_zvec, event_bus=event_bus)
    with pytest.raises(RuntimeError):
        async with uow:
            uow.conn.execute("INSERT INTO test VALUES (?)", ("1",))
            uow.add_vector("test_coll", "1", [0.1, 0.2, 0.3, 0.4], {})
            uow.add_event(TransactionCreated(
                timestamp=datetime.now(timezone.utc),
                transaction_id="1", user_id="tg:123",
            ))
            await uow.commit()

    assert len(received) == 0
    db.disconnect()
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && pytest tests/test_uow/test_unit_of_work.py -v`
Expected: FAIL

**Step 3: Implement UnitOfWork**

```python
# uow/unit_of_work.py
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.events.bus import EventBus
    from flux_core.events.events import Event
    from flux_core.vector.store import ZvecStore

logger = logging.getLogger(__name__)


@dataclass
class VectorOp:
    collection: str
    doc_id: str
    vector: list[float]
    metadata: dict


class UnitOfWork:
    def __init__(
        self,
        db,
        vector_store: ZvecStore | None = None,
        event_bus: EventBus | None = None,
    ):
        self._db = db
        self._vector_store = vector_store
        self._event_bus = event_bus
        self._pending_vectors: list[VectorOp] = []
        self._pending_events: list[Event] = []
        self._conn: sqlite3.Connection | None = None
        self._committed = False

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("UnitOfWork not entered. Use 'async with uow:'")
        return self._conn

    def add_vector(
        self, collection: str, doc_id: str, vector: list[float], metadata: dict
    ) -> None:
        self._pending_vectors.append(VectorOp(collection, doc_id, vector, metadata))

    def add_event(self, event: Event) -> None:
        self._pending_events.append(event)

    async def commit(self) -> None:
        conn = self.conn
        try:
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        written_vectors: list[VectorOp] = []
        if self._pending_vectors and self._vector_store:
            try:
                for op in self._pending_vectors:
                    self._vector_store.upsert(op.collection, op.doc_id, op.vector, op.metadata)
                    written_vectors.append(op)
            except Exception:
                logger.error("zvec write failed, compensating SQLite rollback")
                self._compensate_sqlite(conn)
                self._compensate_zvec(written_vectors)
                raise

        if self._event_bus:
            for event in self._pending_events:
                await self._event_bus.emit(event)

        self._committed = True

    def _compensate_sqlite(self, conn: sqlite3.Connection) -> None:
        """Re-execute inverse by rolling back. Since we already committed,
        we need to delete the rows. This is best-effort."""
        # For simplicity, we use a savepoint-based approach in future iterations.
        # For now, we rely on the fact that SQLite committed data is visible
        # and the caller knows the operation failed.
        # A more robust approach: don't COMMIT sqlite until zvec succeeds.
        pass

    def _compensate_zvec(self, written: list[VectorOp]) -> None:
        if not self._vector_store:
            return
        for op in written:
            try:
                self._vector_store.delete(op.collection, op.doc_id)
            except Exception:
                logger.error("Failed to compensate zvec delete for %s", op.doc_id)

    async def __aenter__(self):
        self._conn = self._db.connection()
        self._conn.execute("BEGIN")
        self._pending_vectors.clear()
        self._pending_events.clear()
        self._committed = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and not self._committed:
            try:
                self.conn.execute("ROLLBACK")
            except Exception:
                pass
        self._conn = None
        return False
```

> **Implementation note:** The compensate_sqlite method is a known limitation. A more robust approach would defer the SQLite COMMIT until after zvec succeeds. The implementer should consider: `BEGIN` → SQL writes → zvec writes → `COMMIT`. If zvec fails, `ROLLBACK` the still-uncommitted SQLite transaction. This avoids needing compensation entirely. Update the implementation accordingly if tests reveal this is needed.

```python
# uow/__init__.py
from flux_core.uow.unit_of_work import UnitOfWork

__all__ = ["UnitOfWork"]
```

**Step 4: Run tests**

Run: `cd packages/core && pytest tests/test_uow/test_unit_of_work.py -v`
Expected: All 5 tests PASS

> **Note:** The `test_compensate_on_zvec_failure` test may need adjustment depending on whether we commit SQLite before or after zvec. The preferred approach is: SQL writes happen within the BEGIN/COMMIT, but COMMIT is deferred until after zvec succeeds. If zvec fails, ROLLBACK the SQLite transaction — no compensation needed. Adjust the UoW implementation to follow this pattern if the test fails.

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/uow/ packages/core/tests/test_uow/
git commit -m "feat: add UnitOfWork for strict dual-write coordination"
```

---

## Phase 2: Repository Interfaces

Protocol classes defining what each repository does. No implementations yet.

---

### Task 7: Repository Protocol interfaces

**Files:**
- Create: `packages/core/src/flux_core/repositories/__init__.py`
- Create: `packages/core/src/flux_core/repositories/user_repo.py`
- Create: `packages/core/src/flux_core/repositories/transaction_repo.py`
- Create: `packages/core/src/flux_core/repositories/budget_repo.py`
- Create: `packages/core/src/flux_core/repositories/goal_repo.py`
- Create: `packages/core/src/flux_core/repositories/subscription_repo.py`
- Create: `packages/core/src/flux_core/repositories/asset_repo.py`
- Create: `packages/core/src/flux_core/repositories/memory_repo.py`
- Create: `packages/core/src/flux_core/repositories/embedding_repo.py`
- Create: `packages/core/src/flux_core/repositories/bot/__init__.py`
- Create: `packages/core/src/flux_core/repositories/bot/message_repo.py`
- Create: `packages/core/src/flux_core/repositories/bot/session_repo.py`
- Create: `packages/core/src/flux_core/repositories/bot/scheduled_task_repo.py`
- Create: `packages/core/src/flux_core/repositories/bot/outbound_repo.py`

**Step 1: Define all Protocol interfaces**

Use the existing `db/*_repo.py` methods as reference for method signatures. Replace asyncpg types with Pydantic models at the boundary.

Each Protocol class should mirror the methods from the current repos. Key points:
- All methods are sync (no `async` — SQLite is sync via executor)
- Accept and return Pydantic models from `flux_core.models/`
- `EmbeddingRepository` is the zvec interface: `upsert()`, `delete()`, `search()`

Reference the current repo files:
- `packages/core/src/flux_core/db/transaction_repo.py` → `TransactionRepository` Protocol
- `packages/core/src/flux_core/db/budget_repo.py` → `BudgetRepository` Protocol
- `packages/core/src/flux_core/db/goal_repo.py` → `GoalRepository` Protocol
- `packages/core/src/flux_core/db/subscription_repo.py` → `SubscriptionRepository` Protocol
- `packages/core/src/flux_core/db/asset_repo.py` → `AssetRepository` Protocol
- `packages/core/src/flux_core/db/memory_repo.py` → `MemoryRepository` Protocol
- `packages/core/src/flux_core/db/user_repo.py` → `UserRepository` Protocol
- `packages/core/src/flux_core/db/user_profile_repo.py` → `UserProfileRepository` Protocol (merge into `UserRepository`)

Bot repos — reference agent-bot's DB interactions:
- `BotMessageRepository`: `insert()`, `mark_processing()`, `mark_processed()`, `mark_failed()`, `get_pending()`
- `BotSessionRepository`: `get_session_id()`, `upsert()`, `delete()`
- `BotScheduledTaskRepository`: `create()`, `get_active_due()`, `advance_next_run()`, `mark_completed()`, `pause()`, `resume()`, `delete()`
- `BotOutboundRepository`: `insert()`, `get_pending()`, `mark_sent()`, `mark_failed()`

**Step 2: Verify imports**

Run: `python -c "from flux_core.repositories import TransactionRepository"`
Expected: No errors

**Step 3: Commit**

```bash
git add packages/core/src/flux_core/repositories/
git commit -m "feat: add repository Protocol interfaces for all domains"
```

---

## Phase 3: SQLite Repository Implementations

Each repo implemented with TDD. Repos are pure SQL, take `sqlite3.Connection`.

---

### Task 8: SQLite UserRepository

**Files:**
- Create: `packages/core/src/flux_core/sqlite/user_repo.py`
- Test: `packages/core/tests/test_repositories/__init__.py`
- Test: `packages/core/tests/test_repositories/conftest.py`
- Test: `packages/core/tests/test_repositories/test_user_repo.py`

**Step 1: Create test fixtures**

```python
# test_repositories/conftest.py
import pytest
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.connect()
    migrate(database)
    yield database
    database.disconnect()


@pytest.fixture
def conn(db):
    return db.connection()


@pytest.fixture
def user_id(conn):
    conn.execute(
        "INSERT INTO users (id, platform, platform_id, display_name) VALUES (?, ?, ?, ?)",
        ("test:user1", "test", "user1", "Test User"),
    )
    conn.commit()
    return "test:user1"
```

**Step 2: Write failing tests for UserRepository**

Test `ensure_exists()`, `get_by_user_id()`, `get_by_platform_id()`, `update()`, `create_profile()`.

Reference current methods in:
- `packages/core/src/flux_core/db/user_repo.py`
- `packages/core/src/flux_core/db/user_profile_repo.py`

**Step 3: Implement SqliteUserRepository**

All methods use `?` params, return Pydantic models.

**Step 4: Run tests, commit**

```bash
git commit -m "feat: add SqliteUserRepository with profile management"
```

---

### Task 9: SQLite TransactionRepository

**Files:**
- Create: `packages/core/src/flux_core/sqlite/transaction_repo.py`
- Test: `packages/core/tests/test_repositories/test_transaction_repo.py`

**Step 1: Write failing tests**

Test all methods: `create()`, `get_by_id()`, `get_by_ids()`, `list_by_user()` (with filters: limit, skip, start_date, end_date, categories, type), `update()`, `delete()`, `get_summary()`, `get_category_breakdown()`.

Reference: `packages/core/src/flux_core/db/transaction_repo.py`

Key differences to test:
- `tags` stored as JSON string, deserialized to `list[str]`
- `amount` stored as TEXT, deserialized to `Decimal`
- `is_recurring` stored as INTEGER (0/1), deserialized to `bool`
- No `embedding` column — embeddings live in zvec
- No `search_by_embedding()` — that's the use case's job via ZvecStore

**Step 2: Implement SqliteTransactionRepository**

**Step 3: Run tests, commit**

```bash
git commit -m "feat: add SqliteTransactionRepository with full CRUD and analytics"
```

---

### Task 10: SQLite BudgetRepository

**Files:**
- Create: `packages/core/src/flux_core/sqlite/budget_repo.py`
- Test: `packages/core/tests/test_repositories/test_budget_repo.py`

Reference: `packages/core/src/flux_core/db/budget_repo.py`

Methods: `set()` (upsert via `INSERT OR REPLACE`), `list_by_user()`, `get_by_category()`, `remove()`.

**Commit:** `git commit -m "feat: add SqliteBudgetRepository"`

---

### Task 11: SQLite GoalRepository

**Files:**
- Create: `packages/core/src/flux_core/sqlite/goal_repo.py`
- Test: `packages/core/tests/test_repositories/test_goal_repo.py`

Reference: `packages/core/src/flux_core/db/goal_repo.py`

Methods: `create()`, `get_by_id()`, `list_by_user()`, `update()`, `deposit()`, `withdraw()`, `delete()`.

**Commit:** `git commit -m "feat: add SqliteGoalRepository"`

---

### Task 12: SQLite SubscriptionRepository

**Files:**
- Create: `packages/core/src/flux_core/sqlite/subscription_repo.py`
- Test: `packages/core/tests/test_repositories/test_subscription_repo.py`

Reference: `packages/core/src/flux_core/db/subscription_repo.py`

Methods: `create()`, `get()`, `list_by_user()`, `get_due()`, `advance_next_date()`, `toggle_active()`, `delete()`.

**Commit:** `git commit -m "feat: add SqliteSubscriptionRepository"`

---

### Task 13: SQLite AssetRepository

**Files:**
- Create: `packages/core/src/flux_core/sqlite/asset_repo.py`
- Test: `packages/core/tests/test_repositories/test_asset_repo.py`

Reference: `packages/core/src/flux_core/db/asset_repo.py`

Methods: `create()`, `get()`, `list_by_user()`, `get_due()`, `advance_next_date()`, `update_amount()`, `deactivate()`, `delete()`.

**Commit:** `git commit -m "feat: add SqliteAssetRepository"`

---

### Task 14: SQLite MemoryRepository

**Files:**
- Create: `packages/core/src/flux_core/sqlite/memory_repo.py`
- Test: `packages/core/tests/test_repositories/test_memory_repo.py`

Reference: `packages/core/src/flux_core/db/memory_repo.py`

Methods: `create()`, `get_by_ids()`, `list_by_user()`. No `search_by_embedding()` — that moves to the use case via ZvecStore.

**Commit:** `git commit -m "feat: add SqliteMemoryRepository"`

---

### Task 15: SQLite Bot Repositories

**Files:**
- Create: `packages/core/src/flux_core/sqlite/bot/__init__.py`
- Create: `packages/core/src/flux_core/sqlite/bot/message_repo.py`
- Create: `packages/core/src/flux_core/sqlite/bot/session_repo.py`
- Create: `packages/core/src/flux_core/sqlite/bot/scheduled_task_repo.py`
- Create: `packages/core/src/flux_core/sqlite/bot/outbound_repo.py`
- Test: `packages/core/tests/test_repositories/test_bot/__init__.py`
- Test: `packages/core/tests/test_repositories/test_bot/test_message_repo.py`
- Test: `packages/core/tests/test_repositories/test_bot/test_session_repo.py`
- Test: `packages/core/tests/test_repositories/test_bot/test_scheduled_task_repo.py`
- Test: `packages/core/tests/test_repositories/test_bot/test_outbound_repo.py`

Reference the current agent-bot DB code and mcp-server scheduler repos:
- `packages/mcp-server/src/flux_mcp/db/savings_scheduler_repo.py`
- `packages/mcp-server/src/flux_mcp/db/subscription_scheduler_repo.py`
- Agent bot poller/handler code for message/session/outbound patterns

These repos are now in core (not split across mcp-server and agent-bot).

**Commit:** `git commit -m "feat: add SQLite bot repositories (message, session, scheduler, outbound)"`

---

## Phase 4: Use Cases

Business logic extracted into Use Case classes. Each use case tested with mocked repos.

---

### Task 16: Transaction Use Cases

**Files:**
- Create: `packages/core/src/flux_core/use_cases/__init__.py`
- Create: `packages/core/src/flux_core/use_cases/transactions/__init__.py`
- Create: `packages/core/src/flux_core/use_cases/transactions/add_transaction.py`
- Create: `packages/core/src/flux_core/use_cases/transactions/list_transactions.py`
- Create: `packages/core/src/flux_core/use_cases/transactions/search_transactions.py`
- Create: `packages/core/src/flux_core/use_cases/transactions/update_transaction.py`
- Create: `packages/core/src/flux_core/use_cases/transactions/delete_transaction.py`
- Test: `packages/core/tests/test_use_cases/__init__.py`
- Test: `packages/core/tests/test_use_cases/test_transactions.py`

Reference current tool functions: `packages/core/src/flux_core/tools/transaction_tools.py`

Key patterns:
- `AddTransaction`: UoW + embedding_svc. Creates Transaction model, generates embedding, dual-write via UoW.
- `ListTransactions`: Read-only, takes TransactionRepository directly.
- `SearchTransactions`: Read-only, queries ZvecStore for IDs, then fetches from TransactionRepository.
- `UpdateTransaction`: UoW + embedding_svc. Updates SQLite + re-embeds in zvec.
- `DeleteTransaction`: UoW. Deletes from SQLite + zvec.

Test with mocked repos (no real DB). Verify UoW interactions.

**Commit:** `git commit -m "feat: add transaction use cases (add, list, search, update, delete)"`

---

### Task 17: Budget Use Cases

**Files:**
- Create: `packages/core/src/flux_core/use_cases/budgets/__init__.py`
- Create: `packages/core/src/flux_core/use_cases/budgets/set_budget.py`
- Create: `packages/core/src/flux_core/use_cases/budgets/list_budgets.py`
- Create: `packages/core/src/flux_core/use_cases/budgets/remove_budget.py`
- Test: `packages/core/tests/test_use_cases/test_budgets.py`

Reference: `packages/core/src/flux_core/tools/financial_tools.py` (budget section)

All SQLite-only — no zvec. `SetBudget` uses UoW. `ListBudgets` is read-only.

**Commit:** `git commit -m "feat: add budget use cases"`

---

### Task 18: Goal Use Cases

**Files:**
- Create: `packages/core/src/flux_core/use_cases/goals/__init__.py`
- Create: `packages/core/src/flux_core/use_cases/goals/create_goal.py`
- Create: `packages/core/src/flux_core/use_cases/goals/list_goals.py`
- Create: `packages/core/src/flux_core/use_cases/goals/deposit_to_goal.py`
- Create: `packages/core/src/flux_core/use_cases/goals/withdraw_from_goal.py`
- Create: `packages/core/src/flux_core/use_cases/goals/delete_goal.py`
- Test: `packages/core/tests/test_use_cases/test_goals.py`

Reference: `packages/core/src/flux_core/tools/financial_tools.py` (goal section)

**Commit:** `git commit -m "feat: add goal use cases"`

---

### Task 19: Subscription Use Cases

**Files:**
- Create: `packages/core/src/flux_core/use_cases/subscriptions/__init__.py`
- Create: `packages/core/src/flux_core/use_cases/subscriptions/create_subscription.py`
- Create: `packages/core/src/flux_core/use_cases/subscriptions/list_subscriptions.py`
- Create: `packages/core/src/flux_core/use_cases/subscriptions/toggle_subscription.py`
- Create: `packages/core/src/flux_core/use_cases/subscriptions/delete_subscription.py`
- Test: `packages/core/tests/test_use_cases/test_subscriptions.py`

Reference: `packages/mcp-server/src/flux_mcp/tools/financial_tools.py` — `_create_subscription_with_scheduler()`, `_toggle_subscription_with_scheduler()`, `_delete_subscription_with_scheduler()`.

**Critical:** `CreateSubscription` writes to both `subscriptions` and `bot_scheduled_tasks` tables in one UoW transaction. Same for toggle and delete.

**Commit:** `git commit -m "feat: add subscription use cases with scheduler coordination"`

---

### Task 20: Savings Use Cases

**Files:**
- Create: `packages/core/src/flux_core/use_cases/savings/__init__.py`
- Create: `packages/core/src/flux_core/use_cases/savings/create_savings.py`
- Create: `packages/core/src/flux_core/use_cases/savings/process_interest.py`
- Create: `packages/core/src/flux_core/use_cases/savings/withdraw_savings.py`
- Test: `packages/core/tests/test_use_cases/test_savings.py`

Reference: `packages/mcp-server/src/flux_mcp/tools/savings_tools.py`

**Critical:** `CreateSavings` writes `assets` + `bot_scheduled_tasks`. `WithdrawSavings` writes `assets` + `transactions` + deletes `bot_scheduled_tasks` — all in one UoW. `ProcessInterest` compounds and updates `assets.amount` + creates new scheduler task.

**Commit:** `git commit -m "feat: add savings use cases with interest processing and withdrawal"`

---

### Task 21: Memory Use Cases

**Files:**
- Create: `packages/core/src/flux_core/use_cases/memory/__init__.py`
- Create: `packages/core/src/flux_core/use_cases/memory/remember.py`
- Create: `packages/core/src/flux_core/use_cases/memory/recall.py`
- Create: `packages/core/src/flux_core/use_cases/memory/list_memories.py`
- Test: `packages/core/tests/test_use_cases/test_memory.py`

Reference: `packages/core/src/flux_core/tools/memory_tools.py`

`Remember`: UoW + embedding_svc. Dual-write to SQLite + zvec.
`Recall`: Read-only. Search zvec → fetch from SQLite.
`ListMemories`: Read-only. SQLite only.

**Commit:** `git commit -m "feat: add memory use cases (remember, recall, list)"`

---

### Task 22: Analytics Use Cases

**Files:**
- Create: `packages/core/src/flux_core/use_cases/analytics/__init__.py`
- Create: `packages/core/src/flux_core/use_cases/analytics/get_summary.py`
- Create: `packages/core/src/flux_core/use_cases/analytics/get_trends.py`
- Create: `packages/core/src/flux_core/use_cases/analytics/get_category_breakdown.py`
- Test: `packages/core/tests/test_use_cases/test_analytics.py`

Reference: `packages/core/src/flux_core/tools/analytics_tools.py`

All read-only, SQLite-only (aggregation queries: SUM, GROUP BY, etc.).

**Commit:** `git commit -m "feat: add analytics use cases"`

---

### Task 23: Bot Use Cases

**Files:**
- Create: `packages/core/src/flux_core/use_cases/bot/__init__.py`
- Create: `packages/core/src/flux_core/use_cases/bot/process_message.py`
- Create: `packages/core/src/flux_core/use_cases/bot/send_outbound.py`
- Create: `packages/core/src/flux_core/use_cases/bot/create_scheduled_task.py`
- Create: `packages/core/src/flux_core/use_cases/bot/fire_scheduled_task.py`
- Test: `packages/core/tests/test_use_cases/test_bot.py`

`ProcessMessage`: UoW. Marks message processed + inserts outbound + upserts session. Emits `OutboundCreated`.
`SendOutbound`: UoW. Marks outbound sent/failed.
`CreateScheduledTask`: UoW. Inserts into `bot_scheduled_tasks`. Emits `ScheduledTaskCreated`.
`FireScheduledTask`: UoW. Inserts synthetic message + advances/completes task. Emits `MessageCreated`.

**Commit:** `git commit -m "feat: add bot use cases (message processing, scheduling)"`

---

### Task 24: IPC Use Cases (send_message, schedule_task, etc.)

**Files:**
- Create: `packages/core/src/flux_core/use_cases/bot/send_message.py`
- Create: `packages/core/src/flux_core/use_cases/bot/schedule_task.py`
- Create: `packages/core/src/flux_core/use_cases/bot/list_tasks.py`
- Create: `packages/core/src/flux_core/use_cases/bot/pause_task.py`
- Create: `packages/core/src/flux_core/use_cases/bot/resume_task.py`
- Create: `packages/core/src/flux_core/use_cases/bot/cancel_task.py`
- Test: `packages/core/tests/test_use_cases/test_ipc.py`

Reference: `packages/core/src/flux_core/tools/ipc_tools.py`

**Commit:** `git commit -m "feat: add IPC use cases for messaging and task scheduling"`

---

## Phase 5: Interface Layer Updates

Wire use cases into MCP server, API server, and tools layer.

---

### Task 25: Update MCP server

**Files:**
- Modify: `packages/mcp-server/src/flux_mcp/server.py`
- Modify: `packages/mcp-server/src/flux_mcp/tools/transaction_tools.py`
- Modify: `packages/mcp-server/src/flux_mcp/tools/financial_tools.py`
- Modify: `packages/mcp-server/src/flux_mcp/tools/savings_tools.py`
- Modify: `packages/mcp-server/src/flux_mcp/tools/memory_tools.py`
- Modify: `packages/mcp-server/src/flux_mcp/tools/analytics_tools.py`
- Modify: `packages/mcp-server/src/flux_mcp/tools/profile_tools.py`
- Modify: `packages/mcp-server/src/flux_mcp/tools/ipc_tools.py`
- Delete: `packages/mcp-server/src/flux_mcp/db/` (scheduler repos moved to core)
- Modify: `packages/mcp-server/pyproject.toml` (remove testcontainers, asyncpg)

**Key changes:**

1. `server.py`:
   - Replace `_db = None` (asyncpg Database) with SQLite Database + ZvecStore + EventBus initialization
   - Replace `get_db()` with `get_uow()`, `get_repos()`, `get_embedding_svc()`
   - `register_*_tools()` calls pass use-case factories instead of raw DB

2. Each `tools/*.py`:
   - MCP tool functions become thin adapters that instantiate Use Case → call `execute()` → return dict
   - Remove direct DB/repo access
   - Remove scheduler repo logic (now in use cases)

3. Delete `db/savings_scheduler_repo.py` and `db/subscription_scheduler_repo.py` (moved to core repos)

**Commit:** `git commit -m "refactor: update MCP server to use use cases and SQLite+zvec"`

---

### Task 26: Update API server

**Files:**
- Modify: `packages/api-server/src/flux_api/app.py`
- Modify: `packages/api-server/src/flux_api/deps.py`
- Modify: `packages/api-server/src/flux_api/routes/transactions.py`
- Modify: `packages/api-server/src/flux_api/routes/budgets.py`
- Modify: `packages/api-server/src/flux_api/routes/goals.py`
- Modify: `packages/api-server/src/flux_api/routes/subscriptions.py`
- Modify: `packages/api-server/src/flux_api/routes/assets.py`
- Modify: `packages/api-server/src/flux_api/routes/analytics.py`
- Modify: `packages/api-server/src/flux_api/routes/profile.py`
- Modify: `packages/api-server/pyproject.toml`

**Key changes:**

1. `app.py`: Initialize SQLite Database + ZvecStore + EventBus on startup. Run migrations.
2. `deps.py`: Provide `get_uow()`, `get_repos()`, `get_embedding_svc()` as FastAPI dependencies.
3. Each route: Instantiate Use Case → call `execute()` → return response.

**Commit:** `git commit -m "refactor: update API server to use use cases and SQLite+zvec"`

---

### Task 27: Update agent-bot

**Files:**
- Modify: `packages/agent-bot/src/flux_bot/main.py`
- Modify: `packages/agent-bot/src/flux_bot/poller/` (replace with EventBus dispatcher)
- Modify: `packages/agent-bot/src/flux_bot/handler/`
- Modify: `packages/agent-bot/src/flux_bot/outbound/`
- Modify: `packages/agent-bot/src/flux_bot/scheduler/`
- Modify: `packages/agent-bot/pyproject.toml`

**Key changes:**

1. `main.py`: Initialize shared SQLite + EventBus. Subscribe dispatcher to `MessageCreated`, outbound worker to `OutboundCreated`.
2. Replace poller with EventBus-driven dispatcher.
3. Replace LISTEN/NOTIFY outbound worker with EventBus subscriber.
4. Scheduler worker: polls SQLite instead of PostgreSQL (same polling pattern, just different DB).
5. Remove asyncpg dependency.

**Commit:** `git commit -m "refactor: update agent-bot to use EventBus and SQLite"`

---

### Task 28: Delete old asyncpg layer

**Files:**
- Delete: `packages/core/src/flux_core/db/` (entire directory)
- Delete: `packages/core/src/flux_core/migrations/` (replaced by sqlite/migrations/)
- Delete: `packages/core/src/flux_core/vector_store/` (if exists, replaced by vector/)
- Delete: `packages/core/src/flux_core/tools/` (replaced by use_cases/)
- Delete: `packages/core/tests/test_db/` (replaced by test_repositories/)
- Delete: `packages/core/tests/test_tools/` (replaced by test_use_cases/)

**Step 1: Verify no remaining imports**

Run: `cd packages && grep -r "from flux_core.db" --include="*.py" | grep -v __pycache__`
Expected: No results (all imports updated in Tasks 25-27)

Run: `cd packages && grep -r "from flux_core.tools" --include="*.py" | grep -v __pycache__`
Expected: No results

Run: `cd packages && grep -r "asyncpg" --include="*.py" | grep -v __pycache__`
Expected: No results

**Step 2: Delete**

```bash
rm -rf packages/core/src/flux_core/db/
rm -rf packages/core/src/flux_core/migrations/
rm -rf packages/core/src/flux_core/vector_store/
rm -rf packages/core/src/flux_core/tools/
rm -rf packages/core/tests/test_db/
rm -rf packages/core/tests/test_tools/
```

**Step 3: Run all core tests**

Run: `cd packages/core && pytest tests/ -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add -A
git commit -m "refactor: remove old asyncpg/pgvector layer and tools (replaced by SQLite+zvec+use cases)"
```

---

## Phase 6: Testing

E2E and performance tests for the new architecture.

---

### Task 29: MCP server E2E tests

**Files:**
- Modify: `packages/mcp-server/tests/conftest.py`
- Create: `packages/mcp-server/tests/test_e2e/conftest.py` (seeded SQLite + zvec fixtures)
- Modify: `packages/mcp-server/tests/test_e2e/test_tool_execution.py`
- Modify: remaining test files in `packages/mcp-server/tests/`

**Key changes:**
- Replace PostgreSQL testcontainer fixtures with temp SQLite + temp zvec
- `seeded_server` fixture: creates SQLite DB, runs migrations, seeds test data (users, transactions, budgets, goals), creates ZvecStore with seeded embeddings, starts FastMCP server
- Update all E2E tests to use new fixtures
- Add tests for dual-write verification (transaction added → verify both SQLite and zvec)

**Commit:** `git commit -m "test: update MCP server E2E tests for SQLite+zvec"`

---

### Task 30: API server E2E tests

**Files:**
- Create: `packages/api-server/tests/test_e2e/__init__.py`
- Create: `packages/api-server/tests/test_e2e/conftest.py`
- Create: `packages/api-server/tests/test_e2e/test_transactions_api.py`
- Create: `packages/api-server/tests/test_e2e/test_budgets_api.py`
- Create: `packages/api-server/tests/test_e2e/test_goals_api.py`
- Create: `packages/api-server/tests/test_e2e/test_subscriptions_api.py`
- Create: `packages/api-server/tests/test_e2e/test_analytics_api.py`
- Modify: existing API test files

**Key changes:**
- `seeded_app` fixture: creates temp SQLite + zvec, runs migrations, seeds data, creates FastAPI TestClient
- Seed data: 2 users, 10 transactions (mix of income/expense across categories), 3 budgets, 2 goals, 2 subscriptions
- Test full HTTP flow: POST create → GET list → GET by ID → DELETE
- Verify dual-write: POST transaction → check both SQLite and zvec contain the data

**Commit:** `git commit -m "test: add API server E2E tests with seeded SQLite+zvec"`

---

### Task 31: Performance tests

**Files:**
- Create: `packages/api-server/tests/test_perf/__init__.py`
- Create: `packages/api-server/tests/test_perf/conftest.py`
- Create: `packages/api-server/tests/test_perf/test_transaction_perf.py`
- Create: `packages/api-server/tests/test_perf/test_search_perf.py`
- Create: `packages/mcp-server/tests/test_perf/__init__.py`
- Create: `packages/mcp-server/tests/test_perf/conftest.py`
- Create: `packages/mcp-server/tests/test_perf/test_tool_perf.py`

**Tests:**
1. **Add transaction latency** — benchmark `POST /transactions`, assert p50 < 50ms
2. **List transactions latency** — benchmark `GET /transactions`, assert p50 < 20ms
3. **Semantic search latency** — benchmark search with embedding, assert p50 < 200ms
4. **Concurrent writes** — 5 threads × 50 writes, all succeed (WAL test)
5. **MCP tool latency** — benchmark `add_transaction` MCP tool call

Use `pytest-benchmark` for latency. Use `concurrent.futures.ThreadPoolExecutor` for concurrency test.

**Commit:** `git commit -m "test: add performance benchmarks for API and MCP servers"`

---

## Phase 7: Infrastructure & Tooling

---

### Task 32: Dev script

**Files:**
- Create: `dev.sh`

Use the full script from design doc Section 9. Make it executable.

**Step 1: Create dev.sh**

**Step 2: Test it**

Run: `chmod +x dev.sh && ./dev.sh`
Expected: Creates venv, installs packages, runs migrations, starts services

**Step 3: Commit**

```bash
git add dev.sh
git commit -m "chore: add dev.sh for local development with uv and hot reload"
```

---

### Task 33: Docker — single container

**Files:**
- Create: `Dockerfile`
- Create: `nginx.conf`
- Create: `entrypoint.py`
- Modify: `docker-compose.yml` (replace multi-service with single service)
- Create: `docker-compose.test.yml`

**Step 1: Create Dockerfile**

Multi-stage build from design doc Section 7:
- Stage 1: `node:22-slim` builds web-ui
- Stage 2: `python:3.12-slim` + nginx + Node.js + Claude Code CLI

**Step 2: Create nginx.conf**

Serve static files at `/`, proxy `/api/` to `127.0.0.1:8000`.

**Step 3: Create entrypoint.py**

Start nginx (background) + uvicorn + agent-bot.

**Step 4: Create docker-compose.test.yml**

```yaml
services:
  test:
    build: .
    command: >
      sh -c "
        pytest packages/core/tests/ -v --tb=short &&
        pytest packages/api-server/tests/test_e2e/ -v --tb=short &&
        pytest packages/mcp-server/tests/test_e2e/ -v --tb=short &&
        pytest packages/api-server/tests/test_perf/ -v --benchmark-only &&
        pytest packages/mcp-server/tests/test_perf/ -v --benchmark-only
      "
```

**Step 5: Verify Docker build**

Run: `docker compose build flux`
Expected: Builds successfully

**Step 6: Commit**

```bash
git add Dockerfile nginx.conf entrypoint.py docker-compose.yml docker-compose.test.yml
git commit -m "feat: add single-container Docker build with Nginx + SQLite + zvec"
```

---

### Task 34: Update docker-compose.dev.yml

**Files:**
- Modify: `docker-compose.dev.yml`

Remove PostgreSQL, Ollama, adminer services. Replace with single `flux` service for development that mounts source code.

**Commit:** `git commit -m "chore: simplify docker-compose.dev.yml for single-container arch"`

---

### Task 35: Update README.md

**Files:**
- Modify: `README.md`

Update with:

1. **Quick Start (Docker):**
   ```bash
   docker run -d -p 80:80 -v flux_data:/data \
     -e TELEGRAM_BOT_TOKEN=... -e CLAUDE_AUTH_TOKEN=... \
     yourname/flux-finance
   ```

2. **Development:**
   ```bash
   git clone ... && cd FluxFinance
   ./dev.sh
   ```

3. **Testing:**
   ```bash
   docker compose -f docker-compose.test.yml up --build
   ```

4. Updated architecture diagram showing SQLite + zvec + EventBus

5. Updated environment variables table

**Commit:** `git commit -m "docs: update README with new dev/prod/test instructions"`

---

### Task 36: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

Update:
- Architecture section (SQLite + zvec, not PostgreSQL)
- Tech stack (remove asyncpg, pgvector, testcontainers; add zvec, sqlite3)
- Commands (new dev.sh, new migration command, new test commands)
- Key design decisions (UoW, Use Cases, EventBus, repository interfaces)
- Testing section (temp SQLite, no testcontainers)

**Commit:** `git commit -m "docs: update CLAUDE.md for SQLite+zvec architecture"`

---

## Phase 8: Final Verification

---

### Task 37: Full test suite

**Step 1: Run all core tests**

```bash
cd packages/core && pytest tests/ -v
```

**Step 2: Run all API tests**

```bash
cd packages/api-server && pytest tests/ -v
```

**Step 3: Run all MCP tests**

```bash
cd packages/mcp-server && pytest tests/ -v
```

**Step 4: Run linter**

```bash
cd packages/core && ruff check src/ tests/
cd packages/api-server && ruff check src/ tests/
cd packages/mcp-server && ruff check src/ tests/
```

**Step 5: Docker build and test**

```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

**Step 6: Verify dev script**

```bash
./dev.sh  # Ctrl+C after confirming services start
```

All must pass before merging.

---

## Task Dependency Graph

```
Phase 1 (Infrastructure):
  Task 1 (deps) → Task 2 (events) ─┐
                   Task 3 (sqlite) ──┤
                   Task 4 (migrate) ─┤→ Task 6 (UoW)
                   Task 5 (zvec) ────┘

Phase 2 (Interfaces):
  Task 7 (protocols) — depends on models (unchanged)

Phase 3 (Repos):
  Tasks 8-15 — depend on Task 3, 4, 7

Phase 4 (Use Cases):
  Tasks 16-24 — depend on Task 6, 7, and relevant repos

Phase 5 (Interface Updates):
  Task 25 (MCP) — depends on all use cases
  Task 26 (API) — depends on all use cases
  Task 27 (Bot) — depends on use cases + events
  Task 28 (Delete old) — depends on 25, 26, 27

Phase 6 (Testing):
  Tasks 29-31 — depend on 25, 26

Phase 7 (Infra):
  Tasks 32-36 — can run in parallel after Phase 5

Phase 8 (Verification):
  Task 37 — depends on everything
```

---

## Estimated Task Count

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 6 | Core infrastructure |
| 2 | 1 | Repository interfaces |
| 3 | 8 | SQLite repo implementations |
| 4 | 9 | Use cases |
| 5 | 4 | Interface layer updates |
| 6 | 3 | E2E + perf tests |
| 7 | 5 | Docker, dev script, docs |
| 8 | 1 | Final verification |
| **Total** | **37** | |
