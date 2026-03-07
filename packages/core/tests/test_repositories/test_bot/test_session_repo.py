"""Tests for SqliteBotSessionRepository."""
import pytest
from flux_core.sqlite.bot.session_repo import SqliteBotSessionRepository


@pytest.fixture
def repo(conn):
    return SqliteBotSessionRepository(conn)


class TestGetSessionId:
    def test_returns_none_when_no_session(self, repo):
        assert repo.get_session_id("tg:123") is None

    def test_returns_session_id(self, repo):
        repo.upsert("tg:123", "session-abc")
        assert repo.get_session_id("tg:123") == "session-abc"


class TestUpsert:
    def test_insert_new(self, repo):
        repo.upsert("tg:123", "session-1")
        assert repo.get_session_id("tg:123") == "session-1"

    def test_update_existing(self, repo):
        repo.upsert("tg:123", "session-1")
        repo.upsert("tg:123", "session-2")
        assert repo.get_session_id("tg:123") == "session-2"


class TestDelete:
    def test_deletes_session(self, repo):
        repo.upsert("tg:123", "session-1")
        repo.delete("tg:123")
        assert repo.get_session_id("tg:123") is None

    def test_delete_nonexistent_no_error(self, repo):
        repo.delete("tg:nonexistent")  # should not raise
