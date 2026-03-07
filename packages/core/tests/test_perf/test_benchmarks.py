"""Performance benchmarks for SQLite operations.

Uses pytest-benchmark for latency and ThreadPoolExecutor for concurrency.
Targets:
  - add_transaction p50 < 50ms
  - list_transactions p50 < 20ms
  - concurrent writes: 5 threads x 50 writes (WAL stress test)
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from decimal import Decimal

import pytest

from flux_core.models.transaction import TransactionCreate, TransactionType
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository

USER_ID = "bench:user1"


@pytest.fixture
def bench_db(tmp_path):
    """Fresh SQLite DB for benchmarks."""
    db = Database(str(tmp_path / "bench.db"))
    db.connect()
    migrate(db)
    conn = db.connection()
    conn.execute(
        "INSERT INTO users (id, platform, platform_id, display_name) VALUES (?, ?, ?, ?)",
        (USER_ID, "bench", "user1", "Bench User"),
    )
    conn.commit()
    yield db
    db.disconnect()


@pytest.fixture
def bench_repo(bench_db):
    return SqliteTransactionRepository(bench_db.connection())


def _make_txn(i: int = 0) -> TransactionCreate:
    return TransactionCreate(
        user_id=USER_ID,
        date=date(2026, 3, 1),
        amount=Decimal("100.00"),
        category="Food",
        description=f"Bench transaction {i}",
        type=TransactionType.expense,
    )


def test_add_transaction_latency(bench_repo, benchmark):
    """Benchmark: single transaction insert latency."""
    counter = {"i": 0}

    def do_insert():
        counter["i"] += 1
        bench_repo.create(_make_txn(counter["i"]))

    result = benchmark(do_insert)
    # pytest-benchmark handles stats; we assert p50 < 50ms
    # benchmark.stats gives us median
    assert benchmark.stats.stats.median < 0.050, (
        f"p50 latency {benchmark.stats.stats.median * 1000:.1f}ms exceeds 50ms target"
    )


def test_list_transactions_latency(bench_repo, benchmark):
    """Benchmark: list transactions latency with 100 rows seeded."""
    # Seed 100 transactions
    for i in range(100):
        bench_repo.create(_make_txn(i))

    def do_list():
        return bench_repo.list_by_user(USER_ID, limit=50)

    result = benchmark(do_list)
    assert benchmark.stats.stats.median < 0.020, (
        f"p50 latency {benchmark.stats.stats.median * 1000:.1f}ms exceeds 20ms target"
    )


def test_concurrent_writes_wal(tmp_path):
    """Stress test: 5 threads x 50 writes using WAL mode.

    Verifies that concurrent writes succeed without SQLITE_BUSY errors
    when WAL mode is enabled with busy_timeout.
    """
    db_path = str(tmp_path / "concurrent.db")

    # Set up DB
    db = Database(db_path)
    db.connect()
    migrate(db)
    conn = db.connection()
    conn.execute(
        "INSERT INTO users (id, platform, platform_id, display_name) VALUES (?, ?, ?, ?)",
        (USER_ID, "bench", "user1", "Bench User"),
    )
    conn.commit()
    db.disconnect()

    n_threads = 5
    n_writes_per_thread = 50
    errors = []

    def worker(thread_id: int):
        """Each worker opens its own connection and writes transactions."""
        import sqlite3

        worker_conn = sqlite3.connect(
            db_path, timeout=10, isolation_level=None
        )
        worker_conn.row_factory = sqlite3.Row
        worker_conn.execute("PRAGMA journal_mode = WAL")
        worker_conn.execute("PRAGMA busy_timeout = 5000")

        repo = SqliteTransactionRepository(worker_conn)
        for i in range(n_writes_per_thread):
            try:
                txn = TransactionCreate(
                    user_id=USER_ID,
                    date=date(2026, 3, 1),
                    amount=Decimal(f"{thread_id * 100 + i + 1}.00"),
                    category="Concurrent",
                    description=f"Thread {thread_id} txn {i}",
                    type=TransactionType.expense,
                )
                repo.create(txn)
            except Exception as e:
                errors.append((thread_id, i, str(e)))

        worker_conn.close()

    with ThreadPoolExecutor(max_workers=n_threads) as pool:
        futures = [pool.submit(worker, tid) for tid in range(n_threads)]
        for f in as_completed(futures):
            f.result()  # propagate exceptions

    assert len(errors) == 0, f"Concurrent write errors: {errors}"

    # Verify all writes landed
    db2 = Database(db_path)
    db2.connect()
    repo2 = SqliteTransactionRepository(db2.connection())
    all_txns = repo2.list_by_user(USER_ID, limit=1000)
    db2.disconnect()

    expected = n_threads * n_writes_per_thread
    assert len(all_txns) == expected, (
        f"Expected {expected} transactions, got {len(all_txns)}"
    )
