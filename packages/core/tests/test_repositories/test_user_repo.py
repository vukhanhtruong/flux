"""Tests for SqliteUserRepository."""
import pytest
from flux_core.models.user_profile import UserProfile, UserProfileCreate
from flux_core.sqlite.user_repo import SqliteUserRepository


@pytest.fixture
def repo(conn):
    return SqliteUserRepository(conn)


class TestEnsureExists:
    def test_creates_new_user(self, repo, conn):
        repo.ensure_exists("tg:123", "Alice")
        row = conn.execute("SELECT * FROM users WHERE id = ?", ("tg:123",)).fetchone()
        assert row is not None
        assert row["display_name"] == "Alice"
        assert row["platform"] == "tg"

    def test_idempotent(self, repo, conn):
        repo.ensure_exists("tg:123", "Alice")
        repo.ensure_exists("tg:123", "Bob")  # should not raise
        row = conn.execute("SELECT * FROM users WHERE id = ?", ("tg:123",)).fetchone()
        assert row["display_name"] == "Alice"  # unchanged

    def test_defaults_display_name(self, repo, conn):
        repo.ensure_exists("tg:456")
        row = conn.execute("SELECT * FROM users WHERE id = ?", ("tg:456",)).fetchone()
        assert row["display_name"] == "tg:456"

    def test_unknown_platform(self, repo, conn):
        repo.ensure_exists("discord:99")
        row = conn.execute("SELECT * FROM users WHERE id = ?", ("discord:99",)).fetchone()
        assert row["platform"] == "discord"


class TestCreateProfile:
    def test_creates_user_profile(self, repo):
        create = UserProfileCreate(
            username="alice",
            channel="telegram",
            platform_id="12345",
            currency="USD",
            timezone="UTC",
            locale="en-US",
        )
        profile = repo.create_profile(create)
        assert isinstance(profile, UserProfile)
        assert profile.user_id == "tg:alice"
        assert profile.username == "alice"
        assert profile.channel == "telegram"
        assert profile.platform_id == "12345"
        assert profile.currency == "USD"

    def test_duplicate_profile_raises(self, repo):
        create = UserProfileCreate(
            username="bob",
            channel="telegram",
            platform_id="111",
        )
        repo.create_profile(create)
        with pytest.raises(Exception):
            repo.create_profile(create)


class TestGetByUserId:
    def test_found(self, repo):
        create = UserProfileCreate(
            username="carol",
            channel="telegram",
            platform_id="222",
        )
        repo.create_profile(create)
        profile = repo.get_by_user_id("tg:carol")
        assert profile is not None
        assert profile.username == "carol"

    def test_not_found(self, repo):
        assert repo.get_by_user_id("tg:nonexistent") is None


class TestGetByPlatformId:
    def test_found(self, repo):
        create = UserProfileCreate(
            username="dave",
            channel="telegram",
            platform_id="333",
        )
        repo.create_profile(create)
        profile = repo.get_by_platform_id("telegram", "333")
        assert profile is not None
        assert profile.username == "dave"

    def test_not_found(self, repo):
        assert repo.get_by_platform_id("telegram", "999") is None


class TestUsernameExists:
    def test_exists(self, repo):
        create = UserProfileCreate(
            username="eve",
            channel="telegram",
            platform_id="444",
        )
        repo.create_profile(create)
        assert repo.username_exists("telegram", "eve") is True

    def test_not_exists(self, repo):
        assert repo.username_exists("telegram", "nobody") is False


class TestUpdate:
    def test_update_currency(self, repo):
        create = UserProfileCreate(
            username="frank",
            channel="telegram",
            platform_id="555",
        )
        repo.create_profile(create)
        profile = repo.update("tg:frank", currency="EUR")
        assert profile.currency == "EUR"

    def test_update_multiple_fields(self, repo):
        create = UserProfileCreate(
            username="grace",
            channel="telegram",
            platform_id="666",
        )
        repo.create_profile(create)
        profile = repo.update("tg:grace", timezone="US/Eastern", locale="en-US")
        assert profile.timezone == "US/Eastern"
        assert profile.locale == "en-US"

    def test_update_username(self, repo):
        create = UserProfileCreate(
            username="hank",
            channel="telegram",
            platform_id="777",
        )
        repo.create_profile(create)
        profile = repo.update("tg:hank", username="henry")
        assert profile.username == "henry"

    def test_update_not_found_raises(self, repo):
        with pytest.raises(ValueError, match="not found"):
            repo.update("tg:ghost", currency="JPY")
