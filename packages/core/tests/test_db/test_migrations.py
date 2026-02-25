import pytest
from flux_core.migrations.migrate import migrate


async def test_migration_creates_tables(pg_url):
    await migrate(pg_url)

    import asyncpg
    conn = await asyncpg.connect(pg_url)
    try:
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        table_names = {r["table_name"] for r in tables}
        assert "users" in table_names
        assert "transactions" in table_names
        assert "budgets" in table_names
        assert "savings_goals" in table_names
        assert "subscriptions" in table_names
        assert "assets" in table_names
        assert "agent_memory" in table_names
        assert "schema_migrations" in table_names
    finally:
        await conn.close()


async def test_migration_is_idempotent(pg_url):
    """Running migrate twice should not error."""
    await migrate(pg_url)
    await migrate(pg_url)  # Should be a no-op
