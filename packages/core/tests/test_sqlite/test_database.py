from __future__ import annotations

from flux_core.sqlite import Database


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
