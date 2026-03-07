"""Integration tests for ProfileRepository with real SQLite."""
from flux_core.models.user_profile import UserProfileCreate
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
from flux_bot.db.profile import ProfileRepository

import pytest


@pytest.fixture
def profile_repo(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    migrate(db)
    yield ProfileRepository(db)
    db.disconnect()


async def test_create_and_get_profile(profile_repo):
    """Create a profile and retrieve it."""
    create = UserProfileCreate(
        username="testuser",
        channel="telegram",
        platform_id="99999",
    )
    profile = await profile_repo.create(create)
    assert profile.username == "testuser"
    assert profile.user_id.startswith("tg:")

    found = await profile_repo.get_by_user_id(profile.user_id)
    assert found is not None
    assert found.username == "testuser"


async def test_update_profile(profile_repo):
    """Update profile timezone and verify persistence."""
    create = UserProfileCreate(
        username="updater",
        channel="telegram",
        platform_id="88888",
    )
    profile = await profile_repo.create(create)

    updated = await profile_repo.update(
        profile.user_id, timezone="Asia/Bangkok"
    )
    assert updated.timezone == "Asia/Bangkok"

    found = await profile_repo.get_by_user_id(profile.user_id)
    assert found.timezone == "Asia/Bangkok"
