"""Run agent-bot database migrations.

With SQLite, bot tables are in the shared core migrations.
This module is kept for API compatibility but is now a no-op —
core's migrate() already creates all tables including bot_* tables.
"""


async def run_migrations(database_path: str) -> None:
    """No-op — bot table migrations are now handled by core's migrate()."""
    pass
