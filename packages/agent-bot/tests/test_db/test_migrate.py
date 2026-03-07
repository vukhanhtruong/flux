"""Test that bot table migrations work correctly with SQLite."""
from flux_bot.db.migrate import run_migrations
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate


async def test_migrations_create_bot_tables(tmp_path):
    """Core migrations create bot_messages, bot_sessions, bot_scheduled_tasks."""
    db_path = str(tmp_path / "test.db")
    db = Database(db_path)
    db.connect()
    migrate(db)

    conn = db.connection()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {r["name"] for r in rows}

    assert "bot_messages" in table_names
    assert "bot_sessions" in table_names
    assert "bot_scheduled_tasks" in table_names
    db.disconnect()


async def test_bot_migrations_are_noop(tmp_path):
    """run_migrations is a no-op since bot tables are in core migrations."""
    db_path = str(tmp_path / "test.db")
    await run_migrations(db_path)  # Should not raise
    await run_migrations(db_path)  # Should not raise
