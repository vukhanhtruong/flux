"""Confirm bot_user_llm_config table is created by core migrations."""
import sqlite3

from flux_bot.db.migrate import run_migrations
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate


async def test_migration_creates_table(tmp_path):
    db_path = tmp_path / "flux.db"
    # Core migrations apply the bot_user_llm_config schema.
    db = Database(str(db_path))
    db.connect()
    migrate(db)
    db.disconnect()
    # run_migrations is a documented no-op; calling it must still be safe.
    await run_migrations(str(db_path))

    con = sqlite3.connect(db_path)
    cur = con.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name='bot_user_llm_config'"
    )
    assert cur.fetchone() is not None

    cols = {row[1] for row in con.execute("PRAGMA table_info(bot_user_llm_config)")}
    assert cols >= {
        "user_id",
        "provider",
        "model",
        "base_url",
        "api_key_encrypted",
        "created_at",
        "updated_at",
    }
    con.close()
