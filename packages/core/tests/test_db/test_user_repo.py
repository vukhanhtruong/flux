import pytest

from flux_core.db.connection import Database
from flux_core.db.user_repo import UserRepository
from flux_core.migrations.migrate import migrate


@pytest.fixture
async def db(pg_url):
    await migrate(pg_url)
    database = Database(pg_url)
    await database.connect()
    yield database
    await database.disconnect()


@pytest.fixture
def repo(db):
    return UserRepository(db)


async def test_ensure_exists_creates_user(repo, db):
    """Verify that ensure_exists inserts a new user."""
    user_id = "wa:12345"
    await repo.ensure_exists(user_id)

    row = await db.fetchrow("SELECT id, display_name, platform FROM users WHERE id = $1", user_id)
    assert row is not None
    assert row["id"] == "wa:12345"
    assert row["display_name"] == "wa:12345"  # defaults to user_id
    assert row["platform"] == "wa"


async def test_ensure_exists_with_display_name(repo, db):
    """Verify that ensure_exists uses provided display_name."""
    user_id = "tg:67890"
    display_name = "John Doe"
    await repo.ensure_exists(user_id, display_name)

    row = await db.fetchrow("SELECT display_name FROM users WHERE id = $1", user_id)
    assert row["display_name"] == "John Doe"


async def test_ensure_exists_idempotent(repo, db):
    """Verify that calling ensure_exists twice doesn't error."""
    user_id = "wa:99999"
    await repo.ensure_exists(user_id)
    await repo.ensure_exists(user_id)  # Should not raise

    rows = await db.fetch("SELECT id FROM users WHERE id = $1", user_id)
    assert len(rows) == 1  # Only one row inserted


async def test_ensure_exists_extracts_platform(repo, db):
    """Verify that platform is extracted from user_id prefix."""
    test_cases = [
        ("wa:123", "wa"),
        ("tg:456", "tg"),
        ("discord:789", "discord"),
        ("noplat", "unknown"),  # No colon
    ]

    for user_id, expected_platform in test_cases:
        await repo.ensure_exists(user_id)
        row = await db.fetchrow("SELECT platform FROM users WHERE id = $1", user_id)
        assert row["platform"] == expected_platform, f"Failed for {user_id}"
