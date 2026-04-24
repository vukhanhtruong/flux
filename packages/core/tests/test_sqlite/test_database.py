from __future__ import annotations

from flux_core.sqlite import Database
from flux_core.sqlite.migrations.migrate import migrate


def test_connect_sets_wal_mode(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    try:
        row = db.fetchone("PRAGMA journal_mode")
        assert row is not None
        assert row[0] == "wal"
    finally:
        db.disconnect()


def test_foreign_keys_enabled(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    try:
        row = db.fetchone("PRAGMA foreign_keys")
        assert row is not None
        assert row[0] == 1
    finally:
        db.disconnect()


def test_execute_and_fetch(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    try:
        db.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO items (name) VALUES (?)", ("apple",))
        db.execute("INSERT INTO items (name) VALUES (?)", ("banana",))
        rows = db.fetchall("SELECT name FROM items ORDER BY name")
        assert len(rows) == 2
        assert rows[0]["name"] == "apple"
        assert rows[1]["name"] == "banana"
    finally:
        db.disconnect()


def test_fetchone_returns_none_when_empty(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    try:
        db.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        row = db.fetchone("SELECT * FROM items WHERE id = ?", (999,))
        assert row is None
    finally:
        db.disconnect()


def test_transaction_commit(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    try:
        db.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        conn = db.connection()
        conn.execute("BEGIN")
        conn.execute("INSERT INTO items (name) VALUES (?)", ("committed",))
        conn.execute("COMMIT")
        row = db.fetchone("SELECT name FROM items WHERE name = ?", ("committed",))
        assert row is not None
        assert row["name"] == "committed"
    finally:
        db.disconnect()


def test_transaction_rollback(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    try:
        db.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        conn = db.connection()
        conn.execute("BEGIN")
        conn.execute("INSERT INTO items (name) VALUES (?)", ("rolled_back",))
        conn.execute("ROLLBACK")
        row = db.fetchone("SELECT name FROM items WHERE name = ?", ("rolled_back",))
        assert row is None
    finally:
        db.disconnect()


def test_connect_loads_sqlite_vec(tmp_path):
    db = Database(str(tmp_path / "flux.db"))
    db.connect()
    try:
        row = db.fetchone("SELECT vec_version() AS v")
        assert row is not None
        assert row["v"].startswith("v")
    finally:
        db.disconnect()


def test_migration_creates_vec0_tables(tmp_path):
    db = Database(str(tmp_path / "flux.db"))
    db.connect()
    try:
        migrate(db)

        tables = {
            r["name"]
            for r in db.fetchall(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "vec_transaction_embeddings" in tables
        assert "vec_memory_embeddings" in tables
    finally:
        db.disconnect()
