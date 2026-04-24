"""Run agent-bot database migrations.

Bot-specific tables (bot_user_llm_config, etc.) may not exist when the
installed flux_core package predates the migration that introduced them.
run_migrations() ensures they exist idempotently via CREATE TABLE IF NOT EXISTS.
"""

import sqlite3


async def run_migrations(database_path: str) -> None:
    """Create bot-specific tables that may not be covered by flux_core migrations."""
    conn = sqlite3.connect(database_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_user_llm_config (
                user_id           TEXT PRIMARY KEY,
                provider          TEXT NOT NULL,
                model             TEXT NOT NULL,
                base_url          TEXT,
                api_key_encrypted TEXT NOT NULL,
                created_at        TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_bot_user_llm_config_provider
                ON bot_user_llm_config(provider)
            """
        )
        conn.commit()
    finally:
        conn.close()
