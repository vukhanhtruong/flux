import asyncpg
from flux_bot.db.migrate import run_migrations


async def test_run_migrations_creates_bot_tables(pg_url):
    """Migrations create bot_messages, bot_sessions, bot_scheduled_tasks, bot_task_run_logs."""
    await run_migrations(pg_url)

    conn = await asyncpg.connect(pg_url)
    try:
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        table_names = {r["tablename"] for r in tables}
        assert "bot_messages" in table_names
        assert "bot_sessions" in table_names
        assert "bot_scheduled_tasks" in table_names
        assert "bot_task_run_logs" in table_names
    finally:
        await conn.close()


async def test_run_migrations_idempotent(pg_url):
    """Running migrations twice does not fail."""
    await run_migrations(pg_url)
    await run_migrations(pg_url)  # Should not raise
