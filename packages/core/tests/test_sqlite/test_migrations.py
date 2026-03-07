from __future__ import annotations

from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate


EXPECTED_TABLES = {
    "users",
    "transactions",
    "budgets",
    "savings_goals",
    "subscriptions",
    "assets",
    "agent_memory",
    "bot_messages",
    "bot_sessions",
    "bot_scheduled_tasks",
    "bot_outbound_messages",
    "system_config",
    "schema_migrations",
}


def test_migrate_creates_all_tables(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    try:
        migrate(db)
        rows = db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        table_names = {row["name"] for row in rows}
        assert table_names == EXPECTED_TABLES
    finally:
        db.disconnect()


def test_migrate_is_idempotent(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    try:
        migrate(db)
        migrate(db)
        row = db.fetchone("SELECT MAX(version) as v FROM schema_migrations")
        assert row["v"] == 2
    finally:
        db.disconnect()


def test_schema_migrations_tracked(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    try:
        migrate(db)
        row = db.fetchone("SELECT version FROM schema_migrations WHERE version = 1")
        assert row is not None
        assert row["version"] == 1
        row2 = db.fetchone("SELECT version FROM schema_migrations WHERE version = 2")
        assert row2 is not None
        assert row2["version"] == 2
    finally:
        db.disconnect()


def test_system_config_table_schema(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    try:
        migrate(db)
        # Verify we can insert and query system_config
        db.execute(
            "INSERT INTO system_config (key, value, encrypted) VALUES (?, ?, ?)",
            ("test_key", "test_value", 0),
        )
        db.connection().commit()
        row = db.fetchone("SELECT key, value, encrypted, updated_at FROM system_config WHERE key = ?", ("test_key",))
        assert row["key"] == "test_key"
        assert row["value"] == "test_value"
        assert row["encrypted"] == 0
        assert row["updated_at"] is not None
    finally:
        db.disconnect()
