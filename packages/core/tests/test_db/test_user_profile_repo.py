import pytest
from flux_core.db.connection import Database
from flux_core.db.user_profile_repo import UserProfileRepository
from flux_core.migrations.migrate import migrate
from flux_core.models.user_profile import UserProfileCreate


@pytest.fixture
async def repo(pg_url):
    await migrate(pg_url)
    db = Database(pg_url)
    await db.connect()
    yield UserProfileRepository(db)
    await db.disconnect()


async def test_create_and_get_by_user_id(repo):
    create = UserProfileCreate(
        username="truong-vu", channel="telegram", platform_id="12345",
        currency="VND", timezone="Asia/Ho_Chi_Minh",
    )
    profile = await repo.create(create)
    assert profile.user_id == "tg:12345"
    assert profile.currency == "VND"

    fetched = await repo.get_by_user_id("tg:12345")
    assert fetched is not None
    assert fetched.username == "truong-vu"


async def test_get_by_platform_id(repo):
    create = UserProfileCreate(
        username="another-user", channel="telegram", platform_id="99999",
    )
    await repo.create(create)

    fetched = await repo.get_by_platform_id("telegram", "99999")
    assert fetched is not None
    assert fetched.user_id == "tg:99999"


async def test_username_exists(repo):
    create = UserProfileCreate(
        username="taken-name", channel="telegram", platform_id="77777",
    )
    await repo.create(create)

    assert await repo.username_exists("telegram", "taken-name") is True
    assert await repo.username_exists("telegram", "free-name") is False


async def test_get_by_user_id_not_found(repo):
    result = await repo.get_by_user_id("tg:nonexistent")
    assert result is None


async def test_update_currency_and_timezone(repo):
    create = UserProfileCreate(
        username="update-me", channel="telegram", platform_id="11111",
        currency="VND", timezone="Asia/Ho_Chi_Minh",
    )
    await repo.create(create)

    updated = await repo.update(
        "tg:11111",
        currency="USD",
        timezone="America/New_York",
        locale="en-US",
    )
    assert updated.currency == "USD"
    assert updated.timezone == "America/New_York"
    assert updated.locale == "en-US"
    assert updated.username == "update-me"
    assert updated.user_id == "tg:11111"


async def test_update_username_keeps_user_id(repo):
    """Changing username should NOT change user_id (which is based on platform_id)."""
    create = UserProfileCreate(
        username="old-name", channel="telegram", platform_id="22222",
    )
    await repo.create(create)

    updated = await repo.update("tg:22222", username="new-name")
    assert updated.username == "new-name"
    assert updated.user_id == "tg:22222"  # user_id unchanged

    fetched = await repo.get_by_user_id("tg:22222")
    assert fetched is not None
    assert fetched.username == "new-name"


async def test_update_username_conflict_raises(repo):
    await repo.create(UserProfileCreate(
        username="taken", channel="telegram", platform_id="33333",
    ))
    await repo.create(UserProfileCreate(
        username="clashing", channel="telegram", platform_id="44444",
    ))

    with pytest.raises(ValueError, match="username already taken"):
        await repo.update("tg:44444", username="taken")
