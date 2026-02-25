import pytest
from flux_core.db.connection import Database


@pytest.fixture
async def db(pg_url):
    """Create a Database instance connected to the test PostgreSQL."""
    database = Database(pg_url)
    await database.connect()
    yield database
    await database.disconnect()


async def test_connect_and_query(db):
    result = await db.fetchval("SELECT 1")
    assert result == 1


async def test_pool_is_created(db):
    assert db.pool is not None
